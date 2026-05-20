#!/usr/bin/env python3
"""
Migration 0002: Initial Seed Data
Description: Inserts initial seed data for WEX tenant including DORA benchmarks, tenants, integrations, workflows, status mappings, users, and system settings (excludes color-related data)
Author: Pulse Platform Team
Date: 2025-08-18
"""

import os
import sys
import argparse
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add the backend service to the path to access database configuration
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def get_database_connection():
    """Get database connection using backend service configuration."""
    try:
        from app.core.config import Settings
        config = Settings()

        connection = psycopg2.connect(
            host=config.POSTGRES_HOST,
            port=config.POSTGRES_PORT,
            database=config.POSTGRES_DATABASE,
            user=config.POSTGRES_USER,
            password=config.POSTGRES_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return connection
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        raise

def apply(connection):
    """Apply the migration."""
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        # Set timezone for this session to match application timezone
        cursor.execute("SET timezone = 'America/New_York';")
        print("🌍 Session timezone set to America/New_York")

        print("🚀 Applying Migration 0002: Initial Seed Data")

        # 1. Insert global DORA market benchmarks (2024) and insights
        print("📋 Inserting DORA market benchmarks...")
        cursor.execute("""
            INSERT INTO dora_market_benchmarks (report_year, performance_tier, metric_name, metric_value, metric_unit) VALUES
                (2024, 'Elite', 'Deployment Frequency', 'On-demand (multiple deploys per day)', NULL),
                (2024, 'High', 'Deployment Frequency', 'Between once per day and once per week', NULL),
                (2024, 'Medium', 'Deployment Frequency', 'Between once per week and once per month', NULL),
                (2024, 'Low', 'Deployment Frequency', 'Less than once per month', NULL),

                (2024, 'Elite', 'Lead Time for Changes', 'Less than one day', 'days'),
                (2024, 'High', 'Lead Time for Changes', 'Between one day and one week', 'days'),
                (2024, 'Medium', 'Lead Time for Changes', 'Between one week and one month', 'months'),
                (2024, 'Low', 'Lead Time for Changes', 'More than one month', 'months'),

                (2024, 'Elite', 'Change Failure Rate', '0-15%', 'percentage'),
                (2024, 'High', 'Change Failure Rate', '16-30%', 'percentage'),
                (2024, 'Medium', 'Change Failure Rate', '31-45%', 'percentage'),
                (2024, 'Low', 'Change Failure Rate', '46-60%', 'percentage'),

                (2024, 'Elite', 'Time to Restore Service', 'Less than one hour', 'hours'),
                (2024, 'High', 'Time to Restore Service', 'Less than one day', 'hours'),
                (2024, 'Medium', 'Time to Restore Service', 'One day to one week', 'days'),
                (2024, 'Low', 'Time to Restore Service', 'More than one week', 'weeks')
            ON CONFLICT (report_year, performance_tier, metric_name) DO NOTHING;
        """)

        print("📋 Inserting DORA metric insights...")
        cursor.execute("""
            INSERT INTO dora_metric_insights (report_year, metric_name, insight_text) VALUES
                (2024, 'Deployment Frequency', 'Elite performers have fully automated and reliable deployment pipelines, allowing them to release changes to production as soon as they are ready. This continuous flow of small, frequent deployments reduces the risk associated with each release and allows for rapid feedback loops.'),
                (2024, 'Lead Time for Changes', 'A short lead time for changes is a strong indicator of an efficient and automated software delivery process. Elite teams have streamlined their code review, testing, and deployment processes to minimize delays and ensure a smooth path from commit to production.'),
                (2024, 'Change Failure Rate', 'A low change failure rate is a testament to the quality of a team''s testing and validation processes. Elite performers invest heavily in automated testing and comprehensive pre-deployment checks to catch work_items before they impact users. The significant jump in failure rate for low performers highlights the challenges of manual and error-prone deployment processes.'),
                (2024, 'Time to Restore Service', 'Elite performers have robust monitoring and observability in place, coupled with well-defined incident response and rollback procedures. This enables them to recover from failures swiftly, minimizing downtime and user impact. The ability to restore service quickly is a hallmark of a resilient and mature operational capability.')
            ON CONFLICT (report_year, metric_name) DO NOTHING;
        """)

        print("✅ DORA data inserted")

        # 2. Insert default tenant (WEX) - Premium tier
        print("📋 Creating WEX tenant (Premium tier)...")

        # Check if WEX tenant already exists
        cursor.execute("SELECT id FROM tenants WHERE name = 'WEX' LIMIT 1;")
        existing_tenant = cursor.fetchone()

        if existing_tenant:
            print(f"   ℹ️ WEX tenant already exists (ID: {existing_tenant[0]}), updating tier to premium...")
            cursor.execute("""
                UPDATE tenants
                SET tier = 'premium',
                    website = 'https://www.wexinc.com',
                    assets_folder = 'wex',
                    logo_filename = 'logo.png',
                    color_schema_mode = 'default',
                    active = TRUE,
                    last_updated_at = NOW()
                WHERE name = 'WEX';
            """)
        else:
            print("   ➕ Creating new WEX tenant...")
            cursor.execute("""
                INSERT INTO tenants (name, website, assets_folder, logo_filename, color_schema_mode, tier, active, created_at, last_updated_at)
                VALUES ('WEX', 'https://www.wexinc.com', 'wex', 'logo.png', 'default', 'premium', TRUE, NOW(), NOW());
            """)

        # Get the tenant ID for seed data
        cursor.execute("SELECT id FROM tenants WHERE name = 'WEX' LIMIT 1;")
        tenant_result = cursor.fetchone()
        if not tenant_result:
            raise Exception("Failed to create or find WEX tenant")
        tenant_id = tenant_result['id']
        print(f"   ✅ WEX tenant created/found with ID: {tenant_id}")

        # 3. Insert premium queue worker configurations
        print("📋 Creating premium queue worker configurations...")
        cursor.execute("""
            INSERT INTO system_settings (tenant_id, setting_key, setting_value, description, created_at, last_updated_at)
            VALUES
                (%(tenant_id)s, 'premium_extraction_workers', '5', 'Number of workers for premium extraction queue', NOW(), NOW()),
                (%(tenant_id)s, 'premium_transform_workers', '5', 'Number of workers for premium transform queue', NOW(), NOW()),
                (%(tenant_id)s, 'premium_embedding_workers', '15', 'Number of workers for premium embedding queue', NOW(), NOW())
            ON CONFLICT (tenant_id, setting_key) DO UPDATE SET
                setting_value = EXCLUDED.setting_value,
                description = EXCLUDED.description,
                last_updated_at = NOW();
        """, {'tenant_id': tenant_id})
        print("✅ Premium queue worker configurations inserted")

        # 4. Create integrations (JIRA and GitHub only)
        print("📋 Creating integrations...")

        # Get credentials from environment if available
        try:
            # Load environment variables from .env file
            from dotenv import load_dotenv
            import os

            # Try to find .env file in multiple locations
            # __file__ is in migrations/, so '..' = scripts/, '../..' = backend/
            env_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', '.env'),  # services/backend/.env
                os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'),  # project root/.env
            ]

            print(f"   🔍 DEBUG - Looking for .env files:")
            for i, env_path in enumerate(env_paths):
                abs_path = os.path.abspath(env_path)
                exists = os.path.exists(env_path)
                print(f"   🔍 Path {i+1}: {abs_path} - Exists: {exists}")

            env_loaded = False
            for env_path in env_paths:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    print(f"   📋 Loading credentials from: {os.path.abspath(env_path)}")
                    env_loaded = True
                    break

            if not env_loaded:
                print("   ⚠️  No .env file found, using system environment variables")

            from app.core.config import Settings
            from app.core.config import AppConfig
            settings = Settings()

            # Try to load encryption key
            try:
                key = AppConfig.load_key()
                encryption_available = True
                print("   🔐 Encryption available - tokens will be encrypted")
            except Exception as e:
                print(f"   ⚠️  Encryption key not available: {e}")
                encryption_available = False

        except Exception as e:
            print(f"   ⚠️  Could not load settings: {e}")
            settings = None
            encryption_available = False

        # JIRA Integration - Reading credentials from .env file
        jira_url = os.getenv('JIRA_URL')
        jira_username = os.getenv('JIRA_USERNAME')
        jira_token = os.getenv('JIRA_TOKEN')
        jira_password = None
        jira_active = False

        if jira_url and jira_username and jira_token:
            print(f"   📋 Found JIRA credentials in .env: {jira_url}, {jira_username}")
            try:
                if encryption_available:
                    key = AppConfig.load_key()
                    jira_password = AppConfig.encrypt_token(jira_token, key)
                    print("   🔐 JIRA token encrypted successfully")
                    jira_active = True
                else:
                    jira_password = jira_token
                    print("   ⚠️  JIRA token stored unencrypted (AppConfig not available)")
                    jira_active = True
            except Exception as e:
                print(f"   ❌ Failed to process JIRA credentials: {e}")
                jira_active = False
        else:
            print("   ⚠️  JIRA credentials not found in .env file")
            # Use default values for inactive integration
            jira_url = "https://wexinc.atlassian.net"
            jira_username = "gustavo.quinelato@wexinc.com"

        # Jira settings configuration
        jira_settings = {
            "projects": ["BEN", "BST", "CDH", "WSI", "WX", "BENBR"],
            "base_search": None,  # Optional additional filters
            "sync_config": {
                "batch_size": 100,
                "rate_limit": 10
            }
        }

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "Jira", "Data", jira_username, jira_password, jira_url, json.dumps(jira_settings),
            "jira.svg", tenant_id, jira_active
        ))

        jira_result = cursor.fetchone()
        if jira_result:
            jira_integration_id = jira_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'Jira' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                jira_integration_id = result['id']
            else:
                raise Exception("Failed to create or find Jira integration")

        print(f"   ✅ JIRA integration created (ID: {jira_integration_id}, active: {jira_active})")

        # GitHub Integration - Reading credentials from .env file
        github_token = os.getenv('GITHUB_TOKEN')
        github_password = None
        github_active = False  # Always set to False - user must activate manually

        if github_token:
            print(f"   📋 Found GitHub token in .env: {github_token[:10]}...")
            try:
                if encryption_available:
                    key = AppConfig.load_key()
                    github_password = AppConfig.encrypt_token(github_token, key)
                    print("   🔐 GitHub token encrypted successfully")
                else:
                    github_password = github_token
                    print("   ⚠️  GitHub token stored unencrypted (AppConfig not available)")
            except Exception as e:
                print(f"   ❌ Failed to process GitHub credentials: {e}")
        else:
            print("   ⚠️  GitHub token not found in .env file")

        # GitHub settings configuration
        github_org = os.getenv("GITHUB_ORG", "wexinc")
        github_settings = {
            "organization": github_org,  # GitHub organization
            "repository_filter": ["health-", "bp-"],  # Repository name filters (array of patterns)
            "sync_config": {
                "batch_size": 50,
                "rate_limit": 5000  # GitHub API rate limit
            }
        }

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "GitHub", "Data", github_org, github_password, "https://api.github.com", json.dumps(github_settings),
            "github.svg", tenant_id, github_active
        ))

        github_result = cursor.fetchone()
        if github_result:
            github_integration_id = github_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'GitHub' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                github_integration_id = result['id']
            else:
                raise Exception("Failed to create or find GitHub integration")

        print(f"   ✅ GitHub integration created (ID: {github_integration_id}, active: {github_active})")

        # Create AI Gateway integration
        print("   📋 Creating AI Gateway integration...")
        ai_gateway_base_url = os.getenv("WEX_AI_GATEWAY_BASE_URL", "https://aips-ai-gateway.dev.ai-platform.int.wexfabric.com/")
        ai_gateway_api_key = os.getenv("WEX_AI_GATEWAY_API_KEY")
        ai_fallback_model = os.getenv("AI_FALLBACK_MODEL")

        # Encrypt the API key if available, otherwise store None (integration will be inactive)
        encrypted_ai_key = None
        ai_gateway_active = False
        if ai_gateway_api_key:
            try:
                encrypted_ai_key = AppConfig.encrypt_token(ai_gateway_api_key, key)
                ai_gateway_active = True
                print("   🔐 AI Gateway API key encrypted successfully")
            except Exception as e:
                print(f"   ⚠️ Could not encrypt AI Gateway API key: {e} - integration will be inactive")
        else:
            print("   ⚠️ WEX_AI_GATEWAY_API_KEY not set in .env - AI Gateway integration will be inactive")

        # Primary AI Gateway settings — model read from AI_MODEL env var
        ai_model = os.getenv("AI_MODEL", "bedrock-claude-sonnet-4-6-v1")
        ai_gateway_settings = {
            "model": ai_model,
            "model_config": {
                "temperature": 0.3,
                "max_tokens": 700,
                "gateway_route": True,
                "source": "external"
            },
            "cost_config": {
                "max_monthly_cost": 1000,
                "alert_threshold": 0.8
            }
        }

        # Always insert the WEX AI Gateway integration — always active for WEX tenant
        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO UPDATE SET
                password = EXCLUDED.password,
                base_url = EXCLUDED.base_url,
                settings = EXCLUDED.settings,
                active = EXCLUDED.active,
                last_updated_at = NOW()
            RETURNING id;
        """, (
            "WEX AI Gateway", "AI", None, encrypted_ai_key, ai_gateway_base_url, json.dumps(ai_gateway_settings),
            "wex-ai-gateway.svg", tenant_id, True
        ))

        ai_gateway_result = cursor.fetchone()
        if ai_gateway_result:
            ai_gateway_integration_id = ai_gateway_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'WEX AI Gateway' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                ai_gateway_integration_id = result['id']
            else:
                raise Exception("Failed to create or find WEX AI Gateway integration")

        print(f"   ✅ AI Gateway integration created (ID: {ai_gateway_integration_id}, model: {ai_model}, active: {ai_gateway_active})")

        # Create fallback AI Gateway integration if fallback model is specified and credentials are available
        if ai_gateway_active and ai_fallback_model:
            ai_fallback_settings = {
                "model": "azure-gpt-4o-mini",
                "model_config": {
                    "temperature": 0.3,
                    "max_tokens": 700,
                    "gateway_route": True,
                    "source": "external"
                },
                "cost_config": {
                    "max_monthly_cost": 500,
                    "alert_threshold": 0.8
                }
            }

            cursor.execute("""
                INSERT INTO integrations (
                    provider, type, username, password, base_url, settings,
                    logo_filename, tenant_id, active, created_at, last_updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (provider, tenant_id) DO NOTHING
                RETURNING id;
            """, (
                "WEX AI Gateway Fallback", "AI", None, encrypted_ai_key, ai_gateway_base_url, json.dumps(ai_fallback_settings),
                "wex-ai-gateway-fallback.svg", tenant_id, True
            ))

            fallback_result = cursor.fetchone()
            if fallback_result:
                fallback_integration_id = fallback_result['id']
                cursor.execute("""
                    UPDATE integrations SET fallback_integration_id = %s
                    WHERE id = %s;
                """, (fallback_integration_id, ai_gateway_integration_id))
                print(f"   ✅ AI Gateway fallback integration created (ID: {fallback_integration_id}, model: {ai_fallback_model})")
                print(f"   🔗 Primary integration (ID: {ai_gateway_integration_id}) linked to fallback (ID: {fallback_integration_id})")

        # Create embedding integrations
        print("   📋 Creating embedding integrations...")

        # Free local embedding (always inserted, inactive - external is primary)
        local_embedding_settings = {
            "model_path": "models/sentence-transformers/all-mpnet-base-v2",
            "cost_tier": "free",
            "gateway_route": False,
            "source": "local"
        }

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "MPNet base-v2", "Embedding", None, None, None, json.dumps(local_embedding_settings),
            "local-embeddings.svg", tenant_id, False  # Inactive - external embeddings are primary
        ))

        local_embedding_result = cursor.fetchone()
        if local_embedding_result:
            local_embedding_id = local_embedding_result['id']
            print(f"   ✅ Local embedding integration created (ID: {local_embedding_id})")

        # Azure external embedding via WEX AI Gateway — always active for WEX tenant
        azure_embedding_settings = {
            "model_path": "azure-text-embedding-3-small",
            "cost_tier": "paid",
            "gateway_route": True,
            "source": "external"
        }

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO UPDATE SET
                password = EXCLUDED.password,
                base_url = EXCLUDED.base_url,
                settings = EXCLUDED.settings,
                active = EXCLUDED.active,
                last_updated_at = NOW()
            RETURNING id;
        """, (
            "Azure 3-small", "Embedding", None, encrypted_ai_key, ai_gateway_base_url, json.dumps(azure_embedding_settings),
            "wex-embeddings.svg", tenant_id, True
        ))

        paid_embedding_result = cursor.fetchone()
        if paid_embedding_result:
            paid_embedding_id = paid_embedding_result['id']
            print(f"   ✅ Azure 3-small embedding integration created (ID: {paid_embedding_id}, active: True)")

        # Create WEX Fabric integration (placeholder for future)
        print("   📋 Creating WEX Fabric integration...")

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "WEX Fabric", "Data", None, None, "https://fabric.wex.com", None,
            "fabric.svg", tenant_id, False  # Inactive until implemented
        ))

        fabric_result = cursor.fetchone()
        if fabric_result:
            fabric_integration_id = fabric_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'WEX Fabric' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                fabric_integration_id = result['id']
            else:
                raise Exception("Failed to create or find WEX Fabric integration")

        print(f"   ✅ WEX Fabric integration created (ID: {fabric_integration_id}, inactive)")

        # Create Active Directory integration (placeholder for future)
        print("   📋 Creating Active Directory integration...")

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "WEX AD", "Data", None, None, "https://login.microsoftonline.com", None,
            "ad.svg", tenant_id, False  # Inactive until implemented
        ))

        ad_result = cursor.fetchone()
        if ad_result:
            ad_integration_id = ad_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'WEX AD' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                ad_integration_id = result['id']
            else:
                raise Exception("Failed to create or find Active Directory integration")

        print(f"   ✅ Active Directory integration created (ID: {ad_integration_id}, inactive)")

        # Create Internal integration for jobs that don't require external integrations
        print("   📋 Creating Internal integration...")

        cursor.execute("""
            INSERT INTO integrations (
                provider, type, username, password, base_url, settings,
                logo_filename, tenant_id, active, created_at, last_updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (provider, tenant_id) DO NOTHING
            RETURNING id;
        """, (
            "Internal", "System", None, None, None, None,
            "internal.svg", tenant_id, True  # Active for internal jobs
        ))

        internal_result = cursor.fetchone()
        if internal_result:
            internal_integration_id = internal_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE provider = 'Internal' AND tenant_id = %s;", (tenant_id,))
            result = cursor.fetchone()
            if result:
                internal_integration_id = result['id']
            else:
                raise Exception("Failed to create or find Internal integration")

        print(f"   ✅ Internal integration created (ID: {internal_integration_id}, active)")

        print("✅ Integrations created")

        # ====================================================================
        # SEED CUSTOM FIELDS DATA (from JSON file)
        # ====================================================================
        print("\n📋 Loading custom fields seed data from JSON...")

        # Load JSON file
        json_file_path = os.path.join(os.path.dirname(__file__), '0002_initial_seed_data_wex_custom_fields.json')

        # Check if file exists and is not empty
        custom_fields_data = None
        if os.path.exists(json_file_path):
            try:
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        custom_fields_data = json.loads(content)
                    else:
                        print(f"   ⚠️  JSON file is empty: {json_file_path}")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON file is invalid: {e}")
        else:
            print(f"   ⚠️  JSON file not found: {json_file_path}")

        # Only proceed if we have valid data with non-empty arrays
        if custom_fields_data and (
            custom_fields_data.get('projects') or
            custom_fields_data.get('custom_fields') or
            custom_fields_data.get('custom_fields_projects') or
            custom_fields_data.get('custom_fields_mappings')
        ):
            print(f"   ✅ Loaded JSON file: {json_file_path}")
            print(f"   📊 Data summary:")
            print(f"      - Projects: {len(custom_fields_data.get('projects', []))}")
            print(f"      - Custom Fields: {len(custom_fields_data.get('custom_fields', []))}")
            print(f"      - Custom Fields-Projects: {len(custom_fields_data.get('custom_fields_projects', []))}")
            print(f"      - Custom Fields Mappings: {len(custom_fields_data.get('custom_fields_mappings', []))}")

            # 1. Add unique constraint to projects table if it doesn't exist
            print("   📋 Adding unique constraint to projects table...")
            cursor.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'projects'
                AND constraint_type = 'UNIQUE'
                AND constraint_name = 'uk_projects_external_id_tenant_integration';
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE projects
                    ADD CONSTRAINT uk_projects_external_id_tenant_integration
                    UNIQUE (external_id, tenant_id, integration_id);
                """)
                print("   ✅ Unique constraint added to projects table")
            else:
                print("   ✅ Unique constraint already exists on projects table")

            # 2. Insert projects (needed for foreign keys)
            print("   📋 Inserting projects...")
            for project in custom_fields_data.get('projects', []):
                cursor.execute("""
                    INSERT INTO projects (external_id, key, name, project_type, integration_id, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (external_id, tenant_id, integration_id) DO UPDATE SET
                        key = EXCLUDED.key,
                        name = EXCLUDED.name,
                        project_type = EXCLUDED.project_type,
                        active = EXCLUDED.active,
                        last_updated_at = NOW();
                """, (
                    project['external_id'],
                    project['key'],
                    project['name'],
                    project.get('project_type'),
                    jira_integration_id,
                    tenant_id,
                    project.get('active', True)
                ))
            print(f"      ✅ Inserted/updated {len(custom_fields_data.get('projects', []))} projects")

            # 2. Insert custom_fields (needed for foreign keys)
            print("   📋 Inserting custom fields...")
            for field in custom_fields_data.get('custom_fields', []):
                # Convert operations dict to JSON string (handle dict, empty dict, and None)
                operations = field.get('operations')
                if isinstance(operations, dict):
                    operations = json.dumps(operations)
                elif operations is None:
                    operations = None
                else:
                    # If it's already a string, keep it as is
                    operations = str(operations)

                cursor.execute("""
                    INSERT INTO custom_fields (external_id, name, field_type, operations, integration_id, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (external_id, integration_id, tenant_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        field_type = EXCLUDED.field_type,
                        operations = EXCLUDED.operations,
                        active = EXCLUDED.active,
                        last_updated_at = NOW();
                """, (
                    field['external_id'],
                    field['name'],
                    field.get('field_type'),
                    operations,
                    jira_integration_id,
                    tenant_id,
                    field.get('active', True)
                ))
            print(f"      ✅ Inserted/updated {len(custom_fields_data.get('custom_fields', []))} custom fields")

            # 3. Insert custom_fields_projects relationships (junction table)
            # Note: This is a simple junction table with only custom_field_id and project_id (no tenant_id, no timestamps)
            print("   📋 Inserting custom field-project relationships...")
            for relationship in custom_fields_data.get('custom_fields_projects', []):
                # Get custom_field_id and project_id from external_id and key
                cursor.execute("""
                    INSERT INTO custom_fields_projects (custom_field_id, project_id)
                    SELECT cf.id, p.id
                    FROM custom_fields cf
                    JOIN projects p ON p.key = %s AND p.tenant_id = %s AND p.integration_id = %s
                    WHERE cf.external_id = %s AND cf.tenant_id = %s AND cf.integration_id = %s
                    ON CONFLICT (custom_field_id, project_id) DO NOTHING;
                """, (
                    relationship['project_key'],
                    tenant_id,
                    jira_integration_id,
                    relationship['custom_field_external_id'],
                    tenant_id,
                    jira_integration_id
                ))
            print(f"      ✅ Inserted {len(custom_fields_data.get('custom_fields_projects', []))} custom field-project relationships")

            # 4. Insert custom_fields_mappings (look up IDs from external_ids)
            print("   📋 Inserting custom fields mappings...")
            for mapping in custom_fields_data.get('custom_fields_mappings', []):
                # Helper function to get custom field ID from external_id
                def get_field_id(external_id_key):
                    external_id = mapping.get(external_id_key)
                    if not external_id:
                        return None
                    cursor.execute("""
                        SELECT id FROM custom_fields
                        WHERE external_id = %s AND tenant_id = %s AND integration_id = %s
                    """, (external_id, tenant_id, jira_integration_id))
                    result = cursor.fetchone()
                    return result['id'] if result else None  # Access by column name for RealDictCursor

                # Look up IDs for all fields
                field_mappings = {
                    'team_field_id': get_field_id('team_field_external_id'),
                    'sprints_field_id': get_field_id('sprints_field_external_id'),
                    'development_field_id': get_field_id('development_field_external_id'),
                    'story_points_field_id': get_field_id('story_points_field_external_id'),
                    'acceptance_criteria_field_id': get_field_id('acceptance_criteria_field_external_id'),
                    'custom_field_01_id': get_field_id('custom_field_01_external_id'),
                    'custom_field_02_id': get_field_id('custom_field_02_external_id'),
                    'custom_field_03_id': get_field_id('custom_field_03_external_id'),
                    'custom_field_04_id': get_field_id('custom_field_04_external_id'),
                    'custom_field_05_id': get_field_id('custom_field_05_external_id'),
                    'custom_field_06_id': get_field_id('custom_field_06_external_id'),
                    'custom_field_07_id': get_field_id('custom_field_07_external_id'),
                    'custom_field_08_id': get_field_id('custom_field_08_external_id'),
                    'custom_field_09_id': get_field_id('custom_field_09_external_id'),
                    'custom_field_10_id': get_field_id('custom_field_10_external_id'),
                    'custom_field_11_id': get_field_id('custom_field_11_external_id'),
                    'custom_field_12_id': get_field_id('custom_field_12_external_id'),
                    'custom_field_13_id': get_field_id('custom_field_13_external_id'),
                    'custom_field_14_id': get_field_id('custom_field_14_external_id'),
                    'custom_field_15_id': get_field_id('custom_field_15_external_id'),
                    'custom_field_16_id': get_field_id('custom_field_16_external_id'),
                    'custom_field_17_id': get_field_id('custom_field_17_external_id'),
                    'custom_field_18_id': get_field_id('custom_field_18_external_id'),
                    'custom_field_19_id': get_field_id('custom_field_19_external_id'),
                    'custom_field_20_id': get_field_id('custom_field_20_external_id')
                }

                # Build the INSERT statement dynamically based on available fields
                field_names = ['integration_id', 'tenant_id', 'active', 'created_at', 'last_updated_at']
                field_values = [jira_integration_id, tenant_id, mapping.get('active', True)]
                placeholders = ['%s', '%s', '%s', 'NOW()', 'NOW()']

                # Add all custom field mappings that have values
                for field_name, field_id in field_mappings.items():
                    if field_id is not None:
                        field_names.append(field_name)
                        field_values.append(field_id)
                        placeholders.append('%s')

                # Build and execute the query
                query = f"""
                    INSERT INTO custom_fields_mappings ({', '.join(field_names)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (integration_id, tenant_id) DO UPDATE SET
                        {', '.join([f"{fn} = EXCLUDED.{fn}" for fn in field_names if fn not in ['integration_id', 'tenant_id', 'created_at', 'last_updated_at']])},
                        last_updated_at = NOW();
                """

                cursor.execute(query, field_values)
            print(f"      ✅ Inserted/updated {len(custom_fields_data.get('custom_fields_mappings', []))} custom fields mappings")

            print("   ✅ Custom fields seed data loaded successfully")
        else:
            print(f"   ⚠️  Skipping custom fields seed data (file not found, empty, or invalid)")
            print(f"   💡 To seed custom fields data:")
            print(f"      1. Run: python services/backend/scripts/extract_custom_fields_seed_data.py")
            print(f"      2. Re-run this migration")

        # ====================================================================
        # SEED MAPPING TABLES DATA (from JSON file)
        # ====================================================================
        print("\n📋 Loading mapping tables seed data from JSON...")

        # Load JSON file
        mappings_json_file_path = os.path.join(os.path.dirname(__file__), '0002_initial_seed_data_wex_mappings.json')

        # Check if file exists and is not empty
        mappings_data = None
        if os.path.exists(mappings_json_file_path):
            try:
                with open(mappings_json_file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:  # Check if file is not empty
                        mappings_data = json.loads(content)
                    else:
                        print(f"   ⚠️  JSON file is empty: {mappings_json_file_path}")
            except json.JSONDecodeError as e:
                print(f"   ⚠️  JSON file is invalid: {e}")
        else:
            print(f"   ⚠️  JSON file not found: {mappings_json_file_path}")

        # Only proceed if we have valid data with non-empty arrays
        if mappings_data and (
            mappings_data.get('workflows') or
            mappings_data.get('workflow_steps') or
            mappings_data.get('statuses_categories') or
            mappings_data.get('statuses_mappings') or
            mappings_data.get('wits_hierarchies') or
            mappings_data.get('wits_mappings')
        ):
            print(f"   ✅ Loaded JSON file: {mappings_json_file_path}")
            print(f"   📊 Data summary:")
            print(f"      - Workflows: {len(mappings_data.get('workflows', []))}")
            print(f"      - Workflow Steps: {len(mappings_data.get('workflow_steps', []))}")
            print(f"      - Status Categories: {len(mappings_data.get('statuses_categories', []))}")
            print(f"      - Status Mappings: {len(mappings_data.get('statuses_mappings', []))}")
            print(f"      - WIT Hierarchies: {len(mappings_data.get('wits_hierarchies', []))}")
            print(f"      - WIT Mappings: {len(mappings_data.get('wits_mappings', []))}")

            # 1. Insert wits_hierarchies (needed for wits_mappings FK)
            print("   📋 Inserting WIT hierarchies...")
            for hierarchy in mappings_data.get('wits_hierarchies', []):
                # Resolve integration_id from integration_name
                hierarchy_integration_id = None
                if hierarchy.get('integration_name'):
                    cursor.execute("""
                        SELECT id FROM integrations
                        WHERE provider = %s AND tenant_id = %s
                    """, (hierarchy['integration_name'], tenant_id))
                    integration_result = cursor.fetchone()
                    if integration_result:
                        hierarchy_integration_id = integration_result['id']  # Access by column name for RealDictCursor

                cursor.execute("""
                    INSERT INTO wits_hierarchies (name, level, description, integration_id, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (level, tenant_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        integration_id = EXCLUDED.integration_id,
                        active = EXCLUDED.active,
                        last_updated_at = NOW();
                """, (
                    hierarchy['name'],
                    hierarchy['level'],
                    hierarchy.get('description'),
                    hierarchy_integration_id,
                    tenant_id,
                    hierarchy.get('active', True)
                ))
            print(f"      ✅ Inserted/updated {len(mappings_data.get('wits_hierarchies', []))} WIT hierarchies")

            # 2. Insert statuses_categories (needed for statuses_mappings FK)
            print("   📋 Inserting status categories...")
            for category in mappings_data.get('statuses_categories', []):
                # Resolve integration_id from integration_name
                category_integration_id = None
                if category.get('integration_name'):
                    cursor.execute("""
                        SELECT id FROM integrations
                        WHERE provider = %s AND tenant_id = %s
                    """, (category['integration_name'], tenant_id))
                    integration_result = cursor.fetchone()
                    if integration_result:
                        category_integration_id = integration_result['id']

                cursor.execute("""
                    INSERT INTO statuses_categories (name, description, is_waiting, is_done, integration_id, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (name, tenant_id) DO UPDATE SET
                        description = EXCLUDED.description,
                        is_waiting = EXCLUDED.is_waiting,
                        is_done = EXCLUDED.is_done,
                        integration_id = EXCLUDED.integration_id,
                        active = EXCLUDED.active,
                        last_updated_at = NOW();
                """, (
                    category['name'],
                    category.get('description'),
                    category.get('is_waiting', False),
                    category.get('is_done', False),
                    category_integration_id,
                    tenant_id,
                    category.get('active', True)
                ))
            print(f"      ✅ Inserted/updated {len(mappings_data.get('statuses_categories', []))} status categories")

            # 3. Insert workflows (needed for workflow_steps FK)
            print("   📋 Inserting workflows...")
            for workflow in mappings_data.get('workflows', []):
                cursor.execute("""
                    INSERT INTO workflows (name, integration_id, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                    RETURNING id;
                """, (
                    workflow['name'],
                    jira_integration_id,
                    tenant_id,
                    workflow.get('active', True)
                ))
            print(f"      ✅ Inserted {len(mappings_data.get('workflows', []))} workflows")

            # 4. Insert statuses_mappings
            print("   📋 Inserting status mappings...")
            for mapping in mappings_data.get('statuses_mappings', []):
                # Get status_category_id from category_name
                cursor.execute("""
                    SELECT id FROM statuses_categories
                    WHERE name = %s AND tenant_id = %s
                """, (mapping['category_name'], tenant_id))
                category_result = cursor.fetchone()

                if category_result:
                    cursor.execute("""
                        INSERT INTO statuses_mappings (status_from, status_to, status_category_id, integration_id, tenant_id, active, created_at, last_updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (status_from, integration_id, tenant_id) DO UPDATE SET
                            status_to = EXCLUDED.status_to,
                            status_category_id = EXCLUDED.status_category_id,
                            active = EXCLUDED.active,
                            last_updated_at = NOW();
                    """, (
                        mapping['status_from'],
                        mapping['status_to'],
                        category_result['id'],
                        jira_integration_id,
                        tenant_id,
                        mapping.get('active', True)
                    ))
            print(f"      ✅ Inserted/updated {len(mappings_data.get('statuses_mappings', []))} status mappings")

            # 5. Insert workflow_steps (depends on workflows and statuses)
            print("   📋 Inserting workflow steps...")
            for step in mappings_data.get('workflow_steps', []):
                # Get workflow_id from workflow_name
                cursor.execute("""
                    SELECT id FROM workflows
                    WHERE name = %s AND tenant_id = %s AND integration_id = %s
                """, (step['workflow_name'], tenant_id, jira_integration_id))
                workflow_result = cursor.fetchone()

                # Get status_id from status_name (if provided)
                status_id = None
                if step.get('status_name'):
                    cursor.execute("""
                        SELECT id FROM statuses
                        WHERE name = %s AND tenant_id = %s AND integration_id = %s
                    """, (step['status_name'], tenant_id, jira_integration_id))
                    status_result = cursor.fetchone()
                    if status_result:
                        status_id = status_result['id']

                if workflow_result:
                    cursor.execute("""
                        INSERT INTO workflows_steps (workflow_id, name, "order", status_id, is_commitment_point, integration_id, tenant_id, active, created_at, last_updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT DO NOTHING;
                    """, (
                        workflow_result['id'],
                        step['step_name'],
                        step.get('order'),
                        status_id,
                        step.get('is_commitment_point', False),
                        jira_integration_id,
                        tenant_id,
                        step.get('active', True)
                    ))
            print(f"      ✅ Inserted {len(mappings_data.get('workflow_steps', []))} workflow steps")

            # 6. Insert wits_mappings
            print("   📋 Inserting WIT mappings...")
            for mapping in mappings_data.get('wits_mappings', []):
                # Get wits_hierarchy_id from hierarchy_level
                cursor.execute("""
                    SELECT id FROM wits_hierarchies
                    WHERE level = %s AND tenant_id = %s
                """, (mapping['hierarchy_level'], tenant_id))
                hierarchy_result = cursor.fetchone()

                if hierarchy_result:
                    cursor.execute("""
                        INSERT INTO wits_mappings (wit_from, wit_to, wits_hierarchy_id, integration_id, tenant_id, active, created_at, last_updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (wit_from, integration_id, tenant_id) DO UPDATE SET
                            wit_to = EXCLUDED.wit_to,
                            wits_hierarchy_id = EXCLUDED.wits_hierarchy_id,
                            active = EXCLUDED.active,
                            last_updated_at = NOW();
                    """, (
                        mapping['wit_from'],
                        mapping['wit_to'],
                        hierarchy_result['id'],
                        jira_integration_id,
                        tenant_id,
                        mapping.get('active', True)
                    ))
            print(f"      ✅ Inserted/updated {len(mappings_data.get('wits_mappings', []))} WIT mappings")

            print("   ✅ Mapping tables seed data loaded successfully")
        else:
            print(f"   ⚠️  Skipping mapping tables seed data (file not found, empty, or invalid)")
            print(f"   💡 To seed mapping tables data:")
            print(f"      1. Run: python services/backend/scripts/extract_custom_fields_seed_data.py")
            print(f"      2. Re-run this migration")

        # ====================================================================
        # SEED ETL JOBS (from migration 0005)
        # ====================================================================
        print("\n📋 Seeding ETL jobs for autonomous architecture...")

        # Get integration IDs for this tenant
        integrations = {
            'Jira': jira_integration_id,
            'GitHub': github_integration_id,
            'WEX Fabric': fabric_integration_id,
            'WEX AD': ad_integration_id
        }

        # Define jobs with their configurations
        jobs_config = [
            {
                "job_name": "Jira",
                "integration_id": integrations.get('Jira'),
                "schedule_interval_minutes": 60,  # 1 hour
                "status": {
                    "overall": "READY",
                    "token": None,  # 🔑 Execution token - generated when job starts running
                    "reset_deadline": None,  # 🔑 System-level reset countdown deadline
                    "reset_attempt": 0,  # 🔑 Reset attempt counter for exponential backoff
                    "steps": {
                        "jira_issues_with_changelogs": {
                            "order": 1,
                            "display_name": "Issues & Changelogs",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "jira_dev_status": {
                            "order": 2,
                            "display_name": "Development Status",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "jira_sprint_reports": {
                            "order": 3,
                            "display_name": "Sprint Reports",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        }
                    }
                },
                "active": True
            },
            {
                "job_name": "GitHub",
                "integration_id": integrations.get('GitHub'),
                "schedule_interval_minutes": 60,  # 1 hour
                "status": {
                    "overall": "READY",
                    "token": None,  # 🔑 Execution token - generated when job starts running
                    "reset_deadline": None,  # 🔑 System-level reset countdown deadline
                    "reset_attempt": 0,  # 🔑 Reset attempt counter for exponential backoff
                    "steps": {
                        "github_repositories": {
                            "order": 1,
                            "display_name": "Repositories",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "github_prs_commits_reviews_comments": {
                            "order": 2,
                            "display_name": "PRs, Commits, Reviews & Comments",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        }
                    }
                },
                "active": False  # Inactive by default - user must activate
            },
            {
                "job_name": "WEX Fabric",
                "integration_id": integrations.get('WEX Fabric'),
                "schedule_interval_minutes": 1440,  # 24 hours
                "status": {
                    "overall": "READY",
                    "token": None,  # 🔑 Execution token - generated when job starts running
                    "reset_deadline": None,  # 🔑 System-level reset countdown deadline
                    "reset_attempt": 0,  # 🔑 Reset attempt counter for exponential backoff
                    "steps": {
                        "wex_fabric_data": {
                            "order": 1,
                            "display_name": "Fabric Data",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        }
                    }
                },
                "active": False  # Inactive by default (not implemented yet)
            },
            {
                "job_name": "WEX AD",
                "integration_id": integrations.get('WEX AD'),
                "schedule_interval_minutes": 720,  # 12 hours
                "status": {
                    "overall": "READY",
                    "token": None,  # 🔑 Execution token - generated when job starts running
                    "reset_deadline": None,  # 🔑 System-level reset countdown deadline
                    "reset_attempt": 0,  # 🔑 Reset attempt counter for exponential backoff
                    "steps": {
                        "wex_ad_users": {
                            "order": 1,
                            "display_name": "AD Users",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        }
                    }
                },
                "active": False  # Inactive by default (not implemented yet)
            },
            {
                "job_name": "Config",
                "integration_id": integrations.get('Jira'),  # Uses Jira integration
                "schedule_interval_minutes": 999999,  # Manual run only (effectively never auto-runs)
                "status": {
                    "overall": "READY",
                    "token": None,  # 🔑 Execution token - generated when job starts running
                    "reset_deadline": None,  # 🔑 System-level reset countdown deadline
                    "reset_attempt": 0,  # 🔑 Reset attempt counter for exponential backoff
                    "steps": {
                        "config_projects_and_issue_types": {
                            "order": 1,
                            "display_name": "Projects & Types",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_statuses_and_relations": {
                            "order": 2,
                            "display_name": "Statuses & Relations",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_wit_hierarchies": {
                            "order": 3,
                            "display_name": "WIT Hierarchies",
                            "extraction": "idle",  # No extraction for this step
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_wit_mappings": {
                            "order": 4,
                            "display_name": "WIT Mappings",
                            "extraction": "idle",  # No extraction for this step
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_status_mappings": {
                            "order": 5,
                            "display_name": "Status Mappings",
                            "extraction": "idle",  # No extraction for this step
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_workflows": {
                            "order": 6,
                            "display_name": "Workflows",
                            "extraction": "idle",  # No extraction for this step
                            "transform": "idle",
                            "embedding": "idle"
                        },
                        "config_custom_fields": {
                            "order": 7,
                            "display_name": "Custom Fields",
                            "extraction": "idle",
                            "transform": "idle",
                            "embedding": "idle"
                        }
                    }
                },
                "active": True  # Active but manual run only
            }
            # NOTE: No Vectorization job - now integrated into transform workers
        ]

        # Insert jobs
        for job in jobs_config:
            if job["integration_id"]:  # Only insert if integration exists
                cursor.execute("""
                    INSERT INTO etl_jobs (
                        job_name,
                        status,
                        schedule_interval_minutes,
                        retry_interval_minutes,
                        next_run,
                        integration_id,
                        tenant_id,
                        active,
                        created_at,
                        last_updated_at
                    )
                    VALUES (%s, %s, %s, %s, (NOW() AT TIME ZONE 'America/New_York') + make_interval(mins => %s), %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (job_name, tenant_id) DO NOTHING;
                """, (
                    job["job_name"],
                    json.dumps(job["status"]),  # Convert dict to JSON string
                    job["schedule_interval_minutes"],
                    15,  # retry_interval_minutes (15 min for all jobs)
                    job["schedule_interval_minutes"],  # Use job's specific interval for next_run
                    job["integration_id"],
                    tenant_id,
                    job["active"]
                ))
                print(f"    ✅ {job['job_name']} (interval: {job['schedule_interval_minutes']}min, active: {job['active']})")
            else:
                print(f"    ⚠️  {job['job_name']} - integration not found, skipped")

        print("✅ ETL jobs seeded")

        # 4. Workflows - REMOVED
        # Note: Workflow seed data will be added later after testing
        print("⏭️  Skipping workflows seed data (to be added later)")

        # 5. Status categories - REMOVED
        # Note: Status categories seed data will be added later after testing
        print("⏭️  Skipping status categories seed data (to be added later)")

        # 5b. Status mappings - REMOVED
        # Note: Mapping seed data will be added later after testing
        # Mappings tables (statuses_mappings, wits_mappings) should remain empty for now
        print("⏭️  Skipping status mappings seed data (to be added later)")

        # 5c. Statuses - REMOVED
        # Note: Status seed data will be added later after testing
        print("⏭️  Skipping statuses seed data (to be added later)")

        # 5d. Workflow steps - REMOVED
        # Note: Workflow steps seed data will be added later after testing
        print("⏭️  Skipping workflow steps seed data (to be added later)")

        # 6. WITs hierarchies - REMOVED
        # Note: WITs hierarchies seed data will be added later after testing
        print("⏭️  Skipping WITs hierarchies seed data (to be added later)")

        # 7. WITs mappings - REMOVED
        # Note: Mapping seed data will be added later after testing
        # Mappings tables (statuses_mappings, wits_mappings) should remain empty for now
        print("⏭️  Skipping WITs mappings seed data (to be added later)")

        # 8. Insert system settings
        print("📋 Creating system settings...")
        system_settings_data = [
            # Note: Removed old ETL orchestrator settings - now using autonomous ETL jobs
            {"setting_key": "data_retention_days", "setting_value": "365", "setting_type": "integer", "description": "Number of days to retain data"},
            {"setting_key": "font_contrast_threshold", "setting_value": "0.5", "setting_type": "decimal", "description": "Font contrast threshold for color calculations"},
            {"setting_key": "contrast_ratio_normal", "setting_value": "4.5", "setting_type": "decimal", "description": "WCAG contrast ratio for normal text (AA: 4.5, AAA: 7.0)"},
            {"setting_key": "contrast_ratio_large", "setting_value": "3.0", "setting_type": "decimal", "description": "WCAG contrast ratio for large text (AA: 3.0, AAA: 4.5)"}
        ]

        for setting in system_settings_data:
            cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, setting_type, description, tenant_id, active, created_at, last_updated_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (setting_key, tenant_id) DO NOTHING;
            """, (setting["setting_key"], setting["setting_value"], setting["setting_type"], setting["description"], tenant_id))

        print("✅ System settings created")

        # 9. Insert default users
        print("📋 Creating default users...")

        # Import bcrypt for password hashing
        import bcrypt

        def hash_password(password):
            """Hash password using bcrypt (same as auth service)."""
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

        # User passwords
        admin_password = 'Gus@2026!'
        default_password = 'pulse'

        default_users_data = [
            {
                "email": "gustavo.quinelato@wexinc.com",
                "password_hash": hash_password(admin_password),
                "first_name": "Gustavo",
                "last_name": "Quinelato",
                "role": "admin",
                "is_admin": True,
                "auth_provider": "local"
            },
            {
                "email": "admin@pulse.com",
                "password_hash": hash_password(admin_password),
                "first_name": "System",
                "last_name": "Administrator",
                "role": "admin",
                "is_admin": True,
                "auth_provider": "local"
            },
            {
                "email": "user@pulse.com",
                "password_hash": hash_password(default_password),
                "first_name": "Test",
                "last_name": "User",
                "role": "user",
                "is_admin": False,
                "auth_provider": "local"
            },
            {
                "email": "viewer@pulse.com",
                "password_hash": hash_password("pulse"),
                "first_name": "Test",
                "last_name": "Viewer",
                "role": "viewer",
                "is_admin": False,
                "auth_provider": "local"
            }
        ]

        for user in default_users_data:
            cursor.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, role, is_admin, auth_provider, theme_mode, tenant_id, active, created_at, last_updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (email) DO NOTHING;
            """, (user["email"], user["password_hash"], user["first_name"], user["last_name"], user["role"], user["is_admin"], user["auth_provider"], 'light', tenant_id))

        print("✅ Default users created")

        # Insert default user permissions
        print("📋 Creating default user permissions...")

        # Get user IDs for permission assignment
        cursor.execute("SELECT id, email, role FROM users WHERE tenant_id = %s;", (tenant_id,))
        users = cursor.fetchall()

        for user in users:
            user_id = user['id']
            user_role = user['role']

            # Define permissions based on role
            if user_role == 'admin':
                permissions = [
                    ('all', 'read', True),
                    ('all', 'write', True),
                    ('all', 'delete', True),
                    ('all', 'admin', True)
                ]
            elif user_role == 'user':
                permissions = [
                    ('dashboard', 'read', True),
                    ('reports', 'read', True),
                    ('comments', 'write', True),
                    ('projects', 'read', True)
                ]
            elif user_role == 'view':
                permissions = [
                    ('dashboard', 'read', True),
                    ('reports', 'read', True)
                ]
            else:
                permissions = []

            # Insert permissions for this user
            for resource, action, granted in permissions:
                cursor.execute("""
                    INSERT INTO users_permissions (user_id, resource, action, granted, tenant_id, active, created_at, last_updated_at)
                    VALUES (%s, %s, %s, %s, %s, TRUE, NOW(), NOW())
                    ON CONFLICT DO NOTHING;
                """, (user_id, resource, action, granted, tenant_id))

        print("✅ Default user permissions created")

        # 10. ETL jobs already seeded above with autonomous architecture
        # (Removed old orchestrator-based job schedules)

        # 11. Insert colors for WEX tenant
        print("📋 Creating colors for WEX tenant...")

        # Color calculation functions (inline)
        def _luminance(hex_color):
            """Calculate WCAG relative luminance"""
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

            def _linearize(c):
                return (c/12.92) if c <= 0.03928 else ((c+0.055)/1.055) ** 2.4

            return 0.2126*_linearize(r) + 0.7152*_linearize(g) + 0.0722*_linearize(b)

        def _pick_on_color(hex_color):
            """Use 0.5 threshold for font color selection"""
            luminance = _luminance(hex_color)
            return '#FFFFFF' if luminance < 0.5 else '#000000'

        def _pick_on_gradient(color_a, color_b):
            """Choose best font color for gradient pair"""
            on_a = _pick_on_color(color_a)
            on_b = _pick_on_color(color_b)
            return on_a if on_a == on_b else '#FFFFFF'  # Default to white if different

        def _get_accessible_color(hex_color, accessibility_level='AA'):
            """Create accessibility-enhanced color with improved AAA contrast"""
            if accessibility_level == 'AAA':
                # Use 30% darkening for better visual distinction (from fix_aaa_colors.py)
                hex_color = hex_color.lstrip('#')
                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                r = max(0, int(r * 0.7))  # 30% darker
                g = max(0, int(g * 0.7))
                b = max(0, int(b * 0.7))
                return f"#{r:02x}{g:02x}{b:02x}"
            else:
                return hex_color  # AA level uses original color

        def calculate_color_variants(base_colors):
            """Calculate all color variants"""
            variants = {}

            # On-colors (5 columns)
            for i in range(1, 6):
                variants[f'on_color{i}'] = _pick_on_color(base_colors[f'color{i}'])

            # Gradient on-colors (5 combinations including 5→1)
            gradient_pairs = [
                ('color1', 'color2', 'on_gradient_1_2'),
                ('color2', 'color3', 'on_gradient_2_3'),
                ('color3', 'color4', 'on_gradient_3_4'),
                ('color4', 'color5', 'on_gradient_4_5'),
                ('color5', 'color1', 'on_gradient_5_1')
            ]

            for color_a_key, color_b_key, gradient_key in gradient_pairs:
                variants[gradient_key] = _pick_on_gradient(base_colors[color_a_key], base_colors[color_b_key])

            return variants

        # WEX color definitions
        DEFAULT_COLORS = {
            'light': {'color1': '#2862EB', 'color2': '#763DED', 'color3': '#059669', 'color4': '#0EA5E9', 'color5': '#F59E0B'},
            'dark': {'color1': '#2862EB', 'color2': '#763DED', 'color3': '#059669', 'color4': '#0EA5E9', 'color5': '#F59E0B'}
        }

        WEX_CUSTOM_COLORS = {
            'light': {'color1': '#C8102E', 'color2': '#253746', 'color3': '#00C7B1', 'color4': '#A2DDF8', 'color5': '#FFBF3F'},
            'dark': {'color1': '#C8102E', 'color2': '#253746', 'color3': '#00C7B1', 'color4': '#A2DDF8', 'color5': '#FFBF3F'}
        }

        # Insert 12 rows for WEX: 2 modes × 3 accessibility levels × 2 themes
        for mode in ['default', 'custom']:
            for accessibility_level in ['regular', 'AA', 'AAA']:
                for theme_mode in ['light', 'dark']:

                    # Get base colors for this configuration
                    if mode == 'default':
                        base_colors = DEFAULT_COLORS[theme_mode]
                    else:
                        base_colors = WEX_CUSTOM_COLORS[theme_mode]

                    # Apply accessibility enhancement if needed
                    if accessibility_level != 'regular':
                        enhanced_colors = {}
                        for i in range(1, 6):
                            enhanced_colors[f'color{i}'] = _get_accessible_color(base_colors[f'color{i}'], accessibility_level)
                    else:
                        enhanced_colors = base_colors

                    # Calculate variants
                    calculated_variants = calculate_color_variants(enhanced_colors)

                    # Insert row
                    cursor.execute("""
                        INSERT INTO tenants_colors (
                            color_schema_mode, accessibility_level, theme_mode,
                            color1, color2, color3, color4, color5,
                            on_color1, on_color2, on_color3, on_color4, on_color5,
                            on_gradient_1_2, on_gradient_2_3, on_gradient_3_4, on_gradient_4_5, on_gradient_5_1,
                            tenant_id, active, created_at, last_updated_at
                        ) VALUES (
                            %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, TRUE, NOW(), NOW()
                        ) ON CONFLICT (tenant_id, color_schema_mode, accessibility_level, theme_mode) DO NOTHING;
                    """, (
                        mode, accessibility_level, theme_mode,
                        enhanced_colors['color1'], enhanced_colors['color2'], enhanced_colors['color3'], enhanced_colors['color4'], enhanced_colors['color5'],
                        calculated_variants['on_color1'], calculated_variants['on_color2'], calculated_variants['on_color3'], calculated_variants['on_color4'], calculated_variants['on_color5'],
                        calculated_variants['on_gradient_1_2'], calculated_variants['on_gradient_2_3'], calculated_variants['on_gradient_3_4'], calculated_variants['on_gradient_4_5'], calculated_variants['on_gradient_5_1'],
                        tenant_id
                    ))

        print("✅ Colors created for WEX tenant")
        print("✅ WEX tenant seed data completed successfully")

        # Record this migration as applied
        cursor.execute("""
            INSERT INTO migration_history (version, name, applied_at, status)
            VALUES (%s, %s, NOW(), 'applied')
            ON CONFLICT (version)
            DO UPDATE SET applied_at = NOW(), status = 'applied', rollback_at = NULL;
        """, ('0002', 'Initial Seed Data WEX'))

        connection.commit()
        print(f"SUCCESS: Migration 0002 applied successfully")

    except Exception as e:
        connection.rollback()
        print(f"ERROR: Error applying migration: {e}")
        raise

def rollback(connection):
    """Rollback the migration."""
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        print("🔄 Rolling back Migration 0002: Initial Seed Data")

        # Delete seed data in reverse order of creation, handling foreign key constraints properly
        print("📋 Removing ETL jobs...")
        cursor.execute("DELETE FROM etl_jobs WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing user permissions...")
        cursor.execute("DELETE FROM users_permissions WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing user sessions...")
        cursor.execute("DELETE FROM users_sessions WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing default users...")
        # Only delete users that belong specifically to WEX tenant
        cursor.execute("DELETE FROM users WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing system settings...")
        cursor.execute("DELETE FROM system_settings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Remove data tables in correct dependency order
        print("📋 Removing data that references other tables...")
        # First: Remove leaf tables (no other tables depend on them)
        cursor.execute("DELETE FROM prs_reviews WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM prs_commits WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM prs_comments WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM changelogs WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM work_items_prs_links WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Second: Remove tables that depend on work_items/repositories
        cursor.execute("DELETE FROM prs WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Third: Remove work_items (depends on wits, statuses, projects)
        cursor.execute("DELETE FROM work_items WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Fourth: Remove many-to-many relationship tables
        print("📋 Removing relationship tables...")
        cursor.execute("""
            DELETE FROM projects_wits
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX'))
        """)
        cursor.execute("""
            DELETE FROM projects_statuses
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX'))
        """)
        cursor.execute("""
            DELETE FROM custom_fields_projects
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX'))
        """)

        # Fifth: Remove repositories and projects
        cursor.execute("DELETE FROM repositories WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Sixth: Remove workflows steps (depends on workflows and statuses)
        print("📋 Removing workflows steps...")
        cursor.execute("DELETE FROM workflows_steps WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Seventh: Remove wits_mappings (depends on workflows and wits_hierarchies)
        print("📋 Removing WITs mappings...")
        cursor.execute("DELETE FROM wits_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Eighth: Remove wits and statuses (no longer have dependencies)
        cursor.execute("DELETE FROM wits WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")
        cursor.execute("DELETE FROM statuses WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Ninth: Remove workflows (no longer have dependencies from workflows_steps or wits_mappings)
        print("📋 Removing workflows...")
        cursor.execute("DELETE FROM workflows WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        # Tenth: Remove hierarchies and categories
        print("📋 Removing WITs hierarchies...")
        cursor.execute("DELETE FROM wits_hierarchies WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing status mappings...")
        cursor.execute("DELETE FROM statuses_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing status categories...")
        cursor.execute("DELETE FROM statuses_categories WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing raw extraction data...")
        cursor.execute("DELETE FROM raw_extraction_data WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing custom fields mapping...")
        cursor.execute("DELETE FROM custom_fields_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing custom fields...")
        cursor.execute("DELETE FROM custom_fields WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing qdrant vectors...")
        cursor.execute("DELETE FROM qdrant_vectors WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing all integrations for WEX tenant...")
        cursor.execute("DELETE FROM integrations WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing colors...")
        cursor.execute("DELETE FROM tenants_colors WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'WEX');")

        print("📋 Removing premium queue worker configurations...")
        cursor.execute("DELETE FROM system_settings WHERE setting_key IN ('premium_extraction_workers', 'premium_transform_workers', 'premium_embedding_workers');")

        print("📋 Removing WEX tenant...")
        cursor.execute("DELETE FROM tenants WHERE name = 'WEX';")

        print("📋 Removing DORA data...")
        cursor.execute("DELETE FROM dora_metric_insights WHERE report_year = 2024;")
        cursor.execute("DELETE FROM dora_market_benchmarks WHERE report_year = 2024;")

        print("✅ Seed data removed successfully")

        # Record this migration as rolled back
        cursor.execute("""
            UPDATE migration_history
            SET rollback_at = NOW(), status = 'rolled_back'
            WHERE version = %s;
        """, ('0002',))

        connection.commit()
        print(f"SUCCESS: Migration 0002 rolled back successfully")

    except Exception as e:
        connection.rollback()
        print(f"ERROR: Error rolling back migration: {e}")
        raise

def check_status(connection):
    """Check if this migration has been applied."""
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT version, name, applied_at, rollback_at, status
            FROM migration_history
            WHERE version = %s;
        """, ('0002',))

        result = cursor.fetchone()
        if result:
            status = result['status']
            if status == 'applied':
                print(f"SUCCESS: Migration 0002 is applied ({result['applied_at']})")
            elif status == 'rolled_back':
                print(f"ROLLBACK: Migration 0002 was rolled back ({result['rollback_at']})")
        else:
            print(f"PENDING: Migration 0002 has not been applied")

    except Exception as e:
        print(f"ERROR: Error checking migration status: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migration 0002: Initial Seed Data")
    parser.add_argument("--apply", action="store_true", help="Apply the migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--status", action="store_true", help="Check migration status")

    args = parser.parse_args()

    if not any([args.apply, args.rollback, args.status]):
        parser.print_help()
        sys.exit(1)

    try:
        conn = get_database_connection()

        if args.apply:
            apply(conn)
        elif args.rollback:
            rollback(conn)
        elif args.status:
            check_status(conn)

        conn.close()

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        sys.exit(1)
