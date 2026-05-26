/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          500: '#6366f1',   // indigo-500
          600: '#4f46e5',   // indigo-600
          700: '#4338ca',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in':   'fadeIn 0.15s ease-out',
        'slide-up':  'slideUp 0.2s ease-out',
      },
      keyframes: {
        fadeIn:  { from: { opacity: 0 },                    to: { opacity: 1 } },
        slideUp: { from: { opacity: 0, transform: 'translateY(8px)' },
                   to:   { opacity: 1, transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
};
