# MediaPipeHands

> Última actualización: **2026-09-24**. Historial completo de errores, cambios y mejoras en [`CHANGELOG.md`](CHANGELOG.md). Resumen de **comandos nuevos y antiguos, partes quitadas y por qué** en [Cambios: comandos, partes quitadas y por qué](#cambios-comandos-partes-quitadas-y-por-qué).

Detección de manos en tiempo real con [MediaPipe Tasks API](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker), vista 3D de la mano con **dos puntos de vista (POV)** a la vez (como los viewports de Blender) usando la profundidad `z`, el esqueleto extendido **hasta el antebrazo** (codo detectado con YOLO pose), la **velocidad** de cada punto (a partir de `x`, `y`, `z` y del tiempo de cada fotograma), captura de los 21 landmarks por mano (+ el codo) en un CSV, y un script separado para volver a graficar esos mismos puntos a partir del CSV (sin necesidad de la cámara).

## Guía rápida de uso

Todos los comandos se corren desde la carpeta `MediaPipeHands/`:

```bash
cd MediaPipeHands
```

### 1. Preparar el entorno (solo la primera vez)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

El modelo de YOLO para el antebrazo (`models/yolo11s-pose.pt`, ~20 MB) no hace falta bajarlo a mano: se descarga solo la primera vez que corres `Prueba.py` (necesita internet esa primera vez).

En macOS, la primera vez que abras la cámara el sistema te pide permiso para la terminal (Terminal, iTerm, VS Code…). Si lo negaste, actívalo en **Ajustes del Sistema → Privacidad y Seguridad → Cámara** y vuelve a abrir la terminal.

### 2. Capturar tus manos

```bash
./venv/bin/python3 Prueba.py
```

Se abre una ventana con la cámara en modo espejo, como si te vieras en un espejo. Pon una o dos manos frente a la cámara y verás:

- El **esqueleto de cada mano**, con un color por dedo y el **nombre del dedo** en cada punta (Pulgar, Indice, Medio, Anular, Menique).
- Junto a la muñeca, la etiqueta **`Left #0` / `Right #1`**: indica qué mano es (izquierda/derecha real de la persona) y un número que identifica a esa mano mientras siga en cámara.
- El **antebrazo** en azul, desde el **codo** hasta la muñeca: **grueso y sólido** si YOLO ve el codo, **fino y punteado** con la etiqueta `Codo (estimado)` si no lo ve y se estima por la dirección de la palma (ver [Antebrazo](#antebrazo-forearmpy)).
- **Flechas amarillas de velocidad** en la muñeca, las puntas de los dedos y el codo: apuntan hacia donde se mueve cada punto y son más largas cuanto más rápido va (ver [Velocidad](#velocidad-kinematicspy)).
- Junto al nombre de cada dedo, su **velocidad en cm/s** (p. ej. `Indice 32`).
- Arriba a la izquierda, el **panel de estado**: FPS, manos, antebrazos (cuántos de YOLO y cuántos estimados), frames grabados, la **velocidad de la muñeca** y la **de cada dedo** de cada mano en cm/s, y cuántos ms tarda cada etapa (`mano`, `yolo`, `3D`), para ver qué frena si los FPS bajan.

Además se abre una segunda ventana, **Vista 3D - dos POV**, con la misma mano en 3D vista desde dos ángulos a la vez: el **POV 1** arranca desde el lado de la cámara y el **POV 2** girado **180°**, desde atrás. **Cada POV es una cámara virtual independiente**: al girarlo, moverlo o hacerle zoom, el otro no se mueve. Todo se aplica al POV que tenga el mouse encima (el marcado como `(activo)`). Si quieres que se muevan juntos a 180°, activa **Vincular 180** (tecla `l`). Los controles completos están en [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy).

Las teclas funcionan con **cualquiera de las dos ventanas** activa (haz clic en una si no responde):

| Tecla | Qué hace |
|-------|----------|
| `n` | Muestra/oculta los nombres de los dedos |
| `v` | Muestra/oculta las flechas y los números de velocidad (en las dos ventanas) |
| `f` | Cambia la velocidad de cada dedo entre **absoluta** y **relativa a la muñeca** |
| `s` | Guarda una foto de la vista de la cámara en `capturas/` |
| `q` o `Esc` | Termina y guarda los datos |
| `1` `3` `7` `9` `.` `r` `+` `-` | Controles del POV bajo el mouse en la vista 3D (ver más abajo) |
| `l` | Vincular/desvincular la rotación de los dos POV a 180° |

### 3. Terminar y guardar

Presiona **`q`** o **`Esc`** en cualquiera de las dos ventanas, o cierra la ventana de la cámara con el botón rojo. Se cierran las dos ventanas y en la terminal aparece la ruta del CSV generado, por ejemplo:

```
Datos exportados a capturas/hand_data_20260923_115410.csv
```

Si no se detectó ninguna mano en toda la sesión, no se crea el CSV (fíjate que "Frames grabados" no esté en 0 antes de salir). Cerrar solo la ventana de la vista 3D no termina la captura: la cámara sigue grabando sin el 3D. Con `Ctrl+C` en la terminal también se guarda el CSV.

### 4. Ver lo que grabaste

```bash
./venv/bin/python3 plot_csv.py              # reproduce la última captura como animación
./venv/bin/python3 plot_csv.py --frame 38   # o solo un instante fijo
./venv/bin/python3 plot_csv.py --3d         # en 3D, con los dos POV
```

No necesita cámara: solo lee el CSV. En 2D, cierra la ventana de matplotlib para terminar. En 3D: `espacio` pausa, `a`/`d` retroceden/avanzan un frame, `v` muestra/oculta la velocidad y `q`/`Esc` salen. Si el CSV es de antes del 2026-09-23 (Left/Right invertidos), agrega `--swap-hands`.

### Problemas comunes

| Síntoma | Solución |
|---------|----------|
| `No se pudo abrir la cámara` | Da permiso de cámara a la terminal (ver paso 1) y ciérrala y ábrela de nuevo. Cierra otras apps que estén usando la cámara (Zoom, FaceTime…). |
| `No se encontró el modelo en models/hand_landmarker.task` | Falta descargar el modelo (ver paso 1). |
| Le cuesta detectar la mano o la pierde | Más luz, acerca la mano, o baja el umbral: `./venv/bin/python3 Prueba.py --min-detection-confidence 0.3 --min-tracking-confidence 0.3` |
| Va lento (FPS bajos en el panel) | `--max-hands 2` y/o menos resolución: `--cam-width 960 --cam-height 540` |
| Los nombres de los dedos se enciman | Tecla `n` para ocultarlos |
| Crashea con `Service is unavailable` | Se actualizó `mediapipe`; reinstala la versión fijada: `./venv/bin/pip install -r requirements.txt` (ver abajo) |
| Las teclas no hacen nada | Haz clic sobre cualquiera de las dos ventanas (cámara o vista 3D) para darle el foco |
| El antebrazo sale punteado, como `Codo (estimado)` | YOLO no ve el codo: aléjate para que el codo entre en cámara, con buena luz y sin ropa del mismo color que el fondo. Si detecta mal, prueba el modelo más preciso: `--yolo-modelo m` |
| No quiero ver antebrazos estimados | `--antebrazo-solo-yolo` (solo se dibuja cuando YOLO ve el codo de verdad) |
| Va lento (FPS bajos) | Mira la línea `ms:` del panel de estado para ver qué etapa tarda más. Si es `yolo`: `--yolo-modelo n` o `--sin-antebrazo`; si es `mano`: `--max-hands 2` o menos resolución |
| Error al cargar YOLO / descargar `yolo11s-pose.pt` | Falta internet la primera vez, o no está instalado: `./venv/bin/pip install -r requirements.txt`. Mientras tanto: `--sin-antebrazo` |

Los detalles de cada script y todas sus opciones están en las secciones siguientes.

## Estructura del proyecto

```
MediaPipeHands/
├── Prueba.py          # Captura en vivo: cámara + MediaPipe + export a CSV
├── plot_csv.py         # Grafica los landmarks guardados en un CSV
├── hand_style.py        # Colores por dedo (y antebrazo) compartidos por todas las vistas
├── viewer3d.py          # Visor 3D con dos POV (estilo viewports de Blender)
├── forearm.py           # Antebrazo: codo con YOLO pose + estimación de su z
├── kinematics.py        # Velocidad de cada punto (x, y, z + tiempo de cada fotograma)
├── requirements.txt     # Dependencias (mediapipe fijado a 0.10.35, ver más abajo)
├── CHANGELOG.md          # Registro fechado de errores, cambios y mejoras
├── models/
│   ├── hand_landmarker.task   # Modelo de MediaPipe (se descarga aparte, no va en git)
│   └── yolo11s-pose.pt        # Modelo YOLO pose (se descarga solo, no va en git)
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

# Sin antebrazo (no carga YOLO) y/o sin la vista 3D de dos POV:
./venv/bin/python3 Prueba.py --sin-antebrazo
./venv/bin/python3 Prueba.py --sin-3d

# Modelo YOLO más rápido (n) o más preciso (m) para el codo:
./venv/bin/python3 Prueba.py --yolo-modelo m

# Antebrazo solo cuando YOLO ve el codo (sin estimados):
./venv/bin/python3 Prueba.py --antebrazo-solo-yolo
```

| Flag nuevo (2026-09-24) | Default | Qué hace |
|-------------------------|---------|----------|
| `--sin-antebrazo` | apagado | No detecta el codo/antebrazo con YOLO. Más liviano |
| `--sin-3d` | apagado | No abre la ventana de la vista 3D con dos POV |
| `--yolo-modelo {n,s,m}` | `s` | Tamaño del modelo YOLO pose: `n` ~6 ms (detecta peor el codo), `s` ~9 ms, `m` ~17 ms (más preciso). Se descarga solo a `models/` |
| `--antebrazo-solo-yolo` | apagado | No estima el antebrazo cuando YOLO no ve el codo |

> `--vista3d-cada`, que existió unas horas el 2026-09-24, se quitó: el visor nuevo dibuja en ~3 ms y se redibuja en todos los frames.

`--max-hands` (default `4`) fija cuántas manos puede rastrear MediaPipe a la vez — **no hay límite físico de 2**: el modelo detecta tantas manos como quepan en el frame (varias personas incluidas), este flag solo pone un tope al costo de cómputo por frame. El `HandTracker` (ver más abajo) le da a cada una un `track id` propio sin importar cuántas haya, incluso si dos personas muestran la misma mano (dos "Left" al mismo tiempo, por ejemplo) — el id, no el color, es lo que las distingue entre sí.

### Controles y panel de estado

Mientras corre la ventana de la cámara:

| Tecla | Acción |
|-------|--------|
| `q` o `Esc` | Salir y exportar el CSV de la sesión a `capturas/` (también cerrando la ventana de la cámara o con `Ctrl+C`) |
| `v` | Mostrar/ocultar las flechas y los números de velocidad |
| `f` | Velocidad de cada dedo: absoluta ↔ relativa a la muñeca |
| `n` | Mostrar/ocultar los nombres de los dedos (útil si se enciman con el puño cerrado o la mano de perfil) |
| `s` | Guardar una foto del frame actual en `capturas/screenshot_<fecha>.png` (con el esqueleto dibujado, sin el panel de estado) |

En la esquina superior izquierda hay un panel de estado con los **FPS** reales, las **manos** detectadas en el frame, los **antebrazos** (de YOLO / estimados), los **frames grabados** hasta ahora para el CSV, la **velocidad de la muñeca** de cada mano en cm/s y los **ms por etapa** (`mano` = MediaPipe, `yolo` = antebrazo, `3D` = dibujar la vista 3D). Si los FPS bajan mucho, reduce `--max-hands` o la resolución (`--cam-width`/`--cam-height`). Si "Frames grabados" sigue en 0, no se está detectando ninguna mano y al salir no se va a generar CSV.

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
| `z`              | Profundidad relativa a la muñeca, aproximadamente en la misma escala que `x` (fracción del ancho del frame); **positivo = más lejos de la cámara**. En el codo (landmark 21) es una estimación (ver [Antebrazo](#antebrazo-forearmpy)) |
| `img_w`, `img_h` | Tamaño en píxeles del frame capturado (desde 2026-09-24). Lo usa `plot_csv.py --3d` para reconstruir la escena con la proporción correcta |
| `vx`, `vy`, `vz` | Velocidad del punto en **anchos de frame por segundo**, los tres ejes en la misma escala. `vy` positiva = hacia abajo; `vz` positiva = alejándose de la cámara (ver [Velocidad](#velocidad-kinematicspy)) |
| `rapidez_cm_s` | Módulo de la velocidad en **cm/s aproximados** |
| `rapidez_rel_cm_s` | Rapidez **respecto a la muñeca** (cm/s): lo que el punto se mueve dentro de la mano. En las puntas (4, 8, 12, 16, 20) es la velocidad relativa de ese dedo; en la muñeca siempre es 0 |
| `dedo` | A qué parte pertenece el punto: `Pulgar`, `Índice`, `Medio`, `Anular`, `Meñique`, `Muñeca` o `Codo`. Para filtrar por dedo sin memorizar índices |
| `fuente` | De dónde sale el punto: `mediapipe` (0–20), `yolo` o `estimado` (codo) |

Cada mano/frame produce 21 filas consecutivas (una por `landmark_index`, en orden 0→20) y, si se detectó su antebrazo, **una fila 22 con `landmark_index = 21` (el codo)**.

> CSVs anteriores al 2026-09-24 no tienen `img_w`/`img_h`, el codo, la velocidad ni la `fuente`: `plot_csv.py` asume 1280×720, dibuja solo la mano y calcula la velocidad al leer.
>
> CSVs aún más viejos usan la columna `hand_index` (índice por frame, sin persistencia ni suavizado) en vez de `hand_id`. `plot_csv.py` lee ambos formatos.

**Mapa de los 21 landmarks** (índice → punto), según la convención de MediaPipe Hands:

```
0  Muñeca (WRIST)
1-4   Pulgar (CMC, MCP, IP, TIP)
5-8   Índice (MCP, PIP, DIP, TIP)
9-12  Medio (MCP, PIP, DIP, TIP)
13-16 Anular (MCP, PIP, DIP, TIP)
17-20 Meñique (MCP, PIP, DIP, TIP)
21    Codo (no es de MediaPipe: lo agrega YOLO pose o se estima, ver forearm.py)
```

## Vista 3D con dos POV (`viewer3d.py`)

La idea es la de los viewports divididos de Blender: **una sola cámara física**, y en el gráfico dos puntos de vista de la misma escena 3D, uno al lado del otro. Lo abre `Prueba.py` en vivo (salvo con `--sin-3d`) y `plot_csv.py --3d` al reproducir. Tiene fondo oscuro, piso de referencia y ejes de orientación en la esquina, como Blender.

- **POV 1** (izquierda) arranca mirando la mano desde el lado de la cámara, un poco desde arriba y de costado para que se note la profundidad.
- **POV 2** (derecha) arranca **girado 180° en horizontal**: la misma elevación, azimut + 180°, o sea, la mano vista desde atrás (lo que la cámara no ve directamente).

La tercera dimensión es la `z` de MediaPipe: profundidad de cada punto **relativa a la muñeca**, en fracciones del ancho del frame (positiva = más lejos de la cámara). Con una sola cámara es profundidad **relativa** (la forma 3D de la mano), no la distancia absoluta de la mano a la cámara.

La proyección es **ortográfica** (sin perspectiva), como las vistas numéricas de Blender. Los dedos más cercanos a la vista tapan a los más lejanos al girar.

### Controles: cada POV es independiente

Cada POV es una **cámara virtual independiente**, con su propio ángulo, zoom, desplazamiento y encuadre. Todo lo que hagas (mouse, teclas, botones) se aplica **solo al POV que tiene el mouse encima**, marcado como `(activo)` y con un fondo un poco más claro, igual que en Blender. Si empiezas a arrastrar en un POV y el mouse cruza al otro, el arrastre sigue afectando solo al POV donde empezó.

Las teclas funcionan con la vista 3D o con la ventana de la cámara activa.

| Acción | Qué hace (en el POV bajo el mouse) |
|--------|-------------------------------------|
| Arrastrar con clic izquierdo | **Gira** ese POV (órbita) |
| `Shift` + arrastrar, o arrastrar con el botón central | **Mueve** (desplaza) ese POV sin girarlo |
| Rueda del mouse, clic derecho arrastrando, o `+` / `-` | **Zoom** de ese POV |
| `1` | Vista de **frente** (como la ve la cámara) |
| `3` | Vista de **lado** |
| `7` | Vista desde **arriba** |
| `9` | Vista **opuesta** a la actual (frente ↔ atrás, arriba ↔ abajo), como en Blender |
| `.` | Activa/desactiva **Encuadrar** en ese POV |
| `r` | **Reinicia** ese POV (ángulo inicial, zoom, desplazamiento y encuadre) |
| Botones *Frente / Atras / Lado / Arriba* bajo cada POV | Lo mismo que `1`, `3`, `7` y la vista de atrás, para ese POV |
| Botón **Encuadrar** bajo cada POV (azul = activo) | Activo por defecto: el POV sigue a las manos para verlas grandes (con seguimiento suavizado para que no vibre). Apagado, muestra el frame completo de la cámara. Cada POV tiene el suyo: puedes tener uno encuadrado en la mano y el otro con la escena entera |

Controles que afectan a los dos POV:

| Acción | Qué hace |
|--------|----------|
| `l` o botón **Vincular 180** (en el medio; azul = activo) | **Apagado por defecto.** Si lo activas, al girar un POV el otro lo sigue girado 180° en horizontal (misma elevación, azimut + 180°), para ver la mano por delante y por detrás a la vez. Solo vincula la **rotación**: zoom, desplazamiento y encuadre siguen siendo de cada POV |
| `v` | Muestra/oculta las flechas y los números de velocidad |
| `f` | Velocidad de cada dedo: absoluta ↔ relativa a la muñeca |

Arriba de cada POV se ve su estado: `elev` (elevación), `azim` (azimut), `zoom` y `encuadre si/no`. La pirámide gris marca dónde está la **cámara**, para ubicarse al girar.

### Ejes

| Eje (gizmo de la esquina) | Significado |
|---------------------------|-------------|
| `X` (rojo) | Horizontal de la imagen (0 = borde izquierdo, 1 = borde derecho, con la imagen en espejo como en la ventana de la cámara) |
| `Prof` (verde) | La `z` de MediaPipe; hacia el fondo = más lejos de la cámara |
| `Alto` (azul) | Vertical de la imagen, invertida para que "arriba" sea arriba |

Los tres ejes usan la misma escala (fracción del ancho del frame), así la mano no se ve estirada al girarla.

### Por qué OpenCV y no matplotlib (bug del 2026-09-24)

La primera versión del visor (de unas horas antes, ese mismo día) usaba matplotlib y tuvo dos problemas:

1. **`q` no cerraba bien.** `q` es también la tecla con la que matplotlib cierra *su* ventana (`rcParams["keymap.quit"]`): con el visor activo, `q` cerraba solo el visor y la cámara seguía corriendo. Además, el bucle de eventos de matplotlib se "comía" las teclas de la ventana de OpenCV antes de que `cv2.waitKey` las viera, y había que presionar varias veces.
2. **Se volvía lento.** Redibujar dos ejes 3D de matplotlib cuesta ~90 ms por frame.

El visor nuevo proyecta los puntos y los dibuja con OpenCV: **~3 ms por frame** (el bucle completo con las dos ventanas pasó de ir a tirones a ~48 FPS sin cámara). Las dos ventanas son de OpenCV, así que una sola `cv2.waitKey` recibe las teclas de ambas. También se corrigió que en macOS las ventanas quedaban congeladas en pantalla después de salir (faltaba procesar sus eventos tras `destroyAllWindows`).

## Antebrazo (`forearm.py`)

MediaPipe Hands llega solo hasta la muñeca. El antebrazo se agrega con **YOLO pose** (`ultralytics`), que detecta 17 puntos del cuerpo, entre ellos codos y muñecas. Se eligió YOLO y no solo OpenCV porque OpenCV no trae un detector de codo listo para usar (habría que cargar a mano un modelo tipo OpenPose, mucho más pesado). Corre en la GPU de Apple Silicon (MPS) si está disponible, si no en CPU.

Cómo se decide el codo de cada mano, en orden:

1. **YOLO con muñeca visible:** la mano de MediaPipe se empareja con el brazo de YOLO cuya **muñeca** esté más cerca de su muñeca (landmark 0). La distancia máxima se adapta al tamaño de la mano (1.5 palmas, mínimo 6 % del ancho del frame). No se usa la etiqueta izquierda/derecha de YOLO (con la imagen en espejo sale invertida).
2. **YOLO sin muñeca confiable** (pasa seguido: la mano tapa la muñeca o YOLO duda): se acepta un codo de YOLO si está a una distancia plausible (menos de 1.3 antebrazos) y del lado contrario a los dedos.
3. **Memoria:** si YOLO pierde el codo, se sigue usando el último codo detectado (pegado a la muñeca, moviéndose con ella) durante 10 frames. Evita que el antebrazo parpadee.
4. **Estimado:** si no hay nada de lo anterior, se prolonga el eje de la palma (nudillo del medio → muñeca) un largo de antebrazo. Se dibuja **fino y punteado** con la etiqueta `Codo (estimado)`, y en el CSV queda con `fuente = estimado`. Supone la muñeca recta: con la muñeca doblada sale torcido. Se desactiva con `--antebrazo-solo-yolo`.

El codo se suaviza entre frames (YOLO tiembla unos píxeles), lo que también hace suave el paso entre codo detectado y estimado.

**La `z` del codo es una estimación.** YOLO da solo 2D, así que se supone que el antebrazo mide 2.6 veces el largo de la palma (muñeca → nudillo del medio, ~25 cm / ~9.5 cm). Si en la imagen se ve más corto, la diferencia se atribuye a profundidad: `dz = √(largo² − largo_2D²)`. Con una sola cámara no se sabe si el codo está delante o detrás de la muñeca; se asume **detrás** (más lejos de la cámara), que es la postura normal al mostrarle la mano a la webcam.

Para que YOLO detecte el codo, este tiene que estar dentro de la imagen: aléjate un poco de la cámara.

### Mejoras de detección (bug del 2026-09-24)

En la primera versión el antebrazo **tardaba en aparecer y se reconocía mal**. Causas y correcciones:

| Causa | Corrección |
|-------|------------|
| La primera inferencia de YOLO tarda 0.3–0.7 s (carga de kernels en MPS), y ocurría con la primera mano en cámara: tirón y antebrazo que tardaba en salir | Precalentamiento: dos inferencias con una imagen vacía al arrancar, antes de abrir la cámara |
| Modelo `yolo11n-pose` (el más chico): a distancia de webcam el codo sale con baja confianza | Default `yolo11s-pose` (~9 ms vs ~6 ms); `--yolo-modelo` para elegir `n`/`s`/`m` |
| Se exigía confianza ≥ 0.4 al codo **y** a la muñeca de YOLO a la vez | Umbrales 0.25, y la muñeca de YOLO ya no es obligatoria (paso 2) |
| Distancia fija de emparejamiento (12 % del ancho) | Se adapta al tamaño de la mano (1.5 palmas) |
| Si YOLO fallaba un frame, el antebrazo desaparecía | Memoria de 10 frames (paso 3) y estimado por la palma (paso 4) |

Parámetros ajustables al principio de `forearm.py`: `YOLO_PERSON_CONF`, `MIN_ELBOW_CONF`, `MIN_WRIST_CONF`, `MIN_WRIST_MATCH_DIST`, `WRIST_MATCH_PALMS`, `FOREARM_TO_PALM_RATIO`, `HOLD_FRAMES`, `ELBOW_SMOOTHING`.

## Velocidad (`kinematics.py`)

Se calcula la velocidad de los 21 puntos de la mano y del codo usando **juntos la posición (`x`, `y`, `z`) y el tiempo de los fotogramas**:

```
v = (posición_actual − posición_anterior) / (t_actual − t_anterior)
```

- **Posición:** en la escena 3D (`X = x`, `Y = y · alto/ancho`, `Z = z`), los tres ejes en la misma escala (fracción del ancho del frame). Así la velocidad no se deforma según la dirección del movimiento, e incluye el movimiento hacia/desde la cámara (`vz`).
- **Tiempo:** el `timestamp` real de cada fotograma, no el número de frame. Los FPS varían (luz, YOLO, carga de la máquina); suponer "1 frame = 1/30 s" daría velocidades falsas justo cuando el bucle se frena.
- **Suavizado:** la derivada cuadro a cuadro es ruidosa (MediaPipe tiembla un poco aunque la mano esté quieta), así que se suaviza con una media exponencial (`VELOCITY_SMOOTHING = 0.35`).
- **Huecos:** si un punto no se vio por más de 0.25 s (mano perdida y vuelta a encontrar), su velocidad vuelve a 0 en lugar de calcular un salto gigante.

Unidades:

| Magnitud | Unidad |
|----------|--------|
| `vx`, `vy`, `vz` | Anchos de frame por segundo (`vy` + = hacia abajo, `vz` + = alejándose de la cámara) |
| Rapidez en cm/s | **Aproximada**: se convierte suponiendo que la palma (muñeca → nudillo del medio) mide 9.5 cm (`PALM_LENGTH_CM`). Sirve para comparar movimientos, no como medición de laboratorio |

Dónde se ve:

- **Ventana de la cámara:** flechas amarillas en muñeca, puntas de los dedos y codo (solo la parte paralela a la imagen, `vx`/`vy`), y la rapidez de la muñeca de cada mano en el panel de estado.
- **Vista 3D:** las mismas flechas pero en 3D (incluyen `vz`: al girar la vista se ve si el punto se acerca o se aleja de la cámara), y la rapidez de la muñeca junto a cada mano.
- **CSV:** columnas `vx`, `vy`, `vz`, `rapidez_cm_s` para cada punto.

Cada flecha apunta a donde estaría el punto dentro de 0.15 s si siguiera igual; por debajo de 4 cm/s no se dibuja (es temblor, no movimiento). Tecla `v` para mostrarlas/ocultarlas.

### Velocidad de cada dedo

La velocidad de un dedo es la de su **punta** (landmarks 4, 8, 12, 16, 20): es el punto que más se mueve y el que describe lo que hace el dedo. Se muestra de dos formas, que se alternan con la tecla **`f`**:

| Modo | Cálculo | Para qué sirve |
|------|---------|----------------|
| **Absoluta** (por defecto) | Rapidez de la punta tal cual | Movimiento real del dedo en el espacio. Si mueves toda la mano, los cinco dedos "van rápido" |
| **Relativa a la muñeca** | Rapidez de `v_punta − v_muñeca` | Solo lo que el dedo se mueve **dentro de la mano** (doblarlo, estirarlo, tocar algo). Con la mano quieta y un dedo moviéndose, solo ese dedo sube |

Comprobado con datos simulados: mover solo el índice da velocidad solo en el índice (en los dos modos); mover la mano entera da los cinco dedos a la misma velocidad en absoluta y **0** en relativa.

Dónde se ve:

- **Ventana de la cámara:** el número junto al nombre de cada dedo (necesita los nombres visibles, tecla `n`), y una fila por mano en el panel de estado: `Right #0: Pul 12  Ind 30  Med 8  Anu 5  Men 4`.
- **Vista 3D:** el número junto a cada punta, en el color del dedo, en los dos POV, y un panel en el POV 1 con una **barra por dedo** (tope visual 100 cm/s) para comparar de un vistazo cuál se mueve más.
- **CSV:** `rapidez_cm_s` (absoluta) y `rapidez_rel_cm_s` (relativa) en cada fila, y la columna `dedo` para filtrar. Por ejemplo, la velocidad del índice son las filas con `landmark_index = 8`.

Las flechas siempre muestran la velocidad **absoluta** (hacia dónde se mueve el punto de verdad); `f` solo cambia los números de los dedos.

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

# En 3D (x, y, z) con los dos POV, animado o arrancando en pausa en un frame
./venv/bin/python3 plot_csv.py --3d
./venv/bin/python3 plot_csv.py --3d --frame 38

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
- Sin `--3d` grafica solo el plano `x`/`y` con matplotlib; con `--3d` usa también `z` en el mismo visor de dos POV de la captura en vivo (ver [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy)), con flechas de velocidad. La velocidad se recalcula al leer (desde `x`, `y`, `z` y `timestamp_ms`), así funciona también con CSVs viejos.
- Teclas en la reproducción 3D: `espacio` pausa/sigue, `a`/`d` frame anterior/siguiente, `v` velocidad, `f` velocidad de dedos absoluta/relativa, `q`/`Esc` salir, más todas las del visor (`1`, `3`, `7`, `9`, `.`, `l`, `r`, `+`, `-`, mouse). Los POV son independientes igual que en la captura en vivo.
- Si el CSV tiene codo (landmark 21), el antebrazo se dibuja en azul en ambos modos.
- Sin cámara ni modelo `.task` de por medio: solo lee el CSV, así que corre incluso sin permisos de cámara.

## Cambios: comandos, partes quitadas y por qué

Resumen de todo lo que cambió en el proyecto: los comandos de ahora, los de antes, lo que se quitó o reemplazó en el código y por qué. El detalle fechado de cada error y corrección está en [`CHANGELOG.md`](CHANGELOG.md).

El 2026-09-24 hubo tres versiones seguidas, que se nombran así en las tablas:

| Versión | Qué trajo |
|---------|-----------|
| **24-A** (primera) | Eje `z` en 3D, vista de dos POV con **matplotlib**, antebrazo con YOLO (`yolo11n`) |
| **24-B** (segunda, tras la primera prueba con cámara) | Visor rehecho con **OpenCV**, corrección de `q`, de la lentitud y del antebrazo, velocidad |
| **24-C** (tercera) | **POV independientes**: cada uno con su rotación, zoom, desplazamiento y encuadre |
| **24-D** (cuarta) | **Velocidad de cada dedo** (absoluta y relativa a la muñeca, tecla `f`) |

### Comandos actuales (referencia completa)

`Prueba.py` (captura en vivo):

| Comando / flag | Default | Qué hace | Desde |
|----------------|---------|----------|-------|
| `./venv/bin/python3 Prueba.py` | — | Cámara + vista 3D de dos POV + antebrazo + velocidad | — |
| `--max-hands N` | `4` | Máximo de manos a la vez | Inicial |
| `--min-detection-confidence X` | `0.5` | Confianza para detectar una mano nueva | 2026-09-23 |
| `--min-presence-confidence X` | `0.5` | Confianza para seguir considerando presente una mano | 2026-09-23 |
| `--min-tracking-confidence X` | `0.5` | Confianza del tracking entre frames | 2026-09-23 |
| `--cam-width W` / `--cam-height H` | `1280` / `720` | Resolución pedida a la cámara | 2026-09-23 |
| `--sin-antebrazo` | apagado | No carga YOLO; el esqueleto llega hasta la muñeca | 24-A |
| `--sin-3d` | apagado | No abre la vista 3D | 24-A |
| `--yolo-modelo {n,s,m}` | `s` | Modelo YOLO pose: `n` rápido, `s` equilibrado, `m` preciso | 24-B |
| `--antebrazo-solo-yolo` | apagado | No dibuja antebrazos estimados | 24-B |

`plot_csv.py` (reproducir un CSV):

| Comando / flag | Qué hace | Desde |
|----------------|----------|-------|
| `./venv/bin/python3 plot_csv.py` | Anima en 2D el último CSV de `capturas/` | Inicial |
| `plot_csv.py capturas/archivo.csv` | Usa un CSV específico | Inicial |
| `--frame N` | Un solo frame (en 2D estático; en 3D arranca en pausa ahí) | Inicial (en 3D: 24-B) |
| `--interval MS` | ms entre frames de la animación (default `33`) | Inicial |
| `--swap-hands` | Invierte Left/Right (CSVs de antes del 2026-09-23) | 2026-09-23 |
| `--3d` | Reproduce en la vista 3D de dos POV | 24-A (visor OpenCV: 24-B) |

Teclas:

| Dónde | Teclas |
|-------|--------|
| Captura (cualquiera de las dos ventanas) | `q`/`Esc` salir y guardar · `n` nombres · `v` velocidad · `f` dedos absoluta/relativa · `s` foto |
| Vista 3D (POV bajo el mouse) | arrastrar = girar · `Shift`+arrastrar o botón central = mover · rueda/clic derecho/`+`/`-` = zoom · `1` `3` `7` `9` vistas · `.` encuadrar · `r` reiniciar |
| Vista 3D (los dos POV) | `l` vincular 180 · `v` velocidad · `f` dedos absoluta/relativa |
| Reproducción `--3d` | `espacio` pausa · `a`/`d` frame anterior/siguiente · `q`/`Esc` salir · más las de la vista 3D |

### Comandos, teclas y comportamientos que cambiaron o se quitaron

| Antes | Ahora | Cuándo | Por qué |
|-------|-------|--------|---------|
| La cámara abría a la resolución que traía por defecto (a menudo 640×480) | Pide `1280×720`; flags `--cam-width`/`--cam-height` | 2026-09-23 | Con pocos píxeles por mano MediaPipe reconocía mal la mano |
| Umbrales de confianza fijos en `0.5` dentro del código | Flags `--min-*-confidence` | 2026-09-23 | Poder ajustarlos según luz/cámara sin editar el script |
| `plot_csv.py` sin forma de corregir Left/Right | `--swap-hands` | 2026-09-23 | Los CSVs viejos tenían la lateralidad invertida |
| `--vista3d-cada N` (default `3`) | **Eliminado** | 24-B | Existía porque el visor de matplotlib tardaba ~90 ms por frame; el de OpenCV tarda ~3 ms y se redibuja en todos los frames |
| `q` solo en la ventana de la cámara; con el visor 3D activo, `q` cerraba solo el visor | `q` **o** `Esc` en cualquiera de las dos ventanas; también se sale cerrando la ventana de la cámara o con `Ctrl+C`, y siempre se guarda el CSV | 24-B | Bug: `q` es la tecla de matplotlib para cerrar su ventana, y matplotlib se comía las teclas de OpenCV |
| Casillas de matplotlib *Vincular 180°* y *Encuadrar manos* | Botones dibujados con OpenCV (azul = activo) | 24-B | El visor dejó de ser de matplotlib |
| `plot_csv.py --3d` se cerraba con la ventana de matplotlib y no se podía pausar | `espacio`, `a`/`d`, `v`, `q`/`Esc` | 24-B | Visor nuevo con controles de reproducción |
| Modelo YOLO fijo `yolo11n-pose` | `--yolo-modelo`, default `s` | 24-B | `n` detectaba mal el codo a distancia de webcam |
| El antebrazo desaparecía si YOLO no veía el codo | Memoria de 10 frames + codo **estimado** (punteado); `--antebrazo-solo-yolo` para no estimar | 24-B | El antebrazo tardaba en salir y parpadeaba |
| Sin velocidad | Flechas, cm/s en el panel, tecla `v`, columnas en el CSV | 24-B | Pedido: velocidad a partir de `x`, `y`, `z` y los fotogramas |
| **Vincular 180 activado por defecto**: al girar un POV el otro también giraba | **Apagado por defecto**; se activa con `l` o el botón | 24-C | Pedido: mover cada cámara (POV) de forma independiente |
| **Encuadrar** era uno solo para los dos POV (`.` y el botón cambiaban ambos) | Un **Encuadrar por POV** (`.` y un botón bajo cada POV) | 24-C | Independencia: poder tener un POV sobre la mano y otro con la escena entera |
| `r` reiniciaba los dos POV | `r` reinicia solo el POV bajo el mouse | 24-C | Independencia |
| Sin desplazamiento: solo girar y zoom | `Shift`+arrastrar o botón central = **mover** cada POV | 24-C | Poder reubicar cada cámara virtual, como en Blender |
| El zoom ya era por POV | Igual (sin cambio) | — | — |
| Solo la velocidad de la muñeca en números (los dedos solo tenían flecha) | Velocidad de **cada dedo** en números: junto al nombre, en el panel de estado y en un panel con barras en la vista 3D; tecla `f` absoluta ↔ relativa | 24-D | Pedido: velocidad de cada dedo |
| Nombres de los dedos en la vista de la cámara con contorno grueso | Sombra de 1 px | 24-D | Al agregar el número de velocidad, el contorno grueso dejaba letras repetidas al final |

### Partes del código quitadas o reemplazadas

| Qué se quitó / reemplazó | Dónde estaba | Qué lo reemplaza | Por qué |
|--------------------------|--------------|------------------|---------|
| Índices numéricos 0–20 dibujados en cada landmark | `Prueba.py`, `plot_csv.py` | Nombre del dedo solo en la punta | Saturaban la vista (2026-09-23) |
| Iniciales en inglés `T`/`I`/`M`/`R`/`P` | `hand_style.py` | Nombres en español (`Pulgar`…) | Claridad (2026-09-23) |
| Un color por lateralidad para toda la mano | `Prueba.py`, `plot_csv.py` | Un color por dedo (`hand_style.py`); lateralidad por etiqueta y estilo de línea | Identificar dedos de un vistazo (2026-09-23) |
| Columna `hand_index` del CSV | `Prueba.py` | `hand_id` persistente (`HandTracker`) | El índice por frame no identificaba a la misma mano entre frames. `plot_csv.py` sigue leyendo ambos |
| Visor 3D con matplotlib (`Axes3D`, widgets `Button`/`CheckButtons`, `set_hands()`, `refresh()`, `show_nonblocking()`, parámetros `max_hands` y `title`) | `viewer3d.py` (24-A) | Visor con OpenCV (`render()`, `handle_key()`, `is_open()`, `close()`) | Bug de `q` y ~90 ms por frame. OpenCV ya no necesita crear de antemano un grupo de líneas por mano, así que `max_hands` sobraba |
| Constante `DEFAULT_VIEW3D_EVERY` | `Prueba.py` (24-A) | — | Ver `--vista3d-cada` arriba |
| `ForearmDetector.match_elbows()` que devolvía tuplas `(x, y, z)` | `forearm.py` (24-A) | `ForearmDetector.update()` que devuelve `Elbow(x, y, z, source)` | Hacía falta saber si el codo viene de YOLO o es estimado, y guardar memoria entre frames |
| Constantes `MIN_KEYPOINT_CONF = 0.4` y `MAX_WRIST_MATCH_DIST = 0.12` | `forearm.py` (24-A) | `MIN_ELBOW_CONF`/`MIN_WRIST_CONF = 0.25`, `MIN_WRIST_MATCH_DIST` + `WRIST_MATCH_PALMS`, `HOLD_FRAMES`, `YOLO_PERSON_CONF` | Umbrales demasiado estrictos y distancia fija: el codo casi no se detectaba |
| `landmarks_to_rows(frame, ts, tracked_hands, elbows, w, h)` | `Prueba.py` (24-A) | `landmarks_to_rows(frame, ts, hands_scene, scores, w, h)` | Las filas ahora incluyen velocidad y `fuente` |
| `load_frames()` devolvía 3 valores | `plot_csv.py` (24-A) | Devuelve 4 (agrega el origen de cada codo) | Dibujar el codo estimado distinto al de YOLO |
| Texto con "contorno" (el mismo texto más grueso debajo) | `viewer3d.py`, `Prueba.py` (codo) | Sombra de 1 px | En OpenCV el contorno grueso sale más largo que el texto y se veían letras repetidas al final |
| `DualPOVViewer.fit` y `_fit`, un solo encuadre para los dos POV | `viewer3d.py` (24-B) | `fit` y `fit_state` dentro de cada POV (`_POV`) | POV independientes (24-C) |
| `DualPOVViewer.reset()` sin argumentos (reiniciaba los dos) | `viewer3d.py` (24-B) | `reset(idx)` (solo ese POV) | POV independientes (24-C) |
| `linked = True` al crear el visor | `viewer3d.py` (24-A y 24-B) | `linked = False` | POV independientes (24-C) |

### Versiones del formato del CSV

| Versión | Columnas | `plot_csv.py` la lee |
|---------|----------|----------------------|
| Inicial | `frame, timestamp_ms, hand_index, handedness, score, landmark_index, x, y, z` | Sí |
| Con `HandTracker` | `hand_index` → `hand_id` | Sí |
| 24-A | + `img_w, img_h`; fila extra `landmark_index = 21` (codo) | Sí |
| 24-B | + `vx, vy, vz, rapidez_cm_s, fuente` | Sí (en CSVs viejos la velocidad se calcula al leer) |
| 24-D (actual) | + `rapidez_rel_cm_s, dedo` (entre `rapidez_cm_s` y `fuente`) | Sí |

## Flujo típico

```bash
./venv/bin/python3 Prueba.py           # capturar (genera un CSV nuevo en capturas/)
./venv/bin/python3 plot_csv.py         # revisar esa captura graficada
```

## Historial de cambios

Todo error corregido, cambio y mejora se documenta con fecha en [`CHANGELOG.md`](CHANGELOG.md). Última entrada: **2026-09-24** (eje z en 3D, visor de dos POV, antebrazo con YOLO pose, velocidad; corregidos: `q` no cerraba bien, lentitud y detección del antebrazo; POV independientes).
