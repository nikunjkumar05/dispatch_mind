/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        asphalt: '#1C1917',
        stone: '#44403C',
        concrete: '#F5F5F4',
        chalk: '#FFFFFF',
        mist: '#E7E5E4',
        khaki: '#B8960C',
        signal: {
          red: '#B91C1C',
          amber: '#D97706',
          emerald: '#059669',
        },
        tier: {
          critical: '#DC2626',
          high: '#EA580C',
          medium: '#D97706',
          low: '#059669',
        }
      },
      fontFamily: {
        heading: ['Barlow Condensed', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
