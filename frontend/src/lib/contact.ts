/** Public contact address for privacy requests and grievances; set VITE_CONTACT_EMAIL at build time. */
const raw = (import.meta.env.VITE_CONTACT_EMAIL as string | undefined)?.trim();
export const CONTACT_EMAIL: string | null = raw && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(raw) ? raw : null;
