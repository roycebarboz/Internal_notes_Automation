"""
Internal Events Notes Generator

This script automates the generation of Internal Events Notes from Coursedog CSV exports.
It normalizes the CSV data, applies business rules for setup/breakdown times, and generates
formatted notes for events marked with Process_Event = YES.
"""

import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

# =============================================================================
# CONFIGURATION DICTIONARIES
# =============================================================================

VENUE_CODES = {
    # UCC TechFlex Spaces
    "UCC Tech Flex Space A": "UCCA",
    "UCC Tech Flex Space B": "UCCB",
    "UCC Tech Flex Space C": "UCCC",
    # UCC Rooms
    "UCC 106": "UCCG",
    "UCC The Commons": "UCCCOMMONS",
    "UCC 1st Floor Lobby": "UCCLOBBY",
    "UCC Pi Kitchen": "UCCPI",
    "UCC Pre-function": "UCCPRE",
    # Babbio
    "Babbio 100": "BC100",
    "Babbio 104": "BC104",
    "Babbio 122": "BC122",
    "Babbio 202": "BC202",
    "Babbio 203": "BC203",
    "Babbio 210": "BC210",
    "Babbio 212": "BC212",
    "Babbio 219": "BC219",
    "Babbio 220": "BC220",
    "Babbio 221": "BC221",
    "Babbio 304": "BC304",
    "Babbio 310": "BC310",
    "Babbio 312": "BC312",
    "Babbio 319": "BC319",
    "Babbio 320": "BC320",
    "Babbio 321": "BC321",
    "Babbio East Patio": "BCEASTPATIO",
    # Howe
    "Howe 102": "HOWE102",
    "Howe 104": "HOWE104",
    "Howe 303": "HOWE303",
    "Howe 404": "SKYLINE",
    "Howe 409": "BISSINGER",
    "Howe 1017": "HOWE1017",
    "Howe 4th Floor": "HOWE4",
    # Walker
    "Walker Gym": "WALKERGYM",
    "Walker 102": "WALKER102",
    # Gateway
    "Gateway South": "GWS",
    "Gateway North": "GWN",
    # Schaefer
    "Schaefer Swimming Pool": "SCHPOOL",
    "Schaefer Wrestling Room": "SCHWRESTLING",
    "Schaefer Canavan Arena": "SCHCANAVAN",
    "Schaefer Athletic Training": "SCHATC",
    "Schaefer DeBaun Field": "SCHFIELD",
    "Schaefer 309": "SCH309",
    # DeBaun
    "DeBaun Auditorium": "DEBAUN",
    # Other buildings
    "Burchard": "BURCH",
    "Carnegie": "CARN",
    "Edwin A. Stevens": "EAS",
    "McLean": "MCLEAN",
    "Morton": "MORTON",
    "Peirce": "PEIRCE",
    "North Building": "NORTH",
    "Martha Bayard Stevens": "MBS",
    "Griffith": "GRIFF",
    "Library": "LIB",
    "Kidde": "KIDDE",
}

SETUP_LABELS = {
    # TechFlex venues
    "UCCA": "TechFlex",
    "UCCB": "TechFlex",
    "UCCC": "TechFlex",
    "UCCABC": "TechFlex",
    # UCC
    "UCCG": "Gallery",
    "UCCCOMMONS": "UCC The Commons",
    "UCCLOBBY": "UCC 1st Floor Lobby",
    "UCCPI": "UCC PI Kitchen",
    "UCCPRE": "UCC Pre-function",
    # Babbio
    "BC100": "Babbio 100",
    "BC104": "Babbio 104",
    "BC122": "Babbio 122",
    "BC202": "Babbio 202",
    "BC203": "Babbio 203",
    "BC210": "Babbio 210",
    "BC212": "Babbio 212",
    "BC219": "Babbio 219",
    "BC220": "Babbio 220",
    "BC221": "Babbio 221",
    "BC304": "Babbio 304",
    "BC310": "Babbio 310",
    "BC312": "Babbio 312",
    "BC319": "Babbio 319",
    "BC320": "Babbio 320",
    "BC321": "Babbio 321",
    "BCEASTPATIO": "Babbio East Patio",
    # Howe
    "HOWE102": "HOWE 102",
    "HOWE104": "HOWE 104",
    "HOWE303": "HOWE 303",
    "SKYLINE": "SKYLINE",
    "BISSINGER": "BISSINGER",
    "HOWE1017": "HOWE 1017",
    "HOWE4": "HOWE 4th Floor",
    # Walker
    "WALKERGYM": "Walker Gym",
    "WALKER102": "Walker 102",
    # Gateway
    "GWS": "GATEWAY SOUTH",
    "GWN": "GATEWAY NORTH",
    # Schaefer
    "SCHPOOL": "Schaefer Swimming Pool",
    "SCHWRESTLING": "Schaefer Wrestling Room",
    "SCHCANAVAN": "Schaefer Canavan Arena",
    "SCHATC": "Schaefer Athletic Training",
    "SCHFIELD": "Schaefer DeBaun Field",
    "SCH309": "Schaefer 309",
    # DeBaun
    "DEBAUN": "DeBaun Auditorium",
    # Other
    "BURCH": "Burchard",
    "CARN": "Carnegie",
    "EAS": "Edwin A. Stevens",
    "MCLEAN": "McLean",
    "MORTON": "Morton",
    "PEIRCE": "Peirce",
    "NORTH": "North Building",
    "MBS": "Martha Bayard Stevens",
    "GRIFF": "Griffith",
    "LIB": "Library",
    "KIDDE": "Kidde",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_venue_code(location):
    """Get venue code from location string using partial matching."""
    for key, code in VENUE_CODES.items():
        if key in location:
            return code
    return location[:10].upper().replace(" ", "")  # Fallback


def get_setup_label(venue_code):
    """Get setup label from venue code."""
    return SETUP_LABELS.get(venue_code, venue_code)


def parse_date_time(date_time_str):
    """
    Parse date/time string from CSV.
    Handles formats like:
    - "Feb 5, 2026 10:00 AM - 12:00 PM"
    - "5-Feb-26"
    Returns tuple: (date, start_time, end_time) or (date, None, None) for date-only
    """
    date_time_str = date_time_str.strip()
    
    # Check for date-only format like "5-Feb-26"
    if " - " not in date_time_str and ":" not in date_time_str:
        try:
            dt = datetime.strptime(date_time_str, "%d-%b-%y")
            return dt.date(), None, None
        except ValueError:
            pass
    
    # Handle full datetime range like "Feb 5, 2026 10:00 AM - 12:00 PM"
    try:
        # Split by " - " to separate start and end times
        if " - " in date_time_str:
            parts = date_time_str.split(" - ")
            start_part = parts[0].strip()
            end_part = parts[1].strip()
            
            # Parse start datetime
            start_dt = datetime.strptime(start_part, "%b %d, %Y %I:%M %p")
            event_date = start_dt.date()
            start_time = start_dt.time()
            
            # Parse end time (may or may not include date)
            try:
                # Try with full date first (for overnight events)
                end_dt = datetime.strptime(end_part, "%b %d, %Y %I:%M %p")
                end_time = end_dt.time()
            except ValueError:
                # Just time
                end_dt = datetime.strptime(end_part, "%I:%M %p")
                end_time = end_dt.time()
            
            return event_date, start_time, end_time
    except ValueError as e:
        print(f"Warning: Could not parse date/time: {date_time_str} - {e}")
    
    return None, None, None


def format_date_for_output(dt):
    """Format date as 'DAY, MONTH DAY_NO' (e.g., 'Thursday, February 5')"""
    return dt.strftime("%A, %B %d").replace(" 0", " ")


def format_time_for_output(t):
    """Format time as 'H:MM AM/PM'"""
    if t is None:
        return "TBD"
    return t.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")


def is_am_event(start_time):
    """Check if event starts in AM (before noon)."""
    if start_time is None:
        return True
    from datetime import time
    return start_time < time(12, 0)


def calculate_setup_time(event_date, start_time, venue_code, all_events):
    """
    Calculate setup time based on rules:
    - Default: 2 hours before event
    - No setup between 12:00 PM - 1:00 PM
    - Facilities hours: 8:00 AM - 5:00 PM
    - Early events (8 AM): setup at 6 AM (overtime)
    - Evening events with no prior event: setup at 11 AM
    - Weekend events with no back-to-back: Friday setup
    Returns: (setup_datetime, warning_flag)
    """
    from datetime import time, date
    
    warning = ""
    
    if start_time is None:
        return None, ""
    
    event_datetime = datetime.combine(event_date, start_time)
    default_setup = event_datetime - timedelta(hours=2)
    
    # Check for back-to-back events in same venue
    same_venue_events = [e for e in all_events 
                         if e.get("venue_code") == venue_code 
                         and e.get("event_date") == event_date
                         and e.get("end_time") is not None
                         and e.get("start_time") != start_time]
    
    # Check if there's a prior event ending within 30 min of setup time
    for other in same_venue_events:
        if other.get("end_time"):
            other_end = datetime.combine(event_date, other["end_time"])
            gap = (event_datetime - other_end).total_seconds() / 60
            if 0 <= gap < 30:
                warning = " [WARNING: Back-to-back event, verify setup time]"
    
    # Early morning event (before 10 AM) - setup at 6 AM with overtime
    if start_time <= time(10, 0):
        setup_time = time(6, 0)
        return datetime.combine(event_date, setup_time), warning
    
    # Check if event is in evening (after 5 PM) with no prior event same day
    if start_time >= time(17, 0):
        has_prior_event = any(
            e.get("start_time") and e.get("start_time") < start_time
            for e in same_venue_events
        )
        if not has_prior_event:
            setup_time = time(11, 0)
            return datetime.combine(event_date, setup_time), warning
    
    # Weekend check - schedule for Friday if possible
    weekday = event_date.weekday()
    if weekday in (5, 6):  # Saturday or Sunday
        friday = event_date - timedelta(days=(weekday - 4))
        
        # Check if Friday has events in this venue
        friday_events = [e for e in all_events 
                        if e.get("venue_code") == venue_code 
                        and e.get("event_date") == friday]
        
        if not friday_events:
            setup_time = time(11, 0)
            return datetime.combine(friday, setup_time), " [Friday setup]"
    
    # Default: 2 hours before, but avoid lunch break
    setup_hour = default_setup.hour
    setup_minute = default_setup.minute
    
    # If setup would fall during lunch (12-1 PM), move to 11 AM
    if 12 <= setup_hour < 13:
        setup_time = time(11, 0)
        return datetime.combine(event_date, setup_time), warning
    
    return default_setup, warning


def calculate_breakdown_time(event_date, end_time, venue_code, all_events, has_setup):
    """
    Calculate breakdown time based on rules:
    - Default: after event end
    - No breakdown between 12:00 PM - 1:00 PM
    - If event ends after 3 PM: next day in AM
    - Exception: if next day is weekend AND no setups, can be 4 PM
    Returns: (breakdown_datetime_or_str, warning_flag)
    """
    from datetime import time
    
    if end_time is None:
        return None, ""
    
    event_end = datetime.combine(event_date, end_time)
    
    # If event ends after 3 PM
    if end_time >= time(15, 0):
        next_day = event_date + timedelta(days=1)
        next_weekday = next_day.weekday()
        
        # Exception: weekend with no setups
        if next_weekday in (5, 6) and not has_setup:
            breakdown_time = time(16, 0)  # 4 PM
            return datetime.combine(event_date, breakdown_time), ""
        
        # Default: next day in AM (no specific time)
        return f"the next day ({next_day.strftime('%A, %B %d')}) in the AM", ""
    
    # Event ends during lunch break - move to 1 PM
    if 12 <= end_time.hour < 13:
        breakdown_time = time(13, 0)
        return datetime.combine(event_date, breakdown_time), ""
    
    # Default: right after event
    return event_end, ""


# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def normalize_csv(rows):
    """
    Normalize CSV data:
    1. Remove Setup and Teardown rows
    2. Merge TechFlex A, B, C when all booked for same event/date/time
    """
    # Filter out Setup and Teardown
    filtered = [r for r in rows if r.get("Meeting Type", "").strip() not in ("Setup", "Teardown")]
    
    # Group by event name + date/time for TechFlex merging
    techflex_groups = defaultdict(list)
    other_rows = []
    
    for row in filtered:
        location = row.get("Location", "")
        if "UCC Tech Flex Space" in location:
            key = (row.get("Event Name", ""), row.get("Date & Time", ""))
            techflex_groups[key].append(row)
        else:
            other_rows.append(row)
    
    # Process TechFlex groups
    merged_rows = []
    for key, group in techflex_groups.items():
        locations = set(r.get("Location", "") for r in group)
        has_a = any("Space A" in loc for loc in locations)
        has_b = any("Space B" in loc for loc in locations)
        has_c = any("Space C" in loc for loc in locations)
        
        if has_a and has_b and has_c:
            # Merge into single UCCABC row
            merged_row = group[0].copy()
            merged_row["Location"] = "UCC Tech Flex Space ABC"
            merged_row["_venue_code"] = "UCCABC"
            merged_rows.append(merged_row)
        else:
            # Keep individual rows
            merged_rows.extend(group)
    
    return other_rows + merged_rows


def process_events(rows):
    """Process all events and calculate setup/breakdown times."""
    processed = []
    
    # First pass: parse all dates and venue codes
    for row in rows:
        event_date, start_time, end_time = parse_date_time(row.get("Date & Time", ""))
        location = row.get("Location", "")
        
        # Use pre-set venue code for merged TechFlex, otherwise derive it
        venue_code = row.get("_venue_code") or get_venue_code(location)
        
        row["event_date"] = event_date
        row["start_time"] = start_time
        row["end_time"] = end_time
        row["venue_code"] = venue_code
        processed.append(row)
    
    # Second pass: calculate setup/breakdown with context of all events
    for row in processed:
        setup_result, setup_warning = calculate_setup_time(
            row["event_date"], 
            row["start_time"], 
            row["venue_code"],
            processed
        )
        
        has_setup = row.get("Setup_Requirements", "").strip() != ""
        breakdown_result, breakdown_warning = calculate_breakdown_time(
            row["event_date"],
            row["end_time"],
            row["venue_code"],
            processed,
            has_setup
        )
        
        row["setup_datetime"] = setup_result
        row["setup_warning"] = setup_warning
        row["breakdown_result"] = breakdown_result
        row["breakdown_warning"] = breakdown_warning
    
    return processed


def generate_notes(events):
    """Generate Internal Events Notes for events with Process_Event = YES."""
    output_lines = []
    
    # Filter for Process_Event = YES
    to_process = [e for e in events if e.get("Process_Event", "").strip().upper() == "YES"]
    
    # Sort by date and time
    to_process.sort(key=lambda x: (x.get("event_date") or datetime.min.date(), 
                                    x.get("start_time") or datetime.min.time()))
    
    for i, event in enumerate(to_process):
        # Get values
        account_number = event.get("Account Number", "").strip()
        venue_code = event.get("venue_code", "")
        setup_label = get_setup_label(venue_code)
        setup_requirements = event.get("Setup_Requirements", "").strip()
        
        event_date = event.get("event_date")
        start_time = event.get("start_time")
        setup_datetime = event.get("setup_datetime")
        setup_warning = event.get("setup_warning", "")
        breakdown_result = event.get("breakdown_result")
        breakdown_warning = event.get("breakdown_warning", "")
        
        # Format reservation number: MMDDVENUE_CODEAM/PM
        if event_date and start_time:
            am_pm = "AM" if is_am_event(start_time) else "PM"
            reservation_number = f"{event_date.strftime('%m%d')}{venue_code}{am_pm}"
        else:
            reservation_number = f"{venue_code}"
        
        # Format setup line
        if setup_datetime:
            if isinstance(setup_datetime, datetime):
                setup_date_str = format_date_for_output(setup_datetime)
                setup_time_str = format_time_for_output(setup_datetime.time())
                setup_line = f"Please set up on {setup_date_str}, at {setup_time_str}{setup_warning}"
            else:
                setup_line = f"Please set up on {setup_datetime}{setup_warning}"
        else:
            setup_line = "Please set up on TBD"
        
        # Format breakdown line
        if breakdown_result:
            if isinstance(breakdown_result, datetime):
                breakdown_date_str = format_date_for_output(breakdown_result)
                breakdown_time_str = format_time_for_output(breakdown_result.time())
                breakdown_line = f"Please break down on {breakdown_date_str}, at {breakdown_time_str}{breakdown_warning}"
            else:
                breakdown_line = f"Please break down on {breakdown_result}{breakdown_warning}"
        else:
            breakdown_line = "Please break down on TBD"
        
        # Build the note block
        note = f"""Account Number: {account_number}
Reservation Number: {reservation_number}
{setup_label}: {setup_requirements}
{setup_line}
{breakdown_line}"""
        
        output_lines.append(note)
    
    # Join with separator lines
    separator = "\n" + "-" * 50 + "\n"
    return separator.join(output_lines) + "\n"


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main function to run the Internal Events Notes generator."""
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, "input_csv")
    output_dir = os.path.join(script_dir, "output")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Find the most recent CSV file in input directory
    csv_files = [f for f in os.listdir(input_dir) if f.endswith(".csv")]
    if not csv_files:
        print("Error: No CSV files found in input_csv directory")
        return
    
    # Use the first CSV file (or you could sort by date)
    input_file = os.path.join(input_dir, csv_files[0])
    print(f"Processing: {input_file}")
    
    # Read CSV
    with open(input_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Read {len(rows)} rows from CSV")
    
    # Normalize (remove Setup/Teardown, merge TechFlex)
    normalized = normalize_csv(rows)
    print(f"After normalization: {len(normalized)} rows")
    
    # Process events (calculate times)
    processed = process_events(normalized)
    
    # Count events to process
    to_process = [e for e in processed if e.get("Process_Event", "").strip().upper() == "YES"]
    print(f"Events to process (Process_Event=YES): {len(to_process)}")
    
    # Generate notes
    output = generate_notes(processed)
    
    # Write output
    output_file = os.path.join(output_dir, "internal_notes.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
