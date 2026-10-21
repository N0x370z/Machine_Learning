# HandMotion3D

Seguimiento de la **mano y el antebrazo en 3D** con una webcam (o dos, para medir la profundidad real): esqueleto de la mano con MediaPipe, codo con YOLO pose, vista 3D con dos puntos de vista independientes (como Blender) y velocidad de cada punto y de cada dedo.

> **Novedades del 2026-10-19 (versión 19-A):** **pausa** de la captura (`espacio` o `p`), **Excel para artículos** de ingeniería y de medicina (`e` / `m` durante la captura, o `exportar_excel.py`) y **conexión con Unreal Engine** para mover un modelo 3D con la mano (`--unreal`, guía en [`UNREAL.md`](UNREAL.md)). Detalle en [Pausa](#pausa), [Exportar a Excel](#exportar-a-excel-exportar_excelpy) y [Unreal Engine](#unreal-engine-unreal_bridgepy).

> **Novedades del 2026-09-28 (versiones 28-A a 28-F):** `Prueba.py` pasa a llamarse **`captura.py`**; dependencias con **versiones fijas**; el CSV se **escribe mientras se graba**; **`--palma-cm`** para que los cm/s usen el tamaño de tu mano; velocidad con **filtro One Euro** (menos temblor y menos retraso); y **dos cámaras** (`--estereo`, [`estereo.py`](#dos-cámaras-estereopy)) para medir la profundidad y la palma de verdad. Además, desde la 28-F hay **pruebas sin cámara** ([`pruebas/`](pruebas/README.md)), un **registro de comandos** ([`COMANDOS.md`](COMANDOS.md)) y un **registro de revisiones** ([`REVISION.md`](REVISION.md)). Detalle en [Cambios](#cambios-comandos-partes-quitadas-y-por-qué) y en [`CHANGELOG.md`](CHANGELOG.md).

> **Nombre y estructura (2026-09-24, versión 24-E):** el proyecto se llamaba **MediaPipeHands** y vivía en la carpeta `MediaPipeHands/` de un repositorio general de Machine Learning (`Machine_Learning`). Como ya no es solo un ejercicio de ML sino un proyecto propio (detección, 3D, antebrazo, velocidad), pasó a llamarse **HandMotion3D** y sus archivos se movieron a la **raíz del repositorio**. Detalle en [Cambios: comandos, partes quitadas y por qué](#cambios-comandos-partes-quitadas-y-por-qué).

> Última actualización: **2026-10-19**. Historial completo de errores, cambios y mejoras en [`CHANGELOG.md`](CHANGELOG.md). Resumen de **comandos nuevos y antiguos, partes quitadas y por qué** en [Cambios: comandos, partes quitadas y por qué](#cambios-comandos-partes-quitadas-y-por-qué).

### Documentos del proyecto

| Documento | Para qué |
|-----------|----------|
| **README.md** (este) | Qué hace el proyecto, cómo usarlo y cómo funciona cada parte |
| [`COMANDOS.md`](COMANDOS.md) | **Registro de comandos**: todos los comandos, flags y teclas en un lugar; los que cambiaron; y la bitácora de comandos de mantenimiento ejecutados (git, pip) con cómo deshacerlos |
| [`CHANGELOG.md`](CHANGELOG.md) | Historial fechado, versión por versión |
| [`REVISION.md`](REVISION.md) | Revisiones del proyecto: qué se encontró, qué se corrigió y qué queda pendiente |
| [`pruebas/README.md`](pruebas/README.md) | Pruebas sin cámara: qué comprueba cada una y qué no cubren |
| [`UNREAL.md`](UNREAL.md) | **Conexión con Unreal Engine**: formato de los mensajes, plugin OSC, Blueprint y cómo mover los dedos de un modelo 3D |

### Índice

1. [Guía rápida de uso](#guía-rápida-de-uso) · [Problemas comunes](#problemas-comunes)
2. [Estructura del proyecto](#estructura-del-proyecto) · [Instalación](#instalación) · [Versiones fijadas](#versiones-fijadas)
3. [`captura.py` — captura en vivo](#capturapy--captura-en-vivo) · [Formato del CSV](#formato-del-csv-exportado)
4. [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy) · [Antebrazo](#antebrazo-forearmpy) · [Velocidad](#velocidad-kinematicspy)
5. [Dos cámaras (`estereo.py`)](#dos-cámaras-estereopy) · [`plot_csv.py`](#plot_csvpy--graficar-los-puntos-del-csv)
6. [Pausa](#pausa) · [Exportar a Excel (`exportar_excel.py`)](#exportar-a-excel-exportar_excelpy) · [Unreal Engine (`unreal_bridge.py`)](#unreal-engine-unreal_bridgepy)
7. [Pruebas](#pruebas) · [Cambios: comandos, partes quitadas y por qué](#cambios-comandos-partes-quitadas-y-por-qué) · [Historial](#historial-de-cambios)

Detección de manos en tiempo real con [MediaPipe Tasks API](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker), vista 3D de la mano con **dos puntos de vista (POV)** a la vez (como los viewports de Blender) usando la profundidad `z`, el esqueleto extendido **hasta el antebrazo** (codo detectado con YOLO pose), la **velocidad** de cada punto (a partir de `x`, `y`, `z` y del tiempo de cada fotograma), opcionalmente la **profundidad real con dos cámaras** (triangulación estéreo), captura de los 21 landmarks por mano (+ el codo) en un CSV, y un script separado para volver a graficar esos mismos puntos a partir del CSV (sin necesidad de la cámara).

## Guía rápida de uso

Todos los comandos se corren desde la **raíz del repositorio** (la carpeta del proyecto, donde está este README). Antes había que entrar a `MediaPipeHands/`; ya no existe:

```bash
cd HandMotion3D   # o la carpeta donde clonaste el repositorio
```

### 1. Preparar el entorno (solo la primera vez)

```bash
python3 -m venv venv
./venv/bin/python3 -m pip install -r requirements.txt

mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

El modelo de YOLO para el antebrazo (`models/yolo11s-pose.pt`, ~20 MB) no hace falta bajarlo a mano: se descarga solo la primera vez que corres `captura.py` (necesita internet esa primera vez).

En macOS, la primera vez que abras la cámara el sistema te pide permiso para la terminal (Terminal, iTerm, VS Code…). Si lo negaste, actívalo en **Ajustes del Sistema → Privacidad y Seguridad → Cámara** y vuelve a abrir la terminal.

### 2. Capturar tus manos

```bash
./venv/bin/python3 captura.py
```

> Hasta el 2026-09-28 este script se llamaba **`Prueba.py`**. `./venv/bin/python3 Prueba.py` ya no existe: usa `captura.py` (mismos flags).

**Recomendado: mide tu palma.** Las velocidades en cm/s usan el largo de la palma como regla (del pliegue de la muñeca al nudillo del dedo medio, donde el dedo se une a la palma). Si no lo indicas se suponen 9.5 cm (adulto promedio); si tu palma mide, por ejemplo, 8.5 cm, todas las velocidades salen ~12 % más altas de lo real. Mídela con una regla y pásala así:

```bash
./venv/bin/python3 captura.py --palma-cm 8.5
```

Con dos cámaras (`--estereo`) no hace falta: la palma se mide sola (ver [Dos cámaras](#dos-cámaras-estereopy)).

Se abre una ventana con la cámara en modo espejo, como si te vieras en un espejo. Pon una o dos manos frente a la cámara y verás:

- El **esqueleto de cada mano**, con un color por dedo y el **nombre del dedo** en cada punta (Pulgar, Indice, Medio, Anular, Menique).
- Junto a la muñeca, la etiqueta **`Left #0` / `Right #1`**: indica qué mano es (izquierda/derecha real de la persona) y un número que identifica a esa mano mientras siga en cámara.
- El **antebrazo** en azul, desde el **codo** hasta la muñeca: **grueso y sólido** si YOLO ve el codo, **fino y punteado** con la etiqueta `Codo (estimado)` si no lo ve y se estima por la dirección de la palma (ver [Antebrazo](#antebrazo-forearmpy)).
- **Flechas amarillas de velocidad** en la muñeca, las puntas de los dedos y el codo: apuntan hacia donde se mueve cada punto y son más largas cuanto más rápido va (ver [Velocidad](#velocidad-kinematicspy)).
- Junto al nombre de cada dedo, su **velocidad en cm/s** (p. ej. `Indice 32`).
- Arriba a la izquierda, el **panel de estado**: FPS, manos, antebrazos (cuántos de YOLO y cuántos estimados), frames grabados, la **velocidad de la muñeca** y la **de cada dedo** de cada mano en cm/s, y cuántos ms tarda cada etapa (`mano`, `yolo`, `3D` y, con dos cámaras, `estereo`), para ver qué frena si los FPS bajan.

Además se abre una segunda ventana, **Vista 3D - dos POV**, con la misma mano en 3D vista desde dos ángulos a la vez: el **POV 1** arranca desde el lado de la cámara y el **POV 2** girado **180°**, desde atrás. **Cada POV es una cámara virtual independiente**: al girarlo, moverlo o hacerle zoom, el otro no se mueve. Todo se aplica al POV que tenga el mouse encima (el marcado como `(activo)`). Si quieres que se muevan juntos a 180°, activa **Vincular 180** (tecla `l`). Los controles completos están en [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy).

Las teclas funcionan con **cualquiera de las dos ventanas** activa (haz clic en una si no responde):

| Tecla | Qué hace |
|-------|----------|
| `n` | Muestra/oculta los nombres de los dedos |
| `v` | Muestra/oculta las flechas y los números de velocidad (en las dos ventanas) |
| `f` | Cambia la velocidad de cada dedo entre **absoluta** y **relativa a la muñeca** |
| `s` | Guarda una foto de la vista de la cámara en `capturas/` |
| `espacio` o `p` | **Pausa** / sigue (ver [Pausa](#pausa)) |
| `e` / `m` | Genera el **Excel** de lo grabado: `e` formato ingeniería, `m` formato medicina (ver [Exportar a Excel](#exportar-a-excel-exportar_excelpy)) |
| `u` | Con `--unreal`: pausa / reanuda el envío a Unreal Engine |
| `q` o `Esc` | Termina y guarda los datos |
| `1` `3` `7` `9` `.` `r` `+` `-` | Controles del POV bajo el mouse en la vista 3D (ver más abajo) |
| `l` | Vincular/desvincular la rotación de los dos POV a 180° |

### 3. Terminar y guardar

Presiona **`q`** o **`Esc`** en cualquiera de las dos ventanas, o cierra la ventana de la cámara con el botón rojo. Se cierran las ventanas y en la terminal aparece la ruta del CSV, por ejemplo:

```
Datos exportados a capturas/hand_data_20260928_115410.csv
```

**El CSV se va escribiendo mientras grabas** (desde la versión 28-B), no solo al salir: si el programa se cae o se corta la luz, se pierde como mucho el último segundo. El nombre lleva la hora en que **empezó** la sesión (antes era la hora de salida); si ya existe uno con ese nombre se agrega `_2`, `_3`…

Si no se detectó ninguna mano en toda la sesión, no se crea el CSV (fíjate que "Frames grabados" no esté en 0 antes de salir). Cerrar solo la ventana de la vista 3D no termina la captura: la cámara sigue grabando sin el 3D. Con `Ctrl+C` en la terminal el CSV también queda completo.

### 4. Ver lo que grabaste

```bash
./venv/bin/python3 plot_csv.py              # reproduce la última captura como animación
./venv/bin/python3 plot_csv.py --frame 38   # o solo un instante fijo
./venv/bin/python3 plot_csv.py --3d         # en 3D, con los dos POV
```

No necesita cámara: solo lee el CSV. En 2D, cierra la ventana de matplotlib para terminar. En 3D: `espacio` pausa, `a`/`d` retroceden/avanzan un frame, `v` muestra/oculta la velocidad, `f` alterna la velocidad de los dedos absoluta/relativa y `q`/`Esc` salen. Si el CSV es de antes del 2026-09-23 (Left/Right invertidos), agrega `--swap-hands`. En 3D las velocidades usan la palma con la que se grabó (columna `palma_cm`); `--palma-cm` la reemplaza.

### 5. (Opcional) Profundidad real con dos cámaras

Con dos webcams fijas, separadas 10–30 cm y mirando a la misma zona, la profundidad deja de ser una estimación de MediaPipe y se mide (ver [Dos cámaras](#dos-cámaras-estereopy)):

```bash
./venv/bin/python3 estereo.py tablero                  # 1. genera un tablero para imprimir
./venv/bin/python3 estereo.py calibrar --cuadro-mm 25  # 2. calibra (mide el cuadro impreso)
./venv/bin/python3 captura.py --estereo                # 3. captura con las dos
```

### Problemas comunes

| Síntoma | Solución |
|---------|----------|
| `No se pudo abrir la cámara` | Da permiso de cámara a la terminal (ver paso 1) y ciérrala y ábrela de nuevo. Cierra otras apps que estén usando la cámara (Zoom, FaceTime…). |
| `No se encontró el modelo en models/hand_landmarker.task` | Falta descargar el modelo (ver paso 1). |
| Le cuesta detectar la mano o la pierde | Más luz, acerca la mano, o baja el umbral: `./venv/bin/python3 captura.py --min-detection-confidence 0.3 --min-tracking-confidence 0.3` |
| Los nombres de los dedos se enciman | Tecla `n` para ocultarlos |
| Crashea con `Service is unavailable` | Se actualizó `mediapipe`; reinstala la versión fijada: `./venv/bin/python3 -m pip install -r requirements.txt` (ver abajo) |
| `import cv2` falla o da errores raros después de instalar algo | Quedaron `opencv-python` y `opencv-contrib-python` en versiones distintas (se pisan, ver [Versiones fijadas](#versiones-fijadas)). Reinstala las dos fijadas: `./venv/bin/python3 -m pip install --force-reinstall opencv-python==5.0.0.93 opencv-contrib-python==5.0.0.93` |
| `can't open file 'Prueba.py'` | Se renombró a `captura.py` (28-A) |
| Las velocidades en cm/s parecen altas o bajas | Indica el largo de tu palma: `--palma-cm 8.5` (ver paso 2), o usa dos cámaras |
| `No hay calibración en calibracion/estereo.npz` | Antes de `--estereo` hay que calibrar: `./venv/bin/python3 estereo.py calibrar --cuadro-mm <lado>` |
| `La cámara abrió a ... pero la calibración es de ...` | Usa la misma resolución que al calibrar (`--cam-width`/`--cam-height`) o vuelve a calibrar |
| Con `--estereo` el panel dice `Estereo: 0/1 manos` | La cámara 2 no ve la mano (mira su ventana, *Camara 2*) o una cámara se movió después de calibrar: vuelve a calibrar. Si `cam2 ve 0`, revisa `--cam2` |
| `La cámara dejó de entregar imágenes` | Se desconectó la cámara o la tomó otra app. El CSV hasta ese momento queda guardado |
| Con `--estereo`, algunas filas tienen `x_cm`/`y_cm`/`z_cm` vacías | Esos puntos estaban fuera de la imagen de alguna cámara (un dedo que se sale del cuadro) y no se triangulan a propósito (28-F). Acerca la mano al centro de las dos imágenes |
| Quiero comprobar que todo funciona sin cámara | `./venv/bin/python3 pruebas/correr_todo.py` (ver [Pruebas](#pruebas)) |
| Las teclas no hacen nada | Haz clic sobre cualquiera de las dos ventanas (cámara o vista 3D) para darle el foco |
| El antebrazo sale punteado, como `Codo (estimado)` | YOLO no ve el codo: aléjate para que el codo entre en cámara, con buena luz y sin ropa del mismo color que el fondo. Si detecta mal, prueba el modelo más preciso: `--yolo-modelo m` |
| No quiero ver antebrazos estimados | `--antebrazo-solo-yolo` (solo se dibuja cuando YOLO ve el codo de verdad) |
| Va lento (FPS bajos) | Mira la línea `ms:` del panel de estado para ver qué etapa tarda más. Si es `yolo`: `--yolo-modelo n` o `--sin-antebrazo`; si es `mano`: `--max-hands 2` o menos resolución (`--cam-width 960 --cam-height 540`) |
| Error al cargar YOLO / descargar `yolo11s-pose.pt` | Falta internet la primera vez, o no está instalado: `./venv/bin/python3 -m pip install -r requirements.txt`. Mientras tanto: `--sin-antebrazo` |

Los detalles de cada script y todas sus opciones están en las secciones siguientes.

## Estructura del proyecto

```
HandMotion3D/           # raíz del repositorio
├── captura.py          # Captura en vivo: cámara(s) + MediaPipe + CSV (antes Prueba.py)
├── plot_csv.py         # Grafica los landmarks guardados en un CSV (2D o 3D)
├── hand_style.py       # Colores por dedo (y antebrazo) compartidos por todas las vistas
├── viewer3d.py         # Visor 3D con dos POV (estilo viewports de Blender)
├── forearm.py          # Antebrazo: codo con YOLO pose + estimación de su z
├── kinematics.py       # Velocidad (filtro One Euro) y escala en cm (palma)
├── estereo.py          # Dos cámaras: calibración y triangulación (profundidad real)
├── exportar_excel.py   # Excel para artículos: formato ingeniería o medicina (19-A)
├── unreal_bridge.py    # Puente OSC/UDP hacia Unreal Engine (19-A)
├── UNREAL.md           # Guía de la conexión con Unreal Engine
├── pruebas/            # Pruebas sin cámara (ver pruebas/README.md)
│   ├── correr_todo.py        # Corre las cinco y resume
│   ├── filtro_velocidad.py   # One Euro vs media exponencial
│   ├── estereo_simulado.py   # Calibración y triangulación simuladas
│   ├── captura_simulada.py   # captura.py y plot_csv.py de punta a punta (con pausa, Excel y Unreal)
│   ├── excel_simulado.py     # exportar_excel.py: estructura y fórmulas
│   └── unreal_simulado.py    # unreal_bridge.py: OSC, ejes, flexión y UDP
├── COMANDOS.md         # Registro de comandos (referencia + bitácora de mantenimiento)
├── REVISION.md         # Registro de revisiones: hallazgos, correcciones, pendientes
├── requirements.txt    # Dependencias con versiones fijas (ver más abajo)
├── CHANGELOG.md        # Registro fechado de errores, cambios y mejoras
├── .gitignore          # Deja fuera de git venv/, modelos, capturas y calibración
├── models/
│   ├── hand_landmarker.task   # Modelo de MediaPipe (se descarga aparte, no va en git)
│   └── yolo11s-pose.pt        # Modelo YOLO pose (se descarga solo, no va en git)
├── capturas/
│   ├── hand_data_YYYYMMDD_HHMMSS.csv   # Un CSV por sesión (hora de inicio)
│   ├── hand_data_YYYYMMDD_HHMMSS_ingenieria.xlsx / _medicina.xlsx   # Excel (teclas 'e' / 'm' o exportar_excel.py)
│   └── screenshot_*.png                 # Fotos tomadas con la tecla 's'
├── calibracion/        # Solo con dos cámaras; no va en git (es de TUS cámaras)
│   ├── estereo.npz     # Calibración (estereo.py calibrar)
│   └── tablero_9x6.png # Tablero para imprimir (estereo.py tablero)
└── venv/               # Entorno virtual del proyecto
```

## Instalación

> Se usa `./venv/bin/python3 -m pip` y no `./venv/bin/pip`: el script `pip` de un venv guarda la ruta absoluta donde se creó el venv, y deja de funcionar si la carpeta se mueve o se renombra (pasó con esta reorganización). `python3 -m pip` funciona siempre.

```bash
python3 -m venv venv
./venv/bin/python3 -m pip install -r requirements.txt
```

Descargar el modelo de landmarks de mano y colocarlo en `models/hand_landmarker.task`:

```bash
mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

### Versiones fijadas

Desde la versión **28-A** (2026-09-28) todas las dependencias tienen versión fija en [`requirements.txt`](requirements.txt): son las instaladas y probadas en el venv del proyecto (**Python 3.14.5**, macOS con Apple Silicon). Antes solo `mediapipe` estaba fijado y el resto se instalaba en su última versión, así que un `pip install` en otra máquina (o dentro de unos meses) podía traer una versión que rompiera el proyecto, como ya pasó con `mediapipe` (ver abajo).

| Paquete | Versión | Por qué se fija |
|---------|---------|-----------------|
| `mediapipe` | `0.10.35` | `1.0.0`/`1.0.1` crashean en macOS (ver abajo) |
| `opencv-python` y `opencv-contrib-python` | `5.0.0.93` (**las dos iguales**) | `mediapipe` pide `opencv-contrib-python` y `ultralytics` pide `opencv-python`. Se instalan en la **misma carpeta `cv2/`**: si quedan en versiones distintas, el que se instala último pisa archivos del otro y `cv2` puede romperse. No se puede evitar tener los dos, pero sí que coincidan |
| `numpy` | `2.5.3` | Lo usan todos los módulos |
| `matplotlib` | `3.11.2` | `plot_csv.py` en 2D |
| `ultralytics` | `8.4.162` | YOLO pose (antebrazo) |
| `torch` / `torchvision` | `2.14.0` / `0.29.0` | Los instala `ultralytics`; son lo más pesado y lo que más cambia entre versiones |
| `openpyxl` | `3.1.5` | Excel de `exportar_excel.py` (19-A); solo se carga al exportar. Se probó fuera del venv del proyecto (ver CHANGELOG, 19-A) |

Para actualizar una dependencia: subir **una** versión, probar `captura.py` (en vivo) y `plot_csv.py` (2D y `--3d`), y recién ahí cambiarla en `requirements.txt` y anotarlo en el CHANGELOG.

### ⚠️ Por qué `mediapipe` está en 0.10.35

Las versiones `1.0.0`/`1.0.1` de `mediapipe` tienen un bug conocido en macOS (Apple Silicon) que crashea cualquier tarea de visión (`HandLandmarker`, `PoseLandmarker`, etc.) con:

```
Check failed: service_ Service is unavailable
```

(`TensorsToDetectionsCalculator` intenta inicializar un helper de Metal/GPU que nunca se registra en un grafo de solo-CPU). Ver [google-ai-edge/mediapipe#6356](https://github.com/google-ai-edge/mediapipe/issues/6356). **No actualizar `mediapipe` sin volver a probar en macOS.**

## `captura.py` — captura en vivo

```bash
./venv/bin/python3 captura.py

# Más de 2 manos a la vez (varias personas en cámara, por ejemplo):
./venv/bin/python3 captura.py --max-hands 4

# Si cuesta que reconozca la mano (poca luz, cámara lejos), bajar el umbral:
./venv/bin/python3 captura.py --min-detection-confidence 0.3

# Sin antebrazo (no carga YOLO) y/o sin la vista 3D de dos POV:
./venv/bin/python3 captura.py --sin-antebrazo
./venv/bin/python3 captura.py --sin-3d

# Modelo YOLO más rápido (n) o más preciso (m) para el codo:
./venv/bin/python3 captura.py --yolo-modelo m

# Antebrazo solo cuando YOLO ve el codo (sin estimados):
./venv/bin/python3 captura.py --antebrazo-solo-yolo

# Velocidades en cm/s con el largo de TU palma (en vez de 9.5 cm):
./venv/bin/python3 captura.py --palma-cm 8.5

# Otra cámara (si la Mac tiene varias, p. ej. una webcam USB):
./venv/bin/python3 captura.py --cam 1

# Dos cámaras: profundidad y palma medidas (calibrar antes, ver "Dos cámaras"):
./venv/bin/python3 captura.py --estereo
./venv/bin/python3 captura.py --estereo --cam 0 --cam2 2 --calibracion calibracion/otra.npz
```

| Flag nuevo (2026-09-24) | Default | Qué hace |
|-------------------------|---------|----------|
| `--sin-antebrazo` | apagado | No detecta el codo/antebrazo con YOLO. Más liviano |
| `--sin-3d` | apagado | No abre la ventana de la vista 3D con dos POV |
| `--yolo-modelo {n,s,m}` | `s` | Tamaño del modelo YOLO pose: `n` ~6 ms (detecta peor el codo), `s` ~9 ms, `m` ~17 ms (más preciso). Se descarga solo a `models/` |
| `--antebrazo-solo-yolo` | apagado | No estima el antebrazo cuando YOLO no ve el codo |

| Flag nuevo (2026-09-28) | Default | Qué hace |
|-------------------------|---------|----------|
| `--palma-cm CM` | `9.5` | Largo de tu palma (pliegue de la muñeca → nudillo del medio), la regla para pasar las velocidades a cm/s. Acepta 5–15 cm (fuera de eso casi seguro es un error de medición o de unidades) |
| `--cam N` | `0` | Índice de la cámara (la cámara 1 con `--estereo`) |
| `--estereo` | apagado | Usa dos cámaras para medir la profundidad y la palma de verdad (ver [Dos cámaras](#dos-cámaras-estereopy)) |
| `--cam2 N` | `1` | Índice de la segunda cámara (solo con `--estereo`) |
| `--calibracion ARCHIVO` | `calibracion/estereo.npz` | Calibración estéreo a usar (solo con `--estereo`) |

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
| `s` | Guardar una foto del frame actual en `capturas/screenshot_<fecha>.png` (con el esqueleto dibujado, sin el panel de estado; con `--estereo`, solo la cámara 1) |
| `espacio` o `p` | **Pausa** / sigue (ver [Pausa](#pausa)) |
| `e` / `m` | **Excel** de lo grabado hasta ese momento: `e` ingeniería, `m` medicina (ver [Exportar a Excel](#exportar-a-excel-exportar_excelpy)) |
| `u` | Con `--unreal`: pausa / reanuda el envío a Unreal Engine |

En la esquina superior izquierda hay un panel de estado con los **FPS** reales, las **manos** detectadas en el frame, los **antebrazos** (de YOLO / estimados), los **frames grabados** hasta ahora para el CSV, la **velocidad de la muñeca** de cada mano en cm/s, una fila por mano con la **velocidad de cada dedo** (`Pul`, `Ind`, `Med`, `Anu`, `Men`; absoluta o relativa según la tecla `f`, se oculta con `v`), los **ms por etapa** (`mano` = MediaPipe, `yolo` = antebrazo, `3D` = dibujar la vista 3D, `estereo` = MediaPipe en la cámara 2) y una línea con el estado de las teclas `n`, `v`, `f`, `s` y `q`. Si los FPS bajan mucho, reduce `--max-hands` o la resolución (`--cam-width`/`--cam-height`). Si "Frames grabados" sigue en 0, no se está detectando ninguna mano y al salir no se va a generar CSV.

Con `--estereo` el panel agrega una línea `Estereo: 1/1 manos (cam2 ve 1)` (cuántas manos de la cámara 1 se encontraron también en la 2) y, por cada mano triangulada, `a 45 cm, palma 8.5 cm, error 1.3 px`: distancia de la muñeca a la cámara 1, palma medida y error de reproyección (ver [Dos cámaras](#dos-cámaras-estereopy)). La ventana del título de la cámara es ahora **`HandMotion3D - Camara`** (antes `MediaPipe Hands`, el nombre viejo del proyecto), y con `--estereo` se abre además **`HandMotion3D - Camara 2`**, a la mitad de tamaño, con las manos que ve la cámara 2 como puntos blancos.

### ⚠️ Corregido: reconocimiento poco confiable de manos

Antes de la versión del **2026-09-23**, el detector podía tardar en reconocer la mano o perderla con facilidad, sobre todo con poca luz, la mano lejos de la cámara, o webcams que abrían a baja resolución por defecto (640×480 es común). Ver detalle en [`CHANGELOG.md`](CHANGELOG.md#2026-09-23). Se corrigió con dos cambios:

- **Resolución de captura más alta por defecto**: `captura.py` ahora le pide a la cámara `1280x720` (antes usaba lo que la cámara abriera por defecto). Ajustable con `--cam-width`/`--cam-height`; si la cámara no soporta la resolución pedida, se ignora sin error.
- **Umbrales de confianza configurables**: antes estaban fijos en `0.5` dentro del código. Ahora son flags:

| Flag | Default | Qué hace |
|------|---------|----------|
| `--min-detection-confidence` | `0.5` | Confianza mínima para detectar una mano nueva. Bajarlo ayuda si cuesta que te reconozca. |
| `--min-presence-confidence` | `0.5` | Confianza mínima para seguir considerando presente una mano ya detectada. |
| `--min-tracking-confidence` | `0.5` | Confianza mínima del tracking entre frames. Bajarlo ayuda si la mano se "pierde" con movimiento rápido. |
| `--cam-width` / `--cam-height` | `1280` / `720` | Resolución de captura solicitada a la cámara. |

Qué hace:

1. Abre la cámara (`--cam`, por defecto la `0`; con `--estereo` también la `--cam2`), solicita la resolución configurada y voltea el frame horizontalmente (efecto espejo). Con dos cámaras toma los dos frames lo más juntos posible (`grab()` en las dos y después `retrieve()`).
2. Corre `HandLandmarker` en modo `VIDEO` (hasta `--max-hands` manos, con los umbrales de confianza configurados) sobre cada frame, con un reloj monotónico para los timestamps (ver 28-E en [Cambios](#cambios-comandos-partes-quitadas-y-por-qué)). Con `--estereo`, un segundo `HandLandmarker` corre sobre la cámara 2.
3. Le da a cada mano un id estable y estabiliza `Left`/`Right` (`HandTracker`, ver más abajo).
4. Con `--estereo`, empareja cada mano con la de la cámara 2, la triangula y reemplaza su `z` por la medida (ver [Dos cámaras](#dos-cámaras-estereopy)).
5. Si hay manos, busca el **codo** de cada una con YOLO pose (salvo con `--sin-antebrazo`; ver [Antebrazo](#antebrazo-forearmpy)).
6. Calcula la **velocidad** de cada punto y de cada dedo con el filtro One Euro, y la pasa a cm/s con la palma (`--palma-cm` o medida) (ver [Velocidad](#velocidad-kinematicspy)).
7. Dibuja en la ventana de la cámara, para cada mano:
   - El antebrazo (debajo de la mano), los 21 landmarks coloreados **por dedo** (ver "Identificación por dedo" más abajo), con antialiasing y un trazo oscuro de contraste debajo de cada línea.
   - Las conexiones del "esqueleto" (`HandLandmarksConnections.HAND_CONNECTIONS`), también coloreadas por dedo (gris neutro para las conexiones muñeca-nudillo).
   - La etiqueta `Left`/`Right` + el id de track sobre la muñeca (p. ej. `Left #0`), con un fondo oscurecido para que se lea sobre cualquier color de piel/ropa/fondo.
   - Las flechas y los números de velocidad.
8. **Escribe en el CSV** las filas de ese frame (una por landmark, más el codo si lo hay). El archivo se crea con la primera mano y se vacía a disco cada segundo (`CsvRecorder`, desde la 28-B; antes todo se acumulaba en memoria hasta el final).
9. Dibuja la **vista 3D con dos POV** (salvo con `--sin-3d`; ver [Vista 3D](#vista-3d-con-dos-pov-viewer3dpy)), el panel de estado y, con `--estereo`, la ventana de la cámara 2; atiende las teclas `n`, `v`, `f`, `s` y las de la vista 3D (ver "Controles y panel de estado").
10. Al presionar `q` o `Esc` (o cerrar la ventana de la cámara, o `Ctrl+C`, o si la cámara deja de entregar imágenes), libera las cámaras, cierra las ventanas y cierra el CSV.

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

Como el frame se voltea (efecto espejo) antes de pasarlo a MediaPipe, la lateralidad cruda del modelo salía invertida: la mano derecha real aparecía como `Left`. Desde el **2026-09-23** `captura.py` la corrige antes del tracker, así que la vista en vivo y el CSV muestran la mano real de la persona. Para CSVs grabados antes, usar `plot_csv.py --swap-hands`.

### Estabilización de Left/Right (`HandTracker`)

MediaPipe reclasifica `handedness` de forma independiente en cada frame, así que con ciertos movimientos (mano de perfil, dorso hacia la cámara, manos cruzándose) el resultado crudo puede parpadear entre `Left`/`Right` de un frame a otro aunque sea físicamente la misma mano.

`captura.py` corrige esto con una clase `HandTracker` que:

1. **Empareja manos entre frames** por cercanía del centroide de sus 21 landmarks (no por el orden en que MediaPipe las devuelve, que tampoco es estable), asignando un `track id` persistente a cada mano física mientras siga en cámara.
2. **Vota la clasificación** sobre una ventana de los últimos 15 frames (~0.5s a 30fps), ponderada por el `score` de cada frame, y usa esa mayoría como `handedness` estable en vez del valor crudo del frame actual. Una o dos reclasificaciones puntuales quedan diluidas por el resto de la ventana.
3. **Tolera oclusiones cortas**: si una mano desaparece hasta 10 frames y reaparece cerca de donde estaba, se le reasigna el mismo `track id` (y conserva su historial de votos) en vez de tratarse como una mano nueva.

Los tres umbrales (`TRACK_MATCH_MAX_DIST`, `TRACK_MAX_AGE`, `HANDEDNESS_WINDOW`) están al principio de `captura.py` por si hace falta ajustarlos (p. ej. ventana más larga si sigue habiendo parpadeo, o `TRACK_MATCH_MAX_DIST` más chico si dos manos cercanas terminan compartiendo track).

### Formato del CSV exportado

Un archivo por ejecución, nombrado `hand_data_<YYYYMMDD_HHMMSS>.csv` con la hora de **inicio** de la sesión (desde la 28-B; antes, la de salida; si el nombre ya existe se agrega `_2`, `_3`…), escrito **mientras se graba**, con **una fila por landmark por mano por frame**:

| Columna          | Descripción                                                                 |
|------------------|------------------------------------------------------------------------------|
| `frame`          | Índice de frame de video (entero, incremental)                              |
| `timestamp_ms`   | Milisegundos transcurridos desde el inicio de la captura                    |
| `hand_id`        | Id de track persistente por mano física durante toda la sesión (ver `HandTracker` arriba) — no se resetea por frame ni se limita a 0/1 |
| `handedness`     | `"Left"` o `"Right"` **estabilizado** (voto ponderado sobre 15 frames, no el valor crudo de MediaPipe) |
| `score`          | Confianza promedio de esa clasificación estable (0–1)                       |
| `landmark_index` | 0–20: índice del landmark dentro de la mano (ver mapa de landmarks abajo)   |
| `x`, `y`         | Coordenadas normalizadas (0–1) relativas al frame; origen arriba-izquierda   |
| `z`              | Profundidad relativa a la muñeca, aproximadamente en la misma escala que `x` (fracción del ancho del frame); **positivo = más lejos de la cámara**. Con una cámara la estima MediaPipe; con `--estereo` es la **medida** (misma convención). En el codo (landmark 21) es una estimación (ver [Antebrazo](#antebrazo-forearmpy)) |
| `img_w`, `img_h` | Tamaño en píxeles del frame capturado (desde 2026-09-24). Lo usa `plot_csv.py --3d` para reconstruir la escena con la proporción correcta |
| `vx`, `vy`, `vz` | Velocidad del punto en **anchos de frame por segundo**, los tres ejes en la misma escala. `vy` positiva = hacia abajo; `vz` positiva = alejándose de la cámara (ver [Velocidad](#velocidad-kinematicspy)) |
| `rapidez_cm_s` | Módulo de la velocidad en **cm/s** (con la palma de `palma_cm`) |
| `rapidez_rel_cm_s` | Rapidez **respecto a la muñeca** (cm/s): lo que el punto se mueve dentro de la mano. En las puntas (4, 8, 12, 16, 20) es la velocidad relativa de ese dedo; en la muñeca siempre es 0 |
| `dedo` | A qué parte pertenece el punto: `Pulgar`, `Índice`, `Medio`, `Anular`, `Meñique`, `Muñeca` o `Codo`. Para filtrar por dedo sin memorizar índices |
| `fuente` | De dónde sale el punto: `mediapipe` (0–20, una cámara), `estereo` (0–20, `z` medida con dos cámaras; desde la 28-D), `yolo` o `estimado` (codo) |
| `palma_cm` | Largo de palma con el que se pasó a cm/s: `--palma-cm` (default 9.5) o, con `--estereo`, el **medido** para esa mano. `plot_csv.py --3d` lo reutiliza (desde la 28-B) |
| `x_cm`, `y_cm`, `z_cm` | Solo con `--estereo` (desde la 28-D): posición **absoluta** del punto en cm respecto a la cámara 1. `x_cm` hacia la derecha de la imagen en espejo (como se ve en la ventana), `y_cm` hacia abajo, `z_cm` = distancia a lo largo del eje de la cámara. Vacías sin `--estereo`, en manos que la cámara 2 no vio, en puntos fuera de la imagen de alguna de las dos cámaras (desde la 28-F) y en el codo |

Cada mano/frame produce 21 filas consecutivas (una por `landmark_index`, en orden 0→20) y, si se detectó su antebrazo, **una fila 22 con `landmark_index = 21` (el codo)**.

> CSVs anteriores al 2026-09-28 no tienen `palma_cm` ni `x_cm`/`y_cm`/`z_cm`: `plot_csv.py --3d` usa 9.5 cm (o `--palma-cm`).
>
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

La idea es la de los viewports divididos de Blender: **una sola cámara física**, y en el gráfico dos puntos de vista de la misma escena 3D, uno al lado del otro. Lo abre `captura.py` en vivo (salvo con `--sin-3d`) y `plot_csv.py --3d` al reproducir. Tiene fondo oscuro, piso de referencia y ejes de orientación en la esquina, como Blender.

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
| Rueda del mouse, clic derecho arrastrando, o `+` / `-` (`=` también acerca, para no usar `Shift` en teclados donde `+` lo necesita) | **Zoom** de ese POV |
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
- **Filtro One Euro** (desde la 28-C): la derivada cuadro a cuadro es ruidosa (MediaPipe tiembla un poco aunque la mano esté quieta). Cada punto pasa por un [filtro One Euro](https://gery.casiez.net/1euro/) (Casiez, Roussel y Vogel, 2012): un pasa bajos cuya frecuencia de corte **sube con la velocidad**. Con la mano quieta filtra mucho (quita el temblor); con la mano rápida filtra poco (no se atrasa). La velocidad es la derivada de la posición filtrada. Las posiciones que se dibujan y se guardan en el CSV **no** se filtran: siguen siendo las de MediaPipe.
- **Huecos:** si un punto no se vio por más de 0.25 s (mano perdida y vuelta a encontrar), su velocidad vuelve a 0 en lugar de calcular un salto gigante.

#### Por qué One Euro y no la media exponencial de antes

Antes se suavizaba con una media exponencial fija (`VELOCITY_SMOOTHING = 0.35`). Una media fija obliga a elegir: suavizar mucho (la velocidad se atrasa) o poco (la velocidad tiembla con la mano quieta). One Euro ajusta el suavizado solo. Comparación con datos simulados (30 FPS con variación, temblor de ~0.8 px en `x`/`y` y más en `z`, promedio de 4 corridas):

| Situación | Media exponencial (antes) | One Euro (ahora) |
|-----------|---------------------------|------------------|
| Mano quieta: rapidez de ruido (media / p95) | 2.3 / 4.6 cm/s | **0.8 / 1.9 cm/s** |
| Arranca a 40 cm/s: tiempo hasta el 90 % | ~190 ms | **~95 ms** |
| Frena: tiempo hasta volver a ~0 | ~150 ms | **~80 ms** |
| Golpeteo de un dedo (4 Hz, 1.5 cm): pico medido | 49 % del real | 49 % del real |
| Movimiento constante: oscilación de la rapidez | **0.9 cm/s** | 2.0 cm/s |

Es decir: la mitad de temblor y la mitad de retraso, a cambio de un poco más de oscilación mientras la mano se mueve parejo. Con la mano quieta la rapidez de ruido queda por debajo del umbral de 4 cm/s de las flechas, así que ya casi no aparecen flechas "fantasma". Parámetros en `kinematics.py` (`EURO_MIN_CUTOFF = 0.5`, `EURO_BETA = 10`, `EURO_D_CUTOFF = 2`), elegidos probando 72 combinaciones con esas mismas simulaciones. Se repite con `./venv/bin/python3 pruebas/filtro_velocidad.py` (y `--buscar` para las 72 combinaciones).
Unidades:

| Magnitud | Unidad |
|----------|--------|
| `vx`, `vy`, `vz` | Anchos de frame por segundo (`vy` + = hacia abajo, `vz` + = alejándose de la cámara) |
| Rapidez en cm/s | Se convierte con el largo de la palma (muñeca → nudillo del medio) como regla: 9.5 cm por defecto (`PALM_LENGTH_CM`), el de `--palma-cm` (desde la 28-B) o, con `--estereo`, el **medido** (desde la 28-D). Con una cámara y la palma supuesta es **aproximada** (sirve para comparar movimientos); con tu palma medida o con dos cámaras es bastante más fiel |

#### La palma como regla (`--palma-cm`)

Con una sola cámara no se sabe el tamaño real de nada: una mano grande lejos se ve igual que una chica cerca. Para pasar a cm se usa la palma: si en la imagen mide `p` unidades y en la realidad `palma_cm`, cada unidad son `palma_cm / p` cm. Por eso el error de la palma pasa **entero** a todas las velocidades: con 9.5 cm supuestos y una palma real de 8.5 cm, todo sale ~12 % más rápido. En la prueba simulada (mano de 8.5 cm a 20 cm/s, `pruebas/captura_simulada.py`): ~22–23 cm/s con el default, **~20 cm/s con `--palma-cm 8.5`** y con `--estereo` (los decimales varían un poco entre corridas porque la prueba usa tiempos reales).

Cómo medirla: con la mano abierta y estirada, desde el pliegue de la muñeca (el más cercano a la palma) hasta el nudillo del dedo medio, donde el dedo se une a la palma, por el lado de la palma. Se aceptan valores entre 5 y 15 cm.

Dónde se ve:

- **Ventana de la cámara:** flechas amarillas en muñeca, puntas de los dedos y codo (solo la parte paralela a la imagen, `vx`/`vy`), y la rapidez de la muñeca de cada mano en el panel de estado.
- **Vista 3D:** las mismas flechas pero en 3D (incluyen `vz`: al girar la vista se ve si el punto se acerca o se aleja de la cámara), y la rapidez de la muñeca junto a cada mano.
- **CSV:** columnas `vx`, `vy`, `vz`, `rapidez_cm_s` y `rapidez_rel_cm_s` para cada punto (ver [Velocidad de cada dedo](#velocidad-de-cada-dedo)).

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

## Dos cámaras (`estereo.py`)

Desde la versión **28-D**. Con una sola cámara la `z` es una profundidad **relativa** que MediaPipe *adivina* por la forma de la mano, y el tamaño real sale de suponer la palma. Con dos cámaras que ven la mano desde lugares distintos se puede **triangular**: la calibración dice dónde está cada cámara y hacia dónde mira, cada cámara dice en qué dirección ve cada punto, y el punto está donde se cruzan las dos rectas. Así se obtiene la **posición 3D real en cm** de los 21 puntos, sin suponer nada.

### Qué hace falta

- Dos webcams (p. ej. la de la Mac y una USB, o dos USB) **fijas**, separadas **10–30 cm**, mirando a la misma zona. Más separación da más precisión en profundidad pero menos zona que ven las dos. Si una cámara se mueve, hay que volver a calibrar.
- Un **tablero de ajedrez** impreso y pegado sobre algo rígido y plano (cartón, una carpeta dura).
- Las dos a la **misma resolución** (la de `--cam-width`/`--cam-height`, 1280×720 por defecto).

### 1. Tablero

```bash
./venv/bin/python3 estereo.py tablero            # calibracion/tablero_9x6.png (10x7 cuadros)
./venv/bin/python3 estereo.py tablero --tablero 7x5 --cuadro-px 150
```

Imprimirlo **al 100 %** (sin "ajustar a la página") y medir con una regla el lado de un cuadro impreso, en mm. `--tablero` es el número de esquinas **internas** (un tablero de 10×7 cuadros tiene 9×6).

### 2. Calibrar

```bash
./venv/bin/python3 estereo.py calibrar --cuadro-mm 25
./venv/bin/python3 estereo.py calibrar --cuadro-mm 25 --cam1 0 --cam2 2   # otras cámaras
```

Se abre una ventana con las dos cámaras lado a lado. Cuando el tablero se ve **entero en las dos** (`cam1 OK  cam2 OK`, con las esquinas dibujadas en colores), presiona **`espacio`** para guardar ese par. Repite en **15–20 posiciones distintas**: cerca y lejos, inclinado hacia los lados y hacia adelante/atrás, en las esquinas de la imagen. Después presiona **`c`** (mínimo 10 pares). `q`/`Esc` cancela.

En la terminal sale el resultado:

```
Calibración guardada en calibracion/estereo.npz (2026-09-28 12:00).
  Error RMS cámara 1: 0.28 px, cámara 2: 0.28 px, par estéreo: 0.28 px
  Distancia entre cámaras: 18.0 cm
```

El **error RMS** es cuánto se equivoca la calibración al volver a proyectar las esquinas del tablero, en píxeles: menos de 0.5 px es muy bueno, hasta 1 px aceptable; si pasa de 1 px avisa, y conviene repetir con más pares, el tablero bien plano y posiciones más variadas. La **distancia entre cámaras** tiene que coincidir con la que mides con una regla: es la mejor forma de saber que `--cuadro-mm` está bien.

Cómo calcula: primero calibra **cada cámara por separado** (foco, centro de la imagen y distorsión del lente, `cv2.calibrateCamera`) y después **solo la posición de una respecto a la otra** (`cv2.stereoCalibrate` con los lentes ya fijos): cada paso tiene menos incógnitas y es más estable.

### 3. Capturar

```bash
./venv/bin/python3 captura.py --estereo
```

Se abren la ventana de siempre (cámara 1, la principal) y **`HandMotion3D - Camara 2`** (la otra, a la mitad de tamaño, con las manos que ve como puntos blancos). En el panel de estado:

```
Estereo: 1/1 manos (cam2 ve 1)
  Right #0: a 45 cm, palma 8.5 cm, error 1.3 px
```

Qué cambia con `--estereo`:

| | Una cámara | Dos cámaras (`--estereo`) |
|---|------------|---------------------------|
| `z` de los 21 puntos | La estima MediaPipe (relativa a la muñeca) | **Medida** por triangulación, pasada a la misma convención (relativa a la muñeca, en anchos de frame), así el visor 3D, la velocidad y el CSV funcionan igual |
| Palma (regla de los cm/s) | 9.5 cm o `--palma-cm` | **Medida** para cada mano, suavizada en el tiempo |
| Distancia de la mano a la cámara | No se sabe | En el panel y en `z_cm` del CSV |
| Columnas `x_cm`, `y_cm`, `z_cm` | Vacías | Posición absoluta en cm respecto a la cámara 1 |
| `fuente` de los puntos 0–20 | `mediapipe` | `estereo` |

**Cómo se empareja cada mano** de la cámara 1 con la de la cámara 2: se triangulan los 21 puntos con cada combinación posible y se mide el **error de reproyección** (cuánto se equivoca el punto 3D al volver a proyectarlo en cada cámara). La combinación correcta da pocos píxeles; una equivocada, cientos. Se acepta si el error medio es menor que el 1.5 % del ancho del frame (`MAX_REPROJ_FRAC`, ~19 px a 1280). Un error de algunos píxeles es normal: MediaPipe no marca exactamente el mismo punto de la piel desde dos ángulos.

**Si la cámara 2 pierde la mano** (tapada, fuera de cuadro), esa mano sigue con la `z` de MediaPipe (`fuente = mediapipe`) pero **conserva la última palma medida** para los cm/s, para que la escala no salte y no aparezcan picos falsos de velocidad.

**La imagen de la cámara 1 se voltea en espejo** antes de MediaPipe, como siempre; para triangular se "desvoltea" (`u = (1 − x) · ancho`). La cámara 2 no se voltea para procesarla (su ventana se muestra en espejo solo para mirarla).

**Dedos fuera del cuadro** (desde la 28-F): MediaPipe devuelve puntos algo **fuera de la imagen** cuando un dedo se sale del cuadro (los extrapola). Esos puntos no se triangulan: fuera de la imagen el modelo de distorsión del lente de la calibración no vale y el punto se correría varios cm (en las pruebas, hasta 6.45 cm) aunque el error de reproyección se vea bajo. Solo se triangulan los puntos que están **dentro de las dos imágenes**; los demás conservan la `z` de MediaPipe y quedan con `x_cm`/`y_cm`/`z_cm` vacías. Hace falta ver la muñeca y al menos 8 puntos en las dos cámaras (`MIN_VISIBLE_POINTS`); la palma solo se mide si además se ve el nudillo del medio. Ver [REVISION.md](REVISION.md#revisión-3--al-pasar-las-comprobaciones-al-repositorio-versión-28-f).

### Qué tan preciso es (pruebas simuladas)

No se pudo probar con dos webcams reales. Se probó con un par de cámaras **simulado** (lentes con distorsión, cámaras separadas 18 cm y giradas 12°, tableros y manos proyectados con 0.2–1 px de ruido). Todo se repite con `./venv/bin/python3 pruebas/estereo_simulado.py` y `pruebas/captura_simulada.py` (ver [Pruebas](#pruebas)):

| Prueba | Resultado |
|--------|-----------|
| Calibración con 18 pares | Distancia entre cámaras 18.04 cm (real 18.03), RMS 0.28 px |
| Mano a 45 cm, palma de 9.0 cm, entera en las dos imágenes | Palma medida 9.01 cm, distancia 44.9 cm, error de posición máx. 0.45 cm |
| Mano a 60 cm, palma de 8.0 cm | Palma 8.04 cm, distancia 59.9 cm, error máx. 0.75 cm |
| Mano con 5 de 21 puntos fuera de la imagen de la cámara 2 | Esos puntos sin cm; los otros 15 con error máx. 0.27 cm; palma 9.04 |
| Mano con puntos lejos de la imagen | Triangulando todo daba 2.6–6.5 cm de error; ahora esos puntos no se triangulan |
| Dos manos, la cámara 2 las entrega en otro orden | Emparejadas bien |
| Captura completa (`captura.py --estereo` con cámaras y MediaPipe simulados, YOLO y visor 3D reales), mano de 8.5 cm a 20 cm/s | Palma 8.49–8.53 cm, **20.1 cm/s**, distancia 45.0 cm |
| La cámara 2 ve la mano de a ratos | Rapidez mediana ~20.2–20.6 cm/s, p95 < 25: sin picos por cambio de escala |

> Los números de la 28-D eran algo distintos (palma 9.12 cm, error 0.9 cm): la mano de aquella prueba quedaba en parte fuera de la imagen de la cámara 2 sin que se notara. Se corrigió en la 28-F (ver [REVISION.md](REVISION.md#revisión-3--al-pasar-las-comprobaciones-al-repositorio-versión-28-f)).

Con cámaras reales el error será mayor: las webcams no están sincronizadas (se toman los frames lo más juntos posible, pero con movimientos muy rápidos puede haber unos ms de diferencia) y MediaPipe tiembla más que la simulación.

### Limitaciones

- **El codo** sigue saliendo de YOLO en la cámara 1 con `z` estimada (ver [Antebrazo](#antebrazo-forearmpy)), aunque ahora a partir de una palma con `z` medida. Triangular también el codo (YOLO en las dos cámaras) queda como mejora futura.
- Las dos cámaras deben usar la **misma resolución** que en la calibración; si no, `captura.py` avisa y no arranca.
- MediaPipe corre dos veces por frame: los FPS bajan (etapa `estereo` en el panel).
- La calibración (`calibracion/estereo.npz`) es de **tus** cámaras y de dónde están puestas: no va en git.

## `plot_csv.py` — graficar los puntos del CSV

Reconstruye, a partir de un CSV ya guardado, exactamente los mismos puntos y conexiones que se dibujan en vivo en `captura.py` (reutiliza la misma constante `HAND_CONNECTIONS` de MediaPipe), pero con `matplotlib` en vez de la ventana de la cámara.

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

# Otra palma para los cm/s en --3d (por defecto, la guardada en el CSV)
./venv/bin/python3 plot_csv.py --3d --palma-cm 8.5
```

Detalles de la visualización:

- Color por dedo (ver tabla en "Identificación por dedo" más arriba), consistente con la vista en vivo de `captura.py` porque ambas usan la misma paleta en `hand_style.py` — consistente cuadro a cuadro, no se reasigna.
- Lateralidad por estilo de línea: **punteado** para `Left`, **sólido** para `Right` (el color ya no codifica lateralidad, ver arriba).
- Las puntas de dedo (4/8/12/16/20) se dibujan más grandes y con el nombre del dedo (`Pulgar`, `Índice`, `Medio`, `Anular`, `Meñique`); el resto de los puntos va sin etiqueta.
- Cada mano lleva además la etiqueta `{Left|Right} #{hand_id}` junto a la muñeca. Con más de 2 manos en el CSV (varias personas, ver `--max-hands` en `captura.py`) puede haber varias manos del mismo lado; el `hand_id` es lo que las distingue entre sí, igual que en la vista en vivo.
- La leyenda combina ambas claves: color por dedo y estilo de línea por lateralidad.
- El eje Y se invierte porque las coordenadas de MediaPipe crecen hacia abajo (igual que en una imagen), así la orientación coincide con lo que se ve en la cámara.
- Sin `--3d` grafica solo el plano `x`/`y` con matplotlib; con `--3d` usa también `z` en el mismo visor de dos POV de la captura en vivo (ver [Vista 3D con dos POV](#vista-3d-con-dos-pov-viewer3dpy)), con flechas de velocidad. La velocidad se recalcula al leer (desde `x`, `y`, `z` y `timestamp_ms`, con el mismo filtro One Euro que en vivo), así funciona también con CSVs viejos. Para los cm/s usa la palma con la que se grabó cada mano (columna `palma_cm`, desde la 28-B), la de `--palma-cm` si se indica, o 9.5 cm en CSVs anteriores. Con CSVs grabados con `--estereo` la `z` guardada ya es la medida, así que el 3D reproduce la profundidad real.
- Teclas en la reproducción 3D: `espacio` pausa/sigue, `a`/`d` frame anterior/siguiente, `v` velocidad, `f` velocidad de dedos absoluta/relativa, `q`/`Esc` salir, más todas las del visor (`1`, `3`, `7`, `9`, `.`, `l`, `r`, `+`, `-`, mouse). Los POV son independientes igual que en la captura en vivo.
- Si el CSV tiene codo (landmark 21), el antebrazo se dibuja en azul en ambos modos.
- Sin cámara ni modelo `.task` de por medio: solo lee el CSV, así que corre incluso sin permisos de cámara.

## Pausa

Con `captura.py` en marcha, **`espacio`** o **`p`** (en cualquiera de las dos ventanas) pausa la captura; la misma tecla la reanuda.

| Mientras está en pausa | |
|------------------------|--|
| Imagen | Se queda el último fotograma con el aviso **PAUSA** (la cámara no se lee) |
| CSV | **No se graba nada**: los frames quedan seguidos (`frame` no salta) |
| Unreal Engine | **No se manda nada** (el modelo se queda en la última pose) |
| Vista 3D | Sigue viva: se puede girar, mover y hacer zoom |
| Teclas que siguen | `s` (foto sin panel), `e` / `m` (Excel), `u`, las del visor 3D y `q` / `Esc` |

Al reanudar se descartan unos fotogramas que la cámara acumuló, para que la imagen no vaya atrasada. Como el tiempo del CSV es el real, la pausa deja un **hueco en `timestamp_ms`**; la velocidad se reinicia en 0 al volver (hueco mayor que 0.25 s, ver [Velocidad](#velocidad-kinematicspy)) en lugar de inventar un salto.

En **`plot_csv.py`**: `espacio` pausa y sigue la animación 2D (en 3D ya existía, y desde la 19-A `p` también). En 2D no se usa `p` porque matplotlib ya la usa para el paneo.

## Exportar a Excel (`exportar_excel.py`)

Genera un `.xlsx` de una captura **cuando se pide**, listo para escribir un artículo. Hay dos formatos, porque en ingeniería y en medicina las ecuaciones y los resultados se presentan de forma distinta:

| | **Ingeniería** (`ingenieria`, estilo IEEE) | **Medicina** (`medicina`, estilo revista médica) |
|---|---|---|
| Unidades | **SI**: m/s | **cm/s** |
| Ecuaciones | Hoja **Ecuaciones**: 12 ecuaciones numeradas, en texto y en **LaTeX** (velocidad, escala, filtro One Euro, media, RMS, σ, pico, muestreo, triangulación estéreo) | No hay ecuaciones físicas: hoja **Notas estadísticas** con las definiciones estadísticas y cómo reportarlas |
| Resultados | **Tabla II**: N, media, **RMS**, **σ** y **pico** por serie | **Tabla 2**: n, **media (DE)**, **mediana [Q1-Q3]** y **mín-máx** por serie, más las mismas cifras en número |
| Descripción de la medición | Hoja **Parámetros** (N, T, f_s, resolución, largo de palma, profundidad) con símbolos y unidades | Hoja **Métodos** (borrador) y **Tabla 1** de características |
| Campos por completar | Los que no están en el CSV | Más: ética y consentimiento, participante, edad, sexo, instrumento, tarea (celdas amarillas `[completar]`) |
| Estilo | Times New Roman, tablas de tres líneas, pies en cursiva | Arial, tablas de tres líneas, «Tabla N.» en negrita |

Los dos traen además la hoja **Limitaciones** (visión monocular sin validar contra una referencia, escala por la palma, filtro que atenúa picos, fotogramas sin mano, ids de mano) y la hoja **Datos**.

**Cómo está armado:** la hoja *Datos* tiene una fila por fotograma y una columna por serie (por defecto: muñeca, las 5 puntas absolutas y relativas a la muñeca, y el codo; con `--todos-los-puntos`, los 22 puntos). Los resultados son **fórmulas de Excel** sobre esas columnas (`AVERAGE`, `STDEV`, `MEDIAN`, `QUARTILE`...): cualquier número se puede rastrear a sus datos, y si borras filas de *Datos* (un tramo mal detectado) los resultados se recalculan solos. Solo usa funciones clásicas, para que abra igual en Excel, LibreOffice y Google Sheets, y los textos «media (DE)» se arman con `FIXED`, que respeta el separador decimal de tu idioma.

```bash
./venv/bin/python3 exportar_excel.py --formato ingenieria                       # el último CSV de capturas/
./venv/bin/python3 exportar_excel.py capturas/hand_data_X.csv --formato medicina
./venv/bin/python3 exportar_excel.py --formato medicina --todos-los-puntos --salida resultados.xlsx
```

Durante la captura: **`e`** (ingeniería) o **`m`** (medicina) generan el Excel de lo grabado **hasta ese momento**, sin parar la captura, junto al CSV (`hand_data_<inicio>_ingenieria.xlsx`). El aviso sale en el panel y en la terminal. Un error al exportar nunca interrumpe la captura. Necesita `openpyxl` (`requirements.txt`, solo se carga al exportar).

**Qué hay que saber antes de publicar:**

- Los formatos son un **punto de partida**: revisa las normas de tu revista o congreso (IEEE, Vancouver, AMA...). Los textos de las hojas están en español.
- **Los fotogramas consecutivos no son observaciones independientes.** Por eso la versión de medicina **no calcula intervalos de confianza ni valores p entre fotogramas**: saldrían demasiado optimistas. Para comparar personas o condiciones, resume cada participante en un valor (p. ej. su mediana) y analiza esos valores.
- La rapidez se estima con visión por computadora y **no está validada contra una referencia** (captura de movimiento, goniómetro, sensores inerciales). Para una medida clínica o de ingeniería, valídala antes (en medicina, lo habitual es Bland-Altman e ICC).
- Los cm/s dependen del largo de palma que indiques (`--palma-cm`) o midas con dos cámaras.
- Excel calcula las fórmulas **al abrir** el archivo (los visores de vista previa pueden mostrarlas vacías).

## Unreal Engine (`unreal_bridge.py`)

Conecta el movimiento de tus manos con un **modelo 3D en Unreal Engine 5**. `captura.py --unreal` manda por **OSC sobre UDP**, en cada fotograma y por cada mano: la **posición de los 21 puntos en cm** (relativos a la muñeca, en los ejes de Unreal), la posición de la muñeca, el codo y la **flexión en grados de 15 articulaciones** (0° = dedo estirado). Unreal lo recibe con su plugin **OSC** (viene incluido, sin instalar nada) en un Blueprint.

```bash
./venv/bin/python3 captura.py --unreal                       # a 127.0.0.1:8000
./venv/bin/python3 captura.py --unreal 192.168.1.20:8000     # a Unreal en otra computadora
./venv/bin/python3 unreal_bridge.py --demo 127.0.0.1:8000    # mano sintética, sin cámara (para armar el Blueprint)
./venv/bin/python3 unreal_bridge.py --escuchar 8000          # ver lo que llega, sin Unreal
```

**Todo el detalle (formato de los 87 valores, ejes, plugin, Blueprint, mapeo a los huesos del Mannequin y límites) está en [`UNREAL.md`](UNREAL.md).** Dos avisos honestos: *(1)* el lado de Python está probado sin Unreal (`pruebas/unreal_simulado.py`), pero **lo que ocurre dentro de Unreal no se probó**; *(2)* con una cámara la profundidad es aproximada (con `--estereo`, la de la muñeca es real) y **la orientación de la muñeca no se manda** (se calcula en Unreal con los puntos 0, 5 y 17).

## Pruebas

Desde la versión **28-F** el repositorio trae pruebas que se corren **sin cámara ni pantalla**: reemplazan las webcams, las ventanas y el detector de MediaPipe por simulaciones de resultado conocido, y comparan lo que mide el programa con ese resultado. Todos los números de precisión de este README salen de ellas.

```bash
./venv/bin/python3 pruebas/correr_todo.py      # las cinco, con resumen (~1 min)
```

| Prueba | Qué comprueba |
|--------|---------------|
| `pruebas/filtro_velocidad.py` | One Euro contra la media exponencial de antes: menos ruido quieto, menos retraso, mismos golpeteos |
| `pruebas/estereo_simulado.py` | Calibración, triangulación, emparejamiento de manos, dedos fuera de cuadro, casos borde |
| `pruebas/captura_simulada.py` | `captura.py` de punta a punta (**pausa, Excel (`e`/`m`) y envío a Unreal (19-A)**, una cámara, `--palma-cm`, `--estereo`, CSV durante la sesión, `Ctrl+C`, sin manos, nombres de CSV) y `plot_csv.py` con ese CSV |
| `pruebas/excel_simulado.py` | `exportar_excel.py` (19-A): hojas de cada formato, series, y las **fórmulas recalculadas con LibreOffice** contra numpy (media, RMS, σ, pico, «media (DE)», «mediana [Q1-Q3]»); CSV viejo, fila cortada, formato desconocido |
| `pruebas/unreal_simulado.py` | `unreal_bridge.py` (19-A): codificador OSC (ida y vuelta), cambio de ejes a Unreal, ángulos de flexión, envío por UDP, destino `host:puerto` |

Lo que **no** cubren: las cámaras reales (temblor, luz, sincronización), lo que se ve en las ventanas, YOLO sobre personas reales, **Unreal Engine** recibiendo los mensajes y el Excel abierto en **Excel de escritorio** (las fórmulas se comprueban con LibreOffice). Detalle en [`pruebas/README.md`](pruebas/README.md).

## Cambios: comandos, partes quitadas y por qué

Resumen de todo lo que cambió en el proyecto: los comandos de ahora, los de antes, lo que se quitó o reemplazó en el código y por qué. El detalle fechado de cada error y corrección está en [`CHANGELOG.md`](CHANGELOG.md).

Las versiones se nombran por día y letra. El 2026-09-24 hubo cinco (24-A a 24-E), el 2026-09-28 seis (28-A a 28-F) y el 2026-10-19 una (19-A). Todos los comandos en un solo lugar: [`COMANDOS.md`](COMANDOS.md).

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
| **19-A** | **Pausa** (`espacio`/`p`), **Excel para artículos** de ingeniería y de medicina (`exportar_excel.py`, teclas `e`/`m`), **conexión con Unreal Engine** (`unreal_bridge.py`, `--unreal`, [`UNREAL.md`](UNREAL.md)); `openpyxl` en `requirements.txt` |

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
| `--unreal [HOST:PUERTO]` | apagado (sin valor: `127.0.0.1:8000`) | Manda la pose de las manos a Unreal Engine por OSC/UDP (ver [`UNREAL.md`](UNREAL.md)) | 19-A |

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

`exportar_excel.py` (Excel para artículos, desde la 19-A):

| Comando / flag | Default | Qué hace |
|----------------|---------|----------|
| `./venv/bin/python3 exportar_excel.py --formato ingenieria` | (obligatorio) | Excel estilo IEEE (SI, ecuaciones, RMS) del último CSV |
| `--formato medicina` | (obligatorio) | Excel de revista médica (media (DE), mediana [Q1-Q3], Métodos, Tabla 1/2) |
| `exportar_excel.py capturas/archivo.csv ...` | el último CSV | Un CSV específico |
| `--salida ARCHIVO.xlsx` | junto al CSV, con el formato en el nombre | Dónde guardarlo |
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
| Captura (cualquiera de las dos ventanas) | `q`/`Esc` salir y guardar · `n` nombres · `v` velocidad · `f` dedos absoluta/relativa · `s` foto · `espacio`/`p` **pausa** · `e`/`m` **Excel** (ingeniería/medicina) · `u` pausar el envío a Unreal |
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
| Velocidad suavizada con media exponencial (`VELOCITY_SMOOTHING = 0.35`) | Filtro **One Euro** | 28-C | Mitad de temblor con la mano quieta y mitad de retraso al arrancar y frenar (ver [Velocidad](#por-qué-one-euro-y-no-la-media-exponencial-de-antes)) |
| Siempre la cámara `0` | `--cam N` | 28-D | Elegir la cámara (hace falta con dos) |
| Solo una cámara | `--estereo` con `estereo.py` | 28-D | Medir la profundidad y la palma en vez de estimarlas |
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

## Flujo típico

```bash
./venv/bin/python3 captura.py --palma-cm 8.5   # capturar (CSV nuevo en capturas/, con tu palma)
./venv/bin/python3 plot_csv.py                 # revisar esa captura en 2D
./venv/bin/python3 plot_csv.py --3d            # o en 3D con los dos POV
```

Para un artículo (el Excel sale junto al CSV; también con `e` / `m` durante la captura):

```bash
./venv/bin/python3 exportar_excel.py --formato ingenieria    # o medicina
```

Con Unreal Engine (ver [`UNREAL.md`](UNREAL.md)):

```bash
./venv/bin/python3 captura.py --palma-cm 8.5 --unreal
```

Con dos cámaras (calibradas una vez con `estereo.py calibrar`):

```bash
./venv/bin/python3 captura.py --estereo
./venv/bin/python3 plot_csv.py --3d
```

## Historial de cambios

Todo error corregido, cambio y mejora se documenta con fecha en [`CHANGELOG.md`](CHANGELOG.md); las revisiones, en [`REVISION.md`](REVISION.md); los comandos ejecutados sobre el repositorio, en la [bitácora de `COMANDOS.md`](COMANDOS.md#3-bitácora-de-mantenimiento).

Última entrada: **2026-10-19**, versión **19-A** (pausa, Excel para artículos y conexión con Unreal Engine); antes, **2026-09-28**, versiones **28-A** (`captura.py`, versiones fijas), **28-B** (CSV mientras se graba, `--palma-cm`), **28-C** (filtro One Euro), **28-D** (dos cámaras), **28-E** (correcciones de la revisión completa) y **28-F** (pruebas, registro de comandos y de revisiones, puntos fuera de cuadro en estéreo, historial sin `Co-Authored-By`), más la revisión de la documentación de ese mismo día. Antes, el **2026-09-24**: eje z en 3D, visor de dos POV, antebrazo con YOLO pose y velocidad (24-A/24-B), POV independientes (24-C), velocidad de cada dedo (24-D) y el cambio de nombre a HandMotion3D (24-E).

> **Hashes de commits:** el 2026-09-28 se reescribió el historial para quitar una línea `Co-Authored-By` de los mensajes, así que los commits anteriores tienen hashes nuevos (el contenido es el mismo). La tabla de correspondencia está en [`COMANDOS.md`](COMANDOS.md#2026-09-28--versión-28-f-quitar-la-línea-co-authored-by-del-historial).
