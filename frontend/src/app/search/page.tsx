export default function Page() {
  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:py-10">
      <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
        Search
      </h1>
      <p className="mt-1.5 text-sm text-muted">Run a semantic search and inspect the matching source chunks.</p>
      <div className="mt-8 rounded-2xl border border-dashed border-line bg-elevated px-6 py-14 text-center">
        <p className="text-sm font-medium text-ink">Screen not implemented yet</p>
        <p className="mx-auto mt-1 max-w-md text-sm text-muted">
          This route is a placeholder so Dashboard navigation resolves. Build it
          against the shared API layer in src/lib/api.
        </p>
      </div>
    </div>
  );
}
