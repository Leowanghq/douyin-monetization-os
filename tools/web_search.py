"""
Web search via Bing — free, no API key required.
Scrapes Bing's HTML search results directly.
"""

import re
import ssl
import urllib.request
import urllib.parse
from html import unescape

from agent.tools import BaseTool


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    return text.strip()


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information via Bing. Returns titles, URLs, and snippets."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query string. Be specific and include relevant keywords.",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results to return (default 5, max 10).",
        },
    }

    def execute(self, query: str, max_results: int = 5) -> str:
        max_results = min(max_results, 10)

        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.bing.com/search?q={encoded_query}&setlang=en"

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )

            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")

        except Exception as e:
            return f"Search failed: {e}. Try a different query or check your network connection."

        # Parse Bing's search results from HTML
        results = self._parse_bing_results(html, max_results)

        if not results:
            return f"No results found for '{query}'. Try rephrasing your query."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. **{r['title']}**\n   URL: {r['url']}\n   {r['snippet'][:300]}")
        return "\n\n".join(lines)

    def _parse_bing_results(self, html: str, max_results: int) -> list[dict]:
        """Extract search results from Bing HTML."""
        results = []

        # Bing puts main results in <li class="b_algo"> blocks
        # Try to find result blocks
        blocks = re.findall(
            r'<li class="b_algo"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )

        for block in blocks:
            if len(results) >= max_results:
                break

            # Extract title and URL from <h2><a href="...">title</a></h2>
            title_match = re.search(
                r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                block,
                re.DOTALL,
            )
            if not title_match:
                continue

            url = title_match.group(1)
            title = _clean_html(title_match.group(2))

            # Skip non-result URLs
            if "bing.com" in url or not title:
                continue

            # Extract snippet
            snippet_match = re.search(
                r'<p[^>]*>(.*?)</p>',
                block,
                re.DOTALL,
            )
            snippet = _clean_html(snippet_match.group(1)) if snippet_match else ""

            results.append({"title": title, "url": url, "snippet": snippet})

        # Fallback: simpler pattern for older Bing layouts
        if not results:
            alt_blocks = re.findall(
                r'<h2><a\s+href="(https?://[^"]+)"[^>]*>(.*?)</a></h2>',
                html,
                re.DOTALL,
            )
            for url, raw_title in alt_blocks[:max_results]:
                title = _clean_html(raw_title)
                if "bing.com" not in url and title:
                    results.append({"title": title, "url": url, "snippet": ""})

        return results
