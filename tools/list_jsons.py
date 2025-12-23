import boto3
import json
import requests
import os
from dotenv import load_dotenv
import re
import time
import difflib

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
COMPANY_ID = "meditest"
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_MODEL = "grok-4-1-fast-reasoning"
QUERY = ("payslip")  # Change this to your search term
SENDER_ID = "27828530605"  # Change to test for different users


def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


def fetch_json_content(client, key):
    try:
        obj = client.get_object(Bucket=S3_BUCKET_NAME, Key=key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        return data.get('content', json.dumps(data))
    except Exception as e:
        print(f"Error fetching {key}: {str(e)}")
        return ""


def get_all_jsons(sender_id):
    client = get_s3_client()
    # SOPs (global)
    sop_prefix = f"{COMPANY_ID}/sops/all/"
    sop_response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=sop_prefix)
    sop_files = [obj['Key'] for obj in sop_response.get('Contents', []) if obj['Key'].endswith('.json')]

    # Personal (specific to sender_id)
    personal_prefix = f"{COMPANY_ID}/employees/{sender_id}/"
    personal_response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=personal_prefix)
    excluded = ['processed_messages.json', 'queries.json', 'bot_state.json', 'user.json', 'leaves.json', 'state.json']
    personal_files = [obj['Key'] for obj in personal_response.get('Contents', []) if
                      obj['Key'].endswith('.json') and not any(ex in obj['Key'] for ex in excluded)]

    return list(set(sop_files + personal_files))  # Dedupe if any overlap


def get_clean_title(filepath: str) -> str:
    filename = filepath.split('/')[-1].replace('.json', '').replace('_', ' ').replace('-', ' ').strip().lower()
    # Remove version like "v1.2" at end
    filename = re.sub(r'\s+v?\d+\.\d+$', '', filename)
    # Normalize dates like "2025.11" to "Nov 2025"
    date_match = re.search(r'(\d{4})\.(\d{1,2})(?:\.(\d{1,2}))?', filename)
    if date_match:
        year = date_match.group(1)
        month_num = int(date_match.group(2))
        day = date_match.group(3) or ''
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        month_str = months[month_num - 1] if 1 <= month_num <= 12 else ''
        date_str = f"{month_str} {year}" + (f" {day}" if day else '')
        filename = re.sub(r'\d{4}\.\d{1,2}(?:\.\d{1,2})?', date_str, filename)
    return filename.capitalize()


def interpret_query(query, retries=3, backoff=2):
    prompt = f"Query: '{query}'\nIf this seems misspelled or unclear, suggest a corrected version (e.g., 'code of condct' -> 'code of conduct'). Consider common HR/pharma terms like 'payslip', 'leave policy', 'patient marketing'. If no correction needed, output the original query. Output ONLY the query (corrected or original)."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(retries):
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                corrected = response.json()['choices'][0]['message']['content'].strip()
                if corrected != query:
                    print(
                        f"Interpreted '{query}' as '{corrected}' for better results. If incorrect, rerun with exact spelling.")
                    return corrected
                else:
                    return query  # No print if unchanged
        except requests.Timeout:
            print(f"Timeout on attempt {attempt + 1}. Retrying after {backoff} seconds...")
            time.sleep(backoff)
            backoff *= 2
        except Exception as e:
            print(f"Interpretation failed on attempt {attempt + 1}: {e}")
            time.sleep(backoff)
    print("All retries failed. Using original query.")
    return query


def generate_keywords(query, retries=3, backoff=2):
    prompt = f"Query: '{query}'\nExtract key non-stopwords (ignore 'the', 'and', 'or', etc.). Generate variations: common misspellings, American/British spellings (e.g., color/colour), synonyms. Output ONLY a JSON array of unique strings."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(retries):
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                keywords = json.loads(content)
                print(f"Generated keywords: {keywords}")
                return keywords
        except requests.Timeout:
            print(f"Timeout on attempt {attempt + 1}. Retrying after {backoff} seconds...")
            time.sleep(backoff)
            backoff *= 2  # Exponential backoff
        except Exception as e:
            print(f"Keyword generation failed on attempt {attempt + 1}: {e}")
            time.sleep(backoff)
    print("All retries failed. Using original query words.")
    return re.findall(r'\b\w+\b', query.lower())  # Fallback


def search_docs(files, keywords, interpreted_query):
    print("Filtering relevant files with AI...")
    client = get_s3_client()
    matching = []
    for f in files:  # Search all, don't stop early
        content = fetch_json_content(client, f)
        if not content:
            continue
        lower_content = content.lower()
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', lower_content):
                matching.append(f)
                break
    # Now, check for direct match
    direct_matches = [f for f in matching if difflib.SequenceMatcher(None, get_clean_title(f).lower(),
                                                                     interpreted_query.lower()).ratio() > 0.8]
    if direct_matches:
        return direct_matches[:1]  # If direct title match, take the best one
    return matching[:3]  # Otherwise up to 3


def summarize_docs(matching_files, query):
    print("Generating summaries...")
    client = get_s3_client()
    summaries = []
    for f in matching_files:
        content = fetch_json_content(client, f)
        title = get_clean_title(f)
        prompt = f"Document Name: {title}\nContent: {content}\nQuery: {query}\nOutput Markdown: Start with **{title}** - Relevance: High/Medium/Low. 1-sentence summary. Bullet key details, including relevant sections/subsections where info is found (extract quotes/snippets from those sections if huge doc). Numbered insights. Clean, mobile-friendly, emojis optional. No hashes like # or ### in text."
        headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                summary = response.json()['choices'][0]['message']['content'].strip()
                # Remove any hashes
                summary = re.sub(r'#+\s*', '', summary)
                # Parse relevance
                relevance_match = re.search(r'Relevance:\s*(\w+)', summary, re.I)
                relevance = relevance_match.group(1).capitalize() if relevance_match else 'Unknown'
                summaries.append((summary, relevance))
            else:
                summary = f"**{title}** - Error: Summary failed."
                summaries.append((summary, 'Unknown'))
        except Exception as e:
            summary = f"**{title}** - Error: {str(e)}"
            summaries.append((summary, 'Unknown'))

    # Sort by relevance: High > Medium > Low > Unknown
    relevance_order = {'High': 0, 'Medium': 1, 'Low': 2, 'Unknown': 3}
    summaries.sort(key=lambda x: relevance_order.get(x[1], 3))

    # Extract sorted summaries
    sorted_summaries = [summary for summary, _ in summaries]
    return sorted_summaries


if __name__ == "__main__":
    interpreted_query = interpret_query(QUERY)
    keywords = generate_keywords(interpreted_query)
    files = get_all_jsons(SENDER_ID)
    matching_files = search_docs(files, keywords, interpreted_query)
    if not matching_files:
        print("No matching documents found.")
    else:
        print(f"Matching documents: {[get_clean_title(f) for f in matching_files]}")
        summaries = summarize_docs(matching_files, interpreted_query)
        print("\n\n".join(summaries))