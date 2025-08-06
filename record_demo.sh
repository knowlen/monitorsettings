#!/bin/bash

# Asciinema recording script for monitorsettings demo

echo "=== Monitor Settings Demo Recording Script ==="
echo ""
echo "This will record a demo of the monitorsettings tool."
echo "The recording will showcase:"
echo "  1. Starting the application"
echo "  2. Adjusting brightness with arrow keys"
echo "  3. Changing step size"
echo "  4. Selecting individual displays"
echo "  5. Exiting the application"
echo ""
echo "Tips for recording:"
echo "  - Keep actions deliberate and well-paced"
echo "  - Pause briefly between actions so viewers can follow"
echo "  - The recording will capture your exact terminal size"
echo ""
echo "Press Enter to start recording (Ctrl+C to cancel)..."
read

# Start recording with settings optimized for embedding
asciinema rec \
  --title "Monitor Settings - Terminal Brightness Control" \
  --idle-time-limit 2 \
  demo.cast

echo ""
echo "=== Recording Complete ==="
echo ""
echo "To preview your recording locally:"
echo "  asciinema play demo.cast"
echo ""
echo "To upload and get a shareable link:"
echo "  asciinema upload demo.cast"
echo ""
echo "The upload will give you:"
echo "  1. A URL to view the recording"
echo "  2. An embed code for the README"
echo ""
echo "To re-record, just run this script again."