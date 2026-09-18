"""Testes locais de presentes, sem conexão ao TikTok nem uso do banco da live."""
import asyncio
import importlib.util
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen
from app import Jogo, criar_servidor
from presentes import aplicar_efeito_presente
from tiktok_live import TikTokBridge
from test_tiktok import FakeClient, EVENTS, wait_until


class PresentesTest(unittest.TestCase):
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

    def send(self, **kwargs):
        args = dict(presente='Rose', quantidade=1, user_id=1, nome='Ana', msg_id=1, room_id=500)
        args.update(kwargs)
        return self.bridge.processar_presente(**args)

    def test_mapeamento_e_quantidade_invalida(self):
        self.assertEqual(aplicar_efeito_presente(' rose ', 3)['valor'], 15)
        self.assertIsNone(aplicar_efeito_presente('Desconhecido'))
        for quantity in (0,-1,True,1.5,'2',10001):
            with self.assertRaises(ValueError): aplicar_efeito_presente('Rose',quantity)

    def test_quatro_presentes_sem_xp_sono_ou_emocao_forcada(self):
        self.jogo.rex.fome = self.jogo.rex.felicidade = self.jogo.rex.energia = 50
        self.jogo.rex.dormindo = True
        self.jogo.rex.feliz_ate = 123
        self.jogo.rex.celebrando_ate = 456
        for i, gift in enumerate(('Rose','Heart Me','Coffee','Lion'),1):
            self.assertTrue(self.send(presente=gift,msg_id=i)); self.now += 2
        r=self.jogo.rex
        self.assertEqual((r.fome,r.felicidade,r.energia),(55,60,70))
        self.assertEqual((r.experiencia,r.nivel,r.feliz_ate,r.celebrando_ate),(0,1,123,456))
        self.assertTrue(r.dormindo)
        snap=self.jogo.snapshot()
        self.assertEqual(snap['ranking'],[])
        self.assertEqual(snap['ranking_presentes'][0]['pontos'],40)
        self.assertEqual(len(snap['presentes']),4)
        self.assertEqual(snap['eventos'][0]['tipo'],'presente')
        self.assertEqual(snap['eventos'][0]['presente']['efeito'],'especial')

    def test_limite_e_delta_real(self):
        self.jogo.rex.fome=98
        self.assertTrue(self.send(quantidade=3))
        self.assertEqual(self.jogo.rex.fome,100)
        present=self.jogo.snapshot()['presentes'][0]
        self.assertEqual((present['quantidade'],present['valor'],present['efeitos']['fome']),(3,15,2))
        self.assertEqual(present['pontos'],30)

    def test_combo_e_final_repetido_com_outro_msg_id(self):
        self.jogo.rex.fome=10
        self.assertFalse(self.send(quantidade=1,streaking=True,group_id=80,gift_id=5655))
        self.assertFalse(self.send(quantidade=2,streaking=True,group_id=80,gift_id=5655,msg_id=2))
        self.assertTrue(self.send(quantidade=3,group_id=80,gift_id=5655,msg_id=3))
        self.now += 2
        self.assertFalse(self.send(quantidade=3,group_id=80,gift_id=5655,msg_id=4))
        self.assertEqual(self.jogo.rex.fome,25)
        self.assertEqual(len(self.jogo.snapshot()['presentes']),1)

    def test_duplicata_apos_reinicio_e_salas_distintas(self):
        self.assertTrue(self.send())
        self.jogo=Jogo(self.path)
        self.bridge.jogo=self.jogo
        self.bridge.presentes_cooldowns.clear()
        self.assertFalse(self.send())
        self.assertTrue(self.send(room_id=501))
        self.assertEqual(self.jogo.snapshot()['ranking_presentes'][0]['pontos'],20)

    def test_cooldown_separado_preserva_registro_e_pontos(self):
        self.jogo.rex.fome=50
        self.assertTrue(self.bridge.processar(texto='carinho',user_id=1,nome='Ana',msg_id=1,room_id=500))
        self.assertTrue(self.send())
        self.assertTrue(self.send(msg_id=2))
        self.assertEqual(self.jogo.rex.fome,55)
        self.assertFalse(self.jogo.snapshot()['presentes'][0]['efeito_aplicado'])
        self.assertEqual(self.jogo.snapshot()['ranking_presentes'][0]['pontos'],20)
        self.assertEqual(self.jogo.rex.experiencia,10)
        self.now += 1
        self.assertTrue(self.send(msg_id=3))
        self.assertEqual(self.jogo.rex.fome,60)

    def test_identidade_nomes_iguais_e_nome_atualizado(self):
        self.send(); self.send(user_id=2,msg_id=2)
        self.now += 2; self.send(nome='Novo nome',msg_id=3)
        ranking=self.jogo.snapshot()['ranking_presentes']
        self.assertEqual(len(ranking),2)
        self.assertEqual(ranking[0],dict(nome='Novo nome',pontos=20,origem='tiktok'))

    def test_desconhecido_invalido_e_desconectado(self):
        before=self.jogo.snapshot()
        for args in (dict(presente='Unknown'),dict(quantidade=0),dict(quantidade=True),dict(user_id=None),dict(msg_id=0)):
            self.assertFalse(self.send(**args))
        self.bridge.desconectar()
        self.assertFalse(self.send())
        self.assertEqual(self.jogo.snapshot(),before)

    def test_transacao_falha_nao_credita_nem_muda_rex(self):
        with self.jogo.banco.conectar() as db:
            db.execute("CREATE TRIGGER teste_falha BEFORE INSERT ON eventos BEGIN SELECT RAISE(ABORT,'falha teste'); END")
        self.jogo.rex.fome=50
        with self.assertRaises(sqlite3.IntegrityError): self.send()
        self.assertEqual(self.jogo.rex.fome,50)
        self.assertEqual(self.jogo.snapshot()['presentes'],[])
        self.assertEqual(self.jogo.snapshot()['ranking_presentes'],[])

    def test_deduplicacao_concorrente(self):
        results=[]
        def send():
            results.append(self.jogo.receber_presente('Ana','Rose',1,identidade='tiktok:1',recebido='gift:mesma'))
        threads=[threading.Thread(target=send) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(r['aplicada'] for r in results),1)
        self.assertEqual(self.jogo.snapshot()['ranking_presentes'][0]['pontos'],10)

    def test_migracao_reabertura_e_historico_reduzido(self):
        self.jogo.interagir('Ana','carinho')
        self.send()
        for _ in range(101): self.jogo.interagir('Ana','carinho')
        restarted=Jogo(self.path)
        self.assertEqual(len(restarted.snapshot()['eventos']),100)
        self.assertEqual(len(restarted.snapshot()['presentes']),1)
        self.assertEqual(restarted.snapshot()['ranking'][0]['pontos'],1020)
        self.bridge.jogo=restarted
        self.assertFalse(self.send())

    def test_api_expoe_presente_sem_alterar_ranking_antigo(self):
        self.send()
        server=criar_servidor(self.jogo,0,self.bridge)
        worker=threading.Thread(target=server.serve_forever,daemon=True); worker.start()
        try:
            with urlopen(f'http://127.0.0.1:{server.server_port}/api/estado') as response:
                data=json.load(response)
            self.assertEqual(data['ranking'],[])
            self.assertEqual(data['ranking_presentes'][0]['pontos'],10)
            self.assertEqual(data['eventos'][0]['presente']['nome'],'Rosa 🌹')
            self.assertEqual(data['tiktok']['presentes_aplicados'],1)
        finally:
            server.shutdown(); server.server_close(); worker.join()

    @unittest.skipUnless(importlib.util.find_spec('TikTokLive'),'TikTokLive opcional ausente')
    def test_callback_real_biblioteca_combo_sem_rede(self):
        from TikTokLive.events import GiftEvent
        class GiftClient(FakeClient):
            async def start(client, **options):
                connection=await super(GiftClient,client).start(**options)
                await asyncio.sleep(0)
                for final,count,msg in ((0,1,1),(0,2,2),(1,3,3),(1,3,4)):
                    event=GiftEvent.from_dict({'user':{'id':123,'nickname':'Ana'},'common':{'msgId':msg},
                        'giftId':5655,'groupId':99,'repeatCount':count,'repeatEnd':final,
                        'gift':{'id':5655,'name':'Rose','type':1}})
                    await client.handlers['gift'](event)
                return connection
        client=GiftClient()
        self.bridge.factory=lambda _: (client,(*EVENTS,'gift'))
        self.bridge.conectar('terra.updatess')
        wait_until(lambda:self.bridge.snapshot()['presentes_recebidos']==4)
        self.assertEqual(self.bridge.snapshot()['presentes_aplicados'],1)
        self.assertEqual(self.jogo.snapshot()['presentes'][0]['quantidade'],3)
        self.assertEqual(self.jogo.rex.experiencia,0)
        self.assertTrue(client.options['fetch_gift_info'])

    @unittest.skipUnless(importlib.util.find_spec('TikTokLive'),'TikTokLive opcional ausente')
    def test_callbacks_outros_presentes_e_evento_incompleto(self):
        from TikTokLive.events import GiftEvent
        from types import SimpleNamespace
        class GiftClient(FakeClient):
            async def start(client, **options):
                connection=await super(GiftClient,client).start(**options)
                await asyncio.sleep(0)
                await client.handlers['gift'](SimpleNamespace(gift=None))
                for index,name in enumerate(('Heart Me','Coffee','Lion'),1):
                    event=GiftEvent.from_dict({'user':{'id':index,'nickname':'Apoiador'},
                        'common':{'msgId':index},'repeatCount':1,
                        'gift':{'id':index,'name':name,'type':2}})
                    await client.handlers['gift'](event)
                return connection
        self.jogo.rex.felicidade=self.jogo.rex.energia=50
        client=GiftClient()
        self.bridge.factory=lambda _: (client,(*EVENTS,'gift'))
        self.bridge.conectar('terra.updatess')
        wait_until(lambda:self.bridge.snapshot()['presentes_aplicados']==3)
        self.assertEqual((self.jogo.rex.felicidade,self.jogo.rex.energia),(60,70))
        self.assertEqual(self.jogo.rex.experiencia,0)
        self.assertEqual(len(self.jogo.snapshot()['presentes']),3)


if __name__ == '__main__': unittest.main()
