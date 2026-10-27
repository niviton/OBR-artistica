"""Arte genérica ORIGINAL desenhada por código (usada quando faltam arquivos em assets/).

Estilo cartoon: formas arredondadas, contorno escuro grosso, cores vivas, sombras suaves
e olhos expressivos. Os personagens são criações próprias deste projeto.

Personagens — todos recebem o tempo `t` (s) e o `estado` e devolvem uma Surface
com fundo transparente (a base dos pés fica embaixo, no centro):
    draw_generic_mouse()        ratinho com bandeirinha (cena 1)
    draw_generic_gatekeeper()   porteiro de boné e bigode (cena 2)
    draw_generic_boy()          menino de cabelo espetado (cenas 3 e 5)
    draw_generic_bath_mouse()   ratinho de touca na banheira com patinho (cena 4)

Cenários — gerados uma vez e guardados em cache (lru_cache).
"""

import math
import random
from functools import lru_cache

import numpy as np
import pygame
from pygame import gfxdraw

from core.effects import (LARGURA, ALTURA, brilho_aditivo, desfocar, gradiente_vertical,
                          superficie_rgba, vinheta, _distancia)

PARADO, ANDANDO, FALANDO, COMEMORANDO = "parado", "andando", "falando", "comemorando"
CONTORNO = (34, 24, 38)
DOURADO = (240, 190, 60)


# =============================================================================
# Pincel com antialiasing (pygame.gfxdraw). Coordenadas em "unidades do desenho",
# multiplicadas por k. ss > 1 desenha maior e reduz (só para arte gerada uma vez).
# =============================================================================

def _pts_retangulo(x, y, w, h, r, n=6):
    r = min(r, w / 2, h / 2)
    if r <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    pts = []
    for cx, cy, a0 in ((x + w - r, y + r, -90), (x + w - r, y + h - r, 0), (x + r, y + h - r, 90), (x + r, y + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


# Cor "transparente" dos personagens. É quase igual ao contorno: assim o antialiasing
# da borda externa mistura contorno com contorno e não aparece franja colorida.
CHAVE = (35, 25, 40)


class _Tela:
    """ss == 1: superfície opaca com colorkey + gfxdraw (antialiasing rápido).
    ss > 1: superfície com alpha desenhada maior e reduzida (para arte gerada uma vez).
    (gfxdraw em superfícies SRCALPHA estraga o alpha dos pixels — por isso o colorkey.)"""

    def __init__(self, w, h, escala=1.0, ss=1, contorno=5):
        self.escala, self.ss = escala, ss
        self.k = escala * ss
        self.w, self.h = max(1, round(w * escala)), max(1, round(h * escala))
        tam = (max(1, round(w * self.k)), max(1, round(h * self.k)))
        self.aa = ss == 1
        if self.aa:
            self.s = pygame.Surface(tam)
            self.s.fill(CHAVE)
            self.s.set_colorkey(CHAVE)
        else:
            self.s = pygame.Surface(tam, pygame.SRCALPHA)
        self.o = contorno
        self._sombras = []

    def _ret(self, x, y, w, h):
        k = self.k
        return pygame.Rect(round(x * k), round(y * k), max(1, round(w * k)), max(1, round(h * k)))

    def _esp(self, esp):
        return self.o if esp is None else esp

    # primitivas em pixels
    def _elipse_px(self, cor, cx, cy, rx, ry):
        a, b = round(rx), round(ry)
        if a < 1 or b < 1:
            return
        x, y = round(cx), round(cy)
        if self.aa:
            gfxdraw.filled_ellipse(self.s, x, y, a, b, cor)
            gfxdraw.aaellipse(self.s, x, y, a, b, cor)
        else:
            pygame.draw.ellipse(self.s, cor, (x - a, y - b, 2 * a, 2 * b))

    def _poli_px(self, cor, pts):
        if len(pts) < 3:
            return
        p = [(round(x), round(y)) for x, y in pts]
        pygame.draw.polygon(self.s, cor, p)
        if self.aa:
            gfxdraw.aapolygon(self.s, p, cor)

    def elipse(self, cor, cx, cy, rx, ry, contorno=True, esp=None):
        k = self.k
        if contorno:
            o = self._esp(esp)
            self._elipse_px(CONTORNO, cx * k, cy * k, (rx + o) * k, (ry + o) * k)
        self._elipse_px(cor, cx * k, cy * k, rx * k, ry * k)

    def circulo(self, cor, cx, cy, r, contorno=True, esp=None):
        self.elipse(cor, cx, cy, r, r, contorno, esp)

    def retangulo(self, cor, x, y, w, h, raio=0, contorno=True, esp=None):
        k = self.k
        if contorno:
            o = self._esp(esp)
            pts = _pts_retangulo(x - o, y - o, w + 2 * o, h + 2 * o, raio + o if raio else 0)
            self._poli_px(CONTORNO, [(px * k, py * k) for px, py in pts])
        self._poli_px(cor, [(px * k, py * k) for px, py in _pts_retangulo(x, y, w, h, raio)])

    def _traco(self, cor, a, b, larg):
        k = self.k
        x1, y1, x2, y2 = a[0] * k, a[1] * k, b[0] * k, b[1] * k
        r = larg * k / 2
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        if d > 0.01:
            nx, ny = -dy / d * r, dx / d * r
            self._poli_px(cor, [(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)])
        self._elipse_px(cor, x1, y1, r, r)
        self._elipse_px(cor, x2, y2, r, r)

    def linha(self, cor, a, b, larg, contorno=True, esp=None):
        if contorno:
            self._traco(CONTORNO, a, b, larg + 2 * self._esp(esp))
        self._traco(cor, a, b, larg)

    def curva(self, cor, pts, larg, contorno=True, esp=None):
        if contorno:
            for a, b in zip(pts, pts[1:]):
                self._traco(CONTORNO, a, b, larg + 2 * self._esp(esp))
        for a, b in zip(pts, pts[1:]):
            self._traco(cor, a, b, larg)

    def poligono(self, cor, pts, contorno=True, esp=None):
        k = self.k
        if contorno:
            o = self._esp(esp)
            for a, b in zip(pts, pts[1:] + pts[:1]):
                self._traco(CONTORNO, a, b, 2 * o)
        self._poli_px(cor, [(x * k, y * k) for x, y in pts])

    def sombra(self, cx, cy, rx, ry, alpha=70):
        """Sombra suave no chão (aplicada em final(), por baixo do desenho)."""
        self._sombras.append((cx, cy, rx, ry, alpha))

    def colar(self, surf, cx, cy):
        self.s.blit(surf, surf.get_rect(center=(round(cx * self.k), round(cy * self.k))))

    def final(self):
        """Surface com alpha: sombras suaves + desenho."""
        if self.aa:
            out = pygame.Surface(self.s.get_size(), pygame.SRCALPHA)
        else:
            out = self.s
        for cx, cy, rx, ry, alpha in self._sombras:
            for f, a in ((1.0, 0.45), (0.8, 0.7), (0.6, 1.0)):
                r = self._ret(cx - rx * f, cy - ry * f, 2 * rx * f, 2 * ry * f)
                pygame.draw.ellipse(out, (0, 0, 0, int(alpha * a)), r)
        if self.aa:
            out.blit(self.s, (0, 0))
            return out
        return pygame.transform.smoothscale(self.s, (self.w, self.h))


def _piscando(t, periodo=3.7, fase=0.0, dur=0.13):
    return (t + fase) % periodo < dur


def _olho(c, x, y, rx, ry, olhar=(0.0, 0.0), pisca=False, feliz=False):
    if feliz:  # olhinhos fechados de alegria: ^ ^
        c.curva(CONTORNO, [(x - rx, y + 3), (x, y - ry * 0.55), (x + rx, y + 3)], 4.5, contorno=False)
        return
    if pisca:
        c.curva(CONTORNO, [(x - rx, y), (x, y + ry * 0.25), (x + rx, y)], 4, contorno=False)
        return
    c.elipse((255, 255, 255), x, y, rx, ry, esp=3)
    px, py = x + olhar[0] * rx * 0.35, y + olhar[1] * ry * 0.3 + ry * 0.1
    c.elipse((40, 30, 45), px, py, rx * 0.6, ry * 0.62, contorno=False)
    c.circulo((255, 255, 255), px + rx * 0.22, py - ry * 0.25, rx * 0.22, contorno=False)


def _boca(c, x, y, larg, estado, t):
    if estado == FALANDO:
        abre = 0.3 + 0.7 * abs(math.sin(t * 13))
        c.elipse((150, 40, 60), x, y + 4, larg * 0.42, 3 + 9 * abre, esp=3)
        c.elipse((240, 110, 130), x, y + 5 + 5 * abre, larg * 0.22, 1 + 3 * abre, contorno=False)
    elif estado == COMEMORANDO:
        pts = [(x + math.cos(a) * larg * 0.55, y + math.sin(a) * larg * 0.5)
               for a in np.linspace(0, math.pi, 12)]
        c.poligono((150, 40, 60), [(x + larg * 0.55, y)] + pts + [(x - larg * 0.55, y)], esp=3)
        c.elipse((240, 110, 130), x, y + larg * 0.32, larg * 0.25, larg * 0.12, contorno=False)
    else:
        pts = [(x + (i / 6 - 0.5) * larg, y + math.sin(i / 6 * math.pi) * larg * 0.22) for i in range(7)]
        c.curva(CONTORNO, pts, 4, contorno=False)


def _ponto_braco(ombro, ang, comp):
    """ang = 0 aponta para baixo; positivo gira para a direita/frente."""
    return (ombro[0] + math.sin(ang) * comp, ombro[1] + math.cos(ang) * comp)


# =============================================================================
# Ratinho (cena 1)
# =============================================================================

PELO_RATO = (178, 170, 196)
BARRIGA_RATO = (238, 230, 244)
FOCINHO_RATO = (222, 214, 236)
ORELHA_RATO = (255, 172, 192)
NARIZ_RATO = (255, 118, 150)
BOCHECHA = (255, 168, 178)
CAUDA_RATO = (240, 160, 178)
LENCO = (235, 70, 80)
TOUCA = (255, 140, 180)


def _cabeca_rato(c, cx, cy, t, estado, touca=False, olhar=(0.3, 0.0)):
    if touca:
        for sx in (-1, 1):
            c.circulo(PELO_RATO, cx + sx * 58, cy - 4, 22)
            c.circulo(ORELHA_RATO, cx + sx * 58, cy - 4, 12, contorno=False)
    else:
        for sx in (-1, 1):
            c.circulo(PELO_RATO, cx + sx * 46, cy - 40, 32)
            c.circulo(ORELHA_RATO, cx + sx * 46, cy - 40, 19, contorno=False)
    c.elipse(PELO_RATO, cx, cy, 56, 50)
    if touca:  # touca de banho no alto da cabeça, deixando os olhos livres
        c.elipse(TOUCA, cx, cy - 42, 60, 30)
        for dx, dy in ((-32, -52), (0, -62), (30, -54), (-12, -38), (16, -40), (44, -38), (-44, -36)):
            c.circulo((255, 255, 255), cx + dx, cy + dy, 5, contorno=False)
        for i in range(9):
            c.circulo(TOUCA, cx - 58 + i * 14.5, cy - 22 + (3 if i % 2 else 0), 7, esp=3)
    c.elipse(FOCINHO_RATO, cx, cy + 20, 30, 20, contorno=False)
    pisca = _piscando(t)
    feliz = estado == COMEMORANDO
    _olho(c, cx - 20, cy + 2, 11, 15, olhar, pisca, feliz)
    _olho(c, cx + 20, cy + 2, 11, 15, olhar, pisca, feliz)
    c.circulo(BOCHECHA, cx - 38, cy + 18, 8, contorno=False)
    c.circulo(BOCHECHA, cx + 38, cy + 18, 8, contorno=False)
    for sx in (-1, 1):
        for dy in (-4, 4):
            c.curva(CONTORNO, [(cx + sx * 24, cy + 18 + dy * 0.5), (cx + sx * 54, cy + 14 + dy * 2)], 2, contorno=False)
    c.elipse(NARIZ_RATO, cx, cy + 13, 9, 7, esp=3)
    _boca(c, cx, cy + 27, 22, estado, t)
    if estado not in (FALANDO, COMEMORANDO):
        c.retangulo((255, 255, 255), cx - 5, cy + 28, 10, 7, raio=2, esp=2)


def draw_generic_mouse(t, estado=PARADO, altura=300):
    W, H = 300, 340
    c = _Tela(W, H, altura / H)
    andando = estado == ANDANDO
    passo = t * 9
    if andando:
        pulo = abs(math.sin(passo)) * 8
    elif estado == COMEMORANDO:
        pulo = abs(math.sin(t * 5)) * 20
    else:
        pulo = 0
    y0 = -pulo
    resp = math.sin(t * 2.4)
    c.sombra(140, 326, 72 - pulo * 0.8, 10)
    bal = math.sin(t * 3.2)
    c.curva(CAUDA_RATO, [(92, 262 + y0), (55, 272 + y0), (30, 252 + y0),
                         (24 + bal * 6, 216 + y0), (40 + bal * 12, 190 + y0)], 9)
    pe = math.sin(passo) * 16 if andando else 0
    c.elipse(ORELHA_RATO, 112 + pe, 316, 26, 12)
    c.elipse(ORELHA_RATO, 168 - pe, 316, 26, 12)
    ry = 64 * (1 + 0.025 * resp)
    c.elipse(PELO_RATO, 140, 250 + y0 - (ry - 64), 60, ry)
    c.elipse(BARRIGA_RATO, 140, 264 + y0, 38, 40, contorno=False)
    c.elipse(LENCO, 140, 196 + y0, 44, 13)
    # braço livre
    a = (-0.35 + math.sin(passo) * 0.5) if andando else (-0.25 + math.sin(t * 1.7) * 0.08)
    ombro = (98, 222 + y0)
    mao = _ponto_braco(ombro, a, 48)
    c.linha(PELO_RATO, ombro, mao, 18)
    c.circulo(PELO_RATO, mao[0], mao[1], 11)
    _cabeca_rato(c, 140, 130 + y0, t, estado)
    # braço com a bandeirinha
    a = 2.2 + (math.sin(t * 4) * 0.25 if not andando else math.sin(passo) * 0.08)
    ombro = (182, 222 + y0)
    mao = _ponto_braco(ombro, a, 46)
    topo = mao[1] - 112
    c.linha((150, 100, 60), (mao[0] - 2, mao[1] + 26), (mao[0] + 3, topo), 6)
    onda = math.sin(t * 7) * 6
    flag = [(mao[0] + 3, topo), (mao[0] + 36, topo + 8 + onda * 0.5),
            (mao[0] + 66, topo + 18 + onda), (mao[0] + 3, topo + 40)]
    c.poligono((255, 90, 80), flag)
    c.poligono((255, 210, 60), [(mao[0] + 3, topo + 14), (mao[0] + 40, topo + 20 + onda * 0.6),
                                (mao[0] + 3, topo + 27)], contorno=False)
    c.linha(PELO_RATO, ombro, mao, 18)
    c.circulo(PELO_RATO, mao[0], mao[1], 11)
    return c.final()


# =============================================================================
# Porteiro (cena 2)
# =============================================================================

UNIFORME = (48, 80, 158)
UNIFORME_ESC = (32, 55, 115)
PELE = (246, 196, 160)
PELE_ESC = (226, 164, 128)
BIGODE = (98, 62, 40)
SAPATO = (40, 35, 42)
CALCA = (36, 46, 92)


def _cabeca_porteiro(c, cx, cy, t, estado):
    for sx in (-1, 1):
        c.circulo(PELE, cx + sx * 52, cy + 4, 13)
    c.elipse(PELE, cx, cy, 52, 56)
    pisca = _piscando(t, 4.1, 0.7)
    feliz = estado == COMEMORANDO
    _olho(c, cx - 12, cy - 2, 9, 11, (0.9, 0.0), pisca, feliz)
    _olho(c, cx + 24, cy - 2, 9, 11, (0.9, 0.0), pisca, feliz)
    c.curva(BIGODE, [(cx - 25, cy - 18), (cx - 4, cy - 22)], 6, contorno=False)
    c.curva(BIGODE, [(cx + 14, cy - 22), (cx + 35, cy - 18)], 6, contorno=False)
    c.elipse(PELE_ESC, cx + 10, cy + 14, 13, 11, esp=3)
    if estado == FALANDO:
        c.elipse((150, 40, 60), cx + 10, cy + 46, 9, 3 + 6 * abs(math.sin(t * 12)), esp=2)
    elif feliz:
        c.elipse((150, 40, 60), cx + 10, cy + 44, 12, 9, esp=2)
    mexe = math.sin(t * 2.5) * 2
    c.elipse(BIGODE, cx - 6, cy + 31 + mexe * 0.3, 22, 10, esp=3)
    c.elipse(BIGODE, cx + 26, cy + 31 - mexe * 0.3, 22, 10, esp=3)
    c.circulo(BIGODE, cx - 28, cy + 26 - mexe, 7, esp=3)
    c.circulo(BIGODE, cx + 48, cy + 26 + mexe, 7, esp=3)
    # boné
    c.elipse(UNIFORME, cx, cy - 66, 54, 22)
    c.retangulo(UNIFORME, cx - 50, cy - 70, 100, 36, raio=12)
    c.retangulo(UNIFORME_ESC, cx - 53, cy - 42, 106, 14, raio=5, esp=3)
    c.elipse((25, 30, 52), cx + 22, cy - 28, 46, 10, esp=3)
    c.circulo(DOURADO, cx, cy - 56, 9, esp=2)


def draw_generic_gatekeeper(t, estado=PARADO, altura=480, olhar=1):
    """`olhar` = 1 olha para a direita, -1 para a esquerda."""
    W, H = 360, 500   # largura extra para o braço esticado
    c = _Tela(W, H, altura / H)
    resp = math.sin(t * 2)
    c.sombra(160, 486, 92, 12)
    c.retangulo(CALCA, 118, 360, 36, 112, raio=10)
    c.retangulo(CALCA, 166, 360, 36, 112, raio=10)
    c.elipse(SAPATO, 134, 476, 32, 13)
    c.elipse(SAPATO, 190, 476, 32, 13)
    ty = 232 - resp * 2
    # braço de trás
    ombro = (100, ty + 22)
    mao = _ponto_braco(ombro, -0.15 + math.sin(t * 1.3) * 0.05, 95)
    c.linha(UNIFORME, ombro, mao, 30)
    c.circulo(PELE, mao[0], mao[1], 16)
    # tronco
    c.retangulo(UNIFORME, 92, ty, 136, 150, raio=34)
    c.poligono(UNIFORME_ESC, [(128, ty + 4), (160, ty + 60), (192, ty + 4)], esp=3)
    c.poligono((205, 45, 55), [(153, ty + 8), (167, ty + 8), (165, ty + 48), (160, ty + 58), (155, ty + 48)], esp=2)
    for i in range(3):
        c.circulo(DOURADO, 160, ty + 76 + i * 22, 6, esp=2)
    c.retangulo((70, 45, 32), 92, ty + 122, 136, 15, contorno=False)
    c.retangulo(DOURADO, 150, ty + 120, 20, 19, raio=3, esp=2)
    c.retangulo(DOURADO, 84, ty + 2, 36, 12, raio=5, esp=2)
    c.retangulo(DOURADO, 200, ty + 2, 36, 12, raio=5, esp=2)
    # pescoço + cabeça (balançando)
    c.retangulo(PELE_ESC, 145, ty - 22, 30, 30, contorno=False)
    cab = _Tela(180, 200, c.escala, c.ss, c.o)
    _cabeca_porteiro(cab, 90, 112, t, estado)
    ang = math.sin(t * 1.6) * 7
    c.colar(pygame.transform.rotozoom(cab.final(), ang, 1.0), 160, ty - 84)
    # braço da frente (aponta para a porta ao falar, acena ao comemorar)
    if estado == FALANDO:
        a = 1.9 + math.sin(t * 3) * 0.12
    elif estado == COMEMORANDO:   # acena para o alto, longe do rosto
        a = 2.35 + math.sin(t * 8) * 0.25
    else:
        a = 0.15 + math.sin(t * 1.3 + 1) * 0.05
    ombro = (220, ty + 22)
    mao = _ponto_braco(ombro, a, 95)
    c.linha(UNIFORME, ombro, mao, 30)
    c.circulo(PELE, mao[0], mao[1], 16)
    s = c.final()
    return pygame.transform.flip(s, True, False) if olhar < 0 else s


# =============================================================================
# Menino (cenas 3 e 5)
# =============================================================================

PELE_MENINO = (250, 206, 170)
CABELO = (150, 82, 40)
CAMISA = (255, 206, 62)
LISTRA1 = (240, 110, 60)
LISTRA2 = (60, 180, 140)
BERMUDA = (62, 112, 205)
TENIS = (232, 62, 72)


def draw_generic_boy(t, estado=PARADO, altura=480):
    """Estados: parado, andando (entrada), falando (acena e fala), comemorando (pula)."""
    W, H = 340, 520
    c = _Tela(W, H, altura / H)
    cx = 170
    andando, comem = estado == ANDANDO, estado == COMEMORANDO
    passo = t * 8
    pulo = abs(math.sin(passo)) * 10 if andando else abs(math.sin(t * 5.5)) * 40 if comem else 0
    y0 = -pulo
    resp = math.sin(t * 2.2)
    c.sombra(cx, 504, 80 * (1 - pulo / 120), 12)
    # pernas
    s = math.sin(passo) * 0.5 if andando else 0
    abre = 0.25 if comem else 0.06
    for lado, ang in ((-1, -abre + s), (1, abre - s)):
        quadril = (cx + lado * 20, 380 + y0)
        pe = _ponto_braco(quadril, ang, 100)
        c.linha(PELE_MENINO, quadril, pe, 24)
        c.retangulo((255, 255, 255), pe[0] - 13, pe[1] - 16, 26, 12, raio=4, esp=3)
        c.elipse(TENIS, pe[0] + lado * 6, pe[1] + 6, 26, 13)
    c.retangulo(BERMUDA, 128, 350 + y0, 84, 52, raio=14)
    # tronco listrado
    c.retangulo(CAMISA, 116, 240 + y0 - resp * 1.5, 108, 125, raio=30)
    for i, yy in enumerate((276, 300, 324)):
        c.retangulo(LISTRA1 if i % 2 == 0 else LISTRA2, 121, yy + y0, 98, 12, contorno=False)
    # braços
    if andando:   # braços balançam para fora, um de cada vez
        aE = -0.3 - 0.25 * (1 + math.sin(passo)) / 2
        aD = 0.3 + 0.25 * (1 - math.sin(passo)) / 2
    elif estado == FALANDO:   # acena com a mão direita, longe do rosto
        aE, aD = -0.2 + math.sin(t * 2) * 0.05, 2.2 + math.sin(t * 7) * 0.3
    elif comem:   # braços para o alto em "V"
        aE, aD = -2.35 + math.sin(t * 9) * 0.2, 2.35 - math.sin(t * 9) * 0.2
    else:
        aE, aD = -0.15, 0.15 + math.sin(t * 1.5) * 0.04
    for ombro, ang in (((122, 262 + y0), aE), ((218, 262 + y0), aD)):
        mao = _ponto_braco(ombro, ang, 88)
        manga = _ponto_braco(ombro, ang, 30)
        c.linha(PELE_MENINO, ombro, mao, 20)
        c.linha(CAMISA, ombro, manga, 28)
        c.circulo(PELE_MENINO, mao[0], mao[1], 15)
    # cabeça
    hy = 165 + y0
    pts = []
    for i in range(13):
        ang = math.pi + i * math.pi / 12
        r = (92 if i % 2 else 52) + math.sin(t * 3 + i) * 3
        pts.append((cx + math.cos(ang) * r, hy - 6 + math.sin(ang) * r))
    c.poligono(CABELO, pts)
    for sx in (-1, 1):
        c.circulo(PELE_MENINO, cx + sx * 58, hy + 8, 14)
    c.circulo(PELE_MENINO, cx, hy, 60)
    c.poligono(CABELO, [(cx - 57, hy - 16), (cx - 42, hy - 52), (cx, hy - 62), (cx + 42, hy - 52),
                        (cx + 57, hy - 16), (cx + 32, hy - 30), (cx + 14, hy - 14), (cx - 4, hy - 32),
                        (cx - 24, hy - 16), (cx - 38, hy - 30)])
    pisca = _piscando(t, 3.3, 1.1)
    _olho(c, cx - 22, hy + 6, 12, 15, (0.15, 0.0), pisca, comem)
    _olho(c, cx + 22, hy + 6, 12, 15, (0.15, 0.0), pisca, comem)
    sob = -4 if comem else 0
    c.curva(CABELO, [(cx - 34, hy - 13 + sob), (cx - 12, hy - 17 + sob)], 5, contorno=False)
    c.curva(CABELO, [(cx + 12, hy - 17 + sob), (cx + 34, hy - 13 + sob)], 5, contorno=False)
    for dx, dy in ((-40, 26), (-33, 31), (-46, 32), (40, 26), (33, 31), (46, 32)):
        c.circulo((215, 140, 100), cx + dx, hy + dy, 2.3, contorno=False)
    c.circulo(BOCHECHA, cx - 40, hy + 22, 7, contorno=False)
    c.circulo(BOCHECHA, cx + 40, hy + 22, 7, contorno=False)
    c.curva(CONTORNO, [(cx - 3, hy + 18), (cx + 4, hy + 23), (cx - 2, hy + 27)], 3, contorno=False)
    _boca(c, cx, hy + 38, 34, estado, t)
    return c.final()


# =============================================================================
# Ratinho na banheira (cena 4)
# =============================================================================

BANHEIRA = {"w": 600, "h": 470, "cx": 300, "borda_y": 250, "agua_y": 262, "rx_agua": 230}
LOUCA = (246, 248, 252)
INTERIOR = (196, 212, 228)
AGUA = (118, 192, 238)
PATO = (255, 214, 40)
BICO = (255, 140, 40)


def _patinho(c, x, y, t):
    c.poligono(PATO, [(x - 30, y - 4), (x - 46, y - 20), (x - 22, y - 14)], esp=4)
    c.elipse(PATO, x, y, 34, 21)
    c.curva((235, 180, 20), [(x - 14, y - 4), (x + 2, y + 4), (x + 14, y - 4)], 4, contorno=False)
    c.circulo(PATO, x + 22, y - 26, 17)
    c.elipse(BICO, x + 42, y - 22, 12, 6, esp=3)
    if not _piscando(t, 2.9, 0.4):
        c.circulo(CONTORNO, x + 27, y - 30, 3.5, contorno=False)
        c.circulo((255, 255, 255), x + 28, y - 31, 1.2, contorno=False)


def draw_generic_bath_mouse(t, estado=PARADO, altura=520, personagem=None):
    """Banheira + ratinho de touca + patinho. Se `personagem` (Surface) for passado,
    ele aparece dentro da banheira no lugar do ratinho genérico."""
    W, H = BANHEIRA["w"], BANHEIRA["h"]
    c = _Tela(W, H, altura / H)
    cx, by, ay = BANHEIRA["cx"], BANHEIRA["borda_y"], BANHEIRA["agua_y"]
    c.sombra(cx, 452, 260, 16)
    for x in (110, 490):
        c.elipse(DOURADO, x, 424, 22, 28)
    c.retangulo(LOUCA, 38, by, 524, 152, raio=80)
    c.curva((255, 255, 255), [(84, 300), (120, 345), (170, 365)], 7, contorno=False)
    c.elipse(LOUCA, cx, by, 262, 50)
    c.elipse(INTERIOR, cx, by + 4, 236, 38, contorno=False)
    c.elipse(AGUA, cx, ay, 230, 28, contorno=False)
    sway = math.sin(t * 1.3) * 14
    mx = cx + sway
    bob = math.sin(t * 2.1) * 3
    if personagem is None:
        c.elipse(PELO_RATO, mx, 248 + bob, 64, 40)
        _cabeca_rato(c, mx, 176 + bob, t, estado, touca=True)
    else:
        iw, ih = personagem.get_size()
        f = 240 * c.k / ih
        img = pygame.transform.smoothscale(personagem, (max(1, round(iw * f)), max(1, round(ih * f))))
        c.s.blit(img, img.get_rect(midbottom=(round(mx * c.k), round(285 * c.k))))
    # água na frente (com ondinhas) cobre a parte de baixo do corpo
    onda = [(cx - 230 + i * 460 / 24, ay + math.sin(i * 0.9 + t * 3) * 3.5) for i in range(25)]
    fundo = [(cx + math.cos(a) * 236, by + 4 + math.sin(a) * 38) for a in np.linspace(0, math.pi, 20)]
    c.poligono(AGUA, onda + fundo, contorno=False)
    for i in range(3):
        x = cx - 160 + i * 140 + math.sin(t * 1.5 + i) * 10
        c.curva((200, 235, 255), [(x, ay + 10), (x + 30, ay + 8)], 3, contorno=False)
    for i, (dx, dy, r) in enumerate([(-150, -6, 16), (-125, -14, 20), (-100, -4, 14), (120, -8, 18),
                                     (145, -2, 14), (95, -14, 13), (-40, 6, 12), (50, 4, 13)]):
        c.circulo((255, 255, 255), cx + dx + sway * 0.3, ay + dy, r * (1 + 0.08 * math.sin(t * 3 + i)), esp=3)
    _patinho(c, 425 + math.sin(t * 0.8) * 12, ay - 12 + math.sin(t * 2.3) * 4, t)
    # borda da frente da banheira
    externo = [(cx + math.cos(a) * 262, by + math.sin(a) * 50) for a in np.linspace(0, math.pi, 28)]
    interno = [(cx + math.cos(a) * 236, by + 4 + math.sin(a) * 38) for a in np.linspace(math.pi, 0, 28)]
    c.poligono(LOUCA, externo + interno, contorno=False)
    c.curva(CONTORNO, interno, 3, contorno=False)
    if personagem is None:  # bracinhos apoiados na borda
        for sx in (-1, 1):
            ombro, mao = (mx + sx * 46, 236 + bob), (mx + sx * 96, 288)
            c.linha(PELO_RATO, ombro, mao, 20)
            c.elipse(PELO_RATO, mao[0], mao[1], 15, 11)
    return c.final()


# =============================================================================
# Elementos avulsos
# =============================================================================

@lru_cache(maxsize=64)
def bolha(raio):
    """Bolha de sabão translúcida com reflexo colorido."""
    tam = raio * 2 + 4
    s = pygame.Surface((tam, tam), pygame.SRCALPHA)
    c = (tam // 2, tam // 2)
    pygame.draw.circle(s, (210, 235, 255, 45), c, raio)
    pygame.draw.circle(s, (235, 248, 255, 180), c, raio, max(2, raio // 10))
    r = pygame.Rect(0, 0, raio * 2 - 6, raio * 2 - 6)
    r.center = c
    pygame.draw.arc(s, (255, 170, 230, 150), r, 3.6, 5.2, max(2, raio // 8))
    pygame.draw.arc(s, (150, 255, 220, 120), r, 0.2, 1.2, max(2, raio // 9))
    pygame.draw.ellipse(s, (255, 255, 255, 220), (c[0] - raio * 0.55, c[1] - raio * 0.6, raio * 0.45, raio * 0.3))
    return _conv(s, True)


def nuvens(seed=4):
    """Três nuvens suaves (Surfaces com transparência) para o céu noturno."""
    rng = random.Random(seed)
    lista = []
    for i in range(3):
        w, h = 560, 200
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(9):
            r = rng.randint(40, 80)
            x = rng.randint(r + 20, w - r - 20)
            y = rng.randint(h // 2 - 20, h // 2 + 30)
            pygame.draw.circle(s, (130, 120, 185, 95), (x, y), r)
        lista.append(_conv(desfocar(s, 6), True))
    return lista


# =============================================================================
# Cenários (1920x1080, gerados uma vez)
# =============================================================================

def _conv(s, alpha=False):
    if pygame.display.get_surface() is None:
        return s
    return s.convert_alpha() if alpha else s.convert()


def _colinas(s, base, amp, cor, fase, freq=0.003):
    pts = [(x, base + math.sin(x * freq + fase) * amp + math.sin(x * freq * 3.1 + fase) * amp * 0.35)
           for x in range(0, LARGURA + 40, 40)]
    pygame.draw.polygon(s, cor, pts + [(LARGURA, ALTURA), (0, ALTURA)])


@lru_cache(maxsize=1)
def ceu_noturno():
    s = gradiente_vertical(LARGURA, ALTURA, [(6, 8, 28), (22, 20, 62), (58, 40, 96), (96, 60, 112)])
    s.blit(brilho_aditivo(300, (90, 85, 70)), (1560 - 300, 210 - 300), special_flags=pygame.BLEND_ADD)
    pygame.draw.circle(s, (250, 244, 222), (1560, 210), 72)
    for dx, dy, r in ((-20, -15, 14), (22, 10, 10), (-5, 28, 8), (30, -25, 7)):
        pygame.draw.circle(s, (232, 224, 200), (1560 + dx, 210 + dy), r)
    _colinas(s, 860, 40, (42, 34, 82), 0.5)
    _colinas(s, 950, 26, (24, 20, 48), 2.0, 0.0025)
    return _conv(s)


@lru_cache(maxsize=1)
def castelo(escala=0.82):
    """Castelo estilizado original. Retorna dict com surface, janelas e mastro
    (coordenadas relativas à surface)."""
    rng = random.Random(11)
    c = _Tela(1000, 900, escala, ss=2, contorno=6)
    PAREDE, SOMBRA = (80, 72, 126), (60, 54, 100)
    TELHADO, TELHADO_SOMBRA = (152, 48, 100), (112, 32, 76)

    def ameias(x, y, w, n):
        passo = w / n
        for i in range(n):
            c.retangulo(PAREDE, x + i * passo + 5, y - 24, passo - 14, 28)

    def torre(x, y, w, h):
        c.retangulo(PAREDE, x, y, w, h)
        c.retangulo(SOMBRA, x + w * 0.68, y, w * 0.32, h, contorno=False)
        for _ in range(int(w * h / 3500)):
            bx, by = rng.uniform(x + 8, x + w - 38), rng.uniform(y + 10, y + h - 10)
            c.retangulo(SOMBRA, bx, by, 30, 5, contorno=False)

    def telhado(xe, xd, yb, yt):
        meio = (xe + xd) / 2
        c.poligono(TELHADO, [(xe - 16, yb), (meio, yt), (xd + 16, yb)])
        c.poligono(TELHADO_SOMBRA, [(meio, yt), (xd + 16, yb), (meio + (xd - xe) * 0.08, yb)], contorno=False)

    ameias(170, 640, 660, 9)
    torre(170, 640, 660, 260)
    for x in (110, 740):
        torre(x, 500, 150, 400)
        telhado(x, x + 150, 505, 320)
    ameias(330, 550, 340, 5)
    torre(330, 550, 340, 350)
    c.linha((205, 195, 175), (500, 165), (500, 30), 6)
    c.circulo(DOURADO, 500, 28, 8)
    torre(420, 310, 160, 250)
    telhado(420, 580, 315, 160)
    # portão
    c.retangulo((70, 40, 32), 450, 790, 100, 110)
    c.circulo((70, 40, 32), 500, 792, 50)
    c.retangulo((70, 40, 32), 452, 790, 96, 112, contorno=False)
    for x in range(462, 545, 18):
        c.linha((40, 26, 22), (x, 760), (x, 898), 4, contorno=False)
    janelas = [(171, 560), (801, 560), (171, 690), (801, 690), (380, 620), (592, 620),
               (380, 730), (592, 730), (486, 380), (486, 470)]
    for x, y in janelas:
        c.retangulo((28, 24, 50), x, y, 28, 44, raio=13, esp=4)
    janelas.sort(key=lambda p: -p[1])  # acendem de baixo para cima
    e = escala
    return {
        "surface": _conv(c.final(), True),
        "janelas": [(x * e, y * e, 28 * e, 44 * e) for x, y in janelas],
        "mastro": (500 * e, 155 * e, 36 * e),  # x, y_baixo, y_topo
    }


# ------------------------------------------------------------- porta (cena 2)

PORTA = {"cx": 1060, "base": 960, "larg": 500, "alt": 740}
PORTA["raio"] = PORTA["larg"] // 2
PORTA["topo"] = PORTA["base"] - PORTA["alt"]
PORTA["centro_arco"] = PORTA["topo"] + PORTA["raio"]
TOCHAS = [(650, 500), (1470, 500)]


def _mascara_arco(w, h):
    m = pygame.Surface((w, h), pygame.SRCALPHA)
    r = w // 2
    pygame.draw.rect(m, (255, 255, 255, 255), (0, r, w, h - r))
    pygame.draw.circle(m, (255, 255, 255, 255), (r, r), r)
    return m


@lru_cache(maxsize=1)
def porta_cena():
    rng = random.Random(21)
    s = pygame.Surface((LARGURA, ALTURA))
    s.fill((34, 30, 44))
    for linha, y in enumerate(range(0, PORTA["base"], 72)):
        x = -(linha % 2) * 70
        while x < LARGURA:
            w = rng.randint(120, 190)
            v = rng.randint(-8, 8)
            cor = (58 + v, 52 + v, 72 + v)
            pygame.draw.rect(s, cor, (x + 3, y + 3, w - 6, 66), border_radius=6)
            pygame.draw.line(s, (78 + v, 72 + v, 92 + v), (x + 8, y + 6), (x + w - 10, y + 6), 2)
            x += w
    piso = gradiente_vertical(LARGURA, ALTURA - PORTA["base"], [(48, 42, 58), (26, 22, 32)])
    s.blit(piso, (0, PORTA["base"]))
    for x in range(-2000, LARGURA + 2000, 160):
        pygame.draw.line(s, (20, 18, 26), (PORTA["cx"] + (x - PORTA["cx"]) * 0.35, PORTA["base"]), (x, ALTURA), 3)
    for y in (990, 1035):
        pygame.draw.line(s, (20, 18, 26), (0, y), (LARGURA, y), 3)
    # arco de pedra + batentes
    ox, oy = PORTA["cx"] - 420, PORTA["topo"] - 110
    c = _Tela(840, 900, 1.0, ss=2, contorno=4)
    ccx, ccy = 420, PORTA["centro_arco"] - oy
    r_in, r_out = PORTA["raio"], PORTA["raio"] + 88
    n = 13
    for i in range(n):
        a0 = math.pi + i * math.pi / n + 0.01
        a1 = math.pi + (i + 1) * math.pi / n - 0.01
        extra = 18 if i == n // 2 else 0
        v = rng.randint(-10, 10)
        pts = [(ccx + math.cos(a0) * r_in, ccy + math.sin(a0) * r_in),
               (ccx + math.cos(a0) * (r_out + extra), ccy + math.sin(a0) * (r_out + extra)),
               (ccx + math.cos(a1) * (r_out + extra), ccy + math.sin(a1) * (r_out + extra)),
               (ccx + math.cos(a1) * r_in, ccy + math.sin(a1) * r_in)]
        c.poligono((122 + v, 112 + v, 128 + v), pts)
    base_local = PORTA["base"] - oy
    for lado in (-1, 1):
        y = ccy
        i = 0
        while y < base_local - 4:
            w = 88 if i % 2 == 0 else 66
            h = min(70, base_local - y)
            x = ccx - r_in - w if lado < 0 else ccx + r_in
            v = rng.randint(-10, 10)
            c.retangulo((118 + v, 108 + v, 124 + v), x + 2, y + 2, w - 4, h - 4, raio=4)
            y += 70
            i += 1
    s.blit(c.final(), (ox, oy))
    # suportes das tochas
    for x, y in TOCHAS:
        pygame.draw.rect(s, CONTORNO, (x - 9, y, 18, 70), border_radius=4)
        pygame.draw.polygon(s, (70, 60, 60), [(x - 26, y - 6), (x + 26, y - 6), (x + 14, y + 22), (x - 14, y + 22)])
        pygame.draw.polygon(s, CONTORNO, [(x - 26, y - 6), (x + 26, y - 6), (x + 14, y + 22), (x - 14, y + 22)], 4)
    s.blit(vinheta(LARGURA, ALTURA, 190), (0, 0))
    return _conv(s)


@lru_cache(maxsize=1)
def porta_folhas():
    """Retorna (folha_esquerda, folha_direita) — Surfaces com alpha (250x740 cada)."""
    rng = random.Random(5)
    w, h = PORTA["larg"], PORTA["alt"]
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    n = 6
    bw = w / n
    for i in range(n):
        cor = (124, 74, 40) if i % 2 == 0 else (136, 84, 44)
        pygame.draw.rect(s, cor, (round(i * bw), 0, round(bw) + 1, h))
        for j in range(5):
            x0 = i * bw + rng.uniform(10, bw - 10)
            pts = [(x0 + math.sin(y * 0.015 + j * 2) * 4, y) for y in range(0, h + 20, 20)]
            pygame.draw.lines(s, (100, 58, 30), False, pts, 2)
        pygame.draw.line(s, (60, 34, 18), (round(i * bw), 0), (round(i * bw), h), 4)
    for y in (330, 600):
        pygame.draw.rect(s, (52, 46, 54), (0, y, w, 36))
        pygame.draw.line(s, (95, 88, 98), (0, y + 3), (w, y + 3), 3)
        for x in range(20, w, 52):
            pygame.draw.circle(s, (120, 112, 122), (x, y + 18), 6)
            pygame.draw.circle(s, CONTORNO, (x, y + 18), 6, 2)
    s.blit(_mascara_arco(w, h), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    r = w // 2
    contorno = [(4, h)] + [(r + math.cos(a) * (r - 4), r + math.sin(a) * (r - 4))
                           for a in np.linspace(math.pi, 2 * math.pi, 40)] + [(w - 4, h)]
    pygame.draw.lines(s, CONTORNO, False, contorno, 9)
    pygame.draw.line(s, CONTORNO, (r, 0), (r, h), 6)
    for x in (r - 36, r + 36):
        pygame.draw.circle(s, (70, 60, 50), (x, 470), 16)
        pygame.draw.circle(s, (185, 145, 60), (x, 500), 24, 7)
        pygame.draw.circle(s, CONTORNO, (x, 500), 28, 3)
    esq = s.subsurface((0, 0, r, h)).copy()
    dir_ = s.subsurface((r, 0, w - r, h)).copy()
    return _conv(esq, True), _conv(dir_, True)


@lru_cache(maxsize=1)
def porta_interiores():
    """(escuro, luz) — o vão da porta fechado/escuro e iluminado por dentro."""
    w, h = PORTA["larg"], PORTA["alt"]
    mascara = _mascara_arco(w, h)
    escuro = pygame.Surface((w, h), pygame.SRCALPHA)
    escuro.fill((22, 14, 10, 255))
    escuro.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    d = np.clip(_distancia(w, h, w / 2, h * 0.55) / (h * 0.6), 0, 1)
    rgb = np.stack([255 - 10 * d, 245 - 90 * d, 210 - 160 * d], axis=2)
    luz = superficie_rgba(rgb, np.full((w, h), 255))
    luz.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return _conv(escuro, True), _conv(luz, True)


@lru_cache(maxsize=1)
def raios_porta(niveis=8):
    """Raios de luz dourada saindo da porta, em vários níveis de intensidade (BLEND_ADD)."""
    w, h = 1600, 1080
    base = pygame.Surface((w, h))
    cx, cy = w // 2, PORTA["centro_arco"] + 120
    for i in range(14):
        a = -math.pi / 2 + (i - 6.5) * 0.24
        d1, d2 = a - 0.06, a + 0.06
        pts = [(cx, cy), (cx + math.cos(d1) * 1400, cy + math.sin(d1) * 1400 * 0.9),
               (cx + math.cos(d2) * 1400, cy + math.sin(d2) * 1400 * 0.9)]
        pygame.draw.polygon(base, (52, 40, 14), pts)
    for i in range(10):  # raios no chão
        a = math.pi / 2 + (i - 4.5) * 0.28
        pts = [(cx, cy), (cx + math.cos(a - 0.05) * 1400, cy + math.sin(a - 0.05) * 600),
               (cx + math.cos(a + 0.05) * 1400, cy + math.sin(a + 0.05) * 600)]
        pygame.draw.polygon(base, (44, 33, 11), pts)
    base = desfocar(base, 10)
    base.blit(brilho_aditivo(520, (110, 82, 36)), (cx - 520, cy - 640), special_flags=pygame.BLEND_ADD)
    arr = pygame.surfarray.array3d(base).astype(np.float32)
    # some suavemente com a distância e perto das bordas (sem cantos retos)
    queda = np.clip(1 - _distancia(w, h, cx, cy - 120) / 1000, 0, 1) ** 1.3
    xs = np.arange(w)
    borda = np.clip(np.minimum(xs, w - 1 - xs) / 250, 0, 1)[:, None]
    arr *= (queda * borda)[:, :, None]
    lista = []
    for nv in range(1, niveis + 1):
        lista.append(_conv(pygame.surfarray.make_surface((arr * nv / niveis).astype(np.uint8))))
    return lista, (PORTA["cx"] - cx, 0)


# ------------------------------------------------------------- sala (cena 3)

@lru_cache(maxsize=1)
def sala():
    rng = random.Random(3)
    s = gradiente_vertical(LARGURA, ALTURA, [(72, 40, 34), (122, 72, 46), (150, 92, 56)])
    listras = pygame.Surface((LARGURA, 600), pygame.SRCALPHA)
    for x in range(0, LARGURA, 80):
        pygame.draw.rect(listras, (255, 225, 185, 14), (x, 0, 40, 600))
    s.blit(listras, (0, 0))
    pygame.draw.rect(s, (96, 58, 36), (0, 600, LARGURA, 220))
    pygame.draw.rect(s, (128, 82, 46), (0, 588, LARGURA, 20))
    for x in range(30, LARGURA, 240):
        pygame.draw.rect(s, (80, 46, 28), (x, 630, 200, 160), 4, border_radius=6)
    s.blit(gradiente_vertical(LARGURA, 260, [(128, 82, 50), (84, 52, 30)]), (0, 820))
    y, alt = 822, 28
    while y < ALTURA:
        pygame.draw.line(s, (70, 42, 24), (0, y), (LARGURA, y), 2)
        for _ in range(6):
            x = rng.randint(0, LARGURA)
            pygame.draw.line(s, (70, 42, 24), (x, y), (x, y + alt), 2)
        y += alt
        alt = int(alt * 1.18)
    # janela com noite lá fora
    jx, jy, jw, jh = 180, 170, 360, 380
    s.blit(gradiente_vertical(jw, jh, [(14, 16, 48), (50, 40, 96)]), (jx, jy))
    pygame.draw.circle(s, (250, 242, 215), (jx + 260, jy + 90), 38)
    for _ in range(30):
        pygame.draw.circle(s, (255, 250, 230), (jx + rng.randint(5, jw - 5), jy + rng.randint(5, jh - 120)), rng.choice((1, 1, 2)))
    _colinas_janela = [(jx + i * 30, jy + jh - 60 + math.sin(i * 0.8) * 18) for i in range(jw // 30 + 1)]
    pygame.draw.polygon(s, (28, 24, 54), _colinas_janela + [(jx + jw, jy + jh), (jx, jy + jh)])
    pygame.draw.rect(s, (110, 70, 40), (jx - 18, jy - 18, jw + 36, jh + 36), 22, border_radius=8)
    pygame.draw.rect(s, CONTORNO, (jx - 22, jy - 22, jw + 44, jh + 44), 5, border_radius=10)
    pygame.draw.line(s, (110, 70, 40), (jx + jw // 2, jy), (jx + jw // 2, jy + jh), 14)
    pygame.draw.line(s, (110, 70, 40), (jx, jy + jh // 2), (jx + jw, jy + jh // 2), 14)
    pygame.draw.rect(s, (140, 92, 52), (jx - 40, jy + jh + 14, jw + 80, 24), border_radius=6)
    for lado in (-1, 1):
        x0 = jx - 70 if lado < 0 else jx + jw - 20
        pygame.draw.rect(s, (168, 40, 52), (x0, jy - 50, 90, jh + 140), border_radius=20)
        for k in range(3):
            pygame.draw.line(s, (128, 26, 38), (x0 + 22 + k * 24, jy - 40), (x0 + 22 + k * 24, jy + jh + 80), 5)
        pygame.draw.rect(s, CONTORNO, (x0, jy - 50, 90, jh + 140), 4, border_radius=20)
    pygame.draw.rect(s, (90, 60, 40), (jx - 100, jy - 66, jw + 200, 16), border_radius=8)
    # quadro
    pygame.draw.rect(s, (190, 148, 64), (860, 210, 280, 200), border_radius=6)
    s.blit(gradiente_vertical(240, 160, [(120, 190, 240), (210, 235, 250)]), (880, 230))
    pygame.draw.circle(s, (255, 215, 90), (1080, 270), 22)
    pygame.draw.ellipse(s, (90, 170, 90), (870, 330, 200, 140))
    pygame.draw.ellipse(s, (70, 150, 80), (960, 345, 200, 120))
    pygame.draw.rect(s, (72, 40, 34), (880, 390, 240, 40))
    pygame.draw.rect(s, (190, 148, 64), (860, 210, 280, 200), 20, border_radius=6)
    pygame.draw.rect(s, CONTORNO, (856, 206, 288, 208), 5, border_radius=8)
    # estante
    ex, ey, ew, eh = 1570, 250, 290, 570
    pygame.draw.rect(s, (104, 64, 36), (ex, ey, ew, eh), border_radius=6)
    pygame.draw.rect(s, CONTORNO, (ex, ey, ew, eh), 5, border_radius=6)
    for i in range(4):
        prat_y = ey + 30 + i * 135
        x = ex + 18
        while x < ex + ew - 30:
            bw, bh = rng.randint(18, 34), rng.randint(70, 110)
            cor = rng.choice([(200, 70, 70), (70, 120, 200), (230, 180, 60), (90, 170, 110), (160, 90, 180)])
            pygame.draw.rect(s, cor, (x, prat_y + 110 - bh, bw, bh), border_radius=3)
            pygame.draw.rect(s, CONTORNO, (x, prat_y + 110 - bh, bw, bh), 2, border_radius=3)
            x += bw + 3
        pygame.draw.rect(s, (130, 84, 48), (ex + 8, prat_y + 110, ew - 16, 14))
    # tapete
    pygame.draw.ellipse(s, CONTORNO, (590, 868, 1130, 196))
    pygame.draw.ellipse(s, (160, 52, 56), (596, 874, 1118, 184))
    pygame.draw.ellipse(s, (205, 120, 70), (680, 900, 950, 132), 10)
    pygame.draw.ellipse(s, (230, 180, 90), (800, 930, 710, 72), 6)
    # abajur de chão com luz quente
    lx = 760
    pygame.draw.ellipse(s, CONTORNO, (lx - 58, 790, 116, 34))
    pygame.draw.ellipse(s, (60, 46, 40), (lx - 52, 794, 104, 26))
    pygame.draw.line(s, CONTORNO, (lx, 800), (lx, 450), 12)
    pygame.draw.line(s, (150, 120, 80), (lx, 800), (lx, 450), 6)
    cupula = [(lx - 50, 380), (lx + 50, 380), (lx + 86, 470), (lx - 86, 470)]
    s.blit(brilho_aditivo(480, (95, 62, 26)), (lx - 480, 470 - 480), special_flags=pygame.BLEND_ADD)
    pygame.draw.polygon(s, (255, 222, 150), cupula)
    pygame.draw.polygon(s, CONTORNO, cupula, 5)
    s.blit(brilho_aditivo(170, (150, 110, 50)), (lx - 170, 470 - 170), special_flags=pygame.BLEND_ADD)
    s.blit(vinheta(LARGURA, ALTURA, 150), (0, 0))
    return _conv(s)


# ------------------------------------------------------------- banheiro (cena 4)

@lru_cache(maxsize=1)
def banheiro():
    s = pygame.Surface((LARGURA, ALTURA))
    s.fill((150, 192, 204))
    t = 96
    for y in range(0, 840, t):
        for x in range(0, LARGURA, t):
            faixa = 480 <= y < 480 + t
            cor = (112, 176, 202) if faixa else (208, 234, 240)
            pygame.draw.rect(s, cor, (x + 2, y + 2, t - 4, t - 4), border_radius=6)
            pygame.draw.line(s, (236, 250, 252), (x + 8, y + 8), (x + 30, y + 8), 3)
    pygame.draw.rect(s, (130, 170, 184), (0, 830, LARGURA, 16))
    tp = 120
    for i, y in enumerate(range(846, ALTURA, tp)):
        for j, x in enumerate(range(-tp // 2, LARGURA, tp)):
            cor = (236, 238, 244) if (i + j) % 2 == 0 else (84, 134, 168)
            pygame.draw.rect(s, cor, (x, y, tp - 3, tp - 3))
    # espelho
    pygame.draw.ellipse(s, CONTORNO, (1366, 96, 288, 348))
    pygame.draw.ellipse(s, (232, 192, 82), (1372, 102, 276, 336))
    vidro = gradiente_vertical(236, 296, [(190, 225, 240), (140, 190, 215)])
    m = pygame.Surface((236, 296), pygame.SRCALPHA)
    pygame.draw.ellipse(m, (255, 255, 255, 255), m.get_rect())
    vidro = vidro.convert_alpha() if pygame.display.get_surface() else vidro
    v2 = pygame.Surface((236, 296), pygame.SRCALPHA)
    v2.blit(vidro, (0, 0))
    v2.blit(m, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    s.blit(v2, (1392, 122))
    for k in range(2):
        pygame.draw.line(s, (235, 248, 255), (1440 + k * 40, 180), (1500 + k * 40, 130), 8)
    # toalheiro com toalha listrada
    pygame.draw.line(s, CONTORNO, (200, 380), (540, 380), 12)
    pygame.draw.line(s, (200, 205, 215), (200, 380), (540, 380), 6)
    pygame.draw.rect(s, (255, 140, 160), (250, 376, 240, 300), border_radius=14)
    for y in (600, 630):
        pygame.draw.rect(s, (255, 255, 255), (250, y, 240, 14))
    pygame.draw.rect(s, CONTORNO, (250, 376, 240, 300), 5, border_radius=14)
    # prateleira com frascos
    pygame.draw.rect(s, (240, 240, 245), (1180, 560, 300, 18), border_radius=6)
    pygame.draw.rect(s, CONTORNO, (1180, 560, 300, 18), 4, border_radius=6)
    for x, h, cor in ((1200, 90, (120, 200, 120)), (1260, 120, (255, 160, 60)),
                      (1330, 80, (170, 120, 220)), (1400, 105, (90, 170, 230))):
        pygame.draw.rect(s, cor, (x, 560 - h, 50, h), border_radius=14)
        pygame.draw.rect(s, CONTORNO, (x, 560 - h, 50, h), 4, border_radius=14)
        pygame.draw.rect(s, (255, 255, 255), (x + 10, 560 - h + 30, 30, 26), border_radius=4)
    # janelinha
    pygame.draw.rect(s, (226, 240, 248), (170, 110, 230, 170), border_radius=10)
    pygame.draw.rect(s, CONTORNO, (170, 110, 230, 170), 6, border_radius=10)
    pygame.draw.line(s, CONTORNO, (285, 110), (285, 280), 5)
    s.blit(vinheta(LARGURA, ALTURA, 120), (0, 0))
    return _conv(s)


# ------------------------------------------------------------- palco (cena 5)

@lru_cache(maxsize=1)
def palco():
    """Retorna dict: fundo, cortina (esquerda), sanefa (faixa de cima)."""
    s = gradiente_vertical(LARGURA, ALTURA, [(66, 18, 36), (30, 8, 18)])
    arr = pygame.surfarray.pixels3d(s)
    dobras = 0.75 + 0.25 * np.cos(np.arange(LARGURA) * 2 * np.pi / 120)
    arr[:] = (arr * dobras[:, None, None]).astype(np.uint8)
    del arr
    piso_y = 800
    s.blit(gradiente_vertical(LARGURA, ALTURA - piso_y, [(150, 96, 52), (92, 56, 30)]), (0, piso_y))
    fuga = (960, 300)
    for x in range(-1600, LARGURA + 1700, 130):
        f = (piso_y - fuga[1]) / (ALTURA - fuga[1])
        pygame.draw.line(s, (80, 48, 26), (fuga[0] + (x - fuga[0]) * f, piso_y), (x, ALTURA), 3)
    y, passo = piso_y + 20, 22
    while y < ALTURA:
        pygame.draw.line(s, (90, 56, 30), (0, y), (LARGURA, y), 2)
        y += passo
        passo = int(passo * 1.25)
    pygame.draw.line(s, (200, 150, 80), (0, piso_y), (LARGURA, piso_y), 4)
    for x in range(60, LARGURA, 150):  # luzes da ribalta
        s.blit(brilho_aditivo(60, (140, 110, 50)), (x - 60, ALTURA - 70), special_flags=pygame.BLEND_ADD)
    # cortina lateral (esquerda) — dobras via numpy
    cw = 760
    x = np.arange(cw)
    sombra = 0.5 + 0.5 * (0.5 + 0.5 * np.cos(2 * np.pi * x / 95)) ** 0.8
    rgb = np.zeros((cw, ALTURA, 3))
    rgb[:, :, 0] = (185 * sombra)[:, None]
    rgb[:, :, 1] = (28 * sombra)[:, None]
    rgb[:, :, 2] = (44 * sombra)[:, None]
    rgb[cw - 22:, :, :] = (230, 180, 70)
    rgb[cw - 28:cw - 22, :, :] = CONTORNO
    cortina = superficie_rgba(rgb, np.full((cw, ALTURA), 255))
    # sanefa com bordas arredondadas e franja dourada
    sh = 190
    xs = np.arange(LARGURA)
    limite = 130 + 34 * np.abs(np.sin(np.pi * xs / 160))
    ys = np.arange(sh)
    dentro = ys[None, :] < limite[:, None]
    dob = 0.7 + 0.3 * np.cos(2 * np.pi * xs / 80)
    rgb = np.zeros((LARGURA, sh, 3))
    rgb[:, :, 0] = (175 * dob)[:, None]
    rgb[:, :, 1] = (26 * dob)[:, None]
    rgb[:, :, 2] = (42 * dob)[:, None]
    sanefa = superficie_rgba(rgb, dentro * 255.0)
    for xx in range(0, LARGURA, 6):
        yy = int(limite[xx])
        pygame.draw.circle(sanefa, (235, 185, 70), (xx, yy - 3), 5)
    pygame.draw.rect(sanefa, (235, 185, 70), (0, 20, LARGURA, 10))
    # a cortina é totalmente opaca: sem canal alpha o blit fica bem mais rápido
    return {"fundo": _conv(s), "cortina": _conv(cortina), "sanefa": _conv(sanefa, True)}
