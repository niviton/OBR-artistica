"""Cena 2 (2 dedos): a porta do castelo — segure 2 dedos para abrir."""

import math
import random

import pygame

import generic_art as arte
from core.effects import (Particulas, blit_centro, brilho_aditivo, clamp, ease_back, ease_out, lerp,
                          preaquecer_brilhos)
from core.text import texto
from scenes.base import Scene

GESTO_DA_PORTA = 2
ANGULO_ABERTA = math.radians(78)
DUR_ABERTURA = 1.6
ANEL_CENTRO, ANEL_RAIO = (arte.PORTA["cx"], 600), 430
NIVEIS_SOMBRA = 12
ESTILO_DICA = {"tamanho": 42, "cor": (240, 230, 210), "esp": 3}
ESTILO_MSG = {"tamanho": 104, "cor": (255, 222, 110), "esp": 6}
CORES_LUZ = [(255, 210, 120), (255, 250, 210), (255, 170, 80), (255, 240, 190)]


def _escurecidas(folha):
    """Cópias da folha cada vez mais escuras (sombra conforme a porta gira)."""
    lista = []
    for i in range(NIVEIS_SOMBRA):
        v = int(255 * (1 - 0.5 * i / (NIVEIS_SOMBRA - 1)))
        f = folha.copy()
        f.fill((v, v, v, 255), special_flags=pygame.BLEND_RGBA_MULT)
        lista.append(f)
    return lista


class CenaPorta(Scene):
    nome = "cena2"
    titulo = "A porta do castelo"
    som_na_entrada = False   # o som.* desta cena toca quando a porta abre

    def preparar(self):
        self.fundo = arte.porta_cena()
        esq, dir_ = arte.porta_folhas()
        self.folhas = {+1: _escurecidas(esq), -1: _escurecidas(dir_)}
        self.escuro, self.luz = arte.porta_interiores()
        self.raios, self.raios_pos = arte.raios_porta()
        self.part = Particulas(400)
        self.tempo = float(self.app.cfg["porta"]["tempo_desafio"])
        self.descida = float(self.app.cfg["porta"]["velocidade_descida"])
        preaquecer_brilhos(CORES_LUZ, (6, 18))
        texto(self.falas.get("dica", ""), **ESTILO_DICA)
        texto(self.falas.get("mensagem", ""), **ESTILO_MSG)

    def enter(self):
        super().enter()
        self.prog = 0.0
        self.aberta = False
        self.t_aberta = 0.0
        self.auto = False
        self.segurando = False
        self.cache_aberta = None
        self.part.lista.clear()

    def on_key(self, tecla):
        # Plano B: apertar 2 de novo nesta cena "segura" o gesto automaticamente.
        if tecla in (pygame.K_2, pygame.K_KP2) and not self.aberta:
            self.auto = True
            return True
        return False

    def update(self, dt):
        super().update(dt)
        self.segurando = self.auto or self.app.ctx.gesto_mantido == GESTO_DA_PORTA
        if not self.aberta:
            if self.segurando:
                self.prog += dt / max(self.tempo, 0.1)
            else:
                self.prog -= dt * self.descida   # soltou: o progresso desce devagar
            self.prog = clamp(self.prog)
            if self.prog >= 1:
                self._abrir()
        elif random.random() < dt * 30:
            self.part.emitir(arte.PORTA["cx"] + random.uniform(-200, 200), random.uniform(350, 900),
                             "brilho", vel=(0, -40), espalhar=(40, 20), dur=(1.0, 2.2), tam=(6, 12),
                             cores=CORES_LUZ[::3])
        self.part.update(dt)

    def _abrir(self):
        self.aberta = True
        self.t_aberta = self.t
        self.som_evento("porta")
        cx, cy = arte.PORTA["cx"], arte.PORTA["centro_arco"] + 150
        self.part.emitir(cx, cy, "brilho", n=70, espalhar=(420, 320), dur=(0.8, 2.0), tam=(8, 18),
                         cores=CORES_LUZ[:3])
        self.part.emitir(cx, cy, "estrela", n=24, vel=(0, -200), espalhar=(380, 200), dur=(1.5, 2.5),
                         tam=(10, 18), cores=[(255, 215, 90), (255, 250, 220)])
        # Futuro: avisar o ESP32/Spike que a porta abriu (ex.: girar um motor de verdade).

    def draw(self, frame):
        t = self.t
        P = arte.PORTA
        if not self.desenhar_fundo_proprio(frame):
            frame.blit(self.fundo, (0, 0))
        self._tochas(frame, t)
        ix, iy = P["cx"] - P["larg"] // 2, P["topo"]
        ta = t - self.t_aberta if self.aberta else 0.0
        luz = ease_out(ta / 1.2) if self.aberta else 0.0
        frame.blit(self.escuro, (ix, iy))
        if luz > 0:
            self.luz.set_alpha(int(255 * luz))
            frame.blit(self.luz, (ix, iy))
            self.luz.set_alpha(255)
        self._porta(frame, ix, iy, ta)
        if luz > 0:
            nv = int(clamp(luz * (0.85 + 0.15 * math.sin(t * 2.5))) * (len(self.raios) - 1))
            frame.blit(self.raios[nv], self.raios_pos, special_flags=pygame.BLEND_ADD)
        if not self.aberta:
            self._anel(frame)
        estado = arte.COMEMORANDO if self.aberta else arte.FALANDO if self.segurando else arte.PARADO
        porteiro = self.personagem(arte.draw_generic_gatekeeper, estado, 470, olhar=1)
        frame.blit(porteiro, porteiro.get_rect(midbottom=(440, 1005)))
        self.part.draw(frame)
        if not self.aberta:
            dica = texto(self.falas.get("dica", ""), **ESTILO_DICA)
            blit_centro(frame, dica, (960, 1040), 170 + 85 * math.sin(t * 2.2))
        else:
            s = ease_back((ta - 0.5) / 0.6)
            if s > 0.01:
                msg = texto(self.falas.get("mensagem", ""), **ESTILO_MSG)
                blit_centro(frame, pygame.transform.rotozoom(msg, 0, s) if s < 0.999 else msg, (P["cx"], 110))

    def _porta(self, frame, ix, iy, ta):
        P = arte.PORTA
        if self.aberta and ta >= DUR_ABERTURA:   # totalmente aberta: desenha do cache
            if self.cache_aberta is None:
                self.cache_aberta = pygame.Surface((P["larg"], P["alt"]), pygame.SRCALPHA)
                self._folhas(self.cache_aberta, 0, 0, ANGULO_ABERTA, 0)
            frame.blit(self.cache_aberta, (ix, iy))
            return
        ang = ease_out(ta / DUR_ABERTURA) * ANGULO_ABERTA if self.aberta else 0.0
        vib = random.uniform(-1, 1) * 4 * self.prog if (self.segurando and not self.aberta) else 0
        self._folhas(frame, ix, iy, ang, vib)

    def _folhas(self, dest, ix, iy, ang, dx):
        """As duas folhas girando para dentro, com perspectiva (fatias verticais)."""
        larg = arte.PORTA["larg"]
        for lado, x_dobradica in ((+1, ix), (-1, ix + larg)):
            if ang <= 0.001:
                folha = self.folhas[lado][0]
                dest.blit(folha, ((x_dobradica if lado > 0 else x_dobradica - folha.get_width()) + dx, iy))
                continue
            cosa, sina = math.cos(ang), math.sin(ang)
            folha = self.folhas[lado][min(NIVEIS_SOMBRA - 1, int(sina * NIVEIS_SOMBRA))]
            w, h = folha.get_size()
            n = 24
            tira = w / n
            for i in range(n):
                u0, u1 = i / n, (i + 1) / n
                src_x = round(i * tira) if lado > 0 else round(w - (i + 1) * tira)
                src_w = max(1, min(w - src_x, math.ceil(tira)))
                x0 = x_dobradica + lado * u0 * w * cosa
                x1 = x_dobradica + lado * u1 * w * cosa
                esc = 1 - 0.22 * ((u0 + u1) / 2) * sina   # a borda livre fica mais longe
                hh = max(1, int(h * esc))
                fatia = pygame.transform.scale(folha.subsurface((src_x, 0, src_w, h)),
                                               (max(1, math.ceil(abs(x1 - x0)) + 1), hh))
                dest.blit(fatia, (min(x0, x1), iy + (h - hh) / 2))

    def _anel(self, frame):
        """Barra de progresso circular em volta da porta."""
        cx, cy = ANEL_CENTRO
        pygame.draw.circle(frame, (30, 24, 30), (cx, cy), ANEL_RAIO, 20)
        pygame.draw.circle(frame, (80, 66, 60), (cx, cy), ANEL_RAIO, 12)
        if self.prog <= 0.003:
            return
        n = max(2, int(140 * self.prog))
        pts = []
        for i in range(n + 1):
            a = -math.pi / 2 + 2 * math.pi * self.prog * i / n
            pts.append((cx + math.cos(a) * ANEL_RAIO, cy + math.sin(a) * ANEL_RAIO))
        cor = (255, int(lerp(170, 230, self.prog)), int(lerp(60, 130, self.prog)))
        pygame.draw.lines(frame, cor, False, pts, 14)
        for p in (pts[0], pts[-1]):
            pygame.draw.circle(frame, cor, (int(p[0]), int(p[1])), 7)
        g = brilho_aditivo(40, (160, 120, 50))
        frame.blit(g, (pts[-1][0] - 40, pts[-1][1] - 40), special_flags=pygame.BLEND_ADD)

    def _tochas(self, frame, t):
        for i, (x, y) in enumerate(arte.TOCHAS):
            tremor = 0.85 + 0.1 * math.sin(t * 13 + i) + 0.05 * math.sin(t * 29 + i * 2)
            g = brilho_aditivo(int(170 * tremor) // 8 * 8, (110, 66, 22))
            frame.blit(g, (x - g.get_width() // 2, y - 30 - g.get_height() // 2), special_flags=pygame.BLEND_ADD)
            dx = math.sin(t * 9 + i) * 3
            pygame.draw.ellipse(frame, (255, 130, 40), (x - 18 + dx, y - 62 * tremor, 36, 62 * tremor))
            pygame.draw.ellipse(frame, (255, 220, 120), (x - 9 + dx * 1.3, y - 40 * tremor, 18, 36 * tremor))
