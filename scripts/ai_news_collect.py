#!/usr/bin/env python3
"""AI NEWS COLLECTOR — pre-run data collection for the daily AI briefing cron job.

Stdlib only. Collects, in one pass:
  1. RSS/Atom feeds from AI labs, press and community (filtered to the window
     since the last successful run)
  2. New/trending open models from the Hugging Face API
  3. The live free-model catalogue from OpenRouter
  4. A static roster of providers that offer free model access, with the URL the
     agent should check for changes

Prints a compact raw digest to stdout; the cron agent turns it into a brief.
State (last successful window start) lives in STATE and only advances when no
source failed, so a failed source is never silently reported as "no news".

Usage:
  ai_news_collect.py                 # normal run
  ai_news_collect.py --lookback 30   # hours to cover when no state exists
  ai_news_collect.py --no-state      # read/write no state (dry run)
"""
from __future__ import annotations

import gzip
import html
import io
import json
import re
import ssl
import sys
import urllib.request
import zlib
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TEHRAN = ZoneInfo("Asia/Tehran")
STATE = Path("/data/.hermes/state/ai-news-brief/last_run.txt")
TIMEOUT = 15
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
CTX = ssl.create_default_context()

# name -> (url, category, max items kept)
FEEDS: dict[str, tuple[str, str, int]] = {
    # --- AI labs: new models, releases, research ---
    "OpenAI": ("https://openai.com/news/rss.xml", "labs", 6),
    "Google DeepMind": ("https://deepmind.google/blog/rss.xml", "labs", 6),
    "Hugging Face Blog": ("https://huggingface.co/blog/feed.xml", "labs", 6),
    "Google Research": ("https://research.google/blog/rss/", "labs", 4),
    "Microsoft Research": ("https://www.microsoft.com/en-us/research/feed/", "labs", 4),
    "NVIDIA Blog": ("https://blogs.nvidia.com/feed/", "labs", 4),
    "Mistral AI": ("https://mistral.ai/rss.xml", "labs", 4),
    "AI Business": ("https://aibusiness.com/rss.xml", "labs", 3),
    # --- press / analysis ---
    "TechCrunch AI": ("https://techcrunch.com/category/artificial-intelligence/feed/", "press", 8),
    "The Verge AI": ("https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "press", 6),
    "Ars Technica AI": ("https://arstechnica.com/ai/feed/", "press", 5),
    "Marktechpost": ("https://www.marktechpost.com/feed/", "press", 8),
    "Simon Willison": ("https://simonwillison.net/atom/everything/", "press", 4),
    # --- community / open weights ---
    "Reddit LocalLLaMA": ("https://www.reddit.com/r/LocalLLaMA/.rss", "community", 12),
}

# Providers that hand out free model access. The agent verifies changes with
# web_search / web_extract against these URLs.
FREE_PROVIDERS: list[tuple[str, str, str]] = [
    ("OpenRouter free models", "https://openrouter.ai/models?max_price=0", "live API in this digest"),
    ("Google AI Studio / Gemini API", "https://ai.google.dev/gemini-api/docs/pricing", "free tier limits"),
    ("Groq", "https://console.groq.com/docs/rate-limits", "free tier rate limits"),
    ("Cerebras Cloud", "https://inference-docs.cerebras.ai/support/pricing", "free tier"),
    ("Mistral La Plateforme", "https://docs.mistral.ai/deployment/laplateforme/tier/", "free tier"),
    ("Cloudflare Workers AI", "https://developers.cloudflare.com/workers-ai/platform/pricing/", "free daily neurons"),
    ("GitHub Models", "https://docs.github.com/en/github-models/about-github-models", "free per-request limits"),
    ("NVIDIA NIM / build.nvidia.com", "https://build.nvidia.com/", "free credits"),
    ("Hugging Face Inference Providers", "https://huggingface.co/docs/inference-providers/pricing", "monthly free credits"),
    ("Together AI", "https://www.together.ai/pricing", "free models"),
    ("Chutes", "https://chutes.ai/app", "free tier"),
    ("OpenAI / ChatGPT free tier", "https://openai.com/chatgpt/pricing/", "free tier model access"),
    ("Anthropic Claude free tier", "https://www.anthropic.com/pricing", "free tier model access"),
    ("xAI Grok", "https://x.ai/api", "free credits"),
    ("DeepSeek Platform", "https://api-docs.deepseek.com/quick_start/pricing", "free credits"),
    ("Qwen / Alibaba Model Studio", "https://www.alibabacloud.com/en/product/modelstudio", "free quota"),
    ("Z.ai / GLM", "https://z.ai/", "free tier"),
    ("Moonshot / Kimi", "https://platform.moonshot.ai/docs/pricing", "free tier"),
]

BENCH_SOURCES: list[tuple[str, str]] = [
    ("Artificial Analysis", "https://artificialanalysis.ai/leaderboards/models"),
    ("LMArena", "https://lmarena.ai/leaderboard"),
    ("SWE-bench", "https://www.swebench.com/"),
    ("Vals AI", "https://www.vals.ai/"),
    ("Open LLM Leaderboard", "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"),
    ("ARC Prize", "https://arcprize.org/leaderboard"),
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def fetch(url: str, timeout: int = TIMEOUT) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, "
                  "application/json, text/xml;q=0.9, */*;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as resp:
        raw = resp.read()
        enc = (resp.headers.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    elif "deflate" in enc:
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    return raw


def strip_tags(text: str) -> str:
    text = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", text or "", flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_date(value: str):
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=TEHRAN)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt is not None and dt.tzinfo is None:
            dt = dt.replace(tzinfo=TEHRAN)
        return dt
    except Exception:
        return None


def first(pattern: str, block: str, default: str = "") -> str:
    m = re.search(pattern, block, re.S | re.I)
    return m.group(1) if m else default


def parse_feed(raw: bytes) -> list[dict]:
    s = raw.decode("utf-8", "replace")
    blocks = re.findall(r"<entry[\s>].*?</entry>", s, re.S) or \
        re.findall(r"<item[\s>].*?</item>", s, re.S)
    items = []
    for b in blocks:
        items.append({
            "title": strip_tags(first(r"<title[^>]*>(.*?)</title>", b)),
            "link": strip_tags(first(r'<link[^>]*href="([^"]+)"', b) or first(r"<link>(.*?)</link>", b)),
            "date": first(r"<(?:updated|published|pubDate|dc:date)[^>]*>(.*?)</(?:updated|published|pubDate|dc:date)>", b),
            "summary": strip_tags(first(r"<(?:summary|description|content)[^>]*>(.*?)</(?:summary|description|content)>", b))[:220],
        })
    return items


def hf_models(query: str, limit: int = 60) -> list[dict]:
    raw = fetch(f"https://huggingface.co/api/models?{query}&limit={limit}")
    return json.loads(raw.decode("utf-8", "replace"))


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    args = sys.argv[1:]
    lookback_h = 30
    use_state = "--no-state" not in args
    if "--lookback" in args:
        try:
            lookback_h = int(args[args.index("--lookback") + 1])
        except (IndexError, ValueError):
            pass

    now = datetime.now(TEHRAN)
    cutoff = None
    if use_state and STATE.exists():
        try:
            cutoff = datetime.fromisoformat(STATE.read_text(encoding="utf-8").strip())
        except Exception:
            cutoff = None
    first_run = cutoff is None
    if first_run:
        cutoff = now - timedelta(hours=lookback_h)

    out: list[str] = [
        f"# AI NEWS RAW DIGEST — {now.strftime('%Y-%m-%d %H:%M')} Tehran",
        f"# window: published after {cutoff.strftime('%Y-%m-%d %H:%M')} Tehran"
        + (f" (first run: {lookback_h}h lookback)" if first_run else ""),
    ]
    failures: list[str] = []
    counts: dict[str, int] = {}

    # ---- 1. feeds ---------------------------------------------------------- #
    for name, (url, category, limit) in FEEDS.items():
        try:
            items = parse_feed(fetch(url))
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__} {str(exc)[:70]}")
            continue
        fresh = []
        for it in items:
            d = parse_date(it.get("date", ""))
            if d is None:
                continue
            d = d.astimezone(TEHRAN)
            if d >= cutoff:
                fresh.append((d, it))
        fresh.sort(key=lambda x: x[0], reverse=True)
        fresh = fresh[:limit]
        counts[name] = len(fresh)
        if not fresh:
            continue
        out.append(f"\n## [{category}] {name} ({len(fresh)})")
        for d, it in fresh:
            line = f"- {it['title']} | {d.strftime('%m-%d %H:%M')}"
            if it["link"]:
                line += f" | {it['link']}"
            out.append(line)
            if it["summary"] and category != "community":
                out.append(f"    {it['summary']}")

    # ---- 2. new open models (Hugging Face) --------------------------------- #
    try:
        newest = hf_models("sort=createdAt&direction=-1&filter=text-generation",
                           limit=100)
        notable = [m for m in newest
                   if (m.get("likes") or 0) >= 3
                   or (m.get("downloads") or 0) >= 1000
                   or (m.get("trendingScore") or 0) >= 20]
        trending = hf_models("sort=trendingScore&direction=-1", limit=20)
        out.append("\n## [open-models] Hugging Face — notable new / trending")
        if notable:
            out.append("- NEW text-generation repos with early traction:")
            for m in notable[:12]:
                out.append(f"    {m.get('id')} | likes={m.get('likes')} "
                           f"dl={m.get('downloads')} | {m.get('lastModified','')[:10]}"
                           f" | https://huggingface.co/{m.get('id')}")
        else:
            out.append("- no new text-generation repo crossed the traction threshold")
        out.append("- trending by score:")
        for m in trending[:12]:
            out.append(f"    {m.get('id')} | score={m.get('trendingScore')} "
                       f"likes={m.get('likes')} | https://huggingface.co/{m.get('id')}")
        counts["HuggingFace API"] = len(notable)
    except Exception as exc:
        failures.append(f"HuggingFace API: {type(exc).__name__} {str(exc)[:70]}")

    # ---- 3. free-model catalogue (OpenRouter) ------------------------------ #
    try:
        data = json.loads(fetch("https://openrouter.ai/api/v1/models", timeout=20)
                          .decode("utf-8", "replace"))
        free = []
        for m in data.get("data") or []:
            p = m.get("pricing") or {}
            try:
                if float(p.get("prompt", 1) or 1) == 0 and float(p.get("completion", 1) or 1) == 0:
                    free.append(m)
            except (TypeError, ValueError):
                continue
        free.sort(key=lambda m: m.get("created") or 0, reverse=True)
        newly = [m for m in free if (m.get("created") or 0) >= cutoff.timestamp()]
        out.append("\n## [free-models] OpenRouter free catalogue (live API)")
        out.append(f"- free models now listed: {len(free)}")
        out.append(f"- added inside this window: {len(newly)}")
        for m in newly:
            ctx = m.get("context_length")
            ctx = f"{ctx // 1000}K" if isinstance(ctx, int) else "?"
            out.append(f"    NEW: {m.get('name')} | {m.get('id')} | {ctx} ctx")
        out.append("- current free list (id | name | ctx):")
        for m in free:
            ctx = m.get("context_length")
            ctx = f"{ctx // 1000}K" if isinstance(ctx, int) else "?"
            exp = f" | EXPIRES {str(m.get('expiration_date'))[:10]}" if m.get("expiration_date") else ""
            out.append(f"    {m.get('id')} | {m.get('name')} | {ctx}{exp}")

        try:
            chutes = json.loads(fetch("https://llm.chutes.ai/v1/models")
                                .decode("utf-8", "replace"))
            out.append("- Chutes catalogue (subset, free/cheap tier):")
            for m in (chutes.get("data") or [])[:15]:
                out.append(f"    {m.get('id')}")
        except Exception as exc:
            failures.append(f"Chutes API: {type(exc).__name__} {str(exc)[:60]}")
        try:
            nim = json.loads(fetch("https://integrate.api.nvidia.com/v1/models")
                             .decode("utf-8", "replace"))
            ids = [m.get("id") for m in (nim.get("data") or [])]
            out.append(f"- NVIDIA NIM catalogue size: {len(ids)} models "
                       f"(free credits at build.nvidia.com)")
        except Exception as exc:
            failures.append(f"NVIDIA NIM API: {type(exc).__name__} {str(exc)[:60]}")
        counts["Free-model APIs"] = len(newly)
    except Exception as exc:
        failures.append(f"OpenRouter API: {type(exc).__name__} {str(exc)[:70]}")

    # ---- 4. reference rosters for the agent -------------------------------- #
    out.append("\n## [free-providers] roster to verify with web_search (check each for changes)")
    for label, url, note in FREE_PROVIDERS:
        out.append(f"- {label} | {url} | {note}")

    out.append("\n## [benchmarks] sources to check with web_search for NEW results this window")
    for label, url in BENCH_SOURCES:
        out.append(f"- {label} | {url}")

    # ---- 5. health --------------------------------------------------------- #
    out.append("\n## [source-health]")
    if failures:
        out.append("- !! FAILED SOURCES (coverage gap — never report as 'no news'):")
        for f in failures:
            out.append(f"    {f}")
    else:
        out.append("- all sources fetched OK")
    out.append("- new items per source: " + ", ".join(
        f"{k}={v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))

    print("\n".join(out))

    if use_state:
        if failures:
            print(f"# state NOT advanced ({len(failures)} failure(s)); next run re-covers "
                  f"this window", file=sys.stderr)
        else:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(now.isoformat(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
