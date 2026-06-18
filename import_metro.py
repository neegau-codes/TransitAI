import sys
import os

# Add the workspace directory to the path so we can import ingestion modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.metro_importer import MetroImporter

def main():
    print("Starting Metro Data Ingestion...")
    importer = MetroImporter()
    success = importer.run()
    if success:
        print("Metro Data Ingestion Complete.")
        sys.exit(0)
    else:
        print("Metro Data Ingestion Failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
