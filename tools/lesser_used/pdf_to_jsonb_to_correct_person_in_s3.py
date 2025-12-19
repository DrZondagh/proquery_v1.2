import os
import json
import boto3
from dotenv import load_dotenv
import PyPDF2
from botocore.exceptions import ClientError
from datetime import datetime

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")  # proquery-docs-bucket

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Updated mapping with Jake, Wikus added, Jacques fixed to Malan
name_to_info = {
    "Jacques Malan": ("27737381952", "hr_head", "jacques@meditest.com"),
    "Jake Zondagh": ("27828530605", "ceo", "jake@meditest.com"),
    "Kim Wiid": ("27828594539", "employee", "kim@meditest.com"),
    "Michael Zondagh": ("27828589184", "manager", "michael@meditest.com"),
    "Wikus JV Rensburg": ("27823397674", "employee", "wikus@meditest.com")
}

company = "meditest"
company_prefix = f"{company}/"
employees_prefix = f"{company_prefix}employees/"
sops_prefix = f"{company_prefix}sops/all/"
hr_docs_prefix = f"{company_prefix}hr_docs/"  # Empty for now, per request

# Folders
sops_folder = r"C:\Users\drzon\OneDrive\Documents\1. Business and admin\1. AI Chatbot\MediTest docs\PDFs"
employee_docs_folder = r"C:\Users\drzon\OneDrive\Documents\1. Business and admin\1. AI Chatbot\MediTest HR docs"


def extract_text_from_pdf(file_path):
    try:
        text = ""
        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"Failed to extract from {file_path}: {e}")
        return ""


def upload_file_to_s3(key, file_path):
    try:
        with open(file_path, 'rb') as f:
            s3_client.upload_fileobj(f, S3_BUCKET_NAME, key)
        print(f"Uploaded file: {key}")
    except ClientError as e:
        print(f"Error uploading {key}: {e}")


def upload_json_to_s3(key, data):
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=key,
            Body=json.dumps(data, indent=4),
            ContentType='application/json'
        )
        print(f"Uploaded JSON: {key}")
    except ClientError as e:
        print(f"Error uploading {key}: {e}")


def get_or_create_index(key, default_data):
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        return json.loads(obj['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            upload_json_to_s3(key, default_data)
            return default_data
        raise e


def create_folder_if_not_exists(prefix):
    try:
        s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=prefix)
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=prefix)
            print(f"Created folder: {prefix}")


def process_file(file_path, is_sop_folder=False):
    filename = os.path.basename(file_path).lower()
    create_folder_if_not_exists(company_prefix)  # Ensure root

    # SOP if from SOPs or "sop" in name
    if is_sop_folder or "sop" in filename:
        create_folder_if_not_exists(sops_prefix)
        s3_key = f"{sops_prefix}{os.path.basename(file_path)}"
        try:
            s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            print(f"Skipping existing SOP: {s3_key}")
            return "skip"
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                upload_file_to_s3(s3_key, file_path)

                json_data = {"title": os.path.basename(file_path).rsplit('.', 1)[0], "full_text": ""}
                if filename.endswith(".pdf"):
                    json_data["full_text"] = extract_text_from_pdf(file_path)
                    json_data["accessible_roles"] = ["ceo", "hr_head", "manager", "employee"]
                json_key = s3_key.rsplit('.', 1)[0] + ".json"
                upload_json_to_s3(json_key, json_data)
                return "sop"

    # Personal (per-employee HR docs, as per request—no general)
    for name, (phone, role, email) in name_to_info.items():
        normalized_name = name.lower().replace(" ", "").replace(".", "")
        normalized_filename = filename.replace(" ", "").replace("_", "").replace("-", "")
        if normalized_name in normalized_filename:
            emp_folder = f"{employees_prefix}{phone}/"
            create_folder_if_not_exists(emp_folder)

            # user.json
            user_key = f"{emp_folder}user.json"
            user_data = {
                "role": role,
                "person_name": name,
                "company_id": company,
                "email": email
            }
            upload_json_to_s3(user_key, user_data)

            # queries.json
            queries_key = f"{emp_folder}queries.json"
            get_or_create_index(queries_key, [])

            # Upload file if not exists
            s3_key = f"{emp_folder}{os.path.basename(file_path)}"
            try:
                s3_client.head_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                print(f"Skipping existing personal: {s3_key}")
                return "skip"
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    upload_file_to_s3(s3_key, file_path)

                    # JSON
                    json_data = {"title": os.path.basename(file_path).rsplit('.', 1)[0], "full_text": ""}
                    if filename.endswith(".pdf"):
                        json_data["full_text"] = extract_text_from_pdf(file_path)
                        json_data["accessible_roles"] = [role]
                        json_data["owner"] = phone
                    json_key = s3_key.rsplit('.', 1)[0] + ".json"
                    upload_json_to_s3(json_key, json_data)
                    return "personal"

    print(f"No match for {filename} - skipping.")
    return None


def main():
    create_folder_if_not_exists(company_prefix)
    create_folder_if_not_exists(employees_prefix)
    create_folder_if_not_exists(sops_prefix)
    create_folder_if_not_exists(hr_docs_prefix)  # Keep empty

    # Create role-specific SOP folders
    for role in ["all", "ceo", "director", "manager", "employee", "hr_head"]:
        create_folder_if_not_exists(f"{company_prefix}sops/{role}/")

    employees_list = []
    roles_list = []
    personal_count = 0

    # Process SOPs (no change, skip existing to avoid dupes)
    sop_added = 0
    for filename in os.listdir(sops_folder):
        file_path = os.path.join(sops_folder, filename)
        if os.path.isfile(file_path):
            result = process_file(file_path, is_sop_folder=True)
            if result == "sop":
                sop_added += 1

    # Count total SOPs in all/
    sop_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=sops_prefix):
        sop_files.extend([obj['Key'] for obj in page.get('Contents', []) if obj['Key'].endswith('.pdf')])
    sop_count = len(sop_files)

    # Process employee docs (personal only, no general HR)
    for filename in os.listdir(employee_docs_folder):
        file_path = os.path.join(employee_docs_folder, filename)
        if os.path.isfile(file_path):
            result = process_file(file_path)
            if result == "personal":
                personal_count += 1

    # Update indexes (include Jake and Wikus now)
    for name, (phone, role, _) in name_to_info.items():
        employees_list.append(phone)
        if role not in roles_list:
            roles_list.append(role)

    company_index_key = f"{company_prefix}index.json"
    company_default = {"employees": [], "roles": [], "sop_count": 0, "last_updated": ""}
    company_data = get_or_create_index(company_index_key, company_default)
    company_data["employees"] = sorted(set(company_data["employees"] + employees_list))
    company_data["roles"] = sorted(set(company_data["roles"] + roles_list))
    company_data["sop_count"] = sop_count
    company_data["last_updated"] = "2025-12-03"
    upload_json_to_s3(company_index_key, company_data)

    sops_index_key = f"{company_prefix}sops/index.json"
    sops_default = {
        "roles": {
            "ceo": 0,
            "director": 0,
            "hr_head": 0,
            "manager": 0,
            "employee": 0,
            "all": sop_count
        },
        "total_docs": sop_count
    }
    upload_json_to_s3(sops_index_key, sops_default)

    hr_index_key = f"{company_prefix}hr_docs/index.json"
    hr_default = {"docs": [], "last_updated": "2025-12-03"}
    upload_json_to_s3(hr_index_key, hr_default)

    print(f"Processed {sop_added} new SOPs ({sop_count} total), {personal_count} personal files.")
    print("Wikus added, Jake added, Jacques fixed to Malan, structure updated—no general HR as requested. Run checker!")


if __name__ == "__main__":
    main()