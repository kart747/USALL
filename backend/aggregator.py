import glob
import os
import re
from typing import Any, Dict, List

import yaml


def load_schemes(schemes_dir: str = None) -> List[Dict[str, Any]]:
    if schemes_dir is None:
        schemes_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schemes'))
    schemes = []
    for path in glob.glob(os.path.join(schemes_dir, '*.yaml')):
        with open(path, 'r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle)
            if data:
                schemes.append(data)
    return schemes


def _normalize_amount(raw: str) -> int:
    text = (raw or '').lower().replace(',', '')
    crore_match = re.search(r'₹?\s*([0-9]+(?:\.[0-9]+)?)\s*crore', text)
    lakh_match = re.search(r'₹?\s*([0-9]+(?:\.[0-9]+)?)\s*lakh', text)
    money_match = re.search(r'₹\s*([0-9]+(?:\.[0-9]+)?)', text)
    plain_match = re.search(r'([0-9]+(?:\.[0-9]+)?)', text)

    if crore_match:
        return int(float(crore_match.group(1)) * 10000000)
    if lakh_match:
        return int(float(lakh_match.group(1)) * 100000)
    if money_match:
        return int(float(money_match.group(1)))
    if plain_match:
        return int(float(plain_match.group(1)))
    return 0


def _benefit_text(scheme: Dict[str, Any]) -> str:
    return (scheme.get('benefit') or '').strip()


def _is_annual_cash(benefit_text: str) -> bool:
    text = benefit_text.lower()
    return any(token in text for token in ['per year', '/year', 'annual', 'annually', 'yearly']) and any(
        token in text for token in ['₹', 'cash', 'paid', 'installment', 'instalment', 'benefit', 'assistance']
    )


def _is_one_time(benefit_text: str) -> bool:
    text = benefit_text.lower()
    return any(token in text for token in ['one-time', 'one time', 'lump sum', 'construction', 'assistance']) and 'per year' not in text


def _is_recurring_in_kind(benefit_text: str) -> bool:
    text = benefit_text.lower()
    return any(token in text for token in ['cashless', 'ration', 'food grains', 'coverage', 'in-kind', 'subsidised', 'subsidized', 'monthly'])


def summarize_scheme_stacking(matched_schemes: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_schemes = load_schemes()
    by_id = {scheme.get('scheme_id'): scheme for scheme in all_schemes}

    total_annual_cash = 0
    total_one_time = 0
    recurring_benefits: List[str] = []

    for matched in matched_schemes:
        scheme = by_id.get(matched.get('scheme_id'))
        if not scheme:
            continue

        benefit = _benefit_text(scheme)
        amount = _normalize_amount(benefit)
        label = scheme.get('name') or scheme.get('scheme_id') or 'Unknown scheme'
        benefit_line = f'{label}: {benefit}'

        if _is_annual_cash(benefit):
            total_annual_cash += amount
        elif _is_one_time(benefit):
            total_one_time += amount
        elif _is_recurring_in_kind(benefit):
            recurring_benefits.append(benefit_line)
        elif benefit:
            recurring_benefits.append(benefit_line)

    return {
        'total_annual_cash': total_annual_cash,
        'total_one_time': total_one_time,
        'recurring_benefits': recurring_benefits,
    }
