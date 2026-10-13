# Concrete mix proportioning — ACI reference values for auditing an in-app engine

Use when a concrete/mix-design screen's numbers are challenged ("the w/c came out wrong", "check all the formulas against the latest revision"). These are the primary-source values and the exact places an app-sourced table tends to be wrong. Convert and re-check; never copy this file's numbers into new code without re-fetching the standard when the ask is a formal audit.

## Unit constants
- 1 lb/yd³ = 0.5933 kg/m³ (round-trip check: ACI's 350 lb/yd³ = 207 kg/m³, 340 = 205, 280 = 166).
- 1000 psi = 6.895 MPa (6000 psi = 41.4, 5000 = 34.5, 4000 = 27.6, 3000 = 20.7, 2000 = 13.8 MPa).
- ACI covers normal-weight concrete only; heavyweight/mass are separate appendices.

## ACI 211.1-91 Table 6.3.3 — mixing water, kg/m³ (lb/yd³)
Columns are nominal maximum aggregate size: 9.5 / 12.5 / 19 / 25 / 37.5 / 50 / 75 / 150 mm.

Slump 25–50 mm (1–2 in):
- non-air-entrained: 207 / 199 / 190 / 179 / 166 / 154 / 130 / 113
- air-entrained:     181 / 175 / 168 / 160 / 150 / 142 / 122 / 107

Slump 75–100 mm (3–4 in):
- non-air: 228 / 216 / 205 / 193 / 181 / 169 / 145 / 124
- air:     202 / 193 / 184 / 175 / 165 / 157 / 133 / 119

Slump 150–175 mm (6–7 in):
- non-air: 243 / 228 / 216 / 202 / 190 / 178 / 160 / —
- air:     216 / 205 / 197 / 184 / 174 / 166 / 154 / —

Entrapped air in non-air-entrained concrete, percent of concrete volume: 3 / 2.5 / 2 / 1.5 / 1 / 0.5 / 0.3 / 0.2.

Recommended total air content (air-entrained), by exposure: mild 4.5/4.0/3.5/3.0/2.5/2.0/1.5/1.0; moderate 6.0/5.5/5.0/4.5/4.5/4.0/3.5/3.0; severe 7.5/7.0/6.0/6.0/5.5/5.0/4.5/4.0.

Footnotes that are actually binding:
- The air-entrained water column is based on the **moderate** exposure air content — not zero air and not severe.
- Values are maximums for well-shaped angular (crushed) aggregate. **Rounded aggregate takes ~30 lb/yd³ (~18 kg/m³) less water non-air-entrained and ~25 lb/yd³ (~15 kg/m³) less air-entrained.**
- A water-reducing admixture (ASTM C 494) may cut mixing water 5 % or more; HRWR (types F/G) 12–25 %.
- Slump beyond the table's last column is obtained **with** a water reducer, never by adding water — a screen that treats its widest slump column as "just a bit more water" is wrong.

## ACI 211.1-91 Table 6.3.4(a) — w/c vs 28-day strength
Anchor pairs (strength MPa (psi) → max w/c by mass), **one curve per air condition — ACI has no crushed/round split here**; aggregate shape moves unit water, not the strength curve:

- non-air-entrained: 48.3 (7000) → 0.33 · 41.4 (6000) → 0.41 · 34.5 (5000) → 0.48 · 27.6 (4000) → 0.57 · 20.7 (3000) → 0.68 · 13.8 (2000) → 0.82
- air-entrained:     41.4 (6000) → 0.32 · 34.5 (5000) → 0.40 · 27.6 (4000) → 0.48 · 20.7 (3000) → 0.59 · 13.8 (2000) → 0.74

Strength is assumed for nominal maximum aggregate ≈ 19–25 mm and moist-cured cylinders per ASTM C 31. The ACI metric appendix restates the curve with rounded values (e.g. 35 MPa → 0.47 non-air / 0.39 air) — within read-off tolerance of the pair table, so interpolate the pairs, do not mix the two lists cell-by-cell.
A table with invented extra columns (e.g. crushed vs rounded) is the tell that its numbers were never sourced — distrust and re-source the whole table, not the one cell the user noticed.

## ACI 211.1-91 Table 6.3.6 — volume of coarse aggregate per unit volume of concrete
Oven-dry-rodded (ASTM C 29), by fineness modulus 2.40 / 2.60 / 2.80 / 3.00:

- 9.5 mm:  0.50 / 0.48 / 0.46 / 0.44
- 12.5 mm: 0.59 / 0.57 / 0.55 / 0.53
- 19 mm:   0.66 / 0.64 / 0.62 / 0.60
- 25 mm:   0.71 / 0.69 / 0.67 / 0.65
- 37.5 mm: 0.75 / 0.73 / 0.71 / 0.69
- 50 mm:   0.78 / 0.76 / 0.74 / 0.72
- 75 mm:   0.82 / 0.80 / 0.78 / 0.76
- 150 mm:  0.87 / 0.85 / 0.83 / 0.81

This is a dry-rodded volume fraction of the concrete, not a mass; the mass comes from multiplying by the dry-rodded unit weight. §6.3.6.1 lets the volume be **increased** ~10 % for more workable/pumped concrete — so a per-percent-air reduction (a common app heuristic) is not an ACI rule and should be labelled as local practice, not as code.

## Required average strength f'cr
ACI 318-19 Table 5.3.2.2 — no standard-deviation data available: `f'c < 21 MPa → f'c + 7.0`; `21 ≤ f'c ≤ 35 → f'c + 8.5`; `f'c > 35 → 1.10·f'c + 5.0` (psi form: +1000, +1200, 1.10f'c + 700).
ACI 318-19 Table 5.3.2.1 — SD available, the greater of two expressions: for `f'c ≤ 35`: `f'c + 1.34·s` or `f'c + 2.33·s − 3.45 MPa`; for `f'c > 35`: `f'c + 1.34·s` or `0.90·f'c + 2.33·s`.
The 1.34 factor is the 99 %-compliance / 10 %-below-f'c criterion; **a lone `f'c + 1.96·s` term matches no ACI criterion** and is a code-shaped guess — implement the max-of-two form.

## Absolute-volume bookkeeping
`1 = Vc + Vw + Vca + Vair + Vfa` with air expressed as a fraction of total concrete volume. Non-air-entrained concrete still contains entrapped air (table above); carrying `air = 0` there pushes the deficit into the fine-aggregate volume and overstates the sand. Moisture correction on the batch water: `Wadd = W − Msand·(m_s − a_s)/100 − Mca·(m_g − a_g)/100`.

## App-vs-standard defect list (found by auditing a Persian mix-design screen)
- w/c↔strength table invented (extra crushed/round columns, values far above ACI) → the reported "w/c was wrong once".
- f'cr auto rule used `f'c + 4` / `÷ 0.90` / `÷ 0.95` instead of Table 5.3.2.2's three bands.
- Unit-water table had the 75–100 and 150–175 columns too low (e.g. 19 mm: 190/197/209 instead of 190/205/216) — the middle column was interpolated rather than read.
- Air-entrained water column taken for the wrong exposure.
- No rounded-aggregate water reduction and no entrapped-air term in the absolute volume.
- Still open after that pass: the SD branch's `1.96·s`, and the مبحث ۹ durability limits (پیوست پ۱: max w/c, min cement, min f'c, air requirement) — audit those against the Iranian code text itself before calling the screen verified.

## Audit checklist
1. Fetch the standard's own text (the ACI 211.1 PDF extracts cleanly from a university mirror) — not a blog table, not memory.
2. Inventory every constant in the engine and diff each against the standard, one table at a time.
3. Round-trip one known cell per table through the unit conversion.
4. Read the table footnotes and apply them as rules (rounded aggregate, water reducers, exposure basis).
5. Recompute one worked example per branch by hand, and cross-check against the standard's own chapter-7 example.
6. Report a defect list with the clause for each fix; leave formulas you did not audit as named open items instead of silently rewriting them.
