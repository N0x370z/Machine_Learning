# Pruebas — HandMotion3D

Pruebas que se corren **sin cámara ni pantalla**: reemplazan las webcams, las ventanas y (en una de ellas) el detector de MediaPipe por simulaciones de resultado conocido, y comparan lo que mide el programa con ese resultado. De aquí salen todos los números de precisión que aparecen en el [README](../README.md) y el [CHANGELOG](../CHANGELOG.md).

```bash
./venv/bin/python3 pruebas/correr_todo.py      # las tres, con resumen (~30 s)
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

### `captura_simulada.py` — de punta a punta (28-B, 28-D, 28-E)

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

## Qué se encontró al pasarlas aquí (28-F)

1. **Puntos fuera de la imagen mal triangulados.** Con una mano en otra posición, un punto salía con 6.45 cm de error aunque el error de reproyección medio era bajo (1.08 px): la mano quedaba en parte fuera de la imagen de la cámara 2 (hasta x = −506 px), donde el modelo de distorsión del lente no vale. MediaPipe devuelve puntos así cuando un dedo se sale del cuadro. `estereo.py` ahora solo triangula los puntos que están dentro de las dos imágenes (ver `MIN_VISIBLE_POINTS`, `INSIDE_MARGIN_FRAC`).
2. **La simulación de punta a punta era irreal.** La cámara 2 simulada seguía "viendo" la mano aunque estuviera fuera de su imagen, y los números del README de la 28-D (palma 9.12 cm, error 0.9 cm) salían en parte de esos puntos. Ahora la cámara 2 simulada no detecta la mano si la muñeca está fuera de su imagen, como MediaPipe real, y los números se volvieron a medir.

## Lo que estas pruebas NO cubren

- **Cámaras reales**: el temblor real de MediaPipe, la luz, la sincronización entre dos webcams y la calibración con un tablero impreso. Hay que probarlo a mano (ver [`COMANDOS.md`](../COMANDOS.md)).
- **Las ventanas**: el dibujo se hace, pero nadie lo mira; los errores visuales (texto encimado, colores) no se detectan.
- **YOLO sobre personas reales**: con imágenes negras YOLO no encuentra a nadie, así que solo se prueba el codo **estimado**.
