import argparse
import boto3
import json
from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from src.logger import logger  # Reuse existing logger

DEFAULT_SENDER_ID = None  # in format "27828530605"  otherwise "None"Set to a phone number string (e.g., "27828530605") to auto-extract only for that user when no --sender_id; None for all users.

def get_s3_client():
    try:
        client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
        return client
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        return None

def extract_queries(company_id: str, sender_id: str = None, output: str = None):
    client = get_s3_client()
    if not client:
        print("Failed to create S3 client.")
        return

    results = {}
    if sender_id:
        # Specific user
        key = f"{company_id}/employees/{sender_id}/queries.json"
        try:
            obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
            data = json.loads(obj['Body'].read().decode('utf-8'))
            results[sender_id] = data
            print(f"Extracted {len(data)} queries for {sender_id}.")
        except client.exceptions.NoSuchKey:
            print(f"No queries.json for {sender_id}.")
        except Exception as e:
            logger.error(f"Error fetching {key}: {e}")
    else:
        # All users: List all employees/ folders and fetch queries.json
        prefix = f"{company_id}/employees/"
        response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=prefix, Delimiter='/')
        for common_prefix in response.get('CommonPrefixes', []):
            user_prefix = common_prefix['Prefix']
            user_id = user_prefix.split('/')[-2]  # e.g., 27828530605
            key = f"{user_prefix}queries.json"
            try:
                obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
                data = json.loads(obj['Body'].read().decode('utf-8'))
                results[user_id] = data
                print(f"Extracted {len(data)} queries for {user_id}.")
            except client.exceptions.NoSuchKey:
                print(f"No queries.json for {user_id}.")
            except Exception as e:
                logger.error(f"Error fetching {key}: {e}")

    if output:
        with open(output, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Results saved to {output}.")
    else:
        print(json.dumps(results, indent=4))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract queries from S3.")
    parser.add_argument("--company_id", default="meditest", help="Company ID (e.g., meditest; default: meditest)")
    parser.add_argument("--sender_id", help="Specific sender ID (phone number)")
    parser.add_argument("--output", help="Output JSON file path")
    args = parser.parse_args()
    # Use DEFAULT_SENDER_ID if no --sender_id provided and it's set
    effective_sender_id = args.sender_id or DEFAULT_SENDER_ID
    extract_queries(args.company_id, effective_sender_id, args.output)