import os
import sys
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure backend root is importable
BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agents import eligibility_agent, document_agent, handoff_agent
from langdetect import detect


INTAKE_QUESTIONS = [
    {'field': 'age', 'question': 'What is your age? (उम्र कितनी है?)'},
    {'field': 'gender', 'question': 'What is your gender?'},
    {'field': 'caste_category', 'question': 'Caste category (SC/ST/OBC/General)?'},
    {'field': 'state', 'question': 'Which state do you live in?'},
    {'field': 'location_type', 'question': 'Rural or Urban?'},
    {'field': 'monthly_household_income', 'question': 'What is your monthly household income?'},
    {'field': 'employment_type', 'question': 'Employment type (farmer/daily_wage/salaried/unemployed)?'},
    {'field': 'housing_type', 'question': 'Housing type (pucca/kutcha/homeless)?'},
    {'field': 'land_holding_acres', 'question': 'How many acres of land do you own? (0 if none)'}
]


class ChatRequest(BaseModel):
    session_id: str = None
    message: str = None
    collected: Dict[str, Any] = {}


class AnalyzeRequest(BaseModel):
    user_data: Dict[str, Any]


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
    collected = req.collected or {}

    # detect language from message if available
    if req.message:
        try:
            lang = detect(req.message)
            collected.setdefault('language', 'hi' if lang == 'hi' else 'en')
        except Exception:
            collected.setdefault('language', 'en')

    # find next missing field
    for q in INTAKE_QUESTIONS:
        if q['field'] not in collected or collected.get(q['field']) in (None, ''):
            return {'next_question': q['question'], 'collected': collected}

    # all fields collected — trigger analysis
    return {'action': 'analyze', 'collected': collected}


@app.post('/analyze')
def analyze(req: AnalyzeRequest):
    user_data = req.user_data

    # language detection fallback
    if 'language' not in user_data:
        # try to detect from concatenated values
        text = ' '.join([str(v) for v in user_data.values() if isinstance(v, (str, int))])
        try:
            lang = detect(text)
            user_data['language'] = 'hi' if lang == 'hi' else 'en'
        except Exception:
            user_data['language'] = 'en'

    # Run eligibility agent
    try:
        eligibility = eligibility_agent.analyze_eligibility(user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Eligibility agent error: {e}')

    matched = eligibility.get('schemes', [])

    # Call document agent and handoff agent
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
        'handoff': handoff
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8000, reload=True)
