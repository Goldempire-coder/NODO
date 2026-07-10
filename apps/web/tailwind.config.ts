import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        nodo: {
          background: "#020B16",
          card: "#071A2D",
          border: "#1D344B",
          green: "#00C853",
          blue: "#1C9CEB",
          text: "#FFFFFF",
          muted: "#B8C4D6"
        }
      }
    }
  },
  plugins: []
};

export default config;
