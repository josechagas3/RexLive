import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from cachorro import Cachorro
from app import Jogo, criar_servidor


class RegrasTest(unittest.TestCase):
    def test_comandos_e_limites(self):
        rex = Cachorro(fome=50, energia=50, felicidade=50, vida=50)
        rex.agir(' COMIDA ', 100)
        self.assertEqual(rex.fome, 60)
        rex.agir('ÁGUA', 100)
        self.assertEqual((rex.energia, rex.vida), (55, 53))
        rex.agir('brincar', 100)
        self.assertEqual((rex.felicidade, rex.energia, rex.fome), (65,45,57))
        rex.agir('carinho',100)
        self.assertEqual(rex.felicidade,75)
        for _ in range(20): rex.agir('comida',100)
        self.assertEqual(rex.fome,100)
        rex.passar_tempo(100000)
        self.assertTrue(all(0 <= getattr(rex,k) <= 100 for k in ('fome','vida','energia','felicidade')))

    def test_sono_e_tempo(self):
        rex=Cachorro(energia=30)
        rex.agir('dormir',100)
        rex.passar_tempo(60)
        self.assertEqual(rex.energia,38)
        self.assertEqual(rex.fome,98.5)
        self.assertEqual(rex.estado(101),'dormindo')
        rex.agir('acordar',102)
        self.assertFalse(rex.dormindo)
        rex.passar_tempo(60)
        self.assertEqual(rex.energia,37.75)

    def test_emocoes_e_nivel(self):
        rex=Cachorro()
        self.assertEqual(rex.estado(100),'normal')
        rex.agir('carinho',100)
        self.assertEqual(rex.estado(101),'feliz')
        for _ in range(9): rex.agir('carinho',100)
        self.assertEqual(rex.nivel,2)
        self.assertEqual(rex.estado(101),'comemorando')
        self.assertEqual(rex.estado(111),'normal')
        rex.fome=10
        self.assertEqual(rex.estado(111),'fome')
        rex.fome=100;rex.felicidade=10
        self.assertEqual(rex.estado(111),'triste')

    def test_cansaco_nao_da_xp(self):
        rex=Cachorro(energia=5)
        with self.assertRaises(ValueError): rex.agir('brincar',100)
        self.assertEqual(rex.experiencia,0)


class IntegracaoTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'rex.db'
        self.jogo=Jogo(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_reinicio_preserva_estado_e_ranking(self):
        self.jogo.interagir('João','brincar')
        reaberto=Jogo(self.path).snapshot()
        self.assertEqual(reaberto['cachorro']['energia'],90)
        self.assertEqual(reaberto['cachorro']['experiencia'],10)
        self.assertEqual(reaberto['ranking'],[dict(nome='João',pontos=10,origem='simulador')])
        self.assertEqual(len(reaberto['eventos']),1)

    def test_invalido_nao_salva(self):
        before=self.jogo.snapshot()
        for name,cmd in [('', 'comida'),('Ana','inexistente'),('x'*33,'água'),('Ana',None)]:
            with self.assertRaises(ValueError): self.jogo.interagir(name,cmd)
        self.assertEqual(self.jogo.snapshot(),before)

    def test_interacoes_concorrentes(self):
        threads=[threading.Thread(target=self.jogo.interagir,args=('Ana','carinho')) for _ in range(20)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(self.jogo.snapshot()['cachorro']['experiencia'],200)
        self.assertEqual(self.jogo.snapshot()['ranking'][0]['pontos'],200)

    def test_historico_para_rajadas_e_retencao(self):
        for _ in range(105):
            self.jogo.interagir('Ana', 'carinho')
        snapshot = self.jogo.snapshot()
        self.assertEqual(len(snapshot['eventos']), 100)
        self.assertEqual(snapshot['eventos'][0]['id'], 105)
        self.assertEqual(snapshot['eventos'][-1]['id'], 6)
        self.assertEqual(snapshot['ranking'][0]['pontos'], 1050)

    def test_http_e_restricao_local(self):
        server=criar_servidor(self.jogo,0)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(OSError):
                criar_servidor(self.jogo, server.server_port)
            with urlopen(base) as r:self.assertIn('Rex'.encode(),r.read())
            with urlopen(base+'/live-events.js') as r:
                self.assertIn(b'LiveEventQueue',r.read())
            req=Request(base+'/api/acao',data=json.dumps(dict(nome='Maria',comando='água')).encode(),headers={'Content-Type':'application/json'})
            with urlopen(req) as r:self.assertEqual(json.load(r)['ranking'][0]['nome'],'Maria')
            xp = self.jogo.rex.experiencia
            req=Request(base+'/api/momento/previa',data=b'{}',headers={'Content-Type':'application/json'})
            with urlopen(req) as r:self.assertTrue(json.load(r)['momento']['ativo'])
            self.assertEqual(self.jogo.rex.experiencia, xp)
            req=Request(base+'/api/acao',data=b'{}',headers={'Origin':'https://example.com'})
            with self.assertRaises(HTTPError) as e:urlopen(req)
            self.assertEqual(e.exception.code,403)
            req=Request(base+'/api/acao',data=b'[]')
            with self.assertRaises(HTTPError) as e:urlopen(req)
            self.assertEqual(e.exception.code,400)
            with self.assertRaises(HTTPError) as e:urlopen(base+'/../banco.py')
            self.assertEqual(e.exception.code,404)
        finally:
            server.shutdown();server.server_close();worker.join()


if __name__=='__main__':unittest.main(verbosity=2)
