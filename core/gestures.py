"""Anti-flicker: um número só vale depois de ficar estável por um tempo."""

import time


class Estabilizador:
    def __init__(self, tempo, gestos_validos):
        self.tempo = tempo
        self.validos = set(gestos_validos)
        self.candidato = None   # número visto agora (pode ser 0 ou None)
        self.desde = time.monotonic()
        self.estavel = None     # último gesto aceito

    def atualizar(self, numero, agora=None):
        """Recebe o número bruto do frame. Retorna o novo gesto estável quando ele muda."""
        agora = time.monotonic() if agora is None else agora
        if numero != self.candidato:
            self.candidato, self.desde = numero, agora
            return None
        if (numero in self.validos and numero != self.estavel
                and agora - self.desde >= self.tempo):
            self.estavel = numero
            return numero
        return None

    def mantido(self, agora=None):
        """Número segurado de forma estável neste instante (ou None)."""
        agora = time.monotonic() if agora is None else agora
        if self.candidato is not None and agora - self.desde >= self.tempo:
            return self.candidato
        return None

    def progresso(self, agora=None):
        """0..1 — quanto falta para o candidato atual ficar estável (para o HUD)."""
        agora = time.monotonic() if agora is None else agora
        if self.candidato not in self.validos:
            return 0.0
        return min(1.0, (agora - self.desde) / max(self.tempo, 1e-6))

    def forcar(self, numero):
        """Usado pelas teclas: considera `numero` como o gesto atual."""
        self.estavel = numero
