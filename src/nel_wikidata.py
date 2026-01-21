import re
import time
from typing import Dict, Optional, Tuple

import requests

CYR_RE = re.compile(r"[А-Яа-яЁё]")


def is_russian(text: str) -> bool:
    return bool(CYR_RE.search(text or ""))


class EntityLinker:
    def __init__(self, language: str = "ru", limit: int = 1, sleep_s: float = 0.05):
        self.language = language
        self.limit = limit
        self.sleep_s = sleep_s
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "NER-NEL-Semester-Work/1.0"})
        self.cache: Dict[Tuple[str, int], Optional[str]] = {}

    def search_wikidata(self, query: str) -> Optional[str]:
        q = (query or "").strip()
        if not q:
            return None

        key = (q.lower(), self.limit)
        if key in self.cache:
            return self.cache[key]

        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": q,
            "language": self.language,
            "format": "json",
            "limit": self.limit,
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
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
