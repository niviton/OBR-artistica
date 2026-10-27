"""Leitura de config.yaml e config/falas.json, com valores padrão para tudo."""

import copy
import json
import os

import yaml

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PADRAO = {
    "camera": {"indice": 0, "largura": 640, "altura": 480},
    "gestos": {"tempo_estavel": 0.5, "confianca_deteccao": 0.7,
               "confianca_rastreamento": 0.7, "inverter_lateralidade": False},
    "transicao": {"fade": 0.6},
    "porta": {"tempo_desafio": 3.0, "velocidade_descida": 0.35},
    "final": {"fade_final": 4.0},
    "audio": {"ativado": True, "volume": 0.7, "fade_ms": 500, "repetir_som_cena": False},
    "video": {"fps_alvo": 30, "tela_cheia": True, "escala_suave": True},
    "hud": {"mostrar": True, "canto_mini_camera": 1, "fracao_mini_camera": 0.25},
    "teste": {"duracao_cena": 3.0},
    "esp32": {"ativado": True, "nome": "PilarCastelo",
              "angulos": {"cena1": 180, "cena2": 0, "cena3": 90}},
}

FALAS_PADRAO = {
    "espera": {"texto": "Levante 1 dedo para começar"},
    "cena1": {"titulo": "Bem-vindos ao Castelo!", "subtitulo": ""},
    "cena2": {"dica": "Mantenha 2 dedos para abrir a porta", "mensagem": "A porta se abriu!"},
    "cena3": {"falas": ["Oi, pessoal!"], "segundos_por_fala": 4.0},
    "cena4": {"texto": "Hora do banho!"},
    "cena5": {"texto_final": "Obrigado!", "subtitulo": ""},
}


def _mesclar(base, extra):
    for chave, valor in (extra or {}).items():
        if isinstance(valor, dict) and isinstance(base.get(chave), dict):
            _mesclar(base[chave], valor)
        else:
            base[chave] = valor
    return base


def carregar_config(caminho=None):
    caminho = caminho or os.path.join(PASTA_PROJETO, "config.yaml")
    cfg = copy.deepcopy(PADRAO)
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                _mesclar(cfg, yaml.safe_load(f))
        except yaml.YAMLError as e:
            print(f"AVISO: erro ao ler {caminho} ({e}). Usando valores padrão.")
    else:
        print(f"AVISO: {caminho} não encontrado. Usando valores padrão.")
    return cfg


def carregar_falas(caminho=None):
    caminho = caminho or os.path.join(PASTA_PROJETO, "config", "falas.json")
    falas = copy.deepcopy(FALAS_PADRAO)
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding="utf-8") as f:
                _mesclar(falas, json.load(f))
        except json.JSONDecodeError as e:
            print(f"AVISO: erro no JSON de {caminho} ({e}). Usando falas padrão.")
    return falas
