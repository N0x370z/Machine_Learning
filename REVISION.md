# Revisiones — HandMotion3D

Registro de las revisiones hechas al proyecto: qué se revisó, qué se encontró, qué se corrigió y qué queda pendiente. El detalle de cada cambio está en [`CHANGELOG.md`](CHANGELOG.md); los comandos ejecutados, en [`COMANDOS.md`](COMANDOS.md#3-bitácora-de-mantenimiento).

| # | Fecha | Alcance | Resultado |
|---|-------|---------|-----------|
| 1 | 2026-09-28 | Documentación contra el código | 10 errores de documentación corregidos, 35 funciones sin docstring |
| 2 | 2026-09-28 (28-E) | Todo el código y la forma de trabajar | 4 errores corregidos, 3 temas de proceso anotados |
| 3 | 2026-09-28 (28-F) | Pasar las comprobaciones al repositorio | 1 error de `estereo.py` y 1 prueba irreal encontrados y corregidos |
| 4 | 2026-10-19 (19-A) | Pausa, Excel y Unreal Engine (código nuevo) | 4 problemas de diseño corregidos antes de publicar; 5 pendientes anotados |
| 5 | 2026-11-17 (17-A) | Todo lo de la 19-A, con las pruebas en el venv real | 1 error de privacidad y 1 de la mano de `--demo` corregidos; 3 problemas del Excel resueltos al reemplazarlo por CSV (17-B); 2 temas de proceso para decidir |
| 6 | 2026-11-23 (23-A) | Proyecto en Windows, Unreal Engine 5.8 real, panel | 1 error de codificación de los CSV en Windows corregido; 3 hallazgos de Unreal documentados; 2 errores propios corregidos antes de publicar |
| 7 | 2026-11-24 (sin versión nueva) | Documentación de la 17-E contra los hechos; la 23-A y la 23-B en macOS; capturas al repositorio | 4 afirmaciones de la doc corregidas (una quinta ya no aplicaba); 1 mensaje de error con la versión equivocada; nota de apoyo de IA en el README; 14 capturas subidas |

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
| Línea `Co-Authored-By` en 5 commits | GitHub mostraba como colaborador a quien no era autor del proyecto | **Resuelto en la 28-F**: historial reescrito (ver [COMANDOS.md](COMANDOS.md#2026-09-28--versión-28-f-quitar-la-línea-co-authored-by-del-historial)) |
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

## Revisión 4 — pausa, Excel y Unreal Engine (versión 19-A)

Se revisó el código nuevo mientras se escribía y se probó con simulaciones (`pruebas/`). **No se probó con hardware, con Unreal Engine ni con Excel de escritorio.**

### Problemas encontrados y corregidos (antes de publicar la 19-A)

| Problema | Consecuencia | Corrección |
|----------|--------------|------------|
| Tras una pausa, la cámara entrega las imágenes que acumuló | La imagen iría atrasada unos instantes al reanudar | Se descartan 6 fotogramas al reanudar y tras exportar (`drain`) |
| `p` como tecla de pausa en `plot_csv.py` 2D | En matplotlib `p` ya es el paneo: chocaban | En 2D solo `espacio`; `p` solo en las ventanas de OpenCV |
| Mensajes OSC con ints, strings y floats mezclados | En Blueprint el índice de un valor depende de cómo cuente Unreal los argumentos; leer mal los 85 valores | Solo floats (87), con el orden fijo documentado |
| `TEXT(x, "0.0")` para armar «media (DE)» en el Excel | Con Excel en un idioma de coma decimal, el formato `0.0` se interpreta distinto y salen cifras mal formadas | `FIXED(x, 1, TRUE)`, que respeta el idioma |
| Intervalos de confianza y valores p entre fotogramas (idea inicial para medicina) | Fotogramas consecutivos no son independientes: cifras demasiado optimistas | No se calculan; la hoja *Notas estadísticas* explica por qué y qué hacer en su lugar |

### Hallazgo de proceso

- Las pruebas de `captura_simulada.py` exigen `models/hand_landmarker.task` aunque MediaPipe esté simulado, y en un clon limpio fallan con `FileNotFoundError`. Anotado en `pruebas/README.md`.
- La verificación se hizo con Python 3.12 / mediapipe 0.10.33 / OpenCV 4.13 y sin YOLO, no con las versiones fijadas del proyecto: hay que repetirla en el venv real.

## Revisión 5 — la 19-A completa (versión 17-A)

Se leyó todo el código nuevo de la 19-A (`exportar_excel.py`, `unreal_bridge.py`, los cambios de `captura.py` y `plot_csv.py`, las pruebas y `UNREAL.md`) y se corrieron las pruebas en el venv del proyecto.

### Errores encontrados

| # | Gravedad | Error | Consecuencia | Corrección |
|---|----------|-------|--------------|------------|
| 1 | Media | `.gitignore` no ignoraba los `.xlsx` exportados | Un `git add .` subía a GitHub hojas con datos del participante (edad, sexo, condición clínica) | `capturas/*.xlsx` y `capturas/articulos/` (17-A) |
| 2 | Media | `demo_hand()` sobrescribía el nudillo del medio | Con la mano abierta, dedo medio doblado 109° hacia atrás y pulgar a 58°: en Unreal se vería un dedo roto | Mano con proporciones reales y 3 pruebas nuevas (17-A). **Se encontró al dibujar la imagen simulada**, no con la lectura del código |
| 3 | Baja | Largo de palma del Excel = el valor que más se repite | Con `--estereo` la palma se mide en cada fotograma y salía un valor casi al azar; con dos manos se reportaba una sola | Resuelto en la 17-B: mediana de la palma **por mano** |
| 4 | Baja | Formato `0.00` sobre la cantidad de fotogramas | «523.00 fotogramas» | Desaparece con la 17-B (CSV sin formato) |
| 5 | Baja | Comentario de `JOINTS`: floats `[70:85]` | Confunde a quien arme el Blueprint leyendo el código | `[72:87]` (17-A) |
| 6 | Nota | openpyxl no guarda el valor de las fórmulas | Vistas previas (macOS, Drive, pandas) mostraban las celdas vacías | Desaparece con la 17-B (los CSV traen los números ya calculados) |
| 7 | Nota | Exportar congela la captura (2.6 s con 10 min de una mano, medido) y reescribe el archivo anterior sin avisar | La velocidad se reinicia tras el congelamiento; se pierde la exportación anterior | Documentado en la 17-B; el aviso dice que reemplaza la anterior |

### Revisado sin errores

Pausa (último cuadro, descarte de fotogramas, teclas, cerrar en pausa), pausa 2D de `plot_csv.py`, codificador OSC, ejes hacia Unreal (con estéreo `points_cm` ya viene en espejo, igual que con una cámara), flexión, `parse_destino` y las fórmulas del Excel (referencias, `FIXED`, `QUARTILE`, ecuaciones 7-10).

### Pruebas en el venv real

`pruebas/correr_todo.py` con Python 3.14.8, las versiones fijadas y YOLO: **5 de 5 OK**. Cierra el pendiente de la revisión 4. La parte de fórmulas de `excel_simulado.py` se omitió por no tener LibreOffice (y la 17-B elimina el Excel).

### Proceso (para decidir)

| Tema | Qué pasa |
|------|----------|
| Autor del commit de la 19-A | `552d55f` tiene como autor a otra persona, no a Ivan Luna como el resto del historial |
| `Co-Authored-By` | `552d55f` volvió a traer la línea que en la 28-F se quitó de todo el historial; ya está subido a `origin/handmotion3d-19-a`. **Resuelto en la 23-A** (ver abajo) |
| Rama | La 19-A (y la 17-A/17-B) están en la rama `handmotion3d-19-a`; `main` sigue en la 28-F |

## Revisión 6 — Windows, Unreal Engine real y panel (versión 23-A)

Primera revisión en **Windows 11** (Python 3.13.0) y primera con **Unreal Engine** instalado (5.8.4). No había webcam: todo se probó con capturas, simulaciones y Unreal.

### Encontrado y corregido

| Encontrado | Consecuencia | Corrección |
|------------|--------------|------------|
| `captura.py` escribía el CSV sin codificación explícita | En Windows salía en cp1252 (`Muñeca` en un byte) y en macOS en UTF-8; un CSV de la Mac con `Índice` hacía **fallar** `plot_csv.py` en Windows (`UnicodeDecodeError`, byte 0x8D) | UTF-8 al escribir; UTF-8 con `errors="replace"` al leer (`plot_csv.py`, `unreal_bridge.py`); las pruebas también en UTF-8 |
| La imagen de Unreal del README era una simulación y la guía no se había probado | No se sabía si Unreal recibía los datos | Proyecto `unreal/HandMotionUE`, probado en UE 5.8.4: 495 de 495 fotogramas; imágenes reales |

### Hallazgos de Unreal (documentados en `UNREAL.md`)

1. Desde Python, el contenido de un mensaje del plugin OSC llega **vacío** (`FOSCMessage` no expone el paquete como `UPROPERTY`). En Blueprint no pasa. El receptor de Python decodifica el OSC por su cuenta.
2. Un servidor OSC que no queda referenciado lo destruye el recolector de basura a los pocos fotogramas (`Destroying OSC Socket Receiver`). En el Blueprint, guardarlo en una variable.
3. En UE 5.8 el texto de la dirección se obtiene con *Get OSC Address Full Path*.

### Errores propios corregidos antes de publicar

| Error | Corrección |
|-------|------------|
| La primera versión de la prueba de tiempos de `--csv` medía también el tiempo de importar matplotlib (651 ms en vez de 100) | Mide la llegada del primer y el último mensaje |
| En el panel, el campo *Destino* de la captura habría pasado la IP como argumento suelto | Se combina en `--unreal [destino]`; probado contra el `argparse` de cada script |

### Proceso

- Las imágenes de Unreal y del panel se generan **sin ventana** (`docs/imagenes_unreal.py` con `-RenderOffscreen`, `panel.py --captura`): no interrumpen lo que haya en pantalla y se pueden repetir.
- Decisión de la revisión 5: el commit de la 19-A conserva a su autor (Guillermo Campos Salas) y pierde la línea `Co-Authored-By`; la rama se fusiona a `main`. Comandos en [COMANDOS.md](COMANDOS.md#2026-11-23--versión-23-a-windows-panel-y-unreal-probado).

---

## Revisión 7 — documentación de la 17-E, la 23-A/23-B en macOS y capturas (sin versión nueva)

Se empezó el 2026-11-17 en la Mac, justo después de la 17-E, y se quedó sin commit. Mientras tanto, en la PC con Windows se hicieron la 23-A y la 23-B y se reescribió la rama `handmotion3d-19-a` (sin la línea `Co-Authored-By`), así que el `git pull` de la Mac fallaba. Se terminó el 2026-11-24, ya sobre `main` (comandos en [COMANDOS.md](COMANDOS.md#2026-11-24--revisión-7-sincronizar-la-mac-documentación-y-capturas)). En el registro de la Mac se llamaba "revisión 6"; ese número ya lo había tomado la 23-A.

### Documentación de la 17-E contra los hechos

Pedido: documentación correcta, declarando los errores y el apoyo de IA. Se revisaron las afirmaciones del README y de `docs/ARTICULOS.md` (midiendo cuando se podía).

| Afirmación | Problema | Corrección |
|------------|----------|------------|
| Reanalizar un video con la misma versión "obtendrá los mismos números" | No comprobado; MediaPipe/YOLO pueden variar entre equipos | Dice que deberían coincidir o quedar muy cerca, que no está garantizado y que no se midió |
| `shasum -a 256` para macOS **y Linux** | En Linux lo habitual es `sha256sum` | Un comando por sistema |
| "~3 GB libres" | No medido; el venv de macOS ocupa **1.2 GB** (`du -sh venv`) | "~1.5 GB (el entorno ocupa 1.2 GB)"; con torch CUDA ocupa más, sin medir |
| "Tiene que terminar con cinco líneas `OK`" | La salida tiene decenas de `OK` | "Un `RESUMEN` con cinco pruebas, las cinco en `OK`" |
| `git clone` sin rama descargaba la 28-F | Era cierto el 2026-11-17 | **Ya no aplica**: la 23-A fusionó la rama a `main`. Se había agregado `-b handmotion3d-19-a` y se quitó |

Comprobado sin cambios: tamaño del modelo de la mano (~8 MB: 7.8 MB descargados), requisito de Python (≥ 3.12, excepto 3.14.1, según los metadatos de numpy y torchvision), enlaces de todos los `.md`.

**Apoyo de IA:** el README tiene una sección breve, *Apoyo de inteligencia artificial*, que dice que el desarrollo contó con un asistente de IA, que la responsabilidad es del equipo y que las pruebas con hardware y la validación están pendientes. Se descartó un documento más largo de declaración (decisión del dueño).

### La 23-A y la 23-B, probadas en macOS

Se hicieron y probaron en Windows; aquí se repasó el código y se corrió en la Mac (Python 3.14, Apple Silicon):

| Qué | Resultado |
|-----|-----------|
| `pruebas/correr_todo.py` con `requirements.txt` nuevo (PySide6) | 5 de 5 `OK` |
| `panel.py` en macOS (`--captura`, sin ventana) | Abre y dibuja bien; el comando mostrado usa `./venv/bin/python3` |
| `unreal_bridge.py --csv` con los 4 formatos de CSV de `capturas/` (de antes de la 24-A a la 28-D) | Los reproduce todos |
| `exportar_csv.py` con los mismos | Formatos B–D bien; el A (sin velocidad) da un error claro, pero decía "antes de la versión 24-A" y la velocidad llegó en la **24-B**: corregido (también en la prueba) |
| `forearm.py` elige `cuda:0`, luego `mps`, luego CPU | Correcto; en la Mac sigue usando MPS |

Anotado, sin cambiar:
- El botón *Detener* del panel mata el proceso (`kill`). Con `captura.py` el CSV ya está escrito (se graba mientras captura), pero el `.json` de la sesión queda `"en curso"` (sin hora de fin ni resultados). Para cerrar bien, salir con `q` en la ventana de la cámara.
- *Abrir proyecto de Unreal* solo busca Unreal instalado con el Epic Games Launcher **en Windows**; en macOS dice que no lo encontró.

### Capturas al repositorio

Pedido: subir las capturas guardadas para trabajarlas en la PC con Unreal Engine y la RTX 4090. Se subieron las **14** de `capturas/` (2026-09-21 a 2026-10-01, 31 MB, la mayor de 4.6 MB): son pruebas del equipo, sin participantes, sin `.json` ni imágenes. Se agregaron con `git add -f`, **sin cambiar el `.gitignore`**, para que las capturas nuevas (que sí pueden ser de participantes) sigan sin subirse solas. El repositorio es público. Qué tiene cada una y qué se puede hacer con ella: [`capturas/README.md`](capturas/README.md).

**Revisado en Windows (2026-11-24):** las 14 se cargan y se reproducen en Unreal; la tabla es correcta. Faltaba una cosa: cuatro son de antes del arreglo de la lateralidad (`1fa9399`, 2026-09-23 11:59) y `unreal_bridge.py --csv` no tenía cómo invertirla. Se agregó `--swap-hands` (y la casilla en el panel).

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
| Correr `pruebas/correr_todo.py` en el venv del proyecto tras la 19-A (versiones fijadas, con YOLO) | Rev. 4 | ✅ Hecho (rev. 5): 5 de 5 OK |
| Probar la pausa, `e` (CSV para artículos, 17-B) y `--unreal` en vivo con la webcam | Rev. 4 | ⏳ Pendiente |
| Abrir los `.xlsx` en Excel de escritorio (las fórmulas solo se comprobaron con LibreOffice) y revisar el formato contra las normas de la revista elegida | Rev. 4 | ➖ Ya no aplica: el Excel se quitó en la 17-B. Queda revisar los dos CSV contra las normas de la revista elegida |
| Armar el Blueprint en Unreal Engine con `unreal_bridge.py --demo` y confirmar nodos de OSC y eje de giro de los dedos (`UNREAL.md`) | Rev. 4 | 🟡 En parte (rev. 6): Unreal 5.8 recibe y mueve la mano con el proyecto `unreal/HandMotionUE` (Python); nodos de OSC revisados contra el código del plugin. Falta el Blueprint y el eje de giro de los dedos de un modelo con piel |
| Validar la rapidez contra una referencia antes de publicar cifras (captura de movimiento, goniómetro, sensores) | Rev. 4 | ⏳ Pendiente |
| Mandar a Unreal la orientación de la muñeca (cuaternión) | Rev. 4 | 💡 Mejora futura |
| Decidir el autor y la línea `Co-Authored-By` del commit `552d55f` (19-A) y cuándo fusionar `handmotion3d-19-a` a `main` | Rev. 5 | ✅ Hecho (23-A): se quitó la línea, Guillermo Campos Salas sigue como autor; fusionado a `main` el 2026-11-23 |
| Probar `--video` con videos reales (celular con FPS variable, `.mov` de iPhone, video en espejo) y comparar Left/Right con lo que se ve | 17-C | ⏳ Pendiente (solo se probó con un mp4 generado y con simulaciones) |
| Probar en Windows con una webcam real (captura, `--unreal` en vivo, el panel con cámara) | Rev. 6 | ⏳ Pendiente (no había webcam el 2026-11-23) |
| torch con CUDA en Windows, para que YOLO use la tarjeta NVIDIA | Rev. 6 | ✅ Hecho (23-B): 7.6 ms por fotograma en la RTX 4090 (36.9 en CPU); `forearm.py` no elegía CUDA y se corrigió |
| Grabar capturas reales en Windows y regenerar las imágenes de Unreal con una mano real (`docs/imagenes_unreal.py`) | Rev. 6 | ⏳ Pendiente (las de hoy usan el ejemplo simulado). Desde la revisión 7 hay 14 capturas reales en el repositorio: se pueden regenerar sin grabar ([`capturas/README.md`](capturas/README.md#en-la-pc-con-unreal-y-la-4090)) |
| Revisión por una persona experta (estadística y del área) de las decisiones metodológicas de `docs/ARTICULOS.md` (propuestas con apoyo de IA) | Rev. 7 | ⏳ Pendiente |
| Medir cuánto ocupa el entorno con torch CUDA (para el requisito de espacio del README) | Rev. 7 | ⏳ Pendiente (en la PC con la 4090: `du` o *Propiedades* de `venv`) |
| *Detener* en el panel deja el `.json` de `captura.py` en `"en curso"`: cerrar con un aviso al proceso en lugar de matarlo | Rev. 7 | 💡 Mejora futura |
