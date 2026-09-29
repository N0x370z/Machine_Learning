"""
Prueba del filtro de velocidad (versión 28-C): compara la media
exponencial de antes (VELOCITY_SMOOTHING = 0.35) con el filtro One Euro
de kinematics.py, con señales simuladas. De aquí salen los números del
README (sección "Por qué One Euro y no la media exponencial de antes").

Uso:
    ./venv/bin/python3 pruebas/filtro_velocidad.py            # tabla + comprobaciones
    ./venv/bin/python3 pruebas/filtro_velocidad.py --buscar   # prueba 72 combinaciones

Situaciones simuladas (30 FPS con variación, 4 corridas con semillas
distintas, temblor gaussiano en la posición, como el de MediaPipe):
  - quieta: la mano no se mueve; mide la rapidez de ruido.
  - arranque: pasa de 0 a 40 cm/s; mide cuánto tarda en llegar al 90 %.
  - frenado: pasa de 40 a 0 cm/s; mide cuánto tarda en bajar de 8 cm/s.
  - golpeteo: un dedo a 4 Hz y 1.5 cm; mide qué porcentaje del pico real
    llega a medirse.
  - en movimiento: cuánto oscila la rapidez a velocidad constante.

Escala: 1 unidad de escena = 95 cm (palma de 0.1 unidades = 9.5 cm).
Sale con código 1 si One Euro no mejora a la media exponencial en ruido
quieto y en retraso (las dos cosas por las que se cambió).
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kinematics  # noqa: E402

CM_PER_UNIT = 95.0
NOISE_LOW = (0.0008, 0.0008, 0.002)    # ~1 px en x/y a 1280, z más ruidosa
NOISE_HIGH = (0.0015, 0.0015, 0.003)


def ema_velocities(ts, xs, a=0.35):
    """La media exponencial que se usaba hasta la 28-B."""
    out, v = [np.zeros(3)], np.zeros(3)
    for i in range(1, len(ts)):
        raw = (xs[i] - xs[i - 1]) / (ts[i] - ts[i - 1])
        v = a * raw + (1 - a) * v
        out.append(v)
    return out


def euro_velocities(ts, xs, min_cutoff=None, beta=None, d_cutoff=None):
    """El filtro de kinematics.py (con parámetros propios si se pasan)."""
    kw = {k: v for k, v in (("min_cutoff", min_cutoff), ("beta", beta),
                            ("d_cutoff", d_cutoff)) if v is not None}
    filt = kinematics.OneEuroFilter(ts[0], xs[0], **kw)
    return [np.zeros(3)] + [np.array(filt.update(t, x)) for t, x in zip(ts[1:], xs[1:])]


def scenario(fn, seed, noise):
    """Corre las cinco situaciones con un método y devuelve sus métricas."""
    rng = np.random.default_rng(seed)
    ts = np.cumsum(np.clip(rng.normal(1 / 30, 0.004, 180), 0.015, 0.06))
    sig = np.array(noise)
    res = {}

    xs = [np.array([0.5, 0.3, 0.0]) + rng.normal(0, sig) for _ in ts]
    sp = [np.linalg.norm(v) * CM_PER_UNIT for v in fn(ts, xs)[30:]]
    res["quieta_media"], res["quieta_p95"] = np.mean(sp), np.percentile(sp, 95)

    vt = 40 / CM_PER_UNIT
    xs = [np.array([0.3 + vt * (min(max(t, 2), 4) - 2), 0.3, 0.0]) + rng.normal(0, sig)
          for t in ts]
    sp = np.array([np.linalg.norm(v) * CM_PER_UNIT for v in fn(ts, xs)])
    i2, i4 = np.searchsorted(ts, 2), np.searchsorted(ts, 4)
    k = next(i for i in range(i2, len(ts)) if sp[i] >= 36)
    res["arranque_ms"] = (ts[k] - 2) * 1000
    k = next((i for i in range(i4, len(ts)) if all(sp[i:i + 5] < 8)), len(ts) - 1)
    res["frenado_ms"] = (ts[k] - 4) * 1000
    res["movimiento_std"] = np.std(sp[i2 + 20:i4])

    amp, f = 1.5 / CM_PER_UNIT, 4
    xs = [np.array([0.5, 0.3 + amp * math.sin(2 * math.pi * f * t), 0.0])
          + rng.normal(0, sig) for t in ts]
    sp = [np.linalg.norm(v) * CM_PER_UNIT for v in fn(ts, xs)[30:]]
    res["golpeteo_pct"] = np.percentile(sp, 95) / (2 * math.pi * f * 1.5) * 100
    return res


def average(fn, noise, runs=4):
    """Promedio de las métricas en varias corridas."""
    results = [scenario(fn, seed, noise) for seed in range(runs)]
    return {k: float(np.mean([r[k] for r in results])) for k in results[0]}


def print_table(rows):
    """Imprime [(nombre, métricas)] como tabla."""
    keys = list(rows[0][1])
    print(f"{'':36s}" + "".join(f"{k:>16s}" for k in keys))
    for name, m in rows:
        print(f"{name:36s}" + "".join(f"{m[k]:16.1f}" for k in keys))


def main():
    """Tabla comparativa y comprobaciones (o búsqueda de parámetros)."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buscar", action="store_true",
                        help="Prueba 72 combinaciones de parámetros de One Euro")
    args = parser.parse_args()

    ok = True
    for label, noise in (("temblor bajo", NOISE_LOW), ("temblor alto", NOISE_HIGH)):
        print(f"\n== {label}: {noise}")
        ema = average(ema_velocities, noise)
        rows = [("Media exponencial 0.35 (antes)", ema),
                ("One Euro de kinematics.py (ahora)", average(euro_velocities, noise))]
        if args.buscar:
            for mc in (0.5, 1.0, 1.5):
                for b in (5, 10, 20, 40):
                    for dc in (1.0, 2.0, 4.0):
                        fn = (lambda mc, b, dc: lambda t, x: euro_velocities(t, x, mc, b, dc))(mc, b, dc)
                        rows.append((f"euro min={mc} beta={b} d={dc}", average(fn, noise)))
        print_table(rows)
        euro = rows[1][1]
        checks = {
            "menos ruido quieto (p95)": euro["quieta_p95"] < ema["quieta_p95"],
            "menos retraso al arrancar": euro["arranque_ms"] < ema["arranque_ms"],
            "golpeteo igual o mejor (±5 puntos)": euro["golpeteo_pct"] >= ema["golpeteo_pct"] - 5,
        }
        for name, passed in checks.items():
            print(f"  {'OK   ' if passed else 'FALLA'} {name}")
            ok &= passed

    # Un hueco de más de MAX_GAP_S reinicia la velocidad en 0.
    est = kinematics.VelocityEstimator()
    est.update(1, 0.0, {0: (0, 0, 0)})
    est.update(1, 0.033, {0: (0.01, 0, 0)})
    gap = est.update(1, 0.533, {0: (0.5, 0, 0)})[0] == (0.0, 0.0, 0.0)
    print(f"\n  {'OK   ' if gap else 'FALLA'} tras un hueco de 0.5 s la velocidad vuelve a 0")
    ok &= gap
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
