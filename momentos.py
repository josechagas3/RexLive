"""Avisos de crescimento sincronizados entre painel e captura."""
import math
import time


class MomentosLive:
    INTERVALO = 30 * 60
    DURACAO = 20

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.reiniciar()

    def reiniciar(self):
        self.inicio = self.clock()
        self.previa_ate = 0

    def previa(self):
        self.previa_ate = self.clock() + self.DURACAO

    def snapshot(self, rex):
        agora = self.clock()
        decorrido = max(0, agora - self.inicio)
        fase = decorrido % self.INTERVALO
        ativo = agora < self.previa_ate or (decorrido >= self.INTERVALO and fase < self.DURACAO)
        faltam = 100 - rex.experiencia % 100
        return dict(ativo=ativo, previa=agora < self.previa_ate, xp_faltante=faltam,
                    nivel_alvo=rex.nivel + 1, cuidados_faltantes=math.ceil(faltam / 10),
                    proximo_em=math.ceil(self.INTERVALO - fase))
