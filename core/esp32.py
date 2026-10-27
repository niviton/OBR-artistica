"""Conexão Bluetooth BLE com o ESP32 do pilar (esp32/pilar_servo/pilar_servo.ino).

Roda numa thread própria com asyncio: procura o ESP32 pelo nome, conecta,
reconecta sozinho se cair, e envia sempre o ÚLTIMO ângulo pedido.
Se o Bluetooth estiver desligado ou o ESP32 não existir, o telão segue normal.
"""

import asyncio
import threading
import time

try:
    from bleak import BleakClient, BleakScanner
except ImportError:   # bleak não instalado: a integração fica desligada
    BleakClient = BleakScanner = None

CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"   # igual ao do .ino


class Esp32Pilar:
    def __init__(self, cfg):
        self.ativado = bool(cfg["ativado"]) and BleakClient is not None
        self.nome = cfg["nome"]
        self.angulos = {cena: int(a) for cena, a in (cfg["angulos"] or {}).items() if a is not None}
        self.status = "desligado" if not self.ativado else "procurando..."
        self.angulo_enviado = None
        self._pedido = None           # último ângulo pedido (só o mais recente importa)
        self._evento = None
        self._loop = None
        self._rodando = False
        if cfg["ativado"] and BleakClient is None:
            print("AVISO: pacote 'bleak' não instalado; ESP32 desligado (pip install bleak).")

    # ------------------------------------------------------------ API usada pelo app
    def iniciar(self):
        if not self.ativado:
            return
        self._rodando = True
        threading.Thread(target=self._thread, daemon=True).start()

    def cena_entrou(self, cena):
        """Chamado quando uma cena começa. Cenas sem ângulo não mexem o pilar."""
        if cena in self.angulos:
            self.enviar(self.angulos[cena])

    def enviar(self, angulo):
        if not self.ativado:
            return
        self._pedido = max(0, min(180, int(angulo)))
        if self._loop and self._evento:
            self._loop.call_soon_threadsafe(self._evento.set)

    def parar(self):
        self._rodando = False
        if self._loop and self._evento:
            self._loop.call_soon_threadsafe(self._evento.set)

    # ------------------------------------------------------------ thread BLE
    def _thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._evento = asyncio.Event()
        self._loop.run_until_complete(self._principal())

    async def _principal(self):
        espera = 2.0
        while self._rodando:
            try:
                self.status = "procurando..."
                dispositivo = await BleakScanner.find_device_by_name(self.nome, timeout=6.0)
                if dispositivo is None:
                    self.status = "não encontrado"
                    await asyncio.sleep(espera)
                    continue
                self.status = "conectando..."
                async with BleakClient(dispositivo) as cliente:
                    self.status = "conectado"
                    print(f"ESP32 '{self.nome}' conectado.")
                    self.angulo_enviado = None   # reenvia a posição atual após reconectar
                    self._evento.set()
                    while self._rodando and cliente.is_connected:
                        try:
                            await asyncio.wait_for(self._evento.wait(), timeout=1.0)
                        except asyncio.TimeoutError:
                            continue
                        self._evento.clear()
                        alvo = self._pedido
                        if alvo is not None and alvo != self.angulo_enviado:
                            await cliente.write_gatt_char(CHAR_UUID, str(alvo).encode(), response=True)
                            self.angulo_enviado = alvo
                            print(f"[esp32] pilar -> {alvo}°")
                self.status = "desconectado"
            except Exception as e:   # Bluetooth desligado, ESP32 reiniciou, etc.
                msg = str(e).lower()
                self.status = "bluetooth desligado" if "powered" in msg or "radio" in msg else "erro"
                if self.status == "erro":
                    print(f"AVISO ESP32: {e}")
                await asyncio.sleep(espera)
