import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

// Usa tailwind-merge + clsx
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
