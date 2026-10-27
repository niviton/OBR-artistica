"""Captura da câmera + detecção numa thread separada (a interface nunca espera a câmera)."""

import os
import threading
import time

import cv2


class CameraWorker:
    def __init__(self, detector, indice, largura=640, altura=480):
        self.detector = detector
        self.indice = indice
        self.largura, self.altura = largura, altura
        self.cap = None
        self.ok = False
        self.abrindo = False
        self._frame = None
        self._mao = None
        self._lock = threading.Lock()
        self._rodando = False
        self._thread = None

    def iniciar(self):
        """Abre a câmera na própria thread (no Windows isso leva alguns segundos)."""
        self.abrindo = True
        self._rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _abrir(self):
        backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.indice, backend)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            print(f"ERRO: não foi possível abrir a câmera {self.indice}.\n"
                  "  - Verifique se ela está conectada.\n"
                  "  - Feche outros programas que usam a câmera (Teams, Zoom, navegador).\n"
                  "  - Aperte C para tentar outra câmera. As teclas 1-5 continuam funcionando.")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.largura)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.altura)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        print(f"Câmera {self.indice} aberta.")
        return True

    def _loop(self):
        self.ok = self._abrir()
        self.abrindo = False
        if not self.ok:
            return
        falhas = 0
        try:
            while self._rodando:
                lido, frame = self.cap.read()
                if not lido:
                    falhas += 1
                    if falhas > 30:
                        print(f"ERRO: a câmera {self.indice} parou de enviar imagens.")
                        self.ok = False
                        break
                    time.sleep(0.03)
                    continue
                falhas = 0
                frame = cv2.flip(frame, 1)  # espelha: funciona como um espelho para o ator
                try:
                    mao = self.detector.detectar(frame)
                except Exception as e:
                    print(f"Aviso na detecção: {e}")
                    mao = None
                # TODO (futuro) — Bíceps: rodar aqui também um detector de MediaPipe Pose
                #   no mesmo `frame` e guardar o resultado junto com a mão.
                with self._lock:
                    self._frame, self._mao = frame, mao
        finally:
            self.cap.release()   # a própria thread libera a câmera ao terminar

    def ultimo(self):
        """(frame BGR espelhado ou None, Mao ou None)."""
        with self._lock:
            return self._frame, self._mao

    def parar(self):
        self._rodando = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self._frame, self._mao = None, None
        self.ok = False
