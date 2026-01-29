/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'sentinel-bg': '#0a0e1a',
        'sentinel-card': '#1a1f2e',
        'sentinel-border': '#374151',
        'sentinel-purple': '#8b5cf6',
        'sentinel-cyan': '#06b6d4',
      },
    },
  },
  plugins: [],
}
