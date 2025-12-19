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
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # Should be 'proquerytest'

# PostgreSQL Functions
def connect_to_postgres():
    """Establishes connection to PostgreSQL using environment variables."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
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
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
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
                SELECT column_name, data_type
                FROM information_schema.columns
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

# S3 Functions
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

def get_s3_sample_data(s3_client, bucket_name, prefix, limit=2):
    """Fetches up to 2 sample objects from a specific prefix in an S3 bucket."""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix, MaxKeys=limit)
        if 'Contents' not in response:
            return []
        objects = [
            {'Key': obj['Key'], 'Size': obj['Size'], 'LastModified': obj['LastModified']}
            for obj in response['Contents']
        ]
        return objects
    except Exception as e:
        print(f"Error fetching sample data for prefix '{prefix}' in bucket {bucket_name}: {e}")
        return []

# Main Exploration Function
def explore_databases():
    """Explores both PostgreSQL and S3 databases with clear structure."""
    # PostgreSQL Exploration
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

    # S3 Exploration
    print("\n=== Exploring AWS S3 Storage ===")
    s3_client = connect_to_s3()
    if not s3_client or not S3_BUCKET_NAME:
        print("Cannot explore S3: Missing connection or S3_BUCKET_NAME in .env.")
        return

    print(f"Bucket: {S3_BUCKET_NAME}")
    print("Structure:")
    print("  - Prefix: MediTest/")
    sub_prefixes = ['MediTest/HR_Documents/', 'MediTest/SOPs/']
    print(f"    Sub-Prefixes: {sub_prefixes}\n")

    for sub_prefix in sub_prefixes:
        print(f"    - Sub-Prefix: {sub_prefix}")
        sample_data = get_s3_sample_data(s3_client, S3_BUCKET_NAME, sub_prefix)
        if sample_data:
            print("      Sample Objects (2 examples):")
            for i, obj in enumerate(sample_data, 1):
                print(f"        Object {i}: {json.dumps(obj, indent=4, default=str)}")
        else:
            print("      No objects retrieved for this sub-prefix.")
        print()

if __name__ == "__main__":
    explore_databases()