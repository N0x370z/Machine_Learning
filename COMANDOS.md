# Registro de comandos — HandMotion3D

Todos los comandos del proyecto en un solo lugar, en tres partes:

1. **[Referencia](#1-referencia-comandos-actuales)**: cada comando y flag que existe hoy, con su default y desde qué versión.
2. **[Comandos que cambiaron o se quitaron](#2-comandos-que-cambiaron-o-se-quitaron)**: el de antes, el de ahora y por qué.
3. **[Bitácora de mantenimiento](#3-bitácora-de-mantenimiento)**: los comandos de git, pip y verificación que se ejecutaron sobre el repositorio, con fecha, para saber qué se hizo y cómo deshacerlo.

Todos se corren desde la **raíz del repositorio** (donde está este archivo) y con el Python del venv (`./venv/bin/python3`). Las versiones se nombran día-letra (24-A…24-E del 2026-09-24, 28-A…28-F del 2026-09-28, 19-A del 2026-10-19); el detalle de cada una está en [`CHANGELOG.md`](CHANGELOG.md) y la explicación de cada función en el [`README.md`](README.md).

---

## 1. Referencia: comandos actuales

### Preparar el entorno (una vez)

```bash
python3 -m venv venv
./venv/bin/python3 -m pip install -r requirements.txt     # versiones fijas (28-A)

mkdir -p models
curl -L -o models/hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

| Comando | Para qué |
|---------|----------|
| `./venv/bin/python3 -m pip install -r requirements.txt` | Instala las dependencias en las versiones probadas. Se usa `python3 -m pip` y no `./venv/bin/pip` porque este último se rompe si la carpeta se mueve (24-E) |
| `./venv/bin/python3 -m pip install --dry-run -r requirements.txt` | Comprueba si el venv ya tiene exactamente las versiones fijadas (no instala nada) |
| `./venv/bin/python3 -m pip install --force-reinstall opencv-python==5.0.0.93 opencv-contrib-python==5.0.0.93` | Repara `cv2` si las dos variantes de OpenCV quedaron en versiones distintas (28-A) |

El modelo de YOLO (`models/yolo11s-pose.pt`) se descarga solo la primera vez que se usa el antebrazo.

### `captura.py` — captura en vivo

```bash
./venv/bin/python3 captura.py                    # una cámara, todo activado
./venv/bin/python3 captura.py --palma-cm 8.5     # con el largo de TU palma (recomendado)
./venv/bin/python3 captura.py --estereo          # dos cámaras (calibrar antes)
./venv/bin/python3 captura.py --unreal           # además, manda la pose a Unreal Engine
```

| Flag | Default | Qué hace | Desde |
|------|---------|----------|-------|
| `--max-hands N` | `4` | Máximo de manos a la vez | Inicial |
| `--min-detection-confidence X` | `0.5` | Confianza para detectar una mano nueva (bajarla si cuesta que te reconozca) | 2026-09-23 |
| `--min-presence-confidence X` | `0.5` | Confianza para seguir considerando presente una mano | 2026-09-23 |
| `--min-tracking-confidence X` | `0.5` | Confianza del tracking entre frames (bajarla si la mano se pierde con movimiento rápido) | 2026-09-23 |
| `--cam-width W` / `--cam-height H` | `1280` / `720` | Resolución pedida a la cámara (si no la soporta, se ignora) | 2026-09-23 |
| `--sin-antebrazo` | apagado | No carga YOLO; el esqueleto llega hasta la muñeca | 24-A |
| `--sin-3d` | apagado | No abre la vista 3D de dos POV | 24-A |
| `--yolo-modelo {n,s,m}` | `s` | Modelo YOLO pose: `n` rápido (~6 ms), `s` equilibrado (~9 ms), `m` preciso (~17 ms) | 24-B |
| `--antebrazo-solo-yolo` | apagado | No dibuja antebrazos estimados (solo cuando YOLO ve el codo) | 24-B |
| `--palma-cm CM` | `9.5` | Largo de tu palma (pliegue de la muñeca → nudillo del medio), escala de los cm/s. Acepta 5–15 | 28-B |
| `--cam N` | `0` | Índice de la cámara (la cámara 1 con `--estereo`) | 28-D |
| `--estereo` | apagado | Dos cámaras: profundidad y palma medidas | 28-D |
| `--cam2 N` | `1` | Índice de la segunda cámara (solo con `--estereo`) | 28-D |
| `--calibracion ARCHIVO` | `calibracion/estereo.npz` | Calibración estéreo a usar (solo con `--estereo`) | 28-D |
| `--unreal [HOST:PUERTO]` | apagado (sin valor: `127.0.0.1:8000`) | Manda la pose de las manos a Unreal Engine por OSC/UDP ([`UNREAL.md`](UNREAL.md)) | 19-A |
| `--video ARCHIVO` | apagado (cámara) | Analiza un video grabado; el tiempo sale del video. No se combina con `--estereo` | 17-C |
| `--video-espejado` | apagado | Con `--video`: el video ya está en espejo (no se voltea) | 17-C |
| `--participante CODIGO` | vacío | Código del participante (nunca el nombre): va al `.json` de la sesión y al CSV de medicina | 17-D |
| `--notas TEXTO` | vacío | Nota libre para el `.json` de la sesión | 17-D |

Ejemplos útiles:

```bash
./venv/bin/python3 captura.py --min-detection-confidence 0.3 --min-tracking-confidence 0.3  # poca luz
./venv/bin/python3 captura.py --max-hands 2 --cam-width 960 --cam-height 540                # más FPS
./venv/bin/python3 captura.py --yolo-modelo m                                               # codo más preciso
./venv/bin/python3 captura.py --sin-antebrazo --sin-3d                                      # lo más liviano
./venv/bin/python3 captura.py --estereo --cam 0 --cam2 2 --calibracion calibracion/otra.npz
./venv/bin/python3 captura.py --help                                                        # todos los flags
```

### `plot_csv.py` — reproducir un CSV

```bash
./venv/bin/python3 plot_csv.py                     # anima en 2D el último CSV de capturas/
./venv/bin/python3 plot_csv.py --3d                # en 3D con los dos POV
```

| Comando / flag | Qué hace | Desde |
|----------------|----------|-------|
| `plot_csv.py capturas/archivo.csv` | Usa un CSV específico (sin él, el más reciente) | Inicial |
| `--frame N` | Un solo frame (en 2D estático; en 3D arranca en pausa ahí) | Inicial (3D: 24-B) |
| `--interval MS` | ms entre frames de la animación (default `33`) | Inicial |
| `--swap-hands` | Invierte Left/Right (CSVs de antes del 2026-09-23) | 2026-09-23 |
| `--3d` | Reproduce en la vista 3D de dos POV | 24-A (visor OpenCV: 24-B) |
| `--palma-cm CM` | Palma para los cm/s en `--3d` (default: la guardada en el CSV, o 9.5) | 28-B |

### `estereo.py` — dos cámaras

```bash
./venv/bin/python3 estereo.py tablero                     # 1. tablero para imprimir
./venv/bin/python3 estereo.py calibrar --cuadro-mm 25     # 2. calibrar (mide el cuadro impreso)
./venv/bin/python3 captura.py --estereo                   # 3. capturar
```

| Comando / flag | Default | Qué hace |
|----------------|---------|----------|
| `estereo.py tablero` | — | Genera `calibracion/tablero_<COL>x<FIL>.png` |
| `tablero --tablero COLxFIL` | `9x6` | Esquinas **internas** (un tablero de 10×7 cuadros tiene 9×6) |
| `tablero --cuadro-px N` | `120` | Lado de cada cuadro en el PNG |
| `estereo.py calibrar --cuadro-mm MM` | (obligatorio) | Calibra las dos cámaras; `MM` = lado de un cuadro **impreso**, medido con regla |
| `calibrar --tablero COLxFIL` | `9x6` | Esquinas internas del tablero |
| `calibrar --cam1 N` / `--cam2 N` | `0` / `1` | Índices de las cámaras |
| `calibrar --cam-width W` / `--cam-height H` | `1280` / `720` | Resolución (la misma que se usará en `captura.py`) |
| `calibrar --salida ARCHIVO` | `calibracion/estereo.npz` | Dónde guardar la calibración |

### `exportar_csv.py` — dos CSV para artículos (17-B; reemplaza a `exportar_excel.py`)

```bash
./venv/bin/python3 exportar_csv.py                                        # los dos, del último CSV de capturas/
./venv/bin/python3 exportar_csv.py capturas/hand_data_X.csv --participante P01
./venv/bin/python3 exportar_csv.py --formato medicina --todos-los-puntos --salida resultados/
```

| Flag | Default | Qué hace |
|------|---------|----------|
| `csv_path` | el último de `capturas/` | CSV de la captura |
| `--formato {ingenieria,medicina,ambos}` | `ambos` | Ingeniería: SI (m/s), N, T, f_s, media, RMS, σ, pico. Medicina: cm/s, media (DE), mediana [Q1-Q3], mín-máx |
| `--participante CODIGO` | el del `.json` de la sesión, o vacío | Columna `participante` del de medicina |
| `--salida CARPETA` | `articulos/` junto a la captura | Dónde guardarlos (`<captura>_ingenieria.csv`, `<captura>_medicina.csv`) |
| `--todos-los-puntos` | apagado | Una serie por cada uno de los 22 puntos (por defecto: muñeca, puntas de los dedos y codo) |

Durante la captura: `e` genera los dos con lo grabado hasta ese momento, sin parar (si se repite, reemplaza los anteriores). Columnas y cómo usarlos: [docs/ARTICULOS.md](docs/ARTICULOS.md#exportar-para-artículos-exportar_csvpy).

### `panel.py` — el panel (23-A)

```bash
./venv/bin/python3 panel.py           # Windows: venv\Scripts\python panel.py
```

Una ventana con todo lo de esta referencia: elige la tarea a la izquierda, llena las opciones (cada una explicada) y *Ejecutar*. Muestra el comando exacto (botón *Copiar*) y la salida del programa; *Detener* lo corta. No agrega nada que no se pueda hacer desde la terminal. Las opciones de cada pantalla se comprobaron contra el `argparse` de cada script (2026-11-23).

| Pantalla | Comando que arma |
|----------|------------------|
| Capturar con la cámara | `captura.py [--cam N] [--palma-cm X] [--yolo-modelo n/m \| --sin-antebrazo] [--sin-3d] [--estereo --cam2 N] [--unreal [destino]] [--participante] [--notas]` |
| Analizar un video | `captura.py --video ARCHIVO [--video-espejado] …` |
| Ver una captura | `plot_csv.py CSV [--3d] [--frame N] [--palma-cm X]` |
| Exportar para artículos | `exportar_csv.py CSV [--formato] [--participante] [--todos-los-puntos]` |
| Reproducir en Unreal | `unreal_bridge.py --csv CSV [--destino] [--velocidad] [--bucle]`, y botón *Abrir proyecto de Unreal* |
| Mano de prueba / Ver lo que llega | `unreal_bridge.py --demo DESTINO` / `--escuchar PUERTO` |
| Imprimir el tablero / Calibrar | `estereo.py tablero` / `estereo.py calibrar --cuadro-mm X [--cam1] [--cam2]` |
| Pruebas | `pruebas/correr_todo.py` |

`panel.py --captura archivo.png [--pagina N]` guarda una imagen del panel sin mostrar la ventana (así se hicieron `docs/panel_*.png`).

### `unreal_bridge.py` — conexión con Unreal (19-A; `--csv` desde la 23-A)

El envío en vivo es `captura.py --unreal`. Sin cámara:

```bash
./venv/bin/python3 unreal_bridge.py --csv                      # reproduce la última captura como si fuera en vivo
./venv/bin/python3 unreal_bridge.py --csv capturas/hand_data_X.csv --bucle --velocidad 0.5
./venv/bin/python3 unreal_bridge.py --csv --destino 192.168.1.20:8000   # Unreal en otra computadora
./venv/bin/python3 unreal_bridge.py --escuchar 8000            # muestra lo que llega al puerto 8000
./venv/bin/python3 unreal_bridge.py --demo 127.0.0.1:8000      # manda una mano sintética (abre y cierra los dedos)
./venv/bin/python3 unreal_bridge.py --demo 127.0.0.1:8000 --segundos 10
```

El receptor: abrir `unreal/HandMotionUE/HandMotionUE.uproject` (arranca solo, puerto 8000; registro en `unreal/HandMotionUE/Saved/handmotion_receptor.log`).

Imágenes **reales** de Unreal (23-A; abre Unreal sin ventana y lo cierra al terminar, ~1-2 min):

```bash
./venv/bin/python3 docs/imagenes_unreal.py                     # con la última captura
./venv/bin/python3 docs/imagenes_unreal.py capturas/hand_data_X.csv
```

Imagen simulada de la conexión (17-A, se conserva como esquema), se guarda en `docs/unreal_simulado.png`:

```bash
./venv/bin/python3 docs/imagen_unreal.py            # pose a medio cerrar (t = 0.62 s)
./venv/bin/python3 docs/imagen_unreal.py --t 0      # mano abierta (--t 1: cerrada)
```

Guía completa: [`UNREAL.md`](UNREAL.md).

### Teclas

| Dónde | Teclas |
|-------|--------|
| Captura (cualquier ventana) | `q`/`Esc` salir · `n` nombres de los dedos · `v` velocidad · `f` dedos absoluta/relativa · `s` foto en `capturas/` · `espacio`/`p` **pausa** · `e` **CSV para artículos** (ingeniería y medicina) · `u` pausar/reanudar el envío a Unreal |
| Vista 3D (POV bajo el mouse) | arrastrar = girar · `Shift`+arrastrar o botón central = mover · rueda / clic derecho / `+` `=` `-` = zoom · `1` frente · `3` lado · `7` arriba · `9` vista opuesta · `.` encuadrar · `r` reiniciar |
| Vista 3D (los dos POV) | `l` vincular 180° · `v` velocidad · `f` dedos absoluta/relativa |
| Reproducción `plot_csv.py` 2D | `espacio` pausa / sigue |
| Reproducción `plot_csv.py --3d` | `espacio` o `p` pausa · `a`/`d` frame anterior/siguiente · `q`/`Esc` salir · más las de la vista 3D |
| Calibración `estereo.py calibrar` | `espacio` guardar par · `c` calibrar · `q`/`Esc` cancelar |

### Pruebas (sin cámara, desde la 28-F)

```bash
./venv/bin/python3 pruebas/correr_todo.py          # las cinco, con resumen (~1 min)
./venv/bin/python3 pruebas/filtro_velocidad.py     # One Euro vs media exponencial
./venv/bin/python3 pruebas/filtro_velocidad.py --buscar   # las 72 combinaciones de parámetros
./venv/bin/python3 pruebas/estereo_simulado.py     # calibración y triangulación simuladas
./venv/bin/python3 pruebas/captura_simulada.py     # captura.py y plot_csv.py de punta a punta (con pausa, CSV para artículos y Unreal)
./venv/bin/python3 pruebas/exportar_csv_simulado.py   # exportar_csv.py: columnas y cada número contra numpy
./venv/bin/python3 pruebas/unreal_simulado.py      # unreal_bridge.py: OSC, ejes, flexión, UDP y --csv
```

Qué comprueba cada una: [`pruebas/README.md`](pruebas/README.md).

### Git útiles

```bash
git log --follow captura.py      # historial de captura.py incluyendo cuando era Prueba.py
git log --oneline                # versiones (un commit por versión o grupo de versiones)
git status                       # capturas/, models/ y calibracion/ no aparecen: están en .gitignore
```

---

## 2. Comandos que cambiaron o se quitaron

| Antes | Ahora | Versión | Por qué |
|-------|-------|---------|---------|
| `cd MediaPipeHands` antes de todo | Todo desde la raíz (`cd HandMotion3D`) | 24-E | El proyecto pasó a ser todo el repositorio |
| `./venv/bin/pip install -r requirements.txt` | `./venv/bin/python3 -m pip install -r requirements.txt` | 24-E | El script `pip` del venv guarda una ruta absoluta y se rompe al mover la carpeta |
| `./venv/bin/python3 Prueba.py` | `./venv/bin/python3 captura.py` (mismos flags) | 28-A | Nombre descriptivo del programa principal |
| `Prueba.py --vista3d-cada N` | **Eliminado** | 24-B | Existía por el visor de matplotlib (~90 ms); el de OpenCV (~3 ms) se redibuja siempre |
| `q` solo en la ventana de la cámara | `q` o `Esc` en cualquier ventana, cerrar la ventana o `Ctrl+C` | 24-B | Bug: matplotlib se comía las teclas |
| Casillas *Vincular 180°* / *Encuadrar manos* de matplotlib | Botones del visor OpenCV y teclas `l` / `.` | 24-B | El visor dejó de ser de matplotlib |
| `r` y `.` actuaban sobre los dos POV | Solo sobre el POV bajo el mouse | 24-C | POV independientes |
| Vincular 180° activado por defecto | Apagado por defecto (tecla `l`) | 24-C | POV independientes |
| Palma fija de 9.5 cm | `--palma-cm` (o medida con `--estereo`) | 28-B | Con otra palma todas las velocidades se desviaban |
| Siempre la cámara `0` | `--cam N` | 28-D | Elegir cámara (necesario con dos) |
| Sin forma de pausar la captura | `espacio` o `p` | 19-A | Se pedía poder congelar la imagen sin cerrar el programa; nada se quitó |
| `exportar_excel.py --formato X [--salida ARCHIVO.xlsx]` | `exportar_csv.py [--formato X\|ambos] [--salida CARPETA] [--participante CODIGO]` | 17-B | Se pidió que solo se generen CSV: uno con formato de ingeniería y otro de medicina, para publicaciones científicas |
| Teclas `e` (Excel de ingeniería) y `m` (Excel de medicina) | `e` = los dos CSV; `m` ya no hace nada | 17-B | Ídem |

---

## 3. Bitácora de mantenimiento

Comandos que se ejecutaron sobre el repositorio (no sobre el programa), en orden. Sirve para saber exactamente qué se hizo, verificarlo y, si hace falta, deshacerlo.

### 2026-09-24 — versión 24-E: el proyecto pasa a la raíz

El comando exacto no quedó registrado (esta bitácora empezó el 2026-09-28); el CHANGELOG dice que se usó `git mv`. Equivalente:

```bash
git mv MediaPipeHands/* .          # los archivos conservan su historial
# .gitignore: reglas MediaPipeHands/... -> models/*.task, models/*.pt, capturas/*.csv, capturas/*.png
```

`venv/`, `models/` y `capturas/` (fuera de git) se movieron a mano. Se detectó que `./venv/bin/pip` dejó de funcionar (ruta absoluta vieja) y se cambió la documentación a `python3 -m pip`.

### 2026-09-28 — versión 28-A: renombre y versiones fijas

```bash
git mv Prueba.py captura.py                                   # conserva el historial
./venv/bin/python3 -m pip freeze | grep -iE '^(mediapipe|opencv|numpy|ultralytics|matplotlib|torch)'
./venv/bin/python3 -m pip show mediapipe ultralytics          # quién pide cada OpenCV
./venv/bin/python3 -m pip install --dry-run -r requirements.txt   # los pines coinciden con el venv
```

`pip show` mostró que `mediapipe` pide `opencv-contrib-python` y `ultralytics` pide `opencv-python`: por eso se fijaron las dos a `5.0.0.93`.

### 2026-09-28 — versión 28-D: tablero de calibración

```bash
./venv/bin/python3 estereo.py tablero
./venv/bin/python3 -c "import cv2; g=cv2.imread('calibracion/tablero_9x6.png',0); print(cv2.findChessboardCorners(g,(9,6))[0])"
# True: OpenCV detecta las 54 esquinas del tablero generado
```

### 2026-09-28 — versión 28-F: quitar la línea `Co-Authored-By` del historial

Los commits del 2026-09-23 al 2026-09-24 terminaban con una línea `Co-Authored-By` que no correspondía a un autor del proyecto, y GitHub la mostraba como colaborador del repositorio. A pedido del autor se quitó reescribiendo los mensajes. **Solo cambiaron los mensajes**: el contenido de los archivos, el autor y las fechas son los mismos.

```bash
# 1. Respaldo del historial original (rama LOCAL, no se subió a GitHub)
git branch respaldo-historial-con-coautor 49a4bd2

# 2. Reescribir los mensajes: borra la línea y limpia líneas en blanco sobrantes
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --msg-filter "sed '/^Co-Authored-By:/d' | git stripspace" -- main

# 3. Verificar
git log --format='%(trailers:key=Co-Authored-By,valueonly)' | grep -c .   # 0 líneas
git diff --stat respaldo-historial-con-coautor main                        # vacío: archivos idénticos
# + se comparó cada mensaje nuevo con el viejo sin esa línea: los 9 iguales

# 4. Subir, solo si GitHub todavía tenía exactamente el historial viejo
git push --force-with-lease=main:49a4bd2f5e66131adcae7752a533e8fc0cfa5aca origin main

# 5. Limpiar las referencias que deja filter-branch
rm -rf .git/refs/original
```

Correspondencia de hashes (los commits viejos citados en documentos anteriores):

| Antes | Ahora | Commit |
|-------|-------|--------|
| `a3d33d0` | `a3d33d0` | Add MediaPipeHands project (no tenía la línea: no cambia) |
| `b960527` | `1fa9399` | corrige Left/Right invertidos, nombres de dedos y HUD |
| `c7af088` | `7826e34` | guía rápida de uso en el README |
| `ea47aa9` | `bb0910b` | eje z con vista 3D de dos POV, antebrazo con YOLO y velocidad (24-A/24-B) |
| `8cf7146` | `5a53162` | POV independientes (24-C) |
| `d75f63c` | `98e53b2` | velocidad de cada dedo (24-D) |
| `a2ef70f` | `b0bfa33` | renombra el proyecto y lo mueve a la raíz (24-E) |
| `498e6a6` | `6ef958f` | revisión de la documentación |
| `49a4bd2` | `f6f716e` | 28-A a 28-E |

**Si tienes otra copia del repositorio** (otra computadora), su historial ya no coincide con GitHub. Si no tiene cambios propios sin subir:

```bash
git fetch origin
git reset --hard origin/main      # CUIDADO: borra cambios locales sin commit
```

**Para volver al historial original** (no debería hacer falta):

```bash
git push --force origin respaldo-historial-con-coautor:main
```

**Borrar el respaldo** cuando ya no haga falta: `git branch -D respaldo-historial-con-coautor`.

### 2026-10-19 — versión 19-A: dependencia nueva y cómo aplicar el cambio

La 19-A agrega `openpyxl==3.1.5` a `requirements.txt` (solo se usa al exportar a Excel). Para instalarla en el venv del proyecto:

```bash
./venv/bin/python3 -m pip install -r requirements.txt   # instala openpyxl
./venv/bin/python3 -c "import openpyxl; print(openpyxl.__version__)"   # verificar: 3.1.5
./venv/bin/python3 pruebas/correr_todo.py                # verificar todo (~1 min)
```

Deshacer: `./venv/bin/python3 -m pip uninstall openpyxl` (el resto del programa sigue funcionando; solo falla la exportación a Excel, con un mensaje claro).

Nota: este registro lo escribió quien implementó la 19-A **sin acceso a tu venv**: esos comandos están por correr, no corridos.

### 2026-11-17 — versión 17-A: revisión 5

Comandos corridos en el venv del proyecto (Python 3.14.8, versiones fijadas):

```bash
./venv/bin/python3 pruebas/correr_todo.py     # 5 de 5 OK (excel_simulado sin LibreOffice: fórmulas omitidas)
git check-ignore -v capturas/x.xlsx           # antes: sin salida (NO ignorado); después: .gitignore:23
./venv/bin/python3 docs/imagen_unreal.py      # genera docs/unreal_simulado.png
```

Verificar: `git check-ignore -v capturas/a.xlsx capturas/articulos/b.csv` debe nombrar una regla de `.gitignore` para cada uno.

### 2026-11-17 — versión 17-B: se quita el Excel

```bash
git rm exportar_excel.py pruebas/excel_simulado.py     # reemplazados por exportar_csv.py y su prueba
./venv/bin/python3 -m pip uninstall -y openpyxl et_xmlfile   # ya no está en requirements.txt
./venv/bin/python3 -m pip install --dry-run -r requirements.txt   # verificar: no instala nada
./venv/bin/python3 pruebas/correr_todo.py              # 5 de 5 OK
```

Deshacer: `git checkout e8bf00b -- exportar_excel.py pruebas/excel_simulado.py` (el commit de la 17-A) y `./venv/bin/python3 -m pip install openpyxl==3.1.5`.

### 2026-11-17 — versiones 17-C y 17-D: video y datos de la sesión

Sin dependencias nuevas. Comandos corridos:

```bash
./venv/bin/python3 pruebas/correr_todo.py      # 5 de 5 OK (captura_simulada con la sección 6: video y .json)
git check-ignore -v capturas/x.json            # .gitignore:25 capturas/*.json
```

Probar a mano: `./venv/bin/python3 captura.py --video mi_video.mp4 --participante P01` y revisar el `.json` que queda junto al CSV.

### 2026-11-17 — versión 17-E: README reestructurado

Sin comandos de mantenimiento: solo documentación. Las secciones del README anterior se movieron con un script a `docs/TECNICO.md`, `docs/ARTICULOS.md` y `docs/CAMBIOS.md`, reescribiendo los enlaces, y después se comprobaron todos los enlaces de los 9 documentos `.md` (0 rotos). El README anterior completo está en el commit `3d1b7cd` (`git show 3d1b7cd:README.md`).

### 2026-11-23 — versión 23-A: Windows, panel y Unreal probado

Primera vez en **Windows 11** (Python 3.13.0). Comandos corridos:

```powershell
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt     # todas las versiones fijadas se instalan en Windows
curl.exe -L -o models\hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
venv\Scripts\python -m pip install PySide6==6.11.3          # el panel (nueva en requirements.txt)
venv\Scripts\python pruebas\correr_todo.py                 # 5 de 5 OK (antes y después de los cambios)
git switch handmotion3d-19-a                                 # el trabajo de la 19-A a la 17-E estaba solo en esta rama
```

Notas de Windows:
- `pip install torch` trae la versión **para procesador**: aunque haya una tarjeta NVIDIA, YOLO corre en la CPU (`torch.cuda.is_available()` da `False`). Para usar la GPU habría que instalar torch con CUDA desde el índice de PyTorch; no se hizo ni se probó.
- La consola muestra `c�mara` si no se pone `PYTHONIOENCODING=utf-8` (solo afecta a lo que se ve en la terminal).

Publicar la versión (rama → `main`):

```bash
git push origin handmotion3d-19-a
git switch main && git merge --no-ff handmotion3d-19-a      # main estaba en la 28-F
git push origin main
```

Antes del merge se quitó la línea `Co-Authored-By` del commit de la 19-A (había vuelto a aparecer), dejando a su autor:

```bash
git branch respaldo-23a                              # respaldo LOCAL (no se sube); se borra al confirmar
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --msg-filter "sed '/^Co-Authored-By:/d' | git stripspace" -- main..handmotion3d-19-a
git log main..handmotion3d-19-a --format='%(trailers:key=Co-Authored-By,valueonly)' | grep -c .   # 0
git diff --stat respaldo-23a handmotion3d-19-a       # vacío: archivos idénticos
git push --force-with-lease origin handmotion3d-19-a
```

Deshacer el merge (antes de que alguien más lo use): `git reset --hard 845f30b` en `main` (el commit de la 28-F) y `git push --force-with-lease origin main`.

### Pendiente: nombre del repositorio en GitHub

La versión 24-E decía que el repositorio de GitHub se renombraría a `HandMotion3D`, pero al 2026-09-28 **sigue llamándose `Machine_Learning`** (`https://github.com/N0x370z/Machine_Learning` responde sin redirección). Para renombrarlo:

1. En GitHub: *Settings → General → Repository name* → `HandMotion3D` → *Rename*. GitHub redirige la URL vieja.
2. En la copia local:

```bash
git remote set-url origin https://github.com/N0x370z/HandMotion3D.git
git remote -v        # comprobar
```
