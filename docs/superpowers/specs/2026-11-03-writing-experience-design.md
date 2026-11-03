# 写作体验升级设计

## 意图

让作者在后台写文章时更顺手：有 Markdown 工具栏和快捷键，能随时预览渲染结果，图片可以拖拽或粘贴上传，上传后自动压缩。与此同时，把上传相关逻辑抽成 `app/services/uploads.py`，作为 service 层的第一块，为后续重构铺路。

## 目标

- 后台文章编辑页提供 Markdown 工具栏、常用快捷键和预览面板。
- 支持把图片拖进编辑区或直接粘贴上传，并在光标处插入 Markdown 图片语法。
- 上传的 JPEG/PNG 自动转成 WebP、纠正 EXIF 方向、限制长边 2000px、去掉元数据。
- GIF 和 WebP 保留原文件，避免破坏动画。
- 无 JavaScript 时，原有表单提交、图片文件输入仍然可用。
- 新增接口仅管理员可访问，并校验 CSRF。
- 上传逻辑进入 `app/services/uploads.py`，路由不再承担文件处理细节。
- 测试覆盖图片处理、预览、内联上传和权限校验。

## 非目标

- 不做 WYSIWYG，不做客户端 Markdown 渲染。
- 不做媒体库、图床、对象存储。
- 不做草稿分享链接。
- 不支持视频上传。
- 不重写后台其他表单。

## 反目标

- 为了编辑器引入 Node 构建链或 CDN 资源。
- 让预览接口返回未转义的原始 HTML。
- 为了压缩图片而丢失 GIF 动画。
- 把上传逻辑复制一份到新模块，旧代码继续保留两份实现。

## 现状

- [app/templates/admin/post_form.html](../../../app/templates/admin/post_form.html) 目前是一个纯 textarea，加一个文件输入。
- 图片处理集中在 [app/routers/admin/common.py](../../../app/routers/admin/common.py)，路由和业务逻辑混在一起。
- Markdown 渲染由 [app/markdown.py](../../../app/markdown.py) 的 `render_markdown` 完成，配置了 `html=False`，输出可以安全地放进页面。
- CSP 是 `script-src 'self'`，不能直接引 CDN 脚本。

## 决策

### 编辑器

- 自己写一个轻量 vanilla JS 编辑器，不引入 EasyMDE/CodeMirror。
- 原因：项目没有 Node 构建链，CSP 只允许同源脚本，EasyMDE 还需要额外图标资源；所需功能（工具栏、快捷键、预览、拖拽上传）用一个约 200 行的脚本可以完成。
- 工具栏按钮：粗体、斜体、标题、链接、行内代码、引用、无序列表、图片上传。
- 快捷键：Ctrl/Cmd+B、I、K；Tab/Shift+Tab 缩进。
- 预览通过服务端接口完成，保证和最终发布内容用同一个渲染器。

### 图片处理

- 新增 Pillow 依赖，固定版本写入 `requirements.txt`。
- JPEG/PNG：`ImageOps.exif_transpose` → 转 RGB/RGBA → 长边缩到最大 2000px → 保存为 WebP（quality=82, method=6）。
- GIF：保留原始字节，扩展名 `.gif`。
- WebP：保留原始字节，扩展名 `.webp`。
- 其他格式：拒绝。
- 原始文件上限 5 MB；像素数上限 4000 万，防止解压炸弹。
- 文件名继续使用 `uuid4().hex + 扩展名`，避免碰撞和路径注入。

### 接口

- `POST /admin/uploads/inline`：管理员 + CSRF，multipart 字段 `image`、可选 `image_alt`；返回 `{"url": "...", "markdown": "![alt](url)"}`。
- `POST /admin/posts/preview`：管理员 + CSRF，表单字段 `content`；返回渲染后的 HTML 片段，`Cache-Control: no-store`。

### 前端接入

- `app/templates/admin/base.html` 增加 `head` 和 `scripts` 两个空 block，供具体页面扩展。
- 文章表单加 `data-markdown-editor` 容器、工具栏、预览面板；引入 `editor.css` 和 `editor.js`。
- 图片拖拽/粘贴上传使用 `fetch`，把 CSRF token 放进 `FormData`。
- 上传过程中显示状态，失败时显示错误，不阻塞继续编辑。

## 服务层边界

`app/services/uploads.py` 负责：

- `detect_image_extension(data) -> str | None`
- `process_image(data) -> tuple[bytes, str]`
- `save_image_bytes(data) -> str`
- `save_uploaded_image(upload) -> str`
- `append_uploaded_image(content, image, image_alt) -> tuple[str, str | None]`
- `upload_urls_in_text(*texts) -> set[str]`
- `all_referenced_upload_urls(db) -> set[str]`
- `all_upload_urls() -> set[str]`
- `delete_orphan_uploads(db) -> None`
- `delete_unreferenced_uploads(db, candidates) -> None`
- 常量 `UPLOAD_DIR`、`MAX_IMAGE_SIZE`、`MAX_IMAGE_DIMENSION`

路由只负责 HTTP：读表单、调服务、返回模板/重定向/JSON。

## 安全

- 预览内容经过 `render_markdown`，`html=False`，原始 HTML 会被转义。
- 两个新接口都要求管理员会话和 CSRF。
- 上传按文件头判断类型，不信任 `Content-Type` 和扩展名。
- 图片处理捕获 `UnidentifiedImageError`、`OSError`、`DecompressionBombError`，统一返回 400。
- 预览和内联上传响应加 `Cache-Control: no-store`。

## 测试策略

- 单元测试：图片格式转换、缩放、EXIF 方向、GIF/WebP 原样保留、损坏图片、超大文件。
- 接口测试：权限、CSRF、预览 HTML、内联上传返回的 URL/Markdown、非图片拒绝。
- 页面测试：文章编辑页包含编辑器资源，textarea 仍保留 `name="content"`。
- 回归：现有上传清理、文章 CRUD 测试全部通过。

## 后续

这是第一优先级的第一个子项目。后续依次单独出计划：阅读体验（slug/TOC/相关文章）、安全加固（2FA/CSP/HSTS）、通知、HTMX。服务层会随这些功能继续逐块抽取，不做一次性大重构。
