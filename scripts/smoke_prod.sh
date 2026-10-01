#!/usr/bin/env bash
# Black-box smoke test for a deployed Nakshion API. Contains no secrets and mutates nothing.
#
#   BASE_URL=https://nakshion-api.onrender.com scripts/smoke_prod.sh
#   BASE_URL=http://localhost:8010 scripts/smoke_prod.sh                 # local run (skips prod-only checks)
#
# Optional:
#   FRONTEND_ORIGIN=https://your-app.vercel.app   verify CORS allows it (and refuses an unknown origin)
#   EXPECT_PROD=1                                  also assert docs are disabled, HSTS is sent, source link present
set -u
BASE_URL="${BASE_URL:?set BASE_URL, e.g. https://nakshion-api.onrender.com}"
BASE_URL="${BASE_URL%/}"
API="$BASE_URL/api/v1"
pass=0; fail=0
ok()   { echo "  ok    $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail+1)); }
check() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected $3, got $2)"; fi; }
status() { curl -s -o /dev/null -w '%{http_code}' --max-time "${TIMEOUT:-60}" "$@"; }
body()   { curl -s --max-time "${TIMEOUT:-60}" "$@"; }
has()    { case "$1" in *"$2"*) return 0;; *) return 1;; esac; }

echo "== liveness (first call may take ~1 minute while Render wakes the service)"
check "GET /health/live" "$(status "$BASE_URL/health/live")" 200
has "$(body "$BASE_URL/health/live")" '"status":"ok"' && ok "live body" || bad "live body"
check "GET /health (alias)" "$(status "$BASE_URL/health")" 200

echo "== readiness (database, redis, engine)"
ready="$(body "$BASE_URL/health/ready")"
has "$ready" '"database":true' && ok "database up" || bad "database: $ready"
has "$ready" '"redis":true'    && ok "redis up"    || bad "redis: $ready"
has "$ready" '"engine":true'   && ok "ephemeris engine up" || bad "engine: $ready"

echo "== public endpoints"
check "daily horoscope" "$(status "$API/horoscopes/daily?sign=leo")" 200
check "invalid sign is 400" "$(status "$API/horoscopes/daily?sign=dragon")" 400
check "panchang" "$(status "$API/panchang?date=2026-10-01&lat=18.5&lon=73.8")" 200

echo "== auth surface"
check "GET /auth/me without token is 401" "$(status "$API/auth/me")" 401
has "$(body "$API/auth/me")" '"code":"UNAUTHENTICATED"' && ok "401 carries error code" || bad "401 error code"
check "geocoding requires auth" "$(status "$API/geocoding/search?q=pune")" 401
check "charts (no slash) requires auth" "$(status "$API/charts")" 401
check "charts/ (slash) requires auth, no redirect" "$(status "$API/charts/")" 401
check "cron without secret is 401" "$(status -X POST "$BASE_URL/internal/cron/daily_maintenance")" 401

echo "== error shape"
r="$(body -X POST "$API/auth/login" -H 'Content-Type: application/json' -d '{"email": "a@b.co", "password": }')"
has "$r" "isn't valid JSON" && ok "malformed JSON gives a plain message" || bad "malformed JSON message: $r"
check "wrong credentials are 400 (never 401)" "$(status -X POST "$API/auth/login" -H 'Content-Type: application/json' -d '{"email":"nobody@example.com","password":"not-a-real-password"}')" 400
big="$(head -c 70000 /dev/zero | tr '\0' 'x')"
payload="{\"email\":\"a@b.co\",\"password\":\"$big\"}"
check "70 KB body is refused (413)" "$(status -X POST "$API/auth/login" -H 'Content-Type: application/json' --data-binary "$payload")" 413

echo "== security headers"
h="$(curl -s -D - -o /dev/null --max-time 60 "$BASE_URL/health/live" | tr -d '\r' | tr 'A-Z' 'a-z')"
has "$h" "x-content-type-options: nosniff" && ok "nosniff" || bad "nosniff"
has "$h" "x-frame-options: deny" && ok "frame deny" || bad "frame deny"
has "$h" "x-request-id:" && ok "request id" || bad "request id"

if [ -n "${FRONTEND_ORIGIN:-}" ]; then
  echo "== CORS"
  pre() { curl -s -D - -o /dev/null -X OPTIONS "$API/charts" -H "Origin: $1" -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: authorization,content-type' | tr -d '\r' | tr 'A-Z' 'a-z'; }
  has "$(pre "$FRONTEND_ORIGIN")" "access-control-allow-origin: $(echo "$FRONTEND_ORIGIN" | tr 'A-Z' 'a-z')" && ok "frontend origin allowed" || bad "frontend origin NOT allowed"
  has "$(pre "https://evil.example")" "access-control-allow-origin" && bad "unknown origin was allowed" || ok "unknown origin refused"
fi

if [ "${EXPECT_PROD:-0}" = "1" ]; then
  echo "== production-only"
  check "/docs is disabled" "$(status "$BASE_URL/docs")" 404
  check "/openapi.json is disabled" "$(status "$BASE_URL/openapi.json")" 404
  has "$h" "strict-transport-security:" && ok "HSTS sent" || bad "HSTS missing"
  case "$BASE_URL" in https://*) ok "served over https";; *) bad "BASE_URL is not https";; esac
fi

echo; echo "passed=$pass failed=$fail"
[ "$fail" -eq 0 ]
