import os
import boto3
import json
from dotenv import load_dotenv
from botocore.exceptions import ClientError
from pathlib import Path

# From project_schema.py — FIXED & PERFECT
IGNORE = {
    '.venv', '.venv1', '.git', '__pycache__', '.idea', 'build', 'dist', 'node_modules', '.pytest_cache'
}


def tree(dir_path: Path, prefix: str = "") -> None:
    """Print a directory tree, ignoring junk folders"""
    # Get all entries and filter out ignored ones
    contents = [p for p in dir_path.iterdir() if p.name not in IGNORE]
    # Sort directories first, then files
    contents = sorted(contents, key=lambda p: (p.is_file(), p.name.lower()))
    # Build pointers (├── or └──)
    pointers = ["├── "] * (len(contents) - 1) + (["└── "] if contents else [])
    for pointer, path in zip(pointers, contents):
        if path.is_dir():
            print(prefix + pointer + path.name + "/")
            # Decide next prefix (continues the tree line)
            extension = "│   " if pointer == "├── " else "    "  # Adjusted for alignment
            tree(path, prefix + extension)
        else:
            print(prefix + pointer + path.name)


# From entire_proquery_for_grok.py — DUMPS ALL CODE EXCEPT tools/ FOLDER
EXCLUDE_DIRS = {
    '.git', '__pycache__', '.venv', '.venv1', 'venv', '.idea', 'build', 'dist', '.pytest_cache', 'node_modules', 'tools'
    # ← THIS LINE HIDES THE ENTIRE tools/ FOLDER
}
EXCLUDE_FILES = {
    '.env', '.gitignore', 'Thumbs.db', '.DS_Store'
}


def dump_code(root: Path):
    print("PROQUERY FULL CLEAN CODE DUMP".center(80, "="))
    print(f"Root: {root}\n")
    count = 0
    for file in sorted(root.rglob("*.py")):
        # Skip any file inside excluded dirs (including tools/)
        if any(part in EXCLUDE_DIRS for part in file.parts):
            continue
        if file.name in EXCLUDE_FILES:
            continue
        if file.stat().st_size > 5_000_000:
            print(f"SKIPPED (too big): {file.relative_to(root)}")
            continue
        count += 1
        rel = file.relative_to(root)
        print(f"\nFILE {count}: {rel}")
        print("-" * 80)
        try:
            print(file.read_text(encoding="utf-8", errors="replace").rstrip())
        except Exception as e:
            print(f"[READ ERROR: {e}]")
        print("\n" + "=" * 80)
    print(f"DONE — {count} Python files dumped. Ready for Grok!")


# From simplified s3_checker.py
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
    return tree


def print_tree(tree, indent='', summarize=True):
    output = []
    items = sorted(tree.items())
    for i, (key, sub_tree) in enumerate(items):
        is_dir = bool(sub_tree)
        line = f"{indent}{key}{'/' if is_dir else ''}"
        if is_dir and summarize:
            sub_items = list(sub_tree.keys())
            if len(sub_items) > 3:  # Lower threshold for summarization to catch more cases
                example1 = sub_items[0]
                example2 = sub_items[1] if len(sub_items) > 1 else ''
                line += f" (contains {len(sub_items)} items, e.g. {example1}, {example2}...)"
                output.append(line)
                # Don't recurse into summarized dirs
            else:
                output.append(line)
                output.extend(print_tree(sub_tree, indent + '  ', summarize))
        else:
            output.append(line)
            if is_dir:
                output.extend(print_tree(sub_tree, indent + '  ', summarize))
    return output


def get_company_info(company):
    employees = []
    roles = set()
    files = set()
    # Get employees
    emp_prefix = f"{company}/employees/"
    emp_keys = get_all_objects(emp_prefix)
    employee_dirs = set()
    for key in emp_keys:
        if '/user.json' in key:
            parts = key.split('/')
            phone = parts[-2]
            employee_dirs.add(phone)
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
            rel_path = key[len(emp_prefix):]
            files.add(rel_path)
    # Summarize employee files per dir
    summarized_employee_files = {phone: set() for phone in employee_dirs}
    for f in files:
        if '/' in f:
            phone, fname = f.split('/', 1)
            if phone in summarized_employee_files:
                summarized_employee_files[phone].add(fname)
    files.clear()
    for phone, flist in summarized_employee_files.items():
        if len(flist) > 4:
            files.add(
                f"{phone}/ (user.json, queries.json + similar, various docs like *_Benefits_Guide.json/pdf, *_Payslip.json/pdf, etc.)")
        else:
            for fname in sorted(flist):
                files.add(f"{phone}/{fname}")
    # Get other files (sops, hr_docs)
    other_prefixes = [f"{company}/sops/", f"{company}/hr_docs/"]
    for pref in other_prefixes:
        other_keys = get_all_objects(pref)
        for key in other_keys:
            if not key.endswith('/'):
                rel_path = key[len(f"{company}/"):]
                files.add(rel_path)
    # Summarize SOPs
    sop_files = {f for f in files if f.startswith('sops/all/')}
    if sop_files:
        files -= sop_files
        files.add('sops/all/ (many SOP-HR/MA/MKT-*.json/pdf for procedures)')
    return employees, sorted(roles), sorted(files)


def s3_main():
    print(f"Exploring structure in {S3_BUCKET_NAME}")
    all_keys = get_all_objects()
    tree = build_tree(all_keys)
    print("\nSimplified Bucket Structure:")
    print('\n'.join(print_tree(tree)))
    print("\nCompanies and Details:")
    companies = [k for k in tree if k and not k.startswith('admin/')]  # Exclude admin
    for comp in sorted(companies):
        print(f"\nCompany: {comp}")
        employees, roles, files = get_company_info(comp)
        print("  Roles:", ', '.join(roles) if roles else "None")
        print("  Employees:")
        for phone, name, role in sorted(employees):
            print(f"   - {name} ({phone}): {role}")
        print("  Files Present (summarized relative paths):")
        for file in files:
            print(f"   - {file}")
    print("\nExploration complete!")


if __name__ == "__main__":
    # Local project part
    root = Path(__file__).parent.parent
    print(f"Project Structure — {root.name}/\n")
    tree(root)
    print("\nDone with tree.\n")
    dump_code(root)

    # S3 part (requires .env with AWS creds)
    print("\n--- Starting S3 Exploration ---\n")
    s3_main()