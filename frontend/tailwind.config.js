/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        teal: {
          950: "#06181A",
          900: "#0A2528",
          850: "#0D3135",
          800: "#123F44",
          700: "#1A575E",
          600: "#22727C",
          500: "#14B8A6",
          400: "#2DD4BF",
          300: "#5EEAD4",
        },
        ivory: {
          50: "#FCFAF6",
          100: "#F7F3E9",
          200: "#EFE8D6",
          300: "#E3D7BC",
          400: "#C9BA96",
          500: "#A99870",
        },
        gold: {
          400: "#FCD34D",
          500: "#F59E0B",
          600: "#D97706",
          light: "#E5B869",
        },
      },
      fontFamily: {
        serif: ["Newsreader", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
