"""Cena 5 (5 dedos): finalização no palco. Enter faz o fade-out final."""

import math
import random

import pygame

import generic_art as arte
from core.effects import Particulas, blit_centro, clamp, ease_in_out, lerp
from core.text import texto
from scenes.base import Scene

T_TEXTO = 2.4          # quando o texto final começa a aparecer
LETRAS_POR_SEGUNDO = 7
DUR_CORTINA = 2.2
# Holofotes: x do topo, cor, fase, velocidade
HOLOFOTES = [(360, (95, 85, 60), 0.0, 0.7), (960, (90, 60, 90), 1.7, 0.55), (1560, (60, 80, 110), 3.1, 0.8)]
REGIAO_LUZ = (272, 1376)
ESTILO_FINAL = {"tamanho": 170, "cor": (255, 222, 110), "esp": 7}
ESTILO_SUB = {"tamanho": 56, "cor": (255, 255, 255), "esp": 4}   # x inicial e largura da área visível entre as cortinas abertas


class CenaFinal(Scene):
    nome = "cena5"
    titulo = "Finalização"

    def preparar(self):
        p = arte.palco()
        self.fundo, self.sanefa = p["fundo"], p["sanefa"]
        self.cortina_esq = p["cortina"]
        self.cortina_dir = pygame.transform.flip(p["cortina"], True, False)
        meia = (REGIAO_LUZ[1] // 2, 540)
        self.luz_meia = pygame.Surface(meia).convert()
        self.camada = pygame.Surface(meia).convert()
        self.luz_grande = pygame.Surface((REGIAO_LUZ[1], 1080)).convert()
        self.festa = Particulas(600)
        self.fade_final = float(self.app.cfg["final"]["fade_final"])
        self._preto = pygame.Surface((1920, 1080)).convert()
        final = self.falas.get("texto_final", "")
        for n in range(1, len(final) + 1):   # pré-gera cada etapa da máquina de escrever
            texto(final[:n], **ESTILO_FINAL)
        texto(self.falas.get("subtitulo", ""), **ESTILO_SUB)

    def enter(self):
        super().enter()
        self.festa.lista.clear()
        self.t_fim = None
        if not self.assets.som:
            self.app.audio.tocar_generico("aplausos", 0.8)

    def on_key(self, tecla):
        if tecla in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.t_fim is None:
            self.t_fim = self.t
            if self.app.audio.ok:
                pygame.mixer.fadeout(int(self.fade_final * 1000))
            print("[final] fade-out iniciado")
            return True
        return False

    def update(self, dt):
        super().update(dt)
        if self.t > 0.8:
            if random.random() < dt * 55:
                self.festa.emitir(random.uniform(0, 1920), -20, "confete", vel=(0, 140), espalhar=(60, 40),
                                  dur=(7, 10), tam=(6, 11))
            if random.random() < dt * 6:
                self.festa.emitir(random.uniform(100, 1820), -30, "estrela", vel=(0, 150), espalhar=(30, 40),
                                  dur=(7, 9), tam=(10, 18), cores=[(255, 215, 80), (255, 250, 220)])
        self.festa.update(dt)

    def draw(self, frame):
        t = self.t
        if not self.desenhar_fundo_proprio(frame):
            frame.blit(self.fundo, (0, 0))
        self._holofotes(frame, t)
        menino = self.personagem(arte.draw_generic_boy, arte.COMEMORANDO, 500)
        frame.blit(menino, menino.get_rect(midbottom=(960, 960)))
        f = ease_in_out(t / DUR_CORTINA)
        frame.blit(self.cortina_esq, (lerp(960 - 760, -470, f), 0))
        frame.blit(self.cortina_dir, (lerp(960, 1920 - 290, f), 0))
        frame.blit(self.sanefa, (0, 0))
        self.festa.draw(frame)
        self._texto_final(frame, t)
        if self.t_fim is not None:
            self._preto.set_alpha(int(255 * clamp((t - self.t_fim) / max(self.fade_final, 0.1))))
            frame.blit(self._preto, (0, 0))

    def _holofotes(self, frame, t):
        """Cones de luz em meia resolução, desfocados e ampliados. Só a área entre as
        cortinas recebe luz (o resto fica atrás delas), o que economiza tempo."""
        e = 0.5
        ox = REGIAO_LUZ[0]
        self.luz_meia.fill((0, 0, 0))
        for x0, cor, fase, vel in HOLOFOTES:
            ang = math.sin(t * vel + fase) * 0.42
            self.camada.fill((0, 0, 0))
            topo = ((x0 - ox) * e, -10)
            comp = 1250 * e
            for abertura, mult in ((0.19, 0.22), (0.14, 0.34), (0.09, 0.46), (0.045, 0.6)):
                pts = [topo,
                       (topo[0] + math.sin(ang - abertura) * comp, topo[1] + math.cos(ang - abertura) * comp),
                       (topo[0] + math.sin(ang + abertura) * comp, topo[1] + math.cos(ang + abertura) * comp)]
                pygame.draw.polygon(self.camada, tuple(int(v * mult) for v in cor), pts)
            chao_y = 900 * e
            px = topo[0] + math.tan(ang) * (chao_y - topo[1])
            pygame.draw.ellipse(self.camada, tuple(int(v * 0.75) for v in cor), (px - 70, chao_y - 18, 140, 36))
            self.luz_meia.blit(self.camada, (0, 0), special_flags=pygame.BLEND_ADD)
        w, h = self.luz_meia.get_size()
        pygame.transform.smoothscale(pygame.transform.smoothscale(self.luz_meia, (w // 4, h // 4)), (w, h),
                                     self.luz_meia)
        pygame.transform.scale(self.luz_meia, (REGIAO_LUZ[1], 1080), self.luz_grande)
        frame.blit(self.luz_grande, (ox, 0), special_flags=pygame.BLEND_ADD)

    def _texto_final(self, frame, t):
        final = self.falas.get("texto_final", "")
        if t < T_TEXTO or not final:
            return
        n = min(len(final), int((t - T_TEXTO) * LETRAS_POR_SEGUNDO) + 1)
        completo = texto(final, **ESTILO_FINAL)
        y = 265
        if n < len(final):
            parte = texto(final[:n], **ESTILO_FINAL)
            frame.blit(parte, (960 - completo.get_width() // 2, y - completo.get_height() // 2))
        else:   # loop suave: o texto flutua de leve
            blit_centro(frame, completo, (960, y + math.sin(t * 2) * 8))
            sub = self.falas.get("subtitulo", "")
            t_completo = T_TEXTO + len(final) / LETRAS_POR_SEGUNDO
            if sub:
                blit_centro(frame, texto(sub, **ESTILO_SUB), (960, 400),
                            255 * clamp((t - t_completo - 0.4) / 1.0))
