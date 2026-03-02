/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        court: {
          950: '#04070d',
          900: '#070f1a',
          800: '#0d1f35',
          700: '#102840',
        },
        brand: {
          DEFAULT: '#f97316',
          dim: '#c2540a',
          glow: '#fb923c',
        },
        green: {
          alert: '#22c55e',
        },
        red: {
          alert: '#ef4444',
        },
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'sans-serif'],
        body: ['"DM Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backgroundImage: {
        'court-lines': "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(249,115,22,0.08) 0%, transparent 60%)",
      },
    },
  },
  plugins: [],
}
