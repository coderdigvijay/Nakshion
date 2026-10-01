import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// tailwind-merge must know the Nakshion type scale and shadow tokens (tokens.css), otherwise it
// reads `text-body-sm` as a colour and silently drops `text-ai` / `text-fg` in the same class list.
const twMerge = extendTailwindMerge({
  extend: {
    theme: {
      text: ["display", "h1", "h2", "h3", "title", "body-lg", "body", "body-sm", "caption", "overline", "stat"],
      shadow: ["e1", "e2", "e3", "highlight", "glow-accent", "glow-ai"],
      radius: ["control", "card", "sheet", "bubble", "chip"],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
