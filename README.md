# YojanaPath (योजना पाथ) — ClearPath India
[![USAII Global AI Hackathon 2026](https://img.shields.io/badge/Hackathon-USAII_2026-blueviolet?style=for-the-badge)](https://github.com/kart747/USALL)
[![Tech Stack](https://img.shields.io/badge/Tech_Stack-React_%2B_FastAPI-blue?style=for-the-badge)](https://github.com/kart747/USALL)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

An AI-powered government scheme eligibility navigator and fact-checker designed to assist rural and low-income Indian citizens. YojanaPath bridges the digital literacy gap by simplifying complex eligibility criteria into a structured, bilingual chat session.

---

## 📖 Table of Contents
1. [What Is YojanaPath?](#-what-is-yojanapath)
2. [Key Features](#-key-features)
3. [System Architecture & Data Flow](#-system-architecture--data-flow)
4. [Technology Stack](#-technology-stack)
5. [Project Structure](#-project-structure)
6. [Getting Started](#-getting-started)
   - [Backend Setup](#backend-setup)
   - [Frontend Setup](#frontend-setup)
7. [API Reference](#-api-reference)
8. [Design & Agent Architecture Highlights](#-design--agent-architecture-highlights)
9. [Supported Schemes](#-supported-schemes)

---

## 🌟 What Is YojanaPath?

India runs numerous welfare schemes worth billions of rupees, but many deserving citizens miss out due to a lack of awareness, complex rules, missing documents, or widespread rumours.

**YojanaPath** (योजना पाथ) solves these barriers in one interactive session. It functions as a conversational intake assistant that asks **9 quick questions** (age, location, income, land holdings, housing, etc.) in either Hindi or English. Behind the scenes, it runs an ensemble of AI agents to check eligibility, generate a consolidated document checklist, calculate the total stackable benefit value, and write a copyable handoff note that the citizen can hand directly to a **Common Service Centre (CSC)** operator to apply.

---

## ✨ Key Features

- **9-Question Conversational Intake:** Dynamically guides the user through critical demographic fields.
- **Bilingual Interface:** Toggle seamlessly between Hindi (हिन्दी) and English.
- **Ensemble Agent Pipeline:** Runs 4 specialized backend processes in parallel:
  - **Eligibility Agent:** Evaluates conditions and builds a step-by-step reasoning chain.
  - **Document Agent:** Outputs a deduplicated checklist with warning flags (e.g., Aadhaar-linking requirements).
  - **Handoff Agent:** Drafts a concise (≤80 words) note for CSC operators.
  - **Benefit Aggregator:** Normalizes cash and in-kind benefits to display a total stackable value.
- **Transparency Engine:** Expandable rule audit tables showing exactly *why* a user qualifies or fails a rule.
- **Rumour & Fact-Checker:** A dedicated mode to paste viral claims/rumours and cross-reference them against verified scheme rules.
- **Graceful Fallbacks:** The app runs entirely offline with deterministic Python rule engines if Groq API keys are not provided.

---

## 🏗️ System Architecture & Data Flow

```
                   User Input (Chat / Rumour)
                               │
                               ▼
                       FastAPI Server
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
     [/chat Route]     [/analyze Route]    [/fact-check Route]
     Iterate Q&A       Run Agent Pipeline   Check claim aliases
    (9 properties)             │            & status keywords
                               │                  │
               ┌───────────────┼──────────────┐   │
               │               │              │   ▼
               ▼               ▼              ▼  LLM / Heuristic
          Eligibility      Document        Handoff  Fact-Check
             Agent           Agent          Agent     Agent
          (LLM/Python)    (Deduplicator)   (Summary)
               │               │              │
               └───────────────┼──────────────┘
                               │
                               ▼
                        Aggregator.py
                 (Normalizes & sums benefits)
                               │
                               ▼
                      Unified JSON Output
                      (Results Dashboard)
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|:---|:---|
| **Frontend UI** | React 18, Vite 5, Vanilla CSS |
| **Backend API** | Python 3, FastAPI, Uvicorn |
| **AI Inference** | Groq API (`llama-3.1-8b-instant` or configured fallback models) |
| **Language Detection** | `langdetect` (bilingual English / Hindi parsing) |
| **Knowledge Base** | Structured YAML scheme definitions |
| **Package Management**| `npm` (Frontend), `pip` + `venv` (Backend) |

---

## 📁 Project Structure

```
clearpath-india/
├── backend/
│   ├── main.py                    # FastAPI entrypoint (Exposes API endpoints)
│   ├── aggregator.py              # Benefit aggregator & cash normalizer
│   ├── language.py                # Language identification utility
│   ├── requirements.txt           # Python backend dependencies
│   ├── .env                       # Environment configuration (GROQ_API_KEY)
│   ├── agents/
│   │   ├── eligibility_agent.py   # Main rule parsing & LLM reasoning engine
│   │   ├── fact_check_agent.py    # Anti-hallucinating rumour verification
│   │   ├── document_agent.py      # Deduplicated doc list generator
│   │   └── handoff_agent.py       # Conversational note composer for CSCs
│   └── schemes/                   # YAML files containing official rules
│       ├── pm_kisan.yaml          # PM-KISAN rules
│       ├── pmjay.yaml             # Ayushman Bharat rules
│       └── ...
└── frontend/
    ├── package.json               # Frontend dependencies
    ├── vite.config.js             # Vite configurations
    └── src/
        ├── App.jsx                # Application shell & stage manager
        ├── App.css                # Visual themes & variables
        └── components/            # Reusable UI widgets (Chat, ResultCards, etc.)
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+ installed
- Node.js (v18+) & npm installed

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```
5. Start the server:
   ```bash
   python main.py
   ```
   The backend API will run on `http://127.0.0.1:8000`.

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install node packages:
   ```bash
   npm install
   ```
3. Launch the development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:3000` (or the local port printed in your console) to view YojanaPath in your browser.

---

## 🔌 API Reference

| Endpoint | Method | Payload | Description |
|:---|:---:|:---|:---|
| `/health` | `GET` | *None* | Verifies API server status. |
| `/chat` | `POST` | `{"collected": {...}, "message": "User input text"}` | Evaluates Q&A progress; returns the next question or triggers analysis. |
| `/analyze` | `POST` | `{"user_data": {...}}` | Main pipeline running all 4 agents; returns structured eligibility, documents, handoff notes, and aggregated cash values. |
| `/fact-check` | `POST` | `{"claim": "Rumour text"}` | Runs the anti-hallucination fact check; returns verdict and bilingual explanation. |

---

## 🧠 Design & Agent Architecture Highlights

### 🛡️ Deterministic Overrides
Certain high-stakes schemes are bypassed from direct LLM reasoning to ensure 100% logic reliability:
- **PM-KISAN:** Uses Python overrides to evaluate landholder verification, government employee exclusions, and tax-payer thresholds.
- **PMJAY:** Implements a direct age override. Anyone `age >= 70` is immediately marked as eligible for Ayushman Bharat (reflecting the September 2024 update), completely bypassing standard SECC restrictions.

### 🔌 Anti-Hallucination Fact-Checking
The **Fact-Check Agent** runs a strict local filter `_claim_names_unknown_scheme()`. If a user queries a fabricated scheme (e.g., *"PM Dhan Yojana Plus"*), the agent intercepts it immediately and flags it as `UNVERIFIED` rather than allowing the LLM to hallucinate rules.

### 🌐 Resilient Fallbacks
If the Groq API key is missing or the external service fails, YojanaPath falls back gracefully to local Python-based rules for all features so that the navigator never stops working.

---

## 🌾 Supported Schemes

YojanaPath currently supports checking eligibility for:

1. **PM-KISAN** (Pradhan Mantri Kisan Samman Nidhi) — Income support for farmers.
2. **Ayushman Bharat (PMJAY)** — Health insurance cover.
3. **PM Awas Yojana - Gramin (PMAY-G)** — Rural housing development grant.
4. **MGNREGA** — Guaranteed rural wage employment.
5. **PDS (Public Distribution System)** — Subsidized food grains.
6. **PMJJBY** — Life insurance cover.
7. **PMSBY** — Accidental death/disability insurance.
8. **National Scholarship Portal (NSP)** — Educational scholarships.
