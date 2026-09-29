# Revisiones — HandMotion3D

Registro de las revisiones hechas al proyecto: qué se revisó, qué se encontró, qué se corrigió y qué queda pendiente. El detalle de cada cambio está en [`CHANGELOG.md`](CHANGELOG.md); los comandos ejecutados, en [`COMANDOS.md`](COMANDOS.md#3-bitácora-de-mantenimiento).

| # | Fecha | Alcance | Resultado |
|---|-------|---------|-----------|
| 1 | 2026-09-28 | Documentación contra el código | 10 errores de documentación corregidos, 35 funciones sin docstring |
| 2 | 2026-09-28 (28-E) | Todo el código y la forma de trabajar | 4 errores corregidos, 3 temas de proceso anotados |
| 3 | 2026-09-28 (28-F) | Pasar las comprobaciones al repositorio | 1 error de `estereo.py` y 1 prueba irreal encontrados y corregidos |

Estado actual de todo lo pendiente: [al final](#estado-de-los-pendientes).

---

## Revisión 1 — documentación contra el código

Se leyó el README, el CHANGELOG y todos los módulos, y se comparó cada afirmación con lo que hace el código.

| Encontrado | Corrección |
|------------|------------|
| *Instalación* decía `./venv/bin/pip install` justo debajo de la nota que explica por qué no usarlo | `./venv/bin/python3 -m pip` |
| La fila "Va lento" de *Problemas comunes* estaba dos veces | Unificada |
| *Qué hace* de la captura describía el programa anterior a la 24-A (sin codo, velocidad ni 3D; solo `q` para salir) | Reescrita |
| El panel de estado no mencionaba la fila de velocidad por dedo | Agregada |
| *Velocidad → Dónde se ve* no nombraba `rapidez_rel_cm_s` | Agregada |
| "Tres versiones" el 2026-09-24; fueron cinco | Corregido |
| La tecla `=` (zoom) no estaba documentada | Agregada |
| El resumen del historial no mencionaba 24-D ni 24-E | Actualizado |
| La entrada 24-E del CHANGELOG daba reglas de `.gitignore` distintas a las reales | Corregidas |
| 35 funciones y clases sin docstring | Documentadas las que tienen lógica propia; en la revisión 3 se completaron las restantes |

## Revisión 2 — código completo y forma de trabajar (versión 28-E)

Se leyó todo el código después de implementar 28-A a 28-D, y se probó con cámaras y MediaPipe simulados.

### Errores encontrados y corregidos

| Error | Consecuencia | Corrección |
|-------|--------------|------------|
| Timestamps con `time.time()` (hora del sistema) | Si la hora se ajustaba hacia atrás (sincronización por red), MediaPipe fallaba a mitad de la sesión: en modo `VIDEO` exige timestamps crecientes | `time.monotonic()` y timestamp siempre ≥ anterior + 1 ms |
| Dos sesiones iniciadas en el mismo segundo generaban el mismo nombre de CSV | La segunda **pisaba** a la primera sin avisar | Sufijo `_2`, `_3`… |
| Si la cámara dejaba de entregar imágenes, el bucle terminaba en silencio | Parecía un cierre inexplicable | Mensaje `La cámara dejó de entregar imágenes` |
| Título de ventana `MediaPipe Hands` | Nombre viejo del proyecto | `HandMotion3D - Camara` |

Durante la misma implementación también se corrigieron problemas de diseño, cada uno en su versión:

| Problema | Versión |
|----------|---------|
| Solo `mediapipe` tenía versión fija; `opencv-python` y `opencv-contrib-python` podían quedar en versiones distintas y pisarse en `cv2/` | 28-A |
| El CSV se acumulaba en memoria y se escribía al salir (RAM creciente; una caída perdía todo) | 28-B |
| Palma fija de 9.5 cm: con otra palma, todas las velocidades desviadas en la misma proporción | 28-B |
| Con estéreo, si la cámara 2 perdía la mano, la escala saltaba entre la palma medida y la supuesta (picos falsos de velocidad) | 28-D (`known_palm`) |

### Revisado sin cambios

`HandTracker` (emparejamiento, envejecimiento de tracks, voto de lateralidad), `forearm.py` (emparejamiento con YOLO, memoria de 10 frames, codo estimado), `viewer3d.py` (proyección, encuadre, mouse, teclas) y la lectura de CSVs en `plot_csv.py`, probada con CSVs reales del 2026-09-18 (formato con `hand_index`) y del 2026-09-24.

### Forma de trabajar (proceso)

| Tema | Qué pasaba | Estado |
|------|------------|--------|
| Línea `Co-Authored-By` en 5 commits | GitHub mostraba a un asistente de IA como colaborador | **Resuelto en la 28-F**: historial reescrito (ver [COMANDOS.md](COMANDOS.md#2026-09-28--versión-28-f-quitar-la-línea-co-authored-by-del-historial)) |
| Comprobaciones con scripts sueltos | Los números "comprobado con datos simulados" (24-D, 28-B a 28-D) no se podían repetir | **Resuelto en la 28-F**: [`pruebas/`](pruebas/README.md) |
| Sin pruebas con hardware | Nada de 28-B a 28-D se probó con cámaras reales | **Pendiente** |

## Revisión 3 — al pasar las comprobaciones al repositorio (versión 28-F)

Al convertir los scripts sueltos en [`pruebas/`](pruebas/README.md), con posiciones de mano distintas y comprobaciones con tolerancias, aparecieron dos problemas que las pruebas originales no mostraban.

### 1. Puntos fuera de la imagen mal triangulados (`estereo.py`)

- **Síntoma:** una mano a 45 cm salía con un punto a **6.45 cm** de su lugar real, aunque el error de reproyección medio era bajo (1.08 px), así que el emparejamiento la aceptaba.
- **Causa:** parte de la mano quedaba fuera de la imagen de la cámara 2 (un punto en x = −506 px). Fuera de la imagen, el modelo de distorsión del lente que se ajustó en la calibración no vale, y el punto triangulado se corre. MediaPipe devuelve puntos así (los extrapola) cuando un dedo se sale del cuadro, así que pasaría con cámaras reales.
- **Corrección:** solo se triangulan los puntos que están **dentro de las dos imágenes**. Los de afuera conservan la `z` de MediaPipe y quedan sin `x_cm`/`y_cm`/`z_cm`. Hace falta la muñeca y al menos 8 puntos visibles (`MIN_VISIBLE_POINTS`), y la palma solo se mide si también se ve el nudillo del medio.
- **Matiz medido:** con dedos **apenas** afuera, triangular igual daba poco error (0.46 cm en una prueba). El problema grave aparece con puntos lejos del borde. Se eligió el criterio conservador (margen 0, `INSIDE_MARGIN_FRAC`) porque perder la medición de un dedo que se sale es mejor que guardar una posición corrida varios cm sin aviso.

### 2. La simulación de punta a punta era irreal

- La cámara 2 simulada seguía "viendo" la mano aunque estuviera fuera de su imagen. Una cámara real no la detectaría.
- Por eso los números de la 28-D en el README (palma 9.12 cm, error 0.9 cm) salían en parte de puntos que ninguna cámara real vería.
- **Corrección:** la cámara 2 simulada no detecta la mano si su muñeca queda fuera de la imagen, y el recorrido de la mano simulada va por la zona que ven las dos cámaras, con dedos saliéndose en los extremos. Los números se volvieron a medir y se actualizaron en README y CHANGELOG.

### Números antes y después

| Medición | 28-D (prueba irreal) | 28-F |
|----------|----------------------|------|
| Mano a 45 cm, palma de 9.0 cm | palma 9.12, error máx. 0.91 cm (parte de la mano fuera de la cámara 2) | palma 9.01, error máx. **0.45 cm** (mano entera en las dos) |
| Mano con 5 puntos fuera de la cámara 2 | (no se probaba) | 15 puntos triangulados, error máx. **0.27 cm**; palma 9.04 |
| Mano con puntos lejos de la imagen | (no se probaba) | triangulando todo: 2.58–6.45 cm de error; ahora esos puntos no se triangulan |
| Captura `--estereo`, mano de 8.5 cm a 20 cm/s | palma 8.48–8.52, 19.9 cm/s | palma 8.49–8.53, 20.1 cm/s, 45.0 cm |

---

## Estado de los pendientes

| Pendiente | Desde | Estado |
|-----------|-------|--------|
| Quitar `Co-Authored-By` de los commits viejos | Rev. 2 | ✅ Hecho (28-F) |
| Pasar las comprobaciones al repositorio | Rev. 2 | ✅ Hecho (28-F), como scripts; convertirlas a `pytest` + CI queda opcional |
| Probar `captura.py` en vivo tras 28-A…28-F | Rev. 2 | ⏳ Pendiente: con la webcam, `--palma-cm` y la velocidad |
| Probar `estereo.py calibrar` y `--estereo` con dos webcams reales | Rev. 2 | ⏳ Pendiente: comparar la distancia entre cámaras con una regla |
| Renombrar el repositorio de GitHub a `HandMotion3D` | 24-E | ⏳ Pendiente: sigue llamándose `Machine_Learning` (pasos en [COMANDOS.md](COMANDOS.md#pendiente-nombre-del-repositorio-en-github)) |
| Borrar la rama local `respaldo-historial-con-coautor` | 28-F | ⏳ Cuando se confirme que el historial nuevo está bien |
| Triangular también el codo (YOLO en las dos cámaras) | 28-D | 💡 Mejora futura |
| Acentos en las ventanas de OpenCV (`Índice`, `Meñique`) | 2026-09-23 | 💡 Mejora futura (dibujar el texto con Pillow) |
