"""
Telão do Castelo — troca de cenas pelo número de dedos mostrado à webcam.

    python main.py                 espetáculo (câmera + tela cheia)
    python main.py --janela        começa em janela
    python main.py --test-scenes   percorre as 5 cenas sozinho, sem câmera (só visuais genéricos)

Teclas: ESC/Q sair · F tela cheia · P canto da mini câmera · M mini câmera · L pontos da mão
        H esconde o HUD · 1-5 cenas · 0 espera · R reinicia cena · Enter final (cena 5)
        C troca câmera · S liga/desliga som
"""

import argparse
import os
import sys
import time

import pygame

from core.config import PASTA_PROJETO, carregar_config, carregar_falas
from core.effects import LARGURA, ALTURA
from core.text import texto

# =============================================================================
# GESTO -> CENA (edite aqui)
# =============================================================================
GESTO_PARA_CENA = {
    1: "cena1",   # Abertura do castelo
    2: "cena2",   # A porta do castelo
    3: "cena3",   # Cena do menino
    4: "cena4",   # Banho do ratinho
    5: "cena5",   # Finalização
    # "biceps": "cenaX",   # futuro: gesto de braço de força (MediaPipe Pose)
}
CENA_ESPERA = "espera"   # tela antes do primeiro gesto (tecla 0 volta para ela)

_app = None   # preenchido em main()


def on_gesture_change(numero):
    """Chamada SOMENTE quando o gesto estável muda (ou por uma tecla 1-5).
    Gesto 0 e mão ausente nunca chegam aqui: a cena atual continua."""
    cena = GESTO_PARA_CENA.get(numero)
    if cena is None or _app is None:
        return
    print(f"[gesto] {numero} -> {cena}")
    _app.cenas.ir_para(cena)

    # TODO (futuro) — ESP32: enviar o número/cena por Serial ou Wi-Fi, ex.:
    #   esp32.write(f"{numero}\n".encode())          # pyserial
    #   requests.post("http://esp32.local/cena", json={"cena": cena})

    # TODO (futuro) — Spike Prime (Pybricks): mandar o comando via Bluetooth (BLE), ex.:
    #   spike.enviar(numero)   # ver projeto Spiker-pybrinks

    # TODO (futuro) — Gesto de braço de força (bíceps) com MediaPipe Pose:
    #   1. em core/camera.py, rodar um PoseLandmarker no mesmo frame da mão;
    #   2. detectar o cotovelo dobrado com o punho acima do ombro;
    #   3. passar "biceps" pelo Estabilizador e chamar on_gesture_change("biceps");
    #   4. mapear "biceps" em GESTO_PARA_CENA acima.


# =============================================================================
# Aplicação
# =============================================================================

class Contexto:
    """Estado da detecção compartilhado com as cenas."""

    def __init__(self):
        self.dedos = None          # número bruto deste quadro (None = sem mão)
        self.mao = None            # objeto Mao (pontos, lado, dedos esticados)
        self.gesto_mantido = None  # número segurado de forma estável agora


def _dpi_windows():
    if os.name == "nt":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class App:
    def __init__(self, cfg, falas, modo_teste=False, tela_cheia=None):
        self.cfg, self.falas = cfg, falas
        self.modo_teste = modo_teste
        self.fps_alvo = int(cfg["video"]["fps_alvo"])
        self.escala_suave = bool(cfg["video"]["escala_suave"])
        self.tela_cheia = cfg["video"]["tela_cheia"] if tela_cheia is None else tela_cheia

        _dpi_windows()
        # A escala 1920x1080 -> tela é feita pela placa de vídeo (pygame.SCALED).
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "1" if self.escala_suave else "0"
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("Telão do Castelo")
        self._criar_janela()
        self._carregando("Carregando...")

        from core.assets import AssetManager
        from core.audio import Audio
        from core.gestures import Estabilizador
        from core.hud import Hud
        from scenes import TODAS_AS_CENAS, SceneManager

        self.audio = Audio(cfg["audio"])
        self.assets = AssetManager(os.path.join(PASTA_PROJETO, "assets"), self.audio, so_genericos=modo_teste)
        self.ctx = Contexto()
        self.hud = Hud(cfg["hud"])
        self.estab = Estabilizador(float(cfg["gestos"]["tempo_estavel"]), GESTO_PARA_CENA.keys())
        self.detector = None
        self.camera = None
        self.frame_camera = None
        self.indice_camera = int(cfg["camera"]["indice"])
        self.fps = 0.0
        if not modo_teste:   # a câmera abre em paralelo enquanto as cenas são geradas
            self._iniciar_camera()

        print("Gerando cenas e personagens...")
        self._carregando("Preparando o castelo...")
        inicio = time.perf_counter()
        self.cenas = SceneManager(self, TODAS_AS_CENAS, float(cfg["transicao"]["fade"]))
        self.cenas.aquecer(self.canvas)
        print(f"Cenas prontas em {time.perf_counter() - inicio:.1f}s.")
        self.cenas.ir_para(CENA_ESPERA)

    # ------------------------------------------------------------ janela
    def _criar_janela(self):
        """Tela lógica sempre 1920x1080; o SDL escala para o monitor (com barras pretas)."""
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.tela_cheia else pygame.RESIZABLE)
        try:
            pygame.display.set_mode((LARGURA, ALTURA), flags)
            self.escala_gpu = True
        except pygame.error as e:
            print(f"AVISO: escala por GPU indisponível ({e}); usando modo simples.")
            pygame.display.set_mode((LARGURA, ALTURA), pygame.FULLSCREEN if self.tela_cheia else 0)
            self.escala_gpu = False
        if not self.tela_cheia:
            self._tamanho_janela(1280, 720)
        pygame.mouse.set_visible(not self.tela_cheia)

    @staticmethod
    def _tamanho_janela(w, h):
        try:
            from pygame._sdl2.video import Window
            janela = Window.from_display_module()
            janela.size = (w, h)
            janela.position = pygame.WINDOWPOS_CENTERED
        except Exception:
            pass

    def alternar_tela_cheia(self):
        self.tela_cheia = not self.tela_cheia
        if self.escala_gpu:
            pygame.display.toggle_fullscreen()
            if not self.tela_cheia:
                self._tamanho_janela(1280, 720)
            pygame.mouse.set_visible(not self.tela_cheia)
        else:
            self._criar_janela()

    @property
    def canvas(self):
        """Superfície 1920x1080 onde tudo é desenhado."""
        return pygame.display.get_surface()

    def _carregando(self, msg):
        self.canvas.fill((5, 5, 16))
        s = texto(msg, 60, (230, 225, 255))
        self.canvas.blit(s, s.get_rect(center=(LARGURA // 2, ALTURA // 2)))
        self.apresentar()
        pygame.event.pump()

    def apresentar(self):
        pygame.display.flip()

    # ------------------------------------------------------------ câmera
    def _iniciar_camera(self):
        from core.camera import CameraWorker
        if self.detector is None:
            from core.hand_detector import DetectorDedos
            self._carregando("Carregando detector de mãos...")
            self.detector = DetectorDedos(self.cfg["gestos"])
        c = self.cfg["camera"]
        self.camera = CameraWorker(self.detector, self.indice_camera, c["largura"], c["altura"])
        self.camera.iniciar()

    def trocar_camera(self):
        if self.modo_teste:
            return
        if self.camera:
            self.camera.parar()
        self.indice_camera = (self.indice_camera + 1) % 4
        print(f"Trocando para a câmera {self.indice_camera}...")
        self.frame_camera = None
        self._iniciar_camera()

    def _ler_camera(self):
        if not self.camera:
            return
        self.frame_camera, mao = self.camera.ultimo()
        self.ctx.mao = mao
        self.ctx.dedos = mao.total if mao else None
        novo = self.estab.atualizar(self.ctx.dedos)
        self.ctx.gesto_mantido = self.estab.mantido()
        if novo is not None:
            on_gesture_change(novo)

    # ------------------------------------------------------------ teclado
    def tecla(self, k):
        """Retorna False para sair."""
        if k in (pygame.K_ESCAPE, pygame.K_q):
            return False
        if k == pygame.K_f:
            self.alternar_tela_cheia()
        elif k == pygame.K_p:
            print(f"Mini câmera: {self.hud.proximo_canto()}")
        elif k == pygame.K_m:
            self.hud.mini = not self.hud.mini
        elif k == pygame.K_l:
            self.hud.pontos = not self.hud.pontos
        elif k == pygame.K_h:
            self.hud.visivel = not self.hud.visivel
        elif k == pygame.K_c:
            self.trocar_camera()
        elif k == pygame.K_s:
            print(f"Som {'ligado' if self.audio.alternar_mudo() else 'mudo'}")
        elif k == pygame.K_r:
            self.cenas.reiniciar()
        elif self.cenas.on_key(k):
            pass   # a cena atual usou a tecla (ex.: Enter na cena 5, 2 na porta)
        elif k in (pygame.K_0, pygame.K_KP0):
            self.estab.forcar(None)
            self.cenas.ir_para(CENA_ESPERA)
        else:
            n = _numero_tecla(k)
            if n is not None:   # plano B: teclado no lugar da câmera
                self.estab.forcar(n)
                on_gesture_change(n)
        return True

    # ------------------------------------------------------------ laço principal
    def quadro(self, dt):
        self._ler_camera()
        self.cenas.update(dt)
        self.cenas.draw(self.canvas)

    def rodar(self):
        relogio = pygame.time.Clock()
        rodando = True
        while rodando:
            dt = min(relogio.tick(self.fps_alvo) / 1000.0, 0.1)
            self.fps = relogio.get_fps()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    rodando = False
                elif ev.type == pygame.KEYDOWN:
                    rodando = self.tecla(ev.key) and rodando
            self.quadro(dt)
            self.hud.draw(self.canvas, self)
            self.apresentar()

    def rodar_teste(self, duracao, pasta_capturas=None):
        """Percorre as cenas 1-5 sozinho (sem câmera) e mede o desempenho."""
        relogio = pygame.time.Clock()
        if pasta_capturas:
            os.makedirs(pasta_capturas, exist_ok=True)
        relatorio = []
        for numero, cena in GESTO_PARA_CENA.items():
            if not isinstance(numero, int):
                continue
            on_gesture_change(numero)
            self.ctx.gesto_mantido = numero   # simula o gesto segurado (abre a porta, etc.)
            self.ctx.dedos = numero
            decorrido, quadros, trabalho, pior = 0.0, 0, 0.0, 0.0
            while decorrido < duracao:
                dt = min(relogio.tick(self.fps_alvo) / 1000.0, 0.1)
                self.fps = relogio.get_fps()
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_q)):
                        return relatorio
                    if ev.type == pygame.KEYDOWN:
                        self.tecla(ev.key)
                ini = time.perf_counter()
                self.cenas.update(dt)
                self.cenas.draw(self.canvas)
                if pasta_capturas and decorrido + dt >= duracao:
                    pygame.image.save(self.canvas, os.path.join(pasta_capturas, f"{cena}.png"))
                self.hud.draw(self.canvas, self)
                self.apresentar()
                ms = (time.perf_counter() - ini) * 1000
                if quadros > 3:   # ignora os primeiros quadros (fade/aquecimento)
                    trabalho += ms
                    pior = max(pior, ms)
                decorrido += dt
                quadros += 1
            media = trabalho / max(1, quadros - 4)
            relatorio.append((cena, quadros / duracao, media, pior))
            print(f"[teste] {cena}: {quadros / duracao:5.1f} FPS · {media:5.1f} ms/quadro (pior {pior:5.1f} ms)")
        return relatorio

    def fechar(self):
        if self.camera:
            self.camera.parar()
        if self.detector:
            self.detector.fechar()
        pygame.quit()


def _numero_tecla(k):
    for n in range(1, 6):
        if k in (getattr(pygame, f"K_{n}"), getattr(pygame, f"K_KP{n}")):
            return n
    return None


def main():
    global _app
    p = argparse.ArgumentParser(description="Telão do Castelo controlado por gestos")
    p.add_argument("--test-scenes", action="store_true", help="percorre as 5 cenas sem câmera")
    p.add_argument("--duracao", type=float, default=None, help="segundos por cena no --test-scenes")
    p.add_argument("--capturas", default=None, help="pasta para salvar um PNG de cada cena no teste")
    p.add_argument("--janela", action="store_true", help="começa em janela (não tela cheia)")
    p.add_argument("--config", default=None, help="caminho de outro config.yaml")
    args = p.parse_args()

    cfg = carregar_config(args.config)
    falas = carregar_falas()
    _app = App(cfg, falas, modo_teste=args.test_scenes, tela_cheia=False if args.janela else None)
    try:
        if args.test_scenes:
            duracao = args.duracao or float(cfg["teste"]["duracao_cena"])
            relatorio = _app.rodar_teste(duracao, args.capturas)
            ok = len(relatorio) == 5
            print("[teste] OK: as 5 cenas rodaram." if ok else "[teste] interrompido.")
            return 0 if ok else 1
        _app.rodar()
        return 0
    finally:
        _app.fechar()


if __name__ == "__main__":
    sys.exit(main())
