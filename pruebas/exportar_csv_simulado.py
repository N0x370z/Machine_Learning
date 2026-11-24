"""
Prueba de exportar_csv.py (17-B) SIN cámara: arma CSV de captura con
rapideces de valor conocido, exporta los dos formatos y compara cada
número con numpy.

  - Estructura: columnas de cada formato, una fila por serie, carpeta
    articulos/, series por defecto y con --todos-los-puntos.
  - Ingeniería (m/s): N, T, f_s, media, RMS, σ (n - 1) y pico.
  - Medicina (cm/s): n, media, DE, mediana, Q1, Q3 (método inclusivo,
    el de QUARTILE de Excel), mín, máx y los textos «media (DE)» y
    «mediana [Q1-Q3]»; columna participante.
  - Palma por mano (revisión 5): con dos manos y la palma medida cada
    fotograma (estéreo), cada mano lleva la mediana de SU palma.
  - Casos borde: CSV de antes de la 24-A, fila final cortada, formato
    desconocido, sin filas, punto visto una sola vez (DE vacía),
    exportar dos veces (se reemplaza), el CSV se lee con pandas/csv.

Uso:
    ./venv/bin/python3 pruebas/exportar_csv_simulado.py
Sale con código 1 si algo queda fuera de tolerancia.
"""

import csv
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import exportar_csv as ex  # noqa: E402
import hand_style  # noqa: E402
from captura import CSV_HEADER  # noqa: E402

N_FRAMES = 120
FPS = 30.0


def speed_of(idx, k):
    """Rapidez (cm/s) inventada del punto idx en el frame k."""
    return 15 + idx + 10 * np.sin(2 * np.pi * k / 40 + idx)


def make_csv(path, hands=((3, "Right", 8.5, "mediapipe"),), n_frames=N_FRAMES, palm_noise=0.0,
             only_frame0=None):
    """
    CSV de captura con 22 puntos por mano y fotograma. hands: (id, mano,
    palma, fuente). La rapidez del punto idx en el frame k es speed_of
    (+ 5 cm/s en la segunda mano) y la relativa de las puntas, la mitad.
    palm_noise: la palma varía de fotograma a fotograma (como con
    --estereo). only_frame0: índice de un punto que solo aparece en el
    frame 0. Devuelve {(id, idx, tipo): [valores]}.
    """
    rng = np.random.default_rng(1)
    truth = {}
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for k in range(n_frames):
            for h, (hid, label, palm, source) in enumerate(hands):
                p = round(palm + rng.normal(0, palm_noise), 2) if palm_noise else palm
                for idx in range(22):
                    if idx == only_frame0 and k > 0:
                        continue
                    s = speed_of(idx, k) + 5 * h
                    rel = s / 2
                    truth.setdefault((hid, idx, "absoluta"), []).append(s)
                    if idx in ex.FINGERTIPS:
                        truth.setdefault((hid, idx, "relativa_muneca"), []).append(rel)
                    src = source if idx < 21 else "estimado"
                    w.writerow([k, round(k / FPS * 1000, 3), hid, label, 0.99, idx, 0.5, 0.5, 0.0,
                                1280, 720, 0, 0, 0, s, rel, hand_style.point_name(idx),
                                src, p, "", "", ""])
    return truth


def read(path):
    """Filas de un CSV exportado como dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    """Corre todos los casos y sale con 0 (OK) o 1 (FALLA)."""
    results = []

    def check(name, passed, detail):
        results.append(passed)
        print(f"  {'OK   ' if passed else 'FALLA'} {name}: {detail}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "hand_data_20261117_100000.csv"
        truth = make_csv(src)
        written = ex.export(src)

        print("1. Estructura")
        check("dos archivos en articulos/ junto a la captura",
              sorted(p.name for p in written.values()) == [
                  "hand_data_20261117_100000_ingenieria.csv", "hand_data_20261117_100000_medicina.csv"]
              and all(p.parent == tmp / "articulos" for p in written.values()),
              ", ".join(f"{p.parent.name}/{p.name}" for p in written.values()))
        eng, med = read(written["ingenieria"]), read(written["medicina"])
        check("columnas de ingeniería", list(eng[0]) == [c for c, _ in ex.INGENIERIA_COLUMNS],
              f"{len(eng[0])} columnas")
        check("columnas de medicina", list(med[0]) == [c for c, _ in ex.MEDICINA_COLUMNS],
              f"{len(med[0])} columnas")
        check("columnas en ASCII (sin acentos: R, SPSS, Stata)",
              all(c.isascii() for c, _ in ex.INGENIERIA_COLUMNS + ex.MEDICINA_COLUMNS), "ok")
        check("12 series por defecto (7 puntos absolutas + 5 puntas relativas)",
              len(eng) == len(med) == 12, f"{len(eng)} / {len(med)} filas")
        all_pts = ex.export(src, out_dir=tmp / "todos", all_points=True)
        check("--todos-los-puntos: 27 series (22 + 5)", len(read(all_pts["medicina"])) == 27,
              f"{len(read(all_pts['medicina']))} filas")
        check("orden: muñeca primero, absoluta antes que relativa",
              (eng[0]["indice_punto"], eng[0]["rapidez"], eng[2]["rapidez"]) == ("0", "absoluta", "relativa_muneca"),
              f"{eng[0]['punto']}, {eng[1]['punto']} {eng[1]['rapidez']}, {eng[2]['punto']} {eng[2]['rapidez']}")

        print("2. Ingeniería (m/s) contra numpy")
        worst = 0.0
        for row in eng:
            v = np.array(truth[(int(row["id_mano"]), int(row["indice_punto"]), row["rapidez"])]) / 100
            exp = [v.mean(), np.sqrt(np.mean(v ** 2)), v.std(ddof=1), v.max()]
            got = [float(row[c]) for c in ("media_m_s", "rms_m_s", "sigma_m_s", "pico_m_s")]
            worst = max(worst, max(abs(a - b) for a, b in zip(exp, got)))
        check("media, RMS, σ (n-1) y pico de las 12 series", worst < 0.00006, f"error máx. {worst:.6f} m/s")
        r = eng[0]
        check("N, T y f_s", (r["N"], r["T_s"]) == ("120", f"{119 / FPS:.3f}")
              and abs(float(r["fs_hz"]) - FPS) < 0.05, f"N = {r['N']}, T = {r['T_s']} s, f_s = {r['fs_hz']} Hz")
        check("palma, profundidad y resolución", (r["palma_cm"], r["profundidad"], r["resolucion_px"])
              == ("8.5", "monocular", "1280 x 720"), f"{r['palma_cm']} cm, {r['profundidad']}, {r['resolucion_px']}")

        print("3. Medicina (cm/s) contra numpy")
        worst, texts_ok = 0.0, True
        for row in med:
            v = np.array(truth[(int(row["id_mano"]), int(row["indice_punto"]), row["rapidez"])])
            q1, q2, q3 = np.percentile(v, [25, 50, 75])
            exp = [v.mean(), v.std(ddof=1), q2, q1, q3, v.min(), v.max()]
            got = [float(row[c]) for c in ("media_cm_s", "de_cm_s", "mediana_cm_s", "q1_cm_s",
                                           "q3_cm_s", "min_cm_s", "max_cm_s")]
            worst = max(worst, max(abs(a - b) for a, b in zip(exp, got)))
            texts_ok &= row["media_de"] == f"{v.mean():.1f} ({v.std(ddof=1):.1f})"
            texts_ok &= row["mediana_q1_q3"] == f"{q2:.1f} [{q1:.1f}-{q3:.1f}]"
        check("media, DE, mediana, Q1, Q3, mín y máx de las 12 series", worst < 0.006,
              f"error máx. {worst:.4f} cm/s")
        check("textos «media (DE)» y «mediana [Q1-Q3]»", texts_ok,
              f"{med[0]['media_de']}  /  {med[0]['mediana_q1_q3']}")
        # QUARTILE de Excel (inclusivo) con 1..10: Q1 = 3.25, Q3 = 7.75.
        d = ex.describe([(i, float(i)) for i in range(1, 11)])
        check("cuartiles con el método inclusivo (QUARTILE de Excel)", (d["q1"], d["q3"]) == (3.25, 7.75),
              f"1..10 -> Q1 = {d['q1']}, Q3 = {d['q3']}")
        p = ex.export(src, ("medicina",), tmp / "p01", participant="P01")["medicina"]
        check("--participante llena la columna", {r["participante"] for r in read(p)} == {"P01"}, "P01")
        check("--formato medicina genera solo ese", [x.name for x in (tmp / "p01").iterdir()]
              == [p.name], p.name)

        print("4. Palma por mano (revisión 5)")
        two = tmp / "dos_manos.csv"
        make_csv(two, hands=((1, "Left", 8.0, "estereo"), (2, "Right", 9.0, "estereo")), palm_noise=0.03)
        eng2 = read(ex.export(two)["ingenieria"])
        palms = {r["mano"]: float(r["palma_cm"]) for r in eng2}
        check("cada mano con la mediana de SU palma (estéreo, varía cada fotograma)",
              abs(palms["Left"] - 8.0) < 0.02 and abs(palms["Right"] - 9.0) < 0.02,
              f"Left {palms['Left']} cm, Right {palms['Right']} cm")
        check("profundidad estéreo (el codo, estimado, no la cambia)",
              {r["profundidad"] for r in eng2} == {"estereo"}, "estereo")
        check("24 series con dos manos, Left primero", len(eng2) == 24 and eng2[0]["mano"] == "Left",
              f"{len(eng2)} filas")

        print("5. Casos borde")
        one = tmp / "un_frame.csv"
        make_csv(one, only_frame0=8)
        rows = {(r["indice_punto"], r["rapidez"]): r for r in read(ex.export(one)["medicina"])}
        r8 = rows[("8", "absoluta")]
        check("punto visto una vez: n = 1, DE y «media (DE)» vacías, sin error",
              (r8["n"], r8["de_cm_s"], r8["media_de"]) == ("1", "", ""),
              f"n = {r8['n']}, mediana {r8['mediana_q1_q3']}")
        r8e = {(r["indice_punto"], r["rapidez"]): r for r in read(ex.output_paths(one)["ingenieria"])}
        r8e = r8e[("8", "absoluta")]
        check("ingeniería con N = 1: σ y f_s vacías", (r8e["sigma_m_s"], r8e["fs_hz"]) == ("", ""),
              f"T = {r8e['T_s']} s")
        old = tmp / "viejo.csv"
        old.write_text("frame,timestamp_ms,hand_id,handedness,score,landmark_index,x,y,z\n0,0,0,Right,1,0,0.5,0.5,0\n")
        for name, call in (
            ("CSV de antes de la 24-A", lambda: ex.export(old)),
            ("formato desconocido", lambda: ex.export(src, ("apa",))),
            ("CSV sin filas", lambda: (tmp / "vacio.csv").write_text(",".join(CSV_HEADER) + "\n")
             and ex.export(tmp / "vacio.csv")),
            ("CSV que no existe", lambda: ex.export(tmp / "no_existe.csv")),
        ):
            try:
                call()
                check(f"{name}: error claro", False, "no falló")
            except ex.ExportError as err:
                check(f"{name}: error claro", True, str(err)[:70])
        cut = tmp / "cortado.csv"
        make_csv(cut)
        with open(cut, "a", encoding="utf-8") as f:
            f.write("120,4000,3,Right,0.9")          # el programa se cortó a mitad de fila
        n = int(read(ex.export(cut)["ingenieria"])[0]["N"])
        check("fila final cortada: se salta y el resto se exporta", n == N_FRAMES, f"N = {n}")
        before = written["medicina"].stat().st_mtime_ns
        make_csv(src, n_frames=60)
        again = read(ex.export(src)["medicina"])
        check("exportar otra vez reemplaza (sin archivos .tmp sueltos)",
              again[0]["n"] == "60" and written["medicina"].stat().st_mtime_ns >= before
              and not list((tmp / "articulos").glob("*.tmp")), f"n = {again[0]['n']}")
        try:
            import pandas as pd
            df = pd.read_csv(written["ingenieria"])
            check("pandas lo lee con los tipos correctos", df["media_m_s"].dtype.kind == "f"
                  and df["N"].dtype.kind == "i", f"{df.shape[0]} filas x {df.shape[1]} columnas")
        except ImportError:
            print("  (omitido: pandas no está instalado; la lectura con csv ya se comprobó)")

    ok = all(results)
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
