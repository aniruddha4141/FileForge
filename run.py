import sys
import os
import linecache
import tokenize

# Ensure the root of the project is added to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import main

if __name__ == "__main__":
    main()
