import sqlite3
import re
import os
import json
from database.db import DATABASE_PATH

class DataValidator:
    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH

    def run_validation(self) -> dict:
        """Runs all validations and returns a report dictionary."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        report = {
            "duplicate_routes": [],
            "missing_stations": [],
            "invalid_schedules": [],
            "circular_routes": [],
            "isolated_locations": [],
            "summary": {
                "total_locations": 0,
                "total_routes": 0,
                "total_schedules": 0,
                "passed": True
            }
        }

        try:
            # Gather totals
            cursor.execute("SELECT count(*) FROM locations")
            report["summary"]["total_locations"] = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM routes")
            report["summary"]["total_routes"] = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM schedules")
            report["summary"]["total_schedules"] = cursor.fetchone()[0]

            # 1. Circular Routes (source == destination)
            cursor.execute("""
                SELECT r.id, r.route_name, r.transport_mode, l.name as station_name 
                FROM routes r
                JOIN locations l ON r.source_location_id = l.id
                WHERE r.source_location_id = r.destination_location_id
            """)
            for row in cursor.fetchall():
                report["circular_routes"].append({
                    "route_id": row["id"],
                    "route_name": row["route_name"],
                    "mode": row["transport_mode"],
                    "station": row["station_name"]
                })

            # 2. Duplicate Routes (same source, destination, mode, provider, route_name)
            cursor.execute("""
                SELECT source_location_id, destination_location_id, transport_mode, provider, route_name, count(*) as count
                FROM routes
                GROUP BY source_location_id, destination_location_id, transport_mode, provider, route_name
                HAVING count > 1
            """)
            for row in cursor.fetchall():
                cursor.execute("SELECT name FROM locations WHERE id = ?", (row["source_location_id"],))
                src_name = cursor.fetchone()["name"]
                cursor.execute("SELECT name FROM locations WHERE id = ?", (row["destination_location_id"],))
                dst_name = cursor.fetchone()["name"]
                report["duplicate_routes"].append({
                    "source": src_name,
                    "destination": dst_name,
                    "mode": row["transport_mode"],
                    "provider": row["provider"],
                    "route_name": row["route_name"],
                    "occurrences": row["count"]
                })

            # 3. Invalid Schedules
            # A schedule is invalid if:
            # - Departure/arrival times don't match HH:MM
            # - Duration is negative (unless it crosses midnight, check time math)
            cursor.execute("""
                SELECT s.id as schedule_id, r.id as route_id, r.route_name, s.departure_time, s.arrival_time, r.duration_minutes
                FROM schedules s
                JOIN routes r ON s.route_id = r.id
            """)
            time_pattern = re.compile(r"^\d{2}:\d{2}$")
            for row in cursor.fetchall():
                dep = row["departure_time"]
                arr = row["arrival_time"]
                
                # Format check
                if not time_pattern.match(dep) or not time_pattern.match(arr):
                    report["invalid_schedules"].append({
                        "schedule_id": row["schedule_id"],
                        "route_id": row["route_id"],
                        "route_name": row["route_name"],
                        "departure": dep,
                        "arrival": arr,
                        "issue": "Invalid time format (must be HH:MM)"
                    })
                    continue

                # Parse minutes
                try:
                    dh, dm = map(int, dep.split(":"))
                    ah, am = map(int, arr.split(":"))
                    if dh < 0 or dh > 23 or dm < 0 or dm > 59 or ah < 0 or ah > 23 or am < 0 or am > 59:
                        raise ValueError()
                except ValueError:
                    report["invalid_schedules"].append({
                        "schedule_id": row["schedule_id"],
                        "route_id": row["route_id"],
                        "route_name": row["route_name"],
                        "departure": dep,
                        "arrival": arr,
                        "issue": "Out-of-range hours/minutes"
                    })
                    continue

                # Duration check (crosses midnight vs standard)
                dep_mins = dh * 60 + dm
                arr_mins = ah * 60 + am
                calc_dur = arr_mins - dep_mins if arr_mins >= dep_mins else (1440 - dep_mins) + arr_mins
                
                # Accept a tiny mismatch (e.g. 1 min) but flag large ones
                if abs(calc_dur - row["duration_minutes"]) > 2:
                    report["invalid_schedules"].append({
                        "schedule_id": row["schedule_id"],
                        "route_id": row["route_id"],
                        "route_name": row["route_name"],
                        "departure": dep,
                        "arrival": arr,
                        "route_duration": row["duration_minutes"],
                        "computed_duration": calc_dur,
                        "issue": f"Duration mismatch: route lists {row['duration_minutes']}m, schedule implies {calc_dur}m"
                    })

            # 4. Isolated / Unlinked Locations (no incoming OR outgoing routes, excluding walk)
            cursor.execute("""
                SELECT l.id, l.name, l.city
                FROM locations l
                WHERE l.id NOT IN (SELECT source_location_id FROM routes WHERE transport_mode != 'walk')
                  AND l.id NOT IN (SELECT destination_location_id FROM routes WHERE transport_mode != 'walk')
            """)
            for row in cursor.fetchall():
                report["isolated_locations"].append({
                    "id": row["id"],
                    "name": row["name"],
                    "city": row["city"]
                })

            # Determine pass/fail
            issues_found = (
                len(report["duplicate_routes"]) > 0 or
                len(report["circular_routes"]) > 0 or
                len(report["invalid_schedules"]) > 0
            )
            report["summary"]["passed"] = not issues_found

        except Exception as e:
            report["summary"]["passed"] = False
            report["summary"]["error"] = str(e)
            print(f"Error during validation: {e}")
        finally:
            conn.close()

        # Write report to file
        report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "validation_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def print_report(self, report: dict):
        """Prints a human-readable summary of the validation report."""
        print("=" * 60)
        print("               TransitAI Data Validation Report")
        print("=" * 60)
        print(f"Total Locations: {report['summary']['total_locations']}")
        print(f"Total Routes:    {report['summary']['total_routes']}")
        print(f"Total Schedules: {report['summary']['total_schedules']}")
        print("-" * 60)
        
        status = "PASSED" if report["summary"]["passed"] else "FAILED (Issues Found)"
        print(f"Validation Status: {status}")
        
        if report["circular_routes"]:
            print(f"\n[WARNING] Circular Routes Detected ({len(report['circular_routes'])}):")
            for r in report["circular_routes"]:
                print(f"  - Route #{r['route_id']} '{r['route_name']}' ({r['mode']}) loops on station '{r['station']}'")

        if report["duplicate_routes"]:
            print(f"\n[WARNING] Duplicate Routes Detected ({len(report['duplicate_routes'])}):")
            for r in report["duplicate_routes"]:
                print(f"  - {r['route_name']} ({r['mode']} by {r['provider']}): {r['source']} -> {r['destination']} ({r['occurrences']} duplicates)")

        if report["invalid_schedules"]:
            print(f"\n[ERROR] Invalid Schedules/Timetables Detected ({len(report['invalid_schedules'])}):")
            for r in report["invalid_schedules"]:
                print(f"  - Route '{r['route_name']}' schedule #{r['schedule_id']} ({r['departure']} -> {r['arrival']}): {r['issue']}")

        if report["isolated_locations"]:
            print(f"\n[INFO] Isolated / Unlinked Locations ({len(report['isolated_locations'])}):")
            for r in report["isolated_locations"]:
                print(f"  - Station '{r['name']}' in {r['city']} has no transit routes (walk excluded)")

        print("=" * 60)

if __name__ == "__main__":
    validator = DataValidator()
    report = validator.run_validation()
    validator.print_report(report)
