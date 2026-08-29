import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--sb-canvas) / <alpha-value>)",
        surface: "rgb(var(--sb-surface) / <alpha-value>)",
        elevated: "rgb(var(--sb-elevated) / <alpha-value>)",
        hover: "rgb(var(--sb-hover) / <alpha-value>)",
        line: "rgb(var(--sb-line) / <alpha-value>)",
        ink: "rgb(var(--sb-ink) / <alpha-value>)",
        muted: "rgb(var(--sb-muted) / <alpha-value>)",
        faint: "rgb(var(--sb-faint) / <alpha-value>)",
        accent: "rgb(var(--sb-accent) / <alpha-value>)",
        danger: "rgb(var(--sb-danger) / <alpha-value>)",
        warning: "rgb(var(--sb-warning) / <alpha-value>)",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.25rem",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 240ms ease-out both",
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};

export default config;
