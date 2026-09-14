"use client";

import { useState, useEffect, FormEvent, useRef } from "react";
import {
  fetchSupportedFormats,
  listArticles,
  uploadArticle,
  getArticle,
  deleteArticle,
} from "@/lib/api/articles";
import type { Article, SupportedFormatsData } from "@/types/api";
import { Button } from "@/components/ui/Button";
import { SearchIcon, CloseIcon } from "@/components/ui/Icons";
import ReactMarkdown from "react-markdown";

export default function DocumentsPage() {
  const [formats, setFormats] = useState<SupportedFormatsData | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    chunks_created: number;
  } | null>(null);
  const [uploadError, setUploadError] = useState("");

  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);

  const [articleToDelete, setArticleToDelete] = useState<Article | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadFormats();
    loadArticles();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadArticles(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  async function loadFormats() {
    try {
      const res = await fetchSupportedFormats();
      setFormats(res);
    } catch (e: any) {
      console.error("Failed to fetch formats", e);
    }
  }

  async function loadArticles(search = "") {
    try {
      setIsLoading(true);
      const res = await listArticles({ search, limit: 100 });
      setArticles(res);
    } catch (e: any) {
      console.error("Failed to load articles", e);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;

    if (formats && file.size > formats.max_upload_size_mb * 1024 * 1024) {
      setUploadError(`File is too large. Max size is ${formats.max_upload_size_mb}MB.`);
      return;
    }

    try {
      setIsUploading(true);
      setUploadError("");
      setUploadResult(null);

      const formData = new FormData();
      formData.append("file", file);
      if (title.trim()) {
        formData.append("title", title.trim());
      }

      const res = await uploadArticle(formData);
      setUploadResult({ chunks_created: res.chunks_created });
      setFile(null);
      setTitle("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      loadArticles(searchQuery);
    } catch (e: any) {
      setUploadError(e.message || "Failed to upload file");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleViewArticle(id: string) {
    try {
      setIsDetailLoading(true);
      const article = await getArticle(id);
      setSelectedArticle(article);
    } catch (e: any) {
      console.error("Failed to load article detail", e);
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function handleDeleteConfirm() {
    if (!articleToDelete) return;
    try {
      setIsDeleting(true);
      await deleteArticle(articleToDelete.id);
      setArticleToDelete(null);
      if (selectedArticle?.id === articleToDelete.id) {
        setSelectedArticle(null);
      }
      loadArticles(searchQuery);
    } catch (e: any) {
      if (e.status === 404 || e.kind === "not_found") {
        // Already deleted
        setArticleToDelete(null);
        if (selectedArticle?.id === articleToDelete.id) {
          setSelectedArticle(null);
        }
        loadArticles(searchQuery);
      } else {
        console.error("Failed to delete article", e);
        // Optional: you could add a setDeleteError here, but closing it might be jarring if it's a real error.
        // For now, we'll keep it open on other errors so the user sees it didn't work.
      }
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-4 md:p-6 lg:p-8">
      <h1 className="mb-6 text-2xl font-bold text-ink">Documents</h1>

      <div className="grid gap-6 md:grid-cols-[300px_1fr]">
        {/* Upload Section */}
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-ink">Upload Document</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-ink">
                File
              </label>
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  className="w-full rounded-lg border border-line bg-canvas p-2 text-sm text-ink file:mr-4 file:rounded-full file:border-0 file:bg-elevated file:px-4 file:py-1 file:text-sm file:font-semibold file:text-ink hover:file:bg-hover"
                  onChange={(e) => {
                    setFile(e.target.files?.[0] || null);
                    setUploadResult(null);
                    setUploadError("");
                  }}
                  accept={formats?.extensions.map((ext) => ext.startsWith('.') ? ext : `.${ext}`).join(",")}
                />
                {file && (
                  <button
                    type="button"
                    onClick={() => {
                      setFile(null);
                      setUploadResult(null);
                      setUploadError("");
                      if (fileInputRef.current) {
                        fileInputRef.current.value = "";
                      }
                    }}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-red-500"
                    title="Remove file"
                  >
                    <CloseIcon className="h-5 w-5" />
                  </button>
                )}
              </div>
              {formats && (
                <p className="mt-1 text-xs text-muted">
                  Supported formats: {formats.extensions.join(", ")}. Max size:{" "}
                  {formats.max_upload_size_mb}MB.
                </p>
              )}
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-ink">
                Title (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a title..."
                className="w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder-faint focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {uploadError && (
              <div className="rounded-md bg-red-500/10 p-3 text-sm text-red-500">
                {uploadError}
              </div>
            )}

            {uploadResult && (
              <div className="rounded-md bg-green-500/10 p-3 text-sm text-green-600">
                Successfully uploaded! Created {uploadResult.chunks_created}{" "}
                chunks.
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full"
              disabled={!file || isUploading}
            >
              {isUploading ? "Uploading & Processing..." : "Upload"}
            </Button>
          </form>
        </div>

        {/* List Section */}
        <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
          <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <h2 className="text-lg font-semibold text-ink">Your Documents</h2>
            <div className="relative">
              <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
              <input
                type="text"
                placeholder="Search by title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-full border border-line bg-canvas py-1.5 pl-9 pr-4 text-sm text-ink placeholder-faint focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-64"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="py-8 text-center text-sm text-muted">Loading...</div>
          ) : articles.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted">
              {searchQuery
                ? "No documents matched your search."
                : "No documents uploaded yet."}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-muted">
                    <th className="pb-2 pl-2 font-medium">Title</th>
                    <th className="pb-2 font-medium">Source File</th>
                    <th className="pb-2 font-medium">Format</th>
                    <th className="pb-2 font-medium">Updated</th>
                    <th className="pb-2 pr-2 text-right font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {articles.map((article) => {
                    const ext = article.source_file.split('.').pop()?.toUpperCase() || 'UNKNOWN';
                    return (
                    <tr
                      key={article.id}
                      className="group transition-colors hover:bg-hover"
                    >
                      <td className="py-3 pl-2 font-medium text-ink">
                        {article.title}
                      </td>
                      <td className="py-3 text-muted">{article.source_file}</td>
                      <td className="py-3 text-muted">{ext}</td>
                      <td className="py-3 text-muted">
                        {new Date(article.updated_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 pr-2 text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            className="h-8 px-3 text-xs"
                            onClick={() => handleViewArticle(article.id)}
                          >
                            View
                          </Button>
                          <Button
                            variant="ghost"
                            className="h-8 px-3 text-xs text-red-500 hover:bg-red-500/10 hover:text-red-600"
                            onClick={() => setArticleToDelete(article)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  )})}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedArticle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-xl bg-surface shadow-lg">
            <div className="flex items-center justify-between border-b border-line p-4">
              <h2 className="font-semibold text-ink">{selectedArticle.title}</h2>
              <button
                onClick={() => setSelectedArticle(null)}
                className="rounded-lg p-1 text-muted hover:bg-hover hover:text-ink"
              >
                <CloseIcon className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 md:p-6 prose prose-sm max-w-none dark:prose-invert">
              <ReactMarkdown>{selectedArticle.content}</ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {articleToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
            <h3 className="mb-2 text-lg font-semibold text-ink">
              Delete Document
            </h3>
            <p className="mb-6 text-sm text-muted">
              Are you sure you want to delete{" "}
              <span className="font-medium text-ink">
                {articleToDelete.title}
              </span>
              ? This action will permanently remove the article from the SQLite
              database and delete all of its corresponding chunks from ChromaDB.
            </p>
            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                onClick={() => setArticleToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                className="bg-red-500 text-white hover:bg-red-600"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Yes, Delete"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
