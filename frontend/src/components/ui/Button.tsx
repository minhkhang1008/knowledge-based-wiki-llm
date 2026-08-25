"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  children: ReactNode;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary:
    "bg-ink text-canvas hover:opacity-90 disabled:opacity-40",
  secondary:
    "border border-line bg-elevated text-ink hover:bg-hover disabled:opacity-40",
  ghost: "text-muted hover:bg-hover hover:text-ink disabled:opacity-40",
};

export function Button({
  variant = "secondary",
  className = "",
  children,
  type = "button",
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed ${VARIANT_CLASS[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  );
}
