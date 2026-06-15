import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta quente e profissional — "escritório", não "IA genérica"
        sand: {
          50: "#faf7f2",
          100: "#f3ece0",
          200: "#e7d9c4",
        },
        ink: {
          700: "#3f3a34",
          800: "#2c2924",
          900: "#1c1a17",
        },
        accent: {
          400: "#f0a44b",
          500: "#e8872b",
          600: "#cf6f1a",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(28,26,23,.06), 0 8px 24px rgba(28,26,23,.06)",
      },
    },
  },
  plugins: [],
} satisfies Config;
