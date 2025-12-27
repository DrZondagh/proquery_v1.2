import os
import json
import boto3
from dotenv import load_dotenv
import psycopg2
from datetime import datetime, date, time
from src.core.config import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

# Load environment variables
load_dotenv()

# AWS S3 config
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


def connect_to_s3():
    try:
        return boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
    except Exception as e:
        print(f"Error connecting to S3: {e}")
        return None


def connect_to_postgres():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        print(f"Error connecting to Postgres: {e}")
        return None


def get_company_name(conn, company_id):
    if not conn:
        return "Unknown"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT name FROM companies WHERE id = %s;", (int(company_id),))
            row = cursor.fetchone()
            return row[0] if row else "Unknown"
    except Exception:
        return "Unknown"


def get_user_name(conn, user_id, company_id):
    if not conn:
        return "Unknown"
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT full_name FROM users WHERE id = %s AND company_id = %s;",
                           (int(user_id), int(company_id)))
            row = cursor.fetchone()
            return row[0] if row else "Unknown"
    except Exception:
        return "Unknown"


def get_s3_structure(s3_client, db_conn, prefix='', depth=0, max_depth=5, max_examples=3, structure=None):
    if structure is None:
        structure = {"subfolders": [], "files": [], "children": {}}
    if depth > max_depth:
        structure["note"] = f"Depth limit reached (max={max_depth}); substructure truncated."
        return structure
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix, Delimiter='/')
        sub_prefixes = []
        objects = []
        for page in page_iterator:
            if 'CommonPrefixes' in page:
                sub_prefixes.extend([p['Prefix'] for p in page['CommonPrefixes']])
            if 'Contents' in page:
                objects.extend([obj['Key'] for obj in page['Contents'] if obj['Key'] != prefix])

        parts = prefix.strip('/').split('/')
        label = prefix or '/'
        if len(parts) > 0 and parts[0].isdigit():
            company_id = parts[0]
            company_name = get_company_name(db_conn, company_id)
            label += f" (Company: {company_name})"
        if len(parts) > 3 and parts[1] == 'personal' and parts[2] == 'employees' and parts[3].isdigit():
            user_id = parts[3]
            user_name = get_user_name(db_conn, user_id, company_id)
            label += f" (User: {user_name})"

        structure["label"] = label
        structure["subfolders"] = [p.strip('/') for p in sub_prefixes]
        if objects:
            examples = objects[:max_examples]
            if len(objects) > max_examples:
                examples.append(f"... ({len(objects) - max_examples} more)")
            structure["files"] = examples

        for sub_prefix in sub_prefixes:
            child_structure = {}
            get_s3_structure(s3_client, db_conn, sub_prefix, depth + 1, max_depth, max_examples, child_structure)
            structure["children"][sub_prefix.strip('/')] = child_structure
    except Exception as e:
        print(f"Error exploring prefix '{prefix}': {e}")
    return structure


def get_table_list(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []


def get_table_structure(conn, table_name):
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public';",
                (table_name,))
            return [{"column": col[0], "type": col[1], "nullable": col[2], "default": col[3]} for col in
                    cursor.fetchall()]
    except Exception:
        return []


def get_row_count(conn, table_name):
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            return cursor.fetchone()[0]
    except Exception:
        return 0


def convert_to_serializable(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def get_sample_data(conn, table_name, sample_rows=3):
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT {sample_rows};")
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            return [{k: convert_to_serializable(v) for k, v in zip(column_names, row)} for row in rows]
    except Exception:
        return []


def dump_to_json(max_examples=3, include_sample_data=True, sample_rows=3, max_depth=5):
    s3_client = connect_to_s3()
    db_conn = connect_to_postgres()
    output = {"postgres": {"tables": {}}, "s3": {"bucket": S3_BUCKET_NAME, "structure": {}}}

    if db_conn:
        tables = get_table_list(db_conn)
        for table in tables:
            table_info = {
                "schema": get_table_structure(db_conn, table),
                "row_count": get_row_count(db_conn, table)
            }
            if include_sample_data:
                table_info["sample_data"] = get_sample_data(db_conn, table, sample_rows)
            output["postgres"]["tables"][table] = table_info
        db_conn.close()

    if s3_client:
        root_structure = {}
        get_s3_structure(s3_client, db_conn, '', 0, max_depth, max_examples, root_structure)
        output["s3"]["structure"] = root_structure

    return json.dumps(output, indent=2)


if __name__ == "__main__":
    print(dump_to_json(max_examples=3, include_sample_data=True, sample_rows=3, max_depth=5))