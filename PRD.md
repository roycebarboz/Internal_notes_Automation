# Internal note generator

## overview

This script will generate the internal notes for the events that are booked in the coursedog system.

## input

the input will be a csv file that contains the events that are booked in the coursedog system.

## script

the python script will normalize CSV file by deleting the rows which have set the Meeting Type to setup or teardown.And bring the events with same name together which are hosted in the UCC Tech Flex Space A,B,C and merge them into a single row. Also watch out for the different evnt in between them and don't merge them like in the example below.

for example 
Event Name,Date & Time,Location,Meeting Type,Process_Event,Setup_Requirements,Account Number
Student Affairs Monthly Meeting,"Feb 5, 2026 10:00 AM - 12:00 PM",UCC Tech Flex Space A (Back),Main Meeting,,,
APO Pining,"Feb 5, 2026 08:00 AM - 12:00 PM",Bissinger,Main Meeting,,,
Student Affairs Monthly Meeting,"Feb 5, 2026 10:00 AM - 12:00 PM",UCC Tech Flex Space B (Middle),Main Meeting,,,
Student Affairs Monthly Meeting,"Feb 5, 2026 10:00 AM - 12:00 PM",UCC Tech Flex Space C (Front),Main Meeting,,,

## output

the output should be a text file with all the events listed in the order.