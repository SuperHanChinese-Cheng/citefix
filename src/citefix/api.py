"""FastAPI application — upload/download endpoints."""

from __future__ import annotations

import logging
import os
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from citefix.pipeline import process

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CiteFix",
    description="AGLC4 citation auto-formatter — upload a Word doc, get back fixed footnotes",
    version="0.1.0",
)


@app.post("/fix")
async def fix_document(file: UploadFile, use_ai: bool = Query(False)) -> StreamingResponse:
    """Upload a .docx file and get back the corrected version."""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = process(contents, use_ai=use_ai)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail="Internal processing error")

    output_filename = file.filename.rsplit(".", 1)[0] + "_fixed.docx"

    return StreamingResponse(
        BytesIO(result.fixed_docx),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'},
    )


@app.post("/analyze")
async def analyze_document(file: UploadFile) -> dict:
    """Upload a .docx file and get a JSON report of issues found (no fixes applied)."""
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = process(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Pipeline error")
        raise HTTPException(status_code=500, detail="Internal processing error")

    return {
        "footnote_count": result.footnote_count,
        "total_issues": result.error_count,
        "auto_fixable": len(result.issues_fixed),
        "needs_review": len(result.issues_flagged),
        "issues": [
            {
                "footnote": i.footnote_index,
                "rule": i.rule,
                "description": i.description,
                "current": i.current,
                "suggested": i.suggested,
                "severity": i.severity,
                "auto_fixable": i.auto_fixable,
            }
            for i in result.issues_found
        ],
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve frontend static files (Vite build output).
# In Docker the built frontend is copied to /app/static; in dev you can
# override via CITEFIX_STATIC_DIR.  The catch-all MUST come AFTER all API
# routes (/fix, /analyze, /health) so they are not intercepted.
# ---------------------------------------------------------------------------
_static_dir = Path(os.environ.get("CITEFIX_STATIC_DIR", "/app/static"))
if _static_dir.is_dir():
    # Serve hashed assets (JS/CSS) under /assets
    _assets_dir = _static_dir / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str) -> FileResponse:
        """Serve the React SPA — return the requested file if it exists, otherwise index.html."""
        file_path = _static_dir / path
        if path and file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(_static_dir / "index.html"))
