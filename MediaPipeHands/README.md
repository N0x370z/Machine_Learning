# MediaPipeHands

> Última actualización: **2026-09-24**. Historial completo de errores, cambios y mejoras en [`CHANGELOG.md`](CHANGELOG.md).

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
- Arriba a la izquierda, el **panel de estado**: FPS, manos, antebrazos (cuántos de YOLO y cuántos estimados), frames grabados, la **velocidad de la muñeca de cada mano en cm/s** y cuántos ms tarda cada etapa (`mano`, `yolo`, `3D`), para ver qué frena si los FPS bajan.

Además se abre una segunda ventana, **Vista 3D - dos POV**, con la misma mano en 3D vista desde dos ángulos a la vez: el **POV 1** desde el lado de la cámara y el **POV 2** girado **180°**, desde atrás. Arrastra con el mouse sobre cualquiera de las dos para girarla; con "Vincular 180" activado la otra la sigue desde el lado opuesto. Los controles completos están en [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy).

Las teclas funcionan con **cualquiera de las dos ventanas** activa (haz clic en una si no responde):

| Tecla | Qué hace |
|-------|----------|
| `n` | Muestra/oculta los nombres de los dedos |
| `v` | Muestra/oculta las flechas de velocidad (en las dos ventanas) |
| `s` | Guarda una foto de la vista de la cámara en `capturas/` |
| `q` o `Esc` | Termina y guarda los datos |
| `1` `3` `7` `9` `.` `l` `r` `+` `-` | Controles de la vista 3D (ver más abajo) |

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
| `v` | Mostrar/ocultar las flechas de velocidad |
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

### Controles

Las teclas funcionan con la vista 3D o con la ventana de la cámara activa. Las de vista (`1`, `3`, `7`, `9`, `+`, `-`) actúan sobre el POV que tenga el mouse encima (resaltado con un fondo un poco más claro), igual que en Blender:

| Acción | Qué hace |
|--------|----------|
| Arrastrar con clic izquierdo sobre una vista | Gira esa vista (órbita) |
| Rueda del mouse, clic derecho arrastrando, o `+` / `-` | Zoom de esa vista |
| `1` | Vista de **frente** (como la ve la cámara) |
| `3` | Vista de **lado** |
| `7` | Vista desde **arriba** |
| `9` | Vista **opuesta** a la actual (frente ↔ atrás, arriba ↔ abajo), como en Blender |
| `.` | Activa/desactiva **Encuadrar** |
| `l` | Activa/desactiva **Vincular 180** |
| `r` | Reinicia ambas vistas y el zoom |
| `v` | Muestra/oculta las flechas de velocidad |
| Botones *Frente / Atras / Lado / Arriba* | Lo mismo que las teclas, bajo cada vista |
| Botón **Vincular 180** (azul = activo) | Activo por defecto: al girar una vista la otra la sigue a 180°. Apágalo para mover cada POV por su cuenta |
| Botón **Encuadrar** (azul = activo) | Activo por defecto: la vista sigue a las manos para verlas grandes (con un seguimiento suavizado para que no vibre). Apagado, se ve el frame completo de la cámara |

La pirámide gris marca dónde está la **cámara**, para ubicarse al girar.

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
- Teclas en la reproducción 3D: `espacio` pausa/sigue, `a`/`d` frame anterior/siguiente, `v` velocidad, `q`/`Esc` salir, más todas las del visor (`1`, `3`, `7`, `9`, `.`, `l`, `r`, `+`, `-`, mouse).
- Si el CSV tiene codo (landmark 21), el antebrazo se dibuja en azul en ambos modos.
- Sin cámara ni modelo `.task` de por medio: solo lee el CSV, así que corre incluso sin permisos de cámara.

## Flujo típico

```bash
./venv/bin/python3 Prueba.py           # capturar (genera un CSV nuevo en capturas/)
./venv/bin/python3 plot_csv.py         # revisar esa captura graficada
```

## Historial de cambios

Todo error corregido, cambio y mejora se documenta con fecha en [`CHANGELOG.md`](CHANGELOG.md). Última entrada: **2026-09-24** (eje z en 3D, visor de dos POV, antebrazo con YOLO pose, velocidad; corregidos: `q` no cerraba bien, lentitud y detección del antebrazo).
