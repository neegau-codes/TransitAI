import json
import os
from ingestion.base_importer import BaseImporter

class BusImporter(BaseImporter):
    def run(self):
        """Runs the bus data ingestion pipeline."""
        data_path = os.path.join(os.path.dirname(__file__), "data", "bus_routes.json")
        if not os.path.exists(data_path):
            print(f"Error: Bus data file not found at {data_path}")
            return False

        with open(data_path, "r") as f:
            bus_data = json.load(f)

        conn = self.connect()
        cursor = conn.cursor()

        try:
            for bus_route in bus_data:
                route_name = bus_route["route_name"]
                provider = bus_route["provider"]
                source = bus_route["source"]
                destination = bus_route["destination"]
                duration = bus_route["duration_minutes"]
                cost = bus_route["cost"]
                distance = bus_route.get("distance_km", 0.0)
                schedules = bus_route["schedules"]

                self.ensure_provider(cursor, provider, "bus")

                print(f"Ingesting bus route: {route_name} run by {provider}")

                try:
                    source_id = self.get_location_id(cursor, source)
                    dest_id = self.get_location_id(cursor, destination)
                except ValueError as e:
                    print(f"Warning: Skipping bus route: {e}")
                    continue

                # Insert Route
                route_id = self.insert_route(
                    cursor=cursor,
                    source_id=source_id,
                    dest_id=dest_id,
                    mode="bus",
                    provider=provider,
                    duration=duration,
                    cost=cost,
                    distance=distance,
                    route_name=route_name
                )

                # Insert Schedules
                for dep_time in schedules:
                    arr_time = self.calculate_arrival(dep_time, duration)
                    self.insert_schedule(cursor, route_id, dep_time, arr_time)

            conn.commit()
            print("Bus data ingestion completed successfully.")
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error during bus ingestion: {e}")
            return False
        finally:
            self.close()

if __name__ == "__main__":
    importer = BusImporter()
    importer.run()
