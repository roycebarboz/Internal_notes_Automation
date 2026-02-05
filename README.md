# Internal Events Notes Generator

Automates the generation of "Internal Events Notes" from Coursedog-exported CSV files.

## Overview

This script reads a Coursedog event export CSV, filters events marked for processing, and generates formatted Internal Events Notes following Stevens University facilities guidelines.

## Folder Structure

```
Events_Automation/
├── input_csv/           ← Place your CSV files here
│   └── events.csv
├── output/              ← Generated notes appear here
│   └── events_internal_notes.txt
├── generate_internal_notes.py
└── README.md
```

## Features

- **Auto-detect CSVs**: Automatically processes all CSV files in the `input_csv` folder
- **Process_Event Filtering**: Only generates notes for events marked `YES` in the `Process_Event` column
- **UCC TechFlex ABC Detection**: Automatically detects when all three TechFlex spaces (A, B, C) are booked for the same event and uses combined venue code `UCCABC`
- **Venue-Specific Labels**: Uses correct labels (TechFlex, Gallery, Skyline, Bissinger, etc.) based on venue
- **Smart Setup Time Calculation**:
  - Default: 2 hours before event start
  - Respects facilities work hours (8 AM - 5 PM)
  - Avoids lunch break (12 PM - 1 PM)
  - Adjusts for conflicting events in the same venue
- **Smart Breakdown Time Calculation**:
  - Events ending after 8 PM → breakdown next day at 10 AM
  - Adjusts for subsequent events in the same venue

## Quick Start

### 1. Prepare Your CSV

Add a `Process_Event` column to your Coursedog export with `YES` or `NO` values:

| Event Name | Date & Time | Location | Meeting Type | Setup_Requirements | Process_Event |
|------------|-------------|----------|--------------|-------------------|---------------|
| Champion Quest | Jan 27, 2026 6:30 PM - 10:00 PM | UCC Tech Flex Space A | Main Meeting | 8 round tables | YES |
| Other Event | Jan 27, 2026 2:00 PM - 4:00 PM | Babbio 202 | Main Meeting | | NO |

### 2. Place CSV in input_csv folder

Copy your CSV file(s) to the `input_csv` folder.

### 3. Run the Script

```bash
# Process ALL CSV files in input_csv folder
python generate_internal_notes.py

# Process a specific file from input_csv folder
python generate_internal_notes.py my_events.csv

# Output as CSV with notes column
python generate_internal_notes.py --output-csv
```

### 4. Get Your Notes

Output files are saved to the `output` folder with formatted notes like:

```
Account Number: __________
Reservation Number: 0127UCCABCPM
Please set up on Tuesday, January 27, at 4:30 PM
TechFlex: 8-60in round tables with 10 chairs each
Please break down on Wednesday, January 28, at 10:00 AM
```

## CSV Column Requirements

### Required Columns
| Column | Description |
|--------|-------------|
| `Event Name` | Name of the event |
| `Date & Time` | Date and time range (e.g., "Jan 27, 2026 6:30 PM - 10:00 PM") |
| `Location` | Venue name |
| `Process_Event` | `YES` to generate notes, `NO` to skip |

### Optional Columns
| Column | Description |
|--------|-------------|
| `Setup_Requirements` or `Resources` | Equipment/furniture requirements for TechFlex notes |
| `Meeting Type` | Type of meeting (informational only) |

## Date/Time Formats Supported

The script automatically parses these formats:
- `Jan 27, 2026 6:30 PM - 10:00 PM` (full datetime range)
- `Jan 27, 2026 10:00 PM - Jan 28, 2026 1:00 AM` (overnight events)
- `27-Jan-26` (date only)
- `Jan 27, 2026` (date only)

## Reservation Number Format

Generated as: `MMDD` + `VENUE_CODE` + `AM/PM`

Examples:
- `0127UCCABCPM` - Jan 27, UCC Tech Flex A+B+C, PM event
- `0128UCC106AM` - Jan 28, UCC 106, AM event
- `0205BAB100PM` - Feb 5, Babbio 100, PM event

## UCC TechFlex ABC Combined Booking

The script automatically detects when all three TechFlex spaces are booked:
- Same event name
- Same date
- Spaces A, B, and C all present in CSV

When detected:
- Uses venue code `UCCABC`
- Generates **one** combined note (not three separate ones)
- Merges setup requirements from all three spaces

**Important**: You only need to mark ONE of the three TechFlex rows as `YES` in `Process_Event` - the script will detect the combined booking automatically.

## Venue Codes

Common venue codes (add more in the script's `VENUE_CODES` dictionary):

| Location | Code |
|----------|------|
| UCC Tech Flex Space A | UCCA |
| UCC Tech Flex Space B | UCCB |
| UCC Tech Flex Space C | UCCC |
| UCC Tech Flex A+B+C | UCCABC |
| UCC 106 (The Gallery) | UCC106 |
| Babbio 100 (Atrium) | BAB100 |
| Walker Gym | WALKERGYM |
| Howe 409 (Bissinger) | HOWE409 |

## Setup Time Rules

1. **Default**: 2 hours before event start
2. **Work Hours**: 8:00 AM - 8:00 PM only
3. **Lunch Break**: No setup during 12:00 PM - 1:00 PM
4. **Conflicts**: If another event ends just before yours in the same venue, setup starts after it ends

## Breakdown Time Rules

1. **After 8 PM**: Breakdown next day at 10:00 AM
2. **Conflicts**: If another event starts after yours in the same venue, breakdown occurs before it
3. **Default**: Immediately after event ends

## Customization

### Adding Venue Codes

Edit the `VENUE_CODES` dictionary in `generate_internal_notes.py`:

```python
VENUE_CODES = {
    "UCC Tech Flex Space A": "UCCA",
    "My Custom Venue": "MYCODE",
    # Add more...
}
```

### Changing Work Hours

Edit these constants in the script:

```python
WORK_START = 8   # 8:00 AM
WORK_END = 20    # 8:00 PM
LUNCH_START = 12 # 12:00 PM
LUNCH_END = 13   # 1:00 PM
DEFAULT_SETUP_HOURS = 2
```

## Troubleshooting

### "No events found with Process_Event = YES"

- Check your CSV has a `Process_Event` column (case-insensitive)
- Make sure at least one row has `YES` (not "yes " with trailing space)
- Verify CSV encoding is UTF-8

### Date/Time Not Parsing

- Use supported formats (see above)
- Check for typos in month abbreviations
- Ensure time includes AM/PM

### Wrong Venue Code

- Add the venue to `VENUE_CODES` dictionary
- Use exact match or partial match (script checks both)

## Files & Folders

| Path | Description |
|------|-------------|
| `input_csv/` | **Place your CSV files here** - script auto-detects all CSVs |
| `output/` | **Output folder** - generated notes saved here |
| `generate_internal_notes.py` | Main script |
| `requirements.txt` | Dependencies (standard library only) |
| `sample_events.csv` | Sample CSV with Setup_Requirements |

## Requirements

- Python 3.7 or higher
- No external dependencies (uses only standard library)

## Support

For issues or feature requests, contact your system administrator or modify the script directly - it's well-commented and easy to customize.
