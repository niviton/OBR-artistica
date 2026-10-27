"""Cena 3 (3 dedos): o menino entra, acena e conversa com a plateia."""

import math
import random

import pygame

import generic_art as arte
from core.effects import Particulas, ease_back, ease_out, lerp, mascara_holofote, preaquecer_brilhos
from core.text import balao
from scenes.base import Scene

DUR_ENTRADA = 1.8
X_INICIO, X_FINAL, CHAO_Y = 2150, 1280, 1010
ALTURA_MENINO = 520
VELOCIDADE_TEXTO = 28   # letras por segundo


class CenaMenino(Scene):
    nome = "cena3"
    titulo = "Cena do menino"

    def preparar(self):
        self.sala = arte.sala()
        self.holofote = mascara_holofote(340, escuridao=150, suavidade=0.55)
        self.poeira = Particulas(80)
        self._cache = None
        preaquecer_brilhos([(255, 230, 170)], (3, 6))

    def enter(self):
        super().enter()
        self.poeira.lista.clear()
        self._cache = None
        if not self.assets.som:
            self.app.audio.tocar_generico("ding", 0.6)

    def update(self, dt):
        super().update(dt)
        if random.random() < dt * 10:   # poeirinha brilhando na luz
            self.poeira.emitir(self._x() + random.uniform(-260, 260), random.uniform(350, 950), "brilho",
                               vel=(0, -12), espalhar=(8, 6), dur=(2.0, 4.0), tam=(3, 6),
                               cores=[(255, 230, 170)])
        self.poeira.update(dt)

    def _x(self):
        return lerp(X_INICIO, X_FINAL, ease_out(self.t / DUR_ENTRADA))

    def draw(self, frame):
        t = self.t
        x = self._x()
        entrando = t < DUR_ENTRADA
        self._fundo_com_holofote(frame, int(x), entrando)
        estado = arte.ANDANDO if entrando else arte.FALANDO
        menino = self.personagem(arte.draw_generic_boy, estado, ALTURA_MENINO)
        if entrando:  # leve balanço enquanto desliza
            menino = pygame.transform.rotozoom(menino, math.sin(t * 7) * 5 * (1 - t / DUR_ENTRADA), 1.0)
        frame.blit(menino, menino.get_rect(midbottom=(x, CHAO_Y)))
        self.poeira.draw(frame)
        self._fala(frame, x)

    def _fundo_com_holofote(self, frame, cx, movendo):
        """Fundo escurecido nas bordas, com a luz no menino. Parado = vem do cache."""
        cy = 700
        area = pygame.Rect(1920 - cx, 1080 - cy, 1920, 1080)
        if self._video or movendo:
            if not self.desenhar_fundo_proprio(frame):
                frame.blit(self.sala, (0, 0))
            frame.blit(self.holofote, (0, 0), area=area)
            return
        if self._cache is None:
            self._cache = pygame.Surface((1920, 1080)).convert()
            fundo = self.assets.fundo if self.assets.fundo is not None else self.sala
            self._cache.blit(fundo, (0, 0))
            self._cache.blit(self.holofote, (0, 0), area=area)
        frame.blit(self._cache, (0, 0))

    def _fala(self, frame, x):
        falas = self.falas.get("falas") or [""]
        seg = float(self.falas.get("segundos_por_fala", 4.0))
        inicio = DUR_ENTRADA + 0.3
        if self.t < inicio:
            return
        decorrido = self.t - inicio
        idx = int(decorrido // seg) % len(falas)
        local = decorrido % seg
        fala = falas[idx]
        surf, ponta = balao(fala, min(len(fala), int(local * VELOCIDADE_TEXTO)), cauda=0.82)
        esc = ease_back(local / 0.35)
        alvo = (x - 70, CHAO_Y - ALTURA_MENINO + 60)
        if esc < 0.999:
            w, h = surf.get_size()
            surf = pygame.transform.rotozoom(surf, 0, max(0.01, esc))
            ponta = (ponta[0] * surf.get_width() / w, ponta[1] * surf.get_height() / h)
        frame.blit(surf, (alvo[0] - ponta[0], alvo[1] - ponta[1]))
