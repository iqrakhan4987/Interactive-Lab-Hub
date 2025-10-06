#!/bin/bash
# ask_number.sh - Ask for numeric input verbally and record the answer

# Ask the question
QUESTION="Please enter your zipcode now."
espeak "$QUESTION"

# Prompt the user to type the number
read -p "Enter your number: " NUMBER

# Confirm what the user entered
espeak "You entered $NUMBER. Thank you!"
echo "Recorded number: $NUMBER"
