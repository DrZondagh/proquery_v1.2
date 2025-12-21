# run_local.py (in project root)
from src.main import app

if __name__ == '__main__':
    app.run(debug=True, port=5000)