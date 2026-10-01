# Premium UI Stack — Cosmic Intelligence (Astrology)

## Master Agent Knowledge Document
**Created:** 2026-03-29
**Domain:** Frontend / UI Libraries
**Applies to:** All frontend tasks requiring elite-level visual polish

---

## Philosophy

Premium UIs separate average products from $10M+ feeling products. This stack is battle-tested by:
- Award-winning agency sites
- YC startups (Linear, Vercel, Cal.com)
- Apple-style marketing pages
- Enterprise SaaS dashboards

---

## Tier 1: Foundation (MANDATORY)

### shadcn/ui + Radix UI + Tailwind CSS
**Why:** You own the code, no vendor lock-in, accessible by default

```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card input label dialog tabs badge avatar
```

**Components:**
- Button, Card, Dialog, Tabs, Badge, Avatar, Dropdown Menu
- All built on Radix UI (WCAG AA accessible)
- Customizable with Tailwind

**Project use:**
- All form inputs, modals, cards
- Base component library
- Design system foundation

---

## Tier 2: Animation (ALWAYS USE)

### Framer Motion (Primary)
**Use for:** 90% of animations

```typescript
import { motion, AnimatePresence } from 'framer-motion';

// AI message entrance
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ type: "spring", stiffness: 400, damping: 25 }}
>
  {message}
</motion.div>

// Draggable natal chart
<motion.div
  drag
  dragConstraints={{ left: -200, right: 200 }}
  whileHover={{ scale: 1.02 }}
/>
```

**Cosmic Intelligence use cases:**
- AI messages stagger entrance
- Modal/dialog animations
- Draggable natal chart
- Zodiac sign hover effects
- Layout transitions

---

### GSAP (Advanced — Cinematic Effects)
**Use for:** Landing page hero, storytelling

```typescript
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// Hero timeline
const tl = gsap.timeline();
tl.from('.hero-title', { opacity: 0, y: 100, duration: 1 })
  .from('.hero-cta', { opacity: 0, scale: 0.8, duration: 0.5 });

// Scroll-triggered reveal
gsap.from('.feature-card', {
  scrollTrigger: {
    trigger: '.feature-card',
    start: 'top 80%'
  },
  opacity: 0,
  y: 50,
  stagger: 0.2
});
```

**Cosmic Intelligence use cases:**
- Landing page hero entrance
- Constellation drawing animation
- Section reveals on scroll
- Storytelling sequences

---

### Animation Decision Matrix

| Need | Library | Reason |
|------|---------|--------|
| Button hover | Tailwind | Lightest |
| Component entrance | Framer Motion | Best DX |
| Draggable element | Framer Motion | Built-in |
| Modal/dialog | Framer Motion | AnimatePresence |
| Hero section | GSAP | Timeline control |
| Scroll reveal | GSAP ScrollTrigger | Performance |
| 3D animation | Three.js | Only option |

---

## Tier 3: Scroll Experience (PREMIUM FEEL)

### Lenis (Smooth Scroll)
**Critical:** This makes sites feel $1M+

```typescript
import Lenis from '@studio-freight/lenis';

const lenis = new Lenis({
  duration: 1.2,
  easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  orientation: 'vertical',
  smoothWheel: true
});

function raf(time: number) {
  lenis.raf(time);
  requestAnimationFrame(raf);
}
requestAnimationFrame(raf);
```

**Result:** Buttery 60fps scroll feel

**Cosmic Intelligence use:**
- Landing page scroll
- Dashboard scroll (optional — test performance)

---

## Tier 4: 3D (OPTIONAL — Premium Pages Only)

### Three.js + React Three Fiber
**Use sparingly** — heavy bundle, mobile performance

```typescript
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';

<Canvas>
  <Stars radius={100} depth={50} count={5000} factor={4} />
  <OrbitControls />
</Canvas>
```

**Cosmic Intelligence use cases:**
- Landing page 3D zodiac wheel hero
- Premium tier 3D natal chart
- Floating cosmic particles background

**Don't use:**
- Dashboard (too heavy)
- Mobile (performance kill)
- Form pages (unnecessary)

---

## Tier 5: Premium UI Blocks (Copy-Paste)

### Magic UI
**URL:** https://magicui.design

**Best for:**
- Glowing cards
- Animated buttons
- Premium pricing sections
- Testimonial carousels

**Cosmic Intelligence use:**
- Pricing page cards
- Feature showcases with glow
- Premium tier upsell

---

### Aceternity UI
**URL:** https://ui.aceternity.com

**Best for:**
- Hero sections
- Spotlight cards
- Animated backgrounds
- Parallax sections

**Cosmic Intelligence use:**
- Landing page hero
- Feature grid with spotlight
- About section

---

### hover.dev
**URL:** https://hover.dev

**Best for:**
- Micro-interactions
- Button hover effects
- Card animations

---

## Tier 6: Particles & Effects

### tsParticles
**Use:** Cosmic star fields, moving particles

```typescript
import Particles from "react-tsparticles";

<Particles
  options={{
    particles: {
      number: { value: 50 },
      color: { value: "#ffffff" },
      size: { value: 3 }
    }
  }}
/>
```

**Cosmic Intelligence use:**
- Landing page star background
- Dashboard ambient stars (subtle)

---

### Lottie
**Use:** JSON animations (loading, success, illustrations)

```typescript
import Lottie from 'lottie-react';
import animationData from './cosmic-loader.json';

<Lottie animationData={animationData} loop={true} />
```

**Cosmic Intelligence use:**
- Loading states
- Success confirmations
- Empty state illustrations

---

## Tier 7: Charts

### Recharts (PRIMARY)
```typescript
import { RadialBarChart, RadialBar, PolarAngleAxis } from 'recharts';

<RadialBarChart data={natalChartData}>
  <RadialBar dataKey="value" />
</RadialBarChart>
```

**Cosmic Intelligence use:**
- Natal chart wheel
- Compatibility scores
- Transit timelines

---

## Tier 8: Typography

### Premium Fonts (Google Fonts)
- **Inter** — body text (modern, readable)
- **Geist** — headings (premium feel)
- **Satoshi** — alternative luxury font
- **General Sans** — rounded, friendly

```javascript
// tailwind.config.js
{
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui'],
        display: ['Geist', 'Inter']
      }
    }
  }
}
```

---

## Installation Commands

```bash
# Foundation
npx shadcn-ui@latest init

# Animation (MANDATORY)
npm install framer-motion gsap @studio-freight/lenis

# Icons
npm install lucide-react@0.575.0

# Forms
npm install react-hook-form @hookform/resolvers zod

# Charts
npm install recharts

# State
npm install zustand @tanstack/react-query

# 3D (OPTIONAL)
npm install three @react-three/fiber @react-three/drei

# Particles (OPTIONAL)
npm install tsparticles

# Lottie (OPTIONAL)
npm install lottie-react
```

---

## Agent Usage Rules

### UI/UX Elite Designer
- **Always** check Magic UI / Aceternity UI for inspiration
- Use Stitch MCP to generate designs
- Reference this stack when specifying animations
- Specify: "Use Framer Motion for X" or "Use GSAP for Y"

### Frontend Elite Engineer
- **Mandatory:** Framer Motion + GSAP
- **Landing page:** Add Lenis smooth scroll
- **Optional:** Three.js only if approved by Master Agent
- Copy premium UI blocks, adapt to Tailwind

### Master Agent
- Approve 3D usage (bundle size concern)
- Ensure agents use correct animation library
- Review for performance (GSAP > Framer Motion for complex timelines)

---

## Performance Rules

**Bundle size priority:**
1. Tailwind (transitions only) — 0KB extra
2. Framer Motion — 35KB
3. GSAP — 50KB
4. Three.js — 500KB+ (use sparingly)

**Mobile rules:**
- Reduce motion on mobile (check `prefers-reduced-motion`)
- Avoid Three.js on mobile
- Simplify GSAP timelines on mobile

---

## Examples for Cosmic Intelligence

### Landing Page Hero
```typescript
// GSAP timeline
const tl = gsap.timeline();
tl.from('.cosmic-title', { opacity: 0, y: 100, duration: 1.2 })
  .from('.zodiac-wheel', { scale: 0, rotation: -180, duration: 1.5 }, '-=0.5')
  .from('.cta-button', { opacity: 0, scale: 0.8 });
```

### AI Chat Messages
```typescript
// Framer Motion stagger
<motion.div variants={containerVariants} initial="hidden" animate="visible">
  {messages.map(msg => (
    <motion.div key={msg.id} variants={messageVariants}>
      {msg.content}
    </motion.div>
  ))}
</motion.div>
```

### Draggable Natal Chart
```typescript
<motion.div
  drag
  dragConstraints={{ left: -100, right: 100 }}
  whileHover={{ scale: 1.05 }}
  whileTap={{ scale: 0.95 }}
>
  <NatalChartSVG />
</motion.div>
```

### Smooth Scroll
```typescript
// App.tsx
useEffect(() => {
  const lenis = new Lenis();
  function raf(time: number) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
}, []);
```

---

## Success Metrics

Premium UI stack achieves:
- ✅ 60fps animations
- ✅ Buttery smooth scroll
- ✅ Apple-level polish
- ✅ Accessible (WCAG AA)
- ✅ Fast load times (<3s)

---

## Knowledge Captured By
Master Agent, 2026-03-29
Sentinel: Knowledge Curator (auto-saved)
