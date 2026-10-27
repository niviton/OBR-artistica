"""Efeitos sonoros sintetizados com numpy (usados quando falta som.wav/mp3 na cena)."""

import numpy as np
import pygame

TAXA = 44100
_rng = np.random.default_rng(7)


def _t(segundos):
    return np.arange(int(TAXA * segundos)) / TAXA


def _suavizar(sinal, n):
    return np.convolve(sinal, np.ones(n) / n, mode="same")


def ding():
    """Sininho suave."""
    t = _t(1.8)
    s = (np.sin(2 * np.pi * 880 * t) + 0.45 * np.sin(2 * np.pi * 1762 * t)
         + 0.2 * np.sin(2 * np.pi * 2641 * t))
    return s * np.exp(-t * 2.8) * (1 - np.exp(-t * 300))


def rangido_porta():
    """Porta velha rangendo + batida grave no fim."""
    t = _t(1.9)
    freq = 95 + 45 * np.sin(2 * np.pi * 0.55 * t) + _suavizar(_rng.normal(0, 25, t.size), 800)
    fase = np.cumsum(freq) / TAXA
    serra = 2 * (fase % 1.0) - 1
    tremido = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * 6.5 * t + _suavizar(_rng.normal(0, 3, t.size), 400)))
    s = _suavizar(serra * tremido, 6)
    s *= np.clip(t / 0.15, 0, 1) * np.clip((1.6 - t) / 0.4, 0, 1)
    batida = np.sin(2 * np.pi * 55 * t) * np.exp(-np.clip(t - 1.55, 0, None) * 18) * (t > 1.55)
    return 0.7 * s + 0.8 * batida


def estouro_bolha(tom=1.0):
    """'Plop' curtinho de bolha."""
    t = _t(0.09)
    freq = (1100 * tom) * np.exp(-t * 18)
    s = np.sin(2 * np.pi * np.cumsum(freq) / TAXA) * np.exp(-t * 55)
    return s + 0.25 * _rng.normal(0, 1, t.size) * np.exp(-t * 250)


def aplausos(segundos=4.5):
    """Plateia batendo palmas (palmas individuais somadas)."""
    n = int(TAXA * segundos)
    s = np.zeros(n)
    nucleos = []
    for _ in range(6):
        k = int(TAXA * _rng.uniform(0.006, 0.012))
        ruido = np.diff(_rng.normal(0, 1, k + 1))  # agudo, como uma palma
        nucleos.append(ruido * np.exp(-np.arange(k) / (k / 4)))
    for _ in range(int(segundos * 45)):
        inicio = _rng.integers(0, n - 700)
        nucleo = nucleos[_rng.integers(len(nucleos))]
        s[inicio:inicio + nucleo.size] += nucleo * _rng.uniform(0.3, 1.0)
    t = np.arange(n) / TAXA
    return s * np.clip(t / 0.6, 0, 1) * np.clip((segundos - t) / 1.2, 0, 1)


def para_som(mono, volume=0.8):
    """numpy mono (-1..1) -> pygame.mixer.Sound no formato do mixer."""
    pico = np.max(np.abs(mono)) or 1.0
    dados = (mono / pico * volume * 32767).astype(np.int16)
    _, _, canais = pygame.mixer.get_init()
    if canais > 1:
        dados = np.repeat(dados[:, None], canais, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(dados))


def criar_todos():
    return {
        "ding": para_som(ding(), 0.6),
        "porta": para_som(rangido_porta(), 0.8),
        "bolha0": para_som(estouro_bolha(0.8), 0.35),
        "bolha1": para_som(estouro_bolha(1.0), 0.35),
        "bolha2": para_som(estouro_bolha(1.3), 0.35),
        "aplausos": para_som(aplausos(), 0.7),
    }
