"""Fontes, texto com contorno e balão de fala (com cache)."""

import math
from functools import lru_cache

import pygame

NOMES_FONTE = "arialroundedmtbold,segoeuiblack,segoeuibold,trebuchetms,verdana,arial"
_fontes = {}

COR_CONTORNO = (34, 24, 38)


def fonte(tamanho, negrito=True):
    chave = (tamanho, negrito)
    if chave not in _fontes:
        _fontes[chave] = pygame.font.SysFont(NOMES_FONTE, tamanho, bold=negrito)
    return _fontes[chave]


@lru_cache(maxsize=512)
def texto(conteudo, tamanho, cor=(255, 255, 255), contorno=COR_CONTORNO, esp=4, sombra=True):
    """Texto com contorno grosso e sombra suave — legível sobre qualquer fundo."""
    f = fonte(tamanho)
    base = f.render(conteudo, True, cor)
    if not esp and not sombra:
        return base
    off = 8 if sombra else 0
    s = pygame.Surface((base.get_width() + 2 * esp + off, base.get_height() + 2 * esp + off),
                       pygame.SRCALPHA)
    if sombra:
        sm = f.render(conteudo, True, (0, 0, 0))
        sm.set_alpha(110)
        s.blit(sm, (esp + off, esp + off))
    if esp:
        cont = f.render(conteudo, True, contorno)
        for i in range(16):
            a = i * math.pi / 8
            s.blit(cont, (esp + round(math.cos(a) * esp), esp + round(math.sin(a) * esp)))
    s.blit(base, (esp, esp))
    return s


def quebrar_linhas(conteudo, f, largura_max):
    linhas, atual = [], ""
    for palavra in conteudo.split():
        teste = (atual + " " + palavra).strip()
        if f.size(teste)[0] <= largura_max or not atual:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


@lru_cache(maxsize=256)
def balao(conteudo, visiveis=None, largura_max=680, tamanho=46, cauda=0.75,
          cor=(255, 252, 240), cor_texto=(40, 30, 50)):
    """Balão de fala. `visiveis` = quantos caracteres mostrar (efeito máquina de escrever).
    O tamanho do balão já considera o texto completo, para não 'pular' enquanto digita.
    `cauda` = posição horizontal (0..1) da pontinha embaixo.
    Retorna (surface, (x, y) da ponta da cauda dentro da surface)."""
    f = fonte(tamanho)
    linhas = quebrar_linhas(conteudo, f, largura_max)
    alt_linha = f.get_linesize()
    pad, borda, alt_cauda = 34, 6, 60
    w = max(f.size(l)[0] for l in linhas) + pad * 2
    h = alt_linha * len(linhas) + pad * 2
    s = pygame.Surface((w + borda * 2 + 12, h + borda * 2 + alt_cauda + 12), pygame.SRCALPHA)
    caixa = pygame.Rect(borda, borda, w, h)
    # sombra
    sombra = caixa.move(10, 10)
    pygame.draw.rect(s, (0, 0, 0, 70), sombra, border_radius=40)
    # cauda (triângulo) com contorno
    cx = borda + w * cauda
    tri = [(cx - 40, borda + h - 8), (cx + 20, borda + h - 8), (cx + 45, borda + h + alt_cauda)]
    pygame.draw.polygon(s, COR_CONTORNO, tri)
    pygame.draw.rect(s, COR_CONTORNO, caixa.inflate(borda * 2, borda * 2), border_radius=46)
    pygame.draw.rect(s, cor, caixa, border_radius=40)
    tri_int = [(cx - 30, borda + h - 12), (cx + 14, borda + h - 12), (cx + 36, borda + h + alt_cauda - 16)]
    pygame.draw.polygon(s, cor, tri_int)
    # texto (só os primeiros `visiveis` caracteres)
    restante = len(conteudo) if visiveis is None else visiveis
    for i, linha in enumerate(linhas):
        if restante <= 0:
            break
        parte = linha[:restante]
        restante -= len(linha) + 1
        s.blit(f.render(parte, True, cor_texto), (borda + pad, borda + pad + i * alt_linha))
    return s, (cx + 45, borda + h + alt_cauda)
