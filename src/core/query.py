# src/core/query.py
# Shifted to AI-based selection of relevant docs from all files using titles/snippets.
# Fetches content only for selected ones to summarize.
# This lets AI decide relevance holistically, fixing keyword misses.

import boto3
import json
import requests
import re
import time
import difflib
from src.core.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME, GROK_API_KEY, \
    GROK_MODEL
from src.core.whatsapp_handler import send_whatsapp_text  # Import to send progress messages


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


def get_all_jsons(company_id, sender_id):
    client = get_s3_client()
    # SOPs (global)
    sop_prefix = f"{company_id}/sops/all/"
    sop_response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=sop_prefix)
    sop_files = [obj['Key'] for obj in sop_response.get('Contents', []) if obj['Key'].endswith('.json')]

    # Personal (specific to sender_id) - prioritize by listing first
    personal_prefix = f"{company_id}/employees/{sender_id}/"
    personal_response = client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=personal_prefix)
    excluded = ['processed_messages.json', 'queries.json', 'bot_state.json', 'user.json', 'leaves.json', 'state.json']
    personal_files = [obj['Key'] for obj in personal_response.get('Contents', []) if
                      obj['Key'].endswith('.json') and not any(ex in obj['Key'] for ex in excluded)]

    return list(set(personal_files + sop_files))  # Personal first, dedupe


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


def interpret_query(query, sender_id, company_id, retries=3, backoff=2):
    prompt = f"Query: '{query}'\nIf this seems misspelled or unclear, suggest a corrected version (e.g., 'code of condct' -> 'code of conduct'). Consider common HR/pharma terms like 'payslip', 'leave policy', 'patient marketing'. If no correction needed, output the original query. Output ONLY the query (corrected or original)."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    for attempt in range(retries):
        try:
            response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                corrected = response.json()['choices'][0]['message']['content'].strip()
                if corrected != query:
                    msg = f"Interpreted '{query}' as '{corrected}' for better results. If incorrect, rerun with exact spelling."
                    send_whatsapp_text(sender_id, msg)
                    return corrected
                else:
                    return query  # No message if unchanged
        except requests.Timeout:
            print(f"Timeout on attempt {attempt + 1}. Retrying after {backoff} seconds...")
            time.sleep(backoff)
            backoff *= 2
        except Exception as e:
            print(f"Interpretation failed on attempt {attempt + 1}: {e}")
            time.sleep(backoff)
    print("All retries failed. Using original query.")
    return query


def ai_select_docs(query, files, sender_id, company_id, max_select=3):
    send_whatsapp_text(sender_id, "Filtering relevant files with AI...")
    client = get_s3_client()
    doc_entries = []
    for f in files:
        snippet = fetch_json_content(client, f)[:200]
        doc_entries.append(f"Path: {f}\nTitle: {get_clean_title(f)}\nSnippet: {snippet}")
    doc_str = "\n\n".join(doc_entries)
    prompt = f"Query: '{query}'\nDocuments:\n{doc_str}\n\nSelect up to {max_select} most relevant documents (must directly relate; e.g., for 'leave policy', prioritize 'benefits guide' or 'employee handbook' over unrelated SOPs). Output ONLY a JSON array of selected paths (full keys), prioritized by relevance."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            selected = json.loads(response.json()['choices'][0]['message']['content'].strip())
            print(f"AI selected docs: {selected}")
            return [f for f in selected if f in files]  # Validate
    except Exception as e:
        print(f"AI selection failed: {e}")
    return []  # Empty if fails


def summarize_docs(matching_files, query, sender_id, company_id):
    send_whatsapp_text(sender_id, "Generating summaries...")
    client = get_s3_client()
    summaries = []
    for f in matching_files:
        content = fetch_json_content(client, f)
        title = get_clean_title(f)
        prompt = f"Document Name: {title}\nContent: {content[:4000]}...\nQuery: {query}\nOutput Markdown: Start with **{title}** - Relevance: High/Medium/Low. 1-sentence summary. Bullet key details, including relevant sections/subsections where info is found (extract quotes/snippets from those sections if huge doc). Numbered insights. Clean, mobile-friendly, emojis optional. No hashes like # or ### in text."
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
                summaries.append((summary, relevance, f))
            else:
                summary = f"**{title}** - Error: Summary failed."
                summaries.append((summary, 'Unknown', f))
        except Exception as e:
            summary = f"**{title}** - Error: {str(e)}"
            summaries.append((summary, 'Unknown', f))

    # Sort by relevance: High > Medium > Low > Unknown
    relevance_order = {'High': 0, 'Medium': 1, 'Low': 2, 'Unknown': 3}
    summaries.sort(key=lambda x: relevance_order.get(x[1], 3))

    # Extract sorted summaries and files
    return [(summary, f) for summary, _, f in summaries]


def process_query(company_id, sender_id, query):
    send_whatsapp_text(sender_id, "ProQuery: AI driven efficiency. Incoming 🚀")
    try:
        interpreted_query = interpret_query(query, sender_id, company_id)
        files = get_all_jsons(company_id, sender_id)
        matching_files = ai_select_docs(interpreted_query, files, sender_id, company_id)
        if not matching_files:
            return None, "No matching documents found. Check your Benefits Guide or Employee Handbook in Documents menu."
        summaries = summarize_docs(matching_files, interpreted_query, sender_id, company_id)
        if not summaries:
            return None, "Nothing related for your search query. Check your Benefits Guide or Employee Handbook in Documents menu."
        return summaries, None  # Return list of (summary, file_path) tuples or error message
    except Exception as e:
        print(f"Query processing failed: {e}")
        return None, "ProQuery down try again later and let me know via email (info@proquery.live)"