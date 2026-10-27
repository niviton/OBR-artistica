"""Cena 1 (1 dedo): abertura do castelo."""

import math
import random

import pygame

import generic_art as arte
from core.effects import (CampoEstrelas, Particulas, blit_centro, brilho_aditivo, clamp,
                          ease_in_out, ease_out, lerp, preaquecer_brilhos)
from core.text import texto
from scenes.base import Scene

# Linha do tempo (segundos)
T_JANELAS = 1.0          # primeira janela acende
INTERVALO_JANELAS = 0.45
T_RATO_INICIO, T_RATO_FIM = 1.2, 7.0
RATO_X0, RATO_X1, CHAO_Y = -180, 770, 1012
T_BANDEIRA, DUR_BANDEIRA = 7.5, 4.0
ESTILO_TITULO = {"tamanho": 112, "cor": (255, 222, 120), "esp": 6}
ESTILO_SUB = {"tamanho": 44, "cor": (225, 220, 255), "esp": 3}
CORES_BRILHO = [(255, 220, 140), (200, 200, 255), (255, 255, 255)]


class CenaCastelo(Scene):
    nome = "cena1"
    titulo = "Abertura do castelo"

    def preparar(self):
        self.ceu = arte.ceu_noturno()
        c = arte.castelo()
        self.castelo = c["surface"]
        w, h = self.castelo.get_size()
        self.cx, self.cy = 960 - w // 2, 915 - h
        self.janelas = [(x + self.cx, y + self.cy, jw, jh) for x, y, jw, jh in c["janelas"]]
        mx, y_baixo, y_topo = c["mastro"]
        self.mastro = (mx + self.cx, y_baixo + self.cy, y_topo + self.cy)
        self.nuvens = arte.nuvens()
        self.longe = CampoEstrelas(150, (0, 0, 1920, 780), seed=3, deriva=(4, 0), tamanhos=(1, 2, 2))
        self.perto = CampoEstrelas(40, (0, 0, 1920, 700), seed=5, deriva=(10, 0), tamanhos=(2, 3, 4))
        self.brilhos = Particulas(160)
        self.luz_janela = brilho_aditivo(46, (120, 90, 30))
        preaquecer_brilhos(CORES_BRILHO, (6, 14))
        texto(self.falas.get("titulo", ""), **ESTILO_TITULO)
        texto(self.falas.get("subtitulo", ""), **ESTILO_SUB)

    def enter(self):
        super().enter()
        rng = random.Random(9)
        self.nuvem_pos = [[rng.uniform(-300, 1900), rng.uniform(60, 520), rng.uniform(12, 30), i % 3]
                          for i in range(6)]
        self.brilhos.lista.clear()
        self.ding = False
        self.acum = 0.0

    def update(self, dt):
        super().update(dt)
        self.longe.update(dt)
        self.perto.update(dt)
        for n in self.nuvem_pos:
            n[0] += n[2] * dt
            if n[0] > 2000:
                n[0] = -600
        fim_bandeira = T_BANDEIRA + DUR_BANDEIRA
        if self.t >= fim_bandeira:
            if not self.ding and not self.assets.som:
                self.app.audio.tocar_generico("ding")
            self.ding = True
            self.acum += dt * 14
            while self.acum >= 1:
                self.acum -= 1
                self.brilhos.emitir(random.uniform(500, 1420), random.uniform(180, 900), "brilho",
                                    vel=(0, -18), espalhar=(10, 10), dur=(1.5, 3.0), tam=(6, 14),
                                    cores=CORES_BRILHO)
        self.brilhos.update(dt)

    def draw(self, frame):
        t = self.t
        balanco = math.sin(t * 0.25) * 6   # paralaxe leve
        if not self.desenhar_fundo_proprio(frame):
            frame.blit(self.ceu, (0, 0))
            self.longe.draw(frame, (balanco * 0.3, 0))
            for x, y, vel, i in self.nuvem_pos[:3]:
                frame.blit(self.nuvens[i], (x + balanco * 0.5, y))
            self.perto.draw(frame, (balanco * 0.6, 0))
            for x, y, vel, i in self.nuvem_pos[3:]:
                frame.blit(self.nuvens[i], (x * 1.2 + balanco, y + 120))
            frame.blit(self.castelo, (self.cx, self.cy))
            self._janelas(frame, t)
            self._bandeira(frame, t)
        # ratinho caminha até o pé do castelo
        f = clamp((t - T_RATO_INICIO) / (T_RATO_FIM - T_RATO_INICIO))
        x = lerp(RATO_X0, RATO_X1, f)
        estado = arte.ANDANDO if 0 < f < 1 else arte.PARADO
        if t >= T_BANDEIRA + DUR_BANDEIRA:
            estado = arte.COMEMORANDO if (t - T_BANDEIRA - DUR_BANDEIRA) < 2.5 else arte.PARADO
        rato = self.personagem(arte.draw_generic_mouse, estado, 240)
        frame.blit(rato, rato.get_rect(midbottom=(x, CHAO_Y)))
        self.brilhos.draw(frame)
        # título: fade + leve zoom
        ft = ease_out(t / 2.2)
        titulo = texto(self.falas.get("titulo", ""), **ESTILO_TITULO)
        if ft < 1:
            titulo = pygame.transform.rotozoom(titulo, 0, 0.82 + 0.18 * ft)
        blit_centro(frame, titulo, (960, 110), 255 * ft)
        sub = self.falas.get("subtitulo", "")
        if sub:
            blit_centro(frame, texto(sub, **ESTILO_SUB), (960, 1040),
                        255 * clamp((t - 2.5) / 1.5))

    def _janelas(self, frame, t):
        for i, (x, y, w, h) in enumerate(self.janelas):
            f = clamp((t - (T_JANELAS + i * INTERVALO_JANELAS)) / 0.35)
            if f <= 0:
                continue
            tremor = 0.88 + 0.12 * math.sin(t * 7 + i * 1.7)
            cor = (int(lerp(28, 255, f * tremor)), int(lerp(24, 212, f * tremor)), int(lerp(50, 120, f)))
            r = pygame.Rect(round(x + 3), round(y + 3), round(w - 6), round(h - 6))
            pygame.draw.rect(frame, cor, r, border_top_left_radius=int(w / 2), border_top_right_radius=int(w / 2))
            if f > 0.5:
                g = self.luz_janela
                frame.blit(g, (r.centerx - g.get_width() // 2, r.centery - g.get_height() // 2),
                           special_flags=pygame.BLEND_ADD)

    def _bandeira(self, frame, t):
        mx, y_baixo, y_topo = self.mastro
        f = ease_in_out((t - T_BANDEIRA) / DUR_BANDEIRA)
        if t < T_BANDEIRA - 0.5:
            return
        topo = lerp(y_baixo - 10, y_topo + 6, f)
        pts = []
        for i in range(9):
            u = i / 8
            pts.append((mx + 3 + u * 84, topo + math.sin(t * 6 - u * 4) * 5 * u))
        baixo = [(x, y + 50 - 8 * (i / 8)) for i, (x, y) in enumerate(pts)]
        poly = pts + baixo[::-1]
        pygame.draw.polygon(frame, (255, 200, 60), poly)
        pygame.draw.polygon(frame, arte.CONTORNO, poly, 4)
        estrela = [(mx + 40 + dx, topo + 25 + dy + math.sin(t * 6 - 2) * 2.5)
                   for dx, dy in [(math.cos(a) * r, math.sin(a) * r) for a, r in
                                  [(-math.pi / 2 + k * math.pi / 5, 13 if k % 2 == 0 else 6) for k in range(10)]]]
        pygame.draw.polygon(frame, (230, 70, 90), estrela)
