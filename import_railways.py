import sys
import os

# Add the workspace directory to the path so we can import ingestion modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.railway_importer import RailwayImporter

def main():
    print("Starting Railway Data Ingestion...")
    importer = RailwayImporter()
    success = importer.run()
    if success:
        print("Railway Data Ingestion Complete.")
        sys.exit(0)
    else:
        print("Railway Data Ingestion Failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
