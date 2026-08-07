from __future__ import annotations

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


async def search_web(query: str, max_results: int = 5) -> list[dict]:
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title") or "",
                        "url": r.get("href") or "",
                        "snippet": r.get("body") or "",
                    }
                )
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]
    return results


async def fetch_page_text(url: str, max_chars: int = 3500) -> str:
    if not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "PairesResearchBot/0.2 (+demo)"},
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "footer", "noscript", "header"]):
                tag.decompose()
            text = " ".join(soup.get_text(separator=" ").split())
            return text[:max_chars]
    except Exception:
        return ""


async def gather_online_signals(
    investor_name: str,
    firm: str,
    sector: str | None = None,
) -> dict:
    """
    Search places that actually matter for investor research:
    - firm + partner identity
    - recent investments / announcements
    - sector thesis / market movement
    """
    queries = [
        f'"{firm}" (venture OR "venture capital" OR VC OR partner)',
        f'"{investor_name}" "{firm}"',
        f'"{firm}" (invested OR investment OR portfolio OR led OR participated)',
    ]
    if sector:
        queries.append(f'"{firm}" ({sector} OR semiconductor OR "AI infrastructure" OR fintech)')
        queries.append(f'{sector} venture funding thesis 2024 OR 2025 OR 2026')

    all_hits: list[dict] = []
    seen: set[str] = set()

    for q in queries:
        for hit in await search_web(q, max_results=4):
            url = (hit.get("url") or "").strip()
            if not url or url in seen:
                continue
            # Skip pure noise domains when possible
            low = url.lower()
            if any(x in low for x in ("pinterest.", "facebook.com/login", "linkedin.com/login")):
                continue
            seen.add(url)
            hit["query"] = q
            all_hits.append(hit)
            if len(all_hits) >= 10:
                break
        if len(all_hits) >= 10:
            break

    deepened = []
    for hit in all_hits[:3]:
        page_text = await fetch_page_text(hit["url"])
        deepened.append({**hit, "page_excerpt": page_text[:1200] if page_text else ""})

    return {
        "queries": queries,
        "hits": all_hits,
        "deepened": deepened,
    }


def format_signals_for_prompt(signals: dict) -> str:
    lines = ["=== LIVE WEB SIGNALS (external) ==="]
    lines.append("Queries run:")
    for q in signals.get("queries", []):
        lines.append(f"  - {q}")
    lines.append("")
    lines.append("Search hits:")
    hits = signals.get("hits") or []
    if not hits:
        lines.append("  (no web hits returned)")
    for i, hit in enumerate(hits[:8], 1):
        lines.append(f"{i}. {hit.get('title', '')}")
        lines.append(f"   URL: {hit.get('url', '')}")
        lines.append(f"   Snippet: {hit.get('snippet', '')}")
    for d in signals.get("deepened", []):
        if d.get("page_excerpt"):
            lines.append(f"\nPage excerpt ({d.get('url', '')}):")
            lines.append(d["page_excerpt"][:900])
    return "\n".join(lines)