import os
import psycopg2
import boto3
from dotenv import load_dotenv
import json

# Load environment variables from .env
load_dotenv()

# PostgreSQL connection details from environment variables
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

# AWS S3 configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "af-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # Should be 'proquery-hr'


# PostgreSQL Functions (unchanged)
def connect_to_postgres():
    """Establishes connection to PostgreSQL using environment variables."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        print("Successfully connected to PostgreSQL database!")
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None


def get_table_list(conn):
    """Fetches all table names from the public schema."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
            """)
            tables = [row[0] for row in cursor.fetchall()]
            return tables
    except Exception as e:
        print(f"Error fetching table list: {e}")
        return []


def get_table_structure(conn, table_name):
    """Fetches column names and data types for a given table."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public';
            """, (table_name,))
            structure = cursor.fetchall()
            return structure
    except Exception as e:
        print(f"Error fetching structure for table {table_name}: {e}")
        return []


def get_postgres_sample_data(conn, table_name, limit=5):
    """Fetches up to 5 sample rows from a given PostgreSQL table."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s;", (limit,))
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            sample_data = [dict(zip(column_names, row)) for row in rows]
            return sample_data
    except Exception as e:
        print(f"Error fetching sample data for table {table_name}: {e}")
        return []


# S3 Functions (Modified for Full Recursive Listing)
def connect_to_s3():
    """Establishes connection to AWS S3 using environment variables or AWS CLI config."""
    try:
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )
        else:
            s3_client = boto3.client('s3', region_name=AWS_REGION)
        print("Successfully connected to AWS S3!")
        return s3_client
    except Exception as e:
        print(f"Error connecting to AWS S3: {e}")
        return None


def list_all_s3_objects(s3_client, bucket_name, prefix=''):
    """Recursively lists all objects and prefixes in the S3 bucket starting from the given prefix."""
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        all_objects = []
        all_prefixes = set()

        for page in page_iterator:
            if 'CommonPrefixes' in page:
                for common_prefix in page['CommonPrefixes']:
                    all_prefixes.add(common_prefix['Prefix'])
            if 'Contents' in page:
                for obj in page['Contents']:
                    all_objects.append({
                        'Key': obj['Key'],
                        'Size': obj['Size'],
                        'LastModified': obj['LastModified']
                    })

        # Recurse into sub-prefixes
        for sub_prefix in all_prefixes:
            sub_objects, sub_prefixes = list_all_s3_objects(s3_client, bucket_name, sub_prefix)
            all_objects.extend(sub_objects)
            all_prefixes.update(sub_prefixes)

        return all_objects, all_prefixes
    except Exception as e:
        print(f"Error listing S3 objects for prefix '{prefix}' in bucket {bucket_name}: {e}")
        return [], set()


# Main Exploration Function (Updated to Use Full S3 Listing)
def explore_databases():
    """Explores both PostgreSQL and S3 databases with clear structure."""
    # PostgreSQL Exploration (unchanged)
    print("\n=== Exploring PostgreSQL Database ===")
    conn = connect_to_postgres()
    if conn:
        tables = get_table_list(conn)
        if not tables:
            print("No tables found in the 'public' schema.")
        else:
            print(f"Database: {DB_NAME}")
            print(f"Found {len(tables)} tables: {tables}\n")
            for table in tables:
                print(f"  - Table: {table}")
                structure = get_table_structure(conn, table)
                if structure:
                    print("    Structure:")
                    for column_name, data_type in structure:
                        print(f"      - {column_name}: {data_type}")
                sample_data = get_postgres_sample_data(conn, table)
                if sample_data:
                    print("    Sample Data (up to 5 rows):")
                    for i, row in enumerate(sample_data, 1):
                        print(f"      Row {i}: {json.dumps(row, indent=4, default=str)}")
                else:
                    print("    No sample data retrieved.")
                print()
        conn.close()

    # S3 Exploration (Now Full Recursive)
    print("\n=== Exploring AWS S3 Storage ===")
    s3_client = connect_to_s3()
    if not s3_client or not S3_BUCKET_NAME:
        print("Cannot explore S3: Missing connection or S3_BUCKET_NAME in .env.")
        return
    print(f"Bucket: {S3_BUCKET_NAME}")

    # Start from root or specific prefix (e.g., 'MediTest/')
    root_prefix = 'MediTest/'  # Adjust if needed; '' for full bucket
    all_objects, all_prefixes = list_all_s3_objects(s3_client, S3_BUCKET_NAME, root_prefix)

    print("Full Structure:")
    print(f" - Prefixes Found: {sorted(all_prefixes)}")
    if all_objects:
        print(" - All Objects:")
        for obj in all_objects:
            print(f"   - Key: {obj['Key']}, Size: {obj['Size']}, LastModified: {obj['LastModified']}")
    else:
        print(" - No objects found under the prefix.")


if __name__ == "__main__":
    explore_databases()