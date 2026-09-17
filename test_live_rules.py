import tempfile
import unittest
from pathlib import Path
from cachorro import Cachorro
from momentos import MomentosLive
from app import Jogo
from banco import Banco
from tiktok_live import interpretar_comentario


class EnergiaTest(unittest.TestCase):
    def test_consumo_lento(self):
        rex = Cachorro()
        rex.passar_tempo(30 * 60)
        self.assertEqual(rex.energia, 92.5)
        self.assertFalse(rex.dormindo)

    def test_zero_faz_dormir_e_sono_recupera(self):
        rex = Cachorro(energia=.1)
        rex.passar_tempo(60)
        self.assertTrue(rex.dormindo)
        self.assertEqual(rex.energia, 0)
        rex.passar_tempo(60)
        self.assertEqual(rex.energia, 8)
        self.assertTrue(rex.dormindo)
        rex.passar_tempo(1000)
        self.assertEqual(rex.energia, 100)
        self.assertTrue(rex.dormindo)

    def test_brincar_ate_zero_faz_dormir(self):
        rex = Cachorro(energia=10)
        rex.agir('brincar', 10)
        self.assertEqual(rex.energia, 0)
        self.assertTrue(rex.dormindo)

    def test_comunidade_acorda_com_energia_minima(self):
        rex = Cachorro(energia=0, dormindo=True)
        rex.agir('!acordar', 10)
        self.assertEqual(rex.energia, 15)
        self.assertFalse(rex.dormindo)
        self.assertEqual(rex.experiencia, 10)
        with self.assertRaises(ValueError): rex.agir('!acordar', 11)
        self.assertEqual(rex.experiencia, 10)
        self.assertEqual(interpretar_comentario('!acordar'), 'acordar')

    def test_cuidados_nao_acordam_sem_comando(self):
        rex = Cachorro(energia=50, dormindo=True)
        for cmd in ('comida', 'agua', 'carinho'):
            rex.agir(cmd, 10)
            self.assertTrue(rex.dormindo)
        with self.assertRaises(ValueError): rex.agir('brincar', 10)
        rex.agir('acordar', 11)
        self.assertEqual(rex.energia, 55)

    def test_salvamento_antigo_zero_energia(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rex.db'
            Banco(path).salvar(Cachorro(energia=0, dormindo=False))
            jogo = Jogo(path)
            self.assertTrue(jogo.rex.dormindo)
            result = jogo.interagir('João', '!acordar')
            self.assertEqual(result['eventos'][0]['comando'], 'acordar')
            self.assertEqual(result['eventos'][0]['efeitos']['energia'], 15)
            self.assertFalse(Jogo(path).rex.dormindo)

    def test_evento_registra_ganho_real(self):
        with tempfile.TemporaryDirectory() as folder:
            jogo = Jogo(Path(folder) / 'rex.db')
            jogo.rex.fome = 96
            result = jogo.interagir('João', '!comida')
            self.assertEqual(result['eventos'][0]['efeitos']['fome'], 4)
            self.assertEqual(result['cachorro']['fome'], 100)


class MomentosTest(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.momentos = MomentosLive(clock=lambda: self.now)
        self.rex = Cachorro(experiencia=380)

    def test_aviso_a_cada_trinta_minutos(self):
        for seconds, expected in ((0,False),(1799,False),(1800,True),(1819,True),(1820,False),(3599,False),(3600,True)):
            self.now = seconds
            self.assertEqual(self.momentos.snapshot(self.rex)['ativo'], expected)

    def test_xp_real_nivel_e_cuidados(self):
        self.now = 1800
        state = self.momentos.snapshot(self.rex)
        self.assertEqual((state['xp_faltante'], state['nivel_alvo'], state['cuidados_faltantes']), (20,5,2))
        self.rex.agir('carinho', 1800)
        self.assertEqual(self.momentos.snapshot(self.rex)['xp_faltante'], 10)
        self.rex.agir('carinho', 1801)
        state = self.momentos.snapshot(self.rex)
        self.assertEqual((state['xp_faltante'], state['nivel_alvo']), (100,6))

    def test_previa_nao_altera_xp_ou_agendamento(self):
        self.now = 50
        self.momentos.previa()
        self.assertTrue(self.momentos.snapshot(self.rex)['ativo'])
        self.assertEqual(self.rex.experiencia, 380)
        self.now = 70
        self.assertFalse(self.momentos.snapshot(self.rex)['ativo'])
        self.assertEqual(self.momentos.snapshot(self.rex)['proximo_em'], 1730)

    def test_nova_sessao_reinicia_relogio(self):
        self.now = 1800
        self.momentos.reiniciar()
        self.assertFalse(self.momentos.snapshot(self.rex)['ativo'])
        self.assertEqual(self.momentos.snapshot(self.rex)['proximo_em'], 1800)


if __name__ == '__main__': unittest.main(verbosity=2)
