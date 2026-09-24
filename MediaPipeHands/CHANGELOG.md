# Changelog

Historial de cambios del proyecto. Formato libre pero cronológico
(más reciente arriba), en español porque así está el resto del repo.

## 2026-09-24 (segunda parte: correcciones tras la primera prueba con cámara)

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

## 2026-09-24 (primera parte)

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
