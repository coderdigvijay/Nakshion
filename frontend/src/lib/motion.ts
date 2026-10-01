// Motion tokens mirrored from tokens.css (MASTER §8.1).
import type { Transition, Variants } from "framer-motion";

export const dur = { instant: 0.1, fast: 0.15, base: 0.25, slow: 0.4, slower: 0.6, ambient: 2.4 } as const;

export const ease = {
  standard: [0.2, 0, 0, 1],
  enter: [0.16, 1, 0.3, 1],
  exit: [0.4, 0, 1, 1],
  emphasized: [0.3, 0, 0, 1.2],
} as const satisfies Record<string, [number, number, number, number]>;

export const spring = {
  snappy: { type: "spring", stiffness: 400, damping: 30 },
  smooth: { type: "spring", stiffness: 300, damping: 32 },
  gentle: { type: "spring", stiffness: 180, damping: 24 },
} as const satisfies Record<string, Transition>;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: dur.base, ease: ease.enter } },
};

/** Stagger container: 40 ms, used for at most 6 children (MASTER §8.1). */
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};
