import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { IconButton } from "../ui/IconButton";
import { Badge } from "../ui/Badge";
import { ELEMENT_LABEL, SIGNS } from "../../lib/astro";

// "Explore the signs" (pages/landing.md §5). CSS scroll-snap instead of Swiper: zero JS cost on the
// landing bundle, native keyboard/touch scrolling, never auto-plays. Art is 480w AVIF (~45 KB) with
// a JPEG fallback, lazy-loaded with explicit dimensions (MASTER §7.3).

const ALT: Record<string, string> = {
  Aries: "Aries — a ram with spiralling horns",
  Taurus: "Taurus — a calm bull among flowers",
  Gemini: "Gemini — twin figures facing each other",
  Cancer: "Cancer — a crab beneath the moon",
  Leo: "Leo — a lion crowned in sunlight",
  Virgo: "Virgo — a maiden holding wheat",
  Libra: "Libra — balanced scales",
  Scorpio: "Scorpio — a scorpion in deep colours",
  Sagittarius: "Sagittarius — an archer drawing a bow",
  Capricorn: "Capricorn — a sea-goat on a mountain",
  Aquarius: "Aquarius — a water bearer pouring a stream",
  Pisces: "Pisces — two fish circling",
};

export function ZodiacCards() {
  const scroller = useRef<HTMLUListElement>(null);
  const scrollBy = (dir: 1 | -1) => {
    const el = scroller.current;
    if (!el) return;
    el.scrollBy({ left: dir * Math.min(el.clientWidth * 0.8, 760), behavior: "smooth" });
  };

  return (
    <section aria-labelledby="signs-h" className="py-16 md:py-24">
      <div className="mx-auto max-w-app px-4 md:px-6 lg:px-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 id="signs-h" className="text-h2 text-fg">
              Explore the signs
            </h2>
            <p className="mt-2 text-body text-fg-secondary">Twelve rashis, each with its own element and temperament.</p>
          </div>
          <div className="hidden gap-2 md:flex">
            <IconButton aria-label="Previous signs" variant="secondary" round onClick={() => scrollBy(-1)}>
              <ChevronLeft aria-hidden="true" />
            </IconButton>
            <IconButton aria-label="Next signs" variant="secondary" round onClick={() => scrollBy(1)}>
              <ChevronRight aria-hidden="true" />
            </IconButton>
          </div>
        </div>
      </div>
      <ul
        ref={scroller}
        aria-label="Zodiac signs"
        tabIndex={0}
        className="focus-ring mt-6 flex snap-x snap-mandatory scroll-px-4 gap-4 overflow-x-auto scroll-smooth px-4 pb-4 [scrollbar-width:none] md:scroll-px-6 md:px-6 lg:scroll-px-[max(2rem,calc((100vw-75rem)/2+2rem))] lg:px-[max(2rem,calc((100vw-75rem)/2+2rem))]"
      >
        {SIGNS.map((s) => {
          const slug = s.english.toLowerCase();
          return (
            <li key={s.english} className="w-[240px] shrink-0 snap-start">
              <article className="overflow-hidden rounded-card border border-border bg-surface">
                <picture>
                  <source srcSet={`/images/zodiac/opt/${slug}-480.avif`} type="image/avif" />
                  <img
                    src={`/images/zodiac/opt/${slug}-480.jpg`}
                    alt={ALT[s.english]}
                    width={480}
                    height={643}
                    loading="lazy"
                    decoding="async"
                    className="aspect-[3/4] h-auto w-full bg-elevated object-cover"
                  />
                </picture>
                <div className="p-4">
                  <h3 className="font-sans text-title text-fg">{s.english}</h3>
                  <p className="text-caption text-fg-muted">
                    {s.rashi} · <span lang="hi">{s.devanagari}</span>
                  </p>
                  <Badge className="mt-2">{ELEMENT_LABEL[s.element]}</Badge>
                </div>
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
