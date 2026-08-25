"use client";

import Link from "next/link";
import { NAV_ITEMS } from "@/components/layout/navigation";
import { ArrowRightIcon } from "@/components/ui/Icons";

/** Quick links to Documents, Search, and Ask. */
export function QuickLinks() {
  const items = NAV_ITEMS.filter((item) => item.href !== "/");

  return (
    <section aria-labelledby="quick-links-heading" className="mt-10">
      <h2
        id="quick-links-heading"
        className="text-sm font-semibold text-ink"
      >
        Continue working
      </h2>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="group flex flex-col gap-3 rounded-2xl border border-line bg-elevated p-4 transition-colors hover:bg-hover"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface text-muted group-hover:text-ink">
                <Icon className="h-[18px] w-[18px]" />
              </span>
              <span className="flex items-center gap-1.5 text-sm font-medium text-ink">
                {item.label}
                <ArrowRightIcon className="h-4 w-4 -translate-x-1 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
              </span>
              <span className="text-xs leading-relaxed text-muted">
                {item.description}
              </span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
