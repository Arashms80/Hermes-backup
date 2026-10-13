# Iranian market price sources (tested)

Domain depth for in-app live-price features (قیمت‌ها tab) in the user's single-file HTML app, and for any fetch of Iranian market quotes from a browser page. Under "Verified" = answered HTTP 200 with a parseable body from a browser page. Free-API availability churns: re-test any source in the same session before wiring it in, and never present a stale verification as live.

## Feature gate
- The refresh cross-checks **≥3 independent sources** for whatever items have a live feed; three mirrors of one upstream are not three sources. When no materials feed answers (the usual case), the three may all be financial feeds — materials rows then stay **manual**, and the sources panel lists the materials sources tried with their status so the user still sees what was checked.
- It **shows the sources**: per-item attribution plus the quote's own date/time.
- Manual prices are the fallback: overwrite a stored price only from a source that actually answered.

## Verified endpoints

### TGJU call2 — primary: طلا/دلار/یورو/سکه، CORS-open
`https://call2.tgju.org/ajax.json` → ~170 KB JSON; `fetch` straight from the page works — verified `mode:'cors'` → 200 from `about:blank` AND from a `file://` page (no proxy, no latency). `current` maps slug → `{p, h, l, d (تغییر مطلق), dp (درصدی), t (ساعت فارسی), t_en, ts}`; slugs carry no title — titles live in the `last` list.
- Values are **RIAL — ÷10 for تومان** (geram18/geram24 are rial per gram).
- Keys: `price_dollar_rl` (دلار آزاد), `price_eur`, `geram18`, `geram24`, `sekee` (امامی), `sekeb` (بهار آزادی), `nim` (نیم), `rob` (ربع), `gerami` (گرمی); `retail_*` = خرده‌فروشی. `price_dollar` does not exist and the other `price_dollar_*` keys are other markets or stale — check `t_en` on every key before using it.
- **call1.tgju.org sends NO CORS headers** — its fetch fails while call2 succeeds side-by-side in the same tab. Do not swap the host to call1.

### Bonbast — second opinion: currency, gold, coins, dated (via r.jina.ai)
`https://r.jina.ai/https://bonbast.com/` → ~7 KB markdown text; all values **TOMAN** (the page states it). Parse with regex:
- Top cards: `US Dollar/ IRR` then a blank line then `253,500 Toman` — same shape for `Euro/ IRR`, `Gold Gram`, `Gold Mithqal`, `Coin Emami`. regex-escape label specials (`½/¼/½ Azadi` are literal chars; `US Dollar/ IRR` contains `/`).
- Coins: `Azadi 257,000,000 252,000,000` (sell, buy) — Azadi/Emami/½ Azadi/¼ Azadi/Gerami — and the top-card render also emits a **single-number + `Toman`** shape. Parse BOTH shapes: try `label <num> <num>` first, fall back to `label <num> Toman` (window ~120 chars). A coins regex that only accepts the two-number shape returns 0 for every coin when the page render emits the other shape.
- Quote date: a line like `_Month DD, YYYY HH:MM_` → `/_([A-Z][a-z]+ \d{1,2}, \d{4} \d{2}:\d{2})_/`.
- jina adds ~5–15 s latency (cache makes repeat calls ~0.3 s); bonbast itself sends no CORS headers — the jina route is the only browser path.

### Nobitex + Bitpin — two CORS-open crypto exchanges: tether ≈ dollar, fetch DIRECT
`https://apiv2.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls` → tiny (~330 B) JSON, `CORS: *`, ~0.4 s; read `stats['usdt-rls'].latest` (RIAL → ÷10 for تومان). The sibling `/currencies/list` endpoint is 403 — do not chain guesses; the stats URL above is the one that answers. When a test burst of fetches from one page all fail with instant `TypeError: Failed to fetch` but server-side curl answers 200, suspect the burst itself (the exchange rate-limits the tab), not each endpoint — re-probe one at a time with `Origin` set before declaring a source dead.
`https://api.bitpin.ir/v1/mkt/markets/` → ~3.2 MB JSON, `CORS: *`, ~3 s; there is **no filter or symbol endpoint** — every query param (`?page_size`, `?search`, `?symbol=…`) still returns all 1364 markets, so fetch once and loop `results[]` for `currency1.code==='USDT' && currency2.code==='IRT'`, read `m.price` (تومان). PAXG/XAUT pairs (gold-pegged) also exist on the same response if a gold cross-check is ever needed. The jina route 422s on bitpin — direct only.
With these two, a refresh can keep ≥3 sources answering even when every jina route is slow: TGJU + nobitex + bitpin respond directly in <4 s; bonbast/Wallex (jina) join when they join.

### Wallex — third opinion: tether ≈ dollar (via r.jina.ai)
`https://r.jina.ai/https://api.wallex.ir/v1/markets` → ~440 KB markdown-wrapped JSON — never stringify it into a tool result; extract in JS. Find `"USDTTMN":{`, **bound the `lastPrice` search to that symbol's object** (stop at the next `"symbol":` occurrence — 371 symbols follow, so an unbounded slice+match can read a neighbor's price), read `lastPrice` (string, تومان) ≈ the free-market dollar rate. There are 371 symbols and `EURTMN` is NOT one of them — Wallex carries tether/crypto pairs only, so wire the euro from TGJU/bonbast, never from Wallex. Direct browser fetch of `api.wallex.ir` is 403 (its ACAO pins `https://wallex.ir`, plus gzip) — the jina route is the only browser path.

## Construction materials — no verified live feed; manual entry is the path
- tgju carries **no Iranian materials keys** — only global benchmarks (`base_global_steel`, `base_global_iron_ore`, `base-us-steel-coil`, `base-us-iron-ore`) in USD: a trend note, not an Iran-market price.
- forsatnet (`price.forsatnet.ir/construction-materials.html`) serves a usable HTML table (سیمان/گچ/بلوک — no شن/ماسه rows) but only to server-side curl: the browser fetch has no ACAO and the jina route 422s (`HTTP/3 error`).
- ahanonline serves full steel tables to direct browser navigation (lazy: tables arrive ~10 s in + scroll) but is unreachable from the app (no ACAO) and via jina (422).
- Mirror proxies all failed when tested together (allorigins 502/500, codetabs 522) — do not stack them as a fallback chain; re-test whichever route you pick per session before trusting it.
- Net rule: keep materials rows manual and let these sources' status lines report in the sources panel — do not let their known failures make the whole refresh look broken.
- alanchand's real API is `https://api.alanchand.com?type=currency|gold|crypto&symbols=…` requiring `Authorization: Bearer <token>` (free tier: 1 req/hour, token via their contact form); the guessed `/api-types-currency` path is 404 — not usable without a token.
- sahimino.com — currency/gold/coin/iron-steel/materials categories with dated Rial prices; still unverified — curl with a browser User-Agent before trusting it.

## CORS: browser-side fetch routes
- **Try the direct fetch first** — call2.tgju.org is CORS-open (verified); probe every other host the same way before assuming it needs a proxy.
- **Text proxy: `https://r.jina.ai/<target>`** (verified CORS-free from the browser; echoes the requesting Origin in ACAO, so it works from any page). jina rate-limits — 6+ rapid calls start failing: stagger proxy-based sources in the app instead of firing them simultaneously. Mirror proxies churn — re-test per session, and record which path served each item.
- Probe with the fetch-probe pattern in `references/browser-verification.md`: fire-and-forget to a window flag, read in a second call — never await a long fetch inside `js()`.

## Validation
- Cross-check the coins against bonbast: tgju rial/10 == bonbast toman (sekee→Emami, sekeb→Azadi, nim→½ Azadi, rob→¼ Azadi) and `geram18/10 ≈` bonbast Gold Gram — when they diverge one feed is stale; prefer the newer `t_en`/date.
- Cross-check gold against ounce×dollar: `g24 ≈ ounce_usd × dollar_toman / 31.1035`.
- Cross-check dollar: tgju `price_dollar_rl/10` vs bonbast USD vs wallex `USDTTMN.lastPrice` — within a few percent of each other.
- Watch the app-side unit mismatch: external sources quote ماسه per ton/truck while the app's est fields are m³ or ton — convert explicitly or leave that field manual.

## App-side price inputs a global profile feeds
masonry `mwPc/mwPs/mwPb`, plaster `plPc/plPs`, concrete `cnPc/cnPs/cnPg`, mix-design `mdPc/mdPs/mdPg` (قیمت سیمان تومان/کیسه ۵۰، ماسه تومان/m³ یا /تن، شن تومان/تن، بلوک تومان/عدد). A prices tab can push into these with one «اعمال به برآورد» button — read the field ids from the est-section markup first, never assume.
