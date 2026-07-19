/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Montserrat', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: '#5E44EB',
          container: '#ECE8FD',
        },
        secondary: {
          DEFAULT: '#DCF252',
          container: '#F8FCE3',
        },
        background: '#FAFAFB',
        surface: {
          DEFAULT: '#FFFFFF',
          variant: '#F1F2F6',
        },
        on: {
          surface: '#1C1B1F',
          'surface-variant': '#5F6368',
        },
        outline: '#E1E2E8',
        error: { container: '#FBE9E9' },
        success: { container: '#E6F4E2' },
        neutral: { container: '#F1F1F1' },
        // shadcn/ui-вдохновлённые нейтральные токены
        muted: {
          DEFAULT: '#F4F4F5',
          foreground: '#71717A',
        },
      },
      borderRadius: {
        btn: '12px',
        card: '16px',
        modal: '24px',
      },
      boxShadow: {
        card: '0 2px 8px rgba(28, 27, 31, 0.06)',
        'card-hover': '0 4px 16px rgba(28, 27, 31, 0.10)',
      },
    },
  },
  plugins: [],
};
