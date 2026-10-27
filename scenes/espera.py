"""Tela de espera: céu escuro com estrelas suaves e convite para começar."""

import math
import random

import pygame

from core.effects import (CampoEstrelas, brilho_aditivo, blit_centro, gradiente_vertical,
                          vinheta, LARGURA, ALTURA)
from core.text import texto
from scenes.base import Scene


class TelaEspera(Scene):
    nome = "espera"
    titulo = "Tela de espera"

    def preparar(self):
        fundo = gradiente_vertical(LARGURA, ALTURA, [(3, 3, 14), (12, 10, 34), (26, 18, 54)])
        fundo.blit(vinheta(LARGURA, ALTURA, 160), (0, 0))
        fundo.blit(brilho_aditivo(560, (26, 20, 48)), (960 - 560, 560 - 560), special_flags=pygame.BLEND_ADD)
        self.fundo = fundo.convert()
        self.camadas = [
            CampoEstrelas(160, seed=1, deriva=(3, 0), tamanhos=(1, 2, 2)),
            CampoEstrelas(70, seed=2, deriva=(7, 0), tamanhos=(2, 3, 3)),
            CampoEstrelas(22, seed=3, deriva=(12, 0), tamanhos=(3, 4, 6)),
        ]
        self.cometa = None

    def enter(self):
        super().enter()
        self.proximo_cometa = 3.0

    def update(self, dt):
        super().update(dt)
        for c in self.camadas:
            c.update(dt)
        if self.cometa is None and self.t >= self.proximo_cometa:
            self.cometa = [random.uniform(700, 1900), random.uniform(-40, 300), 0.0]
            self.proximo_cometa = self.t + random.uniform(5, 9)
        if self.cometa:
            self.cometa[2] += dt
            if self.cometa[2] > 1.3:
                self.cometa = None

    def draw(self, frame):
        frame.blit(self.fundo, (0, 0))
        for i, c in enumerate(self.camadas):
            c.draw(frame, (math.sin(self.t * 0.15) * 6 * (i + 1), 0))
        if self.cometa:
            x0, y0, vida = self.cometa
            f = vida / 1.3
            for k in range(14):
                tk = max(0.0, vida - k * 0.02)
                x, y = x0 - 900 * tk, y0 + 380 * tk
                luz = (1 - k / 14) * math.sin(math.pi * f)
                frame.blit(brilho_aditivo(10, (200, 200, 255), round(luz, 1)), (x - 10, y - 10),
                           special_flags=pygame.BLEND_ADD)
        pulso = 0.5 + 0.5 * math.sin(self.t * 1.8)
        msg = texto(self.falas.get("texto", ""), 76, (238, 232, 255), (18, 14, 40), 3)
        blit_centro(frame, msg, (960, 560), 150 + 105 * pulso)
