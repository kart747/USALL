import os
import glob
import json
from typing import Any, Dict, List

import re
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


def _strip_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


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

    base = os.environ.get('GROQ_API_URL', 'https://api.groq.com')
    url = f"{base}/openai/v1/chat/completions"

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    body = {
        'model': 'llama-3.1-8b-instant',
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

    content = None
    if isinstance(data, dict):
        choices = data.get('choices') or []
        if choices and isinstance(choices, list):
            first = choices[0]
            if 'message' in first and isinstance(first['message'], dict):
                content = first['message'].get('content')
            else:
                content = first.get('text') or first.get('content')
        if not content:
            content = data.get('text')

    if not content:
        raise ValueError('Unable to extract completion text from Groq response')

    return content


def _check_condition(op: str, user_val: Any, expected: Any) -> str:
    if op == 'equals':
        if isinstance(expected, str) and isinstance(user_val, str):
            return 'pass' if user_val.strip().lower() == expected.strip().lower() else 'fail'
        return 'pass' if user_val == expected else 'fail'

    if op == 'in':
        if not isinstance(expected, list):
            return 'uncertain'
        normalized_expected = [str(v).strip().lower() for v in expected]
        normalized_val = str(user_val).strip().lower()
        return 'pass' if normalized_val in normalized_expected else 'fail'

    if op == 'greater_than':
        try:
            return 'pass' if float(user_val) > float(expected) else 'fail'
        except (ValueError, TypeError):
            return 'uncertain'

    if op == 'greater_than_or_equal':
        try:
            return 'pass' if float(user_val) >= float(expected) else 'fail'
        except (ValueError, TypeError):
            return 'uncertain'

    if op == 'less_than_or_equal':
        try:
            return 'pass' if float(user_val) <= float(expected) else 'fail'
        except (ValueError, TypeError):
            return 'uncertain'

    if op == 'contains':
        if isinstance(user_val, list):
            return 'pass' if expected in user_val else 'fail'
        if isinstance(user_val, str):
            return 'pass' if str(expected).lower() in user_val.lower() else 'fail'
        return 'uncertain'

    return 'uncertain'


def _eval_required_rule(rule: Dict[str, Any], user_val: Any) -> Dict[str, Any]:
    field = rule.get('field')
    reason_text = rule.get('reason', '')
    user_display = f"{field}: {user_val}" if user_val is not None else None

    if user_val is None:
        return {'user_value': user_display, 'rule': reason_text, 'result': 'uncertain', 'explanation': 'Required field not provided'}

    op = rule.get('operator')
    expected = rule.get('value')
    result = _check_condition(op, user_val, expected)

    if result == 'pass':
        return {'user_value': user_display, 'rule': reason_text, 'result': 'pass', 'explanation': 'Condition satisfied'}
    elif result == 'fail':
        return {'user_value': user_display, 'rule': reason_text, 'result': 'fail', 'explanation': f'Expected {expected}, got {user_val}'}
    else:
        return {'user_value': user_display, 'rule': reason_text, 'result': 'uncertain', 'explanation': f'Could not evaluate rule ({op}) for value {user_val}'}


def _eval_exclusion_rule(rule: Dict[str, Any], user_val: Any) -> Dict[str, Any] or None:
    if user_val is None:
        return None

    field = rule.get('field')
    reason_text = rule.get('reason', '')
    user_display = f"{field}: {user_val}"
    op = rule.get('operator')
    expected = rule.get('value')
    result = _check_condition(op, user_val, expected)

    if result == 'pass':
        return {'user_value': user_display, 'rule': reason_text, 'result': 'fail', 'explanation': f'Exclusion triggered: {user_val} matches {expected}'}
    if result == 'fail':
        return None
    return None


def _eval_any_of_rule(rule: Dict[str, Any], user_val: Any) -> Dict[str, Any] or None:
    field = rule.get('field')
    reason_text = rule.get('reason', '')
    user_display = f"{field}: {user_val}" if user_val is not None else None

    if user_val is None:
        return None

    op = rule.get('operator')
    expected = rule.get('value')
    result = _check_condition(op, user_val, expected)

    if result == 'pass':
        return {'user_value': user_display, 'rule': reason_text, 'result': 'pass', 'explanation': 'Condition met for any_of rule'}
    return None


def _confidence_level_to_score(level: str) -> int:
    mapping = {
        'high': 92,
        'medium': 65,
        'uncertain': 35,
        'not_eligible': 0,
    }
    return mapping.get(level, 35)


def compute_confidence(reasoning_steps: list) -> str:
    if not reasoning_steps:
        return "uncertain"
    if any(s["result"] == "fail" for s in reasoning_steps):
        return "not_eligible"
    uncertain_count = sum(1 for s in reasoning_steps if s["result"] == "uncertain")
    if uncertain_count == 0:
        return "high"
    elif uncertain_count == 1:
        return "medium"
    else:
        return "uncertain"


def _make_scheme_entry(scheme_data: Dict, sid: str, verdict: str, confidence_level: str, reasoning: list, missing: list, next_step: str) -> Dict:
    return {
        'scheme_id': sid,
        'scheme_name': scheme_data.get('name'),
        'verdict': verdict,
        'confidence_level': confidence_level.upper(),
        'confidence_score': _confidence_level_to_score(confidence_level),
        'reasoning_chain': reasoning,
        'missing_fields': missing,
        'next_step': next_step,
    }


def _simple_local_rule_engine(user_data: Dict[str, Any], schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results = []
    for s in schemes:
        sid = s.get('scheme_id')
        scheme_name = s.get('name')
        elig = s.get('eligibility', {})
        reqs = elig.get('required', [])
        exs = elig.get('exclusions', [])
        any_of = elig.get('any_of', [])
        missing = []
        reasoning = []
        verdict = 'likely_qualifies'

        for r in reqs:
            field = r.get('field')
            user_val = user_data.get(field)
            step = _eval_required_rule(r, user_val)
            if step['result'] == 'uncertain':
                missing.append(field)
                verdict = 'possibly_qualifies'
            elif step['result'] == 'fail':
                verdict = 'unlikely_to_qualify'
            reasoning.append(step)

        any_of_met = False
        any_of_uncertain = False
        for r in any_of:
            field = r.get('field')
            user_val = user_data.get(field)
            step = _eval_any_of_rule(r, user_val)
            if step is not None:
                if step['result'] == 'pass':
                    any_of_met = True
                reasoning.append(step)
            elif user_val is not None:
                reasoning.append({
                    'user_value': f"{field}: {user_val}",
                    'rule': r.get('reason', ''),
                    'result': 'uncertain',
                    'explanation': f'Field present but could not verify condition'
                })
                any_of_uncertain = True

        if any_of and not any_of_met:
            if any_of_uncertain:
                if verdict not in ('unlikely_to_qualify',):
                    verdict = 'possibly_qualifies'
            else:
                if verdict not in ('unlikely_to_qualify',):
                    verdict = 'unlikely_to_qualify'

        for e in exs:
            field = e.get('field')
            user_val = user_data.get(field)
            step = _eval_exclusion_rule(e, user_val)
            if step is not None:
                reasoning.append(step)
                verdict = 'unlikely_to_qualify'

        results.append(_make_scheme_entry(
            s, sid, verdict, compute_confidence(reasoning),
            reasoning, missing, s.get('application_route', {}).get('instruction', '')
        ))

    return results


def _handle_pm_kisan(user_data: Dict[str, Any], scheme_data: Dict) -> Dict:
    is_govt = bool(user_data.get('is_government_employee', False))
    emp = str(user_data.get('employment_type') or '').lower()
    annual_income = user_data.get('annual_income') or 0
    monthly_income = user_data.get('monthly_household_income') or 0
    effective_annual = annual_income if annual_income else monthly_income * 12
    land = user_data.get('land_holding_acres')
    profession = str(user_data.get('profession') or '').lower()

    steps = []
    verdict = 'likely_qualifies'

    if land is None:
        steps.append({
            'user_value': None,
            'rule': 'Scheme targets landholding farmer families',
            'result': 'uncertain',
            'explanation': 'land_holding_acres not provided'
        })
        verdict = 'possibly_qualifies'
    elif float(land) < 0.01:
        explanation = 'No land holding — user does not meet the landholding requirement'
        if emp == 'farmer':
            explanation += ' (employment_type is farmer but land_holding_acres is 0 — possible data mismatch)'
        steps.append({
            'user_value': f"land_holding_acres: {land}",
            'rule': 'Scheme targets landholding farmer families',
            'result': 'fail',
            'explanation': explanation
        })
        verdict = 'unlikely_to_qualify'
    else:
        steps.append({
            'user_value': f"land_holding_acres: {land}",
            'rule': 'Scheme targets landholding farmer families',
            'result': 'pass',
            'explanation': f'Land holding {land} acres meets the ≥0.01 acre requirement'
        })

    if is_govt or emp in ('government', 'govt', 'salaried_govt'):
        steps.append({
            'user_value': f"is_government_employee: {is_govt}, employment_type: {emp}",
            'rule': 'Government employees are excluded from PM-KISAN',
            'result': 'fail',
            'explanation': 'is_government_employee=True or employment maps to government service'
        })
        verdict = 'unlikely_to_qualify'

    if verdict != 'unlikely_to_qualify' and effective_annual > 250000:
        steps.append({
            'user_value': f"annual_income: ₹{effective_annual:,}",
            'rule': 'Income tax payers / high-income individuals are excluded from PM-KISAN',
            'result': 'fail',
            'explanation': f'Annual income ₹{effective_annual:,} exceeds ₹2,50,000 — likely income-tax payer'
        })
        verdict = 'unlikely_to_qualify'

    if profession in ('doctor', 'lawyer', 'chartered_accountant', 'ca'):
        steps.append({
            'user_value': f"profession: {profession}",
            'rule': 'Professionals (doctors/lawyers/CAs) are excluded from PM-KISAN',
            'result': 'fail',
            'explanation': f'Profession {profession} is in the exclusion list'
        })
        verdict = 'unlikely_to_qualify'

    conf_level = compute_confidence(steps)
    return _make_scheme_entry(
        scheme_data, 'pm_kisan', verdict, conf_level,
        steps, [] if land is not None else ['land_holding_acres'],
        scheme_data.get('application_route', {}).get('instruction', '')
    )


def _handle_pmjay_bypass(age: int, scheme_data: Dict) -> Dict:
    steps = [
        {
            'user_value': f"age: {age}",
            'rule': 'Age 70+ bypass',
            'result': 'pass',
            'explanation': 'Age >= 70 triggers PMJAY direct eligibility override (Sept 2024 update)'
        }
    ]
    return _make_scheme_entry(
        scheme_data, 'pmjay', 'likely_qualifies', 'high',
        steps, [],
        scheme_data.get('application_route', {}).get('instruction', '')
    )


def analyze_eligibility(user_data: Dict[str, Any]) -> Dict[str, Any]:
    schemes = load_schemes()
    results: List[Dict[str, Any]] = []

    try:
        age = int(user_data.get('age')) if 'age' in user_data and user_data.get('age') is not None else None
    except Exception:
        age = None

    schemes_for_llm = []
    for s in schemes:
        sid = s.get('scheme_id')
        if sid == 'pmjay' and age is not None and age >= 70:
            results.append(_handle_pmjay_bypass(age, s))
        elif sid == 'pm_kisan':
            results.append(_handle_pm_kisan(user_data, s))
        else:
            schemes_for_llm.append(s)

    user_message = _prepare_user_message(user_data, schemes_for_llm)

    groq_api_key = os.environ.get('GROQ_API_KEY')
    if groq_api_key:
        try:
            completion_text = _call_groq_system(SYSTEM_PROMPT, user_message)
            parsed = json.loads(_strip_markdown(completion_text))
            llm_schemes = parsed.get('schemes', [])
            for s in llm_schemes:
                chain = s.get('reasoning_chain', [])
                normalised_chain = [
                    {**step, 'result': step.get('result') if step.get('result') in ('pass', 'fail', 'uncertain') else 'uncertain'}
                    for step in chain
                ]
                conf_level = compute_confidence(normalised_chain)
                sid = s.get('scheme_id')
                scheme_data = None
                for sc in schemes:
                    if sc.get('scheme_id') == sid:
                        scheme_data = sc
                        break
                entry = _make_scheme_entry(
                    scheme_data or {}, sid,
                    s.get('verdict'), conf_level, chain,
                    s.get('missing_fields', []), s.get('next_step', '')
                )
                results.append(entry)
        except Exception:
            fallback = _simple_local_rule_engine(user_data, schemes_for_llm)
            results.extend(fallback)
    else:
        fallback = _simple_local_rule_engine(user_data, schemes_for_llm)
        results.extend(fallback)

    return {'schemes': results}


if __name__ == '__main__':
    sample_user = {
        'age': 30,
        'gender': 'male',
        'caste_category': 'sc',
        'state': 'Karnataka',
        'location_type': 'rural',
        'monthly_household_income': 8000,
        'employment_type': 'farmer',
        'housing_type': 'kutcha',
        'land_holding_acres': 2,
        'vehicle_type': 'none',
        'has_savings_bank_account': True,
        'aadhaar_seeded_bank_account': True,
        'willing_to_work': True,
    }
    out = analyze_eligibility(sample_user)
    for s in out['schemes']:
        print(f"{s['scheme_id']:12s} → {s['verdict']:24s} ({s['confidence_level']:12s} score={s['confidence_score']})")
    print()
    matched = [s for s in out['schemes'] if s['verdict'] in ('likely_qualifies', 'possibly_qualifies')]
    print(f"Total matched: {len(matched)}/{len(out['schemes'])}")
