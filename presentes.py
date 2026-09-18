"""
Regras dos presentes TikTok do Rex Live.
Cada presente possui um efeito no jogo.
"""


PRESENTES = {
    "Rose": {
        "nome": "Rosa 🌹",
        "efeito": "saciedade",
        "valor": 5,
    },

    "Heart Me": {
        "nome": "Coração ❤️",
        "efeito": "felicidade",
        "valor": 10,
    },

    "Coffee": {
        "nome": "Café ☕",
        "efeito": "energia",
        "valor": 20,
    },

    "Lion": {
        "nome": "Leão 🦁",
        "efeito": "especial",
        "valor": 1,
    },
}


def normalizar_presente(nome):
    """
    Normaliza o nome recebido do TikTok.
    """
    if not nome:
        return ""

    return str(nome).strip().lower()


def buscar_presente(nome):
    """
    Procura um presente conhecido.
    """

    nome = normalizar_presente(nome)

    for chave, presente in PRESENTES.items():
        if chave.lower() == nome:
            return presente

    return None


def aplicar_efeito_presente(nome, quantidade=1):
    """
    Retorna o efeito do presente.
    """

    if type(quantidade) is not int or not 1 <= quantidade <= 10000:
        raise ValueError('Quantidade de presentes inválida.')
    presente = buscar_presente(nome)

    if not presente:
        return None

    return {
        "nome": presente["nome"],
        "efeito": presente["efeito"],
        "valor": presente["valor"] * quantidade,
    }

def aplicar_no_rex(rex, presente):
    """Aplica apenas atributos; não concede XP, acorda ou ativa emoções."""
    atributo = {'saciedade': 'fome', 'felicidade': 'felicidade', 'energia': 'energia'}.get(presente['efeito'])
    if atributo:
        setattr(rex, atributo, min(100, max(0, getattr(rex, atributo) + presente['valor'])))
    # Leão é um evento especial registrado, sem evolução ou atributo inventado.
