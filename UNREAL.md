# Conexión con Unreal Engine — HandMotion3D

Cómo hacer que un modelo 3D de **Unreal Engine 5** siga el movimiento de tus manos, usando lo que ya detecta `captura.py`. Funciona desde la versión **19-A** (2026-10-19).

> **Estado de la prueba (honesto):** el lado de Python (`unreal_bridge.py`) está probado sin Unreal ([`pruebas/unreal_simulado.py`](pruebas/README.md)): el formato de los mensajes, los ejes, los ángulos y el envío por UDP. **Lo que pasa dentro de Unreal Engine no se probó**: esta guía se escribió sin tener Unreal a mano, así que los nombres exactos de los nodos de Blueprint pueden variar un poco entre versiones de UE 5. Para eso está `--demo`: una mano sintética que no necesita cámara, para armar y depurar el lado de Unreal por separado.

> **"Real engine":** se interpretó como **Unreal Engine** (el motor de Epic Games). Si era otro motor (Unity, Godot…), el formato de red sigue sirviendo (es OSC estándar sobre UDP), pero esta guía no.

## Cómo viaja la información

```
cámara ──► captura.py ──► unreal_bridge.py ──► OSC / UDP ──► plugin OSC de Unreal ──► Blueprint ──► huesos del modelo
           (MediaPipe)    (cm, ejes de UE,     puerto 8000    (OSC Server)
                           flexión en grados)
```

- **OSC** (Open Sound Control) sobre **UDP**: ligero, sin conexión (si Unreal no está escuchando, simplemente se pierden los paquetes y `captura.py` sigue igual).
- Unreal Engine 5 trae el **plugin OSC**; no hay que instalar nada más. En Python el codificador OSC es propio: **no hay dependencias nuevas** por esto.

## Paso 1 — Probar el envío sin Unreal

Con dos terminales (desde la raíz del repositorio):

```bash
./venv/bin/python3 unreal_bridge.py --escuchar 8000                # terminal 1: muestra lo que llega
./venv/bin/python3 unreal_bridge.py --demo 127.0.0.1:8000          # terminal 2: una mano sintética abriendo y cerrando los dedos
```

En la terminal 1 deben verse líneas como:

```
/handmotion/frame  fotograma 0, manos 1, t = 0.000 s
/handmotion/Right  id 0, codo 0, 87 floats; flexión índice (MCP/PIP/DIP):  19.5 /   0.0 /   0.0
```

Con la cámara de verdad: `./venv/bin/python3 captura.py --unreal` (o `--unreal 192.168.1.20:8000` si Unreal corre en **otra computadora** de la misma red; abre el puerto UDP en su firewall). En el panel de la cámara aparece `Unreal 127.0.0.1:8000: enviando ([u])`; la tecla `u` pausa y reanuda el envío sin parar la captura, y la **pausa** (`espacio`) también detiene el envío.

## Paso 2 — Activar el plugin en Unreal

1. **Edit → Plugins**, busca **OSC** (categoría *Protocols*) y actívalo.
2. Reinicia el editor.

## Paso 3 — Recibir los mensajes (Blueprint)

1. Crea un **Blueprint Actor** (por ejemplo `BP_ManoReceptor`) y colócalo en el nivel.
2. En el **Event BeginPlay**: nodo **Create OSC Server** con *Receive IP Address* `0.0.0.0` (o `127.0.0.1` si todo está en la misma máquina), *Port* `8000` y *Start Listening* activado. Guarda el resultado en una variable `OscServer`.
3. Con `OscServer`: **Bind Event to On OSC Message Received** y conecta un evento propio.
4. En ese evento recibes el mensaje: usa **Get OSC Message Address** y compáralo con `/handmotion/Right` o `/handmotion/Left` (y `/handmotion/frame` si quieres saber cuántas manos hay en el fotograma).
5. Para leer los números, usa los nodos de **OSC → Message** que obtienen los **floats** del mensaje (por índice, o todos a la vez en un arreglo). **Todos los mensajes llevan solo floats**, y en cada mano van en este orden (87 valores):

| Índices | Qué es | Unidad |
|---------|--------|--------|
| `[0]` | id de la mano (el seguimiento; cambia si la pierde de vista y la recupera) | — |
| `[1]` | tiene codo: `1` si hay codo (YOLO o estimado), `0` si no | — |
| `[2]` | largo de la palma (la escala de la mano) | cm |
| `[3..5]` | posición de la **muñeca** (X, Y, Z de Unreal) | cm |
| `[6..68]` | los **21 puntos** de la mano (X, Y, Z cada uno), **relativos a la muñeca**: el punto `n` está en `[6 + 3n .. 8 + 3n]`; el punto 0 (muñeca) es `(0, 0, 0)` | cm |
| `[69..71]` | **codo** relativo a la muñeca (`0, 0, 0` si no hay) | cm |
| `[72..86]` | **flexión** de 15 articulaciones (ver tabla de abajo) | grados |

Los puntos son los de MediaPipe (0 muñeca; 1-4 pulgar; 5-8 índice; 9-12 medio; 13-16 anular; 17-20 meñique; la punta de cada dedo es 4, 8, 12, 16 y 20).

### Ejes y unidades

Convención de Unreal: **X adelante, Y derecha, Z arriba, centímetros.**

| Eje de Unreal | Qué es en la imagen |
|---------------|---------------------|
| X (adelante) | profundidad: positivo = se **aleja** de la cámara |
| Y (derecha) | derecha de la pantalla (la imagen está en espejo, como te ves tú) |
| Z (arriba) | arriba de la pantalla |

Con **una cámara** la profundidad absoluta de la muñeca se desconoce (`[3]` queda en `0`) y la de los dedos es la `z` relativa de MediaPipe, aproximada. Con **dos cámaras** (`--estereo`) la posición de la muñeca (`[3..5]`) es absoluta, en cm respecto a la cámara 1.

### Flexión: 0° = dedo estirado, positivo = doblado

Es 180° menos el ángulo entre los dos huesos que se unen en la articulación. Es lo más cómodo para mover un esqueleto, porque cada articulación necesita **un solo giro**:

| Índice | Dedo | Articulación | Hueso del Mannequin de UE5 (mano derecha) |
|--------|------|--------------|-------------------------------------------|
| `[72]` | Pulgar | CMC | `thumb_01_r` |
| `[73]` | Pulgar | MCP | `thumb_02_r` |
| `[74]` | Pulgar | IP | `thumb_03_r` |
| `[75]` | Índice | MCP | `index_01_r` |
| `[76]` | Índice | PIP | `index_02_r` |
| `[77]` | Índice | DIP | `index_03_r` |
| `[78]`-`[80]` | Medio | MCP, PIP, DIP | `middle_01_r`, `middle_02_r`, `middle_03_r` |
| `[81]`-`[83]` | Anular | MCP, PIP, DIP | `ring_01_r`, `ring_02_r`, `ring_03_r` |
| `[84]`-`[86]` | Meñique | MCP, PIP, DIP | `pinky_01_r`, `pinky_02_r`, `pinky_03_r` |

Los nombres de hueso son los del Mannequin de UE5 (con `_l` en vez de `_r` para la mano izquierda); si usas otro modelo (MetaHuman u otro), cámbialos por los suyos. **El eje de giro del dedo depende del esqueleto** (en muchos es el eje local Y o Z): pruébalo con `--demo`, que dobla y estira los dedos en bucle, hasta que el dedo del modelo se doble hacia la palma.

## Paso 4 — Mover el modelo

Dos formas, de más simple a más completa:

1. **Solo dedos (lo más simple):** en un **Anim Blueprint** (o con *Transform (Modify) Bone* en el Anim Graph), aplica a cada hueso de la tabla un giro de `flexión` grados. Deja la muñeca del modelo donde la pone tu animación.
2. **Muñeca y antebrazo:** usa `[3..5]` como posición objetivo de la mano (por ejemplo, el objetivo de un **IK de brazo** o de un *Control Rig*) y `[69..71]` para el codo. La **orientación** de la mano (hacia dónde apunta la palma) **no se manda**: se calcula en Unreal con los puntos 0, 5 y 17 (el producto cruz de `punto5 − punto0` y `punto17 − punto0` es la normal de la palma). Si prefieres que Python la mande ya calculada, es una mejora pendiente (ver abajo).

Consejos:

- **Suaviza** en Unreal (por ejemplo `FInterp To` o `Interp To`): los mensajes llegan a los FPS de la cámara (~30), menos que los de Unreal.
- **Izquierda y derecha:** el nombre del mensaje (`/handmotion/Left`, `/handmotion/Right`) es la mano **real** de la persona, ya corregida. Si el modelo se ve "al revés", es que está espejado respecto a la cámara: cambia el signo del eje Y.
- **Dos manos:** el mismo Blueprint puede atender a las dos, cada una con su dirección.

## Qué pasa cuando…

| Situación | Qué ocurre |
|-----------|------------|
| Pausas la captura (`espacio` o `p`) | No se manda nada: el modelo se queda en la última pose |
| Pausas solo el envío (`u`) | La captura y el CSV siguen; Unreal no recibe |
| La mano sale de cámara | Se sigue mandando `/handmotion/frame` con `manos = 0` y ya no llegan mensajes de mano: el Blueprint debe decidir si congela o relaja el modelo |
| Unreal no está abierto | Los paquetes se pierden; `captura.py` no se entera ni se frena |
| Los dos corren en máquinas distintas | `--unreal IP:PUERTO`, misma red, puerto UDP abierto en el firewall del que recibe |

## Limitaciones y pendientes

- **Sin probar en Unreal Engine real** (ver arriba). Lo primero que hay que confirmar allí: los nombres de los nodos de OSC y el eje de giro de los dedos del modelo.
- **Una cámara = profundidad aproximada.** Los dedos se doblan bien de frente; la profundidad fina mejora con `--estereo`.
- **No se manda la orientación de la muñeca** (se calcula en Unreal con los puntos 0, 5 y 17). Mejora pendiente: mandarla como cuaternión.
- **No se manda audio, imagen ni el CSV**: solo la pose. Para el CSV y el Excel, ver el [README](README.md#exportar-a-excel-exportar_excelpy).
- El `id` de la mano cambia si la pierde de vista; el nombre del mensaje (`Left`/`Right`) es más estable para elegir qué mano mover.

Historial de cambios: [`CHANGELOG.md`](CHANGELOG.md) (versión 19-A) · Comandos: [`COMANDOS.md`](COMANDOS.md).
