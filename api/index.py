import sys
import os

# Backend modüllerini içe aktarmak için path ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from main import app
