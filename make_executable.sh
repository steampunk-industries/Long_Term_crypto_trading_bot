#!/bin/bash
# Make scripts executable

# Make the setup script executable
chmod +x scripts/setup.py
echo "Made scripts/setup.py executable"

# Make the run script executable
chmod +x run_bot.py
echo "Made run_bot.py executable"

# Make the main script executable
chmod +x src/main.py
echo "Made src/main.py executable"

echo "All scripts are now executable"
echo "You can now run:"
echo "  ./scripts/setup.py     # To set up the project"
echo "  ./run_bot.py           # To run the bot"
