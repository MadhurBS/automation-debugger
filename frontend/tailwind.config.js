/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // ── IBM Carbon Design System colour tokens ────────────────────────
      colors: {
        // Interactive / brand blue
        ibm: {
          blue10:  '#edf5ff',
          blue20:  '#d0e2ff',
          blue40:  '#78a9ff',
          blue50:  '#4589ff',
          blue60:  '#0f62fe',   // $interactive-01  (primary CTA)
          blue70:  '#0043ce',   // hover
          blue80:  '#002d9c',
          blue100: '#001141',
        },
        // Neutral greys (Carbon "Gray" scale)
        carbon: {
          10:  '#f4f4f4',   // page background
          20:  '#e0e0e0',   // subtle border
          30:  '#c6c6c6',   // border
          40:  '#a8a8a8',   // placeholder
          50:  '#8d8d8d',   // helper text
          60:  '#6f6f6f',   // secondary label
          70:  '#525252',   // body
          80:  '#393939',
          90:  '#262626',   // heading
          100: '#161616',   // emphasis
        },
        // Shell / sidebar — Carbon White theme
        shell: {
          bg:       '#ffffff',   // White theme: nav panel is white
          header:   '#ffffff',   // Global header bar white
          navItem:  '#f4f4f4',
          hover:    '#e8e8e8',
          active:   '#0f62fe',   // selected item blue fill
          text:     '#525252',   // Carbon Gray 70
          textHigh: '#161616',   // Carbon Gray 100
          border:   '#e0e0e0',   // Carbon Gray 20
        },
        // Keep platform colours (tweaked to Carbon palette)
        platform: {
          uipath:   '#ff6900',
          powerautomate: '#0043ce',
          blueprism: '#8a3ffc',
          aa:        '#ff7eb6',
        },
        // Semantic
        severity: {
          critical: '#da1e28',
          high:     '#ff832b',
          medium:   '#f1c21b',
          low:      '#24a148',
        },
        // Primary alias → IBM blue
        primary: {
          50:  '#edf5ff',
          100: '#d0e2ff',
          200: '#a6c8ff',
          400: '#78a9ff',
          500: '#4589ff',
          600: '#0f62fe',
          700: '#0043ce',
          900: '#001141',
        },
      },
      // ── IBM Plex Sans ─────────────────────────────────────────────────
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'Helvetica Neue', 'Arial', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"Courier New"', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],   // 11px / Carbon label-01
      },
      boxShadow: {
        card:       '0 1px 2px 0 rgba(0,0,0,.12)',
        'card-md':  '0 2px 6px 0 rgba(0,0,0,.16)',
        'card-hover':'0 4px 12px 0 rgba(0,0,0,.20)',
      },
      borderRadius: {
        DEFAULT: '0px',    // Carbon uses square corners by default
        sm: '2px',
        md: '4px',
        lg: '4px',
        xl: '4px',
        '2xl': '4px',
        full: '9999px',
      },
    },
  },
  plugins: [],
}
