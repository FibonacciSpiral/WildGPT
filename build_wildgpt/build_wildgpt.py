# build.py
from __future__ import annotations

import os
from pathlib import Path
import PyInstaller.__main__ as pyim


def _datas_arg(src_dir: Path, dst_name: str) -> list[str]:
    """Create a cross-platform --add-data argument (handles ; on Win, : elsewhere)."""
    if not src_dir.exists():
        return []
    sep = ";" if os.name == "nt" else ":"
    return ["--add-data", f"{src_dir}{sep}{dst_name}"]


def _pick_entry(root: Path) -> Path:
    """
    Try a few common entrypoints, in order of preference.
    Adjust the list if your project differs.
    """
    for p in (
        root / "src" / "wildgpt.py",
        root / "src" / "main.py",
        root / "main.py",
    ):
        if p.exists():
            return p
    raise FileNotFoundError(
        "Could not find an entry script. Looked for: src/wildgpt.py, src/main.py, main.py"
    )


def build(
    onefile: bool = True,
    noconsole: bool = True,
    name: str = "WildGPT",
    dist: str = "Build/dist",
    work: str = "Build/build",
    specs: str = "Build/specs",
) -> None:
    root = Path(__file__).parent.parent.resolve()
    print(str(root))
    entry = _pick_entry(root)

    # Optional dependencies
    dependencies_dir = root / "Dependencies"
    icon = dependencies_dir / "wildAI.ico"

    args: list[str] = [
        str(entry),
        f"--name={name}",
        f"--distpath={dist}",
        f"--workpath={work}",
        f"--specpath={specs}",
    ]

    if onefile:
        args.append("--onefile")
    if noconsole:
        args.append("--noconsole")
    if icon.exists():
        args.append(f"--icon={icon}")

    # Only include resources that actually exist
    # args += _datas_arg(dependencies_dir, "Dependencies")

    # Print for sanity, then run
    print("\nPyInstaller args:\n  " + " \\\n  ".join(args) + "\n")
    pyim.run(args)


build()

