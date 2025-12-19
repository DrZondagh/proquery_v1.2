import os
import boto3
import json
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
    endpoint_url=f"https://s3.{AWS_REGION}.amazonaws.com"
)


def get_all_objects(prefix=''):
    objects = []
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix):
        if 'Contents' in page:
            objects.extend(page['Contents'])
    return [obj['Key'] for obj in objects]


def build_tree(keys):
    tree = {}
    for key in keys:
        parts = key.split('/')
        current = tree
        for part in parts:
            if part:
                if part not in current:
                    current[part] = {}
                current = current[part]
            else:
                current['/'] = {}  # Root empty
    return tree


def print_tree(tree, indent=''):
    output = []
    for key, sub_tree in sorted(tree.items()):
        output.append(f"{indent}{key}" + ('/' if sub_tree else ''))
        output.extend(print_tree(sub_tree, indent + '    '))
    return output


def get_company_info(company):
    employees = []
    roles = set()
    files = []

    # Get employees
    emp_prefix = f"{company}/employees/"
    emp_keys = get_all_objects(emp_prefix)

    for key in emp_keys:
        if '/user.json' in key:
            phone = key.split('/')[-2]
            try:
                obj = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
                data = json.loads(obj['Body'].read().decode('utf-8'))
                name = data.get('person_name', 'Unknown')
                role = data.get('role', 'Unknown')
                employees.append((phone, name, role))
                roles.add(role)
            except (ClientError, json.JSONDecodeError) as e:
                print(f"Error reading {key}: {e}")

        elif not key.endswith('/'):
            files.append(key.split(emp_prefix)[-1])  # Relative path

    # Get other files (sops, hr_docs)
    other_prefixes = [f"{company}/sops/", f"{company}/hr_docs/"]
    for pref in other_prefixes:
        other_keys = get_all_objects(pref)
        for key in other_keys:
            if not key.endswith('/'):
                files.append(key.split(f"{company}/")[-1])

    return employees, sorted(roles), sorted(set(files))


def main():
    print(f"Exploring structure in {S3_BUCKET_NAME}")

    all_keys = get_all_objects()
    tree = build_tree(all_keys)

    print("\nFull Bucket Structure:")
    print('\n'.join(print_tree(tree)))

    print("\nCompanies and Details:")
    companies = [k for k in tree if k and not k.startswith('admin/')]  # Exclude admin

    for comp in sorted(companies):
        print(f"\nCompany: {comp}")
        employees, roles, files = get_company_info(comp)

        print("  Roles:", ', '.join(roles) if roles else "None")

        print("  Employees:")
        for phone, name, role in sorted(employees):
            print(f"    - {name} ({phone}): {role}")

        print("  Files Present (relative paths, no content):")
        for file in files:
            print(f"    - {file}")

    print("\nExploration complete!")


if __name__ == "__main__":
    main()