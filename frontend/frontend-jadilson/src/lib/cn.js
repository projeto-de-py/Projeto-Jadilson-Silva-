import { clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["11", "12", "13", "14", "15", "16", "18", "20", "22", "24", "28", "32", "40"] },
      ],
      rounded: [{ rounded: ["input", "card", "modal", "badge"] }],
    },
  },
});

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
