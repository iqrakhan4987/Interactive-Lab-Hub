#!/bin/bash
# greet.sh - Greets the user by name using TTS

# Set your name here
NAME="Iqra"

# Greeting message
MESSAGE="Hello, $NAME! Welcome back to your Raspberry Pi."

# Use espeak to speak the message
espeak "$MESSAGE"
