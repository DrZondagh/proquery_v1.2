# src/core/query.py
import json
import requests
import re
import time
import difflib
from src.core.config import GROK_API_KEY, GROK_MODEL
from src.core.whatsapp_handler import send_whatsapp_text
from src.core.db_handler import get_user_id, get_pg_conn

def get_all_docs(company_id, sender_id):
    user_id = get_user_id(sender_id)
    conn = get_pg_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT s3_key, content FROM documents WHERE company_id = %s AND (user_id IS NULL OR user_id = %s)",
                (company_id, user_id)
            )
            rows = cur.fetchall()
            return [{'s3_key': row[0], 'content': row[1]} for row in rows]
    except Exception as e:
        print(f"Error fetching docs: {str(e)}")
        return []
    finally:
        conn.close()

def get_clean_title(filepath: str) -> str:
    filename = filepath.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ').strip().lower()
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

def ai_select_docs(query, docs, sender_id, company_id, max_select=3):
    send_whatsapp_text(sender_id, "Filtering relevant files with AI...")
    doc_entries = []
    for d in docs:
        snippet = json.dumps(d['content'])[:200]
        doc_entries.append(f"Path: {d['s3_key']}\nTitle: {get_clean_title(d['s3_key'])}\nSnippet: {snippet}")
    doc_str = "\n\n".join(doc_entries)
    prompt = f"Query: '{query}'\nDocuments:\n{doc_str}\n\nSelect up to {max_select} most relevant documents (must directly relate; e.g., for 'leave policy', prioritize 'benefits guide' or 'employee handbook' over unrelated SOPs). Output ONLY a JSON array of selected paths (full keys), prioritized by relevance."
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GROK_MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post("https://api.x.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            selected = json.loads(response.json()['choices'][0]['message']['content'].strip())
            print(f"AI selected docs: {selected}")
            return [f for f in selected if any(d['s3_key'] == f for d in docs)]  # Validate
    except Exception as e:
        print(f"AI selection failed: {e}")
    return []  # Empty if fails

def summarize_docs(matching_files, query, docs, sender_id, company_id):
    send_whatsapp_text(sender_id, "Generating summaries...")
    summaries = []
    for f in matching_files:
        content = next((d['content'] for d in docs if d['s3_key'] == f), None)
        if not content:
            continue
        title = get_clean_title(f)
        prompt = f"Document Name: {title}\nContent: {json.dumps(content)[:4000]}...\nQuery: {query}\nOutput Markdown: Start with **{title}** - Relevance: High/Medium/Low. 1-sentence summary. Bullet key details, including relevant sections/subsections where info is found (extract quotes/snippets from those sections if huge doc). Numbered insights. Clean, mobile-friendly, emojis optional. No hashes like # or ### in text."
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
        docs = get_all_docs(company_id, sender_id)
        if not docs:
            return None, "No documents available."
        matching_files = ai_select_docs(interpreted_query, docs, sender_id, company_id)
        if not matching_files:
            return None, "No matching documents found. Check your Benefits Guide or Employee Handbook in Documents menu."
        summaries = summarize_docs(matching_files, interpreted_query, docs, sender_id, company_id)
        if not summaries:
            return None, "Nothing related for your search query. Check your Benefits Guide or Employee Handbook in Documents menu."
        return summaries, None  # Return list of (summary, s3_key) tuples or error message
    except Exception as e:
        print(f"Query processing failed: {e}")
        return None, "ProQuery down try again later and let me know via email (info@proquery.live)"