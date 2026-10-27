"""Registro das cenas. Para adicionar uma cena nova, importe a classe e coloque na lista."""

from scenes.base import Scene, SceneManager
from scenes.espera import TelaEspera
from scenes.cena1_castelo import CenaCastelo
from scenes.cena2_porta import CenaPorta
from scenes.cena3_menino import CenaMenino
from scenes.cena4_banho import CenaBanho
from scenes.cena5_final import CenaFinal

TODAS_AS_CENAS = [TelaEspera, CenaCastelo, CenaPorta, CenaMenino, CenaBanho, CenaFinal]
