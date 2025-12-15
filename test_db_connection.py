#!/usr/bin/env python3
"""Test database connection and permissions."""

import psycopg2
import os

# Database credentials (same as in .env)
DB_HOST = 'localhost'
DB_PORT = '5432'
DB_USER = 'postgres'
DB_PASSWORD = 'devpass'
DB_NAME = 'customer_db'

print("Testing PostgreSQL Connection and Permissions...")
print(f"Connecting to: {DB_NAME} as {DB_USER}@{DB_HOST}:{DB_PORT}")

try:
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASSWORD,
        dbname=DB_NAME
    )
    conn.autocommit = True
    print("✓ Connection successful!")
    
    # Test table creation
    cur = conn.cursor()
    print("\nTesting table creation...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS test_permissions_check (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Table created successfully!")
    
    # Test insert
    print("\nTesting data insertion...")
    cur.execute("INSERT INTO test_permissions_check (name) VALUES ('test_record')")
    print("✓ Data inserted successfully!")
    
    # Test select
    print("\nTesting data retrieval...")
    cur.execute("SELECT * FROM test_permissions_check")
    rows = cur.fetchall()
    print(f"✓ Retrieved {len(rows)} row(s)")
    
    # Cleanup
    print("\nCleaning up...")
    cur.execute("DROP TABLE test_permissions_check")
    print("✓ Test table dropped")
    
    # Check CSV file
    print("\n" + "="*50)
    print("Checking CSV file...")
    csv_path = os.path.abspath('customer_data.csv')
    if os.path.exists(csv_path):
        print(f"✓ CSV file found at: {csv_path}")
        with open(csv_path, 'r') as f:
            lines = f.readlines()
            print(f"✓ CSV has {len(lines)} lines (including header)")
            print(f"✓ Header: {lines[0].strip()}")
    else:
        print(f"✗ CSV file NOT found at: {csv_path}")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ ALL TESTS PASSED!")
    print("Your database is ready for code generation!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()
