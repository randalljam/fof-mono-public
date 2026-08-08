#!/bin/bash

# Command to run in terminal from directory for the chalice project , i.e. 'qrag-deutsch-v3'
# ../chalicelib_mirror_deploy.sh

# Enable debug mode
# set -x

# Define the target chalice lib folder within the current directory
TARGET_FOLDER="./chalicelib"

# Ensure the target folder exists
if [ ! -d "$TARGET_FOLDER" ]; then
  echo "Chalice lib folder '$TARGET_FOLDER' does not exist."
  exit 1
fi

# List of paths to the files that have the code you want copied into the chalicelib files
SOURCE_FILES=(
  "../../../primary/aws.py"
  "../../../primary/fileops.py"
  "../../../primary/llm.py"
  "../../../primary/rag.py"
  "../../../primary/vectordb.py"
  "../../../primary/rag_prompts_routes.py"
  # Add more file paths as needed
)

# Delimiter to indicate where to start syncing code
DELIMITER="# ---START OF SYNCED CODE---"

# Iterate over the specified files
for file in "${SOURCE_FILES[@]}"; do
  # Get the base name of the file (without directory)
  base_name=$(basename "$file")

  # Find the corresponding file in the chalice lib folder
  target_file="$TARGET_FOLDER/$base_name"

  if [ ! -f "$file" ]; then
    echo "Source file '$file' does not exist. Skipping."
    continue
  fi

  if [ ! -f "$target_file" ]; then
    echo "Target file '$target_file' does not exist. Skipping."
    continue
  fi

  echo "Updating '$target_file' with code from '$file'"

  # Extract content from the target file above the delimiter
  awk -v delim="$DELIMITER" '
    $0 ~ delim {exit}
    {print}
  ' "$target_file" > temp_target_header.py

  # Extract content from the source file including and below the delimiter
  awk -v delim="$DELIMITER" '
    $0 ~ delim {p=1}
    p
  ' "$file" > temp_source_code.py

  # Combine the target header and source code
  cat temp_target_header.py temp_source_code.py > "$target_file"

  # # DEBUG: Print the last 5 lines of temp_target_header.py
  # echo "Last 5 lines of temp_target_header.py:"
  # tail -n 5 temp_target_header.py

  # # DEBUG: Print the first 10 lines of temp_source_code.py
  # echo "First 10 lines of temp_source_code.py:"
  # head -n 10 temp_source_code.py

  # # DEBUG: Print the first 10 lines after the delimiter in the updated file
  # echo "First 10 lines after delimiter in $target_file after update:"
  # sed -n "/$DELIMITER/,+10p" "$target_file"

  # Clean up temporary files
  rm temp_target_header.py temp_source_code.py
done

# Disable debug mode
set +x

# Run chalice deploy at the end
# echo "Running chalice deploy..."
# chalice deploy
