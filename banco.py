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
                CREATE TABLE IF NOT EXISTS presentes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT NOT NULL UNIQUE,
                    identidade TEXT NOT NULL, usuario TEXT NOT NULL, presente TEXT NOT NULL,
                    quantidade INTEGER NOT NULL, valor INTEGER NOT NULL, efeito TEXT NOT NULL,
                    efeitos TEXT NOT NULL, pontos INTEGER NOT NULL, data REAL NOT NULL,
                    efeito_aplicado INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS presentes_identidade ON presentes(identidade);
            ''')
            # Migração aditiva: preserva o ranking e o histórico das fases anteriores.
            db.execute("INSERT OR IGNORE INTO cuidadores_v2 SELECT 'sim:' || nome, nome, 'simulador', pontos FROM cuidadores")
            colunas = {row[1] for row in db.execute('PRAGMA table_info(eventos)')}
            if 'origem' not in colunas:
                db.execute("ALTER TABLE eventos ADD COLUMN origem TEXT NOT NULL DEFAULT 'simulador'")
            if 'comando' not in colunas:
                db.execute("ALTER TABLE eventos ADD COLUMN comando TEXT NOT NULL DEFAULT ''")
            if 'efeitos' not in colunas:
                db.execute("ALTER TABLE eventos ADD COLUMN efeitos TEXT NOT NULL DEFAULT '{}'")

            if 'presente' not in colunas:
                db.execute("ALTER TABLE eventos ADD COLUMN presente TEXT NOT NULL DEFAULT '{}'")

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

    def salvar(self, rex, evento=None, *, identidade=None, origem='simulador', recebido=None, comando='', efeitos=None):
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
                db.execute('INSERT INTO eventos(nome, mensagem, instante, origem, comando, efeitos) VALUES (?, ?, ?, ?, ?, ?)', (*evento, origem, comando, json.dumps(efeitos or {})))
                db.execute('DELETE FROM eventos WHERE id NOT IN (SELECT id FROM eventos ORDER BY id DESC LIMIT 100)')
                db.execute('DELETE FROM recebidos WHERE chave NOT IN (SELECT chave FROM recebidos ORDER BY instante DESC LIMIT 10000)')
        return True

    def comunidade(self):
        with self.conectar() as db:
            ranking = [dict(nome=n, pontos=p, origem=o) for n, p, o in db.execute('SELECT nome, pontos, origem FROM cuidadores_v2 ORDER BY pontos DESC, nome, identidade LIMIT 5')]
            eventos = [dict(id=i, nome=n, mensagem=m, instante=t, origem=o, comando=c, efeitos=json.loads(e)) for i, n, m, t, o, c, e in db.execute('SELECT id, nome, mensagem, instante, origem, comando, efeitos FROM eventos ORDER BY id DESC LIMIT 100')]
            # Campos antigos permanecem compatíveis: ranking continua sendo de comentários.
            presentes = [dict(id=i, nome=n, presente=p, quantidade=q, valor=v, efeito=e,
                              efeitos=json.loads(ef), pontos=pt, instante=t, efeito_aplicado=bool(a))
                         for i,n,p,q,v,e,ef,pt,t,a in db.execute(
                             'SELECT id,usuario,presente,quantidade,valor,efeito,efeitos,pontos,data,efeito_aplicado FROM presentes ORDER BY id DESC LIMIT 100')]
            ranking_presentes = [dict(nome=n, pontos=p, origem='tiktok') for n,p in db.execute('''
                SELECT (SELECT usuario FROM presentes latest WHERE latest.identidade=p.identidade ORDER BY id DESC LIMIT 1), SUM(pontos)
                FROM presentes p GROUP BY identidade ORDER BY SUM(pontos) DESC, p.identidade LIMIT 5''')]
            detalhes = {i:json.loads(p) for i,p in db.execute("SELECT id,presente FROM eventos WHERE presente != '{}' ")}
            for evento in eventos:
                if evento['id'] in detalhes:
                    evento.update(tipo='presente', presente=detalhes[evento['id']])
        return dict(ranking=ranking, eventos=eventos, ranking_presentes=ranking_presentes, presentes=presentes)

    def salvar_presente(self, rex, *, chave, identidade, nome, presente, quantidade, efeitos, agora, efeito_aplicado):
        pontos = quantidade * 10
        detalhe = dict(presente, quantidade=quantidade, pontos=pontos, efeito_aplicado=efeito_aplicado)
        mensagem = f"{nome} enviou {quantidade} × {presente['nome']}!"
        with self.conectar() as db:
            inserido = db.execute('''INSERT OR IGNORE INTO presentes
                (chave,identidade,usuario,presente,quantidade,valor,efeito,efeitos,pontos,data,efeito_aplicado)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                (chave,identidade,nome,presente['nome'],quantidade,presente['valor'],presente['efeito'],
                 json.dumps(efeitos),pontos,agora,int(efeito_aplicado)))
            if not inserido.rowcount:
                return False
            db.execute('INSERT OR REPLACE INTO cachorro VALUES (1, ?)', (json.dumps(asdict(rex)),))
            db.execute('''INSERT INTO eventos(nome,mensagem,instante,origem,comando,efeitos,presente)
                          VALUES (?,?,?,'tiktok','',?,?)''',
                       (nome,mensagem,agora,json.dumps(efeitos),json.dumps(detalhe)))
            db.execute('DELETE FROM eventos WHERE id NOT IN (SELECT id FROM eventos ORDER BY id DESC LIMIT 100)')
        return True
