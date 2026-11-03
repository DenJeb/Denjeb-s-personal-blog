"""
========== 后台编辑器接口：Markdown 预览、内联图片上传 ==========
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth import CurrentAdmin
from app.csrf import verify_csrf
from app.markdown import render_markdown
from app.services.uploads import save_uploaded_image

router = APIRouter()

NO_STORE = {"Cache-Control": "no-store"}


@router.post("/uploads/inline")
def inline_upload(
    _admin: CurrentAdmin,
    image: UploadFile = File(...),
    image_alt: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    try:
        url = save_uploaded_image(image)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    alt = image_alt.strip().replace("[", "").replace("]", "") or "图片"
    return JSONResponse(
        {"url": url, "markdown": f"![{alt}]({url})"},
        headers=NO_STORE,
    )


@router.post("/posts/preview")
def preview_post(
    _admin: CurrentAdmin,
    content: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    return HTMLResponse(render_markdown(content), headers=NO_STORE)
