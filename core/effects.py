"""Efeitos visuais reutilizáveis: gradientes, brilhos, estrelas e partículas (tudo com dt)."""

import math
import random
from functools import lru_cache

import numpy as np
import pygame

LARGURA, ALTURA = 1920, 1080


# ---------------------------------------------------------------- utilidades

def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def lerp(a, b, f):
    return a + (b - a) * f


def ease_out(f):
    f = clamp(f)
    return 1 - (1 - f) ** 3


def ease_in_out(f):
    f = clamp(f)
    return 3 * f * f - 2 * f * f * f


def ease_back(f):
    """Passa um pouco do ponto e volta (efeito 'pop')."""
    f = clamp(f)
    c = 1.7
    return 1 + (c + 1) * (f - 1) ** 3 + c * (f - 1) ** 2


def blit_alpha(destino, surf, pos, alpha):
    """Blit com transparência extra sem estragar superfícies em cache."""
    alpha = int(clamp(alpha, 0, 255))
    if alpha <= 0:
        return
    surf.set_alpha(alpha)
    destino.blit(surf, pos)
    surf.set_alpha(255)


def blit_centro(destino, surf, centro, alpha=255):
    r = surf.get_rect(center=(int(centro[0]), int(centro[1])))
    blit_alpha(destino, surf, r.topleft, alpha)


# ---------------------------------------------------------------- geração (numpy)

def pronta(surf, alpha=False):
    """Converte para o formato da tela (blits muito mais rápidos), se a janela já existe."""
    if pygame.display.get_surface() is None:
        return surf
    return surf.convert_alpha() if alpha else surf.convert()


def gradiente_vertical(w, h, cores):
    """Gradiente com 2+ cores de cima para baixo. Retorna Surface RGB."""
    paradas = np.linspace(0, 1, len(cores))
    y = np.linspace(0, 1, h)
    canais = [np.interp(y, paradas, [c[i] for c in cores]) for i in range(3)]
    coluna = np.stack(canais, axis=1)                    # (h, 3)
    arr = np.repeat(coluna[None, :, :], w, axis=0)       # (w, h, 3)
    return pygame.surfarray.make_surface(arr.astype(np.uint8))


def superficie_rgba(rgb, alpha):
    """rgb (w,h,3) + alpha (w,h) -> Surface SRCALPHA."""
    w, h = alpha.shape
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.pixels3d(s)[:] = rgb
    pygame.surfarray.pixels_alpha(s)[:] = np.clip(alpha, 0, 255).astype(np.uint8)
    return s


def _distancia(w, h, cx=None, cy=None):
    cx = w / 2 if cx is None else cx
    cy = h / 2 if cy is None else cy
    x = np.arange(w)[:, None] - cx
    y = np.arange(h)[None, :] - cy
    return np.sqrt(x * x + y * y)


@lru_cache(maxsize=2048)
def brilho_aditivo(raio, cor, intensidade=1.0):
    """Bola de luz para BLEND_ADD (fundo preto não soma nada)."""
    tam = max(2, int(raio * 2))
    d = np.clip(_distancia(tam, tam) / max(raio, 1), 0, 1)
    f = ((1 - d) ** 2) * intensidade
    arr = np.stack([f * c for c in cor], axis=2)
    return pronta(pygame.surfarray.make_surface(np.clip(arr, 0, 255).astype(np.uint8)))


def preaquecer_brilhos(cores, tam=(3, 20)):
    """Gera antes os sprites de brilho usados pelas partículas (evita travadas na hora)."""
    for cor in cores:
        for r in range(int(tam[0] * 2) // 4 * 4 + 4, int(tam[1] * 2) // 4 * 4 + 8, 4):
            for nv in range(9):
                brilho_aditivo(r, cor, nv / 8)


@lru_cache(maxsize=64)
def brilho_alpha(raio, cor, alpha_max=255):
    """Bola de luz com transparência (blit normal)."""
    tam = max(2, int(raio * 2))
    d = np.clip(_distancia(tam, tam) / max(raio, 1), 0, 1)
    a = ((1 - d) ** 2) * alpha_max
    rgb = np.zeros((tam, tam, 3)) + np.array(cor)
    return pronta(superficie_rgba(rgb, a), True)


def vinheta(w, h, forca=170, inicio=0.55):
    """Escurece as bordas."""
    d = _distancia(w, h) / math.hypot(w / 2, h / 2)
    a = np.clip((d - inicio) / (1 - inicio), 0, 1) ** 1.6 * forca
    return pronta(superficie_rgba(np.zeros((w, h, 3)), a), True)


def mascara_holofote(raio, escuridao=170, suavidade=0.45):
    """Camada escura 2x maior que a tela com um 'buraco' de luz no centro."""
    w, h = LARGURA * 2, ALTURA * 2
    d = _distancia(w, h) / raio
    a = np.clip((d - (1 - suavidade)) / suavidade, 0, 1) * escuridao
    return pronta(superficie_rgba(np.zeros((w, h, 3)), a), True)


def sombra_suave(w, h, alpha=90):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
    pequena = pygame.transform.smoothscale(s, (max(1, w // 6), max(1, h // 6)))
    return pygame.transform.smoothscale(pequena, (w, h))


def desfocar(surf, fator=8):
    w, h = surf.get_size()
    pequena = pygame.transform.smoothscale(surf, (max(1, w // fator), max(1, h // fator)))
    return pygame.transform.smoothscale(pequena, (w, h))


def pontos_estrela(cx, cy, r, ang=0.0, pontas=5, interno=0.45):
    pts = []
    for i in range(pontas * 2):
        rr = r if i % 2 == 0 else r * interno
        a = ang + i * math.pi / pontas - math.pi / 2
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts


# ---------------------------------------------------------------- estrelas

class CampoEstrelas:
    """Estrelas que piscam suavemente, com deriva lenta (paralaxe)."""

    NIVEIS = 8

    def __init__(self, n, area=(0, 0, LARGURA, ALTURA), seed=1, deriva=(0.0, 0.0),
                 tamanhos=(2, 3, 5), cor=(255, 248, 225)):
        rng = random.Random(seed)
        x0, y0, w, h = area
        self.area = area
        self.estrelas = [[x0 + rng.random() * w, y0 + rng.random() * h,
                          rng.randrange(len(tamanhos)), rng.random() * 6.28,
                          rng.uniform(0.6, 2.2)] for _ in range(n)]
        self.deriva = deriva
        self.sprites = [[brilho_aditivo(r * 2.2, cor, 0.25 + 0.75 * nv / (self.NIVEIS - 1))
                         for nv in range(self.NIVEIS)] for r in tamanhos]
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        x0, y0, w, h = self.area
        dx, dy = self.deriva[0] * dt, self.deriva[1] * dt
        for e in self.estrelas:
            e[0] = x0 + (e[0] - x0 + dx) % w
            e[1] = y0 + (e[1] - y0 + dy) % h

    def draw(self, surf, desloc=(0, 0), brilho=1.0):
        t = self.t
        ox, oy = desloc
        topo = self.NIVEIS - 1
        for x, y, tam, fase, vel in self.estrelas:
            b = (0.5 + 0.5 * math.sin(t * vel + fase)) * brilho
            spr = self.sprites[tam][int(clamp(b) * topo)]
            r = spr.get_width() // 2
            surf.blit(spr, (x + ox - r, y + oy - r), special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------- partículas

CORES_CONFETE = [(255, 80, 90), (255, 200, 40), (70, 200, 120), (60, 160, 255),
                 (190, 90, 255), (255, 130, 200), (255, 255, 255)]


class Particula:
    __slots__ = ("x", "y", "vx", "vy", "vida", "dur", "tipo", "tam", "cor", "ang", "vang", "fase")

    def __init__(self, x, y, vx, vy, dur, tipo, tam, cor, ang=0.0, vang=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.vida, self.dur = 0.0, dur
        self.tipo, self.tam, self.cor = tipo, tam, cor
        self.ang, self.vang = ang, vang
        self.fase = random.random() * 6.28


class Particulas:
    """Sistema simples: 'brilho' (luz aditiva), 'confete', 'estrela', 'gota'."""

    def __init__(self, maximo=500):
        self.lista = []
        self.maximo = maximo

    def emitir(self, x, y, tipo, n=1, vel=(0, 0), espalhar=(30, 30), dur=(1.0, 2.0),
               tam=(6, 12), cores=None):
        for _ in range(n):
            if len(self.lista) >= self.maximo:
                return
            cor = random.choice(cores or CORES_CONFETE)
            self.lista.append(Particula(
                x, y,
                vel[0] + random.uniform(-espalhar[0], espalhar[0]),
                vel[1] + random.uniform(-espalhar[1], espalhar[1]),
                random.uniform(*dur), tipo, random.uniform(*tam), cor,
                random.uniform(0, 6.28), random.uniform(-6, 6)))

    def update(self, dt):
        vivas = []
        for p in self.lista:
            p.vida += dt
            if p.vida >= p.dur or p.y > ALTURA + 80:
                continue
            if p.tipo == "confete":
                p.vy += 60 * dt
                p.vx *= (1 - 0.8 * dt)
                p.x += math.sin(p.vida * 3 + p.fase) * 40 * dt
            elif p.tipo == "estrela":
                p.vy += 30 * dt
            elif p.tipo == "gota":
                p.vy += 900 * dt
            elif p.tipo == "brilho":
                p.vx *= (1 - 1.5 * dt)
                p.vy *= (1 - 1.5 * dt)
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.ang += p.vang * dt
            vivas.append(p)
        self.lista = vivas

    def draw(self, surf):
        for p in self.lista:
            f = p.vida / p.dur
            if p.tipo == "brilho":
                luz = math.sin(math.pi * f)  # acende e apaga
                spr = brilho_aditivo(int(p.tam * 2) // 4 * 4 + 4, p.cor, round(luz * 8) / 8)
                r = spr.get_width() // 2
                surf.blit(spr, (p.x - r, p.y - r), special_flags=pygame.BLEND_ADD)
            elif p.tipo == "confete":
                larg = p.tam * abs(math.cos(p.vida * 5 + p.fase))  # efeito de girar no ar
                c, s = math.cos(p.ang), math.sin(p.ang)
                pts = []
                for dx, dy in ((-larg, -p.tam * 0.5), (larg, -p.tam * 0.5),
                               (larg, p.tam * 0.5), (-larg, p.tam * 0.5)):
                    pts.append((p.x + dx * c - dy * s, p.y + dx * s + dy * c))
                pygame.draw.polygon(surf, p.cor, pts)
            elif p.tipo == "estrela":
                pts = pontos_estrela(p.x, p.y, p.tam, p.ang)
                pygame.draw.polygon(surf, p.cor, pts)
                pygame.draw.polygon(surf, (60, 40, 20), pts, 2)
            elif p.tipo == "gota":
                pygame.draw.circle(surf, p.cor, (int(p.x), int(p.y)), max(1, int(p.tam * (1 - f))))
