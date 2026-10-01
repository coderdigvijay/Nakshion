// Compatibility score bands (MASTER §9.4a). Colour is always paired with an icon and a word.
import { AlertCircle, CheckCircle2, Scale, Sparkles } from "lucide-react";

export interface Band {
  label: string;
  text: string;
  stroke: string;
  bg: string;
  icon: React.ReactNode;
  glow?: boolean;
}

export function bandFor(score: number, max: 10 | 36 = 10): Band {
  const s10 = max === 36 ? (score / 36) * 10 : score;
  if (s10 >= 8.5) return { label: "Exceptional", text: "text-accent-text", stroke: "stroke-accent", bg: "bg-accent", icon: <Sparkles aria-hidden="true" />, glow: true };
  if (s10 >= 6.5) return { label: "Harmonious", text: "text-success", stroke: "stroke-success", bg: "bg-success", icon: <CheckCircle2 aria-hidden="true" /> };
  // Mid scores are neutral violet, not orange: "mixed" is not a warning.
  if (s10 >= 4) return { label: "Workable", text: "text-ai", stroke: "stroke-ai", bg: "bg-ai-fill", icon: <Scale aria-hidden="true" /> };
  return { label: "Challenging", text: "text-danger", stroke: "stroke-danger", bg: "bg-danger", icon: <AlertCircle aria-hidden="true" /> };
}
