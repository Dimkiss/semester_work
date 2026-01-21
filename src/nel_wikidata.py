import time
from typing import Dict, Optional, Tuple

import httpx


class WikidataNEL:
    def __init__(self, language: str = "ru", sleep_s: float = 0.05, timeout_s: float = 10.0):
        self.language = language
        self.sleep_s = sleep_s
        self.client = httpx.Client(
            headers={"User-Agent": "NER-NEL-Semester-Work/1.0"},
            timeout=timeout_s,
            follow_redirects=True,
        )
        self.cache: Dict[Tuple[str, int], Optional[str]] = {}

    def search_wikidata(self, query: str, limit: int = 5) -> Optional[str]:
        q = (query or "").strip()
        if not q:
            return None

        key = (q.lower(), limit)
        if key in self.cache:
            return self.cache[key]

        params = {
            "action": "wbsearchentities",
            "search": q,
            "language": self.language,
            "format": "json",
            "limit": limit,
        }

        try:
            resp = self.client.get("https://www.wikidata.org/w/api.php", params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("search", [])
            uri = results[0]["concepturi"] if results else None
            self.cache[key] = uri
            time.sleep(self.sleep_s)
            return uri
        except Exception:
            self.cache[key] = None
            return None

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
