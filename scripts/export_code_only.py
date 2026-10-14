"""Prepare a new code-only checkout without copying any existing Git history."""
import hashlib
import json
import shutil
from pathlib import Path

from check_repository_privacy import confidential_path

ROOT = Path(__file__).resolve().parents[1]


def export(target: Path) -> dict:
    target = target.resolve()
    if not target.is_relative_to((ROOT / ".runtime").resolve()):
        raise ValueError("Export must stay under the local runtime directory")
    if target.exists():
        raise ValueError("Choose a new empty export path; existing files will not be overwritten")
    names = {".gitignore", ".python-version", "AGENTS.md", "README.md", "pyproject.toml", "uv.lock", "docs/DATASET_CARD.md", "docs/DATA_PRIVACY.md", "docs/DATASET_ZIP_SCHEMA.md", "docs/PORTFOLIO_PLAN.md", "powerbi/README.md", "data/README.md", "dashboard/index.html", "dashboard/engineering.js", "dashboard/care.js"}
    for pattern in ["scripts/*.py", "scripts/*.mjs", "scripts/*.R", "tests/*.py", ".github/workflows/*.yml"]:
        names.update(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern))
    for name in names:
        if confidential_path(name) or (ROOT / name).is_symlink():
            raise ValueError(f"Disallowed export path: {name}")
    entries = []
    for name in sorted(names):
        source = ROOT / name
        destination = target / name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
        entries.append({"file":name,"sha256":hashlib.sha256(source.read_bytes()).hexdigest()})
    report = {"directory":str(target),"files":entries,"contains_git_history":False,"contains_real_data":False,"scope":"Explicit code/methodology allowlist; review before initializing a fresh repository"}
    (ROOT / ".runtime/validation").mkdir(parents=True,exist_ok=True)
    (ROOT / ".runtime/validation/code_export.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"Code-only export: {len(entries)} files, no Git history, no data directories.")
    return report


if __name__ == "__main__":
    export(ROOT / ".runtime/portfolio-code")
