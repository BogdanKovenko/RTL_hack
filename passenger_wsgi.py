import sys
import os

INTERP = os.path.expanduser("~/venv/bin/python")  # Измените flaskenv на venv
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

sys.path.append(os.getcwd())
from main import app
application = app
