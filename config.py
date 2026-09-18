from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'dados' / 'rex.db'
HOST = '127.0.0.1'
PORT = 8765
TICK_SECONDS = 2
XP_PER_LEVEL = 100
TIKTOK_PERFIL = 'terra.updatess'
TIKTOK_COOLDOWN = 5

# Limita efeitos; todos os presentes válidos continuam registrados e pontuados.
TIKTOK_PRESENTE_COOLDOWN = 1
