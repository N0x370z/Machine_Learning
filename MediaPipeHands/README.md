# MediaPipeHands

> Última actualización: **2026-09-23**. Historial completo de errores, cambios y mejoras en [`CHANGELOG.md`](CHANGELOG.md).

Detección de manos en tiempo real con [MediaPipe Tasks API](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker), captura de los 21 landmarks por mano en un CSV, y un script separado para volver a graficar esos mismos puntos a partir del CSV (sin necesidad de la cámara).

## Estructura del proyecto

```
MediaPipeHands/
├── Prueba.py          # Captura en vivo: cámara + MediaPipe + export a CSV
├── plot_csv.py         # Grafica los landmarks guardados en un CSV
├── hand_style.py        # Colores por dedo compartidos entre Prueba.py y plot_csv.py
├── requirements.txt     # Dependencias (mediapipe fijado a 0.10.35, ver más abajo)
├── CHANGELOG.md          # Registro fechado de errores, cambios y mejoras
├── models/
│   └── hand_landmarker.task   # Modelo de MediaPipe (se descarga aparte, no va en git)
├── capturas/
│   ├── hand_data_YYYYMMDD_HHMMSS.csv   # Un CSV por sesión de captura
│   └── screenshot_*.png                 # Fotos tomadas con la tecla 's'
└── venv/                # Entorno virtual del proyecto
```

## Instalación

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

Descargar el modelo de landmarks de mano y colocarlo en `models/hand_landmarker.task`:

```bash
mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

### ⚠️ Versión de MediaPipe fijada

El proyecto está fijado a `mediapipe==0.10.35`. Las versiones `1.0.0`/`1.0.1` tienen un bug conocido en macOS (Apple Silicon) que crashea cualquier tarea de visión (`HandLandmarker`, `PoseLandmarker`, etc.) con:

```
Check failed: service_ Service is unavailable
```

(`TensorsToDetectionsCalculator` intenta inicializar un helper de Metal/GPU que nunca se registra en un grafo de solo-CPU). Ver [google-ai-edge/mediapipe#6356](https://github.com/google-ai-edge/mediapipe/issues/6356). **No actualizar `mediapipe` sin volver a probar en macOS.**

## `Prueba.py` — captura en vivo

```bash
./venv/bin/python3 Prueba.py

# Más de 2 manos a la vez (varias personas en cámara, por ejemplo):
./venv/bin/python3 Prueba.py --max-hands 4

# Si cuesta que reconozca la mano (poca luz, cámara lejos), bajar el umbral:
./venv/bin/python3 Prueba.py --min-detection-confidence 0.3
```

`--max-hands` (default `4`) fija cuántas manos puede rastrear MediaPipe a la vez — **no hay límite físico de 2**: el modelo detecta tantas manos como quepan en el frame (varias personas incluidas), este flag solo pone un tope al costo de cómputo por frame. El `HandTracker` (ver más abajo) le da a cada una un `track id` propio sin importar cuántas haya, incluso si dos personas muestran la misma mano (dos "Left" al mismo tiempo, por ejemplo) — el id, no el color, es lo que las distingue entre sí.

### Controles y panel de estado

Mientras corre la ventana de la cámara:

| Tecla | Acción |
|-------|--------|
| `q` | Salir y exportar el CSV de la sesión a `capturas/` |
| `n` | Mostrar/ocultar los nombres de los dedos (útil si se enciman con el puño cerrado o la mano de perfil) |
| `s` | Guardar una foto del frame actual en `capturas/screenshot_<fecha>.png` (con el esqueleto dibujado, sin el panel de estado) |

En la esquina superior izquierda hay un panel de estado con los **FPS** reales, las **manos** detectadas en el frame y los **frames grabados** hasta ahora para el CSV. Si los FPS bajan mucho, reduce `--max-hands` o la resolución (`--cam-width`/`--cam-height`). Si "Frames grabados" sigue en 0, no se está detectando ninguna mano y al salir no se va a generar CSV.

### ⚠️ Corregido: reconocimiento poco confiable de manos

Antes de la versión del **2026-09-23**, el detector podía tardar en reconocer la mano o perderla con facilidad, sobre todo con poca luz, la mano lejos de la cámara, o webcams que abrían a baja resolución por defecto (640×480 es común). Ver detalle en [`CHANGELOG.md`](CHANGELOG.md#2026-09-23). Se corrigió con dos cambios:

- **Resolución de captura más alta por defecto**: `Prueba.py` ahora le pide a la cámara `1280x720` (antes usaba lo que la cámara abriera por defecto). Ajustable con `--cam-width`/`--cam-height`; si la cámara no soporta la resolución pedida, se ignora sin error.
- **Umbrales de confianza configurables**: antes estaban fijos en `0.5` dentro del código. Ahora son flags:

| Flag | Default | Qué hace |
|------|---------|----------|
| `--min-detection-confidence` | `0.5` | Confianza mínima para detectar una mano nueva. Bajarlo ayuda si cuesta que te reconozca. |
| `--min-presence-confidence` | `0.5` | Confianza mínima para seguir considerando presente una mano ya detectada. |
| `--min-tracking-confidence` | `0.5` | Confianza mínima del tracking entre frames. Bajarlo ayuda si la mano se "pierde" con movimiento rápido. |
| `--cam-width` / `--cam-height` | `1280` / `720` | Resolución de captura solicitada a la cámara. |

Qué hace:

1. Abre la cámara por defecto (`cv2.VideoCapture(0)`), solicita la resolución configurada y voltea el frame horizontalmente (efecto espejo).
2. Corre `HandLandmarker` en modo `VIDEO` (hasta `--max-hands` manos, con los umbrales de confianza configurados) sobre cada frame.
3. Dibuja en la ventana de OpenCV, para cada mano detectada:
   - Los 21 landmarks coloreados **por dedo** (ver "Identificación por dedo" más abajo), con antialiasing y un trazo oscuro de contraste debajo de cada línea.
   - Las conexiones del "esqueleto" (`HandLandmarksConnections.HAND_CONNECTIONS`), también coloreadas por dedo (gris neutro para las conexiones muñeca-nudillo).
   - La etiqueta `Left`/`Right` + el id de track sobre la muñeca (p. ej. `Left #0`), con un fondo oscurecido para que se lea sobre cualquier color de piel/ropa/fondo.
4. Acumula en memoria un registro por landmark por frame detectado.
5. Muestra el panel de estado y atiende las teclas `n`/`s` (ver "Controles y panel de estado").
6. Al presionar `q` (o cerrar la ventana), libera la cámara y exporta todo lo acumulado a un nuevo CSV en `capturas/`.

Si no se detectó ninguna mano en toda la sesión, no se genera CSV (se imprime un aviso).

### Identificación por dedo y mejoras gráficas

Desde el **2026-09-23**, tanto la vista en vivo como `plot_csv.py` identifican cada dedo con su propio color (antes todo el esqueleto de una mano usaba un único color por lateralidad). La paleta vive en un solo lugar, [`hand_style.py`](hand_style.py), para que ambas vistas no se desincronicen:

| Dedo | Landmarks | Color | Etiqueta en la punta |
|------|-----------|-------|-----------------------|
| Pulgar (Thumb) | 1–4 | Ámbar `#e69f00` | `Pulgar` |
| Índice (Index) | 5–8 | Azul cielo `#56b4e9` | `Índice` |
| Medio (Middle) | 9–12 | Verde azulado `#009e73` | `Medio` |
| Anular (Ring) | 13–16 | Magenta `#cc79a7` | `Anular` |
| Meñique (Pinky) | 17–20 | Rojo coral `#d55e00` | `Meñique` |
| Muñeca / palma | 0 y conexiones muñeca-nudillo | Gris neutro `#787878` | — |

Es la paleta categórica de Wong (2011), elegida para seguir siendo distinguible bajo las formas más comunes de daltonismo (protanopía/deuteranopía), no solo por matiz "semáforo". Las puntas de los dedos (landmarks 4/8/12/16/20) se dibujan más grandes que el resto y con un aro de resalte, para ubicarlas de un vistazo, con el nombre del dedo al lado. El resto de los landmarks ya no muestra su índice numérico (0–20). En la vista en vivo los nombres van sin acentos (`Indice`, `Menique`) porque las fuentes de OpenCV solo soportan ASCII.

Con el color ahora dedicado a identificar el dedo, la lateralidad (`Left`/`Right`) se sigue mostrando con la etiqueta de texto junto a la muñeca en ambas vistas, y además con estilo de línea en `plot_csv.py` (punteado = Left, sólido = Right; ver más abajo).

### Lateralidad corregida (antes salía invertida)

Como el frame se voltea (efecto espejo) antes de pasarlo a MediaPipe, la lateralidad cruda del modelo salía invertida: la mano derecha real aparecía como `Left`. Desde el **2026-09-23** `Prueba.py` la corrige antes del tracker, así que la vista en vivo y el CSV muestran la mano real de la persona. Para CSVs grabados antes, usar `plot_csv.py --swap-hands`.

### Estabilización de Left/Right (`HandTracker`)

MediaPipe reclasifica `handedness` de forma independiente en cada frame, así que con ciertos movimientos (mano de perfil, dorso hacia la cámara, manos cruzándose) el resultado crudo puede parpadear entre `Left`/`Right` de un frame a otro aunque sea físicamente la misma mano.

`Prueba.py` corrige esto con una clase `HandTracker` que:

1. **Empareja manos entre frames** por cercanía del centroide de sus 21 landmarks (no por el orden en que MediaPipe las devuelve, que tampoco es estable), asignando un `track id` persistente a cada mano física mientras siga en cámara.
2. **Vota la clasificación** sobre una ventana de los últimos 15 frames (~0.5s a 30fps), ponderada por el `score` de cada frame, y usa esa mayoría como `handedness` estable en vez del valor crudo del frame actual. Una o dos reclasificaciones puntuales quedan diluidas por el resto de la ventana.
3. **Tolera oclusiones cortas**: si una mano desaparece hasta 10 frames y reaparece cerca de donde estaba, se le reasigna el mismo `track id` (y conserva su historial de votos) en vez de tratarse como una mano nueva.

Los tres umbrales (`TRACK_MATCH_MAX_DIST`, `TRACK_MAX_AGE`, `HANDEDNESS_WINDOW`) están al principio de `Prueba.py` por si hace falta ajustarlos (p. ej. ventana más larga si sigue habiendo parpadeo, o `TRACK_MATCH_MAX_DIST` más chico si dos manos cercanas terminan compartiendo track).

### Formato del CSV exportado

Un archivo por ejecución, nombrado `hand_data_<YYYYMMDD_HHMMSS>.csv`, con **una fila por landmark por mano por frame**:

| Columna          | Descripción                                                                 |
|------------------|------------------------------------------------------------------------------|
| `frame`          | Índice de frame de video (entero, incremental)                              |
| `timestamp_ms`   | Milisegundos transcurridos desde el inicio de la captura                    |
| `hand_id`        | Id de track persistente por mano física durante toda la sesión (ver `HandTracker` arriba) — no se resetea por frame ni se limita a 0/1 |
| `handedness`     | `"Left"` o `"Right"` **estabilizado** (voto ponderado sobre 15 frames, no el valor crudo de MediaPipe) |
| `score`          | Confianza promedio de esa clasificación estable (0–1)                       |
| `landmark_index` | 0–20: índice del landmark dentro de la mano (ver mapa de landmarks abajo)   |
| `x`, `y`         | Coordenadas normalizadas (0–1) relativas al frame; origen arriba-izquierda   |
| `z`              | Profundidad relativa a la muñeca (unidades arbitrarias, no normalizadas)     |

Cada mano/frame produce 21 filas consecutivas (una por `landmark_index`, en orden 0→20).

> CSVs generados antes de esta versión usan la columna `hand_index` (índice por frame, sin persistencia ni suavizado) en vez de `hand_id`. `plot_csv.py` lee ambos formatos.

**Mapa de los 21 landmarks** (índice → punto), según la convención de MediaPipe Hands:

```
0  Muñeca (WRIST)
1-4   Pulgar (CMC, MCP, IP, TIP)
5-8   Índice (MCP, PIP, DIP, TIP)
9-12  Medio (MCP, PIP, DIP, TIP)
13-16 Anular (MCP, PIP, DIP, TIP)
17-20 Meñique (MCP, PIP, DIP, TIP)
```

## `plot_csv.py` — graficar los puntos del CSV

Reconstruye, a partir de un CSV ya guardado, exactamente los mismos puntos y conexiones que se dibujan en vivo en `Prueba.py` (reutiliza la misma constante `HAND_CONNECTIONS` de MediaPipe), pero con `matplotlib` en vez de la ventana de la cámara.

```bash
# Anima todos los frames del CSV más reciente en capturas/
./venv/bin/python3 plot_csv.py

# Usa un CSV específico
./venv/bin/python3 plot_csv.py capturas/hand_data_20260918_124925.csv

# Grafica un solo frame (estático), útil para inspeccionar un instante puntual
./venv/bin/python3 plot_csv.py --frame 38

# CSV grabado antes del 2026-09-23 (Left/Right invertidos): corregirlo al graficar
./venv/bin/python3 plot_csv.py --swap-hands

# Controla la velocidad de la animación (ms entre frames, default 33 ≈ 30 fps)
./venv/bin/python3 plot_csv.py --interval 50
```

Detalles de la visualización:

- Color por dedo (ver tabla en "Identificación por dedo" más arriba), consistente con la vista en vivo de `Prueba.py` porque ambas usan la misma paleta en `hand_style.py` — consistente cuadro a cuadro, no se reasigna.
- Lateralidad por estilo de línea: **punteado** para `Left`, **sólido** para `Right` (el color ya no codifica lateralidad, ver arriba).
- Las puntas de dedo (4/8/12/16/20) se dibujan más grandes y con el nombre del dedo (`Pulgar`, `Índice`, `Medio`, `Anular`, `Meñique`); el resto de los puntos va sin etiqueta.
- Cada mano lleva además la etiqueta `{Left|Right} #{hand_id}` junto a la muñeca. Con más de 2 manos en el CSV (varias personas, ver `--max-hands` en `Prueba.py`) puede haber varias manos del mismo lado; el `hand_id` es lo que las distingue entre sí, igual que en la vista en vivo.
- La leyenda combina ambas claves: color por dedo y estilo de línea por lateralidad.
- El eje Y se invierte porque las coordenadas de MediaPipe crecen hacia abajo (igual que en una imagen), así la orientación coincide con lo que se ve en la cámara.
- Solo grafica en el plano `x`/`y` (no usa `z`); la profundidad no se representa en este visor.
- Sin cámara ni modelo `.task` de por medio: solo lee el CSV, así que corre incluso sin permisos de cámara.

## Flujo típico

```bash
./venv/bin/python3 Prueba.py           # capturar (genera un CSV nuevo en capturas/)
./venv/bin/python3 plot_csv.py         # revisar esa captura graficada
```

## Historial de cambios

Todo error corregido, cambio y mejora se documenta con fecha en [`CHANGELOG.md`](CHANGELOG.md). Última entrada: **2026-09-23** (fix de lateralidad invertida, nombres de dedos, fix de reconocimiento de manos, mejoras gráficas).
