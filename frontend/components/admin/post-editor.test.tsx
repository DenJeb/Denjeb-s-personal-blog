import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PostEditor } from "./post-editor";

const { pushMock, refreshMock, sendJsonMock, postFormMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
  sendJsonMock: vi.fn(),
  postFormMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, refresh: refreshMock }),
}));

vi.mock("@/lib/api/browser", () => ({
  ApiError: class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  sendJson: sendJsonMock,
  postForm: postFormMock,
}));

function renderEditor() {
  return render(<PostEditor today="2026-11-13" />);
}

function contentField(): HTMLTextAreaElement {
  return screen.getByLabelText("正文") as HTMLTextAreaElement;
}

describe("PostEditor", () => {
  beforeEach(() => {
    pushMock.mockReset();
    refreshMock.mockReset();
    sendJsonMock.mockReset();
    postFormMock.mockReset();
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 0;
    });
    vi.stubGlobal("prompt", vi.fn(() => ""));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("keeps text typed while an image upload is in flight", async () => {
    let resolveUpload!: (value: { markdown: string }) => void;
    postFormMock.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      }),
    );

    const { container } = renderEditor();
    const fileInput = container.querySelector(
      'input[type="file"]',
    ) as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [new File(["x"], "cover.png", { type: "image/png" })],
      },
    });

    const field = contentField();
    fireEvent.change(field, { target: { value: "typed during upload" } });

    resolveUpload({ markdown: "![图片](/static/uploads/mock.webp)" });

    await waitFor(() =>
      expect(field.value).toContain("/static/uploads/mock.webp"),
    );
    expect(field.value).toContain("typed during upload");
  });

  it("splits tags on ASCII and full-width commas", async () => {
    sendJsonMock.mockResolvedValue({});
    const { container } = renderEditor();

    fireEvent.change(screen.getByLabelText("标题"), {
      target: { value: "标题" },
    });
    fireEvent.change(contentField(), { target: { value: "正文" } });
    fireEvent.change(screen.getByLabelText("标签（逗号分隔）"), {
      target: { value: "FastAPI，博客" },
    });
    fireEvent.submit(container.querySelector("form")!);

    await waitFor(() => expect(sendJsonMock).toHaveBeenCalled());
    const body = sendJsonMock.mock.calls[0][2] as { tags: string[] };
    expect(body.tags).toEqual(["FastAPI", "博客"]);
  });

  it("supports the Ctrl+B bold shortcut", async () => {
    renderEditor();
    const field = contentField();
    fireEvent.change(field, { target: { value: "bold" } });
    field.setSelectionRange(0, 4);

    fireEvent.keyDown(field, { key: "b", ctrlKey: true });

    await waitFor(() => expect(field.value).toBe("**bold**"));
  });

  it("prefixes every selected line for a quote", async () => {
    renderEditor();
    const field = contentField();
    fireEvent.change(field, { target: { value: "line1\nline2" } });
    field.setSelectionRange(0, 11);

    fireEvent.click(screen.getByRole("button", { name: "引用" }));

    await waitFor(() => expect(field.value).toBe("> line1\n> line2"));
  });

  it("prompts for a link URL", async () => {
    vi.mocked(window.prompt).mockReturnValue("https://example.com");
    renderEditor();
    const field = contentField();
    fireEvent.change(field, { target: { value: "link" } });
    field.setSelectionRange(0, 4);

    fireEvent.keyDown(field, { key: "k", ctrlKey: true });

    await waitFor(() =>
      expect(field.value).toBe("[link](https://example.com)"),
    );
  });

  it("uploads an image pasted into the editor", async () => {
    postFormMock.mockResolvedValue({
      markdown: "![图片](/static/uploads/mock.webp)",
    });
    renderEditor();
    const field = contentField();
    const file = new File(["x"], "paste.png", { type: "image/png" });

    fireEvent.paste(field, {
      clipboardData: {
        items: [{ type: "image/png", getAsFile: () => file }],
      },
    });

    await waitFor(() => expect(postFormMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(field.value).toContain("/static/uploads/mock.webp"),
    );
  });
});
