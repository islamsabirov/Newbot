from app.locales.uz import TEXTS as UZ
from app.locales.ru import TEXTS as RU
from app.locales.en import TEXTS as EN

ALL = {"uz": UZ, "ru": RU, "en": EN}

def t(key: str, lang: str = "uz") -> str:
    return ALL.get(lang, UZ).get(key) or UZ.get(key) or key
