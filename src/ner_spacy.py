# ner_spacy.py
from typing import List, Dict
import spacy
import os
import re

NUM_RE = re.compile(r"^\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d+)?$|^\d+(?:[.,]\d+)?$")

class SpacyNER:
    def __init__(self, model_name: str = "ru_core_news_lg"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            print(f"[INFO] Модель {model_name} не найдена. Скачиваем...")
            os.system(f"python -m spacy download {model_name}")
            self.nlp = spacy.load(model_name)

    def extract_entities(self, text: str) -> List[Dict]:
        """
        Извлекает сущности из текста одной ячейки.
        + дополнительное правило: если ячейка — число (с пробелами как в '14 215'),
          добавляем сущность QUANTITY.
        """
        doc = self.nlp(text)

        entities: List[Dict] = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "source": "spacy"
            })

        # ---- правило для QUANTITY ----
        t = text.strip()
        if NUM_RE.match(t):
            # не дублируем, если spaCy уже что-то нашёл ровно на всю ячейку
            already = any(e["text"].strip() == t for e in entities)
            if not already:
                entities.append({
                    "text": t,
                    "label": "QUANTITY",
                    "source": "rule"
                })

        return entities
