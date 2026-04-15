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


def build_chart_points(history: list[dict[str, float | str]]) -> str:
    if not history:
        return ""
    if len(history) == 1:
        return "0,100"

    max_percent = max(float(item["available_percent"]) for item in history) or 1
    points: list[str] = []
    for index, item in enumerate(history):
        x = (index / (len(history) - 1)) * 100
        percent = float(item["available_percent"])
        y = 100 - ((percent / max_percent) * 100)
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


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
            "chart_points": build_chart_points(monitor.snapshot.memory_history),
        },
    )


@app.get("/api/status", response_class=JSONResponse)
async def api_status(_: None = Depends(require_auth)) -> JSONResponse:
    return JSONResponse(monitor.snapshot.to_dict())


@app.post("/api/check")
async def api_check(_: None = Depends(require_auth)) -> JSONResponse:
    try:
        snapshot = await monitor.trigger_check()
        return JSONResponse(snapshot.to_dict())
    except Exception as exc:
        monitor.snapshot.last_status = "error"
        monitor.snapshot.last_error = str(exc)
        monitor.snapshot.add_event("error", "Manual check failed", error=str(exc))
        store.save(monitor.snapshot)
        return JSONResponse(monitor.snapshot.to_dict(), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/check")
async def manual_check(_: None = Depends(require_auth)) -> Response:
    try:
        await monitor.trigger_check()
    except Exception as exc:
        monitor.snapshot.last_status = "error"
        monitor.snapshot.last_error = str(exc)
        monitor.snapshot.add_event("error", "Manual check failed", error=str(exc))
        store.save(monitor.snapshot)
    return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
