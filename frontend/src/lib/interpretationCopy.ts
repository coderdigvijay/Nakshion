// Short interpretation copy shown beside server-computed chart facts. Graha drishti, yogas, Ketu
// and the dasha timeline all come from the engine (api-contract G-09 closed); nothing here
// derives astrology. Move this into a KB-backed field when the API offers one.
import type { VedicData } from "../types";

export const DASHA_THEMES: Record<string, string> = {
  Sun: "authority, father, health, identity, leadership",
  Moon: "emotions, mother, travel, the mind, public life",
  Mars: "energy, property, siblings, courage, decisive action",
  Mercury: "communication, business, learning, trade, writing",
  Jupiter: "wisdom, children, teaching, dharma, expansion",
  Venus: "love, marriage, comfort, art, partnerships",
  Saturn: "discipline, career, karma, patience, structure",
  Rahu: "ambition, foreign links, the unconventional, technology",
  Ketu: "spirituality, detachment, inner work, research",
};

const LAGNA_INSIGHTS: Record<string, string> = {
  Mesha: "You lead with action and initiative; patience is your growth edge.",
  Vrishabha: "You build with persistence and sensory wisdom; flexibility is your evolution.",
  Mithuna: "You meet the world through intellect and conversation; depth is your journey.",
  Karka: "You navigate life through emotional intelligence; healthy detachment is your freedom.",
  Simha: "You express through creative authority; humility is your hidden strength.",
  Kanya: "You refine everything you touch; accepting imperfection is your freedom.",
  Tula: "You seek harmony in all things; decisive action is your growth.",
  Vrishchika: "You transform through intensity; trust is your deepest lesson.",
  Dhanu: "You grow through meaning and truth; grounding is your anchor.",
  Makara: "You achieve through discipline and structure; emotional openness is your breakthrough.",
  Kumbha: "You innovate through vision and independence; intimacy is your growth.",
  Meena: "You dissolve boundaries through compassion; firm boundaries protect you.",
};

export function coreSignature(vedic: VedicData): string[] {
  const out: string[] = [];
  const raw = vedic.lagna?.rashi;
  const rashi = raw === "Vrischika" ? "Vrishchika" : raw;
  if (rashi && LAGNA_INSIGHTS[rashi]) out.push(LAGNA_INSIGHTS[rashi]);
  const nature = vedic.moon_nakshatra?.nature;
  if (nature === "Dharma") out.push("Your emotional core is guided by purpose and doing what is right.");
  if (nature === "Artha") out.push("You tend to feel secure when your work and resources are on firm ground.");
  if (nature === "Kama") out.push("You find fulfilment through connection, beauty and shared pleasure.");
  if (nature === "Moksha") out.push("Your emotional depth looks for spiritual meaning.");
  const md = vedic.dasha?.maha_dasha?.current;
  if (md && DASHA_THEMES[md]) out.push(`Your current ${md} period puts weight on ${DASHA_THEMES[md]}.`);
  if (vedic.sade_sati?.active) out.push("Saturn is moving over your Moon (Sade Sati), a period that asks for patience and builds lasting strength.");
  return out.slice(0, 3);
}
