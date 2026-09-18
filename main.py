import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
import google.generativeai as genai

from database import SessionLocal, init_db, Lead

app = FastAPI(title="Multi-Industry Lead Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize DB on Startup
@app.on_event("startup")
def on_startup():
    init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class LeadRequest(BaseModel):
    industry: str
    user_prompt: str
    customer_name: str = ""
    contact_info: str = ""

@app.get("/", response_class=HTMLResponse)
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/leads")
def process_lead(req: LeadRequest, db: Session = Depends(get_db)):
    # AI Intent Engine Process
    ai_intent = "General Inquiry"
    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"Analyze this customer message for {req.industry} industry and extract intent in 3-5 words: {req.user_prompt}"
            response = model.generate_content(prompt)
            if response.text:
                ai_intent = response.text.strip()
        except Exception as e:
            print("Gemini Error:", e)

    # Save to Database
    db_lead = Lead(
        industry=req.industry,
        intent=ai_intent,
        customer_name=req.customer_name,
        contact_info=req.contact_info,
        details=req.user_prompt
    )
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)

    return {
        "status": "success",
        "lead_id": db_lead.id,
        "industry": db_lead.industry,
        "extracted_intent": db_lead.intent,
        "message": "Lead record created successfully!"
    }

@app.get("/api/leads")
def get_leads(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.created_at.desc()).all()
    return leads
