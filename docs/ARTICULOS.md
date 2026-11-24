# Datos para artículos científicos — HandMotion3D

Todo lo necesario para usar las mediciones de HandMotion3D en una publicación: cómo hacer una sesión, qué archivos quedan, los dos CSV de resultados (ingeniería y medicina), las ecuaciones, la reproducibilidad (datos de la sesión y reanálisis de videos) y lo que hay que tener en cuenta antes de publicar.

> **Validación pendiente:** la rapidez de HandMotion3D todavía **no se ha validado contra un sistema de referencia**. Antes de reportarla como medida clínica o de ingeniería hay que validarla (ver [Qué hay que saber antes de publicar](#qué-hay-que-saber-antes-de-publicar)).

## Índice

- [Una sesión, paso a paso](#una-sesión-paso-a-paso)
- [Qué archivos quedan](#qué-archivos-quedan)
- [Exportar para artículos (los dos CSV)](#exportar-para-artículos-exportar_csvpy)
- [Datos de la sesión (`.json`)](#datos-de-la-sesión-json)
- [Reproducibilidad: reanalizar un video](#reproducibilidad-reanalizar-un-video)

## Una sesión, paso a paso

**Antes:**

1. Aprobación del comité de ética y consentimiento informado. Si vas a guardar video, que el consentimiento lo diga.
2. Asigna a cada participante un **código** (`P01`, `P02`…). Nunca uses el nombre: el código queda en los archivos.
3. Mide la **palma** con una regla: del pliegue de la muñeca al nudillo del dedo medio, en cm. Es la regla con la que se pasan las velocidades a cm/s (con dos cámaras se mide sola).
4. Cámara **fija** (trípode), buena luz, fondo liso, la mano entera en cuadro, siempre a la misma distancia. Anótalo para la sección de métodos.

**Durante:**

```bash
./venv/bin/python3 captura.py --participante P01 --palma-cm 8.5 --notas "golpeteo índice-pulgar 10 s, mano derecha"
```

- Comprueba en el panel que diga `Participante: P01` y que `Frames grabados` suba.
- `espacio` pausa (no se graba nada durante la pausa); `q` termina.
- **`e`** genera en cualquier momento los dos CSV de resultados de lo grabado hasta ahí.
- Si además grabas el video de la sesión con otra app, podrás reanalizarlo después (ver [abajo](#reproducibilidad-reanalizar-un-video)).

**Después:**

```bash
./venv/bin/python3 exportar_csv.py         # los dos CSV de la última captura (si no usaste 'e')
```

- Revisa la captura: `./venv/bin/python3 plot_csv.py --3d`. Si un tramo se detectó mal, anótalo.
- Guarda una copia de `capturas/` (CSV, `.json` y `articulos/`). **No se suben a git** y no deberían: pueden tener datos de participantes.

## Qué archivos quedan

| Archivo | Qué tiene | Para qué |
|---------|-----------|----------|
| `capturas/hand_data_<inicio>.csv` | Una fila por punto y fotograma: posición, velocidad, rapidez, palma ([formato](TECNICO.md#formato-del-csv-exportado)) | Datos crudos: todo lo demás sale de aquí |
| `capturas/hand_data_<inicio>.json` | Cómo se midió: participante, fuente, parámetros, versiones ([abajo](#datos-de-la-sesión-json)) | Métodos y reproducibilidad |
| `capturas/articulos/hand_data_<inicio>_ingenieria.csv` | Resultados en SI por serie | Tablas de un artículo de ingeniería |
| `capturas/articulos/hand_data_<inicio>_medicina.csv` | Estadística descriptiva por serie, con `participante` | Tablas de un artículo médico; juntar participantes |

## Exportar para artículos (`exportar_csv.py`)

Desde la **17-B** una captura se exporta a **dos CSV de resultados**, uno con el formato de **ingeniería** y otro con el de **medicina**, para usarlos después en publicaciones científicas. Reemplazan al Excel de la 19-A (ver [Cambios](CAMBIOS.md)).

```bash
./venv/bin/python3 exportar_csv.py                                        # los dos, del último CSV de capturas/
./venv/bin/python3 exportar_csv.py capturas/hand_data_X.csv --participante P01
./venv/bin/python3 exportar_csv.py --formato medicina --todos-los-puntos  # solo uno, con los 22 puntos
```

Durante la captura: **`e`** genera los dos con lo grabado **hasta ese momento**, sin parar. Si se vuelve a pulsar, **reemplaza** los anteriores (que tenían menos datos). El aviso sale en el panel y en la terminal, y un error al exportar nunca interrumpe la captura. Exportar congela la imagen un momento (1.1 s medidos con una captura simulada de 10 min y una mano; con el Excel eran 2.6 s), y como la pausa pasa de 0.25 s, la velocidad vuelve a empezar en 0.

**Dónde quedan:** en `capturas/articulos/`, con el nombre de la captura más el formato:

```
capturas/articulos/hand_data_20261117_100000_ingenieria.csv
capturas/articulos/hand_data_20261117_100000_medicina.csv
```

Van en una subcarpeta para que `plot_csv.py` (que abre el último `hand_data_*.csv` de `capturas/`) no los confunda con una captura. No se suben a git (`.gitignore`): pueden traer datos de participantes.

### Cómo están hechos

- **Una fila por serie:** mano × punto × tipo de rapidez. Por defecto la muñeca, las cinco puntas y el codo (rapidez absoluta), más las cinco puntas relativas a la muñeca: 12 filas por mano. Con `--todos-los-puntos`, 27.
- **Formato "tidy"**, el que esperan R, Python/pandas, SPSS, Stata o JASP: separador **coma**, **punto decimal**, UTF-8, primera fila con los nombres de columna **en ASCII y con la unidad al final** (`media_m_s`, `de_cm_s`). Una celda **vacía** significa que no se puede calcular (la DE con un solo dato).
- **Los números vienen calculados** (no son fórmulas). Para juntar varias sesiones o participantes, se concatenan los CSV: cada fila dice de qué `archivo` y `participante` sale.
- En Excel con idioma de **coma decimal**, ábrelos con *Datos → Desde texto/CSV* (separador coma, origen UTF-8). Si se abren con doble clic, los números se pueden leer mal.

| | **Ingeniería** (`_ingenieria.csv`) | **Medicina** (`_medicina.csv`) |
|---|---|---|
| Unidades | **SI: m/s** (4 decimales = 0.1 mm/s) | **cm/s** (2 decimales; los textos, 1) |
| Resultados por serie | N, T, f_s, **media, RMS, σ, pico** | n, duración, **media, DE, mediana, Q1, Q3, mín, máx** |
| Listo para la tabla del artículo | — | `media_de` = «12.3 (4.5)», `mediana_q1_q3` = «11.0 [8.2-14.1]» |
| Descripción de la medición | `palma_cm`, `profundidad`, `resolucion_px` | `palma_cm`, `profundidad` |
| Para juntar sesiones | `archivo` | `participante` (`--participante`, o por completar) y `archivo` |

`palma_cm` es la **mediana de la palma de esa mano**. Con `--estereo` la palma se mide en cada fotograma, y con dos manos cada una lleva la suya; antes, en el Excel, se ponía un solo valor, el más repetido (revisión 5). `profundidad` vale `monocular` (z estimada por MediaPipe), `estereo` (dos cámaras) o `mixta` (la cámara 2 vio la mano solo a ratos).

#### Columnas de `_ingenieria.csv`

| Columna | Qué es |
|---------|--------|
| `archivo` | CSV de la captura de la que salen los datos |
| `mano` | Lateralidad real de la mano: Left o Right |
| `id_mano` | Número de seguimiento (cambia si la mano sale de cámara y vuelve) |
| `punto` | Nombre del punto: Muñeca, Pulgar, Índice, Medio, Anular, Meñique (punta) o Codo |
| `indice_punto` | Índice del punto en MediaPipe (0-20; 21 = codo) |
| `rapidez` | absoluta, o relativa_muneca (lo que se mueve el dedo dentro de la mano) |
| `N` | Fotogramas en que se vio el punto |
| `T_s` | Duración: del primer al último de esos fotogramas, s |
| `fs_hz` | Frecuencia de muestreo efectiva (N - 1) / T, Hz |
| `media_m_s` | Media de la rapidez, m/s |
| `rms_m_s` | Valor cuadrático medio de la rapidez, m/s |
| `sigma_m_s` | Desviación estándar muestral (N - 1), m/s |
| `pico_m_s` | Rapidez máxima observada, m/s |
| `palma_cm` | Largo de palma con el que se pasó a cm (mediana de esa mano), cm |
| `profundidad` | monocular (z de MediaPipe), estereo (dos cámaras) o mixta |
| `resolucion_px` | Resolución de la imagen, ancho x alto en px |

#### Columnas de `_medicina.csv`

| Columna | Qué es |
|---------|--------|
| `participante` | Código del participante (--participante o por completar) |
| `archivo` | CSV de la captura de la que salen los datos |
| `mano` | Lateralidad real de la mano: Left o Right |
| `id_mano` | Número de seguimiento (cambia si la mano sale de cámara y vuelve) |
| `punto` | Nombre del punto: Muñeca, Pulgar, Índice, Medio, Anular, Meñique (punta) o Codo |
| `indice_punto` | Índice del punto en MediaPipe (0-20; 21 = codo) |
| `rapidez` | absoluta, o relativa_muneca (lo que se mueve el dedo dentro de la mano) |
| `n` | Fotogramas en que se vio el punto |
| `duracion_s` | Duración: del primer al último de esos fotogramas, s |
| `media_cm_s` | Media, cm/s |
| `de_cm_s` | Desviación estándar muestral (n - 1), cm/s |
| `mediana_cm_s` | Mediana, cm/s |
| `q1_cm_s` | Primer cuartil (método inclusivo), cm/s |
| `q3_cm_s` | Tercer cuartil (método inclusivo), cm/s |
| `min_cm_s` | Mínimo, cm/s |
| `max_cm_s` | Máximo, cm/s |
| `media_de` | Texto listo para la tabla: «media (DE)», 1 decimal |
| `mediana_q1_q3` | Texto listo para la tabla: «mediana [Q1-Q3]», 1 decimal |
| `palma_cm` | Largo de palma con el que se pasó a cm (mediana de esa mano), cm |
| `profundidad` | monocular (z de MediaPipe), estereo (dos cámaras) o mixta |

#### Ecuaciones (para la sección de métodos de un artículo de ingeniería)

Antes iban en la hoja *Ecuaciones* del Excel. Con `p̂` la posición filtrada (x, y, z de la escena; unidad = ancho del fotograma) y `t` el tiempo de cada fotograma:

| N.º | Ecuación | Qué es |
|-----|----------|--------|
| (1) | $\vec v_k = (\hat{\vec p}_k - \hat{\vec p}_{k-1}) / (t_k - t_{k-1})$ | Velocidad de un punto |
| (2) | $\kappa = L_{palma} / \lVert \vec p_9 - \vec p_0 \rVert$ | Escala, cm por unidad de escena (muñeca → nudillo del medio) |
| (3) | $s = \kappa \lVert \vec v \rVert$ | Rapidez absoluta (`rapidez_cm_s` del CSV de captura) |
| (4) | $s_{rel} = \kappa \lVert \vec v - \vec v_{mu\tilde{n}eca} \rVert$ | Rapidez relativa a la muñeca |
| (5) | $\alpha = 1/(1+\tau/T_e),\ \tau = 1/(2\pi f_c),\ f_c = f_{min} + \beta\lvert\hat{\dot x}\rvert$ | Filtro One Euro (Casiez, Roussel y Vogel, CHI 2012): $f_{min}$ = 0.5 Hz, β = 10.0, corte de la derivada = 2.0 Hz |
| (6) | $\hat x_k = \alpha x_k + (1-\alpha)\hat x_{k-1}$ | Suavizado con el α de (5) |
| (7) | $\bar v = \frac{1}{N}\sum s_k$ | `media_m_s` |
| (8) | $v_{RMS} = \sqrt{\frac{1}{N}\sum s_k^2}$ | `rms_m_s` |
| (9) | $\sigma = \sqrt{\frac{1}{N-1}\sum (s_k-\bar v)^2}$ | `sigma_m_s` |
| (10) | $v_{pico} = \max_k s_k$ | `pico_m_s` (atenuado por el filtro) |
| (11) | $f_s = (N-1)/(t_N - t_1)$ | `fs_hz`; subestima la real si hubo fotogramas sin mano |
| (12) | $\mathbf x_i \simeq \mathbf P_i \mathbf X,\ \mathbf P_i = \mathbf K_i[\mathbf R_i \mid \mathbf t_i]$ | Solo con dos cámaras: triangulación lineal (DLT) de cada punto |

### Qué hay que saber antes de publicar

- **Fotogramas consecutivos no son observaciones independientes.** Por eso no se calculan intervalos de confianza ni valores p entre fotogramas: saldrían demasiado optimistas. Para comparar personas o condiciones, resume a cada participante en **un valor** (por ejemplo, su `mediana_cm_s`) y analiza esos valores. Para eso está la columna `participante`.
- **Validación:** la rapidez se estima con visión por computadora y **no está validada contra una referencia** (captura de movimiento óptica, goniómetro, sensores inerciales). Antes de reportarla como medida clínica o de ingeniería, hay que validarla. En medicina lo habitual es Bland-Altman (sesgo y límites de concordancia al 95 %) y el coeficiente de correlación intraclase.
- Con **una cámara**, la profundidad `z` es una estimación relativa; con `--estereo` se mide.
- Los cm/s dependen del **largo de palma** (`--palma-cm` o medido con dos cámaras). Si la palma real es distinta, todas las rapideces se desvían en la misma proporción.
- El filtro One Euro quita el temblor, pero **atenúa los picos más breves** (retraso del orden de 0.1 s).
- Solo cuentan los fotogramas con la mano detectada: los huecos **no** cuentan como cero. Si la mano se pierde más de 0.25 s, la velocidad se reinicia.
- `id_mano` es un seguimiento: si la mano sale de cámara y vuelve, recibe otro número. Para agrupar, usa `mano` (Left/Right).
- Los cuartiles se calculan con el método **inclusivo** (el de `QUARTILE`/`QUARTILE.INC` de Excel y `numpy.percentile`). Otros programas usan otros métodos por defecto (R `quantile` type 7 coincide; SPSS no): dilo en los métodos.
- Revisa las normas de tu revista o congreso (IEEE, Vancouver, AMA…) para el formato final de las tablas.
- El participante de los CSV sale de `--participante` (de `exportar_csv.py` o de `captura.py`); si no se da, del `.json` de la sesión.

## Datos de la sesión (`.json`)

Desde la **17-D**, junto a cada CSV de captura queda un `.json` con el mismo nombre que dice **cómo** se obtuvieron esos datos. Sirve para escribir la sección de métodos y para que alguien pueda repetir el análisis.

| Campo | Qué es |
|-------|--------|
| `participante`, `notas` | Los de `--participante` y `--notas` |
| `estado` | `en curso` mientras se graba; `completa` al terminar; `error` si el programa falló. Si quedó en `en curso`, el proceso murió sin cerrar (el CSV tiene lo grabado hasta ese momento) |
| `inicio`, `fin` | Hora local con zona horaria (ISO 8601) |
| `fuente` | `camara` (índice, resolución pedida y real) o `video` (ruta, **huella SHA-256**, FPS, fotogramas, si estaba en espejo); con `--estereo`, la calibración usada con su huella y la separación entre cámaras |
| `parametros` | Palma, máximo de manos, umbrales de MediaPipe, modelo YOLO, parámetros del filtro One Euro y hueco máximo |
| `software` | Versión del programa (la del CHANGELOG), **commit de git** y si había cambios sin commit, Python, sistema y versiones de mediapipe, OpenCV, numpy, ultralytics y torch |
| `resultado` | Motivo del fin, fotogramas procesados y con mano, duración y FPS efectivos |

Para la sección de métodos, por ejemplo: *"Se usó HandMotion3D versión 17-D (commit 3d1b7cd) con MediaPipe 0.10.35, a 1280×720 y 30 FPS efectivos…"*: todo está en el `.json`.

## Reproducibilidad: reanalizar un video

Desde la **17-C**, `captura.py` puede analizar un **video grabado** en lugar de la cámara:

```bash
./venv/bin/python3 captura.py --video sesiones/P01.mp4 --participante P01 --palma-cm 8.5
```

- **El tiempo sale del video**, no del reloj: las velocidades son las reales aunque el análisis vaya más lento (por ejemplo, con YOLO en una computadora lenta). Se analizan todos los fotogramas.
- El `.json` guarda la **huella SHA-256** del video. Otra persona puede comprobar que tiene exactamente el mismo archivo: `shasum -a 256 P01.mp4` en macOS, `sha256sum P01.mp4` en Linux, `certutil -hashfile P01.mp4 SHA256` en Windows. Con la misma versión del programa (el `commit` del `.json`) y las mismas librerías (también en el `.json`) los números deberían coincidir o quedar muy cerca, pero **no se garantiza que sean idénticos**: MediaPipe y YOLO pueden dar resultados ligeramente distintos según el procesador o la GPU. Esto **no se ha medido**: si la reproducibilidad exacta importa para el artículo, reanaliza el mismo video en dos equipos y compara.
- Sirve también para **reprocesar** sesiones cuando mejore el programa, o para analizar videos clínicos que ya existen (con el consentimiento que corresponda).
- Si el video se grabó con la vista previa de una cámara frontal (ya en espejo), agrega `--video-espejado`. Si Left/Right salen al revés, agrega o quita esa opción.
- Con una cámara la profundidad es estimada, igual que en vivo. `--video` no se combina con `--estereo`.
