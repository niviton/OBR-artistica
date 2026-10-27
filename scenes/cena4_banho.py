"""Cena 4 (4 dedos): banho do ratinho com bolhas de sabão."""

import math
import random

import pygame

import generic_art as arte
from core.effects import clamp, ease_back
from core.text import balao
from scenes.base import Scene

ALTURA_BANHO = 560
CENTRO_X, CHAO_Y = 960, 1030
BOLHAS_POR_SEGUNDO = 3.5
VELOCIDADE_TEXTO = 24


class CenaBanho(Scene):
    nome = "cena4"
    titulo = "Banho do ratinho"

    def preparar(self):
        self.banheiro = arte.banheiro()
        B = arte.BANHEIRA
        k = ALTURA_BANHO / B["h"]
        self.k = k
        self.topo = CHAO_Y - ALTURA_BANHO
        self.agua_y = self.topo + B["agua_y"] * k
        self.agua_rx = B["rx_agua"] * k

    def enter(self):
        super().enter()
        self.bolhas = []      # [x, y, r, vy, y_estouro, fase]
        self.estouros = []    # [x, y, r, idade]
        self.acum = 0.0
        self.ultimo_plop = 0.0

    def update(self, dt):
        super().update(dt)
        self.acum += dt * BOLHAS_POR_SEGUNDO
        while self.acum >= 1:
            self.acum -= 1
            r = random.randint(10, 40)
            self.bolhas.append([CENTRO_X + random.uniform(-0.85, 0.85) * self.agua_rx, self.agua_y - 6, r,
                                -random.uniform(60, 130) * (1.25 - r / 60),
                                random.uniform(80, self.agua_y - 160), random.uniform(0, 6.28)])
        vivas = []
        for b in self.bolhas:
            b[1] += b[3] * dt
            b[0] += math.sin(self.t * 2 + b[5]) * 22 * dt
            if b[1] <= b[4]:
                self.estouros.append([b[0], b[1], b[2], 0.0])
                if self.t - self.ultimo_plop > 0.12 and not self.assets.som:
                    self.app.audio.tocar_generico(f"bolha{random.randint(0, 2)}", 0.6)
                    self.ultimo_plop = self.t
            else:
                vivas.append(b)
        self.bolhas = vivas
        for e in self.estouros:
            e[3] += dt
        self.estouros = [e for e in self.estouros if e[3] < 0.35]

    def draw(self, frame):
        t = self.t
        if not self.desenhar_fundo_proprio(frame):
            frame.blit(self.banheiro, (0, 0))
        texto_cena = self.falas.get("texto", "")
        n = int(max(0.0, t - 0.8) * VELOCIDADE_TEXTO)
        estado = arte.FALANDO if 0 < n < len(texto_cena) else arte.PARADO
        banho = arte.draw_generic_bath_mouse(t, estado, ALTURA_BANHO, personagem=self.assets.personagem)
        frame.blit(banho, banho.get_rect(midbottom=(CENTRO_X, CHAO_Y)))
        for x, y, r, *_ in self.bolhas:
            s = arte.bolha(r)
            frame.blit(s, (x - s.get_width() / 2, y - s.get_height() / 2))
        for x, y, r, idade in self.estouros:
            f = idade / 0.35
            raio = int(r * (1 + f * 0.8))
            pygame.draw.circle(frame, (235, 250, 255), (int(x), int(y)), raio, max(1, int(3 * (1 - f))))
            for k in range(6):
                a = k * math.pi / 3 + 0.4
                d = r * (1 + f * 1.6)
                pygame.draw.circle(frame, (225, 245, 255), (int(x + math.cos(a) * d), int(y + math.sin(a) * d)),
                                   max(1, int(4 * (1 - f))))
        if t > 0.8 and texto_cena:
            surf, ponta = balao(texto_cena, min(len(texto_cena), n), cauda=0.85)
            esc = ease_back((t - 0.8) / 0.35)
            if esc < 0.999:
                w, h = surf.get_size()
                surf = pygame.transform.rotozoom(surf, 0, max(0.01, esc))
                ponta = (ponta[0] * surf.get_width() / w, ponta[1] * surf.get_height() / h)
            alvo = (CENTRO_X - 70, self.topo + 70)
            frame.blit(surf, (alvo[0] - ponta[0], alvo[1] - ponta[1]))
