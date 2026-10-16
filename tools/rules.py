"""Category and likelihood rules for the Python tools, read from the same file as the review page.

The rules file is skills/hsa-categorize/category_rules.json. The page and these functions give the same
answers for the same items (tools/test_rules.py checks that). The rules only suggest; they never set a status.
"""

import json
import re
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent.parent / "skills" / "hsa-categorize" / "category_rules.json"


def _rx(spec):
    return re.compile(spec["pattern"], re.I if "i" in spec.get("flags", "") else 0)


class Rules:
    def __init__(self, path=RULES_PATH):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.version = raw["version"]
        self.head = _rx(raw["title_head"])
        self.title_categories = [(_rx(r), r["icon"], r["name"]) for r in raw["title_categories"]]
        self.amazon_categories = [(_rx(r), r["icon"], r["name"]) for r in raw["amazon_categories"]]
        self.medical = _rx(raw["medical_words"])
        self.drug = _rx(raw["drug_words"])
        self.health = raw["health_category"]
        self.unlikely = raw["unlikely_categories"]

    def title_head(self, text):
        """The product type comes first in an Amazon title; the words after for/with/captures describe it."""
        return self.head.split(str(text))[0]

    def amazon_cat(self, path):
        joined = " > ".join(path)
        for rx, icon, name in self.amazon_categories:
            if rx.search(joined):
                return {"icon": icon, "name": name}
        return {"icon": "📦", "name": "Other", "unmapped": True}

    def cat_of(self, text, info=None):
        """Amazon's own category path wins over the title-word guess."""
        if info:
            found = self.amazon_cat(info["path"])
            where = "Other (Amazon: " if found.get("unmapped") else "Category: Amazon ("
            return {**found, "why": where + " › ".join(info["path"]) + ")", "amazon": True}
        head = self.title_head(text)
        for rx, icon, name in self.title_categories:
            m = rx.search(head)
            if m:
                return {"icon": icon, "name": name, "why": f'Category guessed from the word "{m.group(0).strip()}"'}
        return {"icon": "📦", "name": "Other", "why": "Category guessed: no matching word"}

    def likelihood(self, title, marked=False, info=None):
        """Suggested likelihood: Amazon badge, then medical category or words, then mixed categories."""
        if info and info.get("fsa") and not marked:
            return {"n": 4, "label": "Highly likely", "why": "Amazon's product page shows FSA or HSA eligible"}
        if marked:
            return {"n": 4, "label": "Highly likely", "why": "Amazon marks it FSA/HSA eligible"}
        cat = self.cat_of(title, info)
        if cat["name"] == self.health:
            return {"n": 3, "label": "Likely", "why": cat["why"]}
        drug = self.drug.search(title)
        if drug:
            return {"n": 3, "label": "Likely", "why": f'Drug ingredient "{drug.group(0)}" in the name'}
        word = self.medical.search(self.title_head(title))
        if word:
            return {"n": 3, "label": "Likely", "why": f'Medical word "{word.group(0)}" in the name'}
        if cat["name"] in self.unlikely:
            return {"n": 2, "label": "Unlikely", "why": "Mixed category: " + cat["name"]}
        return {"n": 1, "label": "Highly unlikely", "why": "Category: " + cat["name"]}
