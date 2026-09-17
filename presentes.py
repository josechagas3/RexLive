"""Mapeamento de presentes TikTok → efeitos no Cachorro."""
PRESENTES = {
    'rosa': {'felicidade': 10},
    'coracao': {'felicidade': 15, 'vida': 5},
    'cafe': {'energia': 10},
    'leao': {'energia': 20, 'felicidade': 15, 'vida': 10},
}


def efeitos_presente(nome_presente: str) -> dict:
    return PRESENTES.get(nome_presente.lower(), {})