/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/**/*.css"
  ],
  theme: {
    extend: {
      fontFamily: {
        anton: ['Anton SC', 'sans-serif'],
        devil: ['Rubik Wet Paint', 'sans-serif'],
        abel: ['Abel', 'sans-serif']
      }
    },
  },
  plugins: [],
}

