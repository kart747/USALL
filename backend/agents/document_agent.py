import os
import json
from typing import Any, Dict, List

import requests


# System prompt from project plan
SYSTEM_PROMPT = """
You are YojanaPath's document checklist generator. Given a list of matched schemes and the user's situation, generate a consolidated, deduplicated list of documents the user needs to bring to the CSC.

RULES:
1. List only documents actually required for the matched schemes
2. Deduplicate — if Aadhaar appears in 3 schemes, list it once
3. Flag any document the user may not have based on their situation
4. Output in plain Hindi if user language is Hindi, English otherwise
5. Respond ONLY in valid JSON. No preamble.

OUTPUT FORMAT:
{
  "documents": [
    {
      "document": "Aadhaar Card",
      "required_for": ["PMAY-G", "MGNREGA", "PMJJBY"],
      "flag": null
    }
  ]
}
"""


def _call_groq(system_prompt: str, user_message: str) -> str:
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise EnvironmentError('GROQ_API_KEY not set')

    base = os.environ.get('GROQ_API_URL', 'https://api.groq.com/v1')
    url = f"{base}/llms/llama-3.1-8b-instant/completions"
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ],
        'max_tokens': 800,
        'temperature': 0.0
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # extract
    choices = data.get('choices') or []
    if choices:
        first = choices[0]
        if 'message' in first:
            return first['message'].get('content', '')
        return first.get('text', '') or first.get('content', '')
    return data.get('text', '')


def generate_documents(matched_schemes: List[Dict[str, Any]], user_data: Dict[str, Any]) -> Dict[str, Any]:
    # Build a simple payload for LLM or fallback
    user_message = json.dumps({'matched_schemes': matched_schemes, 'user_data': user_data}, ensure_ascii=False)

    # Try Groq first
    try:
        content = _call_groq(SYSTEM_PROMPT, user_message)
        parsed = json.loads(content)
        return parsed
    except Exception:
        # Local deterministic fallback: aggregate documents from schemes
        doc_map: Dict[str, Dict[str, Any]] = {}
        for s in matched_schemes:
            sid = s.get('scheme_id')
            name = s.get('scheme_name') or sid
            docs = s.get('documents_required') or []
            for d in docs:
                if d not in doc_map:
                    doc_map[d] = {'document': d, 'required_for': [], 'flag': None}
                doc_map[d]['required_for'].append(name)

        # Flagging heuristics
        for d, entry in doc_map.items():
            lower = d.lower()
            if 'aadhaar' in lower:
                if not user_data.get('has_aadhaar', True) and not user_data.get('aadhaar'):
                    entry['flag'] = 'User may not have Aadhaar on hand'
            if 'bank' in lower or 'passbook' in lower:
                if not user_data.get('aadhaar_seeded_bank_account', False):
                    entry['flag'] = 'Ensure your bank account is linked to Aadhaar before visiting CSC'

        documents = list(doc_map.values())

        # Language handling: if user prefers Hindi, translate a few known doc names simply
        lang = user_data.get('language') or user_data.get('lang')
        if lang and lang.lower().startswith('hi'):
            for e in documents:
                # naive replacements for common docs
                e['document'] = (
                    e['document'].replace('Aadhaar Card', 'आधार कार्ड')
                                 .replace('Bank Passbook', 'बैंक पासबुक')
                                 .replace('Photo', 'फोटो')
                )

        return {'documents': documents}


if __name__ == '__main__':
    # quick local test
    sample = [{'scheme_id': 'pmay_g', 'scheme_name': 'PMAY-G', 'documents_required': ['Aadhaar Card', 'Bank Passbook (Aadhaar-seeded)', 'Photo of current house (showing kutcha construction)']}]
    user = {'aadhaar_seeded_bank_account': False, 'has_aadhaar': True, 'language': 'en'}
    print(json.dumps(generate_documents(sample, user), ensure_ascii=False, indent=2))
