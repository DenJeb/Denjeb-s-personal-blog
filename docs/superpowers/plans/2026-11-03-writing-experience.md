# 写作体验升级 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在后台文章编辑页提供 Markdown 工具栏、服务端预览、拖拽/粘贴图片上传和自动 WebP 压缩，同时把上传逻辑抽成 `app/services/uploads.py`。

**Architecture:** 上传相关函数从 `app/routers/admin/common.py` 原样迁到 `app/services/uploads.py`，路由改为调用服务层；新增一个管理员专用编辑器路由，提供预览和内联上传；前端用一个同源 vanilla JS 脚本渐进增强现有 textarea，无 JS 时表单照常工作。

**Tech Stack:** FastAPI、Jinja2、SQLAlchemy、Pillow、vanilla JS、pytest。

**Spec:** `docs/superpowers/specs/2026-11-03-writing-experience-design.md`

## Global Constraints

- Python 3.13，依赖固定版本，新增依赖写入 `requirements.txt`。
- 不引入 Node 构建链、CDN 脚本或前端框架。
- 上传上限 5 MB；只接受 JPG、PNG、GIF、WebP。
- 管理员接口必须使用 `CurrentAdmin` 和 `verify_csrf`。
- 保持现有无 JavaScript 表单提交和图片文件输入可用。
- 所有现有测试必须继续通过；Ruff、Black 保持干净。
- 新接口响应加 `Cache-Control: no-store`。

## Review Focus

- 伪装成图片的文本或 SVG：必须返回 400，不能落盘。
- 小体积但像素巨大的解压炸弹：必须返回 400，不能拖垮进程。
- 带 EXIF Orientation 的手机照片：输出方向必须正确，不能侧躺。
- 动画 GIF：必须保留原始字节和动画。
- 预览内容里的原始 HTML/`<script>`：必须被转义，不能在页面执行。
- 缺少 CSRF 的内联上传：必须被拒绝。

---

### Task 1: 抽出上传服务（行为不变）

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/uploads.py`
- Modify: `app/routers/admin/common.py`
- Modify: `app/routers/admin/posts.py`
- Modify: `app/routers/admin/uploads.py`
- Modify: `app/content_io.py`
- Modify: `tests/test_uploads.py`

**Interfaces:**
- Produces: `app.services.uploads` 导出 `UPLOAD_DIR`、`MAX_IMAGE_SIZE`、`detect_image_extension`、`save_uploaded_image`、`append_uploaded_image`、`upload_urls_in_text`、`all_referenced_upload_urls`、`all_upload_urls`、`delete_orphan_uploads`、`delete_unreferenced_uploads`，签名与 `admin/common.py` 中原函数一致。

- [ ] **Step 1: 运行现有上传和后台测试，确认基线**

Run: `.venv/Scripts/python.exe -m pytest tests/test_uploads.py tests/test_admin.py -q`
Expected: 全部通过。

- [ ] **Step 2: 创建 `app/services/uploads.py`，把上传函数原样迁入**

保留原实现，不改变行为。文件需要导入 `Path`、`re`、`uuid4`、`UploadFile`、`Session`、`select`、`BlogPost`。`app/services/__init__.py` 留空。

- [ ] **Step 3: 从 `admin/common.py` 删除上传代码和不再使用的导入**

保留 `page_slice`、`moment_page`、`parse_tags`、`validate_content_fields`、`fill_post`、`post_form_values`。

- [ ] **Step 4: 更新所有引用到新模块**

`admin/posts.py`、`admin/uploads.py`、`content_io.py`、`tests/test_uploads.py` 改为从 `app.services.uploads` 导入。

- [ ] **Step 5: 运行全部测试**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: 73 passed。

- [ ] **Step 6: 运行 Ruff 和 Black**

Run: `.venv/Scripts/python.exe -m ruff check app tests && .venv/Scripts/python.exe -m black --check app tests`
Expected: 全部通过。

- [ ] **Step 7: Commit**

```bash
git add app/services app/routers/admin/common.py app/routers/admin/posts.py app/routers/admin/uploads.py app/content_io.py tests/test_uploads.py
git commit -m "refactor: extract upload service"
```

---

### Task 2: 图片处理（WebP、缩放、EXIF）

**Files:**
- Modify: `requirements.txt`
- Modify: `app/services/uploads.py`
- Modify: `tests/test_uploads.py`

**Interfaces:**
- Consumes: Task 1 的 `app.services.uploads`。
- Produces: `process_image(data: bytes) -> tuple[bytes, str]`；`save_image_bytes(data: bytes) -> str`；`save_uploaded_image(upload: UploadFile) -> str` 改为使用前两者。

- [ ] **Step 1: 安装 Pillow 并固定版本**

Run: `.venv/Scripts/python.exe -m pip install pillow`
把安装到的版本写入 `requirements.txt`，放在 `PyYAML` 之后。

- [ ] **Step 2: 写失败测试**

在 `tests/test_uploads.py` 增加：

```python
def test_process_image_converts_png_to_webp():
    data, extension = process_image(_image_bytes(size=(10, 10)))
    assert extension == ".webp"
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"

def test_process_image_resizes_large_image():
    data, _ = process_image(_image_bytes(size=(3000, 1000), fmt="JPEG"))
    with Image.open(BytesIO(data)) as image:
        assert max(image.size) == MAX_IMAGE_DIMENSION

def test_process_image_applies_exif_orientation():
    image = Image.new("RGB", (40, 20), (255, 0, 0))
    exif = image.getexif()
    exif[274] = 6
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    data, _ = process_image(buffer.getvalue())
    with Image.open(BytesIO(data)) as result:
        assert result.size == (20, 40)

def test_process_image_keeps_gif_bytes():
    data = _image_bytes(size=(10, 10), fmt="GIF")
    assert process_image(data) == (data, ".gif")

def test_process_image_rejects_corrupt_image():
    with pytest.raises(ValueError, match="无法解析"):
        process_image(b"\x89PNG\r\n\x1a\nnot really a png")

def test_process_image_rejects_decompression_bomb(monkeypatch):
    monkeypatch.setattr(uploads, "MAX_IMAGE_PIXELS", 10)
    with pytest.raises(ValueError, match="尺寸过大"):
        process_image(_image_bytes(size=(20, 20)))

def test_save_uploaded_image_rejects_large_file():
    upload = UploadFile(
        filename="big.png",
        file=BytesIO(b"x" * (MAX_IMAGE_SIZE + 1)),
    )
    with pytest.raises(ValueError, match="5 MB"):
        save_uploaded_image(upload)
```

测试辅助函数 `_image_bytes(size, fmt="PNG", color=(255, 0, 0))` 用 Pillow 生成图片字节。

- [ ] **Step 3: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_uploads.py -q`
Expected: `process_image`/`save_image_bytes` 未定义或行为不符。

- [ ] **Step 4: 实现图片处理**

在 `app/services/uploads.py` 增加：

```python
MAX_IMAGE_DIMENSION = 2000
WEBP_QUALITY = 82
MAX_IMAGE_PIXELS = 40_000_000
```

`process_image(data)` 规则：

- 空数据或超过 `MAX_IMAGE_SIZE`：`ValueError`。
- `detect_image_extension` 返回 `None`：`ValueError("只支持 JPG、PNG、GIF、WebP 图片。")`。
- 用 `Image.open(BytesIO(data))` 打开所有格式，先检查 `width * height > MAX_IMAGE_PIXELS`，超过则 `ValueError("图片尺寸过大。")`。这样 GIF/WebP 也能挡住解压炸弹。
- `.gif`、`.webp`：检查通过后原样返回 `(data, extension)`，保留动画。
- `.jpg`、`.png`：`ImageOps.exif_transpose`，`thumbnail((2000, 2000))`，转换到 `RGB` 或 `RGBA`，保存为 WebP（`quality=82, method=6`），返回 `(buffer.getvalue(), ".webp")`。
- 捕获 `UnidentifiedImageError`、`DecompressionBombError`、`OSError`，抛出 `ValueError("图片无法解析，请换一张。")`。

`save_image_bytes(data)`：校验空/大小 → `process_image` → 写入 `UPLOAD_DIR / f"{uuid4().hex}{extension}"` → 返回 URL。

`save_uploaded_image(upload)`：读取 `MAX_IMAGE_SIZE + 1` 字节后调用 `save_image_bytes`。

- [ ] **Step 5: 运行测试确认通过**

Run: `.venv/Scripts/python.exe -m pytest tests/test_uploads.py -q`
Expected: 全部通过。

- [ ] **Step 6: 运行全部测试和格式检查**

Run: `.venv/Scripts/python.exe -m pytest -q && .venv/Scripts/python.exe -m ruff check app tests && .venv/Scripts/python.exe -m black --check app tests`
Expected: 全部通过。

- [ ] **Step 7: Commit**

```bash
git add requirements.txt app/services/uploads.py tests/test_uploads.py
git commit -m "feat: optimize uploaded images to webp"
```

---

### Task 3: 预览与内联上传接口

**Files:**
- Create: `app/routers/admin/editor.py`
- Modify: `app/routers/admin/__init__.py`
- Create: `tests/test_editor.py`

**Interfaces:**
- Consumes: `save_uploaded_image` from `app.services.uploads`；`render_markdown` from `app.markdown`。
- Produces:
  - `POST /admin/posts/preview` → `HTMLResponse`，表单字段 `content`、`csrf_token`。
  - `POST /admin/uploads/inline` → `JSONResponse {"url": str, "markdown": str}`，multipart 字段 `image`、可选 `image_alt`、`csrf_token`。

- [ ] **Step 1: 写失败测试**

`tests/test_editor.py` 覆盖：

```python
def test_preview_requires_admin(client):
    token = csrf_token(client.get("/admin/login").text)
    response = client.post(
        "/admin/posts/preview",
        data={"csrf_token": token, "content": "# hi"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"

def test_preview_renders_markdown(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/posts/preview",
        data={"csrf_token": token, "content": "# 标题\n\n**加粗**\n\n<script>alert(1)</script>"},
    )
    assert response.status_code == 200
    assert "<h1>标题</h1>" in response.text
    assert "<strong>加粗</strong>" in response.text
    assert "<script>" not in response.text
    assert response.headers["cache-control"] == "no-store"

def test_preview_requires_csrf(admin_client):
    response = admin_client.post(
        "/admin/posts/preview", data={"content": "# hi"}
    )
    assert response.status_code == 422

def test_inline_upload_returns_markdown(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token, "image_alt": "截图"},
        files={"image": ("test.png", PNG, "image/png")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["url"].endswith(".webp")
    assert payload["markdown"] == f"![截图]({payload['url']})"
    assert (UPLOAD_DIR / Path(payload["url"]).name).is_file()

def test_inline_upload_rejects_non_image(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("x.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "只支持" in response.json()["detail"]

def test_inline_upload_rejects_svg(admin_client):
    token = csrf_token(admin_client.get("/admin/posts/new").text)
    response = admin_client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("x.svg", b"<svg></svg>", "image/svg+xml")},
    )
    assert response.status_code == 400

def test_inline_upload_requires_admin(client):
    token = csrf_token(client.get("/admin/login").text)
    response = client.post(
        "/admin/uploads/inline",
        data={"csrf_token": token},
        files={"image": ("test.png", PNG, "image/png")},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"

def test_inline_upload_requires_csrf(admin_client):
    response = admin_client.post(
        "/admin/uploads/inline",
        files={"image": ("test.png", PNG, "image/png")},
    )
    assert response.status_code == 422
```

使用现有 `PNG` 常量，测试结束删除生成文件。

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_editor.py -q`
Expected: 404 或路由不存在。

- [ ] **Step 3: 实现 `app/routers/admin/editor.py`**

```python
router = APIRouter()

@router.post("/uploads/inline")
def inline_upload(
    _admin: CurrentAdmin,
    image: UploadFile = File(...),
    image_alt: str = Form(""),
    _csrf: None = Depends(verify_csrf),
):
    # save_uploaded_image → 400 on ValueError
    # alt 去空白、去方括号，空则 "图片"
    # 返回 JSONResponse({"url": url, "markdown": f"![{alt}]({url})"})

@router.post("/posts/preview")
def preview_post(
    _admin: CurrentAdmin,
    content: str = Form(...),
    _csrf: None = Depends(verify_csrf),
):
    # HTMLResponse(render_markdown(content))
```

两个响应都带 `headers={"Cache-Control": "no-store"}`。

- [ ] **Step 4: 注册路由**

在 `app/routers/admin/__init__.py` 导入 `editor` 并 `router.include_router(editor.router)`。

- [ ] **Step 5: 运行测试**

Run: `.venv/Scripts/python.exe -m pytest tests/test_editor.py -q`
Expected: 全部通过。

- [ ] **Step 6: 运行全部测试和格式检查**

Run: `.venv/Scripts/python.exe -m pytest -q && .venv/Scripts/python.exe -m ruff check app tests && .venv/Scripts/python.exe -m black --check app tests`
Expected: 全部通过。

- [ ] **Step 7: Commit**

```bash
git add app/routers/admin/editor.py app/routers/admin/__init__.py tests/test_editor.py
git commit -m "feat: add markdown preview and inline image upload"
```

---

### Task 4: 编辑器前端与模板接入

**Files:**
- Modify: `app/templates/admin/base.html`
- Modify: `app/templates/admin/post_form.html`
- Create: `app/static/css/editor.css`
- Create: `app/static/js/editor.js`
- Modify: `tests/test_admin.py`

**Interfaces:**
- Consumes: 预览接口 `/admin/posts/preview`、内联上传接口 `/admin/uploads/inline`。
- Produces: 文章编辑页的 `[data-markdown-editor]` 容器，textarea 仍使用 `name="content"`。

- [ ] **Step 1: 写页面测试**

在 `tests/test_admin.py` 增加：

```python
def test_post_form_includes_editor(admin_client):
    response = admin_client.get("/admin/posts/new")
    assert response.status_code == 200
    assert "/static/js/editor.js" in response.text
    assert "/static/css/editor.css" in response.text
    assert 'data-markdown-editor' in response.text
    assert 'name="content"' in response.text
```

- [ ] **Step 2: 运行测试确认失败**

Run: `.venv/Scripts/python.exe -m pytest tests/test_admin.py::test_post_form_includes_editor -q`
Expected: FAIL。

- [ ] **Step 3: 给 `admin/base.html` 增加 `head` 和 `scripts` block**

在 `</head>` 前加 `{% block head %}{% endblock %}`，在 `theme.js` 后加 `{% block scripts %}{% endblock %}`。

- [ ] **Step 4: 改 `admin/post_form.html`**

在正文 textarea 外包一层：

```html
<div class="markdown-editor" data-markdown-editor
     data-preview-url="{{ url_for('preview_post') }}"
     data-upload-url="{{ url_for('inline_upload') }}">
  <div class="editor-toolbar">
    <button type="button" data-action="bold">B</button>
    ...
    <button type="button" data-action="preview">预览</button>
  </div>
  <textarea name="content" rows="18" required data-editor-input>{{ form.content }}</textarea>
  <div class="markdown-preview" data-editor-preview hidden></div>
  <p class="editor-status" data-editor-status aria-live="polite"></p>
  <input type="file" accept="image/*" data-editor-image-input hidden>
</div>
```

按钮覆盖：bold、italic、heading、link、code、quote、ul、image、preview。CSS/JS 通过 head/scripts block 引入。保留原文件输入作为无 JS 兜底。

- [ ] **Step 5: 写 `app/static/js/editor.js`**

实现：

- 工具栏动作在选区两侧插入 Markdown 标记，链接弹 `prompt` 输入 URL。
- Tab 插入两个空格，Shift+Tab 删除行首最多两个空格。
- Ctrl/Cmd+B/I/K 快捷键。
- 预览按钮 `fetch` POST `data-preview-url`，FormData 带 `csrf_token` 和 `content`，把返回 HTML 放进预览面板并切换显示。
- 图片按钮、拖拽、粘贴共用 `uploadImage(file)`：FormData 带 `csrf_token` 和 `image`，POST `data-upload-url`，成功后在光标处插入返回的 `markdown`，失败显示 `detail`。
- 上传中禁用图片按钮，状态文字用中文。
- 没有 `data-markdown-editor` 时直接返回，不影响其他页面。

- [ ] **Step 6: 写 `app/static/css/editor.css`**

工具栏 flex 布局、按钮尺寸、预览面板边框和内边距、拖拽高亮、状态文字颜色；颜色使用现有 CSS 变量，兼容暗色模式。

- [ ] **Step 7: 运行测试和格式检查**

Run: `.venv/Scripts/python.exe -m pytest -q && .venv/Scripts/python.exe -m ruff check app tests && .venv/Scripts/python.exe -m black --check app tests`
Expected: 全部通过。

- [ ] **Step 8: Commit**

```bash
git add app/templates/admin/base.html app/templates/admin/post_form.html app/static/css/editor.css app/static/js/editor.js tests/test_admin.py
git commit -m "feat: add markdown editor to post form"
```

---

### Task 5: 文档更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新功能列表**

在“后台”部分补充：Markdown 工具栏、服务端预览、拖拽/粘贴上传、图片自动转 WebP。

- [ ] **Step 2: 更新目录结构说明**

在 `app/` 下补充 `services/`，说明上传逻辑的位置。

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document writing experience upgrade"
```

---

## 验证清单

- [ ] `.venv/Scripts/python.exe -m pytest -q` 全部通过。
- [ ] `.venv/Scripts/python.exe -m ruff check app tests` 通过。
- [ ] `.venv/Scripts/python.exe -m black --check app tests` 通过。
- [ ] 手动打开 `/admin/posts/new`，确认工具栏、预览、拖拽/粘贴上传可用。
- [ ] 无 JavaScript 时，表单保存和文件输入仍可用。
- [ ] 上传 JPEG/PNG 后生成 `.webp` 文件；GIF 保持 `.gif`。
