---
name: rtl-typesetting
version: 1.0.0
author: Hermes Agent
license: MIT
description: "Use when typesetting RTL documents. XeLaTeX workflow."
metadata:
  hermes:
    tags: [rtl, persian, arabic, xelatex, xepersian, pdf, typesetting]
    related_skills: [pdf, docx]
---

# RTL Typesetting

Create or visually restyle right-to-left (Persian/Arabic) documents,
especially rebuilding a PDF to match a reference look via XeLaTeX +
xepersian without changing content values.

## When to Use

- Generate a Persian/Arabic report, invoice, or multi-page document.
- Restyle an existing RTL PDF to match a reference look without
  changing its content values.
- Debug XeLaTeX/xepersian compilation or font problems for RTL text.

## Procedure

1. **Freeze content first.** Extract both documents' text and
   independently verify numbers/formulas before touching visuals.
   A restyle changes styling only — never values. Exception: when
   the user explicitly directs a value change, recompute every
   derived number first and present the new figures for
   confirmation before editing — never silently propagate.
2. **Dump spans, not just text.** Extract per-page spans with
   font/size/color/bbox (pymupdf `get_text("dict")` or equivalent).
   RTL text extracts in *visual* order — reverse each span and
   NFKC-fold presentation forms to recover logical reading order.
3. **Dump vector geometry.** Collect drawing rects/lines (table
   rules, header bands, boxes) and fills (background colors).
   Never guess layout from text positions alone.
4. **Render high-zoom crops** (4x) of ambiguous glyphs — spans
   with blank/placeholder chars need visual transcription,
   especially Latin/math tokens embedded in RTL lines
   (f'c, fy, Greek letters, subscripts).
5. **Smoke-test the toolchain first.** Compile a minimal source
   (article, A4 geometry, fontspec + xepersian, one equation, one
   table) and fix every error there before building the full
   document. Keep a copy of the last working source before each
   new compile attempt.
6. **Match the reference font exactly** (e.g. Noto Naskh Arabic for
   text, Computer Modern for math). Install the full TTF into
   `~/.local/share/fonts`, run `fc-cache`, and verify with
   `fc-list | grep -i <name>`.
7. **Build, compile, compare.** Build the full source, compile,
   and compare page crops against the reference before delivering.

## Pitfalls

- **Tectonic rejects variable fonts.** A variable TTF fails in
  xdvipdfmx with `Invalid TTC index` / `Invalid font: -1 (0)` —
  instantiate static weights first with fonttools
  (`instantiateVariableFont(f, {'wght': w})` for 400/700 at minimum)
  and install those; verify `fc-list` shows `style=Regular` and
  `style=Bold`, not multiple styles on one file.
- **Embedded PDF fonts are subsets** (~30KB) and useless for
   recompilation — they only prove the family name. Download the
   full font instead, and verify the download is a real font
   (first bytes `00 01 00 00` for TTF) — raw hosting URLs can
   silently return an HTML error page.
- **Package order matters:** load fontspec/xepersian *after*
   amsmath/xcolor/tabularx/array, or compilation fails.
- **Avoid fancyhdr with xepersian** — define a custom `ps@plain`
   footer instead; xepersian already handles RTL equation tags
   automatically.
- **Keep custom box environments simple around display math.**
  A `\fcolorbox`+`\parbox` environment opened with `\bgroup`
  across `equation*` blocks fails — use plain rules or a box
  package instead of hand-rolled grouping.
- **Never wrap `$...$` in `\lr{...}` — anywhere.** Math mode is
already LTR; the wrapper breaks bidi handling and fails with
`Missing } inserted`. Use bare `$...$` in body text, and keep
section titles as plain text with no math at all.
- **Scanned/image-only pages have no text layer.** Export them as
  high-DPI PNGs and transcribe visually; never report empty
  extraction as "no content".
- **Latin digits inside `\lr{...}`, never Persian digits.** Persian
  digits (U+06F0–06F9) inside `\lr` resolve against the Latin font
  and warn `Missing character` — convert them to 0-9 there.
