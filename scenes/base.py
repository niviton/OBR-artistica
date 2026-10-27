"""Classe base das cenas e gerenciador com transição suave (fade pelo preto)."""

import math

import pygame

import generic_art as arte
from core.assets import VideoFundo
from core.effects import LARGURA, ALTURA, clamp


class Scene:
    """Base de todas as cenas.

    Ciclo de vida (chamado pelo SceneManager):
        enter()  -> on_enter_hook()   quando a cena começa (meio do fade)
        update(dt) / draw(frame)      a cada quadro; dt em segundos
        exit()   -> on_exit_hook()    quando a cena termina

    Para criar uma cena nova: herde de Scene, defina `nome` (= pasta em assets/)
    e `titulo`, gere seus visuais em `preparar()` e registre em scenes/__init__.py.
    """

    nome = "base"
    titulo = "Cena"
    som_na_entrada = True   # toca assets/<nome>/som.* ao entrar

    def __init__(self, app):
        self.app = app
        self.assets = app.assets.cena(self.nome)
        self.falas = app.falas.get(self.nome, {})
        self.t = 0.0
        self._video = None
        self._canal = None
        self.preparar()

    # ------------------------------------------------------------ ciclo de vida
    def preparar(self):
        """Gera/carrega os visuais uma única vez (na abertura do programa)."""

    def enter(self):
        self.t = 0.0
        if self.assets.video:
            self._video = VideoFundo(self.assets.video)
        if self.som_na_entrada and self.assets.som:
            repetir = self.app.cfg["audio"]["repetir_som_cena"]
            self._canal = self.app.audio.tocar(self.assets.som, loops=-1 if repetir else 0)

    def update(self, dt):
        self.t += dt
        if self._video:
            self._video.update(dt)

    def draw(self, frame):
        frame.fill((0, 0, 0))

    def exit(self):
        if self._video:
            self._video.fechar()
            self._video = None
        self.app.audio.parar_canal(self._canal)
        self._canal = None

    # ------------------------------------------------------------ ganchos de hardware
    def on_enter_hook(self):
        """Chamado logo após enter(). Futuro: avisar ESP32 / Spike Prime que a cena começou."""

    def on_exit_hook(self):
        """Chamado logo após exit(). Futuro: desligar luzes/motores desta cena."""

    def on_key(self, tecla):
        """Teclas extras da cena. Retorne True se a tecla foi usada."""
        return False

    # ------------------------------------------------------------ ajudantes
    def desenhar_fundo_proprio(self, frame):
        """Desenha video.mp4 ou fundo.png/jpg se existirem. Retorna True se desenhou."""
        if self._video and self._video.surface:
            self._video.draw(frame)
            return True
        if self.assets.fundo:
            frame.blit(self.assets.fundo, (0, 0))
            return True
        return False

    def personagem(self, gerador, estado, altura, **kwargs):
        """personagem.png animado (se existir) ou o personagem genérico."""
        if self.assets.personagem:
            return animar_imagem(self.assets.personagem, self.t, estado, altura)
        return gerador(self.t, estado, altura=altura, **kwargs)

    def som_evento(self, generico, volume=1.0):
        """Para cenas com som_na_entrada=False: toca som.* da cena ou o genérico."""
        if self.assets.som:
            self._canal = self.app.audio.tocar(self.assets.som, volume)
        else:
            self.app.audio.tocar_generico(generico, volume)


_escalas = {}


def animar_imagem(img, t, estado, altura):
    """Animação procedural para um personagem.png: respiração, balanço e pulos."""
    chave = (id(img), altura)
    if chave not in _escalas:
        iw, ih = img.get_size()
        _escalas[chave] = pygame.transform.smoothscale(img, (max(1, round(iw * altura / ih)), altura))
    base = _escalas[chave]
    resp = math.sin(t * 2.4)
    sx, sy = 1 - 0.01 * resp, 1 + 0.018 * resp
    ang, pulo = 0.0, 0.0
    if estado == arte.ANDANDO:
        ang = math.sin(t * 9) * 4
        pulo = abs(math.sin(t * 9)) * 10
    elif estado == arte.COMEMORANDO:
        ang = math.sin(t * 6) * 6
        pulo = abs(math.sin(t * 5.5)) * 40
    elif estado == arte.FALANDO:
        ang = math.sin(t * 3) * 2
    w, h = base.get_size()
    s = pygame.transform.smoothscale(base, (max(1, round(w * sx)), max(1, round(h * sy))))
    if ang:
        s = pygame.transform.rotozoom(s, ang, 1.0)
    tela = pygame.Surface((s.get_width(), s.get_height() + 50), pygame.SRCALPHA)
    tela.blit(s, (0, 50 - pulo))
    return tela


class SceneManager:
    """Guarda todas as cenas (criadas uma vez) e troca entre elas com fade."""

    def __init__(self, app, classes, fade=0.6):
        self.app = app
        self.cenas = {}
        for cls in classes:
            print(f"  preparando {cls.nome} ({cls.titulo})...")
            self.cenas[cls.nome] = cls(app)
        self.fade = max(0.0, fade)
        self.atual = None
        self.destino = None
        self.fase = None     # None | "saindo" | "entrando"
        self.tf = 0.0
        self._preto = pygame.Surface((LARGURA, ALTURA)).convert()   # mesmo formato da tela = blit rápido
        self._preto.fill((0, 0, 0))

    def aquecer(self, frame):
        """Roda um quadro de cada cena sem som, para criar fontes e caches antes da peça
        (evita uma travadinha na primeira vez que cada cena aparece)."""
        audio = self.app.audio
        ativo, audio.ativo = audio.ativo, False
        try:
            for cena in self.cenas.values():
                cena.enter()
                cena.update(1 / 30)
                cena.draw(frame)
                cena.exit()
        finally:
            audio.ativo = ativo

    @property
    def nome_atual(self):
        return self.atual.nome if self.atual else "-"

    def ir_para(self, nome, reiniciar=False):
        if nome not in self.cenas:
            print(f"AVISO: cena '{nome}' não existe.")
            return
        alvo = self.cenas[nome]
        if not reiniciar and self.fase is None and self.atual is alvo:
            return
        self.destino = nome
        meia = self.fade / 2
        if self.atual is None or meia <= 0:
            self._trocar(nome)
            self.fase, self.tf = ("entrando", 0.0) if meia > 0 else (None, 0.0)
        elif self.fase == "entrando":   # inverte o fade a partir do ponto atual
            self.fase, self.tf = "saindo", max(0.0, meia - self.tf)
        elif self.fase is None:
            self.fase, self.tf = "saindo", 0.0

    def reiniciar(self):
        if self.atual:
            self.ir_para(self.atual.nome, reiniciar=True)

    def _trocar(self, nome):
        if self.atual:
            self.atual.exit()
            self.atual.on_exit_hook()
        self.atual = self.cenas[nome]
        self.atual.enter()
        self.atual.on_enter_hook()

    def update(self, dt):
        meia = self.fade / 2
        if self.fase == "saindo":
            self.tf += dt
            if self.tf >= meia:
                self._trocar(self.destino)
                self.fase, self.tf = "entrando", 0.0
        elif self.fase == "entrando":
            self.tf += dt
            if self.tf >= meia:
                self.fase = None
        if self.atual:
            self.atual.update(dt)

    def draw(self, frame):
        if not self.atual:
            frame.fill((0, 0, 0))
            return
        self.atual.draw(frame)
        meia = self.fade / 2
        if self.fase and meia > 0:
            f = clamp(self.tf / meia)
            escuro = f if self.fase == "saindo" else 1 - f
            self._preto.set_alpha(int(255 * escuro))
            frame.blit(self._preto, (0, 0))

    def on_key(self, tecla):
        return bool(self.atual and self.fase is None and self.atual.on_key(tecla))
