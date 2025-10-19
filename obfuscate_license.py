"""
PyArmor Obfuscation Script (uses Blender's Python if available)

- Finds Blender's bundled Python (or uses sys.executable if already inside Blender).
- Uses Blender's Python to invoke `python -m pyarmor.cli ...` to avoid ABI/ABI-mismatch issues.
- Obfuscates only the listed license-related files and writes output into dist_obfuscated.
"""

import os
import sys
import subprocess
import shutil
import glob
from pathlib import Path

FILES_TO_OBFUSCATE = [
    "io_scene_niftools/license_check.py",
    "io_scene_niftools/operators/nif_export_op.py",
    "io_scene_niftools/operators/nif_import_op.py",
    "io_scene_niftools/operators/kf_export_op.py",
    "io_scene_niftools/operators/kf_import_op.py",
    "io_scene_niftools/operators/egm_import_op.py",
]

# Configure output directories and runtime folder name used by your addon
DIST_DIR_NAME = "dist_obfuscated"
RUNTIME_FOLDER_NAME = "pyarmor_runtime_000000"  # keep same name as your imports expect
RUNTIME_OUTPUT_PATH = os.path.join("dependencies", RUNTIME_FOLDER_NAME)  # where to place runtime


def is_running_in_blender():
    """Return True if current Python looks like Blender's bundled interpreter."""
    exe = Path(sys.executable).name.lower()
    full = str(sys.executable).lower()
    return ("blender" in exe) or ("blender foundation" in full) or ("blender" in full)


def find_blender_python_on_windows():
    """
    Try common Blender install paths on Windows.
    Returns full path to python.exe (or None).
    """
    candidates = []

    # Common Program Files locations (look for folder pattern Blender*/<version>/python/bin/python.exe)
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")

    # search patterns under Program Files and Program Files (x86)
    for base in (program_files, program_files_x86):
        pattern = os.path.join(base, "Blender Foundation", "Blender*", "*", "python", "bin", "python.exe")
        candidates += glob.glob(pattern)

    # Some portable/alternate installs: top-level Blender*/4.5/python/bin/python.exe
    pattern2 = os.path.join(program_files, "Blender Foundation", "Blender*", "python", "bin", "python.exe")
    candidates += glob.glob(pattern2)

    # Common AppData/local installs or user installs
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        pattern3 = os.path.join(local_appdata, "Programs", "Blender Foundation", "Blender*", "python", "bin", "python.exe")
        candidates += glob.glob(pattern3)

    # Also look around user's AppData Roaming (less common for installed binary, but won't hurt)
    appdata = os.environ.get("APPDATA")
    if appdata:
        pattern4 = os.path.join(appdata, "Blender Foundation", "Blender*", "python", "bin", "python.exe")
        candidates += glob.glob(pattern4)

    # Deduplicate and check existence
    seen = set()
    results = []
    for p in candidates:
        if p and p not in seen and Path(p).is_file():
            seen.add(p)
            results.append(p)
    return results[0] if results else None


def find_blender_python():
    """Return the best guess for Blender's python executable, or None."""
    # 1) If already running inside Blender, use sys.executable
    if is_running_in_blender():
        return sys.executable

    # 2) Try to find Blender Python on Windows
    if os.name == "nt":
        found = find_blender_python_on_windows()
        if found:
            return found

    # 3) Try common unix-like locations (if you use Blender on Linux/mac)
    # (Look for blender executable and assume its sibling python exists)
    possible_unix_paths = [
        "/usr/bin/blender",
        "/usr/local/bin/blender",
        "/snap/bin/blender",
        "/Applications/Blender.app/Contents/Resources/2.*/python/bin/python3"
    ]
    for p in possible_unix_paths:
        # if blender binary exists, try to derive python path
        if Path(p).exists():
            # attempt to find python nearby
            blender_parent = Path(p).parent
            candidate = blender_parent / "python" / "bin" / "python3"
            if candidate.exists():
                return str(candidate)

    # 4) Not found
    return None


def check_pyarmor_available(python_exe):
    """Check that 'python_exe -m pyarmor.cli -h' runs successfully."""
    try:
        proc = subprocess.run([python_exe, "-m", "pyarmor.cli", "-h"],
                              capture_output=True, text=True, timeout=8)
        return proc.returncode == 0
    except Exception:
        return False


def run_pyarmor_gen_file(python_exe, src_path, out_dir):
    """Run: python_exe -m pyarmor.cli gen -O <out_dir> <src_path>"""
    cmd = [python_exe, "-m", "pyarmor.cli", "gen", "-O", out_dir, src_path]
    print("  Command:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def run_pyarmor_gen_runtime(python_exe, platform_tag, out_dir):
    """Run: python_exe -m pyarmor.cli gen runtime --platform <tag> -O <out_dir>"""
    cmd = [python_exe, "-m", "pyarmor.cli", "gen", "runtime", "--platform", platform_tag, "-O", out_dir]
    print("  Command:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def obfuscate_files():
    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / DIST_DIR_NAME

    # prepare dist dir
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    print("Project root:", project_root)
    print("Output dist dir:", dist_dir)

    blender_python = find_blender_python()
    if blender_python:
        print("Detected Blender Python:", blender_python)
    else:
        print("\n⚠️  Blender Python not found automatically.")
        print("Falling back to current Python interpreter (may cause ABI mismatch).")
        blender_python = sys.executable

    # Check pyarmor availability with chosen python
    if not check_pyarmor_available(blender_python):
        print("\n✗ pyarmor.cli not available for this Python interpreter:")
        print("  Interpreter:", blender_python)
        print("Install PyArmor into that interpreter with:")
        print(f"  {blender_python} -m pip install --user --upgrade pyarmor")
        sys.exit(1)

    # Optionally: generate a runtime for the target platform once (free mode).
    # Uncomment the next block if you want the script to also produce the runtime automatically.
    """
    print("\nGenerating PyArmor runtime for Windows x86_64...")
    rc, out, err = run_pyarmor_gen_runtime(blender_python, "windows.x86_64", str(RUNTIME_OUTPUT_PATH))
    if rc != 0:
        print("✗ Failed to generate runtime:")
        print(err or out)
        print("You can try running the following manually:")
        print(f"  {blender_python} -m pyarmor.cli gen runtime --platform windows.x86_64 -O {RUNTIME_OUTPUT_PATH}")
        # But we won't abort; you can still obfuscate files without regenerating runtime here.
    else:
        print("✓ Runtime generated at:", RUNTIME_OUTPUT_PATH)
    """

    # Obfuscate each file
    for rel in FILES_TO_OBFUSCATE:
        src = project_root / rel
        if not src.exists():
            print(f"\n✗ File not found, skipping: {src}")
            continue

        print(f"\n→ Obfuscating: {rel}")
        rc, out, err = run_pyarmor_gen_file(blender_python, str(src), str(dist_dir))
        if rc == 0:
            print("  ✓ Successfully obfuscated")
            # Optionally print a short path to obf file(s)
            print("  Output directory:", dist_dir)
        else:
            print("  ✗ Obfuscation failed")
            if err:
                print("  Error (stderr):", err.strip())
            if out:
                print("  Output (stdout):", out.strip())

    print("\nObfuscation complete.")
    print("Check the dist folder, copy files back to your addon when satisfied.")
    print("Note: if you plan to run in Blender, ensure the runtime (pyarmor_runtime_000000) is built with Blender's Python.")


if __name__ == "__main__":
    try:
        obfuscate_files()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(1)
