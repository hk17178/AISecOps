/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#f4efe4',
        paper: '#fbf8f0',
        paper2: '#f7f2e7',
        side: '#efe9da',
        ink: '#33312b',
        dim: '#8c887b',
        line: '#e0d9c8',
        terra: '#b0512f',
        sage: '#6d7d57',
        ochre: '#bb8a3c',
        clay: '#9a8266',
      },
      fontFamily: {
        serif: ['Georgia', '"Songti SC"', '"Noto Serif SC"', 'serif'],
        sans: ['-apple-system', '"PingFang SC"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
