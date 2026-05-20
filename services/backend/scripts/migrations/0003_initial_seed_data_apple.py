#!/usr/bin/env python3
"""
Migration 0003: Initial Seed Data Apple
Description: Inserts initial seed data for Apple tenant including DORA benchmarks, tenants, integrations, workflows, status mappings, users, and system settings (excludes color-related data)
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

        print("🚀 Applying Migration 0003: Initial Seed Data Apple")

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

        # 2. Insert default tenant (Apple) - Premium tier
        print("📋 Creating Apple tenant (Premium tier)...")

        # Check if Apple tenant already exists
        cursor.execute("SELECT id FROM tenants WHERE name = 'Apple' LIMIT 1;")
        existing_tenant = cursor.fetchone()

        if existing_tenant:
            print(f"   ℹ️ Apple tenant already exists (ID: {existing_tenant[0]}), updating tier to premium...")
            cursor.execute("""
                UPDATE tenants
                SET tier = 'premium',
                    website = 'https://www.apple.com',
                    assets_folder = 'apple',
                    logo_filename = 'logo.png',
                    color_schema_mode = 'default',
                    active = TRUE,
                    last_updated_at = NOW()
                WHERE name = 'Apple';
            """)
        else:
            print("   ➕ Creating new Apple tenant...")
            cursor.execute("""
                INSERT INTO tenants (name, website, assets_folder, logo_filename, color_schema_mode, tier, active, created_at, last_updated_at)
                VALUES ('Apple', 'https://www.apple.com', 'apple', 'logo.png', 'default', 'premium', TRUE, NOW(), NOW());
            """)

        # Get the tenant ID for seed data
        cursor.execute("SELECT id FROM tenants WHERE name = 'Apple' LIMIT 1;")
        tenant_result = cursor.fetchone()
        if not tenant_result:
            raise Exception("Failed to create or find Apple tenant")
        tenant_id = tenant_result['id']
        print(f"   ✅ Apple tenant created/found with ID: {tenant_id}")

        # Note: worker_configs table removed - using shared worker pools based on tenant tier
        # Apple is premium tier = 5 workers per pool (extraction, transform, embedding)

        # 3. Create integrations (JIRA and GitHub only)
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
            "jira.svg",
            tenant_id, jira_active
        ))

        jira_result = cursor.fetchone()
        if jira_result:
            jira_integration_id = jira_result['id']
        else:
            cursor.execute("SELECT id FROM integrations WHERE name = 'JIRA' AND tenant_id = %s;", (tenant_id,))
            jira_integration_id = cursor.fetchone()['id']

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
            github_integration_id = cursor.fetchone()['id']

        print(f"   ✅ GitHub integration created (ID: {github_integration_id}, active: {github_active})")

        # Create AI Gateway integration
        print("   📋 Creating AI Gateway integration...")
        ai_gateway_base_url = os.getenv("WEX_AI_GATEWAY_BASE_URL")
        ai_gateway_api_key = os.getenv("WEX_AI_GATEWAY_API_KEY")
        ai_model = os.getenv("AI_MODEL")
        ai_fallback_model = os.getenv("AI_FALLBACK_MODEL")

        # Initialize before conditional so embedding section can always reference them
        encrypted_ai_key = None
        ai_gateway_active = False

        if ai_gateway_base_url and ai_gateway_api_key and ai_model:
            # Encrypt the AI Gateway API key
            encrypted_ai_key = AppConfig.encrypt_token(ai_gateway_api_key, key)
            ai_gateway_active = True
            print("   🔐 AI Gateway API key encrypted successfully")

            # Primary AI Gateway settings
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

            # Create primary AI Gateway integration
            cursor.execute("""
                INSERT INTO integrations (
                    provider, type, username, password, base_url, settings,
                    logo_filename, tenant_id, active, created_at, last_updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (provider, tenant_id) DO NOTHING
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

            print(f"   ✅ AI Gateway integration created (ID: {ai_gateway_integration_id}, model: {ai_model})")

            # Create fallback AI Gateway integration if fallback model is specified
            if ai_fallback_model and ai_fallback_model != ai_model:
                # Fallback AI Gateway settings
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
                    # Update primary integration to point to fallback
                    cursor.execute("""
                        UPDATE integrations SET fallback_integration_id = %s
                        WHERE id = %s;
                    """, (fallback_integration_id, ai_gateway_integration_id))
                    print(f"   ✅ AI Gateway fallback integration created (ID: {fallback_integration_id}, model: {ai_fallback_model})")
        else:
            print("   ⚠️ AI Gateway credentials not found in .env - skipping AI Gateway integration")

        # Create embedding integrations
        print("   📋 Creating embedding integrations...")

        # Free local embedding settings
        local_embedding_settings = {
            "model_path": "models/sentence-transformers/all-mpnet-base-v2",
            "cost_tier": "free",
            "gateway_route": False,
            "source": "local"
        }

        # Free local embedding
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
            "local-embeddings.svg", tenant_id, False  # Set to inactive - using external embeddings as primary
        ))

        local_embedding_result = cursor.fetchone()
        if local_embedding_result:
            local_embedding_id = local_embedding_result['id']
            print(f"   ✅ Local embedding integration created (ID: {local_embedding_id})")

        # Paid external embedding (WEX AI Gateway)
        if ai_gateway_base_url and encrypted_ai_key:
            # Azure embedding settings
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
                ON CONFLICT (provider, tenant_id) DO NOTHING
                RETURNING id;
            """, (
                "Azure 3-small", "Embedding", None, encrypted_ai_key, ai_gateway_base_url, json.dumps(azure_embedding_settings),
                "wex-embeddings.svg", tenant_id, True  # Set to active - external embeddings as primary
            ))

            paid_embedding_result = cursor.fetchone()
            if paid_embedding_result:
                paid_embedding_id = paid_embedding_result['id']
                print(f"   ✅ WEX embedding integration created (ID: {paid_embedding_id})")
        else:
            print("   ⚠️ AI Gateway credentials not found - skipping WEX embedding integration")

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
            cursor.execute("SELECT id FROM integrations WHERE provider = 'wex_fabric' AND tenant_id = %s;", (tenant_id,))
            fabric_integration_id = cursor.fetchone()['id']

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
            cursor.execute("SELECT id FROM integrations WHERE provider = 'active_directory' AND tenant_id = %s;", (tenant_id,))
            ad_integration_id = cursor.fetchone()['id']

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
            internal_integration_id = cursor.fetchone()['id']

        print(f"   ✅ Internal integration created (ID: {internal_integration_id}, active)")

        print("✅ Integrations created")

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
                "active": False  # Inactive by default - user must activate
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
                "active": False  # Inactive by default - user must activate
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

        # Note: Workflows, status mappings, WITs hierarchies, and WITs mappings removed
        # These should be configured by users through the UI based on their specific needs

        # 4. Insert system settings
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

        # Get user passwords from environment variables
        admin_password = os.getenv('ADMIN_USER_PASSWORD', 'pulse')
        default_password = os.getenv('DEFAULT_USER_PASSWORD', 'pulse')

        default_users_data = [
            {
                "email": "admin@apple.com",
                "password_hash": hash_password(admin_password),
                "first_name": "Apple",
                "last_name": "Admin",
                "role": "admin",
                "is_admin": True,
                "auth_provider": "local"
            },
            {
                "email": "user@apple.com",
                "password_hash": hash_password(default_password),
                "first_name": "Apple",
                "last_name": "User",
                "role": "user",
                "is_admin": False,
                "auth_provider": "local"
            },
            {
                "email": "viewer@apple.com",
                "password_hash": hash_password(default_password),
                "first_name": "Apple",
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

        print("✅ Colors created for Apple tenant")
        print("✅ Apple tenant seed data completed successfully")

        # Record this migration as applied
        cursor.execute("""
            INSERT INTO migration_history (version, name, applied_at, status)
            VALUES (%s, %s, NOW(), 'applied')
            ON CONFLICT (version)
            DO UPDATE SET applied_at = NOW(), status = 'applied', rollback_at = NULL;
        """, ('0003', 'Initial Seed Data WEX'))

        connection.commit()
        print(f"SUCCESS: Migration 0003 applied successfully")

    except Exception as e:
        connection.rollback()
        print(f"ERROR: Error applying migration: {e}")
        raise

def rollback(connection):
    """Rollback the migration."""
    cursor = connection.cursor(cursor_factory=RealDictCursor)

    try:
        print("🔄 Rolling back Migration 0003: Initial Seed Data Apple")

        # Delete seed data in reverse order of creation, handling foreign key constraints properly
        print("📋 Removing ETL jobs...")
        cursor.execute("DELETE FROM etl_jobs WHERE tenant_id = (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing user permissions...")
        cursor.execute("DELETE FROM users_permissions WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing user sessions...")
        cursor.execute("DELETE FROM users_sessions WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing default users...")
        # Only delete users that belong specifically to Apple tenant
        cursor.execute("DELETE FROM users WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing system settings...")
        cursor.execute("DELETE FROM system_settings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Remove data tables in correct dependency order
        print("📋 Removing data that references other tables...")
        # First: Remove leaf tables (no other tables depend on them)
        cursor.execute("DELETE FROM prs_reviews WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM prs_commits WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM prs_comments WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM changelogs WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM work_items_prs_links WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Second: Remove tables that depend on work_items/repositories
        cursor.execute("DELETE FROM prs WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Third: Remove work_items (depends on wits, statuses, projects)
        cursor.execute("DELETE FROM work_items WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Fourth: Remove many-to-many relationship tables
        print("📋 Removing relationship tables...")
        cursor.execute("""
            DELETE FROM projects_wits
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple'))
        """)
        cursor.execute("""
            DELETE FROM projects_statuses
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple'))
        """)
        cursor.execute("""
            DELETE FROM custom_fields_projects
            WHERE project_id IN (SELECT id FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple'))
        """)

        # Fifth: Remove repositories and projects
        cursor.execute("DELETE FROM repositories WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM projects WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Sixth: Remove wits and statuses (depend on mappings)
        cursor.execute("DELETE FROM wits WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")
        cursor.execute("DELETE FROM statuses WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        # Note: Mappings are now configured by users through the UI (not seeded in migrations 3+)
        # But we still need to delete any that exist during rollback

        print("📋 Removing custom fields mappings...")
        cursor.execute("DELETE FROM custom_fields_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing custom fields...")
        cursor.execute("DELETE FROM custom_fields WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing wits_mappings (references workflows and hierarchies - must be deleted first)...")
        cursor.execute("DELETE FROM wits_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing wits_hierarchies...")
        cursor.execute("DELETE FROM wits_hierarchies WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing workflows steps (must be deleted before workflows)...")
        cursor.execute("DELETE FROM workflows_steps WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing workflows (must be deleted before integrations)...")
        cursor.execute("DELETE FROM workflows WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing statuses_mappings...")
        cursor.execute("DELETE FROM statuses_mappings WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing all integrations for Apple tenant...")
        cursor.execute("DELETE FROM integrations WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing colors...")
        cursor.execute("DELETE FROM tenants_colors WHERE tenant_id IN (SELECT id FROM tenants WHERE name = 'Apple');")

        print("📋 Removing Apple tenant...")
        cursor.execute("DELETE FROM tenants WHERE name = 'Apple';")

        print("📋 Removing DORA data...")
        cursor.execute("DELETE FROM dora_metric_insights WHERE report_year = 2024;")
        cursor.execute("DELETE FROM dora_market_benchmarks WHERE report_year = 2024;")

        print("✅ Seed data removed successfully")

        # Record this migration as rolled back
        cursor.execute("""
            UPDATE migration_history
            SET rollback_at = NOW(), status = 'rolled_back'
            WHERE version = %s;
        """, ('0003',))

        connection.commit()
        print(f"SUCCESS: Migration 0003 rolled back successfully")

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
        """, ('0003',))

        result = cursor.fetchone()
        if result:
            status = result['status']
            if status == 'applied':
                print(f"SUCCESS: Migration 0003 is applied ({result['applied_at']})")
            elif status == 'rolled_back':
                print(f"ROLLBACK: Migration 0003 was rolled back ({result['rollback_at']})")
        else:
            print(f"PENDING: Migration 0003 has not been applied")

    except Exception as e:
        print(f"ERROR: Error checking migration status: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migration 0003: Initial Seed Data")
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
