"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV_ITEMS } from "./navigation";
import { CloseIcon, SparkIcon } from "@/components/ui/Icons";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Fixed rail on desktop, slide-over drawer under 768 px.
 * Mirrors the ChatGPT sidebar: quiet background, pill-shaped active row.
 */
export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile scrim */}
      <div
        className={`fixed inset-0 z-30 bg-black/40 transition-opacity md:hidden ${
          isOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside
        id="app-sidebar"
        aria-label="Main navigation"
        className={`fixed inset-y-0 left-0 z-40 flex w-[260px] flex-col border-r border-line bg-surface transition-transform duration-200 md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-3 py-3">
          <Link
            href="/"
            className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm font-semibold text-ink transition-colors hover:bg-hover"
            onClick={onClose}
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-elevated">
              <SparkIcon className="h-4 w-4" />
            </span>
            Knowledge Wiki
          </Link>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-ink md:hidden"
          >
            <CloseIcon className="h-[18px] w-[18px]" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-4">
          <p className="px-2 pb-2 pt-3 text-xs font-medium text-faint">
            Workspace
          </p>
          <ul className="space-y-1">
            {NAV_ITEMS.map((item) => {
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              const Icon = item.icon;

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onClose}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-hover font-medium text-ink"
                        : "text-muted hover:bg-hover hover:text-ink"
                    }`}
                  >
                    <Icon className="h-[18px] w-[18px] shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-line px-4 py-3">
          <p className="text-xs text-faint">
            Local-first RAG over your own documents.
          </p>
        </div>
      </aside>
    </>
  );
}
