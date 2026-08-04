/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,js}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#1e1e1e",
          dark: "#121212",
          light: "#2d2d2d",
        },
        accent: {
          purple: "#bb86fc",
          teal: "#03dac6",
          pink: "#ff7597",
        },
        text: {
          primary: "#e0e0e0",
          secondary: "#a0a0a0",
        },
      },
      fontFamily: {
        sans: ["Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
