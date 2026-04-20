/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0a0e1a',
          secondary: '#0f1629',
          card: '#111827',
        },
        accent: {
          primary: '#00d4ff',
          green: '#10b981',
        },
        text: {
          primary: '#ffffff',
          secondary: '#9ca3af',
          muted: '#6b7280',
        },
        border: {
          light: 'rgba(255, 255, 255, 0.06)',
          accent: 'rgba(0, 212, 255, 0.2)',
        }
      },
    },
  },
  plugins: [],
}
