"""
Update existing Jira job in database to remove first 2 steps and update to 3-step structure.

This script updates the status JSON for the Jira ETL job to remove the config steps
(projects/types and statuses/relations) which are now handled by the Config job.

New structure:
1. jira_issues_with_changelogs (order: 1)
2. jira_dev_status (order: 2)
3. jira_sprint_reports (order: 3)
"""

import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.database import get_database
from sqlalchemy import text

def update_jira_job_status():
    """Update Jira job status to 3-step structure (remove config steps)."""

    db = get_database()

    try:
        # Get write session
        with db.get_write_session() as session:
            # Get current Jira job
            result = session.execute(text("""
                SELECT id, status
                FROM etl_jobs
                WHERE job_name = 'Jira'
            """)).fetchone()

            if not result:
                print("❌ No Jira job found in database")
                return False

            job_id, current_status = result

            print(f"📋 Found Jira job (ID: {job_id})")
            print(f"Current steps: {list(current_status.get('steps', {}).keys())}")

            # Check if already updated to 3-step structure
            if 'jira_projects_and_issue_types' not in current_status.get('steps', {}):
                print("✅ Jira job already updated to 3-step structure")
                return True

            # Create new steps dict with only the 3 transactional steps
            new_steps = {
                'jira_issues_with_changelogs': {
                    'order': 1,
                    'display_name': 'Issues & Changelogs',
                    'extraction': 'idle',
                    'transform': 'idle',
                    'embedding': 'idle'
                },
                'jira_dev_status': {
                    'order': 2,
                    'display_name': 'Development Status',
                    'extraction': 'idle',
                    'transform': 'idle',
                    'embedding': 'idle'
                },
                'jira_sprint_reports': {
                    'order': 3,
                    'display_name': 'Sprint Reports',
                    'extraction': 'idle',
                    'transform': 'idle',
                    'embedding': 'idle'
                }
            }

            # Update the steps
            current_status['steps'] = new_steps

            # Update the database
            session.execute(text("""
                UPDATE etl_jobs
                SET status = :status
                WHERE id = :job_id
            """), {
                'status': json.dumps(current_status),
                'job_id': job_id
            })

            session.commit()

            print(f"✅ Updated Jira job to 3-step structure")
            print(f"New steps: {list(current_status.get('steps', {}).keys())}")

            return True

    except Exception as e:
        print(f"❌ Error updating Jira job: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_jira_job_status()
    sys.exit(0 if success else 1)

