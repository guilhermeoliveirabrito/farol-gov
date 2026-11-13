import sys
from pathlib import Path

# deixa importar tests.fakes e o pacote sem precisar de pip install
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
