#!/bin/bash

# Run this script from the root folder of the project corpus-tools
# bash dependencies/get_direct_dependencies.sh
#
# NOTE (2026-05-31, Option B reorg): the old "code file copies" mirror folder was
# retired. pipreqs is now run directly against core/ (the shared library) instead of
# copying a hand-picked set of source files into a tracked folder first. This whole
# script is slated to be replaced by a pyproject.toml migration
# (see docs/2026-04-09_repos-reorg/2026-05-30_post-file-organization-followup.md).

# Store the original directory
ORIGINAL_DIR=$(pwd)
echo "Original directory: $ORIGINAL_DIR"

# Source files whose imports historically drove these requirements (provenance note,
# appended to the generated file below). Paths reflect the post-reorg layout
# (primary/ -> core/); docwork.py was not migrated to core/.
SOURCE_FILES=(
  "core/fileops.py"
  "core/transcribe.py"
  "core/llm.py"
  "core/vectordb.py"
  "core/rag.py"
  "core/conversion.py"
  "core/structured.py"
  "core/corpuses.py"
  "core/aws.py"
  "tests/test_fileops.py"
  "tests/test_transcribe.py"
  "tests/test_llm.py"
  "docs/codeindex/create_codeindex.py"
  "docs/vis/codebase_graph_vis.py"
)

# Generate requirements.txt using pipreqs
echo "Generating requirements.txt..."
if ! command -v pipreqs &> /dev/null; then
    echo "pipreqs could not be found. Please install it using 'pip install pipreqs'"
    exit 1
fi

# Run pipreqs directly on the core/ library (no more "code file copies" mirror folder)
pipreqs "$ORIGINAL_DIR/core" --force --savepath "$ORIGINAL_DIR/dependencies/requirements.txt"

# Get current date in the required format
CURRENT_DATE=$(date +"%Y-%m-%d")

# Check if requirements.txt was created in the dependencies folder
if [ -f "$ORIGINAL_DIR/dependencies/requirements.txt" ]; then
    # Rename requirements.txt with the current date and piprecs in the dependencies folder
    mv "$ORIGINAL_DIR/dependencies/requirements.txt" "$ORIGINAL_DIR/dependencies/requirements_${CURRENT_DATE}_piprecs.txt"
    echo "Created requirements_${CURRENT_DATE}_piprecs.txt in the dependencies folder"

    # Add pipreqs to the requirements file
    echo "pipreqs>=0.5.0,<0.6.0" >> "$ORIGINAL_DIR/dependencies/requirements_${CURRENT_DATE}_piprecs.txt"

    # Add the provenance file list to the requirements file
    echo -e "\n\n# Files whose imports historically drove these requirements:" >> "$ORIGINAL_DIR/dependencies/requirements_${CURRENT_DATE}_piprecs.txt"
    for file in "${SOURCE_FILES[@]}"; do
        echo "# $file" >> "$ORIGINAL_DIR/dependencies/requirements_${CURRENT_DATE}_piprecs.txt"
    done
else
    echo "Error: requirements.txt was not created in the dependencies folder. Check the pipreqs output for errors."
fi

echo "Process completed successfully."
