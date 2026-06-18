import json
import os
from ingestion.base_importer import BaseImporter

class RailwayImporter(BaseImporter):
    def run(self):
        """Runs the railway data ingestion pipeline."""
        data_path = os.path.join(os.path.dirname(__file__), "data", "railway_routes.json")
        if not os.path.exists(data_path):
            print(f"Error: Railway data file not found at {data_path}")
            return False

        with open(data_path, "r") as f:
            railway_data = json.load(f)

        conn = self.connect()
        cursor = conn.cursor()

        try:
            for train in railway_data:
                train_num = train["train_number"]
                train_name = train["train_name"]
                provider = train["provider"]
                stops = train["stops"]

                self.ensure_provider(cursor, provider, "train")

                full_route_name = f"{train_name} ({train_num})"
                print(f"Ingesting train: {full_route_name}")

                # Loop through stops to create segment links
                for i in range(len(stops) - 1):
                    src_stop = stops[i]
                    dst_stop = stops[i+1]

                    source = src_stop["station"]
                    destination = dst_stop["station"]
                    
                    try:
                        source_id = self.get_location_id(cursor, source)
                        dest_id = self.get_location_id(cursor, destination)
                    except ValueError as e:
                        print(f"Warning: Skipping train stop link: {e}")
                        continue

                    # Calculate duration
                    dep_time = src_stop["departure"]
                    arr_time = dst_stop["arrival"]
                    
                    dep_mins = self.time_to_mins(dep_time)
                    arr_mins = self.time_to_mins(arr_time)
                    
                    if arr_mins < dep_mins:
                        # Crosses midnight
                        duration = (1440 - dep_mins) + arr_mins
                    else:
                        duration = arr_mins - dep_mins

                    # Cost and distance diffs
                    cost = max(dst_stop["cost"] - src_stop["cost"], 10.0) # Ensure a minimum fare if cost is 0
                    distance = max(dst_stop["distance_km"] - src_stop["distance_km"], 1.0)

                    # Insert Route
                    route_id = self.insert_route(
                        cursor=cursor,
                        source_id=source_id,
                        dest_id=dest_id,
                        mode="train",
                        provider=provider,
                        duration=duration,
                        cost=cost,
                        distance=distance,
                        route_name=full_route_name
                    )

                    # Insert Schedule
                    self.insert_schedule(cursor, route_id, dep_time, arr_time)

            conn.commit()
            print("Railway data ingestion completed successfully.")
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error during railway ingestion: {e}")
            return False
        finally:
            self.close()

if __name__ == "__main__":
    importer = RailwayImporter()
    importer.run()
