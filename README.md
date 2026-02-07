# Internal Events Notes Generator

## Overview

This Python script automates the generation of Internal Events Notes from Coursedog CSV exports.

## Required CSV Columns

The input CSV must contain these columns:

| Column | Description |
|--------|-------------|
| Event Name | Name of the event |
| Date & Time | Event date and time range (e.g., "Feb 5, 2026 10:00 AM - 12:00 PM") |
| Location | Venue/room name |
| Meeting Type | Must be "Main Meeting" to be processed (Setup/Teardown rows are filtered out) |
| Process_Event | Set to "YES" for events that need notes generated |
| Setup_Requirements | Setup instructions (e.g., "3 6ft tables") |
| Account Number | Billing account (e.g., "CC1000190") |

## Manual Preprocessing Steps

Before running the script:

1. Export the events report CSV from Coursedog
2. Save it to the `input_csv/` folder
3. Add/update these columns for relevant events:
   - `Process_Event`: Set to "YES" for events needing notes
   - `Setup_Requirements`: Enter setup details
   - `Account Number`: Enter the billing account

## How to Run

```bash
cd c:\Users\Royce Barboz\OneDrive\Desktop\Internal_notes_Automation
python generate_internal_notes.py
```

Output will be written to `output/internal_notes.txt`.

## Rule Assumptions

### Setup Time Rules

- Default: 2 hours before event start
- Early events (before 10 AM): Setup at 6:00 AM (overtime allowed)
- Evening events (5 PM or later) with no prior event: Setup at 11:00 AM
- Weekend events with no back-to-back: Setup on Friday at 11:00 AM
- No setup during lunch break (12:00 PM - 1:00 PM)
- Back-to-back events (less than 30 min gap): Warning symbol added

### Breakdown Time Rules

- Default: After event end time
- Events ending after 3:00 PM: Breakdown next day in the AM
- Exception: If next day is weekend and no setups, breakdown can be 4:00 PM
- No breakdown during lunch break (12:00 PM - 1:00 PM)

### TechFlex Merging

When UCC Tech Flex Space A, B, and C are all booked for the same event name, date, and time, they are merged into a single UCCABC entry.

## Output Format

```
Account Number: CC1000190
Reservation Number: 0205BC310PM
Babbio 310: 3 6ft tables
Please set up on Thursday, February 5, at 11:00 AM
Please break down on the next day (Friday, February 6) in the AM
```
