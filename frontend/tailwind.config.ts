import type { Config } from "tailwindcss";
import tailwindAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
    "./modules/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // ── PAC Surface Palette ──────────────────────────────
        bg: {
          base:     "#0d1117",
          surface:  "#161b22",
          elevated: "#21262d",
          input:    "#0d1117",
          overlay:  "rgba(1,4,9,0.8)",
        },
        border: {
          DEFAULT: "#30363d",
          focus:   "#58a6ff",
          muted:   "#21262d",
        },
        // ── PAC Text Palette ─────────────────────────────────
        text: {
          primary: "#e6edf3",
          muted:   "#8b949e",
          subtle:  "#484f58",
          inverse: "#0d1117",
        },
        // ── PAC Intelligence Semantic Colours ────────────────
        critical: {
          DEFAULT: "#f85149",
          subtle:  "rgba(248,81,73,0.15)",
          border:  "rgba(248,81,73,0.4)",
        },
        high: {
          DEFAULT: "#e98d30",
          subtle:  "rgba(233,141,48,0.15)",
          border:  "rgba(233,141,48,0.4)",
        },
        moderate: {
          DEFAULT: "#d29922",
          subtle:  "rgba(210,153,34,0.15)",
          border:  "rgba(210,153,34,0.4)",
        },
        low: {
          DEFAULT: "#3fb950",
          subtle:  "rgba(63,185,80,0.15)",
          border:  "rgba(63,185,80,0.4)",
        },
        info: {
          DEFAULT: "#58a6ff",
          subtle:  "rgba(88,166,255,0.15)",
          border:  "rgba(88,166,255,0.4)",
        },
        // ── Intelligence Accent ──────────────────────────────
        purple: {
          DEFAULT: "#bc8cff",
          subtle:  "rgba(188,140,255,0.15)",
          border:  "rgba(188,140,255,0.4)",
        },
        // ── Interactive Accent ───────────────────────────────
        accent: {
          DEFAULT: "#1f6feb",
          hover:   "#388bfd",
          muted:   "rgba(31,111,235,0.15)",
        },
        // shadcn compatibility
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        input:   "hsl(var(--input))",
        ring:    "hsl(var(--ring))",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "page-title":    ["1.25rem",  { lineHeight: "1.75rem", fontWeight: "600" }],
        "section-title": ["1rem",     { lineHeight: "1.5rem",  fontWeight: "600" }],
        "card-title":    ["0.875rem", { lineHeight: "1.25rem", fontWeight: "500" }],
        body:            ["0.875rem", { lineHeight: "1.25rem", fontWeight: "400" }],
        caption:         ["0.75rem",  { lineHeight: "1rem",    fontWeight: "400" }],
        mono:            ["0.8125rem",{ lineHeight: "1.25rem", fontWeight: "400" }],
      },
      spacing: {
        "1":  "4px",
        "2":  "8px",
        "3":  "12px",
        "4":  "16px",
        "5":  "20px",
        "6":  "24px",
        "8":  "32px",
        "10": "40px",
        "12": "48px",
        "16": "64px",
        "20": "80px",
      },
      borderRadius: {
        sm:  "4px",
        DEFAULT: "6px",
        md:  "8px",
        lg:  "12px",
        xl:  "16px",
        "2xl": "20px",
        full: "9999px",
        // shadcn
        var: "var(--radius)",
      },
      boxShadow: {
        "card":    "0 1px 0 rgba(255,255,255,0.04), 0 0 0 1px #30363d",
        "elevated":"0 8px 24px rgba(1,4,9,0.6), 0 0 0 1px #30363d",
        "critical":"0 0 0 1px rgba(248,81,73,0.4), 0 4px 12px rgba(248,81,73,0.2)",
        "focus":   "0 0 0 3px rgba(88,166,255,0.3)",
        "glow-red":"0 0 12px rgba(248,81,73,0.5)",
        "glow-blue":"0 0 12px rgba(88,166,255,0.5)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "fade-in":    "fadeIn 0.2s ease-out",
        "slide-in":   "slideIn 0.25s ease-out",
        shimmer:      "shimmer 1.5s infinite",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0", transform: "translateY(-4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      transitionDuration: {
        fast:   "100ms",
        normal: "200ms",
        slow:   "300ms",
      },
    },
  },
  plugins: [tailwindAnimate],
};

export default config;
