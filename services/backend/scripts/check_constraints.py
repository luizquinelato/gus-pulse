#!/usr/bin/env python3
"""
Quick script to check database constraints
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection details
db_host = os.getenv('POSTGRES_HOST', 'localhost')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_user = os.getenv('POSTGRES_USER', 'postgres')
db_password = os.getenv('POSTGRES_PASSWORD', 'pulse')
db_name = os.getenv('POSTGRES_DATABASE', 'pulse_db')

print(f"🔍 Connecting to database: {db_user}@{db_host}:{db_port}/{db_name}")

try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name
    )
    cur = conn.cursor()
    
    print("\n" + "="*80)
    print("CHECKING SPRINTS TABLE CONSTRAINTS")
    print("="*80)
    
    cur.execute("""
        SELECT conname, contype, pg_get_constraintdef(oid) 
        FROM pg_constraint 
        WHERE conrelid = 'sprints'::regclass
        ORDER BY conname;
    """)
    
    sprints_constraints = cur.fetchall()
    if sprints_constraints:
        for row in sprints_constraints:
            print(f"  {row[0]} ({row[1]}): {row[2]}")
    else:
        print("  ❌ NO CONSTRAINTS FOUND ON SPRINTS TABLE!")
    
    print("\n" + "="*80)
    print("CHECKING TENANTS TABLE CONSTRAINTS")
    print("="*80)
    
    cur.execute("""
        SELECT conname, contype, pg_get_constraintdef(oid) 
        FROM pg_constraint 
        WHERE conrelid = 'tenants'::regclass
        ORDER BY conname;
    """)
    
    tenants_constraints = cur.fetchall()
    if tenants_constraints:
        for row in tenants_constraints:
            print(f"  {row[0]} ({row[1]}): {row[2]}")
    else:
        print("  ❌ NO CONSTRAINTS FOUND ON TENANTS TABLE!")
    
    print("\n" + "="*80)
    print("CHECKING MIGRATION HISTORY")
    print("="*80)
    
    cur.execute("""
        SELECT migration_name, applied_at 
        FROM migration_history 
        ORDER BY applied_at DESC 
        LIMIT 10;
    """)
    
    migrations = cur.fetchall()
    if migrations:
        for row in migrations:
            print(f"  {row[1]}: {row[0]}")
    else:
        print("  ❌ NO MIGRATION HISTORY FOUND!")
    
    conn.close()
    print("\n✅ Check complete")
    
except Exception as e:
    print(f"\n❌ Error: {e}")

