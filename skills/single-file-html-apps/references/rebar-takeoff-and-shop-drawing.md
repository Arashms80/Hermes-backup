# Takeoff list + cut-and-bend shop drawing (one piece, real dimensions)

> Status: the BEAMETS MOD-01 screen this describes was REMOVED at the user's request after the upgrade shipped — kept as the reusable recipe for any future cut-to-stock takeoff screen (rebar, pipe, profile, cable tray) and for re-adding MOD-01 (its source files stay on disk; the build skips them).

Companion to §5h. Instance: rebar (BEAMETS MOD-01), but the shape carries to any cut-to-stock material — pipe, profile, cable tray. The point of the screen is that the workshop can cut and join from the sheet alone.

## Row inputs

| field | meaning | source |
|---|---|---|
| قطر Φ | mm | fixed size list |
| تعداد | count | user |
| طول خالص | net length of one piece, m | user |
| **خم روی چند سر؟** | 0 / 1 / 2 / 3 / 4 bent ends | user — the option the user explicitly asked for |
| نوع خم / قلاب | T90 · T135 · T180 · L90 · L180 | user |
| وصله | none · A (1.0×Ld) · B (1.3×Ld) | user |

Hook addition per end comes from the app's own engine so the numbers match the dedicated hook screen:
`PC.bendLen(form, 40, 30, d, steel)` → `.mm` (arc + straight extension). Multiply by the number of bent ends.
`PC.ldStraightM9({db,fy,fc,top,epoxy})` → lap length; `A = 1.0×Ld`, `B = 1.3×Ld`, floor 300 mm.
Fallback if the engine is unreachable: transverse `max(6d,75)` @90/135, `max(6d,65)` @180; longitudinal `12d` @90, `max(4d,65)` @180.

## Splitting one piece into stock bars with overlaps

```
cutLen = net + hookPer*nEnds + lapAdd
if cutLen <= stock or lap >= stock: one piece, no overlap
k     = ceil((cutLen - lap) / (stock - lap))      # number of stock bars
pieces = [stock] * (k-1) + [cutLen - (k-1)*(stock - lap)]
laps  = k - 1
```

Worked example the user cares about: net 16 m, Φ16, وصله B → lap ≈ 1.28 m; cutLen ≈ 16.28 m; k = ceil(15/10.72) = 2 → piece 1 = the full 12 m stock bar, piece 2 = 16.28 − (12 − 1.28) = **5.56 m**, with one 1.28 m overlap. With `lap = 0` the same total is simply 12 + 4.28 butted (no overlap band drawn).

`lap = 0` still means `laps = k-1` **joints**; report overlap length as `laps * lapLen` so a zero-lap split never claims overlap it does not have.

## SVG scaffold (viewBox 980×210, drawn L→R, RTL labels anchored)

1. Card rect + hairline border (`#e6ebf0`).
2. Title at the right edge: `نقشهٔ شاپ · Φ{d} — قطعهٔ {idx} · {n} عدد`.
3. Bar row at `y=88`, `barH=16`; `scale = (W − padL − padR) / cutLen`; full bars `#16324a`, the remainder `#2f6f9e`.
4. Above each segment: `قطعهٔ {i} · {len} m` plus, smaller, `شاخهٔ کامل {stock}m` / `قطعهٔ باقی‌مانده`.
5. End ticks at both segment boundaries.
6. Overlap band only when `lapLen > 0`: dashed rect `#f47b20` @0.28 alpha, dimensions in `#c85f10` under the bar.
7. Hooks on free ends only — `L*` hooks bend down, `T*` bend across; hook length label next to the glyph.
8. Total dimension line at `y=176`: `طول برش کل = {cutLen} m ({k} شاخه · {laps} اورلپ)`.
9. Footer line: `خالص {net} m + خم {hook} m + اورلپ {laps*lap} m`.

## Order text template

One array of sentences per row, rendered as an `<ol>` on screen and as a `kind:'list'` PDF section:

- single piece: `شاخهٔ {stock}متری را قطع کن → یک قطعه به طول {cutLen} m` + `و {nEnds} سر آن را {hookPer} m خم بزن`.
- split: step 1 cuts the stock bar to `pieces[0]` and bends the first free end; steps 2..k cut each remaining piece and bend the far end on the last one; then `اتصال: هر قطعه را به اندازهٔ {lap} m روی قبلی اورلپ کن ({laps} اورلپ) و ببند`; then the `جمع طول برش` identity line.

Strip the leading enumerator and `▪` before feeding the list to the PDF renderer (it numbers the rows itself) — otherwise the output is double-numbered.

## Totals block worth showing

طول خالص · افزوده قلاب · افزوده وصله · طول برش کل · تناژ (ton + kg) · شاخهٔ stock لازم · پرت = شاخه×stock − طول برش کل با درصد · مبلغ کل (only when a price is available).

## Verification assertions that actually catch defects

- `splitBar(16.28, 12, 1.28)` → `bars=2, pieces[0]=12, laps=1`; `splitBar(16,12,0)` → 2 pieces and `laps*lapLen = 0`.
- Set the end selector to 2 and a `L90` hook → `nEnds=2`, `hookPer>0`, note contains `2 سر`; set it to 0 → `nEnds=0` and `cutLen = net` exactly.
- The generated SVG string contains `قطعه` and, when splits exist, `اورلپ` — assert on the string, not on a screenshot.
- A 16 m row must satisfy `split.bars >= 2` and `cutLen > 16`.
- PDF: `sections.some(s=>s.kind==='image')` and `some(s=>s.kind==='list')` true, and the image items each carry a non-empty `src`.
