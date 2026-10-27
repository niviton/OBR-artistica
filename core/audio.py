"""Áudio com pygame.mixer: volume, fade e modo mudo. Nunca derruba o programa."""

import pygame

import generic_sounds


class Audio:
    def __init__(self, cfg_audio):
        self.ativo = bool(cfg_audio["ativado"])
        self.volume = float(cfg_audio["volume"])
        self.fade_ms = int(cfg_audio["fade_ms"])
        self.ok = False
        self.genericos = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 2, 512)
            pygame.mixer.set_num_channels(24)
            self.ok = True
        except pygame.error as e:
            print(f"AVISO: áudio indisponível ({e}). O programa segue sem som.")
            return
        try:
            self.genericos = generic_sounds.criar_todos()
        except Exception as e:
            print(f"AVISO: não consegui gerar os sons genéricos ({e}).")

    def carregar(self, caminho):
        if not self.ok:
            return None
        try:
            return pygame.mixer.Sound(caminho)
        except pygame.error as e:
            print(f"AVISO: não consegui carregar o som {caminho} ({e}).")
            return None

    def tocar(self, som, volume=1.0, loops=0, fade=True):
        if not (self.ok and self.ativo and som):
            return None
        canal = som.play(loops=loops, fade_ms=self.fade_ms if fade else 0)
        if canal:
            canal.set_volume(max(0.0, min(1.0, volume * self.volume)))
        return canal

    def tocar_generico(self, nome, volume=1.0):
        return self.tocar(self.genericos.get(nome), volume, fade=False)

    def parar_canal(self, canal):
        if canal and self.ok:
            canal.fadeout(self.fade_ms)

    def parar_tudo(self):
        if self.ok:
            pygame.mixer.fadeout(self.fade_ms)

    def alternar_mudo(self):
        self.ativo = not self.ativo
        if not self.ativo and self.ok:
            pygame.mixer.stop()
        return self.ativo
