"""Servidor local. TikTokLive é opcional para receber comentários reais."""
import argparse
import copy
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
from banco import Banco
from cachorro import comando_normalizado
from momentos import MomentosLive
from config import BASE_DIR, DB_PATH, HOST, PORT, TICK_SECONDS


class ServidorLocal(ThreadingHTTPServer):
    # No Windows, impede dois processos de servir respostas na mesma porta.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Jogo:
    def __init__(self, caminho=DB_PATH):
        self.banco = Banco(caminho)
        self.rex = self.banco.carregar()
        self.rex.limitar()
        self.momentos = MomentosLive()
        self.lock = threading.RLock()
        self.ultimo = time.monotonic()
        self.rex.feliz_ate = self.rex.celebrando_ate = 0
        self.banco.salvar(self.rex)

    def tick(self):
        with self.lock:
            agora = time.monotonic()
            novo = copy.deepcopy(self.rex)
            # Pausa também durante suspensão prolongada do computador.
            novo.passar_tempo(min(agora - self.ultimo, 10))
            self.banco.salvar(novo)
            self.rex, self.ultimo = novo, agora

    def snapshot(self):
        with self.lock:
            return dict(cachorro=self.rex.publico(time.time()), momento=self.momentos.snapshot(self.rex), **self.banco.comunidade())

    def interagir(self, nome, comando, *, identidade=None, origem='simulador', recebido=None):
        if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 32 or any(ord(c) < 32 for c in nome):
            raise ValueError('Informe um nome de 1 a 32 caracteres.')
        if not isinstance(comando, str) or len(comando) > 30:
            raise ValueError('Comando inválido.')
        with self.lock:
            comando = comando_normalizado(comando).removeprefix('!')
            if origem == 'tiktok' and comando == 'dormir' and self.rex.dormindo:
                return dict(self.snapshot(), aplicada=False, motivo='Rex já está dormindo.')
            novo = copy.deepcopy(self.rex)
            agora = time.time()
            mensagem = novo.agir(comando, agora)
            efeitos = {key: round(getattr(novo, key) - getattr(self.rex, key), 1) for key in ('fome', 'vida', 'energia', 'felicidade')}
            aplicada = self.banco.salvar(novo, (nome.strip(), mensagem, agora), identidade=identidade, origem=origem, recebido=recebido, comando=comando, efeitos=efeitos)
            if aplicada:
                self.rex = novo
            return dict(self.snapshot(), aplicada=aplicada)

    def interagir_presente(self, nome, presente_id, nome_presente, *, identidade=None, origem='tiktok', recebido=None):
        if not isinstance(nome, str) or not 1 <= len(nome.strip()) <= 32 or any(ord(c) < 32 for c in nome):
            raise ValueError('Informe um nome de 1 a 32 caracteres.')
        if not isinstance(presente_id, str) or not presente_id:
            raise ValueError('ID do presente inválido.')
        if not isinstance(nome_presente, str) or not nome_presente:
            raise ValueError('Nome do presente inválido.')
        with self.lock:
            novo = copy.deepcopy(self.rex)
            agora = time.time()
            efeitos, mensagem = novo.aplicar_presente(presente_id, nome_presente, agora)
            if not efeitos:
                return dict(self.snapshot(), aplicada=False, motivo=mensagem)
            comando = f'presente:{nome_presente}'
            aplicada = self.banco.salvar(novo, (nome.strip(), mensagem, agora), identidade=identidade, origem=origem, recebido=recebido, comando=comando, efeitos=efeitos)
            if aplicada:
                self.rex = novo
            return dict(self.snapshot(), aplicada=aplicada)


def criar_servidor(jogo, porta=PORT, tiktok=None):
    from tiktok_live import TikTokBridge
    tiktok = tiktok or TikTokBridge(jogo)
    def estado():
        return dict(jogo.snapshot(), tiktok=tiktok.snapshot())
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def responder(self, status, data, tipo='application/json; charset=utf-8'):
            body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, dict) else data
            self.send_response(status)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def local(self):
            host = self.headers.get('Host', '')
            permitidos = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            origin = self.headers.get('Origin')
            return host in permitidos and (origin is None or origin in {'http://' + h for h in permitidos})

        def do_GET(self):
            if not self.local():
                return self.responder(403, {'erro': 'Acesso apenas local.'})
            rota = urlparse(self.path).path
            if rota == '/api/estado':
                return self.responder(200, estado())
            arquivos = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/script.js': ('script.js', 'text/javascript; charset=utf-8')}
            arquivos['/live-events.js'] = ('live-events.js', 'text/javascript; charset=utf-8')
            if rota not in arquivos:
                return self.responder(404, {'erro': 'Página não encontrada.'})
            arquivo, tipo = arquivos[rota]
            self.responder(200, (BASE_DIR / 'interface' / arquivo).read_bytes(), tipo)

        def do_POST(self):
            if not self.local():
                return self.responder(403, {'erro': 'Acesso apenas local.'})
            if self.path not in ('/api/acao', '/api/tiktok/conectar', '/api/tiktok/desconectar', '/api/momento/previa'):
                return self.responder(404, {'erro': 'Rota não encontrada.'})
            try:
                tamanho = int(self.headers.get('Content-Length', '0'))
                if not 0 < tamanho <= 2048:
                    raise ValueError('Requisição inválida.')
                dados = json.loads(self.rfile.read(tamanho))
                if not isinstance(dados, dict):
                    raise ValueError('Requisição inválida.')
                if self.path == '/api/momento/previa':
                    with jogo.lock:
                        jogo.momentos.previa()
                    resultado = estado()
                elif self.path == '/api/tiktok/conectar':
                    tiktok.conectar(dados.get('perfil'))
                    resultado = estado()
                elif self.path == '/api/tiktok/desconectar':
                    tiktok.desconectar()
                    resultado = estado()
                else:
                    resultado = dict(tiktok.simular(dados.get('nome'), dados.get('comando')), tiktok=tiktok.snapshot())
            except (ValueError, UnicodeDecodeError) as error:
                return self.responder(400, {'erro': str(error)})
            self.responder(200, resultado)
    servidor = ServidorLocal((HOST, porta), Handler)
    servidor.tiktok = tiktok
    return servidor


def main():
    parser = argparse.ArgumentParser(description='Rex Live — protótipo local')
    parser.add_argument('--port', type=int, default=PORT)
    parser.add_argument('--db', type=Path, default=DB_PATH)
    args = parser.parse_args()
    jogo = Jogo(args.db)
    servidor = criar_servidor(jogo, args.port)
    parar = threading.Event()
    def relogio():
        while not parar.wait(TICK_SECONDS):
            jogo.tick()
    worker = threading.Thread(target=relogio, daemon=True)
    worker.start()
    print(f'Rex Live em http://{HOST}:{servidor.server_port} — Ctrl+C para encerrar.', flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        parar.set()
        servidor.tiktok.desconectar()
        servidor.tiktok.aguardar(5)
        worker.join()
        servidor.server_close()


if __name__ == '__main__':
    main()
