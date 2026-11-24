# Capturas guardadas en el repositorio

`capturas/` **no se sube a git** por defecto (`.gitignore`): ahí quedan los CSV, los `.json` de sesión y los resultados para artículos, que pueden tener datos de participantes. Las 14 capturas de esta tabla son la excepción: se subieron el **2026-11-24** con `git add -f` para trabajarlas en la PC con **Unreal Engine** y la **RTX 4090**.

- Son **pruebas del propio equipo**: no hay participantes, no hay columna `participante`, no hay `.json` de sesión (son de antes de la 17-D) ni imágenes. Solo coordenadas de los puntos de la mano.
- El repositorio es **público**: lo que se suba aquí lo puede ver cualquiera.
- Las capturas **nuevas siguen sin subirse** solas. Para subir otra, hay que pedirlo a propósito: `git add -f capturas/hand_data_<fecha>_<hora>.csv` (y, si es de un participante, comprobar antes que el consentimiento lo permite).

## Qué hay

El nombre lleva la fecha y hora de inicio. "Fotogramas" son los que tienen al menos una mano; la duración va del primero al último.

| Archivo | Formato | Fotogramas | Duración | Resolución | Palma (cm) |
|---------|:-------:|-----------:|---------:|:----------:|:----------:|
| `hand_data_20260921_120519.csv` | A | 150 | 9.7 s | — | — |
| `hand_data_20260921_120603.csv` | A | 200 | 11.1 s | — | — |
| `hand_data_20260923_115410.csv` | A | 98 | 6.4 s | — | — |
| `hand_data_20260923_115658.csv` | A | 192 | 11.1 s | — | — |
| `hand_data_20260923_120818.csv` | A | 536 | 21.8 s | — | — |
| `hand_data_20260924_110548.csv` | A | 184 | 9.9 s | — | — |
| `hand_data_20260924_122925.csv` | A | 445 | 19.9 s | — | — |
| `hand_data_20260924_125327.csv` | A | 681 | 25.3 s | — | — |
| `hand_data_20260924_125606.csv` | A | 895 | 37.5 s | — | — |
| `hand_data_20260924_133351.csv` | B | 438 | 29.5 s | 1280×720 | — |
| `hand_data_20260924_134038.csv` | B | 215 | 14.3 s | 1280×720 | — |
| `hand_data_20260924_135051.csv` | C | 470 | 31.3 s | 1280×720 | — |
| `hand_data_20260929_100851.csv` | D | 182 | 12.1 s | 1280×720 | 9.5 |
| `hand_data_20261001_105542.csv` | D | 205 | 20.2 s | 1280×720 | 8.5 |

Formatos (el CSV fue ganando columnas con las versiones; detalle de cada columna en [docs/TECNICO.md](../docs/TECNICO.md#formato-del-csv-exportado)):

| Formato | Versión | Columnas |
|:-------:|---------|----------|
| A | antes de la 24-A | `frame, timestamp_ms, hand_id, handedness, score, landmark_index, x, y, z` (sin velocidad) |
| B | 24-B y 24-C | A + `img_w, img_h` (24-A) + `vx, vy, vz, rapidez_cm_s, fuente` (24-B) |
| C | 24-D a 28-A | B + `rapidez_rel_cm_s, dedo` |
| D | 28-D en adelante | C + `palma_cm` (28-B) + `x_cm, y_cm, z_cm` (28-D; vacías aquí: no son de estéreo) |

Ninguna es de dos cámaras (`--estereo`): la muñeca no tiene posición absoluta en cm.

## Qué se puede hacer con cada una

Comprobado el 2026-11-24 en macOS con el código de la 23-B:

| Uso | Formato A | B, C, D |
|-----|:---------:|:-------:|
| `unreal_bridge.py --csv` (Unreal, como en vivo) | ✅ | ✅ |
| `plot_csv.py` (verla en 2D / 3D) | ✅ (la velocidad se recalcula) | ✅ |
| `exportar_csv.py` (CSV para artículos) | ❌ `no tiene la(s) columna(s) ['rapidez_cm_s']` | ✅ |

Para Unreal conviene empezar con una de formato **D** (palma conocida) o la **C** de 31 s. En `hand_data_20260924_125606.csv` casi todas las filas dicen `Right` (a veces dos manos con la misma lateralidad): sirve para probar ese caso.

## En la PC con Unreal y la 4090

Con el proyecto ya instalado (README, pasos 1 a 4, y el **2b** para torch con CUDA):

```powershell
git pull
venv\Scripts\python unreal_bridge.py --csv capturas\hand_data_20261001_105542.csv --bucle   # con Unreal abierto (unreal\HandMotionUE)
venv\Scripts\python docs\imagenes_unreal.py capturas\hand_data_20261001_105542.csv          # regenerar las imágenes de la documentación con una mano real
```

`unreal_bridge.py --csv` **sin ruta** toma la captura más reciente de `capturas/`; con estas en el repositorio, en una PC sin capturas propias es `hand_data_20261001_105542.csv`. Lo mismo hace `docs/imagenes_unreal.py` sin argumentos. Las imágenes que hay en `docs/` (23-A) salieron del ejemplo **simulado** de las pruebas, no de una mano real.

Estas capturas **no ejercitan la GPU**: la 4090 solo acelera YOLO (el codo) al **capturar** o al **analizar un video** (`captura.py --video`); reproducir un CSV no usa YOLO.
