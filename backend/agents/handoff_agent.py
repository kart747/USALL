import os
import re
import json
from typing import Any, Dict, List

import requests
from textwrap import shorten


SYSTEM_PROMPT = """
You are YojanaPath's CSC handoff generator. Generate a short, plain-language summary the user can show to the VLE operator at their nearest Common Service Centre.

RULES:
1. Keep it under 80 words — simple, clear language
2. Include: any name if given, which schemes they qualify for, 2-3 key facts (location, housing, income)
3. Output in Hindi if user language is Hindi, English otherwise
4. End with: "Please help this person apply for the above schemes."
5. Respond ONLY in valid JSON — no markdown, no code fences, no preamble

OUTPUT FORMAT:
{
  "handoff_summary": "...",
  "schemes_to_apply": ["PMAY-G", "MGNREGA"],
  "csc_instruction": "Please help this person apply for the above schemes."
}
"""


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences the LLM sometimes wraps around JSON."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


def _call_groq(system_prompt: str, user_message: str) -> str:
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise EnvironmentError('GROQ_API_KEY not set')

    base = os.environ.get('GROQ_API_URL', 'https://api.groq.com')
    url = f"{base}/openai/v1/chat/completions"
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    body = {
        'model': 'llama-3.1-8b-instant',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ],
        'max_tokens': 400,
        'temperature': 0.0
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get('choices') or []
    if choices:
        first = choices[0]
        if 'message' in first:
            return first['message'].get('content', '')
        return first.get('text', '') or first.get('content', '')
    return data.get('text', '')


def generate_handoff(matched_schemes: List[Dict[str, Any]], user_data: Dict[str, Any]) -> Dict[str, Any]:
    user_message = json.dumps({'matched_schemes': matched_schemes, 'user_data': user_data}, ensure_ascii=False)

    try:
        raw = _call_groq(SYSTEM_PROMPT, user_message)
        cleaned = _strip_markdown(raw)
        parsed = json.loads(cleaned)
        return parsed
    except Exception:
        # Graceful fallback — no "My name ." when name is missing
        lang = (user_data.get('language') or user_data.get('lang') or 'en').lower()
        name = (user_data.get('name') or '').strip()

        # Short scheme list — use scheme_id if name is too long
        scheme_labels = []
        for s in matched_schemes:
            nm = s.get('scheme_name') or s.get('scheme_id') or ''
            # shorten very long names to their ID for readability
            sid = s.get('scheme_id') or ''
            scheme_labels.append(sid.upper() if len(nm) > 30 else nm)
        scheme_str = ', '.join(scheme_labels[:5])

        # Facts about the person
        facts = []
        loc = user_data.get('location_type')
        housing = user_data.get('housing_type')
        income = user_data.get('monthly_household_income')
        if loc:    facts.append(f"{loc} area")
        if housing: facts.append(f"{housing} house")
        if income is not None: facts.append(f"income ₹{income}/month")
        fact_str = ', '.join(facts)

        if lang.startswith('hi'):
            name_part = f"मेरा नाम {name} है। " if name else ""
            summary = f"{name_part}{fact_str}। संभावित योजनाएं: {scheme_str}। कृपया आवेदन में मदद करें।"
        else:
            name_part = f"Name: {name}. " if name else ""
            summary = f"{name_part}{fact_str}. Likely qualifies for: {scheme_str}. Please help this person apply for the above schemes."

        return {
            'handoff_summary': summary.strip(),
            'schemes_to_apply': [s.get('scheme_name') or s.get('scheme_id') for s in matched_schemes],
            'csc_instruction': 'Please help this person apply for the above schemes.'
        }


if __name__ == '__main__':
    sample = [
        {'scheme_id': 'pmay_g', 'scheme_name': 'Pradhan Mantri Awas Yojana - Gramin'},
        {'scheme_id': 'pds',    'scheme_name': 'PDS / Ration Card'},
    ]
    user = {'location_type': 'rural', 'housing_type': 'kutcha', 'monthly_household_income': 8000, 'language': 'en'}
    print(json.dumps(generate_handoff(sample, user), ensure_ascii=False, indent=2))
