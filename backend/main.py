import logging
import os
from pathlib import Path
from typing import Literal

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.router import route_prompt

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
VALID_REFINEMENTS = {"brief", "bullet", "detailed"}

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    prompt: str
    refinement: Literal["brief", "bullet", "detailed"] = "brief"


@app.get("/")
def home():
    return {"status": "Backend running"}


@app.get("/health")
def health():
    return home()


@app.post("/ask")
def ask(
    payload: AskRequest | None = Body(default=None),
    prompt: str | None = Query(default=None),
    refinement: str | None = Query(default=None),
):
    prompt_text = payload.prompt if payload else prompt
    refinement_value = payload.refinement if payload else refinement
    refinement_value = (refinement_value or "brief").strip().lower()

    if not prompt_text or not prompt_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide a prompt in the JSON body as {'prompt': '...'} or as ?prompt=...",
        )

    if refinement_value not in VALID_REFINEMENTS:
        raise HTTPException(
            status_code=400,
            detail="refinement must be one of: brief, bullet, detailed",
        )

    result = route_prompt(prompt_text.strip(), refinement=refinement_value)
    status_code = 200 if result["ok"] else 502
    return JSONResponse(status_code=status_code, content=result)


if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
