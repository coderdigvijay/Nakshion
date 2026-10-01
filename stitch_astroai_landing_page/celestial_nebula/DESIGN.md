# Design System Strategy: The Celestial Editorial

## 1. Overview & Creative North Star
The Creative North Star for this design system is **"The Cosmic Oracle."** 

This system transcends the utility of a standard AI app to become an immersive, high-end editorial experience. We reject the "flat" web by embracing the infinite depth of the cosmos. The interface is not a set of containers on a page, but a series of celestial bodies and ethereal data layers floating within a deep-space vacuum. By utilizing intentional asymmetry—placing heavy-weighted typography against delicate, glowing astrological charts—we create a rhythmic visual tension that feels both ancient and futuristic. 

The goal is to evoke wonder through **Atmospheric Depth**. We use overlapping glass layers, vibrant neon "auras," and sophisticated typography to guide the user through their destiny with the authority of a premium editorial publication.

---

## 2. Colors
Our palette is rooted in the void of space, punctuated by the high-energy light of distant stars and nebulas.

*   **The Foundation:** `background` (#0a0e1a) is the absolute void. All depth is built upwards from here.
*   **The Accents:** `primary` (#ca98ff) and `secondary` (#ffd709) represent neon cosmic energy and solar prestige. 
*   **The "No-Line" Rule:** Standard 1px borders are strictly prohibited for sectioning. To separate content, use background shifts. For instance, a section using `surface-container-low` should transition into the base `background` without a visible stroke. Let the change in value define the edge.
*   **Surface Hierarchy & Nesting:** Use the `surface-container` tiers to create a physical sense of "stacking." 
    *   *Base Level:* `surface`
    *   *Intermediate Depth:* `surface-container`
    *   *Top Layer (Floating Cards):* `surface-container-highest` with 40-60% opacity.
*   **The "Glass & Gradient" Rule:** All interactive containers must utilize Glassmorphism. Apply `backdrop-blur` (at least 12px) and a subtle gradient from `primary-container` to a transparent variant of `surface-variant`. This ensures the UI feels like a physical lens into the stars.
*   **Signature Textures:** For high-impact areas like CTAs, use a linear gradient: `primary` (#ca98ff) to `primary-dim` (#9c42f4). This provides the "neon glow" characteristic of high-end celestial imagery.

---

## 3. Typography
We use a high-contrast pairing to balance technical AI precision with human-centric storytelling.

*   **Display & Headlines (Plus Jakarta Sans):** Our authoritative voice. Use `display-lg` for hero statements. To achieve the signature editorial look, use "Sentence case" and experiment with tight letter spacing (-0.02em) to make the large type feel like a singular graphic element.
*   **Body & Labels (Manrope):** Our functional voice. Manrope provides a clean, geometric counter-balance to the expressive headlines. `body-lg` should be used for insights, ensuring line-height is generous (1.5x - 1.6x) to allow the "celestial air" to flow between lines of text.
*   **Tonal Contrast:** Mix `secondary` (Gold) for keywords within a `primary` or `on-surface` sentence to create a "highlight" effect that mimics ancient manuscripts.

---

## 4. Elevation & Depth
Depth is not a decoration; it is the core of the navigation.

*   **The Layering Principle:** Instead of shadows, use **Tonal Layering**. Place a `surface-container-lowest` card (#000000) inside a `surface-container-high` (#1a1f2f) wrapper. This "recessed" look creates a sophisticated, carved-out aesthetic.
*   **Ambient Shadows:** When an element must "float" (like an insight card), use a diffuse shadow. 
    *   *Shadow Color:* `primary` at 10% opacity. 
    *   *Blur:* 40px to 60px. 
    *   *Offset:* 0px (centered glow). 
    *   This mimics the light pollution of a nebula rather than a synthetic drop shadow.
*   **The "Ghost Border" Fallback:** If a boundary is required for legibility, use `outline-variant` (#444756) at 20% opacity. It should be felt, not seen.
*   **Glassmorphism:** All floating cards must use a semi-transparent `surface-container-highest` with a 1px "inner glow" border (white at 10% opacity) on the top and left edges to simulate light hitting the edge of a glass pane.

---

## 5. Components

### Buttons
*   **Primary:** A vibrant gradient from `primary` to `primary-dim`. Roundedness: `full`. No border. Add a soft outer glow of the same color.
*   **Secondary/Ghost:** A "Ghost Border" using `outline`. Text should be `on-surface`. On hover, the background fills with a 10% opacity `primary` tint.

### Insight Cards (Glassmorphism)
*   **Style:** `surface-container-highest` at 50% opacity.
*   **Effect:** `backdrop-filter: blur(16px)`.
*   **Border:** `outline-variant` at 15% opacity.
*   **Corner Radius:** `lg` (1rem).

### Zodiac Chips
*   **Selection:** Circular (`full` roundedness). Use `surface-container-high` as the base. 
*   **Active State:** `primary` neon border and a subtle inner glow. The icon should shift to `on-primary-fixed`.

### Input Fields
*   **Style:** Minimalist. No bottom line or box. Use `surface-container-low` as a subtle pill shape. 
*   **Active State:** Transition the background to `surface-container-high` and add a `primary` outer glow (4px blur).

### Astrology Charts (Specialty Component)
*   **Style:** Use `tertiary` (#7ed3ff) and `secondary` (#ffd709) for hairline-thin (0.5px - 1px) stroke weights. These should be treated as "background art" that conveys data, overlapping with text to create depth.

---

## 6. Do's and Don'ts

### Do:
*   **DO** use extreme vertical whitespace (`spacing-20` and `spacing-24`) to separate major narrative beats.
*   **DO** overlap elements. Let a glass card partially cover a celestial chart to create a 3D z-axis.
*   **DO** use `secondary` (Gold) sparingly for "Divine Moments"—achievements, rare insights, or premium CTAs.

### Don't:
*   **DON'T** use 100% opaque solid black or grey for cards. It kills the "Cosmic" depth.
*   **DON'T** use standard grid-based dividers. Use a `surface` color shift or simply 64px of empty space.
*   **DON'T** use high-contrast white text on dark backgrounds for long-form reading. Use `on-surface-variant` (#a7aabb) for a softer, more premium "dimmed" feel that reduces eye strain in dark environments.