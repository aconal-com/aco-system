import type { Config } from 'tailwindcss';

export default {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        orange: { DEFAULT: '#f97316', light: '#fed7aa', dark: '#ea580c' },
      },
    },
  },
  plugins: [],
} satisfies Config;
