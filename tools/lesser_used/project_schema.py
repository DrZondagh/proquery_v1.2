# tools/project_schema.py — FIXED & PERFECT
from pathlib import Path

IGNORE = {
    '.venv', '.venv1', '.git', '__pycache__', '.idea',
    'build', 'dist', 'node_modules', '.pytest_cache'
}

def tree(dir_path: Path, prefix: str = "") -> None:
    """Print a directory tree, ignoring junk folders"""
    # Get all entries and filter out ignored ones
    contents = [p for p in dir_path.iterdir() if p.name not in IGNORE]
    # Sort directories first, then files
    contents = sorted(contents, key=lambda p: (p.is_file(), p.name.lower()))

    # Build pointers (├── or └──)
    pointers = ["├── "] * (len(contents) - 1) + (["└── "] if contents else [])

    for pointer, path in zip(pointers, contents):
        if path.is_dir():
            print(prefix + pointer + path.name + "/")
            # Decide next prefix (continues the tree line)
            extension = "│   " if pointer == "├── " else "    "
            tree(path, prefix + extension)
        else:
            print(prefix + pointer + path.name)

if __name__ == "__main__":
    # Go up two levels from this file → project root
    root = Path(__file__).parent.parent
    print(f"Project Structure — {root.name}/\n")
    tree(root)
    print("\nDone.")