"""Ejecuta los seis escenarios requeridos con PDI 9.4 y guarda logs reproducibles."""

from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree, ignore_patterns
import os
import re
import subprocess


REPO = Path(__file__).resolve().parents[1]
EVIDENCE = REPO / "evidencias"


def resolve_pdi_home() -> Path:
    candidates = [
        os.environ.get("PDI_HOME"),
        r"C:\dev\PDI-9.4\data-integration",
        "/home/iabd00/.local/opt/pentaho-data-integration",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        folder = Path(candidate)
        launcher = folder / ("Kitchen.bat" if os.name == "nt" else "kitchen.sh")
        if launcher.is_file():
            return folder
    raise SystemExit("No se encontró PDI. Define PDI_HOME con la carpeta data-integration.")


PDI_DIR = resolve_pdi_home()
KITCHEN = PDI_DIR / ("Kitchen.bat" if os.name == "nt" else "kitchen.sh")
PAN = PDI_DIR / ("Pan.bat" if os.name == "nt" else "pan.sh")


def command_for(launcher: Path, file_path: Path) -> list[str]:
    if os.name == "nt":
        return ["cmd", "/c", str(launcher), f"/file:{file_path}", "/level:Basic"]
    return [str(launcher), f"-file={file_path}", "-level=Basic"]


def clean_paths(text: str, target: Path) -> str:
    replacements = [
        (str(target.resolve()), "${RUTA_PROYECTO}"),
        (str(REPO.resolve()), "${RUTA_PROYECTO}"),
        (str(PDI_DIR.resolve()), "${PDI_HOME}"),
    ]
    for original, replacement in replacements:
        text = text.replace(original, replacement)
        text = text.replace(original.replace("/", "\\"), replacement)
    return re.sub(
        r"(?i)(?:file:/+)?[A-Z]:[/\\](?:[^/\\\s\"'<>]+[/\\])*([^/\\\s\"'<>]+)",
        lambda match: "${RUTA}/" + match.group(1),
        text,
    )


def run(label: str, target: Path, relative_file: str, kind: str = "job") -> tuple[str, int]:
    env = os.environ.copy()
    java_home = env.get("JAVA_HOME")
    if not java_home:
        raise SystemExit("Define JAVA_HOME con una instalación de Java 8 antes de ejecutar las pruebas.")
    path_key = "Path" if os.name == "nt" else "PATH"
    env[path_key] = str(Path(java_home) / "bin") + os.pathsep + env.get(path_key, "")
    launcher = KITCHEN if kind == "job" else PAN
    file_path = target / relative_file
    command = command_for(launcher, file_path)
    result = subprocess.run(
        command,
        cwd=PDI_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    body = result.stdout.decode("utf-8", errors="replace")
    body = clean_paths(body, target)
    body = "\n".join(line.rstrip() for line in body.splitlines()) + "\n"
    visible_command = " ".join(command_for(Path("${PDI_HOME}") / launcher.name, Path("${RUTA_PROYECTO}") / relative_file))
    log = (
        f"Prueba: {label}\n"
        f"Entorno: PDI 9.4.0.0-343 y Java 8\n"
        f"Comando: {visible_command}\n"
        f"Código de salida: {result.returncode}\n\n"
        f"{body}"
    )
    (EVIDENCE / f"kitchen_{label}.log").write_text(log, encoding="utf-8")
    return log, result.returncode


def successful(log: str, returncode: int) -> bool:
    return returncode == 0 and "Job execution finished" in log and "Finished with errors" not in log


def failed(log: str, returncode: int) -> bool:
    return returncode != 0 and ("Finished with errors" in log or "Abort and log as an error" in log)


def copy_case(folder: Path) -> Path:
    target = folder / "repo"
    copytree(REPO, target, ignore=ignore_patterns(".git", "evidencias"))
    for sub in ("temporal", "salida"):
        directory = target / sub
        directory.mkdir(exist_ok=True)
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.name != ".gitkeep":
                file_path.unlink()
    return target


results = []

# 1. Primera ejecución completa.
log, code = run("01_primera_ejecucion", REPO, "procesos/cierre_hotel.kjb")
assert successful(log, code), "Falló la primera ejecución"
results.append(("Primera ejecución", "OK: job completo en Kitchen"))

# 2. Repetición sin duplicados.
log, code = run("02_repeticion", REPO, "procesos/cierre_hotel.kjb")
assert successful(log, code), "Falló la repetición"
results.append(("Repetición", "OK: job completo sin duplicar salidas"))

with TemporaryDirectory(prefix="pentaho-a009-") as temporary:
    base = Path(temporary)

    # 3. Falta una entrada en una copia aislada.
    test = copy_case(base / "falta_entrada")
    (test / "entrada" / "cobros_pdi.csv").unlink()
    log, code = run("03_falta_entrada", test, "procesos/cierre_hotel.kjb")
    assert code != 0 and "Finished with errors" in log, "Falta de entrada no hizo fallar el job"
    assert not (test / "salida" / "informe_hotel_canal.csv").exists()
    assert not (test / "salida" / "reservas_sin_cobro.csv").exists()
    results.append(("Falta de entrada", "OK: job fallido y sin salidas publicadas"))

    # 4. Un informe con solo cabecera se rechaza.
    test = copy_case(base / "informe_vacio")
    (test / "temporal" / "informe_hotel_canal.csv").write_text(
        "hotel;canal;n_reservas;cobrado_total\n", encoding="utf-8"
    )
    log, code = run("04_informe_vacio", test, "procesos/validar_informe.ktr", "trans")
    assert failed(log, code), "El validador aceptó un informe vacío"
    results.append(("Informe solo con cabecera", "OK: validador lo rechaza"))

    # 5. Un total aumentado en un euro se rechaza.
    test = copy_case(base / "total_incorrecto")
    report = REPO / "temporal" / "informe_hotel_canal.csv"
    target_report = test / "temporal" / report.name
    target_report.write_bytes(report.read_bytes())
    lines = target_report.read_text(encoding="utf-8-sig").splitlines()
    first = lines[1].split(";")
    first[3] = str(float(first[3]) + 1.0)
    lines[1] = ";".join(first)
    target_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log, code = run("05_total_incorrecto", test, "procesos/validar_informe.ktr", "trans")
    assert failed(log, code), "El validador aceptó el total incorrecto"
    results.append(("Total incorrecto", "OK: validador lo rechaza"))

# 6. Recuperación con las fuentes originales.
log, code = run("06_recuperacion", REPO, "procesos/cierre_hotel.kjb")
assert successful(log, code), "Falló la recuperación"
results.append(("Recuperación", "OK: originales procesados y salidas publicadas"))

(EVIDENCE / "resultado_pruebas_kitchen.csv").write_text(
    "prueba;resultado\n" + "".join(f"{name};{result}\n" for name, result in results),
    encoding="utf-8",
)

for name, result in results:
    print(f"{name}: {result}")
