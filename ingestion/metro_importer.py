import json
import os
from ingestion.base_importer import BaseImporter

class MetroImporter(BaseImporter):
    def run(self):
        """Runs the metro data ingestion pipeline."""
        data_path = os.path.join(os.path.dirname(__file__), "data", "metro_routes.json")
        if not os.path.exists(data_path):
            print(f"Error: Metro data file not found at {data_path}")
            return False

        with open(data_path, "r") as f:
            metro_data = json.load(f)

        conn = self.connect()
        cursor = conn.cursor()

        try:
            for route_cfg in metro_data:
                provider = route_cfg["provider"]
                route_name = route_cfg["route_name"]
                
                self.ensure_provider(cursor, provider, "metro")
                print(f"Ingesting metro line: {route_name} run by {provider}")

                for conn_data in route_cfg["connections"]:
                    source = conn_data["source"]
                    destination = conn_data["destination"]
                    duration = conn_data["duration"]
                    cost = conn_data["cost"]
                    distance = conn_data.get("distance_km", 0.0)
                    schedules = conn_data.get("schedules", [])

                    try:
                        source_id = self.get_location_id(cursor, source)
                        dest_id = self.get_location_id(cursor, destination)
                    except ValueError as e:
                        print(f"Warning: Skipping connection: {e}")
                        continue

                    # Insert Route
                    route_id = self.insert_route(
                        cursor=cursor,
                        source_id=source_id,
                        dest_id=dest_id,
                        mode="metro",
                        provider=provider,
                        duration=duration,
                        cost=cost,
                        distance=distance,
                        route_name=route_name
                    )

                    # Generate Schedules
                    for dep_time in schedules:
                        arr_time = self.calculate_arrival(dep_time, duration)
                        self.insert_schedule(cursor, route_id, dep_time, arr_time)

            conn.commit()
            print("Metro data ingestion completed successfully.")
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error during metro ingestion: {e}")
            return False
        finally:
            self.close()

if __name__ == "__main__":
    importer = MetroImporter()
    importer.run()
