"""Detecção da mão e contagem de dedos com MediaPipe (Tasks API, mediapipe >= 0.10)."""

import os
import sys
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from core.config import PASTA_PROJETO

MODELO_PATH = os.path.join(PASTA_PROJETO, "models", "hand_landmarker.task")
MODELO_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
              "hand_landmarker/float16/latest/hand_landmarker.task")

# Índices dos 21 pontos da mão
PONTAS = [4, 8, 12, 16, 20]   # polegar, indicador, médio, anelar, mindinho
PIPS = [3, 6, 10, 14, 18]     # para o polegar usamos o IP (3)
CONEXOES = [(c.start, c.end) for c in vision.HandLandmarksConnections.HAND_CONNECTIONS]


def garantir_modelo():
    """Baixa o modelo do MediaPipe na primeira execução."""
    if os.path.exists(MODELO_PATH):
        return
    os.makedirs(os.path.dirname(MODELO_PATH), exist_ok=True)
    print(f"Baixando modelo de mãos para {MODELO_PATH} ...")
    try:
        urllib.request.urlretrieve(MODELO_URL, MODELO_PATH + ".tmp")
        os.replace(MODELO_PATH + ".tmp", MODELO_PATH)
    except Exception as e:
        sys.exit(f"ERRO: não consegui baixar o modelo ({e}).\n"
                 f"Baixe manualmente de {MODELO_URL}\ne salve em {MODELO_PATH}")
    print("Modelo baixado.")


class Mao:
    """Resultado da detecção de uma mão."""

    def __init__(self, pontos, lado, esticados):
        self.pontos = pontos        # 21 (x, y) normalizados 0..1 (imagem espelhada)
        self.lado = lado            # "Direita" / "Esquerda"
        self.esticados = esticados  # 5 bools: polegar..mindinho

    @property
    def total(self):
        return sum(self.esticados)


class DetectorDedos:
    def __init__(self, cfg_gestos):
        garantir_modelo()
        self.inverter = cfg_gestos["inverter_lateralidade"]
        opcoes = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODELO_PATH),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=cfg_gestos["confianca_deteccao"],
            min_hand_presence_confidence=cfg_gestos["confianca_deteccao"],
            min_tracking_confidence=cfg_gestos["confianca_rastreamento"],
        )
        self.landmarker = vision.HandLandmarker.create_from_options(opcoes)
        self._ultimo_ts = 0

    def detectar(self, frame_bgr_espelhado):
        rgb = cv2.cvtColor(frame_bgr_espelhado, cv2.COLOR_BGR2RGB)
        imagem = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        ts = max(int(time.monotonic() * 1000), self._ultimo_ts + 1)  # precisa sempre crescer
        self._ultimo_ts = ts
        resultado = self.landmarker.detect_for_video(imagem, ts)
        if not resultado.hand_landmarks:
            return None
        pontos = [(p.x, p.y) for p in resultado.hand_landmarks[0]]
        lado = resultado.handedness[0][0].category_name  # "Left" / "Right"
        if self.inverter:
            lado = "Left" if lado == "Right" else "Right"
        lado = "Direita" if lado == "Right" else "Esquerda"
        return Mao(pontos, lado, contar_dedos(pontos, lado))

    def fechar(self):
        self.landmarker.close()


def contar_dedos(pontos, lado):
    """Retorna 5 bools (polegar, indicador, médio, anelar, mindinho)."""
    # Polegar: eixo X. Na imagem espelhada, com a palma para a câmera,
    # o polegar da mão direita aponta para a esquerda da tela (x menor).
    ponta_x, ip_x = pontos[4][0], pontos[3][0]
    polegar = ponta_x < ip_x if lado == "Direita" else ponta_x > ip_x
    # Demais dedos: ponta acima do PIP (y menor = mais alto na imagem).
    outros = [pontos[t][1] < pontos[p][1] for t, p in zip(PONTAS[1:], PIPS[1:])]
    return [polegar] + outros
