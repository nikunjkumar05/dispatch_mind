/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        base: '#0B0F19',
        surface: '#111827',
        elevated: '#1F2937',
        sidebar: '#0D1321',
        accent: {
          DEFAULT: '#3B82F6',
          glow: '#60A5FA',
          dim: '#2563EB',
        },
        chalk: '#F9FAFB',
        muted: '#6B7280',
        signal: {
          red: '#EF4444',
          amber: '#F59E0B',
          emerald: '#22C55E',
        },
        tier: {
          critical: '#EF4444',
          high: '#F97316',
          medium: '#EAB308',
          low: '#22C55E',
        }
      },
      fontFamily: {
        heading: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        'glow-red': '0 0 20px rgba(239, 68, 68, 0.15)',
        'glow-orange': '0 0 20px rgba(249, 115, 22, 0.15)',
        'glow-amber': '0 0 20px rgba(234, 179, 8, 0.15)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.15)',
        'glow-blue': '0 0 20px rgba(59, 130, 246, 0.2)',
      },
    },
  },
  plugins: [],
}
