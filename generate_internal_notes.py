"""
Internal Events Notes Generator
================================
This script automates generating "Internal Events Notes" from a Coursedog-exported CSV file.

Author: Auto-generated
Date: January 2026

ASSUMPTIONS & NOTES:
--------------------
1. The CSV file MUST contain a "Process_Event" column with values YES/NO (case-insensitive)
2. If a "Setup_Requirements" column exists, it will be used for TechFlex notes
   - If missing, the script will use a placeholder "[Setup requirements not specified in CSV]"
   - You can add this column to your CSV to include specific setup requirements
3. Venue codes are derived from location names (see VENUE_CODES dictionary)
4. Facilities work hours: 8:00 AM - 5:00 PM
5. Lunch break (no setup): 12:00 PM - 1:00 PM
6. Default setup time: 2 hours before event start

REQUIRED CSV COLUMNS:
---------------------
- Event Name
- Date & Time (or separate Date and Time columns)
- Location
- Process_Event (YES/NO)

OPTIONAL CSV COLUMNS:
---------------------
- Setup_Requirements: copy paste the setup from Coursedog maunually in the csv file
- Account Number: copy paste the account number from Coursedog maunually in the csv file
"""

import csv
import re
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
import os

# =============================================================================
# CONFIGURATION - Modify these as needed
# =============================================================================

# Venue code mapping - add more as needed
# Format: "Location Name (or partial match)": "VENUE_CODE"
VENUE_CODES = {
    # UCC TechFlex Spaces
    "UCC Tech Flex Space A": "UCCA",
    "UCC Tech Flex Space B": "UCCB", 
    "UCC Tech Flex Space C": "UCCC",
    # if all the above are booked under the same event name and same date and time then use "UCCABC"
    # if (UCC Tech Flex Space B, UCC Tech Flex Space C) booked under the same event name and same date and time then use "UCCBC"
    # if (UCC Tech Flex Space A, UCC Tech Flex Space B) booked under the same event name and same date and time then use "UCCAB"
    # if the above are booked under different event names and same date and time then add "Close the wall between A and B, B and C"
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

# Setup label mapping - determines what prefix to use for setup requirements
# Based on venue code or location name
# Format: "VENUE_CODE" or "Location partial match": "Label"
SETUP_LABELS = {
    # TechFlex venues use "TechFlex:"
    "UCCA": "TechFlex",
    "UCCB": "TechFlex",
    "UCCC": "TechFlex",
    "UCCABC": "TechFlex",
    "UCCPI": "TechFlex",
    "UCC Tech Flex": "TechFlex",
    "UCC Pi Kitchen": "TechFlex",
    
    # Gallery uses "Gallery:"
    "UCCG": "Gallery",
    "UCC 106": "Gallery",
    "The Gallery": "Gallery",
    
    # Babbio East Patio uses "Babbio East Patio:"
    "BCEASTPATIO": "Babbio East Patio",
    "Babbio East Patio": "Babbio East Patio",
    
    # Skyline uses "Skyline:"
    "SKYLINE": "Skyline",
    "Howe 404": "Skyline",
    "Skyline": "Skyline",
    
    # Bissinger uses "Bissinger:"
    "BISSINGER": "Bissinger",
    "Howe 409": "Bissinger",
    "Howe 4th Floor": "Bissinger",
    "Bissinger": "Bissinger",
}

# Facilities working hours
WORK_START = 8  # 8:00 AM
WORK_END = 20   # 8:00 PM
LUNCH_START = 12  # 12:00 PM
LUNCH_END = 13    # 1:00 PM
DEFAULT_SETUP_HOURS = 2

# Day names for formatting
DAY_NAMES = {
    0: "Monday",
    1: "Tuesday", 
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_datetime(date_time_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse various date/time formats from the CSV.
    
    Handles formats like:
    - "Jan 27, 2026 6:30 PM - 9:00 PM"
    - "27-Jan-26"
    - "Jan 27, 2026"
    
    Returns: (start_datetime, end_datetime) or (None, None) if parsing fails
    """
    if not date_time_str or date_time_str.strip() == "":
        return None, None
    
    date_time_str = date_time_str.strip()
    
    # Pattern 1: "Jan 27, 2026 6:30 AM - 9:00 AM" or with PM
    pattern1 = r"(\w{3} \d{1,2}, \d{4}) (\d{1,2}:\d{2} [AP]M) - (\d{1,2}:\d{2} [AP]M)"
    match = re.match(pattern1, date_time_str)
    if match:
        date_str = match.group(1)
        start_time_str = match.group(2)
        end_time_str = match.group(3)
        
        try:
            start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%b %d, %Y %I:%M %p")
            end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%b %d, %Y %I:%M %p")
            return start_dt, end_dt
        except ValueError:
            pass
    
    # Pattern 1b: With date spanning midnight like "Jan 27, 2026 10:00 PM - Jan 28, 2026 1:00 AM"
    pattern1b = r"(\w{3} \d{1,2}, \d{4}) (\d{1,2}:\d{2} [AP]M) - (\w{3} \d{1,2}, \d{4}) (\d{1,2}:\d{2} [AP]M)"
    match = re.match(pattern1b, date_time_str)
    if match:
        start_date_str = match.group(1)
        start_time_str = match.group(2)
        end_date_str = match.group(3)
        end_time_str = match.group(4)
        
        try:
            start_dt = datetime.strptime(f"{start_date_str} {start_time_str}", "%b %d, %Y %I:%M %p")
            end_dt = datetime.strptime(f"{end_date_str} {end_time_str}", "%b %d, %Y %I:%M %p")
            return start_dt, end_dt
        except ValueError:
            pass
    
    # Pattern 2: "27-Jan-26" (date only, no time)
    pattern2 = r"(\d{1,2})-(\w{3})-(\d{2})"
    match = re.match(pattern2, date_time_str)
    if match:
        try:
            # Assume year is 2000s
            dt = datetime.strptime(date_time_str, "%d-%b-%y")
            return dt, dt
        except ValueError:
            pass
    
    # Pattern 3: Just date like "Jan 27, 2026"
    try:
        dt = datetime.strptime(date_time_str, "%b %d, %Y")
        return dt, dt
    except ValueError:
        pass
    
    return None, None


def get_venue_code(location: str) -> str:
    """
    Generate a venue code from the location name.
    Checks VENUE_CODES dictionary for matches, otherwise generates from location.
    """
    if not location:
        return "UNKNOWN"
    
    location_upper = location.upper()
    
    # Check for exact or partial matches in VENUE_CODES
    for key, code in VENUE_CODES.items():
        if key.upper() in location_upper or location_upper.startswith(key.upper()):
            return code
    
    # Generate a code from the location name
    # Take first letters of significant words, max 8 chars
    words = re.findall(r'[A-Za-z]+', location)
    if words:
        code = ''.join(word[0].upper() for word in words[:4])
        # Add any numbers from the location
        numbers = re.findall(r'\d+', location)
        if numbers:
            code += numbers[0]
        return code[:8] if len(code) > 8 else code
    
    return "VENUE"


def get_setup_label(location: str, venue_code: str) -> str:
    """
    Get the appropriate setup label prefix based on the venue/location.
    
    Different venues have different labels:
    - TechFlex spaces → "TechFlex"
    - UCC 106 (Gallery) → "Gallery"
    - Babbio East Patio → "Babbio East Patio"
    - Howe 404 (Skyline) → "Skyline"
    - Howe 409 (Bissinger) → "Bissinger"
    - Default → "Setup" for unknown venues
    
    Returns: The label string (without colon)
    """
    # First check by venue code
    if venue_code in SETUP_LABELS:
        return SETUP_LABELS[venue_code]
    
    # Then check by location name (partial match)
    if location:
        location_lower = location.lower()
        for key, label in SETUP_LABELS.items():
            if key.lower() in location_lower:
                return label
    
    # Default label for unknown venues
    return "Setup"


def get_am_pm(dt: datetime) -> str:
    """Return AM or PM based on the datetime hour."""
    return "AM" if dt.hour < 12 else "PM"


def generate_reservation_number(event_date: datetime, venue_code: str, start_time: datetime) -> str:
    """
    Generate reservation number in format: MMDD + VENUE_CODE + AM/PM
    
    Example: 0127UCCABCPM
    """
    mmdd = event_date.strftime("%m%d")
    am_pm = get_am_pm(start_time)
    return f"{mmdd}{venue_code}{am_pm}"


def calculate_setup_time(event_start: datetime, same_venue_events: List[dict]) -> datetime:
    """
    Calculate setup time following these rules:
    1. Default: 2 hours before event start
    2. Facilities work hours: 8:00 AM - 8:00 PM
    3. No setup during 12:00 PM - 1:00 PM (lunch)
    4. If another event exists before in same venue, setup after it ends
    
    Returns: setup datetime
    """
    # Start with 2 hours before event
    setup_time = event_start - timedelta(hours=DEFAULT_SETUP_HOURS)
    
    # Check if setup falls during lunch break (12 PM - 1 PM)
    if setup_time.hour == 12:
        # Move to 11 AM
        setup_time = setup_time.replace(hour=11, minute=0)
    elif setup_time.hour < 12 and (setup_time + timedelta(hours=DEFAULT_SETUP_HOURS)).hour > 12:
        # Setup would span lunch, start earlier
        setup_time = setup_time.replace(hour=11, minute=0)
    
    # Ensure setup is within work hours (8 AM - 8 PM)
    if setup_time.hour < WORK_START:
        setup_time = setup_time.replace(hour=WORK_START, minute=0)
    elif setup_time.hour >= WORK_END:
        # Setup needs to be day before or early same day
        setup_time = setup_time.replace(hour=WORK_START, minute=0)
    
    # Check for conflicts with other events in the same venue
    for other_event in same_venue_events:
        other_end = other_event.get('end_time')
        other_start = other_event.get('start_time')
        
        if other_end and other_start:
            # If the other event ends before our event starts on the same day
            if (other_end.date() == event_start.date() and 
                other_end < event_start and 
                other_end > setup_time):
                # Adjust setup to start after the previous event ends
                setup_time = other_end
                # Add 15-minute buffer
                setup_time = setup_time + timedelta(minutes=15)
    
    return setup_time


def calculate_breakdown_time(event_end: datetime, same_venue_events: List[dict]) -> Tuple[datetime, str]:
    """
    Calculate breakdown time following these rules:
    1. If event ends after 8 PM → breakdown next day at 10:00 AM
    2. If another event exists after in same venue → breakdown before it starts
    3. Otherwise → breakdown immediately after event end
    
    Returns: (breakdown_datetime, note_if_any)
    """
    note = ""
    
    # Rule 1: Event ends after 8 PM
    if event_end.hour >= WORK_END:
        next_day = event_end + timedelta(days=1)
        breakdown_time = next_day.replace(hour=10, minute=0, second=0, microsecond=0)
        return breakdown_time, note
    
    # Check for subsequent events in the same venue
    for other_event in same_venue_events:
        other_start = other_event.get('start_time')
        
        if other_start:
            # If there's an event starting after this one on the same day
            if (other_start.date() == event_end.date() and 
                other_start > event_end):
                # Breakdown must occur before next event
                breakdown_time = event_end + timedelta(minutes=15)
                if breakdown_time >= other_start:
                    breakdown_time = event_end  # Immediate breakdown
                    note = f"(Before next event at {other_start.strftime('%I:%M %p')})"
                return breakdown_time, note
    
    # Rule 3: Default - breakdown immediately after
    breakdown_time = event_end
    return breakdown_time, note


def format_datetime_for_notes(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime for Internal Events Notes.
    Example: "Tuesday, January 27, at 4:30 PM"
    """
    day_name = DAY_NAMES[dt.weekday()]
    
    if include_time:
        time_str = dt.strftime("%I:%M %p").lstrip("0").replace(" 0", " ")
        return f"{day_name}, {dt.strftime('%B')} {dt.day}, at {time_str}"
    else:
        return f"{day_name}, {dt.strftime('%B')} {dt.day}"


def detect_techflex_abc_booking(events: List[dict]) -> Dict[str, List[dict]]:
    """
    Detect when UCC Tech Flex Space A, B, and C are ALL booked
    under the SAME event name on the SAME date.
    
    Returns: Dictionary mapping combined_key to list of events that should use UCCABC code
    """
    techflex_events = defaultdict(list)
    combined_bookings = {}
    
    # Filter for TechFlex events only
    for event in events:
        location = event.get('location', '')
        if 'UCC Tech Flex Space' in location:
            # Create a key: event_name + date
            event_name = event.get('event_name', '').strip().lower()
            event_date = event.get('start_time')
            if event_date:
                key = f"{event_name}_{event_date.strftime('%Y-%m-%d')}"
                techflex_events[key].append(event)
    
    # Check which keys have all three spaces (A, B, C)
    for key, event_list in techflex_events.items():
        spaces = set()
        for evt in event_list:
            loc = evt.get('location', '')
            if 'Space A' in loc:
                spaces.add('A')
            elif 'Space B' in loc:
                spaces.add('B')
            elif 'Space C' in loc:
                spaces.add('C')
        
        # If all three spaces are booked
        if spaces == {'A', 'B', 'C'}:
            combined_bookings[key] = event_list
    
    return combined_bookings


def generate_internal_notes(event: dict, venue_code: str, same_venue_events: List[dict]) -> str:
    """
    Generate the Internal Events Notes block for a single event.
    """
    start_time = event.get('start_time')
    end_time = event.get('end_time')
    location = event.get('location', '')
    setup_requirements = event.get('setup_requirements', '[Setup requirements not specified in CSV]')
    
    if not start_time or not end_time:
        return f"# ERROR: Could not parse date/time for event: {event.get('event_name', 'Unknown')}\n"
    
    # Generate reservation number
    reservation_number = generate_reservation_number(start_time, venue_code, start_time)
    
    # Calculate setup time
    setup_time = calculate_setup_time(start_time, same_venue_events)
    
    # Calculate breakdown time
    breakdown_time, breakdown_note = calculate_breakdown_time(end_time, same_venue_events)
    
    # Get the appropriate setup label based on venue
    setup_label = get_setup_label(location, venue_code)
    
    # Format the notes
    notes = []
    notes.append("Account Number: __________")
    notes.append(f"Reservation Number: {reservation_number}")
    notes.append(f"Please set up on {format_datetime_for_notes(setup_time)}")
    notes.append(f"{setup_label}: {setup_requirements}")
    
    breakdown_str = f"Please break down on {format_datetime_for_notes(breakdown_time)}"
    if breakdown_note:
        breakdown_str += f" {breakdown_note}"
    notes.append(breakdown_str)
    
    return "\n".join(notes)


def process_csv(input_file: str, output_format: str = "text") -> Tuple[List[str], List[dict]]:
    """
    Process the CSV file and generate Internal Events Notes.
    
    Args:
        input_file: Path to the input CSV file
        output_format: "text" for text file output, "csv" for CSV column output
    
    Returns:
        Tuple of (list of notes strings, list of processed event dicts)
    """
    events = []
    all_events = []  # ALL events from CSV for detecting combined bookings
    notes_output = []
    
    # Read and parse CSV - FIRST PASS: Load ALL events to detect combined bookings
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        for row in reader:
            # Extract event data from ALL rows
            event_name = None
            date_time = None
            location = None
            setup_requirements = None
            process_event = None
            
            for key, value in row.items():
                if not key:
                    continue
                key_lower = key.strip().lower()
                
                if 'event' in key_lower and 'name' in key_lower:
                    event_name = value
                elif key_lower in ['event name', 'eventname']:
                    event_name = value
                elif 'date' in key_lower and 'time' in key_lower:
                    date_time = value
                elif key_lower == 'date & time':
                    date_time = value
                elif key_lower == 'location':
                    location = value
                elif 'setup' in key_lower or 'resource' in key_lower:
                    setup_requirements = value
                elif 'process' in key_lower:
                    process_event = value
            
            # Fallback: use first column as event name if not found
            if not event_name and fieldnames:
                event_name = row.get(fieldnames[0], 'Unknown Event')
            
            # Parse date/time
            start_time, end_time = parse_datetime(date_time)
            
            if start_time:
                event_data = {
                    'event_name': event_name,
                    'location': location,
                    'start_time': start_time,
                    'end_time': end_time,
                    'setup_requirements': setup_requirements or '[Setup requirements not specified in CSV]',
                    'process_event': process_event,
                    'raw_row': row
                }
                all_events.append(event_data)
                
                # Also add to events list if marked for processing
                if process_event and process_event.strip().upper() == 'YES':
                    events.append(event_data)
    
    if not events:
        return ["No events found with Process_Event = YES"], events
    
    # Detect TechFlex ABC combined bookings from ALL events (not just YES ones)
    # This ensures we detect combined bookings even if only one space is marked YES
    combined_bookings = detect_techflex_abc_booking(all_events)
    
    # Create a mapping of event name + date to combined booking info
    combined_booking_keys = {}
    for key, event_list in combined_bookings.items():
        for evt in event_list:
            # Map each individual event to its combined key
            evt_key = f"{evt.get('event_name', '').strip().lower()}_{evt['start_time'].strftime('%Y-%m-%d')}"
            combined_booking_keys[evt_key] = key
    
    # Group ALL events by venue and date for conflict detection
    venue_date_events = defaultdict(list)
    for event in all_events:
        venue_key = f"{event['location']}_{event['start_time'].strftime('%Y-%m-%d')}"
        venue_date_events[venue_key].append(event)
    
    # Track which combined bookings have been processed
    processed_combined = set()
    
    # Generate notes for each event marked for processing
    for event in events:
        # Check if this event is part of a combined TechFlex ABC booking
        event_name = event.get('event_name', '').strip().lower()
        event_date = event.get('start_time')
        evt_key = f"{event_name}_{event_date.strftime('%Y-%m-%d')}" if event_date else ""
        
        is_combined = evt_key in combined_booking_keys
        combined_key = combined_booking_keys.get(evt_key) if is_combined else None
        
        if is_combined and combined_key:
            # Skip if we've already processed this combined booking
            if combined_key in processed_combined:
                continue
            
            processed_combined.add(combined_key)
            venue_code = "UCCABC"
            
            # Update location to show combined booking
            event['location'] = "UCC Tech Flex Space A, B, C (Combined)"
            
            # Get all setup requirements from the combined events
            setup_reqs = []
            for evt in combined_bookings[combined_key]:
                req = evt.get('setup_requirements', '')
                if req and req != '[Setup requirements not specified in CSV]':
                    setup_reqs.append(req)
            
            if setup_reqs:
                event['setup_requirements'] = '; '.join(set(setup_reqs))
        else:
            venue_code = get_venue_code(event.get('location', ''))
        
        # Get other events in the same venue on the same date for conflict detection
        # For combined bookings, check all three TechFlex spaces
        if is_combined:
            same_venue_events = []
            for space in ['UCC Tech Flex Space A', 'UCC Tech Flex Space B', 'UCC Tech Flex Space C']:
                for evt in all_events:
                    if space in evt.get('location', '') and evt['start_time'].strftime('%Y-%m-%d') == event_date.strftime('%Y-%m-%d'):
                        if id(evt) != id(event) and evt.get('event_name', '').strip().lower() != event_name:
                            same_venue_events.append(evt)
        else:
            venue_key = f"{event['location']}_{event['start_time'].strftime('%Y-%m-%d')}"
            same_venue_events = [e for e in venue_date_events[venue_key] if id(e) != id(event)]
        
        # Generate notes
        notes = generate_internal_notes(event, venue_code, same_venue_events)
        
        # Add header with event info
        header = f"\n{'='*60}\nEvent: {event.get('event_name', 'Unknown')}\nLocation: {event.get('location', 'Unknown')}\nDate: {event['start_time'].strftime('%B %d, %Y')}\n{'='*60}\n"
        
        notes_output.append(header + notes)
    
    return notes_output, events


def main():
    """Main function to run the script."""
    import sys
    import argparse
    import glob
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define input and output folder paths
    input_folder = os.path.join(script_dir, "input_csv")
    output_folder = os.path.join(script_dir, "output")
    
    # Create folders if they don't exist
    os.makedirs(input_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    
    parser = argparse.ArgumentParser(
        description='Generate Internal Events Notes from Coursedog CSV export',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Folder Structure:
  - Place CSV files in: {input_folder}
  - Output will be saved to: {output_folder}

Examples:
  python generate_internal_notes.py                    # Process all CSVs in input_csv folder
  python generate_internal_notes.py events.csv        # Process specific file from input_csv folder
  python generate_internal_notes.py --output-csv      # Output as CSV with notes column
        """
    )
    
    parser.add_argument('input_csv', nargs='?', default=None,
                        help='Input CSV filename (looked up in input_csv folder). If not provided, processes all CSVs in the folder.')
    parser.add_argument('-o', '--output', default=None,
                        help='Output filename (saved to output folder)')
    parser.add_argument('--output-csv', action='store_true',
                        help='Output as CSV with Internal_Events_Notes column')
    
    args = parser.parse_args()
    
    # Find CSV files to process
    if args.input_csv:
        # Specific file provided
        input_file = os.path.join(input_folder, args.input_csv)
        if not os.path.exists(input_file):
            # Try as absolute/relative path
            if os.path.exists(args.input_csv):
                input_file = args.input_csv
            else:
                print(f"ERROR: Input file not found: {args.input_csv}")
                print(f"  Looked in: {input_folder}")
                print(f"  Also tried: {args.input_csv}")
                sys.exit(1)
        csv_files = [input_file]
    else:
        # Find all CSV files in input folder
        csv_files = glob.glob(os.path.join(input_folder, "*.csv"))
        if not csv_files:
            print(f"No CSV files found in: {input_folder}")
            print(f"\nPlease place your Coursedog CSV export in the input_csv folder.")
            sys.exit(0)
    
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Found {len(csv_files)} CSV file(s) to process")
    print("-" * 60)
    
    # Process each CSV file
    all_notes = []
    for input_file in csv_files:
        print(f"\nProcessing: {os.path.basename(input_file)}")
        print("-" * 40)
        
        # Process the CSV
        notes_output, processed_events = process_csv(input_file)
        
        if not processed_events:
            print("  No events found with Process_Event = YES")
            print("  Make sure your CSV has a 'Process_Event' column with 'YES' values")
            continue
        
        print(f"  Found {len(processed_events)} event(s) to process")
        
        # Determine output file name (in output folder)
        input_basename = os.path.basename(input_file)
        if args.output:
            output_basename = args.output
        elif args.output_csv:
            output_basename = input_basename.replace('.csv', '_with_notes.csv')
        else:
            output_basename = input_basename.replace('.csv', '_internal_notes.txt')
        
        output_file = os.path.join(output_folder, output_basename)
        
        # Write output
        if args.output_csv:
            # Write CSV with new column
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames) + ['Internal_Events_Notes']
                rows = list(reader)
            
            # Create a mapping of processed events to their notes
            event_notes_map = {}
            for event, notes in zip(processed_events, notes_output):
                key = f"{event.get('event_name', '')}_{event.get('location', '')}"
                # Clean up the notes for CSV (remove header)
                clean_notes = notes.split('='*60)[-1].strip()
                event_notes_map[key] = clean_notes
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in rows:
                    key = f"{row.get('Event Name', '')}_{row.get('Location', '')}"
                    row['Internal_Events_Notes'] = event_notes_map.get(key, '')
                    writer.writerow(row)
            
            print(f"  Output: {output_file}")
        else:
            # Write text file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("INTERNAL EVENTS NOTES\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Source: {os.path.basename(input_file)}\n")
                f.write("=" * 60 + "\n")
                
                for notes in notes_output:
                    f.write(notes)
                    f.write("\n")
            
            print(f"  Output: {output_file}")
        
        # Collect notes for console output
        all_notes.extend(notes_output)
    
    # Print summary to console
    if all_notes:
        print("\n" + "=" * 60)
        print("GENERATED INTERNAL EVENTS NOTES:")
        print("=" * 60)
        
        for notes in all_notes:
            print(notes)
            print()
    
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"Output files saved to: {output_folder}")
    print("=" * 60)


if __name__ == "__main__":
    main()
