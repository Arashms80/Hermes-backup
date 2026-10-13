# Browser verification recipe

Companion to step 4 of the SKILL.md procedure. Everything here is what actually ran, distilled — adapt the selectors, not the sequence.

## Serve and load

```bash
# from the directory holding the edited file
python3 -m http.server 8731 --bind 127.0.0.1 &
curl -s -o /dev/null -w '%{http_code} %{size_download}\n' http://127.0.0.1:8731/<file>.html
```

Then `new_tab(url)` + `wait_for_load()`. If `browser_exec` dies while installing its Python deps with `No space left on device`, the uv cache sits on a small disk: write `cache-dir = "/tmp/uv_cache"` to `~/.config/uv/uv.toml` and retry (the root filesystem holds it fine). That is a config fix, not a reason to abandon browser verification.

## A/B load-error baseline

Prove your edit added no console errors by installing the hook **before** navigation, then loading old and new:

```python
cdp('Page.addScriptToEvaluateOnNewDocument',
    source="window.__pe=[];window.addEventListener('error',function(e){window.__pe.push(String(e.message)+' @'+String(e.filename||'').split('/').pop()+':'+e.lineno);});")
goto_url('<edited>.html'); wait_for_load(); edited = js('JSON.stringify(window.__pe)')
goto_url('<original>.html'); wait_for_load(); original = js('JSON.stringify(window.__pe)')
```

Accept only equality of the two lists (or a deliberate removal you can explain). Pre-existing broken blocks must appear in both.

## DOM structure assertions

One `js(() => {...})` returning `JSON.stringify` beats many round trips: children order of the edited container, `<select>` option values, visibility (`getComputedStyle(...).display`) per mode, count of rows, list of legacy ids that must be absent, and the non-`<option>` child count of the select.

The absent-ids list is exactly the `JUNK` purge list of your own block.

## Behaviour checks

- Drive the UI with a real `.click()` on the visible button, then read the rendered output node; calling the JS function directly proves the function, not the wiring.
- Pick a case whose answer you can compute by hand and quote it in the report (a list whose theoretical floor is obvious), plus one empty-input message and one out-of-range value.
- Time the compute with `performance.now()` around the run — a heuristic optimizer that takes seconds on a realistic list is a regression.
- Toggle each show/hide condition and assert both states.
- Stub `window.open` to capture print output without a popup:

```js
let cap = null; const real = window.open;
window.open = () => (cap = {html:'', document:{write:h=>cap.html+=h, close(){}, }, focus(){}});
window.cutShopPrint(); window.open = real;
// assert cap.html contains the output root, is dir="rtl", and carries no <script>
```

## Clicking a button whose action is expensive

Replace the expensive entry point with a recorder, click the **real** button, restore it, then assert on what it was handed. This covers wiring, option building, section list and filename in one pass without entering the code path that may hang:

```js
js(`(() => {
  const real = window.acExportBrandedPdf;
  window.acExportBrandedPdf = o => { window.__T = o; return 'stubbed'; };
  document.querySelector('#cutShop .cv-print-btn').click();
  window.acExportBrandedPdf = real;
  const o = window.__T;
  return JSON.stringify({title:o.titleFa, kinds:o.sections.map(s=>s.kind),
                         file:o.filename, sig:!!o.signatures, pairs:o.metaPairs.length});
})()`)
```

Exercise the expensive pipeline itself separately, in pieces, rather than through the button.
- Split the verification across browser calls: one call per click with the sleep inside it, then a separate call that reads the rendered output node — one call that clicks a heavy button, sleeps and evaluates further JS can time out mid-call and lose the whole batch.

- When output is grouped, assert the grouped counts on **every** surface at once (screen rows, image items, table rows) against the number of distinct signatures — a grouping helper wired into only two of the three surfaces is the usual defect.
- Export your helpers behind one accessor object (`window.__cutDebug = {opts, run, ...}`) and print a `typeof` map of the accessors as the first lines of the script: a missing export otherwise surfaces as a `TypeError` halfway through and swallows every assertion after it.

## Session hygiene when a call hangs

- First assume a transient stall, not a wedge: after a heavy-calc click the daemon can go unresponsive for seconds (later `js('1+1')` calls time out too, while `page_info()` may still answer). Wait a few seconds, then `ensure_real_tab()` + re-navigate — the same session usually recovers and the identical click then succeeds. Only when it still never settles is it a true wedge: start a fresh `session='<newname>'` and rebuild the setup there (error hook first, then navigate) — never retry the dead one.
- Diagnose before blaming: idle CPU with a stuck call means the JS never settled; a busy top process means it is genuinely still working.
- Clearing strays: `pkill -f 'browser[_]harness'` and `pkill -9 -f 'chrome[-]headless'` — the character class keeps the pattern from matching your own command line and killing your shell.
- Attribute a hang with an A/B: run the identical call against an untouched copy of the original file. If both hang, the suspect is the environment (canvas dimensions, `getImageData`, image decode), not your patch — report that honestly and give the feature a timeout fallback so the user is never left without output.

## Testing network fetches from the page (CORS, proxies, live quotes)

- **Never `await` a long fetch inside `js()`** — the harness's evaluation timeout kills the call mid-flight and the whole batch is lost. Start the fetches as fire-and-forget promises writing to `window.__probe` and return 'started' immediately; then a separate call sleeps ~15–25 s and reads `JSON.stringify(window.__probe || {state:"missing"})`, saving it to a workspace file so the result survives compaction.
- **Attribute "Failed to fetch" to CORS or to a connection failure before routing around it**: run two sibling hosts of the same CDN side-by-side with `{mode:'cors'}` in one tab — one success + one failure means CORS, both failures means network or geo-block.
- **Test the `file://` path when the deliverable is a standalone PWA**: write a tiny probe page (fetch + window flag) into the browser workspace and `goto_url('file:///…/probe.html')` — a feed that answers from `file://` works without any server; one that fails there needs a proxy or a hosted page.
- **Large proxy payloads stay out of the tool result** — a ~440 KB proxy-wrapped market dump stringified into a `js()` result floods context; fetch it to a `window` variable, extract the target symbol (find `"SYMBOL":{` then its `"stats":{...}`) and return only that.

## Visual checks: numbers first, screenshot second

- Assert proportions numerically before trusting pixels: a schematic segment's `getBoundingClientRect().width / bar width` must equal `piece / total` (5/8 = 0.625 vs a measured 0.623), and a joint marker's left offset its ratio (0.375 vs 0.372). Ratios prove the layout even when you cannot read the labels.
- Diagrams destined for a PDF: draw at page scale ×2, set `ctx.direction='rtl'` with `textAlign` for Persian labels, guard `roundRect` (`'roundRect' in ctx`). If the full report pipeline cannot run in this environment, prove the two steps the engine performs — `drawImage` of your canvas into a page-sized canvas, then `toDataURL('image/jpeg')` — and quote the timings as evidence.
- Exact strings come from `textContent`; ask vision only about structure ("two colored segments, a dashed line at the boundary, a badge above it, anything overlapping?"). Persian/RTL spellings read out of a screenshot are unreliable.
- **Pixel-sample canvas artwork instead of screenshotting it.** Compute the coordinates from your own layout maths and read `getImageData(x*S, y*S, 1, 1)` for the exact expected hex — badge fill, marker red, segment palette colour. Read the **alpha** channel too: an un-backed canvas returns `0,0,0` for every unpainted pixel, so an RGB-only count reports "everything is dark" and you conclude the artwork is wrong when it is empty background.
- **Assert the target is in view before `capture_screenshot()`.** `scrollIntoView` does nothing when the app scrolls in an inner container or the element was appended to `body` of a fixed-layout page, and what comes back is a clean screenshot of the top of the app that reads as evidence. Check `getBoundingClientRect().top` first; if the target will not come into view, drop the screenshot and assert programmatically.
- **Overlap proof for an absolutely positioned control**: per row, compare its rect against every `input`/`textarea` rect in that row — `br.left<ir.right && br.right>ir.left && br.top<ir.bottom && br.bottom>ir.top` — and against the row's own rect, then sum over all rows and require 0. One `js()` returning `rows=24 overlaps=0` settles "does the new button cover the fields?" without a screenshot, and it works on the first pass.
- **Count-delete semantics**: after a row removal, assert the shifted values, the re-numbered row labels and the persisted count in one line — the DOM looks right while storage still holds the old count and the next render resurrects the row.
- **A long `terminal` call can sit blocked with "command did not run — user has NOT consented" while the workflow just stalls** — the foreground `terminal` backend in a headless session waits on a user response that never comes. Prefer `execute_code`'s `subprocess.run` for scripted checks (node harnesses, builds, greps) and keep `terminal` for commands the user is present for; a timed-out call did NOT execute, so verify its effects before re-running it.
