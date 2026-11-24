# Cambios: comandos, partes quitadas y por qué — HandMotion3D

Resumen de todo lo que cambió en el proyecto: los comandos de ahora, los de antes, lo que se quitó o reemplazó en el código y por qué. El detalle fechado de cada versión está en [`CHANGELOG.md`](../CHANGELOG.md); todos los comandos, en [`COMANDOS.md`](../COMANDOS.md).

> Hasta la versión 17-E (2026-11-17) esta sección estaba dentro del README. Se movió aquí entera para que el README sea solo la guía de uso; se sigue actualizando con cada cambio.

Las versiones se nombran por día y letra. El 2026-09-24 hubo cinco (24-A a 24-E), el 2026-09-28 seis (28-A a 28-F), el 2026-10-19 una (19-A), el 2026-11-17 cinco (17-A a 17-E) y el 2026-11-23 dos (23-A y 23-B). Todos los comandos en un solo lugar: [`COMANDOS.md`](../COMANDOS.md).

| Versión | Qué trajo |
|---------|-----------|
| **24-A** (primera) | Eje `z` en 3D, vista de dos POV con **matplotlib**, antebrazo con YOLO (`yolo11n`) |
| **24-B** (segunda, tras la primera prueba con cámara) | Visor rehecho con **OpenCV**, corrección de `q`, de la lentitud y del antebrazo, velocidad |
| **24-C** (tercera) | **POV independientes**: cada uno con su rotación, zoom, desplazamiento y encuadre |
| **24-D** (cuarta) | **Velocidad de cada dedo** (absoluta y relativa a la muñeca, tecla `f`) |
| **24-E** (quinta) | **Nombre y estructura:** `MediaPipeHands` → **HandMotion3D**, archivos en la raíz del repositorio |
| **28-A** | `Prueba.py` → **`captura.py`**; **versiones fijas** en `requirements.txt` (con las dos variantes de OpenCV iguales) |
| **28-B** | **CSV escrito mientras se graba** (`CsvRecorder`); **`--palma-cm`** y columna `palma_cm` |
| **28-C** | Velocidad con **filtro One Euro** en vez de media exponencial |
| **28-D** | **Dos cámaras** (`estereo.py`, `--estereo`): calibración, triangulación, palma medida, columnas `x_cm`/`y_cm`/`z_cm` |
| **28-E** | **Correcciones de la revisión completa**: reloj monotónico, CSV que se pisaba, cámara que se desconecta, título de la ventana |
| **28-F** | **Pruebas en el repositorio** (`pruebas/`), **registro de comandos** (`COMANDOS.md`) y **de revisiones** (`REVISION.md`); `estereo.py` ya no triangula puntos fuera de la imagen; historial de git sin la línea `Co-Authored-By` |
| **19-A** | **Pausa** (`espacio`/`p`), **Excel para artículos** de ingeniería y de medicina (`exportar_excel.py`, teclas `e`/`m`), **conexión con Unreal Engine** (`unreal_bridge.py`, `--unreal`, [`UNREAL.md`](../UNREAL.md)); `openpyxl` en `requirements.txt` |
| **17-A** | **Correcciones de la revisión 5**: `.gitignore` deja fuera las exportaciones, mano de `--demo` con proporciones reales, comentario de `JOINTS`; **imagen simulada de Unreal** (`docs/imagen_unreal.py`) |
| **17-B** | El **Excel se reemplaza por dos CSV para artículos** (`exportar_csv.py`, tecla `e`): ingeniería (SI) y medicina (estadística descriptiva), en `capturas/articulos/`; se quitan `exportar_excel.py`, la tecla `m` y `openpyxl` |
| **17-C** | **Analizar videos grabados** (`captura.py --video`, `--video-espejado`): el tiempo sale del video |
| **17-D** | **Datos de cada sesión** (`sesion.py`, `hand_data_<inicio>.json`): participante, fuente con huella SHA-256, parámetros, versiones; `--participante`, `--notas` |
| **23-A** | **Panel** (`panel.py`); **`unreal_bridge.py --csv`** (reproducir una captura en Unreal); **proyecto de Unreal** listo (`unreal/HandMotionUE`), **probado en UE 5.8**, con **imágenes reales** (`docs/imagenes_unreal.py`) en lugar de la simulada; CSV siempre en UTF-8 (en Windows fallaba con acentos); probado en Windows |
| **23-B** | **YOLO en la GPU NVIDIA**: `forearm.py` elige CUDA; torch con CUDA 13.0 (paso 2b del README) |
| **17-E** | **README reestructurado** como guía de uso (instalación para macOS/Linux y Windows, primera captura, recetas); lo técnico pasa a `docs/TECNICO.md`, la guía para publicar a `docs/ARTICULOS.md` y esta sección a `docs/CAMBIOS.md` |

### Comandos actuales (referencia completa)

`captura.py` (captura en vivo):

| Comando / flag | Default | Qué hace | Desde |
|----------------|---------|----------|-------|
| `./venv/bin/python3 captura.py` | — | Cámara + vista 3D de dos POV + antebrazo + velocidad | 28-A (antes `Prueba.py`) |
| `--max-hands N` | `4` | Máximo de manos a la vez | Inicial |
| `--min-detection-confidence X` | `0.5` | Confianza para detectar una mano nueva | 2026-09-23 |
| `--min-presence-confidence X` | `0.5` | Confianza para seguir considerando presente una mano | 2026-09-23 |
| `--min-tracking-confidence X` | `0.5` | Confianza del tracking entre frames | 2026-09-23 |
| `--cam-width W` / `--cam-height H` | `1280` / `720` | Resolución pedida a la cámara | 2026-09-23 |
| `--sin-antebrazo` | apagado | No carga YOLO; el esqueleto llega hasta la muñeca | 24-A |
| `--sin-3d` | apagado | No abre la vista 3D | 24-A |
| `--yolo-modelo {n,s,m}` | `s` | Modelo YOLO pose: `n` rápido, `s` equilibrado, `m` preciso | 24-B |
| `--antebrazo-solo-yolo` | apagado | No dibuja antebrazos estimados | 24-B |
| `--palma-cm CM` | `9.5` | Largo de tu palma: escala de los cm/s | 28-B |
| `--cam N` | `0` | Índice de la cámara (la 1 con `--estereo`) | 28-D |
| `--estereo` | apagado | Dos cámaras: profundidad y palma medidas | 28-D |
| `--cam2 N` | `1` | Segunda cámara | 28-D |
| `--calibracion ARCHIVO` | `calibracion/estereo.npz` | Calibración estéreo | 28-D |
| `--unreal [HOST:PUERTO]` | apagado (sin valor: `127.0.0.1:8000`) | Manda la pose de las manos a Unreal Engine por OSC/UDP (ver [`UNREAL.md`](../UNREAL.md)) | 19-A |
| `--video ARCHIVO` / `--video-espejado` | apagado | Analiza un video grabado (el tiempo sale del video) / el video ya está en espejo | 17-C |
| `--participante CODIGO` / `--notas TEXTO` | vacío | Datos para el `.json` de la sesión; el participante va también al CSV de medicina | 17-D |

`estereo.py` (dos cámaras, desde la 28-D):

| Comando / flag | Default | Qué hace |
|----------------|---------|----------|
| `./venv/bin/python3 estereo.py tablero` | — | Genera `calibracion/tablero_9x6.png` para imprimir |
| `tablero --tablero COLxFIL` | `9x6` | Esquinas internas del tablero |
| `tablero --cuadro-px N` | `120` | Lado de cada cuadro en el PNG |
| `./venv/bin/python3 estereo.py calibrar --cuadro-mm MM` | (obligatorio) | Calibra las dos cámaras; `MM` = lado del cuadro impreso |
| `calibrar --tablero COLxFIL` | `9x6` | Esquinas internas del tablero |
| `calibrar --cam1 N` / `--cam2 N` | `0` / `1` | Índices de las cámaras |
| `calibrar --cam-width W` / `--cam-height H` | `1280` / `720` | Resolución (la misma que se usará en `captura.py`) |
| `calibrar --salida ARCHIVO` | `calibracion/estereo.npz` | Dónde guardar la calibración |

`exportar_csv.py` (dos CSV para artículos, desde la 17-B; reemplaza a `exportar_excel.py`):

| Comando / flag | Default | Qué hace |
|----------------|---------|----------|
| `./venv/bin/python3 exportar_csv.py` | — | Los dos CSV (ingeniería y medicina) del último CSV de `capturas/` |
| `exportar_csv.py capturas/archivo.csv` | el último CSV | Un CSV de captura específico |
| `--formato {ingenieria,medicina,ambos}` | `ambos` | Generar solo uno |
| `--participante CODIGO` | el del `.json` de la sesión, o vacío | Llena la columna `participante` (medicina) |
| `--salida CARPETA` | `articulos/` junto a la captura | Dónde guardarlos |
| `--todos-los-puntos` | apagado | Una serie por cada uno de los 22 puntos (por defecto: muñeca, puntas y codo) |

`unreal_bridge.py` (herramientas de prueba, desde la 19-A; el envío real es `captura.py --unreal`):

| Comando / flag | Qué hace |
|----------------|----------|
| `./venv/bin/python3 unreal_bridge.py --escuchar PUERTO` | Muestra los mensajes que llegan a ese puerto (comprobar sin Unreal) |
| `unreal_bridge.py --demo HOST:PUERTO` | Manda una mano sintética que abre y cierra los dedos (armar Unreal sin cámara) |
| `--segundos S` | Termina sola tras S segundos (default: sin fin) |

`plot_csv.py` (reproducir un CSV):

| Comando / flag | Qué hace | Desde |
|----------------|----------|-------|
| `./venv/bin/python3 plot_csv.py` | Anima en 2D el último CSV de `capturas/` | Inicial |
| `plot_csv.py capturas/archivo.csv` | Usa un CSV específico | Inicial |
| `--frame N` | Un solo frame (en 2D estático; en 3D arranca en pausa ahí) | Inicial (en 3D: 24-B) |
| `--interval MS` | ms entre frames de la animación (default `33`) | Inicial |
| `--swap-hands` | Invierte Left/Right (CSVs de antes del 2026-09-23) | 2026-09-23 |
| `--palma-cm CM` | Palma para los cm/s en `--3d` (por defecto, la del CSV) | 28-B |
| `--3d` | Reproduce en la vista 3D de dos POV | 24-A (visor OpenCV: 24-B) |

Teclas:

| Dónde | Teclas |
|-------|--------|
| Captura (cualquiera de las dos ventanas) | `q`/`Esc` salir y guardar · `n` nombres · `v` velocidad · `f` dedos absoluta/relativa · `s` foto · `espacio`/`p` **pausa** · `e` **CSV para artículos** (ingeniería y medicina) · `u` pausar el envío a Unreal |
| Vista 3D (POV bajo el mouse) | arrastrar = girar · `Shift`+arrastrar o botón central = mover · rueda/clic derecho/`+`/`-` = zoom · `1` `3` `7` `9` vistas · `.` encuadrar · `r` reiniciar |
| Vista 3D (los dos POV) | `l` vincular 180 · `v` velocidad · `f` dedos absoluta/relativa |
| Reproducción 2D | `espacio` pausa / sigue |
| Reproducción `--3d` | `espacio` o `p` pausa · `a`/`d` frame anterior/siguiente · `q`/`Esc` salir · más las de la vista 3D |

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
| `cd MediaPipeHands` antes de cualquier comando | Los comandos se corren desde la **raíz** del repositorio (`cd HandMotion3D`) | 24-E | El proyecto ahora es todo el repositorio, no una subcarpeta |
| `./venv/bin/pip install -r requirements.txt` | `./venv/bin/python3 -m pip install -r requirements.txt` | 24-E | El script `pip` del venv guarda una ruta absoluta y se rompe al mover la carpeta |
| Nombre del proyecto **MediaPipeHands**, repositorio **Machine_Learning** | **HandMotion3D** (proyecto, carpeta y repositorio) | 24-E | Ya no es un ejercicio suelto de Machine Learning sino un proyecto propio |
| `./venv/bin/python3 Prueba.py` | `./venv/bin/python3 captura.py` (mismos flags) | 28-A | "Prueba" era el nombre de cuando el proyecto era un ejercicio; hoy es el programa principal y el nombre no lo decía |
| `requirements.txt` con solo `mediapipe` fijado | **Todas** las dependencias con versión fija | 28-A | Un `pip install` nuevo podía traer versiones que rompieran el proyecto, como ya pasó con `mediapipe` 1.0 |
| `opencv-contrib-python` sin versión (y `opencv-python` traído por `ultralytics`) | Las dos fijadas a `5.0.0.93` | 28-A | Comparten la carpeta `cv2/`: en versiones distintas se pisan y `cv2` puede romperse |
| Ventana `MediaPipe Hands` | Ventana `HandMotion3D - Camara` | 28-A | Quedaba el nombre viejo del proyecto |
| El CSV se escribía **al salir**, todo junto | Se escribe **mientras se graba** (vaciado a disco cada 1 s) | 28-B | Una sesión larga ocupaba cada vez más RAM y una caída perdía toda la grabación |
| Nombre del CSV con la hora de **salida** | Hora de **inicio**; `_2`, `_3`… si ya existe | 28-B / 28-E | La hora de inicio identifica la sesión; y dos sesiones en el mismo segundo se pisaban |
| Palma fija de 9.5 cm para los cm/s | `--palma-cm` (y medida con `--estereo`) | 28-B | Con una palma distinta todas las velocidades salían desviadas en la misma proporción |
| Velocidad suavizada con media exponencial (`VELOCITY_SMOOTHING = 0.35`) | Filtro **One Euro** | 28-C | Mitad de temblor con la mano quieta y mitad de retraso al arrancar y frenar (ver [Velocidad](TECNICO.md#por-qué-one-euro-y-no-la-media-exponencial-de-antes)) |
| Siempre la cámara `0` | `--cam N` | 28-D | Elegir la cámara (hace falta con dos) |
| Solo una cámara | `--estereo` con `estereo.py` | 28-D | Medir la profundidad y la palma en vez de estimarlas |
| `e` = Excel de ingeniería, `m` = Excel de medicina (`.xlsx` junto al CSV) | `e` = **los dos CSV** para artículos, en `capturas/articulos/`; `m` ya no hace nada | 17-B | Pedido: solo CSV, uno con el formato de ingeniería y otro con el de medicina, para publicaciones científicas |
| `exportar_excel.py --formato X [--salida ARCHIVO.xlsx]` | `exportar_csv.py [--formato X\|ambos] [--salida CARPETA] [--participante CODIGO]` | 17-B | Ídem; un CSV lo lee cualquier programa de estadística, sin depender de que Excel recalcule fórmulas |
| Solo la cámara en vivo | `--video ARCHIVO` | 17-C | Reanalizar sesiones, procesar videos ya grabados y que otra persona reproduzca los resultados |
| El README (1,100 líneas) tenía la guía, la parte técnica y el historial | README = guía de uso; `docs/TECNICO.md`, `docs/ARTICULOS.md`, `docs/CAMBIOS.md` | 17-E | Antes de la primera instrucción había 6 bloques de novedades; faltaban Windows, requisitos y una receta para sesiones de artículos |
| Si la cámara dejaba de entregar imágenes, el programa terminaba sin decir nada | Avisa `La cámara dejó de entregar imágenes` (y el CSV queda guardado) | 28-E | Se veía como un cierre inexplicable |

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
| Carpeta `MediaPipeHands/` | Raíz del repositorio | Los mismos archivos en la raíz (movidos con `git mv`, conservan su historial) | Proyecto propio: todo el repositorio le pertenece (24-E) |
| Reglas `MediaPipeHands/models/*`, `MediaPipeHands/capturas/*` | `.gitignore` | `models/*.task`, `models/*.pt`, `capturas/*.csv`, `capturas/*.png` | Las rutas cambiaron al mover la carpeta; sin esto los modelos y capturas se habrían subido a git (24-E) |
| Archivo `Prueba.py` | Raíz | `captura.py` (movido con `git mv`: `git log --follow captura.py`) | Nombre descriptivo (28-A) |
| `export_to_csv(records)` y la lista `records` en memoria | `captura.py` | Clase `CsvRecorder` (`write()` por frame, `close()` al salir) | CSV escrito durante la sesión (28-B) |
| `cap = cv2.VideoCapture(0)` dentro de `main()` | `captura.py` | `open_camera(index, width, height)` | Se abren una o dos cámaras con el mismo código (28-D) |
| `kinematics.cm_per_unit(points)` con la palma fija | `kinematics.py` | `cm_per_unit(points, palm_cm=9.5)`, `hand_scale(hand)` y la escala guardada en cada mano (`hand["cm_per_unit"]`, `hand["palm_cm"]`) | Palma configurable o medida (28-B) |
| `finger_speeds(points, velocities)` | `kinematics.py` | `finger_speeds(points, velocities, scale=None)` | Usar la escala de cada mano (28-B) |
| Constante `VELOCITY_SMOOTHING` y el estado `(t, pos, vel)` por punto | `kinematics.py` | Clase `OneEuroFilter` (una por mano y punto) y `EURO_MIN_CUTOFF`, `EURO_BETA`, `EURO_D_CUTOFF` | Filtro One Euro (28-C) |
| `load_frames()` devolvía 4 valores | `plot_csv.py` | Devuelve 5 (agrega `palma_cm` de cada mano y frame) | Reproducir con la misma escala con la que se grabó (28-B) |
| `time.time()` para timestamps y FPS | `captura.py` | `time.monotonic()` y timestamps que siempre crecen | La hora del sistema puede saltar hacia atrás y MediaPipe exige timestamps crecientes (28-E) |
| `StereoHands.update` triangulaba los 21 puntos siempre | `estereo.py` | Solo los puntos dentro de las dos imágenes (`_inside`, `MIN_VISIBLE_POINTS`, `INSIDE_MARGIN_FRAC`); `StereoHand.points_cm` tiene `None` en los de afuera y `palm_cm` puede ser `None` hasta poder medirla | Fuera de la imagen el modelo del lente no vale y el punto se corría varios cm (28-F) |
| `exportar_excel.py` (Excel con hojas Parámetros/Ecuaciones/Resultados o Métodos/Tabla 1/Tabla 2, fórmulas de Excel) y `pruebas/excel_simulado.py` | Raíz, `pruebas/` (19-A) | `exportar_csv.py` (una fila por serie, números ya calculados) y `pruebas/exportar_csv_simulado.py`; las ecuaciones, limitaciones y notas estadísticas pasaron al README | Pedido: solo CSV (17-B). Además resolvía tres hallazgos de la revisión 5: palma «más repetida», `523.00` fotogramas y fórmulas vacías en vistas previas |
| `export_excel_now(recorder, fmt)` y `EXCEL_KEYS` | `captura.py` (19-A) | `export_now(recorder)` y `EXPORT_KEY` (`e`) | Un solo comando genera los dos formatos (17-B) |
| `openpyxl==3.1.5` | `requirements.txt` (19-A) | — | Ya no hace falta (17-B) |
| `frame_idx` como cuenta de fotogramas procesados | `captura.py` | `frames_read` (para el `.json`) | Al salir con `q`, `frame_idx` iba uno atrás (17-D) |
| Mano de `demo_hand()` armada con offsets fijos (y `points[9]` sobrescrito al final) | `unreal_bridge.py` (19-A) | `demo_hand()` con `_DEMO_FINGERS`: nudillos, falanges y flexión máxima de una mano adulta | El dedo medio salía doblado 109° hacia atrás con la mano abierta; en Unreal se habría visto un dedo roto (17-A) |
| Scripts de comprobación sueltos, fuera del repositorio | — | `pruebas/` (`correr_todo.py`, `filtro_velocidad.py`, `estereo_simulado.py`, `captura_simulada.py`) | Poder repetir cada número documentado (28-F) |

### Versiones del formato del CSV

| Versión | Columnas | `plot_csv.py` la lee |
|---------|----------|----------------------|
| Inicial | `frame, timestamp_ms, hand_index, handedness, score, landmark_index, x, y, z` | Sí |
| Con `HandTracker` | `hand_index` → `hand_id` | Sí |
| 24-A | + `img_w, img_h`; fila extra `landmark_index = 21` (codo) | Sí |
| 24-B | + `vx, vy, vz, rapidez_cm_s, fuente` | Sí (en CSVs viejos la velocidad se calcula al leer) |
| 24-D | + `rapidez_rel_cm_s, dedo` (entre `rapidez_cm_s` y `fuente`) | Sí |
| 28-B / 28-D (actual) | + `palma_cm, x_cm, y_cm, z_cm` al final (`x_cm`/`y_cm`/`z_cm` solo con `--estereo`); `fuente` puede ser `estereo` | Sí (en CSVs viejos usa 9.5 cm o `--palma-cm`) |

## Historial

Todo error corregido, cambio y mejora se documenta con fecha en [`CHANGELOG.md`](../CHANGELOG.md); las revisiones, en [`REVISION.md`](../REVISION.md); los comandos ejecutados sobre el repositorio, en la [bitácora de `COMANDOS.md`](../COMANDOS.md#3-bitácora-de-mantenimiento).

Última entrada: **2026-11-17**, versiones **17-A** (correcciones de la revisión 5 e imagen simulada de Unreal) y **17-B** (el Excel se reemplaza por dos CSV para artículos: ingeniería y medicina). Antes, **2026-10-19**, versión **19-A** (pausa, Excel para artículos y conexión con Unreal Engine); antes, **2026-09-28**, versiones **28-A** (`captura.py`, versiones fijas), **28-B** (CSV mientras se graba, `--palma-cm`), **28-C** (filtro One Euro), **28-D** (dos cámaras), **28-E** (correcciones de la revisión completa) y **28-F** (pruebas, registro de comandos y de revisiones, puntos fuera de cuadro en estéreo, historial sin `Co-Authored-By`), más la revisión de la documentación de ese mismo día. Antes, el **2026-09-24**: eje z en 3D, visor de dos POV, antebrazo con YOLO pose y velocidad (24-A/24-B), POV independientes (24-C), velocidad de cada dedo (24-D) y el cambio de nombre a HandMotion3D (24-E).

> **Hashes de commits:** el 2026-09-28 se reescribió el historial para quitar una línea `Co-Authored-By` de los mensajes, así que los commits anteriores tienen hashes nuevos (el contenido es el mismo). La tabla de correspondencia está en [`COMANDOS.md`](../COMANDOS.md#2026-09-28--versión-28-f-quitar-la-línea-co-authored-by-del-historial).
