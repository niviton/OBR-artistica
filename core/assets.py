"""Carrega os arquivos de assets/cenaN (se existirem) uma única vez, com cache.

Cada pasta aceita:
    fundo.png | fundo.jpg | fundo.jpeg   -> imagem de fundo (cobre a tela)
    video.mp4                            -> vídeo de fundo em loop (tem prioridade sobre o fundo)
    personagem.png                       -> personagem com fundo transparente
    som.wav | som.mp3 | som.ogg          -> som tocado ao entrar na cena
O que faltar é substituído pelo visual/som genérico gerado por código.
"""

import os

import cv2
import pygame

from core.effects import LARGURA, ALTURA


def _primeiro(pasta, nome, extensoes):
    for ext in extensoes:
        caminho = os.path.join(pasta, f"{nome}.{ext}")
        if os.path.isfile(caminho):
            return caminho
    return None


def _cobrir(img, w=LARGURA, h=ALTURA):
    """Escala mantendo proporção e corta o excesso (como 'cover' no CSS)."""
    iw, ih = img.get_size()
    escala = max(w / iw, h / ih)
    nova = pygame.transform.smoothscale(img, (max(1, round(iw * escala)), max(1, round(ih * escala))))
    r = nova.get_rect(center=(w // 2, h // 2))
    tela = pygame.Surface((w, h)).convert()
    tela.blit(nova, r)
    return tela


class CenaAssets:
    def __init__(self):
        self.fundo = None        # Surface 1920x1080 ou None
        self.personagem = None   # Surface com alpha ou None
        self.video = None        # caminho do .mp4 ou None
        self.som = None          # pygame.mixer.Sound ou None
        self.faltando = []       # para o aviso discreto do HUD

    @property
    def aviso(self):
        if not self.faltando:
            return ""
        return "genérico: " + ", ".join(self.faltando)


class AssetManager:
    def __init__(self, pasta, audio, so_genericos=False):
        self.pasta = pasta
        self.audio = audio
        self.so_genericos = so_genericos
        self._cache = {}

    def cena(self, nome):
        if nome not in self._cache:
            self._cache[nome] = self._carregar(nome)
        return self._cache[nome]

    def _carregar(self, nome):
        a = CenaAssets()
        pasta = os.path.join(self.pasta, nome)
        if self.so_genericos or not os.path.isdir(pasta):
            a.faltando = ["fundo", "personagem", "som"]
            return a
        caminho = _primeiro(pasta, "fundo", ("png", "jpg", "jpeg"))
        if caminho:
            try:
                a.fundo = _cobrir(pygame.image.load(caminho).convert())
                print(f"[assets] {nome}: fundo {os.path.basename(caminho)}")
            except pygame.error as e:
                print(f"AVISO: não consegui abrir {caminho} ({e}).")
        caminho = _primeiro(pasta, "video", ("mp4",))
        if caminho:
            teste = cv2.VideoCapture(caminho)
            if teste.isOpened():
                a.video = caminho
                print(f"[assets] {nome}: vídeo {os.path.basename(caminho)}")
            else:
                print(f"AVISO: não consegui abrir o vídeo {caminho}.")
            teste.release()
        caminho = _primeiro(pasta, "personagem", ("png",))
        if caminho:
            try:
                a.personagem = pygame.image.load(caminho).convert_alpha()
                print(f"[assets] {nome}: personagem {os.path.basename(caminho)}")
            except pygame.error as e:
                print(f"AVISO: não consegui abrir {caminho} ({e}).")
        caminho = _primeiro(pasta, "som", ("wav", "mp3", "ogg"))
        if caminho:
            a.som = self.audio.carregar(caminho)
            if a.som:
                print(f"[assets] {nome}: som {os.path.basename(caminho)}")
        if a.fundo is None and a.video is None:
            a.faltando.append("fundo")
        if a.personagem is None:
            a.faltando.append("personagem")
        if a.som is None:
            a.faltando.append("som")
        return a


class VideoFundo:
    """Toca um .mp4 em loop como fundo, avançando pelo dt (não pelo FPS da tela)."""

    def __init__(self, caminho):
        self.cap = cv2.VideoCapture(caminho)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.acumulado = 0.0
        self.surface = None
        self._ler()

    def _ler(self):
        ok, frame = self.cap.read()
        if not ok:  # fim do vídeo -> volta ao início
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
            if not ok:
                return
        frame = cv2.resize(frame, (LARGURA, ALTURA), interpolation=cv2.INTER_LINEAR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.surface = pygame.image.frombuffer(frame.tobytes(), (LARGURA, ALTURA), "RGB")

    def update(self, dt):
        self.acumulado += dt
        passos = 0
        while self.acumulado >= 1 / self.fps and passos < 3:
            self.acumulado -= 1 / self.fps
            passos += 1
            if passos == 1:
                continue
            self.cap.grab()  # pula frames atrasados sem decodificar
        if passos:
            self._ler()
        self.acumulado = min(self.acumulado, 1 / self.fps)

    def draw(self, frame):
        if self.surface:
            frame.blit(self.surface, (0, 0))

    def fechar(self):
        self.cap.release()
