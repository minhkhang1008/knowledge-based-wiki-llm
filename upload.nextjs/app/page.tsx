"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import styles from "./page.module.css";

type ApiError = {
  code?: string;
  detail?: string | Record<string, unknown>;
};

type ApiEnvelope<T> = {
  success?: boolean;
  data: T;
  message?: string;
  error?: ApiError | null;
};

type SupportedFormatData = {
  extensions: string[];
  max_upload_size_mb: number;
};

type Article = {
  id: string;
  document_id: string;
  title: string;
  content: string;
  source_file: string;
  created_at: string;
  updated_at: string;
};

type IngestionData = {
  article: Article;
  document_id: string;
  chunk_count: number;
};

const API_ORIGIN = process.env.NEXT_PUBLIC_API_ORIGIN?.trim() ?? "";

function getFileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  if (index < 0) {
    return "";
  }
  return name.slice(index).toLowerCase();
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Không xác định";
  }
  return date.toLocaleString("vi-VN", { hour12: false });
}

function describeApiError(status: number, payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return `Yêu cầu thất bại (${status}).`;
  }

  const data = payload as {
    detail?: unknown;
    message?: string;
    error?: ApiError;
  };

  if (typeof data.message === "string" && data.message.trim()) {
    return data.message;
  }

  if (typeof data.detail === "string" && data.detail.trim()) {
    return data.detail;
  }

  if (data.error?.detail) {
    if (typeof data.error.detail === "string") {
      return data.error.detail;
    }
    return JSON.stringify(data.error.detail);
  }

  if (typeof data.detail === "object" && data.detail !== null) {
    const supported = (data.detail as { supported_extensions?: unknown }).supported_extensions;
    const message = (data.detail as { message?: unknown }).message;
    const supportedText = Array.isArray(supported) ? ` Hỗ trợ: ${supported.join(", ")}.` : "";
    if (typeof message === "string") {
      return `${message}${supportedText}`;
    }
    return JSON.stringify(data.detail);
  }

  return `Yêu cầu thất bại (${status}).`;
}

export default function DocumentsPage() {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [formats, setFormats] = useState<SupportedFormatData | null>(null);
  const [formatsError, setFormatsError] = useState<string>("");

  const [title, setTitle] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [titleError, setTitleError] = useState<string>("");
  const [fileError, setFileError] = useState<string>("");
  const [submitError, setSubmitError] = useState<string>("");
  const [submitSuccess, setSubmitSuccess] = useState<string>("");

  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const [searchTerm, setSearchTerm] = useState<string>("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [articlesError, setArticlesError] = useState<string>("");
  const [isLoadingList, setIsLoadingList] = useState<boolean>(false);

  const [selectedArticleId, setSelectedArticleId] = useState<string>("");
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [detailError, setDetailError] = useState<string>("");
  const [isLoadingDetail, setIsLoadingDetail] = useState<boolean>(false);

  const [chunkCounts, setChunkCounts] = useState<Record<string, number>>({});

  const hasApiOrigin = API_ORIGIN.length > 0;

  const visibleArticles = useMemo(
    () => articles.filter((article) => article.content.trim().length > 0),
    [articles],
  );

  const allowedExtensions = useMemo(
    () => new Set((formats?.extensions ?? []).map((ext) => ext.toLowerCase())),
    [formats],
  );

  async function fetchSupportedFormats(): Promise<void> {
    if (!hasApiOrigin) {
      setFormatsError("Thiếu NEXT_PUBLIC_API_ORIGIN. Vui lòng cấu hình biến môi trường.");
      return;
    }

    setFormatsError("");
    try {
      const response = await fetch(`${API_ORIGIN}/api/v1/articles/supported-formats`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });

      const payload = (await response.json()) as ApiEnvelope<SupportedFormatData>;

      if (!response.ok) {
        throw new Error(describeApiError(response.status, payload));
      }

      setFormats(payload.data);
    } catch (error) {
      setFormatsError(error instanceof Error ? error.message : "Không thể lấy định dạng hỗ trợ.");
    }
  }

  async function fetchArticles(search: string): Promise<void> {
    if (!hasApiOrigin) {
      return;
    }

    setArticlesError("");
    setIsLoadingList(true);

    try {
      const params = new URLSearchParams({ skip: "0", limit: "50" });
      if (search.trim()) {
        params.set("search", search.trim());
      }

      const response = await fetch(`${API_ORIGIN}/api/articles?${params.toString()}`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      const payload = (await response.json()) as ApiEnvelope<Article[]>;

      if (!response.ok) {
        throw new Error(describeApiError(response.status, payload));
      }

      const nextArticles = (payload.data ?? []).filter((item) => {
        return (
          item &&
          typeof item.id === "string" &&
          typeof item.source_file === "string" &&
          typeof item.content === "string" &&
          item.content.trim().length > 0
        );
      });

      setArticles(nextArticles);
      if (!selectedArticleId && nextArticles.length > 0) {
        setSelectedArticleId(nextArticles[0].id);
      }
    } catch (error) {
      setArticlesError(error instanceof Error ? error.message : "Không thể tải danh sách tài liệu.");
    } finally {
      setIsLoadingList(false);
    }
  }

  async function fetchArticleDetail(articleId: string): Promise<void> {
    if (!hasApiOrigin || !articleId) {
      return;
    }

    setDetailError("");
    setIsLoadingDetail(true);

    try {
      const response = await fetch(`${API_ORIGIN}/api/articles/${articleId}`, {
        method: "GET",
        headers: { Accept: "application/json" },
      });
      const payload = (await response.json()) as ApiEnvelope<Article>;

      if (!response.ok) {
        throw new Error(describeApiError(response.status, payload));
      }

      const article = payload.data;
      if (!article?.content?.trim()) {
        throw new Error("Bài viết chưa index hoàn tất nên không hiển thị.");
      }
      setSelectedArticle(article);
    } catch (error) {
      setSelectedArticle(null);
      setDetailError(error instanceof Error ? error.message : "Không thể tải chi tiết tài liệu.");
    } finally {
      setIsLoadingDetail(false);
    }
  }

  function validateSelectedFile(nextFile: File | null): boolean {
    setFileError("");

    if (!nextFile) {
      setFileError("Vui lòng chọn tài liệu để tải lên.");
      return false;
    }

    if (!formats) {
      setFileError("Chưa có dữ liệu định dạng từ API. Vui lòng thử lại.");
      return false;
    }

    const extension = getFileExtension(nextFile.name);
    if (!allowedExtensions.has(extension)) {
      setFileError(`Định dạng ${extension || "(không có)"} chưa được hỗ trợ.`);
      return false;
    }

    const maxSizeBytes = formats.max_upload_size_mb * 1024 * 1024;
    if (nextFile.size > maxSizeBytes) {
      setFileError(`Tệp vượt quá ${formats.max_upload_size_mb}MB theo cấu hình API.`);
      return false;
    }

    return true;
  }

  async function uploadDocument(): Promise<void> {
    if (isUploading) {
      return;
    }

    setTitleError("");
    setSubmitError("");
    setSubmitSuccess("");

    if (!hasApiOrigin) {
      setSubmitError("Thiếu NEXT_PUBLIC_API_ORIGIN. Không thể gọi API.");
      return;
    }

    if (!validateSelectedFile(file)) {
      return;
    }

    const chosenFile = file as File;

    setIsUploading(true);
    setUploadProgress(0);

    const form = new FormData();
    form.append("file", chosenFile);
    if (title.trim()) {
      form.append("title", title.trim());
    }

    try {
      const payload = await new Promise<{ status: number; body: unknown }>((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_ORIGIN}/api/v1/articles/upload`);
        xhr.responseType = "json";

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            setUploadProgress(Math.round((event.loaded / event.total) * 100));
          }
        };

        xhr.onload = () => {
          resolve({ status: xhr.status, body: xhr.response ?? {} });
        };

        xhr.onerror = () => {
          reject(new Error("Không thể kết nối tới server."));
        };

        xhr.send(form);
      });

      const parsed = payload.body as ApiEnvelope<IngestionData>;

      if (payload.status < 200 || payload.status >= 300) {
        const message = describeApiError(payload.status, parsed);

        if (payload.status === 422 && /title|tiêu đề/i.test(message)) {
          setTitleError(message);
        } else if ([413, 415, 422].includes(payload.status)) {
          setFileError(message);
        } else if ([500, 502, 503, 504].includes(payload.status)) {
          setSubmitError(message);
        } else {
          setSubmitError(message);
        }
        return;
      }

      const data = parsed.data;
      setChunkCounts((prev) => ({
        ...prev,
        [data.article.id]: data.chunk_count,
      }));

      setArticles((prev) => {
        const next = [data.article, ...prev.filter((item) => item.id !== data.article.id)];
        return next.filter((item) => item.content.trim().length > 0);
      });

      setSelectedArticleId(data.article.id);
      setSelectedArticle(data.article);
      setSubmitSuccess(`Tải lên thành công. Tạo ${data.chunk_count} chunks.`);
      setUploadProgress(100);
      setTitle("");
      setFile(null);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Không thể tải tệp.");
    } finally {
      setIsUploading(false);
    }
  }

  async function deleteArticle(articleId: string): Promise<void> {
    const confirmed = window.confirm("Xóa cả bản ghi SQLite và Chroma chunks");
    if (!confirmed) {
      return;
    }

    setSubmitError("");
    setSubmitSuccess("");

    try {
      const response = await fetch(`${API_ORIGIN}/api/articles/${articleId}`, {
        method: "DELETE",
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(describeApiError(response.status, payload));
      }

      setArticles((prev) => prev.filter((item) => item.id !== articleId));
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[articleId];
        return next;
      });

      if (selectedArticleId === articleId) {
        setSelectedArticleId("");
        setSelectedArticle(null);
      }

      setSubmitSuccess("Đã xóa tài liệu.");
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Xóa tài liệu thất bại.");
    }
  }

  function pickFile(next: File | null): void {
    setFile(next);
    setSubmitError("");
    setSubmitSuccess("");
    validateSelectedFile(next);
  }

  useEffect(() => {
    void fetchSupportedFormats();
    void fetchArticles("");
  }, []);

  useEffect(() => {
    if (!selectedArticleId) {
      return;
    }

    const snapshot = articles.find((item) => item.id === selectedArticleId) ?? null;
    if (snapshot?.content?.trim()) {
      setSelectedArticle(snapshot);
    }
    void fetchArticleDetail(selectedArticleId);
  }, [selectedArticleId]);

  return (
    <main>
      <section className={styles.shell}>
        <header className={styles.hero}>
          <h1>Documents</h1>
          <p>Upload và quản lý file theo luồng ingest của hệ thống RAG.</p>
        </header>

        {!hasApiOrigin && <div className={styles.alert}>Thiếu NEXT_PUBLIC_API_ORIGIN trong môi trường.</div>}
        {formatsError && <div className={styles.alert}>{formatsError}</div>}

        <div className={styles.grid}>
          <article className={styles.card} aria-label="Khu vực upload tài liệu">
            <h2>Tải tài liệu mới</h2>
            <div className={styles.form}>
              <label className={styles.label} htmlFor="title-input">
                <span className={styles.labelText}>Tiêu đề (Optional)</span>
                <input
                  id="title-input"
                  className={styles.input}
                  type="text"
                  value={title}
                  placeholder="Ví dụ: Hướng dẫn vận hành v1"
                  onChange={(event) => setTitle(event.target.value)}
                />
                {titleError && <span className={styles.errorText}>{titleError}</span>}
              </label>

              <input
                ref={inputRef}
                id="file-input"
                className={styles.srOnly}
                type="file"
                onChange={(event) => pickFile(event.target.files?.[0] ?? null)}
                disabled={!formats || isUploading}
              />

              <button
                type="button"
                className={`${styles.dropZone} ${isDragging ? styles.dropActive : ""}`}
                onClick={() => inputRef.current?.click()}
                onDragOver={(event) => {
                  event.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(event) => {
                  event.preventDefault();
                  setIsDragging(false);
                  pickFile(event.dataTransfer.files?.[0] ?? null);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    inputRef.current?.click();
                  }
                }}
                disabled={!formats || isUploading}
              >
                <span className={styles.labelText}>Kéo thả file vào đây hoặc bấm để chọn</span>
                <span className={styles.helpText}>{file ? `Đã chọn: ${file.name}` : "Chưa chọn tệp"}</span>
              </button>

              {fileError && <span className={styles.errorText}>{fileError}</span>}
              {formats && (
                <p className={styles.helpText}>
                  Hỗ trợ: {formats.extensions.join(", ")} | Giới hạn: {formats.max_upload_size_mb}MB
                </p>
              )}

              {isUploading && (
                <div>
                  <div className={styles.progressWrap} aria-label="Tiến trình upload">
                    <div className={styles.progressBar} style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <p className={styles.helpText}>Processing {uploadProgress}%</p>
                </div>
              )}

              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={() => void uploadDocument()}
                  disabled={!formats || !hasApiOrigin || isUploading}
                >
                  {isUploading ? "Đang xử lý..." : "Upload"}
                </button>
                <button
                  type="button"
                  className={styles.ghostButton}
                  onClick={() => {
                    setTitle("");
                    setFile(null);
                    setTitleError("");
                    setFileError("");
                    setSubmitError("");
                    setSubmitSuccess("");
                    if (inputRef.current) {
                      inputRef.current.value = "";
                    }
                  }}
                  disabled={isUploading}
                >
                  Làm mới form
                </button>
              </div>

              {submitError && <div className={styles.alert}>{submitError}</div>}
              {submitSuccess && <div className={styles.ok}>{submitSuccess}</div>}
            </div>
          </article>

          <article className={styles.card} aria-label="Danh sách tài liệu">
            <h2>Danh sách tài liệu</h2>
            <form
              className={styles.searchRow}
              onSubmit={(event) => {
                event.preventDefault();
                void fetchArticles(searchTerm);
              }}
            >
              <input
                className={styles.input}
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Tìm theo tiêu đề hoặc tên file"
              />
              <button type="submit" className={styles.searchButton}>
                Tìm
              </button>
            </form>

            {articlesError && <div className={styles.alert}>{articlesError}</div>}
            {isLoadingList && <p className={styles.helpText}>Đang tải danh sách...</p>}

            <ul className={styles.list}>
              {visibleArticles.map((article) => {
                const extension = getFileExtension(article.source_file) || "(none)";
                return (
                  <li key={article.id}>
                    <button
                      type="button"
                      className={styles.listButton}
                      aria-current={selectedArticleId === article.id}
                      onClick={() => setSelectedArticleId(article.id)}
                    >
                      <strong>{article.title}</strong>
                      <div className={styles.listMeta}>
                        {article.source_file} | {extension} | cập nhật {formatDate(article.updated_at)}
                      </div>
                      {chunkCounts[article.id] !== undefined && (
                        <span className={styles.badge}>{chunkCounts[article.id]} chunks</span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </article>
        </div>

        <article className={styles.card} aria-label="Chi tiết tài liệu">
          <h2>Chi tiết</h2>
          <div className={styles.detail}>
            {detailError && <div className={styles.alert}>{detailError}</div>}
            {isLoadingDetail && <p className={styles.helpText}>Đang tải nội dung chi tiết...</p>}

            {!selectedArticle && !isLoadingDetail && <p className={styles.helpText}>Chọn một tài liệu để xem nội dung.</p>}

            {selectedArticle && (
              <>
                <header className={styles.detailHeader}>
                  <div>
                    <h3>{selectedArticle.title}</h3>
                    <div className={styles.listMeta}>
                      {selectedArticle.source_file} | cập nhật {formatDate(selectedArticle.updated_at)}
                    </div>
                    {chunkCounts[selectedArticle.id] !== undefined && (
                      <span className={styles.badge}>{chunkCounts[selectedArticle.id]} chunks</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className={styles.deleteButton}
                    onClick={() => void deleteArticle(selectedArticle.id)}
                  >
                    Xóa tài liệu
                  </button>
                </header>

                <div className={styles.markdown}>
                  <ReactMarkdown>{selectedArticle.content}</ReactMarkdown>
                </div>
              </>
            )}
          </div>
        </article>
      </section>
    </main>
  );
}
