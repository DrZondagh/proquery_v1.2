# tools/entire_proquery_for_grok.py — DUMPS ALL CODE EXCEPT tools/ FOLDER
from pathlib import Path

EXCLUDE_DIRS = {
    '.git', '__pycache__', '.venv', '.venv1', 'venv', '.idea',
    'build', 'dist', '.pytest_cache', 'node_modules',
    'tools'          # ← THIS LINE HIDES THE ENTIRE tools/ FOLDER
}

EXCLUDE_FILES = {
    '.env', '.gitignore', 'Thumbs.db', '.DS_Store'
}

root = Path(__file__).parent.parent

print("PROQUERY FULL CLEAN CODE DUMP".center(80, "="))
print(f"Root: {root}\n")

count = 0
for file in sorted(root.rglob("*.py")):
    # Skip any file inside excluded dirs (including tools/)
    if any(part in EXCLUDE_DIRS for part in file.parts):
        continue
    if file.name in EXCLUDE_FILES:
        continue
    if file.stat().st_size > 5_000_000:
        print(f"SKIPPED (too big): {file.relative_to(root)}")
        continue

    count += 1
    rel = file.relative_to(root)
    print(f"\nFILE {count}: {rel}")
    print("-" * 80)
    try:
        print(file.read_text(encoding="utf-8", errors="replace").rstrip())
    except Exception as e:
        print(f"[READ ERROR: {e}]")
    print("\n" + "=" * 80)

print(f"DONE — {count} Python files dumped. Ready for Grok!")