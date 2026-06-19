"""
scheduler.py
Provides schedule-aware time and transfer checking utility functions.
"""

from typing import List, Optional

def time_to_mins(time_str: str) -> int:
    """
    Converts a time string in HH:MM format to minutes since midnight.
    Handles extra characters like spaces and seconds gracefully.
    """
    try:
        # Strip potential suffixes or seconds (e.g., '09:30:00' -> '09:30')
        clean_time = time_str.strip().split()[0]
        parts = clean_time.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except Exception:
        return 0

def mins_to_time(mins: int) -> str:
    """
    Converts minutes since midnight to a time string in HH:MM format.
    Wraps around 24 hours (1440 minutes) if overflow occurs.
    """
    mins = mins % 1440
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

def is_valid_transfer(
    arr_time_str: str, 
    dep_time_str: str, 
    min_transfer_time: int = 5, 
    max_transfer_time: int = 180
) -> bool:
    """
    Checks if transferring from one service arriving at arr_time_str to 
    another departing at dep_time_str is valid.
    
    If the departure time is less than the arrival time, it assumes a
    next-day transfer (midnight rollover) and adds 1440 minutes.
    """
    arr_mins = time_to_mins(arr_time_str)
    dep_mins = time_to_mins(dep_time_str)
    
    if dep_mins < arr_mins:
        dep_mins += 1440  # Next-day departure
        
    wait_time = dep_mins - arr_mins
    return min_transfer_time <= wait_time <= max_transfer_time

def get_next_departure(
    schedule: List[str], 
    current_time_str: str, 
    min_wait: int = 0
) -> Optional[str]:
    """
    Finds the earliest departure time in the schedule that is at least
    min_wait minutes after current_time_str.
    
    If no more departures are scheduled today, returns the first departure
    of the next day (rollover).
    """
    if not schedule:
        return None
        
    current_mins = time_to_mins(current_time_str)
    ready_mins = current_mins + min_wait
    
    # Parse and sort schedule
    sched_mins = []
    for t in schedule:
        sched_mins.append((time_to_mins(t), t))
    sched_mins.sort(key=lambda x: x[0])
    
    # Look for departures today
    for mins, t_str in sched_mins:
        if mins >= ready_mins:
            return t_str
            
    # Rollover to next day - return the first scheduled run tomorrow
    return sched_mins[0][1]

def calculate_waiting_time(
    arrival_time_str: str, 
    departure_time_str: str
) -> int:
    """
    Calculates waiting time in minutes between arrival at a station 
    and departure of the next transit connection.
    """
    arr_mins = time_to_mins(arrival_time_str)
    dep_mins = time_to_mins(departure_time_str)
    
    if dep_mins < arr_mins:
        dep_mins += 1440  # Next-day rollover
        
    return dep_mins - arr_mins
