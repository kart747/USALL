import glob
import json
import os
import re
from typing import Any, Dict, List

import requests
import yaml

try:
    from langdetect import detect
except Exception:  # pragma: no cover - langdetect is available in normal runs
    detect = None


def load_schemes(schemes_dir: str = None) -> List[Dict[str, Any]]:
    if schemes_dir is None:
        schemes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'schemes'))
    pattern = os.path.join(schemes_dir, '*.yaml')
    files = glob.glob(pattern)
    schemes = []
    for path in files:
        with open(path, 'r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle)
            if data:
                schemes.append(data)
    return schemes


SYSTEM_PROMPT = """
You are YojanaPath's misinformation fact-checking engine.

STRICT RULES:
1. Use ONLY the facts present in the provided scheme YAML data.
2. Never invent scheme status, suspension, new rules, or policy changes.
3. If the claim refers to something not explicitly supported by the YAML facts, return UNVERIFIED.
4. If the claim mixes a supported fact with an unsupported status claim, use PARTIALLY_TRUE only when the supported part is clear.
5. Respond only in valid JSON with the exact schema below.
6. If language is hi, write the explanation in Hindi.

OUTPUT FORMAT:
{
  "claim": "...",
  "verdict": "TRUE" | "FALSE" | "PARTIALLY_TRUE" | "UNVERIFIED",
  "explanation": "...",
  "source_scheme": "...",
  "language": "hi" | "en"
}
"""


def _strip_markdown(text: str) -> str:
    text = text.strip()
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
        'max_tokens': 600,
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


def _detect_language(text: str) -> str:
    if not text:
        return 'en'
    if detect is None:
        return 'en'
    try:
        lang = detect(text)
        return 'hi' if lang == 'hi' else 'en'
    except Exception:
        return 'en'


def _normalize(text: str) -> str:
    text = text or ''
    text = text.lower()
    text = text.replace('-', ' ')
    text = re.sub(r'[^\w\s₹/,.+%-]', ' ', text, flags=re.UNICODE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _extract_amounts(text: str) -> List[str]:
    values = []
    for token in re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?', text or ''):
        values.append(token.replace(',', ''))
    return values


def _scheme_label(scheme: Dict[str, Any]) -> str:
    scheme_id = scheme.get('scheme_id') or ''
    if scheme_id:
        return scheme_id.replace('_', '-').upper()
    return scheme.get('name') or ''


def _benefit_mismatch_explanation(scheme: Dict[str, Any], claimed_amounts: List[str], language: str) -> str:
    label = _scheme_label(scheme)
    benefit = (scheme.get('benefit') or '').strip()
    if claimed_amounts:
        claim_text = ', '.join(f'₹{amount}' for amount in claimed_amounts)
    else:
        claim_text = ''

    if language == 'hi':
        if claim_text:
            return f'{label} वास्तव में {benefit} प्रदान करता है, न कि {claim_text} जैसा दावा किया गया है।'
        return f'{label} वास्तव में {benefit} प्रदान करता है।'

    if claim_text:
        return f'{label} actually provides {benefit}, not {claim_text} as claimed.'
    return f'{label} actually provides {benefit}.'


def _scheme_aliases(scheme: Dict[str, Any]) -> List[str]:
    aliases = []
    for value in [scheme.get('scheme_id'), scheme.get('name'), scheme.get('name_hindi')]:
        if value:
            aliases.append(_normalize(str(value)))
    scheme_id = scheme.get('scheme_id') or ''
    if scheme_id:
        aliases.append(_normalize(scheme_id.replace('_', ' ')))
        aliases.append(_normalize(scheme_id.replace('_', '-')))
        aliases.append(_normalize(scheme_id.upper()))
    return list(dict.fromkeys([alias for alias in aliases if alias]))


def _select_candidate_schemes(claim: str, schemes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm_claim = _normalize(claim)
    exact_matches = []
    for scheme in schemes:
        aliases = _scheme_aliases(scheme)
        if any(alias in norm_claim for alias in aliases):
            exact_matches.append(scheme)

    if exact_matches:
        return exact_matches[:3]

    keyword_map = {
        'pm_kisan': ['kisan', 'farmer', 'landholding', 'pm kisan', 'किसान'],
        'pmay_g': ['awas', 'housing', 'house', 'kutcha', 'pucca', 'pmay', 'आवास', 'घर'],
        'pmjay': ['ayushman', 'health', 'hospital', 'secc', 'pm jay', 'pmjay', 'आयुष्मान'],
        'pds': ['ration', 'nfsa', 'pds', 'food grain', 'राशन', 'अनाज'],
        'mgnrega': ['mgnrega', 'nrega', 'job card', 'wage', 'मनरेगा', 'काम'],
        'pmsby': ['accident', 'personal accident', 'insurance', 'बीमा'],
        'pmjjby': ['life insurance', 'death', 'insurance', 'जीवन बीमा'],
        'nsp': ['scholarship', 'education', 'student', 'छात्रवृत्ति'],
    }
    scored = []
    for scheme in schemes:
        sid = (scheme.get('scheme_id') or '').lower()
        score = 0
        if sid in keyword_map:
            for keyword in keyword_map[sid]:
                if keyword in norm_claim:
                    score += 2
        if any(alias in norm_claim for alias in _scheme_aliases(scheme)):
            score += 3
        if score:
            scored.append((score, scheme))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [scheme for _, scheme in scored[:2]]


def _scheme_facts(scheme: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'scheme_id': scheme.get('scheme_id'),
        'name': scheme.get('name'),
        'name_hindi': scheme.get('name_hindi'),
        'benefit': scheme.get('benefit'),
        'ministry': scheme.get('ministry'),
        'last_updated': scheme.get('last_updated'),
        'eligibility': scheme.get('eligibility', {}),
        'documents_required': scheme.get('documents_required', []),
        'application_route': scheme.get('application_route', {}),
        'special_override': scheme.get('special_override', []),
        'human_in_loop_trigger': scheme.get('human_in_loop_trigger', []),
    }


def _local_verdict(claim: str, language: str, schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
    norm_claim = _normalize(claim)
    status_words = ['band', 'stopped', 'closed', 'shut', 'cancelled', 'cancel', 'changed', 'new rule', 'new rules', 'new update', 'banda', 'बंद', 'बदल', 'नई']
    claim_amounts = _extract_amounts(claim)

    if not schemes:
        explanation = 'This claim cannot be verified from the current scheme YAML files.'
        if language == 'hi':
            explanation = 'यह दावा मौजूदा योजना YAML फाइलों से सत्यापित नहीं किया जा सकता।'
        return {
            'claim': claim,
            'verdict': 'UNVERIFIED',
            'explanation': explanation,
            'source_scheme': '',
            'language': language,
        }

    scheme = schemes[0]
    facts = _scheme_facts(scheme)
    source_scheme = facts.get('name') or facts.get('scheme_id') or ''

    benefit = _normalize(str(facts.get('benefit') or ''))
    eligibility_text = _normalize(json.dumps(facts.get('eligibility', {}), ensure_ascii=False))
    override_text = _normalize(json.dumps(facts.get('special_override', []), ensure_ascii=False))
    route_text = _normalize(json.dumps(facts.get('application_route', {}), ensure_ascii=False))
    documents_text = _normalize(json.dumps(facts.get('documents_required', []), ensure_ascii=False))
    fact_blob = ' '.join([benefit, eligibility_text, override_text, route_text, documents_text])

    if any(word in norm_claim for word in status_words) and not any(token in fact_blob for token in ['bypass', 'age 70', 'last_updated', 'benefit', 'eligibility']):
        explanation = 'The claim talks about a scheme being stopped or changed, but the YAML files do not contain that status fact.'
        if language == 'hi':
            explanation = 'दावा योजना के बंद या बदले जाने के बारे में है, लेकिन YAML फाइलों में ऐसा कोई तथ्य नहीं है।'
        return {
            'claim': claim,
            'verdict': 'UNVERIFIED',
            'explanation': explanation,
            'source_scheme': source_scheme,
            'language': language,
        }

    if claim_amounts and facts.get('benefit'):
        benefit_amounts = _extract_amounts(str(facts.get('benefit')))
        if any(amount in benefit_amounts for amount in claim_amounts):
            explanation = 'The benefit amount in the claim matches the scheme YAML.'
            if language == 'hi':
                explanation = 'दावे में बताया गया लाभ-राशि योजना YAML से मेल खाती है।'
            return {
                'claim': claim,
                'verdict': 'TRUE',
                'explanation': explanation,
                'source_scheme': source_scheme,
                'language': language,
            }
        explanation = _benefit_mismatch_explanation(facts, claim_amounts, language)
        claim_amount_set = set(claim_amounts)
        verdict = 'FALSE' if claim_amount_set.isdisjoint(benefit_amounts) else 'PARTIALLY_TRUE'
        return {
            'claim': claim,
            'verdict': verdict,
            'explanation': explanation,
            'source_scheme': source_scheme,
            'language': language,
        }

    if any(token in fact_blob for token in ['age 70', '70+']) and '70' in norm_claim:
        explanation = 'The claim matches the age-based override described in the YAML.'
        if language == 'hi':
            explanation = 'दावा YAML में दिए गए आयु-आधारित override से मेल खाता है।'
        return {
            'claim': claim,
            'verdict': 'TRUE',
            'explanation': explanation,
            'source_scheme': source_scheme,
            'language': language,
        }

    if 'not eligible' in norm_claim or 'not qualify' in norm_claim:
        explanation = 'The claim cannot be confirmed from the current scheme facts.'
        if language == 'hi':
            explanation = 'दावे को मौजूदा योजना तथ्यों से पुष्ट नहीं किया जा सकता।'
        return {
            'claim': claim,
            'verdict': 'UNVERIFIED',
            'explanation': explanation,
            'source_scheme': source_scheme,
            'language': language,
        }

    explanation = 'The claim could not be checked from the available scheme facts.'
    if language == 'hi':
        explanation = 'दावे को उपलब्ध योजना तथ्यों से जांचा नहीं जा सका।'
    return {
        'claim': claim,
        'verdict': 'UNVERIFIED',
        'explanation': explanation,
        'source_scheme': source_scheme,
        'language': language,
    }


def fact_check_claim(claim: str) -> Dict[str, Any]:
    schemes = load_schemes()
    language = _detect_language(claim)
    candidates = _select_candidate_schemes(claim, schemes)

    if not candidates:
        return _local_verdict(claim, language, candidates)

    candidate_payload = [_scheme_facts(scheme) for scheme in candidates]
    user_message = json.dumps(
        {
            'claim': claim,
            'language': language,
            'candidate_schemes': candidate_payload,
        },
        ensure_ascii=False,
    )

    try:
        completion_text = _call_groq(SYSTEM_PROMPT, user_message)
        parsed = json.loads(_strip_markdown(completion_text))
        verdict = parsed.get('verdict', 'UNVERIFIED')
        if verdict not in {'TRUE', 'FALSE', 'PARTIALLY_TRUE', 'UNVERIFIED'}:
            verdict = 'UNVERIFIED'

        source_scheme = parsed.get('source_scheme') or (candidates[0].get('name') or candidates[0].get('scheme_id') or '')
        top_scheme = candidates[0]
        top_facts = _scheme_facts(top_scheme)
        claim_amounts = set(_extract_amounts(claim))
        benefit_amounts = set(_extract_amounts(str(top_facts.get('benefit') or '')))
        status_rumor = any(word in _normalize(claim) for word in ['band', 'stopped', 'closed', 'shut', 'cancelled', 'cancel', 'changed', 'new rule', 'new rules', 'new update', 'banda', 'बंद', 'बदल', 'नई'])
        explanation = parsed.get('explanation') or ''
        if status_rumor and not any(token in _normalize(json.dumps(top_facts, ensure_ascii=False)) for token in ['bypass', 'age 70', '70+']):
            verdict = 'UNVERIFIED'
            if language == 'hi':
                explanation = 'दावा योजना के बंद या बदले जाने के बारे में है, लेकिन YAML फाइलों में ऐसा कोई तथ्य नहीं है।'
            else:
                explanation = 'The claim talks about a scheme being stopped or changed, but the YAML files do not contain that status fact.'
        elif claim_amounts and benefit_amounts:
            if claim_amounts.issubset(benefit_amounts):
                verdict = 'TRUE'
                if language == 'hi':
                    explanation = 'दावे में बताया गया लाभ-राशि योजना YAML से मेल खाती है।'
                else:
                    explanation = 'The benefit amount in the claim matches the scheme YAML.'
            elif claim_amounts.isdisjoint(benefit_amounts):
                verdict = 'FALSE'
                explanation = _benefit_mismatch_explanation(top_facts, list(claim_amounts), language)
            else:
                verdict = 'PARTIALLY_TRUE'
                explanation = _benefit_mismatch_explanation(top_facts, list(claim_amounts), language)
        if not explanation:
            explanation = 'The claim could not be checked from the available scheme facts.'
            if language == 'hi':
                explanation = 'दावे को उपलब्ध योजना तथ्यों से जांचा नहीं जा सका।'

        return {
            'claim': claim,
            'verdict': verdict,
            'explanation': explanation,
            'source_scheme': source_scheme,
            'language': parsed.get('language') if parsed.get('language') in {'hi', 'en'} else language,
        }
    except Exception:
        return _local_verdict(claim, language, candidates)


if __name__ == '__main__':
    sample_claim = 'PM-KISAN band ho gaya hai'
    print(json.dumps(fact_check_claim(sample_claim), ensure_ascii=False, indent=2))