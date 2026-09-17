"""Ponte de leitura TikTokLive; nenhuma mensagem é enviada à live."""
import asyncio
import importlib.util
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from cachorro import comando_normalizado
from config import TIKTOK_PERFIL, TIKTOK_COOLDOWN
from presentes import efeitos_presente

COMANDOS = {'comida', 'agua', 'brincar', 'dormir', 'acordar', 'carinho'}


def normalizar_perfil(perfil):
    if not isinstance(perfil, str):
        raise ValueError('Informe o @ do perfil da live.')
    perfil = perfil.strip().removeprefix('@')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.]{0,23}', perfil) or perfil.endswith('.'):
        raise ValueError('Use somente o @ do perfil, sem link ou espaços (até 24 caracteres).')
    return perfil.lower()


def interpretar_comentario(texto):
    if not isinstance(texto, str) or len(texto) > 40:
        return None
    comando = comando_normalizado(texto).removeprefix('!')
    return comando if comando in COMANDOS else None


def nome_seguro(nome, fallback):
    nome = ''.join(c for c in str(nome or '') if not unicodedata.category(c).startswith('C')).strip()
    return (nome or fallback)[:32]


def carregar_cliente(perfil):
    from TikTokLive import TikTokLiveClient
    from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent, LiveEndEvent, GiftEvent
    class ClienteAssincrono(TikTokLiveClient):
        async def close(self):
            # TikTokLive 7.0.1 chama run_until_complete em close(), apesar de
            # ser async. A ponte já cancela/drena suas tarefas com asyncio.run.
            await self.web.close()
    client = ClienteAssincrono(unique_id=perfil, web_kwargs={'httpx_kwargs': {'timeout': 15}})
    return client, (ConnectEvent, CommentEvent, DisconnectEvent, LiveEndEvent, GiftEvent)


class TikTokBridge:
    def __init__(self, jogo, factory=None, clock=time.monotonic, retry_delays=(5, 10, 20)):
        self.jogo = jogo
        self.factory = factory or carregar_cliente
        self.disponivel = factory is not None or importlib.util.find_spec('TikTokLive') is not None
        self.clock = clock
        self.retry_delays = retry_delays
        self.lock = threading.RLock()
        self.thread = None
        self.loop = None
        self.task = None
        self.stop = threading.Event()
        self.perfil = TIKTOK_PERFIL
        self.estado = 'desconectado' if self.disponivel else 'dependencia_ausente'
        self.mensagem = 'Informe seu perfil e conecte com a live aberta.' if self.disponivel else 'Execute instalar_tiktok.bat e reinicie o servidor.'
        self.recebidos = self.aplicados = self.ignorados = 0
        self.ultimo = ''
        self.cooldowns = OrderedDict()
        self.cooldowns_presentes = OrderedDict()
        self.vistos = OrderedDict()
        self.vistos_presentes = OrderedDict()
        self.attempt_token = None

    def snapshot(self):
        with self.lock:
            return dict(estado=self.estado, mensagem=self.mensagem, perfil=self.perfil,
                        disponivel=self.disponivel, ativo=bool(self.thread and self.thread.is_alive()),
                        recebidos=self.recebidos, aplicados=self.aplicados, ignorados=self.ignorados,
                        ultimo=self.ultimo, intervalo=TIKTOK_COOLDOWN)

    def atualizar(self, estado, mensagem):
        with self.lock:
            if not self.stop.is_set():
                self.estado, self.mensagem = estado, mensagem

    def conectar(self, perfil):
        perfil = normalizar_perfil(perfil)
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError('Já existe uma conexão em andamento. Desconecte antes de trocar o perfil.')
            if not self.disponivel:
                raise ValueError('Execute instalar_tiktok.bat e reinicie o servidor para habilitar o TikTok.')
            self.stop.clear()
            self.perfil = perfil
            self.estado, self.mensagem = 'conectando', f'Procurando a live de @{perfil}…'
            self.recebidos = self.aplicados = self.ignorados = 0
            self.ultimo = ''
            self.sessao_iniciada = False
            self.thread = threading.Thread(target=self._worker, name='rex-tiktok', daemon=True)
            self.thread.start()

    def desconectar(self):
        with self.lock:
            self.stop.set()
            self.estado, self.mensagem = 'desconectado', 'TikTok desconectado. Simulador disponível ao encerrar a conexão.'
            if self.loop and self.task and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.task.cancel)

    def aguardar(self, timeout=5):
        if self.thread:
            self.thread.join(timeout)

    def simular(self, nome, comando):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError('Desconecte o TikTok antes de usar o simulador.')
            return self.jogo.interagir(nome, comando)

    def processar(self, *, texto, user_id, nome, msg_id, room_id):
        with self.lock:
            if self.stop.is_set() or self.estado != 'conectado':
                return False
            self.recebidos += 1
            comando = interpretar_comentario(texto)
            if not comando or not user_id or not msg_id or not room_id:
                self.ignorados += 1
                return False
            chave = f'{room_id}:{msg_id}'
            if chave in self.vistos:
                self.ignorados += 1
                return False
            self.vistos[chave] = True
            if len(self.vistos) > 10000:
                self.vistos.popitem(last=False)
            identidade = 'tiktok:' + str(user_id)
            agora = self.clock()
            if agora - self.cooldowns.get(identidade, float('-inf')) < TIKTOK_COOLDOWN:
                self.ignorados += 1
                return False
            nome = nome_seguro(nome, 'Cuidador TikTok')
            try:
                resultado = self.jogo.interagir(nome, comando, identidade=identidade, origem='tiktok', recebido=chave)
            except ValueError as error:
                self.ultimo = str(error)
                self.ignorados += 1
                return False
            if not resultado['aplicada']:
                self.ignorados += 1
                return False
            self.cooldowns[identidade] = agora
            self.cooldowns.move_to_end(identidade)
            if len(self.cooldowns) > 5000:
                self.cooldowns.popitem(last=False)
            self.aplicados += 1
            self.ultimo = f'{nome}: {comando}'
            return True

    def processar_presente(self, *, gift_id, nome_presente, user_id, nome, msg_id, room_id):
        with self.lock:
            if self.stop.is_set() or self.estado != 'conectado':
                return False
            if not efeitos_presente(nome_presente):
                self.ignorados += 1
                return False
            self.recebidos += 1
            if not user_id or not gift_id or not room_id:
                self.ignorados += 1
                return False
            chave = f'{room_id}:gift:{gift_id}'
            if chave in self.vistos_presentes:
                self.ignorados += 1
                return False
            self.vistos_presentes[chave] = True
            if len(self.vistos_presentes) > 10000:
                self.vistos_presentes.popitem(last=False)
            identidade = 'tiktok:' + str(user_id)
            agora = self.clock()
            if agora - self.cooldowns_presentes.get(identidade, float('-inf')) < TIKTOK_COOLDOWN:
                self.ignorados += 1
                return False
            nome = nome_seguro(nome, 'Cuidador TikTok')
            try:
                resultado = self.jogo.interagir_presente(nome, gift_id, nome_presente, identidade=identidade, origem='tiktok', recebido=chave)
            except ValueError as error:
                self.ultimo = str(error)
                self.ignorados += 1
                return False
            if not resultado['aplicada']:
                self.ignorados += 1
                return False
            self.cooldowns_presentes[identidade] = agora
            self.cooldowns_presentes.move_to_end(identidade)
            if len(self.cooldowns_presentes) > 5000:
                self.cooldowns_presentes.popitem(last=False)
            self.aplicados += 1
            self.ultimo = f'{nome}: presente {nome_presente}'
            return True

    def _worker(self):
        try:
            asyncio.run(self._run())
        except asyncio.CancelledError:
            pass
        except Exception as error:
            self.atualizar('erro', f'Não foi possível iniciar a conexão ({type(error).__name__}).')
        finally:
            with self.lock:
                self.loop = self.task = None
                if self.stop.is_set():
                    self.estado, self.mensagem = 'desconectado', 'TikTok desconectado. Simulador disponível.'

    async def _run(self):
        with self.lock:
            self.loop, self.task = asyncio.get_running_loop(), asyncio.current_task()
        if self.stop.is_set():
            return
        for tentativa in range(4):
            client = None
            encerrada = False
            token = object()
            self.attempt_token = token
            try:
                client, events = self.factory(self.perfil)
                Connect, Comment, Disconnect, LiveEnd = events[:4]
                Gift = events[4] if len(events) > 4 else None

                async def on_connect(event, token=token):
                    if self.attempt_token is token:
                        if not self.sessao_iniciada:
                            with self.jogo.lock:
                                self.jogo.momentos.reiniciar()
                            self.sessao_iniciada = True
                        self.atualizar('conectado', f'Lendo comentários e presentes de @{self.perfil}.')

                async def on_comment(event, token=token, client=client):
                    if self.attempt_token is not token:
                        return
                    try:
                        user = event.user
                        common = event.common
                        self.processar(texto=event.comment, user_id=getattr(user, 'id', None),
                                       nome=getattr(user, 'nickname', None) or getattr(user, 'display_id', None),
                                       msg_id=getattr(common, 'msg_id', None), room_id=client.room_id)
                    except Exception as error:
                        with self.lock:
                            self.ultimo = f'Falha ao processar comentário ({type(error).__name__}).'

                async def on_gift(event, token=token, client=client):
                    if self.attempt_token is not token:
                        return
                    try:
                        gift = event.gift
                        user = event.user
                        common = event.common
                        gift_id = getattr(gift, 'id', None) or getattr(common, 'msg_id', None)
                        nome_presente = getattr(gift, 'name', '') or getattr(gift, 'gift_name', '')
                        self.processar_presente(gift_id=gift_id, nome_presente=nome_presente,
                                                user_id=getattr(user, 'id', None),
                                                nome=getattr(user, 'nickname', None) or getattr(user, 'display_id', None),
                                                msg_id=getattr(common, 'msg_id', None), room_id=client.room_id)
                    except Exception as error:
                        with self.lock:
                            self.ultimo = f'Falha ao processar presente ({type(error).__name__}).'

                async def on_disconnect(event, token=token):
                    if self.attempt_token is token and not encerrada:
                        self.atualizar('reconectando', 'A conexão com o TikTok foi interrompida.')

                async def on_end(event, token=token, client=client):
                    nonlocal encerrada
                    if self.attempt_token is not token:
                        return
                    encerrada = True
                    self.atualizar('offline', 'A live terminou. Abra outra transmissão e conecte novamente.')

                client.add_listener(Connect, on_connect)
                client.add_listener(Comment, on_comment)
                client.add_listener(Disconnect, on_disconnect)
                client.add_listener(LiveEnd, on_end)
                if Gift is not None:
                    client.add_listener(Gift, on_gift)
                # Não processa o lote antigo recebido na abertura da conexão.
                fetch_gifts = Gift is not None
                connection = await asyncio.wait_for(client.start(process_connect_events=False, fetch_gift_info=fetch_gifts), timeout=35)
                await connection
                if encerrada:
                    self.atualizar('offline', 'A live terminou. Abra outra transmissão e conecte novamente.')
                    return
            except asyncio.CancelledError:
                raise
            except Exception as error:
                kind = type(error).__name__
                if 'UserOffline' in kind or 'LiveNotFound' in kind:
                    self.atualizar('offline', f'@{self.perfil} não está ao vivo. Abra a live e tente novamente.')
                    return
                if 'UserNotFound' in kind:
                    self.atualizar('erro', 'Perfil não encontrado. Confira o @ informado.')
                    return
                self.atualizar('reconectando', f'Conexão indisponível ({kind}). Verifique a internet e a live.')
            finally:
                self.attempt_token = None
                if client:
                    try:
                        await asyncio.wait_for(client.disconnect(close_client=True), timeout=3)
                    except (Exception, asyncio.CancelledError):
                        try:
                            await asyncio.wait_for(client.close(), timeout=2)
                        except (Exception, asyncio.CancelledError):
                            pass
            if self.stop.is_set():
                return
            if tentativa == 3:
                self.atualizar('erro', 'Não foi possível manter a conexão após 4 tentativas. Tente novamente mais tarde.')
                return
            atraso = self.retry_delays[tentativa]
            self.atualizar('reconectando', f'Nova tentativa em {atraso}s. A live pode estar indisponível ou o serviço limitado.')
            await asyncio.sleep(atraso)
