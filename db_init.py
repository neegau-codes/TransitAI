import sys
import os

# Add the workspace directory to the path so we can import rebuild_database
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rebuild_database import rebuild_db

if __name__ == "__main__":
    rebuild_db()
