import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        pi: {
          bg: '#0a0a0f',
          surface: '#13131a',
          'surface-hover': '#1a1a24',
          'surface-light': '#22222e',
          border: 'rgba(255, 255, 255, 0.06)',
          'border-hover': 'rgba(255, 255, 255, 0.12)',
          accent: '#6366f1',
          'accent-dim': 'rgba(99, 102, 241, 0.15)',
          'accent-bright': '#818cf8',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Noto Sans SC"', '"PingFang SC"', 'sans-serif'],
        mono: ['"SF Mono"', 'Menlo', 'Consolas', '"Liberation Mono"', 'monospace'],
      },
    },
  },
  plugins: [],
} satisfies Config
