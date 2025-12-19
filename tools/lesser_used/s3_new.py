import boto3
import json
from botocore.exceptions import ClientError
from src.config import AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME


# Create S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def create_folder(prefix):
    """Creates an S3 'folder' by uploading an empty object with trailing /"""
    try:
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=prefix)
        print(f"Created folder: {prefix}")
    except ClientError as e:
        print(f"Error creating {prefix}: {e}")

def upload_json(prefix, filename, data):
    """Uploads a JSON file to S3"""
    key = f"{prefix}{filename}"
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType='application/json'
        )
        print(f"Uploaded: {key}")
    except ClientError as e:
        print(f"Error uploading {key}: {e}")

# Company setup for Renegade_HR
company_prefix = 'renegade_hr/'

# Create company root and index
create_folder(company_prefix)
upload_json(company_prefix, 'index.json', {
    "employees": ["27820000001", "27820000002", "27820000003", "27820000004"],
    "roles": ["ceo", "hr_head", "manager", "employee"],
    "sop_count": 0,
    "last_updated": "2025-12-03"
})

# Employees setup
employees_prefix = f"{company_prefix}employees/"
create_folder(employees_prefix)

# Jake Zondagh - CEO
jake_prefix = f"{employees_prefix}27820000001/"
create_folder(jake_prefix)
upload_json(jake_prefix, 'user.json', {
    "role": "ceo",
    "person_name": "Jake Zondagh",
    "company_id": "renegade_hr",
    "email": "jake@renegadehr.com"
})
upload_json(jake_prefix, 'queries.json', [])  # Empty array for logs

# Jacques Malan - Head of HR
jacques_prefix = f"{employees_prefix}27820000002/"
create_folder(jacques_prefix)
upload_json(jacques_prefix, 'user.json', {
    "role": "hr_head",
    "person_name": "Jacques Malan",
    "company_id": "renegade_hr",
    "email": "jacques@renegadehr.com"
})
upload_json(jacques_prefix, 'queries.json', [])

# Michael Zondagh - Manager
michael_prefix = f"{employees_prefix}27820000003/"
create_folder(michael_prefix)
upload_json(michael_prefix, 'user.json', {
    "role": "manager",
    "person_name": "Michael Zondagh",
    "company_id": "renegade_hr",
    "email": "michael@renegadehr.com"
})
upload_json(michael_prefix, 'queries.json', [])

# Kim Wiid - Employee
kim_prefix = f"{employees_prefix}27820000004/"
create_folder(kim_prefix)
upload_json(kim_prefix, 'user.json', {
    "role": "employee",
    "person_name": "Kim Wiid",
    "company_id": "renegade_hr",
    "email": "kim@renegadehr.com"
})
upload_json(kim_prefix, 'queries.json', [])

# HR Docs setup
hr_docs_prefix = f"{company_prefix}hr_docs/"
create_folder(hr_docs_prefix)
upload_json(hr_docs_prefix, 'index.json', {"docs": [], "last_updated": "2025-12-03"})

# SOPs setup with role-specific folders
sops_prefix = f"{company_prefix}sops/"
create_folder(sops_prefix)
upload_json(sops_prefix, 'index.json', {
    "roles": {"ceo": 0, "hr_head": 0, "manager": 0, "employee": 0, "all": 0},
    "total_docs": 0
})

# Role-specific SOP folders (empty for now)
for role in ['all', 'ceo', 'hr_head', 'manager', 'employee']:
    create_folder(f"{sops_prefix}{role}/")

# Admin global folder (optional, locked via IAM)
admin_prefix = 'admin/'
create_folder(admin_prefix)
create_folder(f"{admin_prefix}exports/")

print("S3 structure for Renegade_HR created successfully! Check your bucket.")