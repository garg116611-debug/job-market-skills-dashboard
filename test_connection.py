"""
Run this first to confirm VS Code can talk to your NEW Neon project.
Usage:  python test_connection.py
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # reads .env in this folder

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found. Did you create a .env file (copied from .env.example)?")
    sys.exit(1)

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print("Connected successfully to Neon.")
    print("Postgres version:", version)
    cur.close()
    conn.close()
except Exception as e:
    print("Connection FAILED.")
    print("Error:", e)
    sys.exit(1)
