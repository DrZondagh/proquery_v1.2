# tools/dump_all_databases.py
import os
import json
import boto3
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# === POSTGRES ===
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# === S3 ===
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# ───── POSTGRES ─────
print("=" * 80)
print("POSTGRES DUMP")
print("=" * 80)

conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
cur = conn.cursor()

# Companies
cur.execute("SELECT id, name, config FROM public.companies")
print("\nCOMPANIES:")
for row in cur.fetchall():
    phones = json.loads(row[2]).get("phones", []) if isinstance(row[2], str) else row[2].get("phones", [])
    print(f"\nID {row[0]} → {row[1]}")
    for p in phones:
        print(f"  • {p.get('phone')} → {p.get('role', 'staff').upper()}")

# SOP count
cur.execute("SELECT company_id, COUNT(*) FROM public.sops GROUP BY company_id")
print("\nSOPs per company:")
for row in cur.fetchall():
    print(f"  Company {row[0]} → {row[1]} SOPs")

cur.close()
conn.close()

# ───── S3 ─────
print("\n" + "=" * 80)
print(f"S3 BUCKET: {S3_BUCKET_NAME}")
print("=" * 80)

s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID,
                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=AWS_REGION)

paginator = s3.get_paginator('list_objects_v2')
folders = set()
pdfs = []

for page in paginator.paginate(Bucket=S3_BUCKET_NAME):
    for prefix in page.get('CommonPrefixes', []):
        folders.add(prefix['Prefix'].rstrip('/'))
    for obj in page.get('Contents', []):
        if obj['Key'].endswith('.pdf'):
            size_mb = obj['Size'] / (1024 * 1024)
            pdfs.append((obj['Key'], size_mb))

print(f"Folders ({len(folders)}):")
for f in sorted(folders):
    print(f"  📁 {f}")

print(f"\nPDFs ({len(pdfs)}):")
for key, size in sorted(pdfs):
    print(f"  📄 {key} ({size:.2f} MB)")

print("\n" + "=" * 80)
print("ALL DONE — Postgres + S3 dumped!")
print("=" * 80)