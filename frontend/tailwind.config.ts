import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        panel: '#111827',
        card: '#1f2937',
        accent: '#8b5cf6'
      }
    }
  },
  plugins: []
};

export default config;
