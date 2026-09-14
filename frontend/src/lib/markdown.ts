import { API_BASE_URL } from "@/lib/api/client";

const INTERNAL_COMMENT_PATTERN =
  /<!--\s*(?:ocr-meta|page):[\s\S]*?-->\s*/gi;

export function markdownForDisplay(markdown: string): string {
  return markdown.replace(INTERNAL_COMMENT_PATTERN, "").trim();
}

export function documentAssetUrl(documentId: string, rawSource: string): string {
  if (/^(?:https?:|data:|blob:)/i.test(rawSource)) return rawSource;

  const segments = rawSource
    .replace(/^\.\//, "")
    .split("/")
    .filter((segment) => segment !== "" && segment !== ".");

  if (segments[0] === documentId) segments.shift();
  if (segments.length === 0 || segments.some((segment) => segment === "..")) {
    return rawSource;
  }

  return `${API_BASE_URL}/api/v1/articles/${encodeURIComponent(documentId)}/assets/${segments.map(encodeURIComponent).join("/")}`;
}
