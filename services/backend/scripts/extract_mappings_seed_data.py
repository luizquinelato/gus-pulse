"""
Extract seed data from database to JSON files.

This script extracts data from multiple tables and generates 2 JSON files:

FILE 1: 0002_initial_seed_data_wex_custom_fields.json
- projects (only those related to custom fields)
- custom_fields
- custom_fields_projects (junction table)
- custom_fields_mappings

FILE 2: 0002_initial_seed_data_wex_mappings.json
- workflows
- workflow_steps
- statuses_categories
- statuses_mappings
- wits_hierarchies
- wits_mappings

Usage:
    python services/backend/scripts/extract_custom_fields_seed_data.py
"""

import os
import sys
import json
import psycopg2
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def extract_custom_fields_data():
    """Extract custom fields related data from database."""

    # Load environment variables from .env file
    from dotenv import load_dotenv

    # Try to find .env file in multiple locations
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),  # services/backend/.env
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'),  # project root/.env
    ]

    print(f"🔍 Looking for .env files:")
    env_loaded = False
    for env_path in env_paths:
        abs_path = os.path.abspath(env_path)
        exists = os.path.exists(env_path)
        print(f"   - {abs_path}: {'✅ Found' if exists else '❌ Not found'}")
        if exists and not env_loaded:
            load_dotenv(env_path, override=True)
            print(f"   📋 Loaded environment from: {abs_path}")
            env_loaded = True

    if not env_loaded:
        print("   ⚠️  No .env file found, using system environment variables")

    # Database connection parameters
    db_params = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', '5432')),
        'database': os.getenv('POSTGRES_DB', 'pulse_db'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    print(f"🔌 Connecting to database: {db_params['host']}:{db_params['port']}/{db_params['database']}")
    
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Get tenant_id for WEX (assuming tenant_id=1 for WEX)
        tenant_id = 1
        
        # Get integration_id for Jira integration
        cursor.execute("""
            SELECT id FROM integrations
            WHERE tenant_id = %s AND provider = 'Jira'
            LIMIT 1
        """, (tenant_id,))
        
        integration_result = cursor.fetchone()
        if not integration_result:
            print("❌ No Jira integration found for WEX tenant")
            return None
        
        integration_id = integration_result[0]
        print(f"📊 Found Jira integration_id: {integration_id}")
        
        # Initialize data structure
        seed_data = {
            'metadata': {
                'extracted_at': datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
                'tenant_id': tenant_id,
                'integration_id': integration_id,
                'description': 'Custom fields seed data for WEX tenant'
            },
            'projects': [],
            'custom_fields': [],
            'custom_fields_projects': [],
            'custom_fields_mappings': []
        }
        
        # 1. Extract custom_fields
        print("📥 Extracting custom_fields...")
        cursor.execute("""
            SELECT external_id, name, field_type, operations, active
            FROM custom_fields
            WHERE tenant_id = %s AND integration_id = %s
            ORDER BY external_id
        """, (tenant_id, integration_id))
        
        for row in cursor.fetchall():
            seed_data['custom_fields'].append({
                'external_id': row[0],
                'name': row[1],
                'field_type': row[2],
                'operations': row[3],
                'active': row[4]
            })
        
        print(f"   ✅ Extracted {len(seed_data['custom_fields'])} custom fields")
        
        # 2. Extract custom_fields_projects relationships
        print("📥 Extracting custom_fields_projects...")
        cursor.execute("""
            SELECT cf.external_id, p.key
            FROM custom_fields_projects cfp
            JOIN custom_fields cf ON cfp.custom_field_id = cf.id
            JOIN projects p ON cfp.project_id = p.id
            WHERE cf.tenant_id = %s AND cf.integration_id = %s
            ORDER BY cf.external_id, p.key
        """, (tenant_id, integration_id))
        
        for row in cursor.fetchall():
            seed_data['custom_fields_projects'].append({
                'custom_field_external_id': row[0],
                'project_key': row[1]
            })
        
        print(f"   ✅ Extracted {len(seed_data['custom_fields_projects'])} custom field-project relationships")
        
        # 3. Extract projects (only those used in custom_fields_projects)
        print("📥 Extracting projects...")
        cursor.execute("""
            SELECT DISTINCT p.external_id, p.key, p.name, p.project_type, p.active
            FROM projects p
            JOIN custom_fields_projects cfp ON p.id = cfp.project_id
            JOIN custom_fields cf ON cfp.custom_field_id = cf.id
            WHERE p.tenant_id = %s AND p.integration_id = %s
            ORDER BY p.key
        """, (tenant_id, integration_id))
        
        for row in cursor.fetchall():
            seed_data['projects'].append({
                'external_id': row[0],
                'key': row[1],
                'name': row[2],
                'project_type': row[3],
                'active': row[4]
            })
        
        print(f"   ✅ Extracted {len(seed_data['projects'])} projects")
        
        # 4. Extract custom_fields_mappings (convert IDs to external_ids)
        print("📥 Extracting custom_fields_mappings...")
        cursor.execute("""
            SELECT
                cfm.active,
                cf_team.external_id as team_field_external_id,
                cf_sprints.external_id as sprints_field_external_id,
                cf_dev.external_id as development_field_external_id,
                cf_sp.external_id as story_points_field_external_id,
                cf_ac.external_id as acceptance_criteria_field_external_id,
                cf_01.external_id as custom_field_01_external_id,
                cf_02.external_id as custom_field_02_external_id,
                cf_03.external_id as custom_field_03_external_id,
                cf_04.external_id as custom_field_04_external_id,
                cf_05.external_id as custom_field_05_external_id,
                cf_06.external_id as custom_field_06_external_id,
                cf_07.external_id as custom_field_07_external_id,
                cf_08.external_id as custom_field_08_external_id,
                cf_09.external_id as custom_field_09_external_id,
                cf_10.external_id as custom_field_10_external_id,
                cf_11.external_id as custom_field_11_external_id,
                cf_12.external_id as custom_field_12_external_id,
                cf_13.external_id as custom_field_13_external_id,
                cf_14.external_id as custom_field_14_external_id,
                cf_15.external_id as custom_field_15_external_id,
                cf_16.external_id as custom_field_16_external_id,
                cf_17.external_id as custom_field_17_external_id,
                cf_18.external_id as custom_field_18_external_id,
                cf_19.external_id as custom_field_19_external_id,
                cf_20.external_id as custom_field_20_external_id
            FROM custom_fields_mappings cfm
            LEFT JOIN custom_fields cf_team ON cfm.team_field_id = cf_team.id
            LEFT JOIN custom_fields cf_sprints ON cfm.sprints_field_id = cf_sprints.id
            LEFT JOIN custom_fields cf_dev ON cfm.development_field_id = cf_dev.id
            LEFT JOIN custom_fields cf_sp ON cfm.story_points_field_id = cf_sp.id
            LEFT JOIN custom_fields cf_ac ON cfm.acceptance_criteria_field_id = cf_ac.id
            LEFT JOIN custom_fields cf_01 ON cfm.custom_field_01_id = cf_01.id
            LEFT JOIN custom_fields cf_02 ON cfm.custom_field_02_id = cf_02.id
            LEFT JOIN custom_fields cf_03 ON cfm.custom_field_03_id = cf_03.id
            LEFT JOIN custom_fields cf_04 ON cfm.custom_field_04_id = cf_04.id
            LEFT JOIN custom_fields cf_05 ON cfm.custom_field_05_id = cf_05.id
            LEFT JOIN custom_fields cf_06 ON cfm.custom_field_06_id = cf_06.id
            LEFT JOIN custom_fields cf_07 ON cfm.custom_field_07_id = cf_07.id
            LEFT JOIN custom_fields cf_08 ON cfm.custom_field_08_id = cf_08.id
            LEFT JOIN custom_fields cf_09 ON cfm.custom_field_09_id = cf_09.id
            LEFT JOIN custom_fields cf_10 ON cfm.custom_field_10_id = cf_10.id
            LEFT JOIN custom_fields cf_11 ON cfm.custom_field_11_id = cf_11.id
            LEFT JOIN custom_fields cf_12 ON cfm.custom_field_12_id = cf_12.id
            LEFT JOIN custom_fields cf_13 ON cfm.custom_field_13_id = cf_13.id
            LEFT JOIN custom_fields cf_14 ON cfm.custom_field_14_id = cf_14.id
            LEFT JOIN custom_fields cf_15 ON cfm.custom_field_15_id = cf_15.id
            LEFT JOIN custom_fields cf_16 ON cfm.custom_field_16_id = cf_16.id
            LEFT JOIN custom_fields cf_17 ON cfm.custom_field_17_id = cf_17.id
            LEFT JOIN custom_fields cf_18 ON cfm.custom_field_18_id = cf_18.id
            LEFT JOIN custom_fields cf_19 ON cfm.custom_field_19_id = cf_19.id
            LEFT JOIN custom_fields cf_20 ON cfm.custom_field_20_id = cf_20.id
            WHERE cfm.tenant_id = %s AND cfm.integration_id = %s
            LIMIT 1
        """, (tenant_id, integration_id))

        mapping_row = cursor.fetchone()
        if mapping_row:
            seed_data['custom_fields_mappings'].append({
                'active': mapping_row[0],
                'team_field_external_id': mapping_row[1],
                'sprints_field_external_id': mapping_row[2],
                'development_field_external_id': mapping_row[3],
                'story_points_field_external_id': mapping_row[4],
                'acceptance_criteria_field_external_id': mapping_row[5],
                'custom_field_01_external_id': mapping_row[6],
                'custom_field_02_external_id': mapping_row[7],
                'custom_field_03_external_id': mapping_row[8],
                'custom_field_04_external_id': mapping_row[9],
                'custom_field_05_external_id': mapping_row[10],
                'custom_field_06_external_id': mapping_row[11],
                'custom_field_07_external_id': mapping_row[12],
                'custom_field_08_external_id': mapping_row[13],
                'custom_field_09_external_id': mapping_row[14],
                'custom_field_10_external_id': mapping_row[15],
                'custom_field_11_external_id': mapping_row[16],
                'custom_field_12_external_id': mapping_row[17],
                'custom_field_13_external_id': mapping_row[18],
                'custom_field_14_external_id': mapping_row[19],
                'custom_field_15_external_id': mapping_row[20],
                'custom_field_16_external_id': mapping_row[21],
                'custom_field_17_external_id': mapping_row[22],
                'custom_field_18_external_id': mapping_row[23],
                'custom_field_19_external_id': mapping_row[24],
                'custom_field_20_external_id': mapping_row[25]
            })
            print(f"   ✅ Extracted custom_fields_mappings with external_ids")
        else:
            print(f"   ⚠️ No custom_fields_mappings found")

        # Close database connection
        cursor.close()
        conn.close()

        return seed_data

    except Exception as e:
        print(f"❌ Error extracting data: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_mappings_data(conn, tenant_id, integration_id):
    """Extract mapping tables data from database."""
    cursor = conn.cursor()

    # Initialize data structure
    mappings_data = {
        'metadata': {
            'extracted_at': datetime.now(datetime.UTC).isoformat() if hasattr(datetime, 'UTC') else datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'integration_id': integration_id,
            'description': 'Mapping tables seed data for WEX tenant'
        },
        'workflows': [],
        'workflow_steps': [],
        'statuses_categories': [],
        'statuses_mappings': [],
        'wits_hierarchies': [],
        'wits_mappings': []
    }

    # 1. Extract workflows
    print("📥 Extracting workflows...")
    cursor.execute("""
        SELECT w.name, i.provider as integration_name, w.active
        FROM workflows w
        LEFT JOIN integrations i ON w.integration_id = i.id
        WHERE w.tenant_id = %s AND w.integration_id = %s
        ORDER BY w.id
    """, (tenant_id, integration_id))

    for row in cursor.fetchall():
        mappings_data['workflows'].append({
            'name': row[0],
            'integration_name': row[1],
            'active': row[2]
        })

    print(f"   ✅ Extracted {len(mappings_data['workflows'])} workflows")

    # 2. Extract workflow_steps
    print("📥 Extracting workflow_steps...")
    cursor.execute("""
        SELECT w.name as workflow_name, ws.name as step_name, ws."order",
               s.name as status_name, ws.is_commitment_point,
               i.provider as integration_name, ws.active
        FROM workflows_steps ws
        JOIN workflows w ON ws.workflow_id = w.id
        LEFT JOIN statuses s ON ws.status_id = s.id
        LEFT JOIN integrations i ON ws.integration_id = i.id
        WHERE ws.tenant_id = %s AND ws.integration_id = %s
        ORDER BY w.name, ws."order"
    """, (tenant_id, integration_id))

    for row in cursor.fetchall():
        mappings_data['workflow_steps'].append({
            'workflow_name': row[0],
            'step_name': row[1],
            'order': row[2],
            'status_name': row[3],
            'is_commitment_point': row[4],
            'integration_name': row[5],
            'active': row[6]
        })

    print(f"   ✅ Extracted {len(mappings_data['workflow_steps'])} workflow steps")

    # 3. Extract statuses_categories
    print("📥 Extracting statuses_categories...")
    cursor.execute("""
        SELECT sc.name, sc.description, sc.is_waiting, sc.is_done,
               i.provider as integration_name, sc.active
        FROM statuses_categories sc
        LEFT JOIN integrations i ON sc.integration_id = i.id
        WHERE sc.tenant_id = %s
        ORDER BY sc.id
    """, (tenant_id,))

    for row in cursor.fetchall():
        mappings_data['statuses_categories'].append({
            'name': row[0],
            'description': row[1],
            'is_waiting': row[2],
            'is_done': row[3],
            'integration_name': row[4],
            'active': row[5]
        })

    print(f"   ✅ Extracted {len(mappings_data['statuses_categories'])} status categories")

    # 4. Extract statuses_mappings
    print("📥 Extracting statuses_mappings...")
    cursor.execute("""
        SELECT sm.status_from, sm.status_to, sc.name as category_name,
               i.provider as integration_name, sm.active
        FROM statuses_mappings sm
        JOIN statuses_categories sc ON sm.status_category_id = sc.id
        LEFT JOIN integrations i ON sm.integration_id = i.id
        WHERE sm.tenant_id = %s AND sm.integration_id = %s
        ORDER BY sm.status_from
    """, (tenant_id, integration_id))

    for row in cursor.fetchall():
        mappings_data['statuses_mappings'].append({
            'status_from': row[0],
            'status_to': row[1],
            'category_name': row[2],
            'integration_name': row[3],
            'active': row[4]
        })

    print(f"   ✅ Extracted {len(mappings_data['statuses_mappings'])} status mappings")

    # 5. Extract wits_hierarchies
    print("📥 Extracting wits_hierarchies...")
    cursor.execute("""
        SELECT wh.name, wh.level, wh.description,
               i.provider as integration_name, wh.active
        FROM wits_hierarchies wh
        LEFT JOIN integrations i ON wh.integration_id = i.id
        WHERE wh.tenant_id = %s
        ORDER BY wh.level
    """, (tenant_id,))

    for row in cursor.fetchall():
        mappings_data['wits_hierarchies'].append({
            'name': row[0],
            'level': row[1],
            'description': row[2],
            'integration_name': row[3],
            'active': row[4]
        })

    print(f"   ✅ Extracted {len(mappings_data['wits_hierarchies'])} WIT hierarchies")

    # 6. Extract wits_mappings
    print("📥 Extracting wits_mappings...")
    cursor.execute("""
        SELECT wm.wit_from, wm.wit_to, wh.level as hierarchy_level,
               i.provider as integration_name, wm.active
        FROM wits_mappings wm
        JOIN wits_hierarchies wh ON wm.wits_hierarchy_id = wh.id
        LEFT JOIN integrations i ON wm.integration_id = i.id
        WHERE wm.tenant_id = %s AND wm.integration_id = %s
        ORDER BY wm.wit_from
    """, (tenant_id, integration_id))

    for row in cursor.fetchall():
        mappings_data['wits_mappings'].append({
            'wit_from': row[0],
            'wit_to': row[1],
            'hierarchy_level': row[2],
            'integration_name': row[3],
            'active': row[4]
        })

    print(f"   ✅ Extracted {len(mappings_data['wits_mappings'])} WIT mappings")

    return mappings_data

def save_to_json(data, output_path):
    """Save data to JSON file."""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✅ Data saved to: {output_path}")
        return True

    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Starting seed data extraction...")
    print("=" * 80)

    # Extract custom fields data
    print("\n📦 PART 1: Custom Fields Data")
    print("-" * 80)
    custom_fields_data = extract_custom_fields_data()

    # Extract mappings data
    print("\n📦 PART 2: Mapping Tables Data")
    print("-" * 80)
    mappings_data = None

    if custom_fields_data:
        # Reuse connection info from custom fields extraction
        from dotenv import load_dotenv

        env_paths = [
            os.path.join(os.path.dirname(__file__), '..', '.env'),
            os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'),
        ]

        for env_path in env_paths:
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                break

        db_params = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'pulse_db'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }

        try:
            conn = psycopg2.connect(**db_params)
            tenant_id = custom_fields_data['metadata']['tenant_id']
            integration_id = custom_fields_data['metadata']['integration_id']

            mappings_data = extract_mappings_data(conn, tenant_id, integration_id)
            conn.close()

        except Exception as e:
            print(f"❌ Error extracting mappings data: {e}")
            import traceback
            traceback.print_exc()

    # Save both files
    if custom_fields_data and mappings_data:
        print("\n💾 Saving JSON files...")
        print("-" * 80)

        # Save custom fields data
        custom_fields_path = os.path.join(
            os.path.dirname(__file__),
            'migrations',
            '0002_initial_seed_data_wex_custom_fields.json'
        )

        # Save mappings data
        mappings_path = os.path.join(
            os.path.dirname(__file__),
            'migrations',
            '0002_initial_seed_data_wex_mappings.json'
        )

        success1 = save_to_json(custom_fields_data, custom_fields_path)
        success2 = save_to_json(mappings_data, mappings_path)

        if success1 and success2:
            print(f"\n" + "=" * 80)
            print(f"📊 EXTRACTION SUMMARY")
            print("=" * 80)
            print(f"\n📄 File 1: Custom Fields Data")
            print(f"   - Projects: {len(custom_fields_data['projects'])}")
            print(f"   - Custom Fields: {len(custom_fields_data['custom_fields'])}")
            print(f"   - Custom Fields-Projects: {len(custom_fields_data['custom_fields_projects'])}")
            print(f"   - Custom Fields Mappings: {len(custom_fields_data['custom_fields_mappings'])}")

            print(f"\n📄 File 2: Mapping Tables Data")
            print(f"   - Workflows: {len(mappings_data['workflows'])}")
            print(f"   - Workflow Steps: {len(mappings_data['workflow_steps'])}")
            print(f"   - Status Categories: {len(mappings_data['statuses_categories'])}")
            print(f"   - Status Mappings: {len(mappings_data['statuses_mappings'])}")
            print(f"   - WIT Hierarchies: {len(mappings_data['wits_hierarchies'])}")
            print(f"   - WIT Mappings: {len(mappings_data['wits_mappings'])}")

            print(f"\n✅ Extraction complete!")
            print("=" * 80)
        else:
            print(f"\n❌ Failed to save data")
            sys.exit(1)
    else:
        print(f"\n❌ Failed to extract data")
        sys.exit(1)

