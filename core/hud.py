"""HUD do operador: mini câmera, número detectado, status e avisos. Tecla H esconde tudo."""

import cv2
import pygame

from core.effects import LARGURA, ALTURA
from core.hand_detector import CONEXOES, PONTAS
from core.text import texto

CANTOS = ["superior esquerdo", "superior direito", "inferior direito", "inferior esquerdo"]
MARGEM = 24


class Hud:
    def __init__(self, cfg_hud):
        self.visivel = bool(cfg_hud["mostrar"])
        self.mini = True
        self.pontos = True
        self.canto = int(cfg_hud["canto_mini_camera"]) % 4
        self.fracao = float(cfg_hud["fracao_mini_camera"])
        self._faixa = None

    def proximo_canto(self):
        self.canto = (self.canto + 1) % 4
        return CANTOS[self.canto]

    def draw(self, frame, app):
        if not self.visivel:
            return
        mw = int(LARGURA * self.fracao)
        mh = int(mw * 3 / 4)
        esquerda, topo = self.canto in (0, 3), self.canto in (0, 1)
        mx = MARGEM if esquerda else LARGURA - mw - MARGEM
        my = MARGEM if topo else ALTURA - mh - MARGEM
        if self.mini:
            self._mini_camera(frame, app, pygame.Rect(mx, my, mw, mh))
        self._numero(frame, app, mx, my, mw, mh, topo)
        self._status(frame, app, esquerda)

    # ------------------------------------------------------------ mini câmera
    def _mini_camera(self, frame, app, r):
        quadro, mao = app.frame_camera, app.ctx.mao
        if quadro is None:
            pygame.draw.rect(frame, (25, 25, 32), r)
            if app.modo_teste:
                msg = "MODO TESTE (sem câmera)"
            elif app.camera and (app.camera.abrindo or app.camera.ok):
                msg = "Iniciando câmera..."
            else:
                msg = "SEM CÂMERA"
            frame.blit(texto(msg, 34, (255, 90, 90), esp=2, sombra=False), (r.x + 20, r.centery - 40))
            frame.blit(texto("C = trocar câmera · 1-5 = cenas", 22, esp=2, sombra=False), (r.x + 20, r.centery + 10))
        else:
            img = cv2.cvtColor(cv2.resize(quadro, (r.w, r.h)), cv2.COLOR_BGR2RGB)
            mini = pygame.image.frombuffer(img.tobytes(), (r.w, r.h), "RGB")
            if mao is not None and self.pontos:
                self._desenhar_mao(mini, mao)
            frame.blit(mini, r)
            if self._faixa is None or self._faixa.get_width() != r.w:
                self._faixa = pygame.Surface((r.w, 44), pygame.SRCALPHA)
                self._faixa.fill((0, 0, 0, 140))
            frame.blit(self._faixa, r.topleft)
            info = f"{mao.total} dedo(s) · mão {mao.lado.lower()}" if mao else "nenhuma mão"
            frame.blit(texto(info, 26, esp=2, sombra=False), (r.x + 10, r.y + 6))
        frame.blit(texto(f"cam {app.indice_camera}", 18, (200, 200, 200), esp=2, sombra=False),
                   (r.x + 8, r.bottom - 28))
        pygame.draw.rect(frame, (240, 240, 240), r.inflate(4, 4), 2)

    @staticmethod
    def _desenhar_mao(surf, mao):
        w, h = surf.get_size()
        px = [(int(x * w), int(y * h)) for x, y in mao.pontos]
        for a, b in CONEXOES:
            pygame.draw.line(surf, (255, 255, 255), px[a], px[b], 2)
        for p in px:
            pygame.draw.circle(surf, (255, 200, 0), p, 3)
        for esticado, idx in zip(mao.esticados, PONTAS):
            cor = (0, 230, 0) if esticado else (240, 40, 40)   # verde esticado, vermelho dobrado
            pygame.draw.circle(surf, cor, px[idx], 9)
            pygame.draw.circle(surf, (0, 0, 0), px[idx], 9, 2)

    # ------------------------------------------------------------ número grande
    def _numero(self, frame, app, mx, my, mw, mh, topo):
        """Painel com o número detectado agora e a barra de estabilidade (anti-flicker)."""
        n = app.ctx.dedos
        alt = 200
        if self.mini:
            y = my + mh + 10 if topo else my - alt - 10
        else:
            y = MARGEM if topo else ALTURA - alt - MARGEM
        painel = pygame.Rect(mx, y, mw, alt)
        _painel(frame, painel)
        if n is None:
            s = texto("sem mão", 56, (200, 200, 210), esp=3)
            frame.blit(s, s.get_rect(center=(painel.centerx, painel.y + 80)))
        else:
            num = texto(str(n), 140, (255, 255, 255), esp=6)
            rot = texto("dedo" if n == 1 else "dedos", 34, (220, 220, 220), esp=3)
            larg = num.get_width() + 10 + rot.get_width()
            x0 = painel.centerx - larg // 2
            frame.blit(num, num.get_rect(midleft=(x0, painel.y + 82)))
            frame.blit(rot, rot.get_rect(midleft=(x0 + num.get_width() + 10, painel.y + 100)))
        prog = app.estab.progresso() if app.estab else 0.0
        barra = pygame.Rect(painel.x + 30, painel.bottom - 34, painel.w - 60, 12)
        pygame.draw.rect(frame, (70, 70, 80), barra, border_radius=6)
        if prog > 0:
            cheia = barra.copy()
            cheia.w = max(1, int(barra.w * prog))
            pygame.draw.rect(frame, (0, 220, 120) if prog >= 1 else (255, 200, 60), cheia, border_radius=6)

    # ------------------------------------------------------------ status
    def _status(self, frame, app, mini_esquerda):
        cena = app.cenas.atual
        if app.modo_teste:
            cam = "teste"
        elif app.camera and app.camera.abrindo:
            cam = "abrindo..."
        else:
            cam = "OK" if app.camera and app.camera.ok else "SEM SINAL"
        linhas = [
            (f"Cena: {app.cenas.nome_atual} — {cena.titulo if cena else ''}", 26, (255, 255, 255)),
            (f"FPS {app.fps:.0f}  ·  câmera {app.indice_camera} {cam}  ·  som {'ligado' if app.audio.ativo else 'mudo'}",
             22, (230, 230, 240)),
            (f"ESP32 pilar: {app.esp32.status}"
             + (f"  ·  {app.esp32.angulo_enviado}°" if app.esp32.angulo_enviado is not None else ""),
             22, (130, 230, 160) if app.esp32.status == "conectado" else (230, 190, 120)),
            ("H esconde HUD · 1-5 cenas · 0 espera · R reinicia · Enter final", 18, (190, 190, 205)),
            ("C câmera · S som · F tela cheia · P canto · M mini câmera · L pontos", 18, (190, 190, 205)),
        ]
        surfs = [texto(t, tam, cor, esp=0, sombra=False) for t, tam, cor in linhas]
        w = max(s.get_width() for s in surfs) + 28
        h = sum(s.get_height() + 2 for s in surfs) + 20
        painel = pygame.Rect(0, MARGEM, w, h)
        if mini_esquerda:
            painel.right = LARGURA - MARGEM
        else:
            painel.left = MARGEM
        _painel(frame, painel)
        y = painel.y + 10
        for s in surfs:
            frame.blit(s, (painel.x + 14, y))
            y += s.get_height() + 2
        aviso = cena.assets.aviso if cena and cena.nome != "espera" else ""
        if aviso:   # aviso discreto: a cena está usando visual/som genérico
            s = texto(f"assets/{cena.nome}: {aviso}", 18, (180, 180, 190), esp=0, sombra=False)
            r = s.get_rect().inflate(20, 10)
            if mini_esquerda:
                r.bottomright = (LARGURA - MARGEM, ALTURA - 8)
            else:
                r.bottomleft = (MARGEM, ALTURA - 8)
            _painel(frame, r, 120)
            frame.blit(s, s.get_rect(center=r.center))


_paineis = {}


def _painel(frame, rect, alpha=150):
    """Fundo escuro translúcido com cantos arredondados (com cache por tamanho)."""
    chave = (rect.w, rect.h, alpha)
    if chave not in _paineis:
        p = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(p, (10, 8, 20, alpha), p.get_rect(), border_radius=14)
        _paineis[chave] = p.convert_alpha()
    frame.blit(_paineis[chave], rect.topleft)
