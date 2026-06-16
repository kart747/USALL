import os
import glob
import json
from typing import Any, Dict, List

import yaml
import requests


def load_schemes(schemes_dir: str = None) -> List[Dict[str, Any]]:
    if schemes_dir is None:
        schemes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'schemes'))
    pattern = os.path.join(schemes_dir, '*.yaml')
    files = glob.glob(pattern)
    schemes = []
    for p in files:
        with open(p, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data:
                schemes.append(data)
    return schemes


# Exact system prompt copied from the project plan
SYSTEM_PROMPT = """
You are YojanaPath's eligibility reasoning engine. Your job is to analyze a citizen's situation against Indian government scheme rules and output structured JSON.

STRICT RULES:
1. NEVER say a user "qualifies" — always say "likely qualifies", "possibly qualifies", or "unlikely to qualify"
2. ONLY reason from the scheme rules provided in the context. Never invent rules.
3. If a required field is missing, lower confidence and ask for it — do not assume.
4. Always output a visible reasoning chain showing exactly which user variable matched which rule.
5. For PMJAY: if user age >= 70, override ALL income and SECC criteria immediately.
6. Respond ONLY in valid JSON. No preamble, no markdown, no explanation outside the JSON.

OUTPUT FORMAT:
{
  "schemes": [
    {
      "scheme_id": "pmay_g",
      "scheme_name": "PM Awas Yojana - Gramin",
      "verdict": "likely_qualifies",
      "confidence_score": 92,
      "confidence_level": "HIGH",
      "reasoning_chain": [
        {
          "user_value": "Housing: Kutcha",
          "rule": "Must live in kutcha or have no house",
          "result": "pass",
          "explanation": "User lives in a mud house which meets the kutcha requirement"
        }
      ],
      "missing_fields": [],
      "next_step": "Visit your nearest CSC with Aadhaar card and a photo of your house"
    }
  ]
}
"""


def _prepare_user_message(user_data: Dict[str, Any], schemes: List[Dict[str, Any]]) -> str:
    payload = {
        'user_data': user_data,
        'schemes': schemes
    }
    return json.dumps(payload, ensure_ascii=False)


def _call_groq_system(system_prompt: str, user_message: str) -> str:
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        raise EnvironmentError('GROQ_API_KEY not set in environment')

    # Default base URL; allow override
    base = os.environ.get('GROQ_API_URL', 'https://api.groq.com/v1')
    url = f"{base}/llms/llama-3.1-8b-instant/completions"

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    body = {
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ],
        'max_tokens': 1500,
        'temperature': 0.0
    }

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    # Try to extract assistant content in common fields
    content = None
    # Groq/OpenAI-like response shapes
    if isinstance(data, dict):
        # choices -> message.content
        choices = data.get('choices') or []
        if choices and isinstance(choices, list):
            first = choices[0]
            # check nested
            if 'message' in first and isinstance(first['message'], dict):
                content = first['message'].get('content')
            else:
                content = first.get('text') or first.get('content')
        # fallback to top-level text
        if not content:
            content = data.get('text')

    if not content:
        raise ValueError('Unable to extract completion text from Groq response')

    return content


def _simple_local_rule_engine(user_data: Dict[str, Any], schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Minimal deterministic fallback so the agent can be tested without API key.
    results = []
    for s in schemes:
        sid = s.get('scheme_id')
        scheme_name = s.get('name')
        reqs = s.get('eligibility', {}).get('required', [])
        exs = s.get('eligibility', {}).get('exclusions', [])
        missing = []
        reasoning = []
        verdict = 'likely_qualifies'
        score = 75

        for r in reqs:
            field = r.get('field')
            if field not in user_data or user_data.get(field) is None:
                missing.append(field)
                reasoning.append({'user_value': None, 'rule': r.get('reason'), 'result': 'unknown', 'explanation': 'Required field missing'})
                verdict = 'possibly_qualifies'
                score = 50
            else:
                # naive pass
                reasoning.append({'user_value': f"{field}: {user_data.get(field)}", 'rule': r.get('reason'), 'result': 'pass', 'explanation': 'Local heuristic pass'})

        for e in exs:
            field = e.get('field')
            if field in user_data and user_data.get(field) is not None:
                val = user_data.get(field)
                # rough exclusion check for equality and contains
                op = e.get('operator')
                ex_val = e.get('value')
                excluded = False
                if op == 'equals' and val == ex_val:
                    excluded = True
                if op == 'contains' and isinstance(val, (list, str)) and ex_val in val:
                    excluded = True
                if op == 'greater_than' and isinstance(val, (int, float)) and val > ex_val:
                    excluded = True
                if excluded:
                    reasoning.append({'user_value': f"{field}: {val}", 'rule': e.get('reason'), 'result': 'fail', 'explanation': 'Local heuristic exclusion matched'})
                    verdict = 'unlikely_to_qualify'
                    score = 10

        results.append({
            'scheme_id': sid,
            'scheme_name': scheme_name,
            'verdict': verdict,
            'confidence_score': score,
            'reasoning_chain': reasoning,
            'missing_fields': missing,
            'next_step': s.get('application_route', {}).get('instruction')
        })

    return results


def analyze_eligibility(user_data: Dict[str, Any]) -> Dict[str, Any]:
    schemes = load_schemes()

    results: List[Dict[str, Any]] = []

    # Implement PMJAY age>=70 bypass in Python before sending to LLM
    try:
        age = int(user_data.get('age')) if 'age' in user_data and user_data.get('age') is not None else None
    except Exception:
        age = None

    schemes_for_llm = []
    for s in schemes:
        if s.get('scheme_id') == 'pmjay' and age is not None and age >= 70:
            # create bypassed result
            entry = {
                'scheme_id': 'pmjay',
                'scheme_name': s.get('name'),
                'verdict': 'likely_qualifies',
                'confidence_score': 98,
                'reasoning_chain': [
                    {
                        'user_value': f"age: {age}",
                        'rule': 'Age 70+ bypass',
                        'result': 'pass',
                        'explanation': 'Age >= 70 triggers PMJAY direct eligibility override'
                    }
                ],
                'missing_fields': [],
                'next_step': s.get('application_route', {}).get('instruction')
            }
            results.append(entry)
            # do not send PMJAY to LLM
        else:
            schemes_for_llm.append(s)

    # Build user message for LLM
    user_message = _prepare_user_message(user_data, schemes_for_llm)

    groq_api_key = os.environ.get('GROQ_API_KEY')
    if groq_api_key:
        try:
            completion_text = _call_groq_system(SYSTEM_PROMPT, user_message)
            # Expecting strict JSON output per system prompt
            parsed = json.loads(completion_text)
            llm_schemes = parsed.get('schemes', [])
            # Normalize to expected fields
            for s in llm_schemes:
                results.append({
                    'scheme_id': s.get('scheme_id'),
                    'scheme_name': s.get('scheme_name') or s.get('scheme_name'),
                    'verdict': s.get('verdict'),
                    'confidence_score': s.get('confidence_score') or s.get('confidence_level') or 0,
                    'reasoning_chain': s.get('reasoning_chain', []),
                    'missing_fields': s.get('missing_fields', []),
                    'next_step': s.get('next_step', '')
                })
        except Exception as e:
            # In case of API or parsing error, fall back to local heuristic
            fallback = _simple_local_rule_engine(user_data, schemes_for_llm)
            results.extend(fallback)
    else:
        # No API key — run local deterministic heuristic
        fallback = _simple_local_rule_engine(user_data, schemes_for_llm)
        results.extend(fallback)

    return {'schemes': results}


if __name__ == '__main__':
    # Simple local test run (does not require GROQ API key)
    sample_user = {
        'age': 42,
        'location_type': 'rural',
        'housing_type': 'kutcha',
        'monthly_household_income': 8000,
        'employment_type': 'daily_wage',
        'has_savings_bank_account': True,
        'aadhaar_seeded_bank_account': True,
        'vehicle_type': []
    }
    out = analyze_eligibility(sample_user)
    print(json.dumps(out, ensure_ascii=False, indent=2))
