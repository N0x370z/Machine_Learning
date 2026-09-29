# Changelog — HandMotion3D (antes MediaPipeHands)

Historial de cambios del proyecto. Formato libre pero cronológico
(más reciente arriba), en español porque así está el resto del repo.

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
- Los commits desde `b960527` hasta `a2ef70f` llevan una línea
  `Co-Authored-By` de un asistente. Desde ahora los commits van solo a
  nombre del autor. Quitarla de los commits viejos requiere reescribir el
  historial (`git push --force`), así que queda a decisión del autor.
- Las comprobaciones "con datos simulados" (24-D y las de hoy) se
  hicieron con scripts sueltos que no quedaron en el repositorio. Pasarlas
  a tests (`pytest`) permitiría repetirlas en cada cambio.
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
  GitHub redirige la URL vieja).
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
