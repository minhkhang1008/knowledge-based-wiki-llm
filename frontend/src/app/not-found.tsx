import Link from "next/link";

export default function NotFound() {
  return (
    <div className="mx-auto w-full max-w-2xl px-4 py-20 text-center sm:px-6">
      <p className="font-mono text-xs uppercase tracking-widest text-faint">
        404
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink">
        Page not found
      </h1>
      <p className="mt-2 text-sm text-muted">
        The page you were looking for does not exist.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center rounded-full bg-ink px-4 py-2 text-sm font-medium text-canvas transition-opacity hover:opacity-90"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}
