from __future__ import annotations

from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import load_settings
from app.db import Database
from app.models import CaptureRequest, CaptureResponse
from app.services.pipeline import process_capture

settings = load_settings()
db = Database(settings.sqlite_path)
app = FastAPI(title="SaveThatTune")
templates = Jinja2Templates(directory="app/templates")


def check_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Bad API key")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/capture", response_model=CaptureResponse, dependencies=[Depends(check_api_key)])
def capture(payload: CaptureRequest, background_tasks: BackgroundTasks):
    request_id, created = db.create_request(payload.artist, payload.title, payload.show_date)
    db.log_action(request_id, "request", "accepted", payload.model_dump())
    background_tasks.add_task(process_capture, db, settings, request_id, payload.artist, payload.title, payload.show_date)
    return CaptureResponse(request_id=request_id, status="queued", created_at=datetime.fromisoformat(created))


@app.get("/actions", dependencies=[Depends(check_api_key)])
def actions(limit: int = 20):
    return {"items": db.recent_requests(limit)}
