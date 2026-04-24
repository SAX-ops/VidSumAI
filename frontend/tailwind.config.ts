import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.{js,vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          from: '#ff6b6b',
          to: '#feca57',
        },
        dark: {
          bg: '#0a0a0f',
          card: 'rgba(255,255,255,0.05)',
          border: 'rgba(255,255,255,0.1)',
        }
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)',
      }
    },
  },
  plugins: [],
} satisfies Config
