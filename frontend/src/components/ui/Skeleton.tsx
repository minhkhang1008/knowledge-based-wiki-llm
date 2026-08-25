/** Neutral shimmer block used to mirror the final content layout. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-md bg-hover ${className}`}
      aria-hidden="true"
    />
  );
}
