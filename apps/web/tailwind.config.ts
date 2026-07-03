import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#04150F",
        panel: "#0C2E21",
        surface: "#123A2A",
        line: "#2A6A4C",
        mist: "#DDEEE3",
        electric: "#13924B",
        lime: "#7CD9A1",
        coral: "#D95F5F"
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(19,146,75,0.16), 0 24px 80px rgba(4,21,15,0.35)"
      },
      fontFamily: {
        display: ['"Buenos Aires"', "system-ui", "sans-serif"],
        body: ['"Buenos Aires"', "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

export default config;
