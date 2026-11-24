"""Ejecuta los seis escenarios requeridos con Kitchen 9.4 y guarda sus logs."""
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree, ignore_patterns
import os
import re
import subprocess

REPO = Path(__file__).resolve().parents[1]
KITCHEN = Path(r"C:\dev\PDI-9.4\data-integration\Kitchen.bat")
PAN = Path(r"C:\dev\PDI-9.4\data-integration\Pan.bat")
PDI_DIR = KITCHEN.parent
JAVA_HOME = Path(r"C:\dev\jdk\jdk8u512-b09")
EVIDENCE = REPO / "evidencias"


def run(label: str, target: Path, relative_file: str, kind: str = "job") -> str:
    env = os.environ.copy()
    env["JAVA_HOME"] = str(JAVA_HOME)
    env["Path"] = str(JAVA_HOME / "bin") + os.pathsep + env.get("Path", "")
    launcher = KITCHEN if kind == "job" else PAN
    command = f'call "{launcher}" /file:"{target / relative_file}" /level:Basic'
    result = subprocess.run(command, shell=True, cwd=PDI_DIR,
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=180)
    log = result.stdout.decode("utf-8", errors="replace")
    log = re.sub(r'(?i)(?:file:/+)?[A-Z]:[/\\](?:[^/\\\s"\'<>]+[/\\])*([^/\\\s"\'<>]+)', lambda m: "${RUTA}/" + m.group(1), log)
    (EVIDENCE / f"kitchen_{label}.log").write_text(log, encoding="utf-8")
    return log


def successful(log: str) -> bool:
    return "Job execution finished" in log and "Finished with errors" not in log


def failed(log: str) -> bool:
    return "Finished with errors" in log or "Abort and log as an error" in log


def copy_case(folder: Path) -> Path:
    target = folder / "repo"
    copytree(REPO, target, ignore=ignore_patterns(".git", "evidencias"))
    for sub in ("temporal", "salida"):
        d = target / sub
        d.mkdir(exist_ok=True)
        for f in d.iterdir():
            if f.is_file() and f.name != ".gitkeep": f.unlink()
    return target

results = []
# 1: primera ejecución completa en la carpeta de trabajo.
log = run("01_primera_ejecucion", REPO, r"procesos\cierre_hotel.kjb")
assert successful(log), "Falló la primera ejecución; revisa kitchen_01_primera_ejecucion.log"
results.append(("Primera ejecución", "OK: job completo en Kitchen"))
# 2: segunda ejecución; los CSV se sobrescriben y los totales no se duplican.
log = run("02_repeticion", REPO, r"procesos\cierre_hotel.kjb")
assert successful(log), "Falló la repetición; revisa kitchen_02_repeticion.log"
results.append(("Repetición", "OK: job completo sin duplicar salidas"))
with TemporaryDirectory(prefix="pentaho-a009-") as tmp:
    base = Path(tmp)
    # 3: falta una entrada en una copia aislada; no se publican informes.
    test = copy_case(base / "falta_entrada")
    (test / "entrada" / "cobros_pdi.csv").unlink()
    log = run("03_falta_entrada", test, r"procesos\cierre_hotel.kjb")
    assert not successful(log), "Falta de entrada no hizo fallar el job"
    assert not (test / "salida" / "informe_hotel_canal.csv").exists()
    assert not (test / "salida" / "reservas_sin_cobro.csv").exists()
    results.append(("Falta de entrada", "OK: job fallido y sin salidas publicadas"))
    # 4: un informe vacío (solo cabecera) se rechaza.
    test = copy_case(base / "informe_vacio")
    (test / "temporal" / "informe_hotel_canal.csv").write_text(
        "hotel;canal;n_reservas;cobrado_total\n", encoding="utf-8")
    log = run("04_informe_vacio", test, r"procesos\validar_informe.ktr", "trans")
    assert failed(log), "El validador aceptó un informe vacío"
    results.append(("Informe solo con cabecera", "OK: validador lo rechaza"))
    # 5: un total modificado debe fallar.
    test = copy_case(base / "total_incorrecto")
    report = REPO / "temporal" / "informe_hotel_canal.csv"
    (test / "temporal" / report.name).write_bytes(report.read_bytes())
    lines = (test / "temporal" / report.name).read_text(encoding="utf-8-sig").splitlines()
    first = lines[1].split(";")
    first[3] = str(float(first[3]) + 1.0)
    lines[1] = ";".join(first)
    (test / "temporal" / report.name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    log = run("05_total_incorrecto", test, r"procesos\validar_informe.ktr", "trans")
    assert failed(log), "El validador aceptó el total incorrecto"
    results.append(("Total incorrecto", "OK: validador lo rechaza"))
# 6: recuperación, con fuentes originales, vuelve a generar y publicar.
log = run("06_recuperacion", REPO, r"procesos\cierre_hotel.kjb")
assert successful(log), "Falló la recuperación; revisa kitchen_06_recuperacion.log"
results.append(("Recuperación", "OK: originales procesados y salidas publicadas"))
(EVIDENCE / "resultado_pruebas_kitchen.csv").write_text(
    "prueba;resultado\n" + "".join(f"{a};{b}\n" for a,b in results), encoding="utf-8")
for name, result in results: print(f"{name}: {result}")
