# Changelog — HandMotion3D (antes MediaPipeHands)

Historial de cambios del proyecto. Formato libre pero cronológico
(más reciente arriba), en español porque así está el resto del repo.

## 2026-11-24 (corrección tras la revisión 7: invertir izquierda/derecha al reproducir en Unreal; sin versión nueva)

Pedido: revisar el commit de la revisión 7 (capturas subidas).

### Corregido
- **Cuatro de las capturas subidas tienen Left/Right al revés** (las del 2026-09-21 y las de las 11:54 y 11:56 del 2026-09-23, grabadas antes del arreglo `1fa9399`). `plot_csv.py` ya tenía `--swap-hands`, pero `unreal_bridge.py --csv` no: en Unreal la mano izquierda se habría movido como la derecha. Ahora `unreal_bridge.py --csv … --swap-hands` y, en el panel, la casilla *Invertir izquierda/derecha* en *Reproducir en Unreal* y en *Ver una captura*. Prueba nueva en `pruebas/unreal_simulado.py`.
- `capturas/README.md` marca esas cuatro (⇄) y explica cuándo usar `--swap-hands`.

### Comprobado
- Las 14 capturas se cargan y cada mano da un mensaje válido para Unreal (87 floats): fotogramas, duraciones y formatos coinciden con la tabla de `capturas/README.md`. Las 5 pruebas pasan.

## 2026-11-24 (revisión 7: documentación, la 23-A/23-B en macOS y capturas subidas; sin versión nueva)

Pedido: revisar por qué fallaba el `git pull` en la Mac, terminar la revisión de la documentación de la 17-E, revisar la 23-A y la 23-B, y subir las capturas guardadas para trabajarlas en la PC con Unreal Engine y la RTX 4090. Detalle en [REVISION.md](REVISION.md#revisión-7--documentación-de-la-17-e-la-23-a23-b-en-macos-y-capturas-sin-versión-nueva).

### Corregido
- `docs/ARTICULOS.md` decía que reanalizar un video con la misma versión da **los mismos números**. No se comprobó, y MediaPipe/YOLO pueden variar entre equipos: ahora lo dice así.
- `docs/ARTICULOS.md`: `shasum -a 256` aparecía como comando de Linux; allí es `sha256sum`.
- README: "~3 GB libres" → "~1.5 GB" (el venv de macOS mide 1.2 GB; con torch CUDA, más, sin medir).
- README: se aclaró el ambiguo "cinco líneas `OK`" (es el `RESUMEN` con cinco pruebas).
- `exportar_csv.py`: el error de un CSV sin velocidad decía "de antes de la versión 24-A"; la velocidad llegó en la **24-B**. También en `pruebas/exportar_csv_simulado.py` y `pruebas/README.md`.

### Añadido
- README: sección breve **Apoyo de inteligencia artificial** (asistente de IA usado en el desarrollo; responsabilidad del equipo; validación pendiente).
- **Las 14 capturas de `capturas/`** (2026-09-21 a 2026-10-01, pruebas del equipo, sin participantes) se suben al repositorio con `git add -f`, sin tocar el `.gitignore`: las nuevas siguen sin subirse solas.
- **`capturas/README.md`**: qué tiene cada captura (fotogramas, duración, formato), qué columnas tiene cada uno de los 4 formatos, qué se puede hacer con cada una (Unreal, `plot_csv.py`, exportar) y los comandos para la PC con Unreal y la 4090. README (*Archivos que se generan*, receta de Unreal) enlaza ahí.

### Comprobado en macOS (la 23-A y la 23-B se habían probado solo en Windows)
- 5 de 5 pruebas `OK` con PySide6 instalado; `panel.py` abre; `unreal_bridge.py --csv` reproduce los 4 formatos de CSV de `capturas/`.

### Rama e historial
- La copia de la Mac tenía los commits de la 19-A a la 17-E de antes de quitarles la línea `Co-Authored-By` (mismos archivos): se adoptó el historial de GitHub y se trabajó sobre `main` (ver `COMANDOS.md`).

## 2026-11-23 (versión 23-B: YOLO en la GPU NVIDIA)

Pedido: instalar torch con CUDA para usar la RTX 4090.

### Corregido
- **`forearm.py` nunca usaba una GPU NVIDIA**: `_pick_device()` solo probaba MPS (Apple) y si no, CPU. Ahora prueba primero CUDA (`cuda:0`). Antes daba igual (torch de `pip` en Windows es solo para CPU), pero con torch CUDA instalado YOLO seguía en el procesador.

### Añadido
- Instalación de torch 2.14.0 / torchvision 0.29.0 **con CUDA 13.0** (las mismas versiones fijadas) para tarjetas NVIDIA: paso 2b del README, comentario en `requirements.txt` y bitácora en `COMANDOS.md`.
- Medido (yolo11s-pose, 1280×720, RTX 4090): **36.9 ms por fotograma en CPU → 7.6 ms en la GPU**. Las 5 pruebas pasan con torch CUDA.

## 2026-11-23 (versión 23-A: Windows, panel y Unreal probado de verdad)

Pedido: revisar el proyecto en la PC con Windows, correrlo con lo guardado (no había webcam), comprobar que funciona con Unreal Engine, hacer una interfaz que se vea bien, guardar imágenes de cómo se ve en Unreal y subirlo todo.

### Corregido
- **CSV con acentos en Windows.** `captura.py` abría el CSV sin decir la codificación: en Windows se escribía en cp1252 (la `ñ` de `Muñeca` en un solo byte) y en macOS en UTF-8. Peor: un CSV hecho en la Mac con `Índice` hacía **fallar** `plot_csv.py` en Windows (el byte 0x8D de la `Í` en UTF-8 no existe en cp1252). Ahora se escribe siempre en UTF-8 (como ya hacían `exportar_csv.py` y `sesion.py`) y `plot_csv.py` / `unreal_bridge.py` leen en UTF-8 tolerando bytes raros (`errors="replace"`), así también se leen los CSV viejos de Windows. Las pruebas leen y escriben en UTF-8.

### Añadido
- **`panel.py`**: una ventana (Qt, PySide6) para usar todo sin recordar comandos: capturar, analizar un video, ver y exportar una captura, reproducir en Unreal, mano de prueba, ver lo que llega, tablero y calibración, pruebas. Cada opción con una línea que la explica, el **comando exacto** que se ejecuta (con *Copiar*) y la salida del programa. Las capturas se eligen de una lista con fecha, duración y participante. Estilo de herramienta de escritorio (gris oscuro, un solo acento ámbar, sin degradados). `PySide6==6.11.3` en `requirements.txt`. Ver [docs/TECNICO.md](docs/TECNICO.md#el-panel-panelpy).
- **`unreal_bridge.py --csv [ruta]`**: reproduce una captura guardada en Unreal **como si fuera en vivo**, con los tiempos con los que se grabó (`--velocidad`, `--bucle`, `--destino`, `--segundos`). Con CSV de estéreo manda la muñeca absoluta.
- **`unreal/HandMotionUE`**: un proyecto de Unreal Engine 5 listo para abrir. Al abrirse arranca un receptor (Python dentro del editor) que dibuja una mano de esferas y cilindros con los colores por dedo de `hand_style.py` y la mueve con los mensajes que llegan al puerto 8000. Registro en `Saved/handmotion_receptor.log`.
- **Imágenes reales de Unreal** (`docs/unreal_mano.png` y las tres sueltas) y el script que las genera, **`docs/imagenes_unreal.py`**: abre Unreal **sin ventana** (`-RenderOffscreen`), le manda una captura con `--csv` y renderiza la mano más abierta y la más cerrada que recibió. Reemplazan a la imagen simulada en el README, `UNREAL.md` y `docs/TECNICO.md` (la simulada se conserva como esquema).
- `pruebas/unreal_simulado.py`: sección 7, `--csv` (tiempos, ejes, palma, id, muñeca de estéreo y acentos en UTF-8). 6 comprobaciones nuevas.

### Comprobado en Unreal Engine 5.8.4 (antes solo se había probado sin Unreal)
- El receptor recibió **495 de 495** fotogramas mandados con `--csv`, a ~41 por segundo; la flexión del índice va de 9° a 74° y vuelve, igual que en el CSV.
- El **plugin OSC** de Unreal recibe los paquetes y dispara *On OSC Message Received*.
- Tres cosas que no se sabían y que quedan en `UNREAL.md`: *(1)* desde **Python** no se puede leer un mensaje del plugin OSC (`FOSCMessage` guarda el paquete en un campo que no es `UPROPERTY` y llega vacío), por eso el receptor decodifica el OSC él mismo; en Blueprint no pasa; *(2)* si el servidor OSC no queda guardado en una variable, el recolector de basura lo destruye a los pocos fotogramas; *(3)* en UE 5.8 la dirección se pasa a texto con *Get OSC Address Full Path*.
- Lo que costó llegar a las imágenes (para no repetirlo): `-ExecutePythonScript` **cierra el editor** al terminar el script (por eso el receptor arranca desde `init_unreal.py`); en un commandlet con `-AllowCommandletRendering` el motor no avanza y la imagen sale negra; con la exposición manual por defecto (EV100 ≈ 10) la escena también sale negra (se fija EV100 = 2); el nivel por defecto del editor trae cielo, terreno y sol (se usa un nivel en blanco); un piso o un fondo oscuro salían blancos por el reflejo del mapa de ambiente (la mano va sobre negro).

### Windows
- Primera vez en **Windows 11** con Python 3.13.0: las versiones fijadas se instalan todas y las **5 pruebas pasan** (antes y después de los cambios). No se probó con una webcam (no había).
- `pip` instala **torch para procesador**: con una tarjeta NVIDIA, YOLO sigue en la CPU. Anotado en `COMANDOS.md`; no se cambió.
- README: Windows en *Requisitos*, *El panel*, la receta de Unreal con el proyecto y `--csv`, y dos problemas comunes nuevos (Unreal no se mueve; acentos en la consola).

### Rama e historial
- Todo el trabajo de la 19-A a la 17-E estaba solo en la rama `handmotion3d-19-a`; en esta PC el clon estaba en `main` (28-F). La 23-A se hizo sobre la rama y se fusiona a `main` (ver `COMANDOS.md`).
- Antes de fusionar se quitó del mensaje del commit de la 19-A la línea `Co-Authored-By` que había vuelto a aparecer (como en la 28-F). **Guillermo Campos Salas sigue como autor** de ese commit; solo cambió el mensaje (archivos, autores y fechas verificados iguales). La documentación ya no nombra herramientas en esas notas.

## 2026-11-17 (versión 17-E: README reestructurado como guía de uso)

Pedido: mejorar las instrucciones del README.

### Problemas del README anterior
- Antes de la primera instrucción había **6 bloques de novedades** e historia.
- **1,105 líneas** que mezclaban tres documentos: la guía de uso, cómo funciona cada parte y el historial (la sección *Cambios* sola, 184 líneas, que repetía buena parte del CHANGELOG y de COMANDOS).
- Faltaban los **requisitos**, cómo **clonar** el repositorio, los comandos para **Windows** (todos eran `./venv/bin/python3`) y cómo **comprobar** que la instalación quedó bien.
- No había una receta para una **sesión de artículo**: había que armarla con partes de cinco secciones.

### Cambiado
- **`README.md`** (247 líneas): qué hace, requisitos, instalación en 4 pasos para macOS/Linux y Windows con una comprobación al final (`pruebas/correr_todo.py`), primera captura en 5 pasos, recetas (sesión para un artículo, analizar un video, dos cámaras, Unreal, más opciones), teclas, archivos que se generan, problemas comunes (con los de `--video`) y un mapa de la documentación.
- **`docs/TECNICO.md`**: todas las secciones técnicas del README anterior, sin recortar (captura, vista 3D, antebrazo, velocidad, dos cámaras, `plot_csv.py`, pausa, Unreal, pruebas, estructura, versiones fijadas), con los flags de la 17-C/17-D.
- **`docs/ARTICULOS.md`**: la sección *Exportar para artículos* más una **sesión paso a paso**, qué archivos quedan, los campos del `.json` de la sesión y cómo reanalizar un video (reproducibilidad, huella SHA-256).
- **`docs/CAMBIOS.md`**: la sección *Cambios: comandos, partes quitadas y por qué*, entera, con las filas de la 17-C a la 17-E. Se sigue actualizando con cada cambio.
- Los enlaces internos se reescribieron al mover las secciones y se comprobaron todos (ninguno roto en los 9 documentos).

### Corregido
- **Requisito de Python:** con las versiones fijadas hace falta **Python 3.12 o más nuevo** (lo exige numpy 2.5; torchvision excluye la 3.14.1). No estaba escrito en ningún lado.
- Cuatro afirmaciones de esta versión estaban mal o sin comprobar; se corrigieron en la revisión 7 (2026-11-24, arriba).

## 2026-11-17 (versión 17-D: datos de cada sesión)

Idea 3 de la lista de mejoras: guardar con qué se midió cada sesión, para la reproducibilidad que piden las revistas.

### Añadido
- **`sesion.py`** y **`capturas/hand_data_<inicio>.json`** junto a cada CSV: participante, notas, fuente (cámara con resolución pedida y real, o video con ruta, **huella SHA-256**, FPS y fotogramas; con `--estereo`, la calibración con su huella y la separación entre cámaras), parámetros que cambian la medición (palma, umbrales, modelo YOLO, filtro One Euro, hueco máximo), destino de Unreal, versión del programa (la del CHANGELOG), **commit de git** y si había cambios sin commit, Python, sistema y versiones de mediapipe, OpenCV, numpy, ultralytics y torch; hora de inicio y fin, fotogramas procesados y con mano, duración, FPS efectivos y motivo del fin.
  - Se crea al grabar la primera mano con `"estado": "en curso"` y se completa al salir (`"completa"`, o `"error"` si el programa falló). Si queda `"en curso"`, el proceso murió sin poder cerrar. Se escribe con archivo temporal + renombrar, y un error al escribirlo solo se avisa.
- `captura.py --participante CODIGO` y `--notas TEXTO`; el participante se muestra en el panel y pasa solo a la columna `participante` del CSV de medicina (tecla `e`). `exportar_csv.py` lo toma del `.json` si no se le da `--participante`.
- `.gitignore`: `capturas/*.json` (pueden tener el código del participante y rutas).
- `pruebas/captura_simulada.py`: el `.json` en vivo y con video (fuente, huella, versión, commit, motivo del fin, error), y el participante hasta el CSV de medicina.

### Corregido al escribir las pruebas
- Los fotogramas procesados del `.json` salían uno menos que los grabados al salir con `q` (el contador del bucle se incrementa al final); ahora hay un contador propio (`frames_read`).

## 2026-11-17 (versión 17-C: analizar videos grabados)

Idea 1 de la lista de mejoras: reanalizar sesiones, procesar videos clínicos ya grabados y que otra persona reproduzca los resultados con el mismo archivo.

### Añadido
- **`captura.py --video ARCHIVO`**: analiza un video (mp4, mov, avi…) en lugar de la cámara, con todo lo demás igual (antebrazo, velocidad, vista 3D, CSV, pausa, `e`, Unreal).
  - **El tiempo sale del video, no del reloj** (`VideoClock`: `CAP_PROP_POS_MSEC`, que sirve para videos de celular con FPS variable, o número de fotograma / FPS). Las velocidades son las reales aunque el análisis vaya más lento o más rápido que el video. Comprobado: con un video simulado a 120 FPS analizado ~3 veces más lento, 20.3 cm/s (real 20.0); con el reloj habría salido ~3 veces menos.
  - Se analizan **todos los fotogramas**: con video no se descartan fotogramas al reanudar la pausa ni tras exportar (`drain` solo con cámara), y la pausa no deja hueco en el tiempo.
  - Al terminar el video: `Fin del video: N fotogramas analizados.` y el CSV queda cerrado.
  - El panel muestra el avance (`Video: 450/900 (50 %), t = 15.00 s`).
  - `--video-espejado`: para videos que ya están en espejo (grabados con la vista previa de una cámara frontal); sin esto se voltean como la webcam.
  - No se combina con `--estereo` (error claro).
- `plot_csv.py` acepta `timestamp_ms` con decimales (por robustez; el CSV sigue escribiendo ms enteros).
- `pruebas/captura_simulada.py`, sección 6: todos los fotogramas, tiempo del video, velocidad real con análisis lento, pausa sin saltos, video inexistente, `--video` con `--estereo`.

### Verificado
- Con un mp4 real escrito por OpenCV (60 FPS, 120 fotogramas): se leen los 120 y el tiempo de cada uno avanza exactamente 16.667 ms.

## 2026-11-17 (versión 17-B: dos CSV para artículos en lugar del Excel)

Pedido: quitar el Excel y que solo se generen CSV: dos, uno con el formato de ingeniería y otro con el de medicina, para usarlos después en publicaciones científicas.

### Añadido
- **`exportar_csv.py`**: de una captura genera `capturas/articulos/<captura>_ingenieria.csv` y `<captura>_medicina.csv`.
  - **Ingeniería** (SI): por serie, `N`, `T_s`, `fs_hz`, `media_m_s`, `rms_m_s`, `sigma_m_s`, `pico_m_s`, más `palma_cm`, `profundidad` y `resolucion_px`.
  - **Medicina** (cm/s): por serie, `n`, `duracion_s`, `media_cm_s`, `de_cm_s`, `mediana_cm_s`, `q1_cm_s`, `q3_cm_s`, `min_cm_s`, `max_cm_s`, los textos `media_de` («12.3 (4.5)») y `mediana_q1_q3` («11.0 [8.2-14.1]»), `palma_cm`, `profundidad` y una columna **`participante`** (`--participante`) para juntar sesiones.
  - Formato *tidy*: una fila por serie (mano × punto × tipo de rapidez), coma, punto decimal, UTF-8, nombres de columna en ASCII con la unidad al final; números ya calculados; celda vacía = no se puede calcular.
  - Flags: `--formato {ingenieria,medicina,ambos}`, `--participante`, `--salida CARPETA`, `--todos-los-puntos`.
  - Se escribe en un `.tmp` y se renombra: nunca queda un CSV a medio escribir.
- **Tecla `e`** en `captura.py`: los dos CSV con lo grabado hasta ese momento; si se repite, reemplaza los anteriores (y lo dice en la terminal).
- **`pruebas/exportar_csv_simulado.py`**: columnas, cada número de los dos formatos contra numpy (error máx. 0.00005 m/s y 0.005 cm/s, por el redondeo), cuartiles inclusivos (1..10 → 3.25 / 7.75, como `QUARTILE` de Excel), palma por mano con dos manos en estéreo, casos borde. `captura_simulada.py`: `e` de punta a punta, dos veces, en pausa, sin datos, y que `m` ya no exporta.
- README: sección **Exportar para artículos** con el diccionario de columnas, las 12 ecuaciones (antes en la hoja *Ecuaciones*) y lo que hay que saber antes de publicar (antes en *Limitaciones* y *Notas estadísticas*).

### Quitado
- `exportar_excel.py`, `pruebas/excel_simulado.py`, la tecla `m`, `export_excel_now` / `EXCEL_KEYS` y `openpyxl` (de `requirements.txt` y del venv).

### Corregido (hallazgos de la revisión 5 que vivían en el Excel)
- **Palma**: era el valor más repetido de todo el CSV; con `--estereo` (palma medida en cada fotograma) salía casi al azar y con dos manos se reportaba una sola. Ahora es la **mediana de cada mano**.
- `523.00` fotogramas (formato numérico aplicado a toda la columna) y fórmulas que las vistas previas mostraban vacías: no aplican a un CSV.
- Las exportaciones van a `capturas/articulos/` para que `plot_csv.py` (que abre el último `hand_data_*.csv`) no las tome por una captura.

### Medido
- Exportar una captura simulada de 10 min con una mano: **1.1 s** (el Excel tardaba 2.6 s).

## 2026-11-17 (versión 17-A: correcciones de la revisión 5 e imagen simulada de Unreal)

Revisión de la 19-A (revisión 5, ver [`REVISION.md`](REVISION.md)) y pedido de una imagen de cómo se vería la conexión con Unreal Engine.

### Corregido
- **`.gitignore` no dejaba fuera las exportaciones.** Solo ignoraba `capturas/*.csv` y `capturas/*.png`: los `.xlsx` de la 19-A (con edad, sexo y condición clínica del participante en el formato de medicina) se habrían subido a GitHub con un `git add .`. Ahora ignora `capturas/*.xlsx` y `capturas/articulos/` (donde van las exportaciones desde la 17-B).
- **La mano de `unreal_bridge.py --demo` estaba mal armada.** El nudillo del dedo medio (`points[9]`) se sobrescribía al final, así que ese dedo salía **doblado 109° hacia atrás** con la mano abierta, y el pulgar marcaba 58° de flexión en reposo. Quien armara el Blueprint con `--demo` habría visto un dedo roto. Se encontró al dibujar la imagen simulada. `demo_hand()` ahora usa `_DEMO_FINGERS` (nudillos, largo de falanges y flexión máxima de una mano adulta): abierta, ninguna articulación pasa de 14°; cerrada, cada una llega a su máximo (índice 75° / 95° / 65°); la palma mide lo que dice `palm_cm`.
- Comentario de `JOINTS` en `unreal_bridge.py`: decía que la flexión va en los floats `[70:85]`; va en `[72:87]` (el código y `UNREAL.md` ya estaban bien).

### Añadido
- **`docs/imagen_unreal.py` y `docs/unreal_simulado.png`**: imagen **simulada** de HandMotion3D conectado con Unreal Engine 5 (ventana de `captura.py --unreal`, registro de mensajes, flexión recibida, la mano en los ejes de Unreal y el Blueprint de `UNREAL.md`). No es una captura de Unreal, pero la pose y los números salen de los mensajes OSC reales de `--demo`, decodificados: si el Blueprint lee bien el mensaje, esa es la pose que tiene que verse. En `UNREAL.md` (sección *Así se vería*) y en el README.
- `pruebas/unreal_simulado.py`: tres comprobaciones nuevas de la mano de `--demo` (abierta sin articulaciones dobladas, cerrada = flexión máxima, largo de palma).

### Verificado
- `pruebas/correr_todo.py` en el **venv del proyecto** (Python 3.14.8 y las versiones fijadas, con YOLO), pendiente desde la 19-A: 5 de 5 OK. La parte de `excel_simulado.py` que recalcula fórmulas se omitió (no hay LibreOffice instalado).

## 2026-10-19 (versión 19-A: pausa, Excel para artículos y conexión con Unreal Engine)

Tres pedidos: pausar el video cuando se solicite, generar un Excel con el formato de artículos de ingeniería y de medicina, y conectar el movimiento de las manos con un modelo 3D en Unreal Engine.

### Añadido
- **Pausa** (`captura.py`): `espacio` o `p` congela la imagen (con el aviso PAUSA), **no lee la cámara, no graba y no manda nada a Unreal**; el visor 3D sigue vivo para girarlo, y siguen disponibles `s` (foto sin panel), `e`/`m`, `u` y `q`. Al reanudar se descartan 6 fotogramas acumulados por la cámara (`DRAIN_FRAMES`), para que la imagen no vaya atrasada. El tiempo del CSV es el real: la pausa deja un hueco en `timestamp_ms` y la velocidad se reinicia en 0 (hueco > `MAX_GAP_S`) en lugar de calcular un salto. `plot_csv.py`: `espacio` pausa la animación 2D, y en `--3d` `p` es alias de `espacio`.
- **`exportar_excel.py`** y teclas `e` / `m` en `captura.py`: Excel de una captura, en dos formatos.
  - **Ingeniería** (estilo IEEE): hojas *Parámetros* (N, T, f_s, resolución, palma), *Ecuaciones* (12, numeradas, en texto y LaTeX), *Resultados* (N, media, RMS, σ, pico **en m/s**), *Limitaciones* y *Datos*.
  - **Medicina**: hojas *Métodos* (borrador con campos por completar: ética, participante, instrumento), *Tabla 1* (características), *Tabla 2* (**media (DE)**, **mediana [Q1-Q3]**, mín-máx **en cm/s**), *Notas estadísticas* y *Datos*.
  - La hoja *Datos* es ancha (un fotograma por fila, una serie por columna) y **los resultados son fórmulas de Excel** sobre ella: rastreables y recalculables si se borran filas. Solo funciones clásicas (`STDEV`, `QUARTILE`, `FIXED`...) para que abra igual en Excel, LibreOffice y Google Sheets.
  - Desde la captura, `e` / `m` exportan **lo grabado hasta ese momento sin parar** (`CsvRecorder.flush()`); un error al exportar nunca interrumpe la captura.
- **`unreal_bridge.py`**, `--unreal [host:puerto]` y tecla `u`: manda la pose de cada mano a Unreal Engine por **OSC sobre UDP** (codificador propio, sin dependencias nuevas): 21 puntos en cm relativos a la muñeca (ejes de Unreal), posición de la muñeca, codo y **flexión en grados de 15 articulaciones**; 87 floats por mano y por fotograma, más un mensaje de fotograma. Incluye `--escuchar` (ver lo que llega) y `--demo` (mano sintética, sin cámara). Guía: **`UNREAL.md`**.
- **Pruebas** (en `pruebas/`, `correr_todo.py` ahora corre cinco): `excel_simulado.py` (fórmulas recalculadas con LibreOffice contra numpy), `unreal_simulado.py` (OSC, ejes, flexión, UDP) y la sección 5 de `captura_simulada.py` (pausa, Excel y Unreal de punta a punta).
- `requirements.txt`: `openpyxl==3.1.5` (solo se carga al exportar).
- Documentación: README (secciones *Pausa*, *Exportar a Excel*, *Unreal Engine*, comandos, estructura, versiones), `UNREAL.md`, `COMANDOS.md`, `REVISION.md` (revisión 4) y `pruebas/README.md`.

### Decisiones de diseño (y por qué)
- **«real engine» se interpretó como Unreal Engine.** El formato de red (OSC estándar) sirve para otro motor, pero la guía es de Unreal.
- **Excel: sin intervalos de confianza ni valores p entre fotogramas.** Fotogramas consecutivos están autocorrelacionados; esas cifras saldrían demasiado optimistas. La hoja de medicina lo explica y propone resumir un valor por participante.
- **Excel: `FIXED` en vez de `TEXT`** para armar «media (DE)»: `TEXT(x, "0.0")` depende del idioma de Excel (con coma decimal, el formato `0.0` se interpreta distinto); `FIXED` no.
- **OSC: todo floats.** Un primer borrador mezclaba ints, strings y floats; en Blueprint el índice de un valor depende de si Unreal cuenta todos los argumentos o solo los de su tipo. Con solo floats no hay ambigüedad.
- **Pausa en `plot_csv.py` 2D solo con `espacio`:** en matplotlib `p` ya es el paneo.
- **Flexión en vez de rotaciones por hueso:** un giro por articulación es lo más fácil de aplicar a cualquier esqueleto sin depender de su orientación.

### Encontrado (pendiente)
- **Nada de esto se probó con hardware, con Unreal Engine ni con Excel de escritorio.** La verificación fue con simulaciones, y las fórmulas con LibreOffice. Falta: la pausa con la webcam real, abrir los `.xlsx` en Excel, y armar el Blueprint en Unreal con `--demo` (los nombres de los nodos de OSC y el eje de giro de los dedos del modelo son lo primero que confirmar).
- La verificación de esta versión se corrió en un entorno **distinto al fijado en `requirements.txt`** (Python 3.12, mediapipe 0.10.33, OpenCV 4.13, sin YOLO/torch: `--sin-antebrazo`). Hay que correr `pruebas/correr_todo.py` en el venv del proyecto.
- Las pruebas de `captura_simulada.py` exigen que **exista `models/hand_landmarker.task`** aunque MediaPipe esté simulado (`captura.main()` lo comprueba antes). En un clon limpio hay que descargar el modelo (README, paso 1) o crear un archivo vacío con ese nombre para correrlas.
- La rapidez **no está validada contra una referencia**: antes de usar las cifras en un artículo hay que validarlas (el Excel lo avisa en *Limitaciones*).
- No se manda la **orientación de la muñeca** a Unreal (se calcula allí con los puntos 0, 5 y 17).

## 2026-09-28 (versión 28-F: pruebas, registro de comandos y de revisiones)

### Corregido
- **`estereo.py` triangulaba puntos fuera de la imagen.** MediaPipe
  devuelve puntos algo fuera del cuadro cuando un dedo se sale de la
  imagen (los extrapola). Fuera de la imagen el modelo de distorsión del
  lente de la calibración no vale, y el punto triangulado se corría: en
  una prueba, 6.45 cm, con un error de reproyección medio de solo
  1.08 px (así que el emparejamiento lo aceptaba). Ahora solo se
  triangulan los puntos dentro de las dos imágenes (`_inside`,
  `INSIDE_MARGIN_FRAC = 0`); los de afuera conservan la `z` de MediaPipe
  y quedan sin `x_cm`/`y_cm`/`z_cm`. Hacen falta la muñeca y 8 puntos
  visibles (`MIN_VISIBLE_POINTS`); la palma solo se mide si también se ve
  el nudillo del medio. `StereoHand.points_cm` puede tener `None` y
  `palm_cm` puede ser `None` hasta que se pueda medir (el panel muestra
  `palma ?`).
- **Prueba de punta a punta irreal:** la cámara 2 simulada "veía" la
  mano aunque estuviera fuera de su imagen. Ahora no la detecta si la
  muñeca queda fuera (como MediaPipe real), y los números de la 28-D se
  volvieron a medir (README y `REVISION.md`).
- Se completaron los últimos 6 docstrings que faltaban
  (`HandTrack.update`, `_norm`, y las funciones internas de dibujo y de
  la animación 2D). `forearm.py`: fecha de actualización.

### Añadido
- **`pruebas/`**: las comprobaciones que hasta la 28-E se hacían con
  scripts sueltos fuera del repositorio, ahora con tolerancias, `OK` /
  `FALLA` y código de salida:
  - `filtro_velocidad.py`: One Euro contra la media exponencial
    (`--buscar` repite la búsqueda de las 72 combinaciones);
  - `estereo_simulado.py`: calibración, guardar/leer, triangulación,
    emparejamiento, dedos fuera de cuadro y casos borde;
  - `captura_simulada.py`: `captura.py` y `plot_csv.py` de punta a punta
    con cámaras, ventanas y MediaPipe simulados;
  - `correr_todo.py`: las tres, cada una en su proceso, con resumen.
  - `pruebas/README.md`: qué comprueba cada una, qué se encontró al
    pasarlas y qué **no** cubren.
- **`COMANDOS.md`**: registro de comandos. Referencia de todos los
  comandos, flags y teclas; comandos que cambiaron o se quitaron; y una
  bitácora de los comandos de mantenimiento ejecutados sobre el
  repositorio (git, pip), con cómo verificarlos y deshacerlos.
- **`REVISION.md`**: registro de las tres revisiones del 2026-09-28
  (documentación, código completo, pruebas), con lo encontrado, lo
  corregido y el estado de los pendientes.
- README: tabla de documentos del proyecto, índice, sección **Pruebas**,
  comportamiento de los dedos fuera de cuadro en estéreo y números
  actualizados.

### Historial de git
- Se quitó una línea `Co-Authored-By` que no correspondía a un autor de los 5
  commits que la tenían, reescribiendo los mensajes con
  `git filter-branch --msg-filter` y subiendo con
  `git push --force-with-lease`. Solo cambiaron los mensajes: los
  archivos, el autor y las fechas son los mismos (verificado con
  `git diff` contra el respaldo y comparando los 9 mensajes). Los hashes
  cambiaron; la correspondencia, los comandos exactos y cómo deshacerlo
  están en `COMANDOS.md` (bitácora). Queda un respaldo **local** en la
  rama `respaldo-historial-con-coautor` (no se subió).

### Encontrado (pendiente)
- El repositorio de GitHub **sigue llamándose `Machine_Learning`**: el
  renombre a `HandMotion3D` que menciona la 24-E no se hizo. Pasos en
  `COMANDOS.md`.

## 2026-09-28 (versión 28-E: correcciones de la revisión completa)

Revisión de todo el código y de cómo se venía manejando el proyecto.
Lo que era un error se corrigió aquí; lo que era de proceso quedó
anotado al final de esta entrada.

### Corregido
- **Timestamps con la hora del sistema.** `captura.py` usaba
  `time.time()`, que puede saltar hacia atrás (ajuste de hora por red).
  MediaPipe en modo `VIDEO` exige timestamps estrictamente crecientes y
  habría fallado a mitad de la sesión. Ahora `time.monotonic()`, y el
  timestamp siempre es al menos 1 ms mayor que el anterior.
- **Dos sesiones en el mismo segundo se pisaban el CSV** (mismo nombre).
  Ahora se agrega `_2`, `_3`… Se encontró en las pruebas de la 28-B.
- **Cámara desconectada:** si la cámara dejaba de entregar imágenes, el
  programa terminaba sin decir nada. Ahora avisa (y el CSV queda
  guardado).
- **Título de la ventana:** seguía siendo `MediaPipe Hands`, el nombre
  viejo del proyecto. Ahora `HandMotion3D - Camara`.
- CHANGELOG: la entrada 24-E tenía la ruta absoluta de la carpeta
  personal del autor; se reemplazó por "la carpeta vieja del proyecto".

### Revisado sin cambios (funciona como está)
- `HandTracker`, `forearm.py` (emparejamiento, memoria, estimación),
  `viewer3d.py` (proyección, encuadre, mouse, teclas) y `plot_csv.py`
  (lectura de los seis formatos de CSV, probada con CSVs reales del
  2026-09-18 y del 2026-09-24).

### Proceso (anotado, no es código)
- Los commits desde `b960527` hasta `a2ef70f` (hoy `1fa9399` a `b0bfa33`)
  llevaban una línea `Co-Authored-By` que no correspondía a un autor. Desde ahora los
  commits van solo a nombre del autor. **Resuelto en la 28-F**: se
  reescribió el historial.
- Las comprobaciones "con datos simulados" (24-D y las de hoy) se
  hicieron con scripts sueltos que no quedaron en el repositorio.
  **Resuelto en la 28-F**: `pruebas/`.
- Muchas funciones nuevas no se pueden probar sin hardware (cámaras
  reales, dos webcams). Las pruebas de hoy reemplazan cámaras, ventanas y
  MediaPipe por simulaciones; falta probar `--estereo` y
  `estereo.py calibrar` con dos webcams reales.

## 2026-09-28 (versión 28-D: profundidad real con dos cámaras)

### Añadido
- **`estereo.py`**: dos webcams fijas miden la posición 3D real de los
  21 puntos de la mano por triangulación, en vez de la `z` relativa que
  estima MediaPipe.
  - `estereo.py tablero`: genera un tablero de ajedrez para imprimir
    (`calibracion/tablero_9x6.png`).
  - `estereo.py calibrar --cuadro-mm MM`: calibra el par con 15–20
    fotos del tablero (`espacio` guarda, `c` calcula). Primero calibra
    cada cámara (`cv2.calibrateCamera`) y después la pose entre las dos
    (`cv2.stereoCalibrate` con `CALIB_FIX_INTRINSIC`). Guarda
    `calibracion/estereo.npz` e informa el error RMS y la distancia entre
    cámaras.
  - `StereoHands`: empareja cada mano de la cámara 1 con la de la cámara
    2 por el error de reproyección (acepta hasta el 1.5 % del ancho),
    triangula, reemplaza la `z` (misma convención que MediaPipe) y mide
    la palma (suavizada). Si la cámara 2 pierde la mano, esa mano vuelve
    a la `z` de MediaPipe pero conserva la última palma medida
    (`known_palm`), para que la escala no salte.
- `captura.py`: flags `--estereo`, `--cam`, `--cam2` y `--calibracion`;
  ventana `HandMotion3D - Camara 2`; en el panel, manos trianguladas,
  distancia, palma medida y error; etapa `estereo` en los ms.
- CSV: columnas `x_cm`, `y_cm`, `z_cm` (posición absoluta respecto a la
  cámara 1, solo con `--estereo`) y `fuente = estereo`.
- `.gitignore`: `calibracion/` (la calibración es de cada par de cámaras).

### Probado (con cámaras simuladas; no con webcams reales)
- Calibración con 18 pares simulados: distancia entre cámaras 18.04 cm
  (real 18.0), RMS 0.28 px.
- Mano a 45 cm con palma de 9.0 cm: palma medida 9.12 cm, distancia
  45.0 cm, error de posición máximo 0.9 cm. Dos manos en distinto orden
  en cada cámara: emparejadas bien.
- `captura.py --estereo` completo (cámaras y MediaPipe simulados, YOLO y
  visor 3D reales), mano de 8.5 cm a 20 cm/s: palma 8.48–8.52 cm,
  19.9 cm/s. Con la cámara 2 viendo la mano de a ratos: 20.2 cm/s de
  mediana, sin picos.
- **Corrección (28-F):** en esas pruebas la mano quedaba en parte fuera
  de la imagen de la cámara 2 sin que se notara, y la simulación la
  seguía "viendo". Los números se volvieron a medir en la 28-F (palma
  9.01 cm, error máximo 0.45 cm con la mano entera en las dos imágenes).

## 2026-09-28 (versión 28-C: velocidad con filtro One Euro)

### Cambiado
- `kinematics.py`: la velocidad se calcula con un **filtro One Euro**
  (Casiez, Roussel y Vogel, 2012) por mano y punto (`OneEuroFilter`),
  en vez de la media exponencial fija `VELOCITY_SMOOTHING = 0.35`. El
  filtro suaviza mucho con el punto quieto y poco con el punto rápido.
  Solo se filtra para la velocidad: las posiciones dibujadas y guardadas
  siguen siendo las de MediaPipe. `plot_csv.py --3d` usa el mismo filtro.
- Parámetros `EURO_MIN_CUTOFF = 0.5`, `EURO_BETA = 10`,
  `EURO_D_CUTOFF = 2`, elegidos entre 72 combinaciones con datos
  simulados (30 FPS, temblor de ~0.8 px y ~1.5 px):
  - mano quieta: rapidez de ruido 2.3 → 0.8 cm/s de media (p95 4.6 → 1.9);
  - arranque a 40 cm/s: 90 % en ~95 ms en vez de ~190 ms;
  - frenado: ~80 ms en vez de ~150 ms;
  - golpeteo de un dedo a 4 Hz: igual que antes (~49 % del pico);
  - a cambio, en movimiento constante la rapidez oscila un poco más
    (2.0 cm/s en vez de 0.9).

## 2026-09-28 (versión 28-B: CSV mientras se graba y `--palma-cm`)

### Cambiado
- **El CSV se escribe durante la sesión** (clase `CsvRecorder` en
  `captura.py`, reemplaza a `export_to_csv` y a la lista `records`).
  Antes todas las filas se guardaban en memoria hasta salir: una sesión
  larga ocupaba cada vez más RAM y una caída perdía toda la grabación.
  Ahora se vacía a disco cada segundo. Se comprobó que en el frame 50 el
  archivo ya tenía 122 KB y que con `Ctrl+C` a mitad quedan todas las
  filas.
- El nombre del CSV usa la hora de **inicio** de la sesión (antes, la de
  salida). Sigue sin crearse archivo si no se detecta ninguna mano.

### Añadido
- **`--palma-cm`** en `captura.py` y `plot_csv.py`: largo de la palma
  de la persona (5–15 cm), la regla con la que se pasa a cm/s. Antes
  era siempre 9.5 cm y con otra palma todas las velocidades salían
  desviadas en la misma proporción (palma de 8.5 cm: +12 %). Prueba
  simulada, mano de 8.5 cm a 20 cm/s: 22.2 cm/s sin el flag, 20.0 cm/s
  con `--palma-cm 8.5`.
- CSV: columna `palma_cm`. `plot_csv.py --3d` la usa para reproducir con
  la misma escala (o `--palma-cm` si se indica; 9.5 en CSVs viejos).
- `kinematics.py`: `cm_per_unit(points, palm_cm)`, `hand_scale(hand)`,
  `palm_cm_arg` (validación compartida del flag) y `finger_speeds(...,
  scale)`. Cada mano de la escena lleva su `palm_cm` y `cm_per_unit`.

## 2026-09-28 (versión 28-A: `captura.py` y versiones fijas)

### Cambiado
- **`Prueba.py` → `captura.py`** (con `git mv`, conserva el historial:
  `git log --follow captura.py`). "Prueba" era el nombre de cuando el
  proyecto era un ejercicio; hoy es el programa principal. Mismos flags.
  Se actualizaron todas las referencias en el código y el README (las
  tablas históricas mantienen `Prueba.py` donde describen lo de antes).
- **Versiones fijas en `requirements.txt`** para todas las dependencias:
  `mediapipe==0.10.35`, `opencv-python==5.0.0.93`,
  `opencv-contrib-python==5.0.0.93`, `numpy==2.5.3`,
  `matplotlib==3.11.2`, `ultralytics==8.4.162`, `torch==2.14.0`,
  `torchvision==0.29.0` (las del venv, Python 3.14.5). Antes solo
  `mediapipe` estaba fijado.
- **Las dos variantes de OpenCV**, `opencv-python` (la pide
  `ultralytics`) y `opencv-contrib-python` (la pide `mediapipe`), se
  instalan en la misma carpeta `cv2/`. Si quedan en versiones distintas
  se pisan archivos. Ahora las dos están fijadas a la misma versión.
- Ventana de la cámara: `MediaPipe Hands` → `HandMotion3D - Camara`.

## 2026-09-28 (revisión de la documentación)

Sin cambios de comportamiento: solo documentación.

### Corregido (documentación)
- README, *Instalación*: todavía decía `./venv/bin/pip install`, justo
  debajo de la nota que explica por qué no usarlo. Ahora
  `./venv/bin/python3 -m pip install`, igual que la guía rápida.
- README, *Problemas comunes*: la fila "Va lento" estaba dos veces; se
  unieron en una.
- README, `Prueba.py` → *Qué hace*: describía el flujo de antes del
  24-A (solo teclas `n`/`s`, salir solo con `q`). Ahora incluye el codo
  con YOLO, la velocidad, la vista 3D, las teclas `v`/`f` y las otras
  formas de salir (`Esc`, cerrar la ventana, `Ctrl+C`).
- README, panel de estado: faltaban la fila de velocidad de cada dedo y
  la línea de teclas.
- README, *Velocidad* → *Dónde se ve*: faltaba la columna
  `rapidez_rel_cm_s`.
- README, *Cambios*: decía "tres versiones" el 2026-09-24; fueron cinco
  (24-A a 24-E).
- README: la tecla `=` también acerca el zoom del POV y no estaba
  documentada.
- README, *Historial de cambios*: el resumen de la última entrada no
  mencionaba 24-D ni 24-E.
- CHANGELOG, 24-E: las reglas nuevas de `.gitignore` son
  `models/*.task`, `models/*.pt`, `capturas/*.csv` y `capturas/*.png`,
  no `models/*` y `capturas/*`.

### Añadido (docstrings)
- `Prueba.py`: `HandTrack` (y `stable_label`/`stable_score`),
  `HandTracker.update` (cómo empareja y cuándo descarta un track),
  `_centroid`, `_distance`, `export_to_csv`, `parse_args`, `main`.
- `plot_csv.py`: `_mpl_color`, `latest_csv`, `draw_frame`, `main`.
- `viewer3d.py`: `_POV.reset`, `_POV.set`, `_Projector.px`,
  `DualPOVViewer.toggle_fit`, `_on_mouse`, `close`.
- `forearm.py`: `ForearmDetector._smooth`. `kinematics.py`:
  `VelocityEstimator._forget_old`.

## 2026-09-24 (quinta parte: nombre y estructura — versión 24-E)

### Cambiado
- **Nombre del proyecto: `MediaPipeHands` → `HandMotion3D`.** El
  proyecto ya no es solo un ejercicio de Machine Learning: detecta la
  mano y el antebrazo, los muestra en 3D con dos POV y mide velocidades.
  El nombre describe eso (mano + movimiento + 3D).
- **Estructura:** los archivos salieron de la carpeta `MediaPipeHands/`
  y pasaron a la **raíz del repositorio**, que ahora es todo del
  proyecto. Se movieron con `git mv`, así que conservan su historial
  (`git log --follow <archivo>`). `venv/`, `models/` y `capturas/`
  (fuera de git) también se movieron a la raíz. El código no cambió:
  todas las rutas se calculan desde la carpeta del propio script.
- La carpeta local y el repositorio de GitHub pasan de `Machine_Learning`
  a `HandMotion3D` (el de GitHub se renombra a mano desde sus ajustes;
  GitHub redirige la URL vieja). **Nota (28-F):** al 2026-09-28 el de
  GitHub todavía no se había renombrado; pasos en `COMANDOS.md`.
- `.gitignore`: las reglas `MediaPipeHands/models/*` y
  `MediaPipeHands/capturas/*` pasan a `models/*.task`, `models/*.pt`,
  `capturas/*.csv` y `capturas/*.png`; sin este cambio los modelos
  (~34 MB) y las capturas se habrían subido a git.
- README: título, descripción, "desde dónde correr los comandos",
  estructura del proyecto e instalación actualizados.

### Corregido
- `./venv/bin/pip` no funcionaba: el script `pip` de un venv guarda la
  ruta absoluta donde se creó (este venv venía de la carpeta vieja del
  proyecto), y deja de funcionar si la carpeta se mueve. El README ahora usa `./venv/bin/python3 -m pip`,
  que funciona siempre.

## 2026-09-24 (cuarta parte: velocidad de cada dedo — versión 24-D)

### Añadido
- **Velocidad de cada dedo** (`kinematics.finger_speeds`): la de su punta
  (landmarks 4, 8, 12, 16, 20), en dos modos que se alternan con la tecla
  **`f`**:
  - *absoluta*: rapidez de la punta (incluye el movimiento de la mano);
  - *relativa a la muñeca*: rapidez de `v_punta − v_muñeca`, solo lo que
    el dedo se mueve dentro de la mano.
  Verificado con datos simulados: mover solo el índice da velocidad solo
  en el índice; mover la mano entera da los cinco dedos iguales en
  absoluta y 0 en relativa.
- Ventana de la cámara: la velocidad junto al nombre de cada dedo
  (`Indice 32`) y una fila por mano en el panel de estado
  (`Pul 12  Ind 30  Med 8  Anu 5  Men 4`).
- Vista 3D: la velocidad junto a cada punta en los dos POV y un panel en
  el POV 1 con una barra por dedo.
- `plot_csv.py --3d`: también con la tecla `f`.
- CSV: columnas `rapidez_rel_cm_s` (rapidez respecto a la muñeca) y
  `dedo` (Pulgar, Índice, Medio, Anular, Meñique, Muñeca o Codo).
- `hand_style.py`: `FINGER_ABBR` (abreviaturas) y `point_name()`.

### Corregido
- Los nombres de los dedos en la vista de la cámara usaban el contorno
  grueso; con el número de velocidad agregado el texto es más largo y
  aparecían letras repetidas al final. Ahora usan la sombra de 1 px, como
  la vista 3D.

## 2026-09-24 (tercera parte: POV independientes — versión 24-C)

### Cambiado: cada POV es una cámara virtual independiente
Pedido: poder mover una cámara (POV) sin que se mueva la otra. En la
versión anterior, "Vincular 180°" venía **activado por defecto**, así que
al girar un POV el otro también giraba, y el encuadre y el reinicio eran
compartidos.

- **"Vincular 180" ahora está apagado por defecto.** Cada POV gira por
  su cuenta. Sigue disponible (tecla `l` o botón en el medio) y, cuando
  está activo, solo vincula la **rotación**.
- **Encuadrar por POV:** cada POV tiene su propio botón *Encuadrar* y
  la tecla `.` actúa sobre el POV bajo el mouse. Antes era uno solo para
  los dos. Así se puede tener un POV siguiendo la mano y el otro con la
  escena entera.
- **`r` reinicia solo el POV bajo el mouse** (ángulo inicial, zoom,
  desplazamiento y encuadre). Antes reiniciaba los dos.
- **Nuevo: desplazar (pan) cada POV** con `Shift` + arrastrar o
  arrastrando con el botón central, como en Blender.
- Un arrastre que empieza en un POV sigue afectando solo a ese POV
  aunque el mouse cruce al otro.
- El POV bajo el mouse se marca como `(activo)` y muestra su estado
  (`elev`, `azim`, `zoom`, `encuadre`).

### Código
- `viewer3d.py`: `_POV` guarda ahora su propio `zoom`, `pan`, `fit` y
  `fit_state` (encuadre suavizado), y `reset()`. `DualPOVViewer` pierde
  `fit`/`_fit` globales; `toggle_fit(idx)` y `reset(idx)` reciben el POV;
  `linked` arranca en `False`; `_frame_target(pov, hands)` calcula el
  encuadre de cada POV por separado.

### Documentación
- `README.md`: sección de controles reescrita ("cada POV es
  independiente") y sección nueva **Cambios: comandos, partes quitadas y
  por qué**, con los comandos actuales, los que cambiaron o se quitaron,
  las partes del código reemplazadas y las versiones del formato del CSV,
  cada una con su motivo.

## 2026-09-24 (segunda parte: correcciones tras la primera prueba con cámara — versión 24-B)

### Corregido
- **Bug: `q` no cerraba bien.** Con la vista 3D (matplotlib) abierta:
  - `q` es también la tecla con la que matplotlib cierra *su* ventana
    (`rcParams["keymap.quit"]`): si el visor tenía el foco, `q` cerraba
    solo el visor y la cámara seguía corriendo.
  - El bucle de eventos de matplotlib (`flush_events`) consumía las
    teclas de la ventana de OpenCV antes de que `cv2.waitKey` las viera:
    había que presionar `q` varias veces.
  - En macOS las ventanas de OpenCV quedaban congeladas en pantalla
    después de salir, porque no se procesaban sus eventos tras
    `destroyAllWindows`.

  Corrección: el visor 3D se rehízo con OpenCV (ver abajo), así una sola
  `cv2.waitKey` recibe las teclas de las dos ventanas. Además, `Prueba.py`:
  - Sale con `q` **o** `Esc` desde cualquiera de las dos ventanas, y
    también al cerrar la ventana de la cámara con el botón rojo (antes el
    bucle seguía corriendo sin ventana).
  - Envuelve el bucle en `try/finally`: pase lo que pase (incluido
    `Ctrl+C` o un error) libera la cámara, cierra las ventanas (con 10
    vueltas de `waitKey` para que macOS las quite de verdad) y guarda el
    CSV.
  - Cerrar solo la ventana 3D ya no afecta a la captura: sigue sin 3D.
- **Bug: se alentaba.** Redibujar los dos ejes 3D de matplotlib costaba
  ~90 ms por frame. `viewer3d.py` ahora proyecta (ortográfica) y dibuja
  con OpenCV: **~3 ms por frame**. Con las dos ventanas, el bucle pasó a
  ~48 FPS en una prueba sin cámara. Se quitó `--vista3d-cada`, que ya no
  hace falta. El panel de estado muestra los ms de cada etapa (`mano`,
  `yolo`, `3D`) para ver qué frena si los FPS bajan.
- **Bug: el antebrazo tardaba en aparecer y se reconocía mal.**
  - La primera inferencia de YOLO tarda 0.3–0.7 s (carga de kernels en
    MPS) y ocurría con la primera mano en cámara. Ahora se precalienta al
    arrancar, antes de abrir la cámara.
  - `yolo11n-pose` detectaba mal el codo a distancia de webcam. Default
    nuevo `yolo11s-pose` (~9 ms vs ~6 ms); flag `--yolo-modelo {n,s,m}`.
  - Se exigía confianza ≥ 0.4 al codo **y** a la muñeca de YOLO a la vez.
    Ahora 0.25, y la muñeca de YOLO ya no es obligatoria: sin ella se
    acepta un codo a distancia plausible y del lado contrario a los dedos.
  - La distancia de emparejamiento era fija (12 % del ancho); ahora se
    adapta al tamaño de la mano (1.5 palmas, mínimo 6 %).
  - Si YOLO fallaba un frame, el antebrazo desaparecía: ahora se recuerda
    el último codo 10 frames (moviéndose con la muñeca).
  - Si YOLO no ve el codo, se **estima** prolongando el eje de la palma
    un largo de antebrazo. Se dibuja fino y punteado, con la etiqueta
    `Codo (estimado)`, y en el CSV queda `fuente = estimado`. Flag
    `--antebrazo-solo-yolo` para desactivarlo.
- Textos de la vista 3D con letras "fantasma" al final: en OpenCV el
  avance de cada letra crece con el grosor, y el contorno grueso quedaba
  más largo que el texto. Se reemplazó por una sombra de 1 px.

### Añadido: velocidad
- Nuevo módulo `kinematics.py`: velocidad de los 21 puntos de la mano y
  del codo usando juntos la posición (`x`, `y`, `z`, en la escala de la
  escena 3D) y el tiempo real de cada fotograma (`timestamp`, no el
  número de frame, porque los FPS varían). Suavizada con media
  exponencial; se reinicia si el punto no se vio por más de 0.25 s.
  Rapidez en cm/s aproximados, suponiendo una palma de 9.5 cm.
- Ventana de la cámara: flechas amarillas de velocidad en muñeca, puntas
  y codo, y la rapidez de la muñeca de cada mano en el panel de estado.
- Vista 3D: las mismas flechas en 3D (incluyen `vz`) y la rapidez junto a
  cada mano.
- Tecla `v` para mostrar/ocultar las flechas.

### Cambiado: vista 3D (`viewer3d.py`, ahora con OpenCV)
- Estética tipo viewport de Blender: fondo oscuro, piso de referencia,
  gizmo de ejes en la esquina, POV bajo el mouse resaltado.
- Proyección ortográfica; los dedos más cercanos tapan a los lejanos.
- Mismos controles que antes (`1`, `3`, `7`, `9`, `.`, botones de vista,
  Vincular 180, Encuadrar) y nuevos: `l` vincular, `r` reiniciar, `+`/`-`
  y rueda del mouse para zoom. Las teclas funcionan con cualquiera de las
  dos ventanas activa.
- `plot_csv.py --3d` usa el visor nuevo, con `espacio` (pausa), `a`/`d`
  (frame anterior/siguiente), `v` (velocidad) y `q`/`Esc` (salir). Con
  `--frame N` arranca en pausa en ese frame. Recalcula la velocidad al
  leer, así funciona también con CSVs viejos.

### Cambiado: formato del CSV
- Columnas nuevas: `vx`, `vy`, `vz` (anchos de frame por segundo),
  `rapidez_cm_s` y `fuente` (`mediapipe`, `yolo` o `estimado`).
  `plot_csv.py` sigue leyendo todos los formatos anteriores.

## 2026-09-24 (primera parte — versión 24-A)

### Añadido: eje z y vista 3D con dos puntos de vista (POV)
- Nuevo módulo `viewer3d.py`: ventana de matplotlib con **dos vistas 3D
  de la misma escena**, al estilo de los viewports divididos de Blender.
  Se usa una sola cámara física: las dos vistas son dos ángulos del
  mismo gráfico.
  - La tercera dimensión es la `z` de MediaPipe (profundidad relativa a
    la muñeca), que antes se guardaba en el CSV pero no se graficaba.
  - POV 1 arranca desde el lado de la cámara; POV 2, **girado 180° en
    horizontal** (la mano vista desde atrás).
  - Cada vista se gira con el mouse. Teclas tipo numpad de Blender:
    `1` frente, `3` lado, `7` arriba, `9` vista opuesta, `.` encuadrar.
    Botones Frente/Atrás/Lado/Arriba bajo cada vista.
  - Casilla **Vincular 180°** (activa por defecto): al girar una vista, la
    otra la sigue desde el lado opuesto.
  - Casilla **Encuadrar manos** (activa por defecto): los ejes siguen a
    las manos con un encuadre suavizado; desactivada, se ve el frame
    completo con una pirámide que marca la posición de la cámara.
  - Los tres ejes usan la misma escala, así la mano no se deforma al
    girarla. Las líneas y textos se crean una sola vez y solo se les
    cambian los datos, porque borrar y redibujar los ejes en cada frame
    era demasiado lento.
- `Prueba.py` abre el visor en vivo junto a la ventana de la cámara.
  Flags nuevos: `--sin-3d` y `--vista3d-cada N` (default 3, porque
  redibujar los dos ejes 3D cuesta ~90 ms).
- `plot_csv.py --3d`: reproduce un CSV (animado o con `--frame`) en el
  mismo visor de dos POV.

### Añadido: antebrazo con YOLO pose
- Nuevo módulo `forearm.py`: detecta el **codo** con YOLO pose
  (`ultralytics`, modelo `yolo11n-pose.pt`, se descarga solo a `models/`)
  y dibuja el antebrazo (codo → muñeca) en azul (`"forearm"` en
  `hand_style.py`, paleta de Wong) en la vista en vivo, en la 3D y en
  `plot_csv.py`.
  - Se eligió YOLO y no solo OpenCV porque OpenCV no trae un detector de
    codo listo para usar. Corre en ~5 ms por frame con MPS (~20 ms en CPU).
  - Cada mano de MediaPipe se empareja con el brazo de YOLO cuya muñeca
    está más cerca de su landmark 0, sin usar la etiqueta
    izquierda/derecha de YOLO (con la imagen en espejo sale invertida).
  - La **z del codo es una estimación**: se supone un antebrazo de 2.6×
    el largo de la palma y la diferencia con el largo visto en la imagen
    se atribuye a profundidad, suponiendo el codo detrás de la muñeca.
  - El codo se suaviza entre frames para quitar el temblor de YOLO.
- `Prueba.py`: flag `--sin-antebrazo` para no cargar YOLO; el panel de
  estado muestra cuántos antebrazos se detectaron.

### Cambiado: formato del CSV
- Nuevas columnas `img_w`, `img_h` (tamaño del frame), para reconstruir
  la escena 3D con la proporción correcta.
- Si una mano tiene antebrazo, se agrega una fila con
  `landmark_index = 21` (el codo) y su `z` estimada.
- `plot_csv.py` sigue leyendo los CSVs anteriores: sin `img_w`/`img_h`
  asume 1280×720, y sin codo dibuja solo la mano. En 2D ahora dibuja solo
  los landmarks 0–20 como mano y el 21 aparte, como antebrazo.

### Dependencias
- `requirements.txt`: se agregan `ultralytics` (instala `torch`) y
  `matplotlib`, que ya se usaba en `plot_csv.py` pero no estaba listado.
- `.gitignore`: ignora `models/*.pt` (modelo de YOLO).

## 2026-09-23

### Documentación (guía de uso)
- `README.md`: nueva sección **Guía rápida de uso**, paso a paso
  (preparar el entorno, capturar, terminar y guardar, ver la grabación),
  con qué se ve en pantalla, las teclas y una tabla de problemas comunes
  con su solución.

### Añadido (vista en vivo)
- **Panel de estado (HUD)** en la esquina superior izquierda de
  `Prueba.py`: FPS reales (suavizados), manos detectadas en el frame,
  frames con manos ya grabados para el CSV y las teclas disponibles.
- **Controles de teclado:**
  - `n`: mostrar/ocultar los nombres de los dedos (útil cuando se
    enciman con el puño cerrado o la mano de perfil).
  - `s`: guardar una foto del frame actual (con el esqueleto dibujado,
    sin el panel de estado) en `capturas/screenshot_<fecha>.png`.
  - `q`: salir y exportar el CSV (sin cambios).
- `.gitignore` ignora también las fotos (`capturas/*.png`).

### Corregido
- **Bug: `Left`/`Right` salían invertidas.** Como el frame se voltea
  (efecto espejo) antes de pasarlo a MediaPipe, la mano derecha real se
  etiquetaba `Left` y viceversa, tanto en la vista en vivo como en el CSV.
  `Prueba.py` ahora corrige la lateralidad cruda (`_swap_handedness`)
  antes del `HandTracker`. Los CSVs grabados antes de este fix se pueden
  graficar corregidos con `plot_csv.py --swap-hands`.

### Cambiado
- **Cada dedo se etiqueta con su nombre** (`Pulgar`, `Índice`, `Medio`,
  `Anular`, `Meñique`) en la punta, en lugar de la inicial en inglés
  (`T`/`I`/`M`/`R`/`P`). Se quitaron los índices numéricos (0–20) del
  resto de los landmarks, que saturaban la vista. En la vista en vivo el
  nombre va sin acentos (`Indice`, `Menique`) porque las fuentes de
  OpenCV solo soportan ASCII. La leyenda de `plot_csv.py` también usa los
  nombres en español.

- **Bug: las manos no se reconocían bien.** MediaPipe perdía o tardaba en
  reconocer la mano con cámaras que abrían a baja resolución (muchas
  webcams por defecto abren a 640×480) y con los umbrales de confianza
  fijos en el código (no ajustables sin editar `Prueba.py`). Corregido:
  - `Prueba.py` ahora pide explícitamente una resolución de captura más
    alta a la cámara (`--cam-width`/`--cam-height`, default `1280x720`);
    si la cámara no la soporta, `cv2` ignora el pedido sin fallar.
  - Los tres umbrales de confianza del detector
    (`min_hand_detection_confidence`, `min_hand_presence_confidence`,
    `min_tracking_confidence`) dejaron de estar fijos en `0.5` dentro del
    código y ahora son flags de línea de comandos
    (`--min-detection-confidence`, `--min-presence-confidence`,
    `--min-tracking-confidence`), para poder ajustarlos según
    iluminación/cámara sin tocar el script.

### Añadido
- **Identificación de cada dedo.** Nuevo módulo `hand_style.py`,
  compartido entre `Prueba.py` y `plot_csv.py`, que define una paleta de
  color por dedo (pulgar, índice, medio, anular, meñique) en vez de un
  único color por mano. Las puntas de los dedos (landmarks 4, 8, 12, 16,
  20) se dibujan más grandes, con un aro blanco de resalte y la inicial
  del dedo (`T`/`I`/`M`/`R`/`P`) al lado; el resto de los landmarks
  conserva su índice numérico (0–20) como antes.
- La paleta usada es la paleta categórica de Wong (2011), pensada para
  seguir siendo distinguible bajo las formas más comunes de daltonismo
  (protanopía/deuteranopía), no solo por separación de matiz.
- `plot_csv.py` ahora distingue `Left`/`Right` por estilo de línea
  (punteado vs. sólido) en vez de por color, ya que el color pasó a
  identificar el dedo; la leyenda muestra ambas claves (dedo y
  lateralidad).

### Cambiado (gráfico)
- Vista en vivo (`Prueba.py`):
  - Líneas y círculos con antialiasing (`cv2.LINE_AA`) en vez de trazo
    "escalonado".
  - Cada conexión se dibuja con un trazo oscuro debajo del color para
    que se vea nítida tanto sobre fondos claros como oscuros (piel,
    ropa, iluminación variable).
  - La etiqueta `Left/Right #id` ahora tiene un fondo oscurecido detrás
    del texto para que se lea sobre cualquier color de fondo, en vez de
    texto plano sobre el video.
- Reproductor de CSV (`plot_csv.py`):
  - Puntas de dedo más grandes que el resto de los landmarks, igual que
    en la vista en vivo, para que ambas vistas se vean consistentes.
  - Leyenda combinada de dedo (color) + lateralidad (estilo de línea).

### Documentación
- `README.md` actualizado: nueva sección de identificación por dedo,
  tabla de colores, documentación de los flags nuevos de `Prueba.py`, y
  fecha de última actualización.
- Este `CHANGELOG.md`, para llevar un registro fechado de errores,
  cambios y mejoras hacia adelante.

## Sin fecha registrada (versión previa a este changelog)

Funcionalidad ya existente antes de empezar a llevar este changelog,
documentada aquí como referencia de partida:

- Captura en vivo con `HandLandmarker` (Tasks API) en modo `VIDEO`,
  hasta `--max-hands` manos simultáneas (default 4).
- `HandTracker`: id de track persistente por mano física + estabilización
  de `Left`/`Right` por voto ponderado sobre una ventana de 15 frames,
  para evitar el parpadeo de lateralidad que MediaPipe reclasifica
  cuadro a cuadro.
- Export a CSV (`capturas/hand_data_<fecha>.csv`) con una fila por
  landmark por mano por frame.
- `plot_csv.py`: reproduce/anima un CSV ya guardado con `matplotlib`,
  sin necesidad de cámara.
- Fijado a `mediapipe==0.10.35` por un bug de macOS/Apple Silicon en las
  versiones `1.0.0`/`1.0.1` (`google-ai-edge/mediapipe#6356`).
