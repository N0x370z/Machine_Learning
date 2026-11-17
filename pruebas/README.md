# Pruebas — HandMotion3D

Pruebas que se corren **sin cámara ni pantalla**: reemplazan las webcams, las ventanas y (en una de ellas) el detector de MediaPipe por simulaciones de resultado conocido, y comparan lo que mide el programa con ese resultado. De aquí salen todos los números de precisión que aparecen en el [README](../README.md) y el [CHANGELOG](../CHANGELOG.md).

```bash
./venv/bin/python3 pruebas/correr_todo.py      # las cinco, con resumen (~1 min)
```

Cada script imprime `OK` o `FALLA` en cada comprobación y termina con `RESULTADO: OK` (código de salida 0) o `RESULTADO: FALLA` (código 1).

> Hasta la versión 28-E estas comprobaciones se hacían con scripts sueltos fuera del repositorio, así que los números documentados no se podían repetir. Desde la **28-F** viven aquí. Al pasarlas se encontraron dos problemas (ver "Qué se encontró al pasarlas aquí" abajo).

## Qué comprueba cada una

### `filtro_velocidad.py` — filtro One Euro (28-C)

Compara la media exponencial de antes (`VELOCITY_SMOOTHING = 0.35`) con el filtro One Euro de `kinematics.py` en cinco situaciones simuladas (30 FPS con variación, temblor gaussiano, 4 corridas), con dos niveles de temblor.

| Comprobación | Condición |
|--------------|-----------|
| Menos ruido con la mano quieta | p95 de One Euro < p95 de la media exponencial |
| Menos retraso al arrancar | tiempo al 90 % de One Euro < el de la media exponencial |
| No pierde golpeteos rápidos | pico medido a 4 Hz ≥ el de antes − 5 puntos |
| Huecos | tras 0.5 s sin ver el punto, la velocidad vuelve a 0 |

Con `--buscar` prueba además las 72 combinaciones de parámetros con las que se eligieron `EURO_MIN_CUTOFF`, `EURO_BETA` y `EURO_D_CUTOFF`.

### `estereo_simulado.py` — dos cámaras (28-D)

Inventa un par de cámaras (lentes con distorsión, separadas 18 cm, la segunda girada 12°) con parámetros conocidos.

| Comprobación | Tolerancia |
|--------------|------------|
| Calibración con 18 tableros (0.2 px de ruido): distancia entre cámaras, traslación, error RMS | ±0.2 cm, ±0.3 cm, < 0.5 px |
| Guardar y leer la calibración (`.npz`) | Mismos valores |
| Dos manos enteras en las dos imágenes (a 45 y 60 cm, 1 px de ruido, orden cruzado): palma, distancia, posición | ±0.3 cm, ±1 cm, error máx. < 1.5 cm |
| `z` en la convención de MediaPipe | < 0.03 anchos de frame |
| Mano con **algunos dedos** fuera de la imagen de la cámara 2 | Esos puntos sin cm; los demás con error < 1.5 cm |
| Mano con puntos **lejos** de la imagen de la cámara 2 | No produce puntos con error > 1.5 cm |
| La cámara 2 ve una sola mano / ninguna; resolución distinta a la calibración | Se triangula solo la que se ve / ninguna / error claro |

### `captura_simulada.py` — de punta a punta (28-B, 28-D, 28-E, 19-A, 17-B, 17-C, 17-D)

Corre el `main()` real de `captura.py` con cámaras que devuelven imágenes negras, ventanas que no se abren (y un `waitKey` que "presiona" teclas en frames fijos) y un `HandLandmarker` que devuelve una mano sintética: palma de 8.5 cm, a 45 cm, yendo y viniendo a 20 cm/s. Todo lo demás es el código real: tracker, `estereo.py`, YOLO (si `models/yolo11s-pose.pt` ya está descargado), velocidad, visor 3D y `CsvRecorder`. Los CSV van a una carpeta temporal, no a `capturas/`.

| Caso | Qué se espera |
|------|---------------|
| Una cámara, palma por defecto (9.5) | ~22 cm/s: sale ~12 % alta porque la palma real es 8.5 |
| `--palma-cm 8.5` | 20 ± 1 cm/s |
| `--estereo` (con YOLO y visor 3D) | Palma medida 8.5 ± 0.2, 20 ± 1 cm/s, distancia 45 ± 0.5 cm, `fuente = estereo` |
| La cámara 2 ve la mano de a ratos | Mediana 20 ± 1 cm/s y p95 < 30 (sin picos por cambio de escala) |
| La cámara 2 nunca la ve | Vuelve a una cámara, palma 9.5 |
| CSV durante la sesión | En el frame 50 el archivo ya tiene > 50 KB |
| `Ctrl+C` en el frame 30 | Las 30 × 21 filas guardadas |
| Sin manos | No se crea CSV |
| Dos sesiones seguidas | Dos archivos distintos (no se pisan) |
| `plot_csv.py --3d` con ese CSV | Usa la palma guardada (8.5); `--palma-cm 10` la reemplaza |
| `plot_csv.py --frame 3` (2D) | Sin errores |
| **Pausa** (19-A): espacio en el frame 20, de nuevo en el 40 | El CSV queda con 50 frames seguidos (sin huecos de `frame`) y a Unreal no llega nada mientras dura |
| **Unreal** (19-A): `--unreal` a un receptor de prueba | Un mensaje de fotograma por frame y uno por mano, con 87 floats; la muñeca relativa es el origen |
| Tecla `u` (19-A) | Pausa y reanuda el envío (30 de 50 fotogramas) sin dejar de grabar |
| Tecla `e` (17-B) | Los dos CSV para artículos en `articulos/`, con lo grabado hasta ese momento (30 frames) y sin parar; `plot_csv.py` no los toma por una captura |
| `e` dos veces, en pausa, sin datos (17-B) | Reemplaza con lo de la segunda (45) / los 10 frames grabados / no se crea nada y no se cae |
| Tecla `m` (17-B) | Ya no exporta nada (era el Excel de medicina) |
| `--video` (17-C): video simulado de 90 fotogramas a 120 FPS, analizado ~3 veces más lento | Los 90 fotogramas, tiempo del video (último a 742 ms), 20 ± 1 cm/s, pausa sin saltos (≤ 9 ms); video inexistente y `--video --estereo` dan error claro |
| `.json` de la sesión (17-D) | Fuente, huella SHA-256, FPS, duración y motivo del fin con video; participante, notas, versión, commit y librerías en vivo; `estado: error` si el programa falla; sin manos no se crea; el participante llega al CSV de medicina (tecla `e` y `exportar_csv.py`) |
| `plot_csv.py --3d`: espacio y `p` (19-A) | Se repite el frame con `[pausa]` mientras dura |

### `exportar_csv_simulado.py` — CSV para artículos (17-B)

Arma CSV de captura con rapideces de valor conocido, exporta los dos formatos y compara **cada número** con numpy. Reemplaza a `excel_simulado.py` (19-A), que necesitaba LibreOffice para recalcular las fórmulas.

| Comprobación | Tolerancia |
|--------------|------------|
| Dos archivos en `articulos/`; columnas de cada formato (en ASCII); 12 series por defecto, 27 con `--todos-los-puntos`; orden | Exacto |
| Ingeniería: media, RMS, σ (n−1) y pico (m/s); N, T, f_s; palma, profundidad, resolución | < 0.00006 m/s (redondeo a 4 decimales); f_s ± 0.05 Hz |
| Medicina: media, DE, mediana, Q1, Q3, mín, máx (cm/s) y los textos «media (DE)» y «mediana [Q1-Q3]» | < 0.006 cm/s (redondeo a 2 decimales); texto idéntico |
| Cuartiles con el método inclusivo (`QUARTILE` de Excel) | 1..10 → Q1 = 3.25, Q3 = 7.75 |
| `--participante`, `--formato medicina` | Columna llena; un solo archivo |
| Dos manos en estéreo con la palma medida cada fotograma (revisión 5) | Cada mano con la mediana de su palma (± 0.02 cm) |
| Punto visto una vez; CSV de antes de la 24-A; formato desconocido; sin filas; no existe; fila final cortada; exportar dos veces | DE/σ/f_s vacías sin error; error claro (×4); se salta la fila; reemplaza sin `.tmp` sueltos |

### `unreal_simulado.py` — puente a Unreal Engine (19-A)

| Comprobación | Condición |
|--------------|-----------|
| OSC | Bytes de un mensaje conocido; ida y vuelta con int, float, string con acento y vacío; tipo no soportado → `TypeError` |
| Flexión | Dedo estirado 0°, a 90°, doblado sobre sí mismo 180°; puntos repetidos no fallan |
| Ejes | Escena (x der, y abajo, z lejos) → Unreal (X adelante, Y der, Z arriba) en cm; muñeca absoluta con estéreo; codo relativo |
| Formato | 87 floats en el orden de `FLOAT_LAYOUT`; solo floats; < 1400 bytes por mensaje |
| UDP | Un mensaje de fotograma + uno por mano; sin manos solo el de fotograma; sin receptor no se cae |
| Destino y demo | `host:puerto` en 4 formas y 3 inválidas; la mano de `--demo` (17-A): abierta, ninguna articulación pasa de 15°; cerrada, cada articulación llega a su flexión máxima (±2°); la palma mide lo que dice `palm_cm` |

## Qué se encontró al pasarlas aquí (28-F)

1. **Puntos fuera de la imagen mal triangulados.** Con una mano en otra posición, un punto salía con 6.45 cm de error aunque el error de reproyección medio era bajo (1.08 px): la mano quedaba en parte fuera de la imagen de la cámara 2 (hasta x = −506 px), donde el modelo de distorsión del lente no vale. MediaPipe devuelve puntos así cuando un dedo se sale del cuadro. `estereo.py` ahora solo triangula los puntos que están dentro de las dos imágenes (ver `MIN_VISIBLE_POINTS`, `INSIDE_MARGIN_FRAC`).
2. **La simulación de punta a punta era irreal.** La cámara 2 simulada seguía "viendo" la mano aunque estuviera fuera de su imagen, y los números del README de la 28-D (palma 9.12 cm, error 0.9 cm) salían en parte de esos puntos. Ahora la cámara 2 simulada no detecta la mano si la muñeca está fuera de su imagen, como MediaPipe real, y los números se volvieron a medir.

## Lo que estas pruebas NO cubren

- **Unreal Engine**: se comprueba lo que Python manda, no que Unreal lo reciba ni cómo se ve el modelo (ver [`UNREAL.md`](../UNREAL.md)).
- **Programas de estadística**: los CSV para artículos se leen con el módulo `csv` de Python (y con pandas si está instalado), no con R, SPSS ni Excel.
- **Requisito:** `captura_simulada.py` necesita que exista `models/hand_landmarker.task` (aunque MediaPipe esté simulado). En un clon limpio, descárgalo (README, paso 1) o crea un archivo vacío con ese nombre.
- **Cámaras reales**: el temblor real de MediaPipe, la luz, la sincronización entre dos webcams y la calibración con un tablero impreso. Hay que probarlo a mano (ver [`COMANDOS.md`](../COMANDOS.md)).
- **Las ventanas**: el dibujo se hace, pero nadie lo mira; los errores visuales (texto encimado, colores) no se detectan.
- **YOLO sobre personas reales**: con imágenes negras YOLO no encuentra a nadie, así que solo se prueba el codo **estimado**.
