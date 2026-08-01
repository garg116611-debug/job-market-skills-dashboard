"""
Creates all project tables in Neon from sql/schema.sql.
Usage:  python create_schema.py
Safe to re-run: uses CREATE TABLE IF NOT EXISTS.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found. Set up .env first.")
    sys.exit(1)

schema_path = os.path.join("sql", "schema.sql")
with open(schema_path, "r") as f:
    schema_sql = f.read()

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(schema_sql)
    conn.commit()
    print("Schema applied. Tables created (or already existed):")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    for row in cur.fetchall():
        print(" -", row[0])

    cur.close()
    conn.close()
except Exception as e:
    print("Failed to apply schema.")
    print("Error:", e)
    sys.exit(1)
