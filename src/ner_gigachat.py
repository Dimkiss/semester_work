from typing import List, Dict
from langchain_gigachat.chat_models import GigaChat
from langchain.schema import HumanMessage
import json
import re

gigachat_api_key = 'MDE5YWFiNDctODQ2Yy03NzAzLWFkYzctNDMzZTAyMjNiN2ViOjQyNjhjOTI4LTMzMWUtNDk5ZS1hOTQ3LTdhZWIzODViYTlhYg=='

class GigaChatNER:
    def __init__(self, mode="zero"):
        self.mode = mode
        self.source = f"gigachat_{mode}"
        self.model = GigaChat(
            credentials=gigachat_api_key,
            verify_ssl_certs=False,
            model="GigaChat",
            temperature=0.1,
            timeout=120
        )

    def _build_prompt(self, text: str) -> str:
        if self.mode == "zero":
            return f"""
Ты — система распознавания именованных сущностей (NER) на русском языке. 
Твоя задача — найти в тексте все значимые сущности и классифицировать их по следующим категориям:

- PER — имя человека
- ORG — организация, компания, учреждение
- LOC — конкретное место (город, деревня, объект)
- GPE — геополитическая территория (страна, регион)
- DATE — дата, год, период времени
- TIME — время
- MONEY — денежные суммы
- PERCENT — проценты
- QUANTITY — количество или мера
- EVENT — событие
- WORK_OF_ART — произведение искусства
- PRODUCT — продукты, товары
- LAW — законы и нормативные акты
- LANGUAGE — языки
- NORP — национальности, религия, политические группы
- FAC — здания, сооружения, аэропорты
- MISC — прочие значимые объекты

Выводи результат строго в формате JSON: [{{"text": "...", "label": "..."}}]  
Если сущностей нет — верни пустой список [].

Текст для анализа: "{text}"
"""
        elif self.mode == "few":
            return f"""
Ты — система распознавания именованных сущностей (NER) на русском языке. 
Твоя задача — найти в тексте все значимые сущности и классифицировать их по следующим категориям:

- PER — имя человека
- ORG — организация, компания, учреждение
- LOC — конкретное место (город, деревня, объект)
- GPE — геополитическая территория (страна, регион)
- DATE — дата, год, период времени
- TIME — время
- MONEY — денежные суммы
- PERCENT — проценты
- QUANTITY — количество или мера
- EVENT — событие
- WORK_OF_ART — произведение искусства
- PRODUCT — продукты, товары
- LAW — законы и нормативные акты
- LANGUAGE — языки
- NORP — национальности, религия, политические группы
- FAC — здания, сооружения, аэропорты
- MISC — прочие значимые объекты

Примеры:

"Иван Иванов" -> [{{"text": "Иван Иванов", "label": "PER"}}]  
"Первый канал" -> [{{"text": "Первый канал", "label": "ORG"}}]  
"Москва" -> [{{"text": "Москва", "label": "LOC"}}]  
"Россия" -> [{{"text": "Россия", "label": "GPE"}}]  
"12 декабря 2020" -> [{{"text": "12 декабря 2020", "label": "DATE"}}]  
"15:30" -> [{{"text": "15:30", "label": "TIME"}}]  
"100 млн ₽" -> [{{"text": "100 млн ₽", "label": "MONEY"}}]  
"10%" -> [{{"text": "10%", "label": "PERCENT"}}]  
"5 кг" -> [{{"text": "5 кг", "label": "QUANTITY"}}]
"14 215" -> [{{"text":"14 215","label":"QUANTITY"}}]  
"Чемпионат мира по футболу 2018" -> [{{"text": "Чемпионат мира по футболу 2018", "label": "EVENT"}}]  
"Война и мир" -> [{{"text": "Война и мир", "label": "WORK_OF_ART"}}]  
"iPhone 14" -> [{{"text": "iPhone 14", "label": "PRODUCT"}}]  
"Федеральный закон №123-ФЗ" -> [{{"text": "Федеральный закон №123-ФЗ", "label": "LAW"}}]  
"русский" -> [{{"text": "русский", "label": "LANGUAGE"}}]  
"русские" -> [{{"text": "русские", "label": "NORP"}}]  
"МГУ" -> [{{"text": "МГУ", "label": "FAC"}}]  
"ВГТРК" -> [{{"text": "ВГТРК", "label": "MISC"}}]

Выведи результат строго в формате JSON: [{{"text": "...", "label": "..."}}]  
Если сущностей нет — верни пустой список [].

Текст для анализа: "{text}"
"""
    def extract_entities(self, text: str) -> List[Dict]:
        prompt = self._build_prompt(text)
        response = self.model.invoke([HumanMessage(content=prompt)])

        try:
            data = json.loads(response.content)
        except Exception:
            return []

        if not isinstance(data, list):
            return []

        entities = []
        for e in data:
            if isinstance(e, dict) and "text" in e and "label" in e:
                entities.append({
                    "text": e["text"],
                    "label": e["label"],
                    "source": f"gigachat_{self.mode}"
                })

        return entities