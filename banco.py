import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from cachorro import Cachorro


class Banco:
    def __init__(self, caminho):
        self.caminho = caminho
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS cachorro (id INTEGER PRIMARY KEY CHECK(id=1), dados TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cuidadores (nome TEXT PRIMARY KEY, pontos INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, mensagem TEXT, instante REAL);
                CREATE TABLE IF NOT EXISTS cuidadores_v2 (identidade TEXT PRIMARY KEY, nome TEXT NOT NULL, origem TEXT NOT NULL, pontos INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS recebidos (chave TEXT PRIMARY KEY, instante REAL NOT NULL);
            ''')
            # Migração aditiva: preserva o ranking e o histórico das fases anteriores.
            db.execute("INSERT OR IGNORE INTO cuidadores_v2 SELECT 'sim:' || nome, nome, 'simulador', pontos FROM cuidadores")
            colunas = {row[1] for row in db.execute('PRAGMA table_info(eventos)')}
            if 'origem' not in colunas:
                db.execute("ALTER TABLE eventos ADD COLUMN origem TEXT NOT NULL DEFAULT 'simulador'")

    @contextmanager
    def conectar(self):
        db = sqlite3.connect(self.caminho, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def carregar(self):
        with self.conectar() as db:
            row = db.execute('SELECT dados FROM cachorro WHERE id=1').fetchone()
        return Cachorro(**json.loads(row[0])) if row else Cachorro()

    def salvar(self, rex, evento=None, *, identidade=None, origem='simulador', recebido=None):
        # Estado, crédito do cuidador e evento entram na mesma transação.
        with self.conectar() as db:
            if recebido:
                if not db.execute('INSERT OR IGNORE INTO recebidos VALUES (?, ?)', (recebido, evento[2])).rowcount:
                    return False
            db.execute('INSERT OR REPLACE INTO cachorro VALUES (1, ?)', (json.dumps(asdict(rex)),))
            if evento:
                nome, mensagem, instante = evento
                chave = identidade or 'sim:' + nome
                db.execute('INSERT INTO cuidadores_v2 VALUES (?, ?, ?, 10) ON CONFLICT(identidade) DO UPDATE SET pontos=pontos+10, nome=excluded.nome', (chave, nome, origem))
                db.execute('INSERT INTO eventos(nome, mensagem, instante, origem) VALUES (?, ?, ?, ?)', (*evento, origem))
                db.execute('DELETE FROM eventos WHERE id NOT IN (SELECT id FROM eventos ORDER BY id DESC LIMIT 100)')
                db.execute('DELETE FROM recebidos WHERE chave NOT IN (SELECT chave FROM recebidos ORDER BY instante DESC LIMIT 10000)')
        return True

    def comunidade(self):
        with self.conectar() as db:
            ranking = [dict(nome=n, pontos=p, origem=o) for n, p, o in db.execute('SELECT nome, pontos, origem FROM cuidadores_v2 ORDER BY pontos DESC, nome, identidade LIMIT 5')]
            eventos = [dict(id=i, nome=n, mensagem=m, instante=t, origem=o) for i, n, m, t, o in db.execute('SELECT id, nome, mensagem, instante, origem FROM eventos ORDER BY id DESC LIMIT 100')]
        return dict(ranking=ranking, eventos=eventos)
