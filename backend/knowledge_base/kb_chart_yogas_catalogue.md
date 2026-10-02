---
title: "Yoga and Dosha Catalogue (engine-aligned)"
tradition: "Jyotish (Parashari, with Jataka Parijata and Brihat Jataka cross-checks)"
system: vedic
tier: 2
language: en
sources:
  - "Jataka Parijata (Vaidyanatha), tr. V. Subrahmanya Sastri, 1932 - archive.org/details/JatakaParijata1932 (Kemadruma, Sakata, Gajakesari, Amala, moolatrikona passages read)"
  - "Brihat Jataka (Varahamihira), tr. B. Suryanarain Rao, 1919 - archive.org/details/in.ernet.dli.2015.312667"
  - "Brihat Parashara Hora Shastra chapters on yogas (ch. 34-43, 79) via secondary summaries - jagannathhora.com, panchangbodh.com, astromangal.in"
  - "Engine definitions: backend/app/astrology/yogas.py"
confidence: medium
school_notes: "Classical formation rules are consistent across texts; strength, cancellation and result descriptions differ by commentator. Where the app engine uses a simplified rule, the section says so under 'Engine rule'."
---

# Yoga and Dosha Catalogue

A yoga is a combination of planets, signs and houses that colours a theme in the chart. Think of each as a *tendency that asks to be developed*, not a verdict. Strength matters more than mere presence: dignity, combustion, house placement, aspects and the running dasha all modulate how visibly a yoga shows up. Each section below is named exactly as the app engine names it (`yogas.py`). Sections for yogas the engine does not yet compute are marked "not computed by the engine".

Where results are described, they follow the classical texts as tendencies. Older texts often use stark language (for example calling Kemadruma poverty-bringing); modern practice reads those statements as themes of self-reliance, isolation or fluctuation that real lives usually soften.

## How the engine measures strength

For each yoga the engine takes the average dignity level of the participating planets (exalted, moolatrikona or own = 2; friendly or neutral = 1; enemy or debilitated = 0), subtracts one level if any participant is combust, adds one if every participant sits in a kendra or trikona (houses 1, 4, 5, 7, 9, 10) from the lagna, and clamps the result to weak / moderate / strong. This is a transparent heuristic, not a classical formula. Treat "strong" as "well supported by dignity and placement" and "weak" as "present but thinly supported".

When birth time is unknown the lagna is unknown, so every lagna-dependent yoga (the five Mahapurusha yogas, Raja, Dhana, Viparita Raja, Neecha Bhanga) is simply not computed. Moon-based and sign-based yogas remain, flagged as approximate.

## Ruchaka Yoga

**Formation.** Mars in its own sign (Aries or Scorpio) or exaltation (Capricorn) *and* in a kendra (1, 4, 7, 10) from the lagna. This is one of the five Pancha Mahapurusha ("five great person") yogas described by Parashara and Varahamihira.

**Tendencies.** Courage, athletic or protective energy, decisive leadership, comfort with competition, a strong constitution. In career terms it is often associated with military, sport, surgery, engineering, law enforcement or entrepreneurship. The growth edge is channelling intensity into constructive effort and learning patience.

**Strength and modification.** Strongest when Mars is exalted in the 10th (Capricorn) or in its own sign in the 1st. Combustion (within 17 degrees of the Sun) or heavy affliction dulls the yoga. The Moon-based variant (Mars in a kendra from the Moon) is accepted by some teachers as a milder form; the engine counts only lagna-based placement.

**How to see it.** Look for Mars in Aries, Scorpio or Capricorn within houses 1, 4, 7 or 10 of the rashi chart.

**Engine rule.** `Ruchaka Yoga` present when Mars is in own/exalted sign and in a kendra from the lagna. Factor id format `N.MARS.H<house>`.

## Bhadra Yoga

**Formation.** Mercury in Gemini or Virgo (own signs; Virgo is also exaltation) in a kendra from the lagna.

**Tendencies.** Sharp intellect, verbal and analytical skill, commercial sense, learning, wit and a youthful manner. Associated with writing, teaching, trade, accounting, technology and communication. The growth edge is avoiding overthinking and scattered effort.

**Strength and modification.** Mercury is easily combust (within 14 degrees, 12 when retrograde), which reduces the yoga; Mercury conjunct malefics takes on their tone. Mercury in Virgo in the 1st or 10th is the cleanest form.

**How to see it.** Mercury in Gemini or Virgo in houses 1, 4, 7 or 10.

**Engine rule.** `Bhadra Yoga`: Mercury in own/exaltation sign and in a kendra from the lagna.

## Hamsa Yoga

**Formation.** Jupiter in Sagittarius, Pisces (own) or Cancer (exalted) in a kendra from the lagna.

**Tendencies.** Wisdom, ethical sense, teaching ability, generosity, reputation for integrity, a bent toward philosophy, law, counselling or spiritual study. Classical texts praise a dignified bearing. The growth edge is avoiding preachiness or complacency.

**Strength and modification.** Jupiter exalted in Cancer in the 1st, 4th, 7th or 10th is the strongest case. Jupiter is rarely combust but retrograde Jupiter's results are read as more internal and delayed.

**How to see it.** Jupiter in Sagittarius, Pisces or Cancer in a kendra.

**Engine rule.** `Hamsa Yoga`: Jupiter in own/exaltation sign in a kendra from the lagna.

## Malavya Yoga

**Formation.** Venus in Taurus, Libra (own) or Pisces (exalted) in a kendra from the lagna.

**Tendencies.** Refinement, charm, aesthetic taste, comfort-seeking, relationships and artistic talent, an appreciation for beauty and harmony. Often associated with arts, design, hospitality, fashion and diplomacy. The growth edge is moderating indulgence and valuing depth over ease.

**Strength and modification.** Combustion (within 10 degrees, 8 when retrograde) weakens it. Venus in Pisces in the 7th or in Libra in the 1st/4th are classic strong cases.

**How to see it.** Venus in Taurus, Libra or Pisces in houses 1, 4, 7 or 10.

**Engine rule.** `Malavya Yoga`: Venus in own/exaltation sign in a kendra from the lagna.

## Sasa Yoga

**Formation.** Saturn in Capricorn or Aquarius (own) or Libra (exalted) in a kendra from the lagna.

**Tendencies.** Discipline, endurance, organisational ability, authority earned over time, comfort with long-term responsibility. Classical texts link it with leadership of groups or institutions. Results often mature after the early thirties. The growth edge is guarding against rigidity, loneliness or overwork.

**Strength and modification.** Saturn exalted in Libra in the 10th or 4th is a favourite textbook case. Saturn is slow, so the yoga tends to build gradually.

**How to see it.** Saturn in Capricorn, Aquarius or Libra in houses 1, 4, 7 or 10.

**Engine rule.** `Sasa Yoga`: Saturn in own/exaltation sign in a kendra from the lagna.

## Raja Yoga

**Formation (general).** A link between the lord of a kendra (1, 4, 7, 10) and the lord of a trikona (1, 5, 9). Parashara treats the trikonas as the most auspicious houses and the kendras as the pillars of the chart; their lords joining forces is read as a combination for status, effectiveness and recognised achievement. Link types: conjunction, mutual aspect, exchange of signs (Parivartana); some schools also accept one planet's placement in the other's sign.

**Tendencies.** Opportunity, authority, influence, the ability to convert effort into position. Timing is read through the dashas of the planets involved, so the yoga often "activates" during their periods.

**Strength and cancellation.** Raja yogas weaken when the participants are debilitated, combust, or placed in dusthanas (6, 8, 12). A planet that rules both a kendra and a dusthana (for instance Mars for Taurus ascendants: 7th and 12th) carries mixed results.

**How to see it.** Identify the lords of houses 1, 4, 5, 7, 9, 10 and look for them together in one sign, in opposition, or swapped.

**Engine rule.** `Raja Yoga`: kendra lords and trikona lords (distinct planets) are conjunct, in *mutual* aspect (graha drishti) or in sign exchange. Factor ids `Y.RAJA.<A>.<CONJ|ASPECT|EXCHANGE>.<B>`. Note the engine does not count the lagna lord as both a kendra and a trikona lord pairing with itself, and a single yogakaraka (see `kb_chart_functional_nature_by_lagna.md`) is not reported as a Raja Yoga by itself.

**School note.** Some teachers also require the pair to be mutually supportive in the navamsa; the engine does not check this.

## Dhana Yoga

**Formation.** The lords of the wealth houses (2nd and 11th) linked with the lords of the 1st, 5th or 9th. Broader versions include the 5th/9th lords with 2nd/11th and the Jupiter, Venus or Mercury influence on the 2nd.

**Tendencies.** Capacity to earn, save and accumulate resources; a lifelong relationship with material security. It describes *potential for resource-building*, not guaranteed riches; the quality depends on the planets and the dashas.

**Strength.** Better when participants are dignified and in kendras/trikonas, weaker when combust or in dusthanas.

**How to see it.** Look at who rules the 2nd and 11th and whether they join the lagna, 5th or 9th lord.

**Engine rule.** `Dhana Yoga`: lord of 2 or 11 *conjunct* or in *sign exchange* with lord of 1, 5 or 9 (aspect-only links are not counted). Ids `Y.DHANA.<A>.<CONJ|EXCHANGE>.<B>`.

## Viparita Raja Yoga

**Formation.** The lord of a dusthana (6, 8 or 12) sits in another dusthana. Classical names for the three versions: Harsha (6th lord), Sarala (8th lord) and Vimala (12th lord).

**Tendencies.** Gains that emerge *through* difficulty: rising after setbacks, benefiting from competitors' stumbles, resilience, unconventional success. Often seen as a "reversal of fortune" pattern, with results largest in the dasha of the participating lord.

**Strength and cancellation.** Weaker if the lord is also conjunct strong benefic influences from kendras/trikonas (which re-routes it toward ordinary house results) or heavily afflicted. Some teachers require that the lord be free of other lordships and not aspected by the lagna lord.

**How to see it.** E.g. 6th lord in the 8th or 12th; 8th lord in the 6th or 12th; 12th lord in the 6th or 8th.

**Engine rule.** `Viparita Raja Yoga`: the lord of 6, 8 or 12 occupies a *different* dusthana. Factor id `Y.VIPARITA.<PLANET>.L<h>.H<placed>`. A dusthana lord sitting in its own house is not counted.

## Neecha Bhanga Raja Yoga

**Formation (cancellation of debilitation).** A debilitated planet's weakness is cancelled or reversed if, for example: (a) the lord of its debilitation sign is in a kendra from the lagna or Moon; (b) the planet that would be exalted in that sign is in a kendra; (c) the debilitated planet is aspected by its sign lord. Different texts list between two and seven variants.

**Tendencies.** A "lesson-then-mastery" pattern: the early life theme is challenging but the planet's significations later become a source of strength or unusual accomplishment.

**Strength.** Several simultaneous cancellations are stronger; a cancelled planet that remains combust or in a dusthana is mixed.

**How to see it.** Find a debilitated planet; check the dispositor (its debilitation sign lord) and the exaltation lord of that sign.

**Engine rule.** `Neecha Bhanga Raja Yoga`: for each debilitated classical planet, the dispositor or the exaltation lord of that sign must be in a kendra from the lagna or the Moon. Reported strength is always "moderate". Ids `Y.NEECHABHANGA.<PLANET>.<HELPER>`. The aspect-based and mutual-exaltation variants are not implemented.

## Gajakesari Yoga

**Formation.** Jupiter in a kendra (1, 4, 7, 10) from the Moon. The Jataka Parijata also records a variant in which the Moon is aspected by Venus, Jupiter and Mercury without being weakened by the Sun.

**Tendencies.** Dignity, reputation, intelligence, a supportive social network, and good counsel in times of need. Jataka Parijata describes the native as energetic, prosperous and capable. Modern reading: emotional resilience grounded in wisdom and goodwill.

**Strength and cancellation.** Weakened if Jupiter is debilitated, combust or in the 6th/8th/12th from the lagna, or the Moon is very weak (waning, near the Sun, afflicted by nodes). Some commentators require both planets to be free of enemy sign placement.

**How to see it.** Count from the Moon's sign: Jupiter in the same sign, 4th, 7th or 10th.

**Engine rule.** `Gajakesari Yoga`: Jupiter in house 1, 4, 7 or 10 counted from the Moon. This works even if the lagna is unknown. Factor id `N.JUPITER.KENDRA_FROM_MOON`.

## Budhaditya Yoga

**Formation.** Sun and Mercury in the same sign.

**Tendencies.** Intelligence, communication skills, administrative or analytical talent, pride in knowledge. Since Mercury never strays far from the Sun (maximum elongation about 28 degrees) this is a very common yoga; its quality depends on how close the planets are.

**Strength and cancellation.** When Mercury is within roughly 14 degrees (12 when retrograde) of the Sun it is combust, and the intellect may feel overshadowed by ego or by external duties. Many teachers still note that Mercury is "cazimi" (within about 1 degree or 0.3 degree depending on school) as a special case of strength; this is a Western-influenced idea that is not part of the classical Parashari system.

**How to see it.** Sun and Mercury both in one rashi.

**Engine rule.** `Budhaditya Yoga` present when the two share a sign; marked "weak" when they are within 4 degrees of each other (engine heuristic for combust dilution). Factor id `N.SUN.CONJ.MERCURY`. Works without a lagna.

## Chandra-Mangala Yoga

**Formation.** Moon and Mars in the same sign (conjunction). In some teachings the mutual aspect between them also counts.

**Tendencies.** Drive for material accomplishment, entrepreneurship, emotional intensity, a strong sense of self-reliance and responsiveness. Classical remarks on money-making ability in trade are balanced by comments on emotional volatility. Growth edge: calming reactivity.

**Strength.** Better when Moon is waxing and Mars well placed; weaker in the sign of debilitation (Moon in Scorpio with Mars is an uneasy case) or heavily afflicted by Saturn.

**How to see it.** Both in one sign.

**Engine rule.** `Chandra-Mangala Yoga`: same-sign conjunction only. Factor id `N.MOON.CONJ.MARS`.

## Kemadruma Yoga

**Formation.** No planet (excluding the Sun, usually the nodes as well) in the 2nd or 12th from the Moon, and no planet in a kendra from the Moon or lagna (cancellation conditions vary). Jataka Parijata records several definitions including one by the absence of Sunapha, Anapha and Durudhara yogas.

**Tendencies.** A sense of standing alone: solitary effort, emotional self-reliance, fluctuating resources or support. Older texts describe poverty or isolation; contemporary reading emphasises building inner stability and conscious community, and notes that the yoga is cancelled in a large share of charts.

**Cancellation.** Jataka Parijata states that the yoga is not operative when a planet occupies a kendra from the lagna or Moon. Other teachers cancel it by a planet in the Moon's sign (except the Sun), Moon in a kendra, Moon aspected by Jupiter or Venus, or Moon in a strong sign. Phaladeepika and Brihat Jataka treat it as a serious yoga if uncancelled.

**How to see it.** Check the signs on both sides of the Moon and the kendras from the Moon.

**Engine rule.** `Kemadruma Yoga` present only if no classical planet other than the Sun and Moon is in the 2nd or 12th from the Moon *and* none in a kendra from the Moon (house 1 included). Strength fixed at "moderate". Because the cancellation is built in, the engine will report Kemadruma more rarely than simple definitions. Factor `D.KEMADRUMA`.

## Kaal Sarp Dosha

**Formation.** All seven classical planets lie within the 180-degree arc between Rahu and Ketu (on one side of the axis).

**Origin note.** Kala Sarpa as a named yoga appears in later commentarial literature and modern popular Jyotish; it is not described under that name in BPHS, Brihat Jataka or Jataka Parijata (the Jataka Parijata index lists "Sarpa yoga", which is a different, Saturn/malefic-based combination). Authorities disagree on whether it is a valid classical yoga at all, so treat claims about it with caution.

**Tendencies (where used).** Life themes revolve around karmic intensity, unevenness, an unusual path and strong focus; many people with this pattern report purposeful, driven lives. Twelve named types are used in popular practice by the Rahu house position (Anant, Kulik, Vasuki and so on).

**Strength.** Reading varies widely; tightly bounded by the axis (no planet outside) is "full", partial versions are common. The engine downgrades to moderate when a planet is within 1 degree of a node.

**How to see it.** Rahu to Ketu going forward, if every planet lies in the arc, in sign or by degree.

**Engine rule.** `Kaal Sarp Dosha`: all seven classical planets strictly within the 180 degrees from Rahu *or* from Ketu. Factor `D.KAALSARP`. It does not distinguish the 12 types.

## Mangal Dosha

**Formation.** Mars in the 1st, 2nd, 4th, 7th, 8th or 12th house from the lagna (many teachers also count from the Moon and from Venus). Southern traditions sometimes omit the 2nd house, and some northern schools omit the 1st for certain lagnas.

**Tendencies.** Intensity and assertiveness in partnerships, a need to channel drive without conflict, and a call for matching energy levels with a partner. Compatibility traditions treat it as a factor to be balanced, not a barrier; many cancellations exist.

**Cancellations (not evaluated by the engine).** Mars in its own or exalted sign; Mars in Cancer/Leo for some [unverified; lists vary]; Jupiter or Venus aspecting or joined with Mars; the partner having a comparable Mars placement; Mars in particular house/sign combinations (for instance 2nd house in Gemini/Virgo; 4th in Aries/Scorpio; 7th in Capricorn; 8th in Sagittarius/Pisces; 12th in Taurus/Libra). Parity matching is the widely used practical remedy.

**How to see it.** Count the house of Mars from lagna and Moon.

**Engine rule.** `Mangal Dosha`: houses (1, 2, 4, 7, 8, 12) from lagna and from Moon. Result "strong" if both references trigger, "moderate" if only one. With unknown time only the Moon reference is used. Cancellations are not evaluated; the description says so. The ManglikResult fields are `from_lagna`, `from_moon`, `mars_house_from_lagna`, `mars_house_from_moon`.

## Yogas outside the engine (for completeness)

### Sakata Yoga (not computed by the engine)
Jupiter in the 6th, 8th or 12th from the Moon. Jataka Parijata notes that the yoga is weakened or void if Jupiter is in a kendra from the lagna. Texts speak of ups and downs in fortune "like a wheel"; a modern reading is of periodic reversals that build adaptability. Not to be confused with the Brihat Jataka's Sakata nabhasa yoga, where all planets lie in the 1st and 7th.

### Amala Yoga (not computed by the engine)
A natural benefic in the 10th house from the lagna or the Moon. Jataka Parijata attributes durable good reputation. Practically it points to public conduct that earns respect.

### Parivartana Yoga (not computed by the engine)
Mutual exchange of signs between two planets. Maha Parivartana: exchange between lords of two good houses (1, 2, 4, 5, 7, 9, 10, 11) gives mutually reinforcing themes. Khala Parivartana involves the 3rd house; Dainya Parivartana involves a dusthana (6, 8, 12) and links those themes with an uncomfortable twist. The engine uses exchange only inside Raja and Dhana yogas.

### Pitra Dosha (not computed by the engine)
A popular (not strictly classical) label for combinations such as an afflicted Sun or 9th house, Sun with Rahu/Saturn, or malefics on the 9th house and 9th lord, read as an ancestral-theme or father-line stress signal. Remedies are devotional (honouring ancestors, charity). Sources differ widely; treat as a reflective prompt rather than a finding.

## Using yogas in conversation

Ask the user for context before assigning meaning. Tell them what the combination is made of, what it tends to highlight, which dasha might switch it on, and what would strengthen or weaken it. Avoid statements that a yoga "guarantees" or "forbids" an outcome.
