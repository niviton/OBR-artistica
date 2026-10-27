# Telão do Castelo — cenas controladas por gestos

Programa para o telão de uma peça inspirada no Castelo Rá-Tim-Bum. A webcam conta quantos
dedos o ator mostra e o telão troca de cena com um fade suave. Todas as cenas funcionam sem nenhum
arquivo: personagens, cenários e sons originais são gerados por código. Para usar a sua própria
arte, basta colocar os arquivos nas pastas `assets/cenaN`.

| Gesto | Cena |
|---|---|
| (antes do 1º gesto) | Tela de espera: estrelas e "Levante 1 dedo para começar" |
| 1 dedo | Abertura do castelo: janelas acendem, o ratinho chega e a bandeira sobe |
| 2 dedos | A porta do castelo: segure 2 dedos até o anel encher e a porta abrir |
| 3 dedos | Cena do menino: ele entra, acena e fala num balão |
| 4 dedos | Banho do ratinho: banheira, patinho e bolhas de sabão |
| 5 dedos | Finalização: palco, confete e "Obrigado!" letra por letra |

0 dedos ou mão fora da câmera não fazem nada: a cena atual continua.

## Instalar (Windows, Python 3.11)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Na primeira execução, o modelo de mãos do MediaPipe é baixado sozinho para `models/` (precisa de internet).

## Rodar

```powershell
python main.py                  # espetáculo: câmera + tela cheia
python main.py --janela         # começa em janela
python main.py --test-scenes    # passa pelas 5 cenas sozinho (3 s cada), sem câmera
```

O `--test-scenes` usa só o visual genérico e mostra o FPS de cada cena no terminal.
Opções extras: `--duracao 10` (segundos por cena) e `--capturas pasta` (salva um PNG de cada cena).

## Teclas

| Tecla | Ação |
|---|---|
| ESC / Q | sair |
| F | tela cheia / janela |
| H | esconder/mostrar todo o HUD (modo apresentação: só a cena) |
| P | mover a mini câmera entre os 4 cantos |
| M | mostrar/esconder a mini câmera |
| L | mostrar/esconder os pontos da mão |
| 1 a 5 | ir direto para a cena (plano B se a câmera falhar) |
| 2 (já na cena 2) | abre a porta sem precisar da câmera |
| 0 | voltar para a tela de espera |
| R | reiniciar a cena atual |
| Enter | na cena 5: fade-out lento final |
| C | trocar de câmera (0, 1, 2, 3) |
| S | ligar/desligar o som |

## Seus arquivos (assets)

Cada cena tem uma pasta. Todos os arquivos são opcionais. O que existir é usado e o que faltar é
gerado por código. Não precisa mexer no código: é só colocar o arquivo e abrir o programa de novo.

```
assets/
  cena1/   abertura do castelo
  cena2/   porta do castelo
  cena3/   cena do menino
  cena4/   banho do ratinho
  cena5/   finalização
```

| Arquivo | O que faz |
|---|---|
| `fundo.png` ou `fundo.jpg` | imagem de fundo, ajustada a 1920x1080 (corta as sobras) |
| `video.mp4` | vídeo de fundo em loop (tem prioridade sobre o `fundo`) |
| `personagem.png` | PNG transparente que substitui o personagem genérico da cena, com a mesma animação (respiração, balanço e pulos) |
| `som.wav` ou `som.mp3` | toca ao entrar na cena. Na cena 2, toca quando a porta abre |

Observações:
- Na cena 1, um `fundo` próprio substitui o céu, o castelo e a bandeira; o ratinho e o título continuam.
- Na cena 4, o `personagem.png` aparece dentro da banheira genérica.
- Com o HUD ligado, um aviso discreto no canto mostra o que a cena está usando do genérico.

## Configuração (sem mexer no código)

`config.yaml`:

| Chave | Para que serve |
|---|---|
| `camera.indice` | qual câmera usar (0 = webcam do notebook) |
| `gestos.tempo_estavel` | segundos que o gesto precisa ficar igual para valer (anti-flicker) |
| `gestos.inverter_lateralidade` | `true` se "esquerda/direita" aparecer trocado |
| `transicao.fade` | duração do fade entre cenas |
| `porta.tempo_desafio` | segundos segurando 2 dedos para abrir a porta |
| `porta.velocidade_descida` | quanto o anel esvazia por segundo ao soltar o gesto |
| `final.fade_final` | duração do fade-out do Enter na cena 5 |
| `audio.ativado`, `audio.volume`, `audio.fade_ms` | som ligado, volume (0 a 1) e fade |
| `video.fps_alvo` | FPS alvo (30) |
| `hud.mostrar`, `hud.canto_mini_camera` | HUD ligado ao abrir e canto inicial da mini câmera |

`config/falas.json`: todos os textos (título da cena 1, dica e mensagem da porta, falas do menino,
texto do banho, "Obrigado!" e o subtítulo final). Salve o arquivo em UTF-8.

O mapeamento gesto → cena fica em `GESTO_PARA_CENA`, no topo do `main.py`.

## Pilar giratório (ESP32 + servo)

Um servo no ESP32 gira o pilar do cenário junto com a troca de cena, via **Bluetooth BLE**
(Wi-Fi é proibido na OBR):

| Cena | Ângulo |
|---|---|
| cena2 (portão) | 0° |
| cena3 (menino) | 90° |
| cena1 (castelo/ratinho) | 180° |
| cena4, cena5, espera | o pilar fica onde está |

1. Ligações: sinal do servo no **GPIO 13**; VCC do servo em **5 V de fonte/bateria externa**;
   GND da fonte ligado ao **GND do ESP32** (terra em comum).
2. Arduino IDE: instale a placa "esp32" (Espressif) e a biblioteca **ESP32Servo**.
3. Abra `esp32/pilar_servo/pilar_servo.ino`, escolha "ESP32 Dev Module" e grave.
   Teste pelo Monitor Serial (115200): digite `0`, `90` ou `180`.
4. No notebook, **ligue o Bluetooth** e rode `python main.py`. Ele procura o ESP32 pelo nome
   `PilarCastelo`, conecta e reconecta sozinho. O HUD mostra "ESP32 pilar: conectado · 90°".
   O LED azul da placa acende quando conectado.

Ângulos e nome ficam em `config.yaml` (`esp32`). Velocidade do giro: `MS_POR_GRAU` no `.ino`.
Se o pilar não chegar exatamente em 0°/180°, ajuste `PULSO_MIN_US`/`PULSO_MAX_US`.

## Estrutura

```
main.py              janela, laço principal, teclas, GESTO_PARA_CENA e on_gesture_change()
config.yaml          configurações
config/falas.json    textos das cenas
generic_art.py       personagens e cenários genéricos desenhados por código
generic_sounds.py    sons genéricos sintetizados (ding, porta, bolha, aplausos)
core/
  camera.py          captura da câmera + detecção numa thread separada
  hand_detector.py   MediaPipe (Tasks API) e contagem de dedos
  gestures.py        anti-flicker (Estabilizador)
  assets.py          carrega assets/cenaN com cache; vídeo de fundo
  audio.py           volume, fade e mudo
  hud.py             mini câmera, número detectado e status
  effects.py         estrelas, partículas, brilhos e gradientes
  text.py            texto com contorno e balão de fala
  config.py          leitura do config.yaml e do falas.json
scenes/
  base.py            classe Scene e SceneManager (fade)
  espera.py          tela de espera
  cena1_castelo.py  ...  cena5_final.py
assets/cena1..5/     seus arquivos (opcionais)
models/              modelo do MediaPipe (baixado sozinho)
```

## Para expandir

- **Nova cena:** crie `scenes/minha_cena.py` com uma classe que herda de `Scene`
  (`preparar`, `enter`, `update(dt)`, `draw(frame)`, `exit`). Registre a classe em
  `scenes/__init__.py` e ligue um gesto a ela em `GESTO_PARA_CENA`.
- **Hardware (ESP32 / Spike Prime):** use `on_gesture_change()` em `main.py` (chamada quando
  o gesto muda) ou os ganchos `on_enter_hook()` / `on_exit_hook()` de cada cena. Os comentários
  `TODO` mostram onde entra cada um.
- **Gesto do bíceps (MediaPipe Pose):** os pontos estão marcados com `TODO` em `core/camera.py`
  e em `on_gesture_change()`.

## Problemas comuns

- **"não foi possível abrir a câmera"**: feche Teams, Zoom ou o navegador, ou aperte C para trocar
  de câmera. As teclas 1 a 5 sempre funcionam.
- **Polegar contado errado:** mostre a palma virada para a câmera. Se a mão aparecer trocada
  no HUD, use `inverter_lateralidade: true`.
- **Notebook lento:** em `config.yaml`, use `escala_suave: false` e diminua `fps_alvo`.
