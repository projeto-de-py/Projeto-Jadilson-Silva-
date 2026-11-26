import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath } from "node:url";

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true, // recusa outra porta (evita Vite "fantasma" em 5173)
    proxy: {
      // Cookie de sessao exige mesma origem: o browser so ve localhost:5173
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  plugins: [react(), tailwindcss()],
  build: {
    // O unico chunk acima de 500 kB e o `html2pdf` (bundle terceirizado que
    // inclui o gerador de PDF). Ele ja e carregado sob demanda em
    // `src/lib/documentos.js`, entao nao entra no download inicial.
    chunkSizeWarningLimit: 800,
    // Separa bibliotecas grandes em chunks cacheaveis. Sem isso o bundle
    // principal passava de 1,7 MB.
    rolldownOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("html2pdf")) return "html2pdf";
          if (id.includes("jspdf")) return "jspdf";
          if (id.includes("html2canvas")) return "html2canvas";
          if (id.includes("mammoth")) return "docx";
          if (id.includes("@tiptap") || id.includes("prosemirror")) return "editor";
          if (id.includes("recharts") || id.includes("d3-")) return "charts";
          if (id.includes("motion") || id.includes("framer")) return "motion";
          if (id.includes("symbols-react")) return "symbols";
          if (id.includes("@radix-ui")) return "radix";
          if (id.includes("react")) return "react-vendor";
          return undefined;
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
