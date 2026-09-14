"use client";

import Image from "next/image";
import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import {
  deleteArticle,
  fetchSupportedFormats,
  getArticle,
  listArticles,
  uploadArticle,
} from "@/lib/api/articles";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { documentAssetUrl, markdownForDisplay } from "@/lib/markdown";
import type { Article, SupportedFormatsData } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CloseIcon,
  DocumentsIcon,
  SearchIcon,
  TrashIcon,
  UploadIcon,
} from "@/components/ui/Icons";

const PAGE_SIZE = 20;
const passthroughImageLoader = ({ src }: { src: string }) => src;

export default function DocumentsPage() {
  const [formats, setFormats] = useState<SupportedFormatsData | null>(null);
  const [formatsError, setFormatsError] = useState("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const [hasNextPage, setHasNextPage] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [listError, setListError] = useState("");

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState("");

  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const [articleToDelete, setArticleToDelete] = useState<Article | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadRequestRef = useRef<AbortController | null>(null);
  const detailRequestRef = useRef<AbortController | null>(null);
  const deleteRequestRef = useRef<AbortController | null>(null);

  useEffect(
    () => () => {
      uploadRequestRef.current?.abort();
      detailRequestRef.current?.abort();
      deleteRequestRef.current?.abort();
      uploadRequestRef.current = null;
      detailRequestRef.current = null;
      deleteRequestRef.current = null;
    },
    [],
  );

  const loadFormats = useCallback(async (signal?: AbortSignal) => {
    try {
      setFormatsError("");
      setFormats(await fetchSupportedFormats(signal));
    } catch (cause) {
      if (signal?.aborted) return;
      setFormatsError(errorMessage(cause));
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void loadFormats(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [loadFormats]);

  const loadArticles = useCallback(
    async (signal?: AbortSignal) => {
      try {
        setIsLoading(true);
        setListError("");
        const results = await listArticles(
          {
            search: searchQuery,
            skip: page * PAGE_SIZE,
            limit: PAGE_SIZE + 1,
          },
          signal,
        );
        setHasNextPage(results.length > PAGE_SIZE);
        setArticles(results.slice(0, PAGE_SIZE));
      } catch (cause) {
        if (signal?.aborted) return;
        setArticles([]);
        setHasNextPage(false);
        setListError(errorMessage(cause));
      } finally {
        if (!signal?.aborted) setIsLoading(false);
      }
    },
    [page, searchQuery],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(
      () => void loadArticles(controller.signal),
      searchQuery ? 300 : 0,
    );
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [loadArticles, searchQuery]);

  function clearFile() {
    setFile(null);
    setUploadResult(null);
    setUploadError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;

    if (formats && file.size > formats.max_upload_size_mb * 1024 * 1024) {
      setUploadError(
        `File is too large. The maximum size is ${formats.max_upload_size_mb} MB.`,
      );
      return;
    }

    const controller = new AbortController();
    uploadRequestRef.current?.abort();
    uploadRequestRef.current = controller;
    try {
      setIsUploading(true);
      setUploadError("");
      setUploadResult(null);
      const formData = new FormData();
      formData.append("file", file);
      if (title.trim()) formData.append("title", title.trim());

      const result = await uploadArticle(formData, controller.signal);
      setUploadResult(result.chunk_count);
      setFile(null);
      setTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (page === 0) {
        await loadArticles();
      } else {
        setPage(0);
      }
    } catch (cause) {
      if (controller.signal.aborted) return;
      setUploadError(errorMessage(cause));
    } finally {
      if (uploadRequestRef.current === controller) {
        setIsUploading(false);
        uploadRequestRef.current = null;
      }
    }
  }

  async function handleViewArticle(id: string) {
    const controller = new AbortController();
    detailRequestRef.current?.abort();
    detailRequestRef.current = controller;
    try {
      setIsDetailLoading(true);
      setDetailError("");
      setSelectedArticle(await getArticle(id, controller.signal));
    } catch (cause) {
      if (controller.signal.aborted) return;
      setDetailError(errorMessage(cause));
    } finally {
      if (detailRequestRef.current === controller) {
        setIsDetailLoading(false);
        detailRequestRef.current = null;
      }
    }
  }

  const closeDetail = useCallback(() => setSelectedArticle(null), []);
  const closeDelete = useCallback(() => {
    if (!isDeleting) {
      setArticleToDelete(null);
      setDeleteError("");
    }
  }, [isDeleting]);

  async function handleDeleteConfirm() {
    if (!articleToDelete) return;
    const controller = new AbortController();
    deleteRequestRef.current?.abort();
    deleteRequestRef.current = controller;
    try {
      setIsDeleting(true);
      setDeleteError("");
      await deleteArticle(articleToDelete.id, controller.signal);
      if (selectedArticle?.id === articleToDelete.id) setSelectedArticle(null);
      setArticleToDelete(null);
      if (articles.length === 1 && page > 0) {
        setPage((value) => Math.max(0, value - 1));
      } else {
        await loadArticles(controller.signal);
      }
    } catch (cause) {
      if (controller.signal.aborted) return;
      if (cause instanceof ApiError && cause.kind === "not_found") {
        setArticleToDelete(null);
        await loadArticles(controller.signal);
      } else {
        setDeleteError(errorMessage(cause));
      }
    } finally {
      if (deleteRequestRef.current === controller) {
        setIsDeleting(false);
        deleteRequestRef.current = null;
      }
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
      <header className="mb-7">
        <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
          Documents
        </h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-muted">
          Upload source files, inspect extracted Markdown, and manage the indexed
          knowledge base.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <section className="self-start rounded-xl border border-line bg-surface p-5 shadow-sm">
          <div className="mb-5 flex items-center gap-2">
            <UploadIcon className="h-5 w-5 text-muted" aria-hidden="true" />
            <h2 className="text-base font-semibold text-ink">Upload document</h2>
          </div>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label htmlFor="document-file" className="mb-1.5 block text-sm font-medium text-ink">
                File
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="document-file"
                  ref={fileInputRef}
                  type="file"
                  className="min-w-0 flex-1 rounded-lg border border-line bg-canvas p-2 text-sm text-ink file:mr-3 file:rounded-md file:border-0 file:bg-hover file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink"
                  onChange={(event) => {
                    setFile(event.target.files?.[0] ?? null);
                    setUploadResult(null);
                    setUploadError("");
                  }}
                  accept={formats?.extensions
                    .map((extension) =>
                      extension.startsWith(".") ? extension : `.${extension}`,
                    )
                    .join(",")}
                />
                {file ? (
                  <button
                    type="button"
                    onClick={clearFile}
                    className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-danger"
                    aria-label="Remove selected file"
                  >
                    <CloseIcon className="h-5 w-5" aria-hidden="true" />
                  </button>
                ) : null}
              </div>
              {formats ? (
                <p className="mt-2 text-xs leading-5 text-muted">
                  {formats.extensions.join(", ")} up to {formats.max_upload_size_mb} MB.
                </p>
              ) : null}
              {formatsError ? (
                <div className="mt-2 text-xs text-danger" role="alert">
                  {formatsError}{" "}
                  <button type="button" className="font-medium underline" onClick={() => void loadFormats()}>
                    Retry
                  </button>
                </div>
              ) : null}
            </div>

            <div>
              <label htmlFor="document-title" className="mb-1.5 block text-sm font-medium text-ink">
                Title <span className="font-normal text-muted">(optional)</span>
              </label>
              <input
                id="document-title"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Quarterly handbook"
                className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-faint"
              />
            </div>

            {uploadError ? (
              <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
                {uploadError}
              </p>
            ) : null}
            {uploadResult !== null ? (
              <p role="status" className="rounded-lg border border-line bg-elevated p-3 text-sm text-ink">
                Upload complete. {uploadResult} {uploadResult === 1 ? "chunk" : "chunks"} indexed.
              </p>
            ) : null}

            <Button type="submit" variant="primary" className="w-full" disabled={!file || isUploading}>
              <UploadIcon className="h-4 w-4" aria-hidden="true" />
              {isUploading ? "Processing..." : "Upload"}
            </Button>
          </form>
        </section>

        <section className="min-w-0 rounded-xl border border-line bg-surface p-5 shadow-sm">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-base font-semibold text-ink">Indexed documents</h2>
            <div className="relative w-full sm:w-72">
              <label htmlFor="document-search" className="sr-only">Search documents by title</label>
              <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
              <input
                id="document-search"
                type="search"
                placeholder="Search by title"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setPage(0);
                }}
                className="w-full rounded-lg border border-line bg-canvas py-2 pl-9 pr-3 text-sm text-ink placeholder:text-faint"
              />
            </div>
          </div>

          {detailError ? (
            <p role="alert" className="mb-4 rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
              Could not open the document. {detailError}
            </p>
          ) : null}

          {listError ? (
            <div role="alert" className="rounded-lg border border-danger/30 bg-danger/10 p-5 text-sm text-danger">
              <p className="font-medium">Could not load documents.</p>
              <p className="mt-1">{listError}</p>
              <Button className="mt-4" onClick={() => void loadArticles()}>
                Retry
              </Button>
            </div>
          ) : isLoading ? (
            <div className="space-y-3" aria-label="Loading documents" aria-busy="true">
              {[0, 1, 2].map((item) => (
                <div key={item} className="h-12 animate-pulse rounded-lg bg-hover" />
              ))}
            </div>
          ) : articles.length === 0 ? (
            <div className="flex min-h-52 flex-col items-center justify-center rounded-lg border border-dashed border-line px-6 text-center">
              <DocumentsIcon className="h-8 w-8 text-faint" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-ink">
                {searchQuery ? "No matching documents" : "No documents yet"}
              </p>
              <p className="mt-1 max-w-sm text-sm text-muted">
                {searchQuery
                  ? "Try a different title or clear the search field."
                  : "Choose a supported file to create your first searchable document."}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-line text-muted">
                      <th className="pb-2 pl-2 font-medium">Title</th>
                      <th className="pb-2 font-medium">Source</th>
                      <th className="pb-2 font-medium">Format</th>
                      <th className="pb-2 font-medium">Updated</th>
                      <th className="pb-2 pr-2 text-right font-medium">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {articles.map((article) => (
                      <tr key={article.id} className="transition-colors hover:bg-hover">
                        <td className="max-w-56 truncate py-3 pl-2 font-medium text-ink">{article.title}</td>
                        <td className="max-w-44 truncate py-3 text-muted">{article.source_file}</td>
                        <td className="py-3 font-mono text-xs text-muted">
                          {article.source_file.split(".").pop()?.toUpperCase() ?? "UNKNOWN"}
                        </td>
                        <td className="py-3 text-muted">
                          {new Date(article.updated_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 pr-2">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              className="h-8 px-3 text-xs"
                              onClick={() => void handleViewArticle(article.id)}
                              disabled={isDetailLoading}
                              aria-label={`View ${article.title}`}
                            >
                              {isDetailLoading ? "Loading..." : "View"}
                            </Button>
                            <Button
                              variant="ghost"
                              className="h-8 px-3 text-xs text-danger hover:bg-danger/10 hover:text-danger"
                              onClick={() => {
                                setArticleToDelete(article);
                                setDeleteError("");
                              }}
                              aria-label={`Delete ${article.title}`}
                            >
                              <TrashIcon className="h-3.5 w-3.5" aria-hidden="true" />
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-line pt-4">
                <span className="text-xs text-muted">Page {page + 1}</span>
                <div className="flex gap-2">
                  <Button variant="ghost" className="h-8 px-3 text-xs" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>
                    <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" /> Previous
                  </Button>
                  <Button variant="ghost" className="h-8 px-3 text-xs" disabled={!hasNextPage} onClick={() => setPage((value) => value + 1)}>
                    Next <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </section>
      </div>

      {selectedArticle ? (
        <Modal title={selectedArticle.title} description={selectedArticle.source_file} onClose={closeDetail} size="lg">
          <div className="prose prose-sm max-w-none flex-1 overflow-y-auto p-5 dark:prose-invert sm:p-6">
            <ReactMarkdown
              components={{
                img: ({ src, alt }) =>
                  typeof src === "string" ? (
                    <Image
                      loader={passthroughImageLoader}
                      unoptimized
                      src={documentAssetUrl(selectedArticle.document_id, src)}
                      alt={alt ?? "Extracted document image"}
                      width={1200}
                      height={800}
                      className="h-auto max-w-full rounded-lg border border-line"
                    />
                  ) : null,
              }}
            >
              {markdownForDisplay(selectedArticle.content)}
            </ReactMarkdown>
          </div>
        </Modal>
      ) : null}

      {articleToDelete ? (
        <Modal
          title="Delete document"
          description="This removes the article and every matching vector chunk."
          onClose={closeDelete}
          showCloseButton={!isDeleting}
        >
          <div className="p-5">
            <p className="text-sm leading-6 text-muted">
              Delete <span className="font-medium text-ink">{articleToDelete.title}</span>? This action cannot be undone.
            </p>
            {deleteError ? (
              <p role="alert" className="mt-4 rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
                {deleteError}
              </p>
            ) : null}
            <div className="mt-6 flex justify-end gap-3">
              <Button variant="ghost" onClick={closeDelete} disabled={isDeleting}>Cancel</Button>
              <Button className="bg-danger text-white hover:opacity-90" onClick={() => void handleDeleteConfirm()} disabled={isDeleting}>
                {isDeleting ? "Deleting..." : "Delete"}
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
