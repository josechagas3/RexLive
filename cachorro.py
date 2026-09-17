"""Regras puras do jogo, independentes da interface e do banco."""
import unicodedata
from dataclasses import dataclass, asdict


def comando_normalizado(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.strip().lower())
                   if unicodedata.category(c) != 'Mn')


@dataclass
class Cachorro:
    nome: str = 'Rex'
    fome: float = 100
    vida: float = 100
    felicidade: float = 100
    energia: float = 100
    experiencia: int = 0
    dormindo: bool = False
    celebrando_ate: float = 0
    feliz_ate: float = 0

    @property
    def nivel(self):
        return 1 + self.experiencia // 100

    def limitar(self):
        for key in ('fome', 'vida', 'felicidade', 'energia'):
            setattr(self, key, max(0, min(100, getattr(self, key))))

    def passar_tempo(self, segundos):
        # Taxas por minuto; chamadas frequentes mantêm transições suaves.
        minutos = max(0, segundos) / 60
        self.fome -= 1.5 * minutos
        self.felicidade -= .7 * minutos
        self.energia += (8 if self.dormindo else -1) * minutos
        if self.fome < 20:
            self.vida -= 2 * minutos
        elif self.fome > 60 and self.energia > 30:
            self.vida += .5 * minutos
        self.limitar()

    def agir(self, comando, agora):
        comando = comando_normalizado(comando)
        if comando not in ('comida', 'agua', 'brincar', 'dormir', 'carinho'):
            raise ValueError('Use comida, água, brincar, dormir ou carinho.')
        anterior = self.nivel
        if comando == 'comida':
            self.dormindo = False
            self.fome += 10
            mensagem = 'Rex comeu! +10 de saciedade'
        elif comando == 'agua':
            self.dormindo = False
            self.energia += 5
            self.vida += 3
            mensagem = 'Água fresquinha! +5 de energia e +3 de vida'
        elif comando == 'brincar':
            if self.energia < 10:
                raise ValueError('Rex está cansado. Deixe ele dormir um pouco!')
            self.dormindo = False
            self.felicidade += 15
            self.energia -= 10
            self.fome -= 3
            mensagem = 'Hora da bolinha! +15 de felicidade'
        elif comando == 'dormir':
            self.dormindo = not self.dormindo
            mensagem = 'Bons sonhos! Rex está recuperando energia.' if self.dormindo else 'Bom dia! Rex acordou.'
        else:
            self.felicidade += 10
            mensagem = 'Rex ganhou carinho! +10 de felicidade'
        self.experiencia += 10
        self.feliz_ate = agora + 7
        if self.nivel > anterior:
            self.celebrando_ate = agora + 10
            mensagem += f' • Subiu para o nível {self.nivel}!'
        self.limitar()
        return mensagem

    def estado(self, agora):
        if self.dormindo:
            return 'dormindo'
        if agora < self.celebrando_ate:
            return 'comemorando'
        if self.fome < 30:
            return 'fome'
        if self.felicidade < 30 or self.vida < 30:
            return 'triste'
        if agora < self.feliz_ate:
            return 'feliz'
        return 'normal'

    def publico(self, agora):
        data = asdict(self)
        for key in ('fome', 'vida', 'felicidade', 'energia'):
            data[key] = round(data[key], 1)
        data.update(nivel=self.nivel, xp_nivel=self.experiencia % 100,
                    xp_meta=100, estado=self.estado(agora))
        return data
