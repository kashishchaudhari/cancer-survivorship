"""Reject confidential data paths in the Git index. Does not certify history."""
import subprocess
from pathlib import PurePosixPath

BLOCKED_FILES = {"docs/RESULTS.md", "docs/CARE_EQUITY.md", "PROJECT_REVIEW.md"}
BLOCKED_DIRS = {"outputs", ".runtime", ".tools", ".venv"}
BLOCKED_EXTENSIONS = {".zip", ".rar", ".xlsx", ".xlsb", ".parquet", ".sav", ".pbix", ".csv"}


def confidential_path(name: str) -> bool:
    path = PurePosixPath(name)
    return (name in BLOCKED_FILES or path.parts[0] in BLOCKED_DIRS
            or name.startswith("data/local/") or name.startswith("dashboard/data/")
            or path.suffix.lower() in BLOCKED_EXTENSIONS)


if __name__ == "__main__":
    tracked = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
    blocked = [name for name in tracked if name and confidential_path(name)]
    if blocked:
        raise SystemExit("Confidential paths still tracked:\n" + "\n".join(blocked))
    print("Git index contains no blocked data paths. Historical commits require a separate audit.")
