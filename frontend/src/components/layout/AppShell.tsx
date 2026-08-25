"use client";

import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { ThemeToggle } from "./ThemeToggle";
import { MenuIcon } from "@/components/ui/Icons";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#main-content"
        className="sr-only-focusable absolute left-4 top-4 z-50 rounded-lg bg-ink px-3 py-2 text-sm font-medium text-canvas"
      >
        Skip to main content
      </a>

      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <div className="md:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b border-line bg-canvas/85 px-3 backdrop-blur md:px-6">
          <button
            type="button"
            onClick={() => setIsSidebarOpen(true)}
            aria-label="Open navigation"
            aria-controls="app-sidebar"
            aria-expanded={isSidebarOpen}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg text-muted hover:bg-hover hover:text-ink md:hidden"
          >
            <MenuIcon className="h-[18px] w-[18px]" />
          </button>
          <span className="text-sm font-medium text-ink md:hidden">
            Knowledge Wiki
          </span>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
          </div>
        </header>

        <main id="main-content" tabIndex={-1} className="focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}
