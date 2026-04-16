"""
Apply auto-mapping to existing custom fields.
This script manually applies the auto-mapping logic to custom fields that were
discovered before the auto-mapping feature was implemented.
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables from root .env file
load_dotenv('.env')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'backend'))

from app.core.database import get_database
from app.models.unified_models import CustomField, CustomFieldMapping
from app.core.utils import DateTimeHelper
from sqlalchemy import text

def apply_auto_mapping(tenant_id: int = 1, integration_id: int = 1):
    """Apply auto-mapping to existing custom fields."""
    print(f"\n{'='*80}")
    print(f"🔧 Applying Auto-Mapping for Tenant {tenant_id}, Integration {integration_id}")
    print(f"{'='*80}\n")
    
    database = get_database()
    
    with database.get_write_session_context() as session:
        # Get or create mapping record
        mapping = session.query(CustomFieldMapping).filter(
            CustomFieldMapping.tenant_id == tenant_id,
            CustomFieldMapping.integration_id == integration_id
        ).first()
        
        if not mapping:
            print("❌ No mapping record found. Creating one...")
            mapping = CustomFieldMapping(
                tenant_id=tenant_id,
                integration_id=integration_id,
                active=True,
                created_at=DateTimeHelper.now_default(),
                last_updated_at=DateTimeHelper.now_default()
            )
            session.add(mapping)
            session.flush()
            print(f"✅ Created mapping record (ID: {mapping.id})\n")
        else:
            print(f"✅ Found existing mapping record (ID: {mapping.id})\n")
        
        # Auto-map custom field columns (custom_field_01 through custom_field_20)
        print("🗺️  Auto-mapping custom field columns...")
        print("-" * 80)
        
        mapped_count = 0
        skipped_count = 0
        missing_count = 0
        
        for i in range(1, 21):
            env_var_name = f"JIRA_CUSTOM_FIELD_{i:02d}_ID"
            custom_field_external_id = os.getenv(env_var_name)
            
            if not custom_field_external_id:
                continue  # Skip empty environment variables
            
            field_attr = f"custom_field_{i:02d}_id"
            current_mapping = getattr(mapping, field_attr, None)
            
            if current_mapping:
                print(f"   ⏭️  CF-{i:02d} already mapped (skipping)")
                skipped_count += 1
                continue
            
            # Look up the field in custom_fields table
            custom_field = session.query(CustomField).filter(
                CustomField.external_id == custom_field_external_id,
                CustomField.tenant_id == tenant_id,
                CustomField.integration_id == integration_id,
                CustomField.active == True
            ).first()
            
            if custom_field:
                setattr(mapping, field_attr, custom_field.id)
                print(f"   ✅ CF-{i:02d} → {custom_field.external_id} ({custom_field.name})")
                mapped_count += 1
            else:
                print(f"   ❌ CF-{i:02d} → {custom_field_external_id} (NOT FOUND IN DATABASE)")
                missing_count += 1
        
        if mapped_count > 0:
            mapping.last_updated_at = DateTimeHelper.now_default()
            session.commit()
            print(f"\n✅ Successfully auto-mapped {mapped_count} custom field columns")
        else:
            print(f"\n⚠️  No new mappings applied")
        
        if skipped_count > 0:
            print(f"⏭️  Skipped {skipped_count} already-mapped fields")
        
        if missing_count > 0:
            print(f"❌ {missing_count} fields not found in database")
            print(f"   💡 These fields may not exist in your Jira instance")
        
        print(f"\n{'='*80}\n")

if __name__ == '__main__':
    apply_auto_mapping()

