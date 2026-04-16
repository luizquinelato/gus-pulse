"""
Check custom field mappings to verify auto-mapping is working.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'backend'))

from app.core.database import get_database
from app.models.unified_models import CustomField, CustomFieldMapping
from sqlalchemy import text

def check_custom_fields_and_mappings(tenant_id: int = 1, integration_id: int = 1):
    """Check custom fields discovered and their mappings."""
    print(f"\n{'='*80}")
    print(f"🔍 Checking Custom Fields and Mappings for Tenant {tenant_id}, Integration {integration_id}")
    print(f"{'='*80}\n")
    
    database = get_database()
    
    with database.get_read_session_context() as session:
        # Check custom fields
        print("📋 Custom Fields Discovered:")
        print("-" * 80)
        
        custom_fields = session.query(CustomField).filter(
            CustomField.tenant_id == tenant_id,
            CustomField.integration_id == integration_id,
            CustomField.active == True
        ).order_by(CustomField.external_id).all()
        
        if not custom_fields:
            print("   ❌ No custom fields found!")
            print("   💡 Run 'Discover Custom Fields' job first")
            return
        
        print(f"   ✅ Found {len(custom_fields)} custom fields\n")
        
        # Show fields we're looking for
        target_fields = {
            'customfield_10001': 'Team Field',
            'customfield_10000': 'Development Field',
            'customfield_10021': 'Sprints Field',
            'customfield_10024': 'Story Points Field',
            'customfield_10128': 'Agile Team (CF-01)',
            'customfield_10501': 'QP Planning Sessions (CF-02)',
            'customfield_10318': 'QP Commitment Type (CF-03)',
            'customfield_10412': 'WEX T-Shirt Size (CF-04)',
            'customfield_10414': 'Project Code (CF-05)',
            'customfield_10251': 'Expense Type (CF-06)',
            'customfield_12007': 'Business Area (CF-07)',
            'customfield_13779': 'Funding (CF-08)',
            'customfield_12044': 'KTLO Type (CF-09)',
            'customfield_10253': 'Investment Category (CF-10)',
            'customfield_13780': 'CPP ID (CF-11)',
        }
        
        found_fields = {}
        for cf in custom_fields:
            if cf.external_id in target_fields:
                found_fields[cf.external_id] = cf
                print(f"   ✅ {cf.external_id:20s} - {cf.name:40s} (ID: {cf.id})")
        
        missing_fields = set(target_fields.keys()) - set(found_fields.keys())
        if missing_fields:
            print(f"\n   ⚠️  Missing {len(missing_fields)} expected fields:")
            for field_id in missing_fields:
                print(f"      ❌ {field_id} - {target_fields[field_id]}")
        
        # Check mappings
        print(f"\n{'='*80}")
        print("🗺️  Custom Field Mappings:")
        print("-" * 80)
        
        mapping = session.query(CustomFieldMapping).filter(
            CustomFieldMapping.tenant_id == tenant_id,
            CustomFieldMapping.integration_id == integration_id,
            CustomFieldMapping.active == True
        ).first()
        
        if not mapping:
            print("   ❌ No custom field mapping record found!")
            print("   💡 Auto-mapping should have created this during discovery")
            return
        
        print(f"   ✅ Mapping record found (ID: {mapping.id})\n")
        
        # Check special fields
        print("   Special Fields:")
        special_fields = [
            ('team_field_id', 'Team Field', 'customfield_10001'),
            ('development_field_id', 'Development Field', 'customfield_10000'),
            ('sprints_field_id', 'Sprints Field', 'customfield_10021'),
            ('story_points_field_id', 'Story Points Field', 'customfield_10024'),
        ]
        
        for field_attr, field_name, expected_external_id in special_fields:
            field_id = getattr(mapping, field_attr, None)
            if field_id:
                cf = session.query(CustomField).filter(CustomField.id == field_id).first()
                if cf:
                    status = "✅" if cf.external_id == expected_external_id else "⚠️"
                    print(f"      {status} {field_name:25s} → {cf.external_id} ({cf.name})")
                else:
                    print(f"      ❌ {field_name:25s} → ID {field_id} (NOT FOUND)")
            else:
                print(f"      ❌ {field_name:25s} → NOT MAPPED")
        
        # Check custom field columns
        print("\n   Custom Field Columns:")
        mapped_count = 0
        for i in range(1, 21):
            field_attr = f"custom_field_{i:02d}_id"
            field_id = getattr(mapping, field_attr, None)
            if field_id:
                cf = session.query(CustomField).filter(CustomField.id == field_id).first()
                if cf:
                    print(f"      ✅ CF-{i:02d} → {cf.external_id} ({cf.name})")
                    mapped_count += 1
                else:
                    print(f"      ❌ CF-{i:02d} → ID {field_id} (NOT FOUND)")
        
        if mapped_count == 0:
            print(f"      ❌ No custom field columns mapped!")
            print(f"      💡 Expected 11 fields to be auto-mapped")
        else:
            print(f"\n   📊 Total custom field columns mapped: {mapped_count}/20")
            if mapped_count < 11:
                print(f"   ⚠️  Expected 11 fields to be auto-mapped, only {mapped_count} found")
        
        print(f"\n{'='*80}\n")

if __name__ == '__main__':
    check_custom_fields_and_mappings()

