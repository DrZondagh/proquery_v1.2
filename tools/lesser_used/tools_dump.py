# show_tools.py
# Save this in your permanent safe folder, e.g. C:\Users\drzon\my-pycharm-tools\show_tools.py

from pathlib import Path

TOOLS_FOLDER = Path(r"/tools")

for py_file in sorted(TOOLS_FOLDER.glob("*.py")):
    print(f"\n{'='*20}  {py_file.name}  {'='*20}\n")
    print(py_file.read_text(encoding="utf-8").rstrip())
    print("\n" + "="*80 + "\n")