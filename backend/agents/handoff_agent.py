import os
import json
from typing import Any, Dict, List

import requests
from textwrap import shorten


# System prompt from project plan
SYSTEM_PROMPT = """
You are YojanaPath's CSC handoff generator. Generate a short, plain-language summary the user can show or read to the VLE operator at their nearest Common Service Centre.

RULES:
1. Keep it under 100 words
2. Use simple language — assume the reader has low literacy
3. Include: user's name (if given), schemes they likely qualify for, key facts supporting eligibility
4. Output in Hindi if user language is Hindi
5. End with: "Please help this person apply for the above schemes."
6. Respond ONLY in valid JSON.

OUTPUT FORMAT:
{
  "handoff_summary": "...",
  "schemes_to_apply": ["PMAY-G", "MGNREGA"],
  "csc_instruction": "Please help this person apply for the above schemes."
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
        content = _call_groq(SYSTEM_PROMPT, user_message)
        parsed = json.loads(content)
        return parsed
    except Exception:
        # fallback: generate a concise summary
        name = user_data.get('name') or ''
        lang = user_data.get('language') or user_data.get('lang') or 'en'
        scheme_names = [s.get('scheme_name') or s.get('scheme_id') for s in matched_schemes]
        scheme_short = ', '.join(scheme_names[:5])
        facts = []
        if user_data.get('location_type'):
            facts.append(user_data.get('location_type'))
        if user_data.get('housing_type'):
            facts.append(user_data.get('housing_type'))
        if user_data.get('monthly_household_income') is not None:
            facts.append(f"income ₹{user_data.get('monthly_household_income')}")

        fact_str = ', '.join(facts)
        if lang.lower().startswith('hi'):
            summary = f"Mera naam {name}. {fact_str}. Sambhavtah yeh: {scheme_short}. Kripya inmein madad karein."
        else:
            summary = f"My name {name}. {fact_str}. Likely: {scheme_short}. Please help apply."

        # Ensure under 100 words
        summary = shorten(summary, width=500, placeholder='')

        return {
            'handoff_summary': summary.strip(),
            'schemes_to_apply': scheme_names,
            'csc_instruction': 'Please help this person apply for the above schemes.'
        }


if __name__ == '__main__':
    sample = [{'scheme_id': 'pmay_g', 'scheme_name': 'PMAY-G'}]
    user = {'name': 'Ramesh', 'location_type': 'rural', 'housing_type': 'kutcha', 'monthly_household_income': 8000, 'language': 'en'}
    print(json.dumps(generate_handoff(sample, user), ensure_ascii=False, indent=2))
