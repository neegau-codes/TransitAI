import sys
import os

# Add the workspace directory to the path so we can import ingestion modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.bus_importer import BusImporter

def main():
    print("Starting Bus Data Ingestion...")
    importer = BusImporter()
    success = importer.run()
    if success:
        print("Bus Data Ingestion Complete.")
        sys.exit(0)
    else:
        print("Bus Data Ingestion Failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
