# Changelog

Historial de cambios del proyecto. Formato libre pero cronológico
(más reciente arriba), en español porque así está el resto del repo.

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
