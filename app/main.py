from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import settings
from .monitor import MonitorService
from .state import StateStore

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
security = HTTPBasic(auto_error=False)
app = FastAPI(title=settings.app_name)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

store = StateStore(settings.state_file)
monitor = MonitorService(settings, store)


def require_auth(credentials: HTTPBasicCredentials | None = Depends(security)) -> None:
    if not settings.ui_username or not settings.ui_password:
        return
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
    username_ok = secrets.compare_digest(credentials.username, settings.ui_username)
    password_ok = secrets.compare_digest(credentials.password, settings.ui_password)
    if not username_ok or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.on_event("startup")
async def startup_event() -> None:
    await monitor.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await monitor.stop()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, _: None = Depends(require_auth)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "snapshot": monitor.snapshot,
            "settings": settings,
        },
    )


@app.get("/api/status", response_class=JSONResponse)
async def api_status(_: None = Depends(require_auth)) -> JSONResponse:
    return JSONResponse(monitor.snapshot.to_dict())


@app.post("/api/check")
async def api_check(_: None = Depends(require_auth)) -> JSONResponse:
    snapshot = await monitor.trigger_check()
    return JSONResponse(snapshot.to_dict())


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check")
async def manual_check(_: None = Depends(require_auth)) -> Response:
    await monitor.trigger_check()
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
