/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
        sidebar: {
          bg: '#1e2433',
          hover: '#2a3347',
          active: '#3b4a63',
          text: '#94a3b8',
          textActive: '#f1f5f9',
        },
        surface: {
          1: '#f8fafc',
          2: '#f1f5f9',
        },
        platform: {
          uipath: '#ff6900',
          powerautomate: '#0066ff',
          blueprism: '#6d28d9',
          aa: '#e91e8c',
        },
        severity: {
          critical: '#dc2626',
          high: '#ea580c',
          medium: '#ca8a04',
          low: '#16a34a',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0,0,0,.07), 0 1px 2px -1px rgba(0,0,0,.07)',
        'card-hover': '0 4px 12px 0 rgba(0,0,0,.1)',
      },
    },
  },
  plugins: [],
}
