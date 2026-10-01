export interface User {
  id: string;
  email: string;
  name: string;
  email_verified: boolean;
  avatar_url?: string | null;
  subscription_tier: string;
  timezone: string;
  created_at: string;
  // [v1-add] optional (api-contract §2.1); absent on MVP backends
  has_password?: boolean;
  preferred_language?: ChatLanguage;
  astrology_system?: "vedic" | "western";
  quota?: { chat_remaining_today: number; chat_daily_limit: number; resets_at: string };
}

export type ChatLanguage = "english" | "hindi" | "hinglish";
export type RelationshipType = "romantic" | "friend" | "family" | "coworker";

export interface ChartSignData {
  sign: string;
  degree: number;
  house?: number;
  element?: string;
  modality?: string;
  approximate?: boolean;
}

export interface VedicPlanet {
  name: string;
  english: string;
  rashi: string;
  rashi_english: string;
  degree: number;
  nakshatra: string;
  pada: number;
  nakshatra_lord: string;
  house?: number | null;
  retrograde: boolean;
  combust: boolean;
  dignity: string;
  speed: number;
}

export interface VedicLagna {
  rashi: string;
  rashi_english: string;
  degree: number;
  nakshatra: string;
  pada: number;
}

export interface MoonNakshatra {
  name: string;
  pada: number;
  lord: string;
  deity: string;
  symbol: string;
  nature: string;
  gana: string;
  nadi: string;
}

export interface DashaPeriod {
  lord: string;
  start: string;
  end: string;
  approximate?: boolean;
}

export interface DashaInfo {
  maha_dasha: { current: string; start: string; end: string; duration_years: number };
  antar_dasha: { current: string; start: string; end: string };
  // [v1-add] (astrology-engine.md §5.2)
  approximate?: boolean;
  /** Engine 2.0, unknown birth time: why the dates are uncertain. */
  approximate_note?: string;
  /** Running MD/AD if born at 00:00 vs 23:59. */
  candidates?: Array<{ moon_longitude?: number; maha_dasha?: string; antar_dasha?: string; balance_at_birth_years?: number }>;
  timeline?: Array<DashaPeriod & { antar?: DashaPeriod[] }>;
}

/** [v1-add] graha drishti emitted by the engine (astrology-engine.md §5.5). `to_house` is null without a birth time. */
export interface VedicAspect {
  from: string;
  to_house: number | null;
  to_planets: string[];
}

export interface YogaInfo {
  name: string;
  present: boolean;
  strength: string;
  description: string;
  factors?: string[];
  /** True when computed without a birth time. */
  approximate?: boolean;
}

export interface HouseLord {
  house: number;
  lord: string;
  lord_in_house: number;
  lord_rashi: string;
}

export interface DivisionalChart {
  lagna: { rashi: string };
  planets: VedicPlanet[];
}

export interface VedicData {
  ayanamsa_value: number;
  /** Absent/null when the birth time is unknown (houses and ascendant cannot be computed). */
  lagna?: VedicLagna | null;
  houses_available?: boolean;
  /** Engine 2.0: what is withheld when the birth time is unknown. */
  suppressed?: { reason?: string; items?: string[] } | null;
  planets: VedicPlanet[];
  moon_nakshatra: MoonNakshatra;
  dasha: DashaInfo;
  yogas?: YogaInfo[];
  house_lords?: HouseLord[];
  functional_benefics?: string[];
  functional_malefics?: string[];
  sade_sati?: { active: boolean; phase: string };
  yogakaraka?: string | null;
  aspects?: VedicAspect[];
  navamsa_d9?: DivisionalChart;
  dashamsa_d10?: DivisionalChart;
}

export interface ChartData {
  sun_sign: ChartSignData;
  moon_sign: ChartSignData;
  rising_sign: ChartSignData;
  planets: PlanetPosition[];
  houses: HousePosition[];
  aspects: Array<{ planet1: string; planet2: string; type: string; angle: number; orb: number }>;
  mc?: ChartSignData;
  metadata?: { house_system: string; approximate_time: boolean; houses_available?: boolean; ayanamsa?: string; timezone?: string; utc_offset_minutes?: number };
  vedic?: VedicData;
  houses_available?: boolean;
}

export interface BirthChart {
  id: string;
  user_id: string;
  name: string;
  relationship_label: string;
  date_of_birth: string;
  time_of_birth: string | null;
  has_exact_time: boolean;
  birth_place_name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  chart_data: ChartData;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}

export interface PlanetPosition {
  name: string;
  sign: string;
  degree: number;
  house: number | null;
  retrograde: boolean;
}

export interface HousePosition {
  number: number;
  sign: string;
  degree: number;
}

export interface Conversation {
  id: string;
  user_id: string;
  chart_id: string | null;
  title: string | null;
  category: string | null;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id?: string;
  role: "user" | "assistant";
  content: string;
  bookmarked?: boolean;
  tokens_used?: number | null;
  created_at: string;
  // [v1-add]
  citations?: Array<{ factor_id: string; label: string }>;
  /** Provenance: source titles only (opaque ids, no long quotes). */
  sources?: Array<{ source_id: string; title: string; section?: string | null; tier?: number | null }>;
  feedback?: "up" | "down" | null;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
}

export interface DailyHoroscope {
  id: string;
  zodiac_sign: string;
  date: string;
  general_reading: string;
  love_reading: string | null;
  career_reading: string | null;
  wellness_reading: string | null;
  lucky_number: number | null;
  lucky_color: string | null;
  transit_data: Record<string, unknown>;
  created_at: string;
}

export interface GeocodingResult {
  name: string;
  lat: number;
  lon: number;
  timezone?: string;
}

export interface CompatibilityCategory {
  score: number;
  summary: string;
}

export interface SynastryAspect {
  planet1: string;
  planet2: string;
  aspect: string;
  orb: number;
  interpretation: string;
}

export interface AshtakootaResult {
  total: number;
  max?: number;
  kootas?: Array<{ name: string; score: number; max: number; note?: string }>;
  nadi_dosha?: boolean;
  bhakoot_dosha?: boolean;
  gana_dosha?: boolean;
  verdict?: string;
  approximate?: boolean;
  alternate_total?: number | null;
  orientation?: string;
  /** Engine 2.0 */
  tables_fixture_verified?: boolean;
  tables_note?: string;
  total_range?: [number, number] | null;
  moon_ambiguous?: boolean;
  note?: string;
}

export interface ScoreBreakdown {
  category_weights?: Record<string, number>;
  category_scores?: Record<string, number>;
  weighted_contributions?: Record<string, number>;
  blend?: string;
  formula?: string;
  explanation?: string;
  ashtakoota?: { included?: boolean; total?: number; scaled_0_10?: number; tables_fixture_verified?: boolean; tables_note?: string };
  overall_range?: [number, number];
}

export interface CompatibilityReport {
  id: string;
  chart1_id: string;
  chart2_id: string;
  relationship_type: string;
  overall_score: number;
  compatibility_data: {
    categories: Record<string, CompatibilityCategory>;
    synastry_aspects: SynastryAspect[];
    strengths: string[];
    challenges: string[];
    // [v1-add]
    summary?: string;
    approximate?: boolean;
    ashtakoota?: AshtakootaResult | null;
    score_breakdown?: ScoreBreakdown | null;
  };
  partner_name?: string;
  created_at: string;
}

/** R3 personal daily reading (api-contract §7, [v1-add]). */
export interface AreaReading {
  score: number;
  text: string;
}

export interface PersonalReading {
  date: string;
  chart_id: string;
  system: "vedic" | "western";
  headline: string;
  overview: string;
  areas: { love: AreaReading; career: AreaReading; wellness: AreaReading; money: AreaReading };
  key_factors: Array<{ factor_id: string; label: string; weight: number }>;
  timing: {
    best_window?: { start: string; end: string; reason: string };
    rahu_kaal?: { start: string; end: string };
  };
  dasha_context?: { maha: string; antar: string; note: string };
  affirmation: string;
  lucky: { number?: number; color?: string };
  generated_by: "llm" | "template";
}

/** SSE events from POST /chat/conversations/{id}/messages/stream (api-contract H6). */
export type ChatStreamEvent =
  | { type: "meta"; user_message: Message }
  | { type: "delta"; text: string }
  | { type: "replace"; text: string }
  | { type: "done"; assistant_message: Message }
  | { type: "error"; code: string; detail: string };

/** End time of a panchang element. `end_local_date` (YYYY-MM-DD) is planned by the backend; absent today. */
export interface PanchangItem {
  end_local: string | null;
  end_local_date?: string | null;
}

/** C9 Panchang (astrology-engine.md §5.7). Times are local "HH:MM" strings (`*_local`). */
export interface Panchang {
  date: string;
  timezone: string;
  sunrise_local: string | null;
  sunset_local: string | null;
  sunrise_available: boolean;
  vara: string;
  tithi: PanchangItem & { number: number; name: string; paksha: string; next: string | null };
  nakshatra: PanchangItem & { name: string; pada: number; lord: string };
  yoga: PanchangItem & { number: number; name: string };
  karana: PanchangItem & { number: number; name: string };
  rahu_kaal: { start_local: string | null; end_local: string | null } | null;
}

/** C7 transits for a chart (insight_service.get_transits). */
export interface WesternTransit {
  transiting: string;
  natal: string;
  type: string;
  orb: number;
  applying: boolean;
  window_start?: string | null;
  window_end?: string | null;
}

export interface Gochara {
  planet: string;
  rashi: string;
  house_from_moon?: number | null;
  house_from_lagna?: number | null;
}

export interface TransitsResponse {
  chart_id: string;
  from: string;
  days: number;
  computed_for: string;
  western: WesternTransit[];
  vedic: {
    gochara?: Gochara[];
    moon_transit_house?: number;
    moon_transit_rashi?: string;
    sade_sati?: { active: boolean; phase: string };
  };
}

/** C8 Vimshottari timeline, levels=2 only (levels=3 returns 422). */
export interface DashaResponse {
  chart_id: string;
  levels: number;
  approximate: boolean;
  current: { maha_dasha?: DashaInfo["maha_dasha"]; antar_dasha?: DashaInfo["antar_dasha"] };
  timeline: NonNullable<DashaInfo["timeline"]>;
}
