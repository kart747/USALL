import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agents import eligibility_agent, document_agent, handoff_agent, fact_check_agent
from aggregator import summarize_scheme_stacking
from langdetect import detect


STATE_ALIASES = {
    'andhra pradesh': 'Andhra Pradesh', 'ap': 'Andhra Pradesh',
    'arunachal pradesh': 'Arunachal Pradesh', 'arunachal': 'Arunachal Pradesh',
    'assam': 'Assam',
    'bihar': 'Bihar',
    'chhattisgarh': 'Chhattisgarh', 'cg': 'Chhattisgarh',
    'goa': 'Goa',
    'gujarat': 'Gujarat', 'gj': 'Gujarat',
    'haryana': 'Haryana', 'hr': 'Haryana',
    'himachal pradesh': 'Himachal Pradesh', 'hp': 'Himachal Pradesh', 'himachal': 'Himachal Pradesh',
    'jharkhand': 'Jharkhand', 'jh': 'Jharkhand',
    'karnataka': 'Karnataka', 'ka': 'Karnataka', 'karnatka': 'Karnataka',
    'kerala': 'Kerala', 'kl': 'Kerala',
    'madhya pradesh': 'Madhya Pradesh', 'mp': 'Madhya Pradesh',
    'maharashtra': 'Maharashtra', 'mh': 'Maharashtra',
    'manipur': 'Manipur', 'mn': 'Manipur',
    'meghalaya': 'Meghalaya', 'ml': 'Meghalaya',
    'mizoram': 'Mizoram', 'mz': 'Mizoram',
    'nagaland': 'Nagaland', 'nl': 'Nagaland',
    'odisha': 'Odisha', 'orissa': 'Odisha', 'od': 'Odisha',
    'punjab': 'Punjab', 'pb': 'Punjab',
    'rajasthan': 'Rajasthan', 'rj': 'Rajasthan',
    'sikkim': 'Sikkim', 'sk': 'Sikkim',
    'tamil nadu': 'Tamil Nadu', 'tn': 'Tamil Nadu', 'tamilnadu': 'Tamil Nadu',
    'telangana': 'Telangana', 'ts': 'Telangana', 'tg': 'Telangana',
    'tripura': 'Tripura', 'tr': 'Tripura',
    'uttar pradesh': 'Uttar Pradesh', 'up': 'Uttar Pradesh',
    'uttarakhand': 'Uttarakhand', 'uk': 'Uttarakhand', 'uttaranchal': 'Uttarakhand',
    'west bengal': 'West Bengal', 'wb': 'West Bengal', 'bengal': 'West Bengal',
}

ENUM_VALIDATORS = {
    'gender': {'male', 'female', 'other'},
    'caste_category': {'sc', 'st', 'obc', 'general'},
    'location_type': {'rural', 'urban'},
    'employment_type': {'farmer', 'daily_wage', 'salaried', 'unemployed', 'government'},
    'housing_type': {'pucca', 'kutcha', 'homeless', 'one_room'},
    'vehicle_type': {'none', 'two_wheeler', 'four_wheeler'},
}

BOOLEAN_FIELDS = {'has_savings_bank_account', 'aadhaar_seeded_bank_account', 'willing_to_work'}

NUMERIC_FIELDS = {'age', 'monthly_household_income', 'land_holding_acres', 'land_irrigated_acres', 'kcc_limit', 'pension_monthly', 'previous_exam_marks_percent'}

INTAKE_QUESTIONS = [
    {'field': 'age', 'question': 'What is your age? (उम्र कितनी है?)'},
    {'field': 'gender', 'question': 'What is your gender? (Male / Female / Other)'},
    {'field': 'caste_category', 'question': 'Caste category? (SC / ST / OBC / General)'},
    {'field': 'state', 'question': 'Which state do you live in?'},
    {'field': 'location_type', 'question': 'Rural or Urban? (गाँव / शहर)'},
    {'field': 'monthly_household_income', 'question': 'What is your monthly household income (₹)?'},
    {'field': 'employment_type', 'question': 'Employment type? (farmer / daily_wage / salaried / unemployed / government)'},
    {'field': 'housing_type', 'question': 'Housing type? (pucca / kutcha / homeless)'},
    {'field': 'land_holding_acres', 'question': 'How many acres of land do you own? (0 if none)'},
    {'field': 'vehicle_type', 'question': 'Do you own a vehicle? (none / two_wheeler / four_wheeler)'},
    {'field': 'has_savings_bank_account', 'question': 'Do you have a savings bank account? (yes / no)'},
    {'field': 'aadhaar_seeded_bank_account', 'question': 'Is your bank account linked to Aadhaar? (yes / no / not_sure)'},
    {'field': 'willing_to_work', 'question': 'Are you willing to do manual labour work? (yes / no)'},
]


def normalize_state(raw: str) -> str:
    if not raw:
        return raw
    cleaned = raw.strip().lower()
    return STATE_ALIASES.get(cleaned, raw.strip())


def validate_enum(field: str, value: str) -> Optional[str]:
    allowed = ENUM_VALIDATORS.get(field)
    if allowed is None:
        return None
    normalized = value.strip().lower()
    if normalized in allowed:
        return normalized
    return None


def normalize_boolean(val: str) -> Any:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ('yes', 'true', '1', 'y', 'haan')
    return val


def validate_and_normalize(collected: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(collected)

    if 'state' in result and isinstance(result['state'], str):
        result['state'] = normalize_state(result['state'])

    for field, allowed in ENUM_VALIDATORS.items():
        if field in result and isinstance(result[field], str):
            normalized = result[field].strip().lower()
            if normalized in allowed:
                result[field] = normalized

    for field in BOOLEAN_FIELDS:
        if field in result:
            result[field] = normalize_boolean(result[field])

    for field in NUMERIC_FIELDS:
        if field in result and isinstance(result[field], str):
            try:
                val = result[field].strip()
                result[field] = int(val) if '.' not in val else float(val)
            except (ValueError, AttributeError):
                pass

    return result


class ChatRequest(BaseModel):
    session_id: str = None
    message: str = None
    collected: Dict[str, Any] = {}


class AnalyzeRequest(BaseModel):
    user_data: Dict[str, Any]


class FactCheckRequest(BaseModel):
    claim: str


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.post('/chat')
def chat(req: ChatRequest):
    collected = dict(req.collected or {})

    if req.message:
        try:
            lang = detect(req.message)
            collected.setdefault('language', 'hi' if lang == 'hi' else 'en')
        except Exception:
            collected.setdefault('language', 'en')

    collected = validate_and_normalize(collected)

    for q in INTAKE_QUESTIONS:
        field = q['field']
        val = collected.get(field)
        if val is None or val == '' or val is False:
            return {'next_question': q['question'], 'collected': collected}

    return {'action': 'analyze', 'collected': collected}


@app.post('/analyze')
def analyze(req: AnalyzeRequest):
    user_data = validate_and_normalize(req.user_data)

    if 'language' not in user_data:
        text = ' '.join([str(v) for v in user_data.values() if isinstance(v, (str, int))])
        try:
            lang = detect(text)
            user_data['language'] = 'hi' if lang == 'hi' else 'en'
        except Exception:
            user_data['language'] = 'en'

    try:
        eligibility = eligibility_agent.analyze_eligibility(user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Eligibility agent error: {e}')

    matched = eligibility.get('schemes', [])
    stacking_summary = summarize_scheme_stacking(matched)

    try:
        documents = document_agent.generate_documents(matched, user_data)
    except Exception:
        documents = {'documents': []}

    try:
        handoff = handoff_agent.generate_handoff(matched, user_data)
    except Exception:
        handoff = {'handoff_summary': '', 'schemes_to_apply': [], 'csc_instruction': ''}

    return {
        'eligibility': eligibility,
        'documents': documents,
        'handoff': handoff,
        'stacking_summary': stacking_summary,
    }


@app.post('/fact-check')
def fact_check(req: FactCheckRequest):
    try:
        return fact_check_agent.fact_check_claim(req.claim)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Fact check agent error: {e}')


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
