"""Paths and process arguments shared by source and frozen distributions."""
import os
from pathlib import Path


def restart_command(executable, argv, frozen=False):
    return [executable, *argv[1:]] if frozen else [executable, *argv]


def prepare_user_data(user_path, resource_path):
    """Create writable data folders and copy bundled examples on first run."""
    import shutil
    for name in ("user_layouts", "user_scripts", "user_sounds"):
        target = Path(user_path) / name
        target.mkdir(parents=True, exist_ok=True)
        source = Path(resource_path) / name / "examples"
        if source.is_dir():
            for item in source.iterdir():
                destination = target / "examples" / item.name
                if item.is_file() and not destination.exists():
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, destination)


def sound_path(root, filename):
    return os.path.join(root, "user_sounds", *filename.replace("\\", "/").split("/"))
