# YojanaPath — India Benefits Navigator
## USAII Global AI Hackathon 2026 | Brief 4 | Team sizeof(int)

---

## One-Line Pitch
An AI-powered benefits navigator that takes a rural Indian's real situation, tells them exactly which government schemes they qualify for, shows the reasoning behind every decision, and tells them exactly where to go next — in plain language, in their language.

---

## The Problem Statement (for Devpost)
> "500 million Indians are eligible for government welfare schemes they never claim — not because they don't want help, but because the system is impossible to navigate. Ramesh, a 42-year-old daily wage laborer in UP, knows the government gives 'ration' and 'housing money' — but the exact scheme names, income thresholds, and documents required are completely hidden behind bureaucratic opacity. When he visits a block office, he loses a full day's wages only to be turned away for a missing document nobody told him about. YojanaPath fixes that."

---

## User Persona: Ramesh

- **Age:** 42
- **Location:** Semi-urban periphery, Tier-3 district, Uttar Pradesh
- **Occupation:** Daily wage laborer (construction + seasonal agriculture)
- **Income:** ~₹8,000/month
- **Housing:** Kutcha (mud) house
- **Family:** Wife + 3 children (2 in government school)
- **Tech:** Low-cost Android phone, uses WhatsApp, struggles with English text
- **Pain point:** Loses a full day's wages visiting block offices, gets turned away for missing documents

Every feature must answer: *Does this help Ramesh get his next step faster and with more confidence?*

---

## What the System Does — Layer by Layer

### Layer 1: Conversational Intake (5-7 questions)
Not a form. A short guided conversation in Hindi or English.

Questions collected:
- Age, gender, caste category (SC/ST/OBC/General)
- State + rural/urban
- Monthly household income
- Employment type (farmer/daily wage/salaried/unemployed)
- Housing type (pucca/kutcha/homeless)
- Land ownership (acres, irrigated/unirrigated)
- Number of dependents + children's ages/school enrollment
- Existing assets (vehicle type, KCC limit)
- Bank account status (Aadhaar-seeded or not)

### Layer 2: Eligibility Reasoning Engine (Main Differentiator)
Three agents working in sequence:

**EligibilityAgent** → Runs structured reasoning against YAML knowledge base
**DocumentAgent** → Generates exact document checklist per matched scheme
**HandoffAgent** → Routes user to nearest CSC with pre-written summary

The LLM receives user data + scheme rules and outputs:
1. Likely eligibility with confidence score (High/Medium/Low + %)
2. Visible reasoning chain — exact variable-to-rule mapping
3. What's missing that could change the answer

### Layer 3: Visible Reasoning Chain (Judge-facing differentiator)

```
Your Situation          Rule                         Result
──────────────────────────────────────────────────────────────────
Monthly income ₹8,000 → PMAY-G limit: ₹15,000/mo  → ✓ Under limit
Housing: Kutcha       → Requires kutcha/homeless     → ✓ Qualifies
No 4-wheeler          → Exclusion: motorized 4W      → ✓ No barrier
No govt. employee     → Exclusion: govt. salary       → ✓ No barrier

Confidence: HIGH (92%)
```

### Layer 4: Actionable Output
For each matched scheme:
- Scheme name in plain Hindi/English
- One sentence on what it provides
- Confidence level + reason
- Exact documents to bring
- Where to go (nearest CSC, not a government portal homepage)
- Estimated timeline

### Layer 5: CSC Handoff (Human-in-the-Loop)
When confidence is low OR Aadhaar verification is needed:
> "This needs Aadhaar verification at a Common Service Centre. Here's what to tell the VLE operator: [pre-written summary]. Bring: Aadhaar card, bank passbook, photo of your house."

The AI never confirms final eligibility. A CSC VLE does.

### Layer 6: Multilingual Support
Hindi toggle built in. Groq handles translation. Costs nothing extra. Judges notice immediately.

---

## Schemes Knowledge Base (8 Core Schemes)

### 1. PM-KISAN
- Benefit: ₹6,000/year (3 installments of ₹2,000)
- Target: Landholding farmer families
- Key exclusions: Income tax payers, govt employees (except Class IV), pensioners >₹10,000/mo, professionals (doctors/lawyers/CAs)
- Watch out: Farmer ID (Kisan Pehchaan Patra) mandatory in 14 states now

### 2. PMJAY (Ayushman Bharat)
- Benefit: ₹5,00,000/family/year cashless hospitalization
- Target: SECC 2011 deprivation criteria OR age 70+ (new Sept 2024 update)
- **Critical:** Age 70+ bypasses ALL income criteria — build this into logic tree

### 3. PDS (Ration Card / NFSA)
- Benefit: 5kg food grains/person/month (PHH) or 35kg/family (AAY)
- State-specific rules — scope to Karnataka/UP for MVP
- Exclusions: 4-wheeler owner, govt employee, income >₹10,000/mo rural

### 4. MGNREGA
- Benefit: 100 days guaranteed unskilled labor/year
- Target: ANY rural resident 18+ willing to do manual work
- Focus: Procedural guidance (Job Card at Gram Panchayat) not eligibility filtering
- Rights: Employment within 15 days or unemployment allowance kicks in

### 5. PMAY-G (Rural Housing)
- Benefit: ₹1.20 lakh (plain) / ₹1.30 lakh (hilly/tribal)
- Aug 2024 update: 2-wheeler, fridge, fishing boat no longer exclusions
- Still excluded: 4-wheeler, KCC >₹50,000, govt employee, >2.5 acres irrigated land

### 6. NSP Scholarships
- Income ceiling: ₹1-2.5 lakh (minority/SC/ST), up to ₹8 lakh (OBC/EBC top class)
- Prerequisite: 50% marks in previous exam
- Mandatory: Aadhaar-seeded bank account

### 7. PMJJBY (Life Insurance)
- Benefit: ₹2 lakh on death (any cause)
- Eligibility: Age 18-50, savings bank account
- Premium: ₹436/year auto-debit

### 8. PMSBY (Accident Insurance)
- Benefit: ₹2 lakh accidental death/total disability, ₹1 lakh partial disability
- Eligibility: Age 18-70, savings bank account
- Premium: ₹20/year auto-debit

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React (plain, no Next.js, no TypeScript) |
| Backend | Python FastAPI |
| LLM | Groq API — llama-3.1-8b-instant |
| Knowledge base | YAML files, manually curated |
| Language detection | langdetect Python library |
| State | In-memory only, no database |
| Styling | Plain CSS |

---

## Project Structure

```
yojanapath/
├── backend/
│   ├── main.py              # FastAPI endpoints
│   ├── schemes/
│   │   ├── pm_kisan.yaml
│   │   ├── pmjay.yaml
│   │   ├── pds.yaml
│   │   ├── mgnrega.yaml
│   │   ├── pmay_g.yaml
│   │   ├── nsp.yaml
│   │   ├── pmjjby.yaml
│   │   └── pmsby.yaml
│   ├── agents/
│   │   ├── eligibility_agent.py
│   │   ├── document_agent.py
│   │   └── handoff_agent.py
│   ├── reasoning.py         # Chain-of-thought prompt builder
│   ├── language.py          # Hindi/English detection
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── Chat.jsx
│       │   ├── Message.jsx
│       │   ├── ReasoningChain.jsx   # The key differentiator component
│       │   ├── ResultCard.jsx
│       │   ├── DocumentChecklist.jsx
│       │   └── HandoffCard.jsx
```

---

## YAML Schema (per scheme)

```yaml
scheme_id: pmay_g
name: "Pradhan Mantri Awas Yojana - Gramin"
name_hindi: "प्रधानमंत्री आवास योजना - ग्रामीण"
benefit: "Financial assistance of ₹1.20 lakh for construction of pucca house"
ministry: "Ministry of Rural Development"
last_updated: "2024-08"

eligibility:
  required:
    - field: location_type
      operator: equals
      value: rural
      reason: "Scheme is strictly for rural households"
    - field: housing_type
      operator: in
      value: [kutcha, homeless, zero_room, one_room]
      reason: "Must be living in kutcha or no house"

  exclusions:
    - field: vehicle_type
      operator: contains
      value: four_wheeler
      reason: "Four-wheeler ownership disqualifies"
    - field: kcc_limit
      operator: greater_than
      value: 50000
      reason: "KCC limit above ₹50,000 disqualifies"
    - field: employment_type
      operator: equals
      value: government
      reason: "Government employees are excluded"
    - field: land_irrigated_acres
      operator: greater_than
      value: 2.5
      reason: "More than 2.5 acres irrigated land disqualifies"

documents_required:
  - "Aadhaar Card"
  - "Bank Passbook (Aadhaar-seeded)"
  - "Photo of current house (showing kutcha construction)"
  - "Self-declaration of houselessness or kutcha status"

application_route:
  type: csc
  instruction: "Visit your nearest Common Service Centre (CSC). The VLE will verify your Aadhaar and submit the Awaas+ form."

human_in_loop_trigger:
  - field: awaas_plus_survey
    reason: "Awaas+ 2024-25 survey enrollment must be confirmed by local Gram Panchayat"
```

---

## LLM System Prompt (Eligibility Agent)

```
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
        },
        {
          "user_value": "Income: ₹8,000/month",
          "rule": "No income limit specified for PMAY-G",
          "result": "pass",
          "explanation": "No income threshold for this scheme"
        },
        {
          "user_value": "No four-wheeler",
          "rule": "Four-wheeler ownership disqualifies",
          "result": "pass",
          "explanation": "User does not own a four-wheeler — no barrier"
        }
      ],
      "missing_fields": [],
      "next_step": "Visit your nearest CSC with Aadhaar card and a photo of your house"
    }
  ]
}
```

---

## LLM System Prompt (Document Agent)

```
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
    },
    {
      "document": "Bank Passbook (Aadhaar-seeded)",
      "required_for": ["PMAY-G", "PMJJBY", "PMSBY"],
      "flag": "Ensure your bank account is linked to Aadhaar before visiting CSC"
    }
  ]
}
```

---

## LLM System Prompt (Handoff Agent)

```
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
  "handoff_summary": "Mera naam Ramesh hai. Main UP mein rehta hoon, kutcha ghar mein. Meri mahine ki kamai ₹8,000 hai. Mujhe bataya gaya hai ki main PMAY-G aur MGNREGA ke liye apply kar sakta hoon. Kripaya meri madad karein.",
  "schemes_to_apply": ["PMAY-G", "MGNREGA", "NSP Pre-Matric"],
  "csc_instruction": "Please help this person apply for the above schemes."
}
```

---

## Task Split (3 People)

| Person | Tasks |
|---|---|
| Person 1 (Backend) | All 8 YAML scheme files + eligibility_agent.py + reasoning.py |
| Person 2 (Backend/API) | main.py FastAPI endpoints + document_agent.py + handoff_agent.py + language.py |
| Person 3 (Frontend) | App.jsx + Chat.jsx + ReasoningChain.jsx + ResultCard.jsx + DocumentChecklist.jsx + HandoffCard.jsx |

---

## Build Order

1. Write all 8 YAML scheme files — everything depends on this
2. Build eligibility_agent.py and test with curl using Ramesh's scenario
3. Build document_agent.py and handoff_agent.py
4. Wire up main.py FastAPI endpoints
5. Test full backend end-to-end with Ramesh scenario before touching frontend
6. Build App.jsx and Chat.jsx skeleton
7. Build ReasoningChain.jsx — this is the visual differentiator, spend time here
8. Build ResultCard.jsx + DocumentChecklist.jsx + HandoffCard.jsx
9. Wire frontend to backend
10. Full end-to-end test: Ramesh scenario must produce 4+ matched schemes with reasoning visible

---

## Acceptance Criteria

- Ramesh's scenario produces at least 4 matched schemes with reasoning chain visible
- Hindi toggle produces Hindi responses
- Age 70+ input triggers PMJAY match regardless of income
- Unknown Aadhaar status triggers HandoffCard
- Disclaimer banner always visible on results page
- App runs with single command per HOW TO RUN

---

## Devpost Submission Framing

**DO NOT write:** "We built an AI that helps people find government schemes."

**Write this:**
> "Ramesh is a 42-year-old daily wage laborer in UP earning ₹8,000/month. He lives in a kutcha house and has two kids in a government school. He knew the government offered 'ration' and 'housing money' — but had no idea what he actually qualified for or what documents to bring. YojanaPath walked him through 6 questions, showed him exactly why he likely qualifies for PMAY-G, MGNREGA, PDS, and NSP scholarships with a visible reasoning chain, generated a document checklist he can bring to his nearest CSC tomorrow, and told him his MGNREGA Job Card must be issued within 15 days or the Panchayat owes him an unemployment allowance. Total time: under 4 minutes."

---

## Responsible AI Section (for Devpost)

**Risk:** LLM hallucinates incorrect scheme amounts or eligibility rules (e.g., invents ₹10,000 PM-KISAN installment instead of ₹2,000), user makes financial decisions based on wrong information.

**Mitigation:** LLM is strictly grounded to YAML knowledge base via RAG. System prompt explicitly forbids reasoning outside injected context. All outputs use "likely qualifies" framing. Confidence score drops when user data is incomplete. Permanent disclaimer banner on results page.

**Human-in-the-Loop:** The system never confirms final eligibility. Aadhaar biometric verification and final application submission is always routed to a CSC Village Level Entrepreneur (VLE) — because only they can authenticate identity and handle localized Panchayat-level nuances the AI cannot know.

**Bonus — DPDPA Compliance:** India's Digital Personal Data Protection Act (2023) prohibits using citizen data for model training without explicit consent. YojanaPath processes all data in-memory only — no persistent storage, no database. Session data is erased when the user closes the app.

---

## Demo Video Script (3-5 minutes)

1. Open with Ramesh's situation — show it on screen in one sentence
2. Start the conversation — show 6 natural back-and-forth questions in Hindi
3. Show the reasoning chain table for PMAY-G — zoom in
4. Show 4 matched schemes with confidence scores
5. Show the document checklist
6. Trigger HandoffCard — show the CSC summary in Hindi
7. Switch to age 70 input — show PMJAY triggering automatically
8. Close: "Ramesh went from confused to knowing his next 3 steps in under 4 minutes — in his own language."

---

## HOW TO RUN

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm start
```
