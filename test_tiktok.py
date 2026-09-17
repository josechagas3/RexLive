import asyncio
import importlib.util
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from app import Jogo, criar_servidor
from tiktok_live import TikTokBridge, interpretar_comentario, normalizar_perfil, carregar_cliente


EVENTS = ('connect', 'comment', 'disconnect', 'end')


class UserOfflineError(Exception):
    pass


class FakeClient:
    """Transporte local injetado apenas nos testes; nunca acessa a rede."""
    def __init__(self, event=None, mode='connected'):
        self.handlers = {}
        self.room_id = 500
        self.event = event
        self.mode = mode
        self.closed = False
        self.ready = threading.Event()

    def add_listener(self, event, handler):
        self.handlers[event] = handler

    async def start(self, **options):
        self.options = options
        self.exit = asyncio.Event()
        self.ready.set()
        if self.mode == 'offline':
            raise UserOfflineError()
        if self.mode == 'pending':
            await self.exit.wait()
        async def run():
            await self.handlers['connect'](None)
            if self.event:
                await self.handlers['comment'](self.event)
            if self.mode == 'ended':
                await self.handlers['end'](None)
                await self.handlers['disconnect'](None)
                return
            await self.exit.wait()
        return asyncio.create_task(run())

    async def disconnect(self, close_client=False):
        self.exit.set()
        # Confere se notificações de limpeza não sobrescrevem o estado terminal.
        await self.handlers['disconnect'](None)
        self.closed = close_client

    async def close(self):
        self.closed = True


def wait_until(predicate, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Tempo esgotado esperando o estado de teste')


class TikTokTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'rex.db'
        self.jogo = Jogo(self.path)
        self.now = 100
        self.bridge = TikTokBridge(self.jogo, factory=lambda _: (FakeClient(), EVENTS), clock=lambda: self.now)
        self.bridge.estado = 'conectado'

    def tearDown(self):
        self.bridge.desconectar()
        self.bridge.aguardar()
        self.temp.cleanup()

    def send(self, **overrides):
        data = dict(texto='carinho', user_id=1, nome='Ana', msg_id=1, room_id=500)
        data.update(overrides)
        return self.bridge.processar(**data)

    def test_comandos_exatos_e_perfil(self):
        for text in (' água ', 'ÁGUA', '!agua'):
            self.assertEqual(interpretar_comentario(text), 'agua')
        for text in ('quero comida', '!comida agora', '!!comida', '', None):
            self.assertIsNone(interpretar_comentario(text))
        self.assertEqual(normalizar_perfil(' @terra.updatess '), 'terra.updatess')
        for value in ('https://tiktok.com/@ana', '@@ana', 'a b', '', None, 'a'*25):
            with self.assertRaises(ValueError): normalizar_perfil(value)

    def test_cooldown_individual_e_duplicacao(self):
        self.assertTrue(self.send())
        self.assertFalse(self.send(msg_id=2))
        self.assertTrue(self.send(user_id=2, msg_id=3))
        self.now += 5
        self.assertFalse(self.send())
        self.assertTrue(self.send(msg_id=4))
        self.assertEqual(self.jogo.rex.experiencia, 30)
        self.assertEqual(self.bridge.snapshot()['aplicados'], 3)

    def test_duplicata_apos_reinicio_nao_credita(self):
        self.assertTrue(self.send())
        jogo = Jogo(self.path)
        bridge = TikTokBridge(jogo)
        bridge.estado = 'conectado'
        self.assertFalse(bridge.processar(texto='carinho', user_id=1, nome='Ana', msg_id=1, room_id=500))
        self.assertEqual(jogo.rex.experiencia, 10)
        self.assertEqual(jogo.snapshot()['ranking'][0]['pontos'], 10)

    def test_identidade_estavel_nomes_iguais_e_simulador(self):
        self.jogo.interagir('Ana', 'carinho')
        self.send()
        self.send(user_id=2, msg_id=2)
        self.now += 5
        self.send(nome='Novo nome', msg_id=3)
        ranking = self.jogo.snapshot()['ranking']
        self.assertEqual(len(ranking), 3)
        self.assertEqual(ranking[0], dict(nome='Novo nome', pontos=20, origem='tiktok'))
        self.assertEqual(sum(row['pontos'] for row in ranking), 40)

    def test_dormir_na_live_nao_acorda_rex(self):
        self.assertTrue(self.send(texto='dormir'))
        self.assertFalse(self.send(texto='dormir', msg_id=2, user_id=2))
        self.assertTrue(self.jogo.rex.dormindo)
        self.assertEqual(self.jogo.rex.experiencia, 10)

    def test_eventos_invalidos_e_apos_desconectar(self):
        for data in (dict(texto='olá'), dict(user_id=0), dict(msg_id=0), dict(room_id=0)):
            self.assertFalse(self.send(**data))
        self.bridge.desconectar()
        self.assertFalse(self.send())
        self.assertEqual(self.jogo.rex.experiencia, 0)

    def test_migracao_do_banco_antigo_preserva_pontos(self):
        old = Path(self.temp.name) / 'old.db'
        db = sqlite3.connect(old)
        db.executescript("CREATE TABLE cuidadores(nome TEXT PRIMARY KEY, pontos INTEGER NOT NULL); INSERT INTO cuidadores VALUES('João',70); CREATE TABLE eventos(id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,mensagem TEXT,instante REAL); INSERT INTO eventos(nome,mensagem,instante) VALUES('João','Cuidado antigo',1);")
        db.commit(); db.close()
        migrated = Jogo(old)
        migrated.interagir('João', 'carinho')
        restarted = Jogo(old).snapshot()
        self.assertEqual(restarted['ranking'][0]['pontos'], 80)
        self.assertEqual(restarted['eventos'][-1]['origem'], 'simulador')

    @unittest.skipUnless(importlib.util.find_spec('TikTokLive'), 'Dependência opcional não instalada')
    def test_callback_com_evento_real_da_biblioteca(self):
        from TikTokLive.events import CommentEvent
        event = CommentEvent.from_dict({'user': {'id':123,'nickname':'Ana'}, 'common':{'msgId':987}, 'content':'!água'})
        client = FakeClient(event)
        self.bridge.factory = lambda _: (client, EVENTS)
        self.bridge.conectar('@terra.updatess')
        wait_until(lambda: self.bridge.snapshot()['aplicados'] == 1)
        self.assertEqual(self.jogo.rex.experiencia, 10)
        self.assertFalse(client.options['process_connect_events'])
        self.assertEqual(self.jogo.snapshot()['eventos'][0]['origem'], 'tiktok')

    def test_cancelamento_durante_conexao(self):
        client = FakeClient(mode='pending')
        self.bridge.factory = lambda _: (client, EVENTS)
        self.bridge.conectar('terra.updatess')
        self.assertTrue(client.ready.wait(2))
        with self.assertRaises(ValueError): self.bridge.conectar('outro')
        self.bridge.desconectar(); self.bridge.aguardar(3)
        self.assertFalse(self.bridge.snapshot()['ativo'])
        self.assertEqual(self.bridge.snapshot()['estado'], 'desconectado')
        self.assertTrue(client.closed)

    def test_live_offline_sem_retentativas(self):
        client = FakeClient(mode='offline')
        self.bridge.factory = lambda _: (client, EVENTS)
        self.bridge.conectar('terra.updatess'); self.bridge.aguardar(3)
        self.assertEqual(self.bridge.snapshot()['estado'], 'offline')
        self.assertFalse(self.bridge.snapshot()['ativo'])

    def test_retentativas_limitadas(self):
        chamadas = []
        def falhar(perfil):
            chamadas.append(perfil)
            raise ConnectionError('Falha de rede de teste')
        self.bridge.factory = falhar
        self.bridge.retry_delays = (0, 0, 0)
        self.bridge.conectar('terra.updatess'); self.bridge.aguardar(3)
        self.assertEqual(len(chamadas), 4)
        self.assertEqual(self.bridge.snapshot()['estado'], 'erro')
        self.assertFalse(self.bridge.snapshot()['ativo'])

    def test_dependencia_ausente_mantem_simulador(self):
        self.bridge.disponivel = False
        with self.assertRaises(ValueError): self.bridge.conectar('terra.updatess')
        self.assertTrue(self.bridge.simular('Ana', 'carinho')['aplicada'])

    @unittest.skipUnless(importlib.util.find_spec('TikTokLive'), 'Dependência opcional não instalada')
    def test_criacao_do_cliente_instalado_sem_conectar(self):
        async def check():
            client, events = carregar_cliente('terra.updatess')
            try:
                self.assertEqual(client.unique_id, 'terra.updatess')
                self.assertEqual(events[1].__name__, 'CommentEvent')
            finally:
                await client.close()
        asyncio.run(check())

    def test_fim_da_live_preserva_estado_offline(self):
        self.bridge.factory = lambda _: (FakeClient(mode='ended'), EVENTS)
        self.bridge.conectar('terra.updatess'); self.bridge.aguardar(3)
        self.assertEqual(self.bridge.snapshot()['estado'], 'offline')
        self.assertFalse(self.bridge.snapshot()['ativo'])

    def test_api_conecta_bloqueia_simulador_e_desconecta(self):
        server = criar_servidor(self.jogo, 0, self.bridge)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        base = f'http://127.0.0.1:{server.server_port}'
        def post(route, data):
            with urlopen(Request(base+route, data=json.dumps(data).encode(), headers={'Content-Type':'application/json'})) as response:
                return json.load(response)
        try:
            with self.assertRaises(HTTPError): post('/api/tiktok/conectar', {'perfil':'https://example.com'})
            post('/api/tiktok/conectar', {'perfil':'terra.updatess'})
            wait_until(lambda: self.bridge.snapshot()['estado'] == 'conectado')
            with self.assertRaises(HTTPError) as error: post('/api/acao', {'nome':'Teste','comando':'comida'})
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(self.jogo.rex.experiencia, 0)
            post('/api/tiktok/desconectar', {})
            self.bridge.aguardar(3)
            self.assertTrue(post('/api/acao', {'nome':'Teste','comando':'comida'})['aplicada'])
        finally:
            server.shutdown(); server.server_close(); worker.join()


if __name__ == '__main__':
    unittest.main(verbosity=2)
