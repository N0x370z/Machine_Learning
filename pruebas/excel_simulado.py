"""
Prueba de exportar_excel.py (19-A) SIN cámara: arma un CSV con rapideces
de valor conocido, exporta los dos formatos y comprueba lo que sale.

  - Estructura: hojas de cada formato, series y columnas de Datos.
  - Fórmulas: se recalculan con LibreOffice (si está instalado; si no, esa
    parte se omite y se dice) y se comparan contra numpy: media, RMS,
    desviación y pico (ingeniería, en m/s) y "media (DE)", "mediana
    [Q1-Q3]" (medicina, en cm/s).
  - Casos borde: CSV de antes de la 24-A, fila final cortada, formato
    desconocido, sin filas.

Uso:
    ./venv/bin/python3 pruebas/excel_simulado.py
Sale con código 1 si algo queda fuera de tolerancia.
"""

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import exportar_excel as xl  # noqa: E402
import hand_style  # noqa: E402
from captura import CSV_HEADER  # noqa: E402

N_FRAMES = 120
FPS = 30.0
PALM = 8.5


def make_csv(path, n_frames=N_FRAMES):
    """
    CSV de una mano (id 3, Right) con 22 puntos por fotograma. La rapidez
    del punto idx en el frame k es conocida (ver speed_of), y la relativa
    de las puntas es la mitad. Devuelve {(idx, tipo): [valores]}.
    """
    truth = {}
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for k in range(n_frames):
            for idx in range(22):
                s = speed_of(idx, k)
                rel = s / 2
                truth.setdefault((idx, "abs"), []).append(s)
                if idx in xl.FINGERTIPS:
                    truth.setdefault((idx, "rel"), []).append(rel)
                w.writerow([k, round(k / FPS * 1000), 3, "Right", 0.99, idx, 0.5, 0.5, 0.0,
                            1280, 720, 0, 0, 0, s, rel, hand_style.point_name(idx),
                            "mediapipe", PALM, "", "", ""])
    return truth


def speed_of(idx, k):
    """Rapidez (cm/s) inventada del punto idx en el frame k."""
    return 15 + idx + 10 * np.sin(2 * np.pi * k / 40 + idx)


def recalc(xlsx, out_dir):
    """Abre y guarda con LibreOffice para que calcule las fórmulas; devuelve la ruta."""
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    out_dir.mkdir(exist_ok=True)
    subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", str(out_dir),
                    str(xlsx)], check=True, capture_output=True, timeout=180)
    return out_dir / xlsx.name


def main():
    """Corre todos los casos y sale con 0 (OK) o 1 (FALLA)."""
    from openpyxl import load_workbook
    results = []

    def check(name, passed, detail):
        results.append(passed)
        print(f"  {'OK   ' if passed else 'FALLA'} {name}: {detail}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "hand_data_prueba.csv"
        truth = make_csv(src)

        print("1. Estructura")
        eng = xl.export(src, "ingenieria")
        med = xl.export(src, "medicina")
        wb_e, wb_m = load_workbook(eng), load_workbook(med)
        check("hojas de ingeniería", wb_e.sheetnames ==
              ["Parámetros", "Ecuaciones", "Resultados", "Limitaciones", "Datos"],
              str(wb_e.sheetnames))
        check("hojas de medicina", wb_m.sheetnames ==
              ["Métodos", "Tabla 1", "Tabla 2", "Notas estadísticas", "Datos"],
              str(wb_m.sheetnames))
        data = wb_e["Datos"]
        check("Datos: 12 series por defecto (muñeca, 5 puntas abs y rel, codo)",
              data.max_column - 2 == 12 and data.max_row - 1 == N_FRAMES,
              f"{data.max_column - 2} series, {data.max_row - 1} frames")
        all_pts = load_workbook(xl.export(src, "medicina", tmp / "todos.xlsx", all_points=True))
        check("--todos-los-puntos: 22 puntos + 5 relativas",
              all_pts["Datos"].max_column - 2 == 27, f"{all_pts['Datos'].max_column - 2} series")
        wrist = [data.cell(row=r, column=3).value for r in range(2, 2 + N_FRAMES)]
        check("Datos guarda los cm/s del CSV (muñeca)",
              np.allclose(wrist, truth[(0, "abs")], atol=0.0006), f"máx. dif. "
              f"{np.max(np.abs(np.array(wrist) - truth[(0, 'abs')])):.4f} cm/s")
        todo = sum(1 for ws in wb_m for row in ws.iter_rows() for c in row
                   if c.value == xl.PLACEHOLDER or (isinstance(c.value, str)
                                                    and xl.PLACEHOLDER in c.value))
        check("medicina deja campos por completar (ética, participante...)", todo >= 8,
              f"{todo} campos")
        eq = [r for r in range(4, wb_e["Ecuaciones"].max_row + 1)
              if str(wb_e["Ecuaciones"].cell(row=r, column=1).value).startswith("(")]
        check("ingeniería: ecuaciones numeradas con LaTeX", len(eq) >= 10 and
              all(wb_e["Ecuaciones"].cell(row=r, column=3).value for r in eq),
              f"{len(eq)} ecuaciones")

        print("2. Fórmulas recalculadas (LibreOffice)")
        rc_e, rc_m = recalc(eng, tmp / "rc"), recalc(med, tmp / "rc")
        if rc_e is None:
            print("  (omitido: LibreOffice no está instalado)")
        else:
            res = load_workbook(rc_e, data_only=True)["Resultados"]
            rows = {res.cell(row=r, column=1).value: r for r in range(3, res.max_row + 1)
                    if res.cell(row=r, column=1).value}
            worst = 0.0
            for name, key in [("Right #3 · Muñeca (absoluta)", (0, "abs")),
                              ("Right #3 · Índice (absoluta)", (8, "abs")),
                              ("Right #3 · Índice (relativa a la muñeca)", (8, "rel"))]:
                r = rows[name]
                v = np.array(truth[key]) / 100
                got = [res.cell(row=r, column=c).value for c in range(2, 7)]
                exp = [len(v), v.mean(), np.sqrt((v ** 2).mean()), v.std(ddof=1), v.max()]
                worst = max(worst, max(abs(g - e) for g, e in zip(got[1:], exp[1:])))
                if got[0] != len(v):
                    worst = 99
            check("ingeniería: N, media, RMS, σ y pico = numpy (m/s)", worst < 0.0005,
                  f"diferencia máxima {worst:.6f} m/s")
            par = load_workbook(rc_e, data_only=True)["Parámetros"]
            fs = par["C6"].value
            check("ingeniería: f_s = (N-1)/T", abs(fs - FPS) < 0.2, f"{fs:.2f} Hz (real {FPS})")
            t2 = load_workbook(rc_m, data_only=True)["Tabla 2"]
            rows = {t2.cell(row=r, column=1).value: r for r in range(3, t2.max_row + 1)
                    if t2.cell(row=r, column=1).value}
            r = rows["Right #3 · Índice (absoluta)"]
            v = np.array(truth[(8, "abs")])
            q1, q3 = np.percentile(v, [25, 75])
            exp_mean = f"{v.mean():.1f} ({v.std(ddof=1):.1f})"
            exp_med = f"{np.median(v):.1f} [{q1:.1f}-{q3:.1f}]"
            got_mean, got_med = t2.cell(row=r, column=3).value, t2.cell(row=r, column=4).value
            check("medicina: «media (DE)» como numpy", got_mean == exp_mean, f"{got_mean!r} vs {exp_mean!r}")
            check("medicina: «mediana [Q1-Q3]» como numpy", got_med == exp_med, f"{got_med!r} vs {exp_med!r}")

        print("3. Casos borde")
        old = tmp / "viejo.csv"
        old.write_text("frame,timestamp_ms,hand_id,handedness,score,landmark_index,x,y,z\n"
                       "0,0,0,Right,0.9,0,0.5,0.5,0\n")
        try:
            xl.export(old, "ingenieria")
            check("CSV de antes de la 24-A", False, "no falló")
        except xl.ExportError as err:
            check("CSV de antes de la 24-A: error claro", "24-A" in str(err), str(err)[:60] + "...")
        cut = tmp / "cortado.csv"
        text = src.read_text()
        cut.write_text(text[:text.rfind(",")] )      # la última fila queda cortada
        try:
            out = xl.export(cut, "medicina")
            n = load_workbook(out)["Datos"].max_row - 1
            check("fila final cortada: se salta y el resto se exporta", n == N_FRAMES,
                  f"{n} frames (de {N_FRAMES})")
        except xl.ExportError as err:
            check("fila final cortada", False, str(err))
        try:
            xl.export(src, "apa")
            check("formato desconocido", False, "no falló")
        except xl.ExportError as err:
            check("formato desconocido: error claro", "ingenieria" in str(err), str(err))
        empty = tmp / "vacio.csv"
        empty.write_text(",".join(CSV_HEADER) + "\n")
        try:
            xl.export(empty, "ingenieria")
            check("CSV sin filas", False, "no falló")
        except xl.ExportError as err:
            check("CSV sin filas: error claro", "válidas" in str(err), str(err))

    ok = all(results)
    print("\nRESULTADO:", "OK" if ok else "FALLA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
