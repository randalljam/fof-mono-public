#!/bin/bash
# chmod +x cloc_count.sh

# Input file containing paths
INPUT_FILE="cloc_paths.txt"

# Output file for the report (changed to .md)
OUTPUT_FILE="cloc_report.md"

# Current date for the report header
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Create header for the report
echo "Code Metrics Report - Generated on $DATE" > "$OUTPUT_FILE"
echo "========================================" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Run cloc and process the output
cloc --list-file="$INPUT_FILE" \
     --exclude-dir=node_modules,venv,__pycache__,.git \
     --exclude-ext=md,json,csv \
     --by-file \
     --md \
     | awk '
        # Store the header lines
        NR==1 {header1=$0; next}
        NR==2 {header2=$0; next}
        NR==3 {header3=$0; next}
        NR==4 {header4=$0; next}
        # Store the SUM line
        /^SUM/ {sum=$0; next}
        # Skip specific lines
        !/^-+\|/ {lines[++count]=$0}  # Skip lines that are just dashes
        END {
            print header1;
            print header2;
            print header3;
            print header4;
            print ":-------|-------:|-------:|-------:";
            print sum;
            for (i in lines) print lines[i]
        }' >> "$OUTPUT_FILE"

# Post-process to remove unwanted lines
sed -i '' '/^--- | ---$/d' "$OUTPUT_FILE"

# Clean up the end of file - remove lines with only special characters and add a newline
perl -i -0pe 's/[\n\r][-:|]+[\n\r]*$/\n/' "$OUTPUT_FILE"

# Sort lines after SUM
sed -i '' -e '/^SUM/,$ {
    /^SUM/!{
        /^[[:space:]]*$/!{
            w /tmp/cloc_to_sort.tmp
        }
    }
    /^SUM/!d
}' "$OUTPUT_FILE"

sort /tmp/cloc_to_sort.tmp >> "$OUTPUT_FILE"
rm /tmp/cloc_to_sort.tmp

# Add commas to numbers
awk '
BEGIN {
    FS=OFS="|"
}
function addcommas(str) {
    # Trim whitespace
    gsub(/^[ \t]+|[ \t]+$/, "", str)
    if (str ~ /^[0-9]+$/) {
        # Insert comma before last 3 digits if number is 4+ digits
        if (length(str) > 3) {
            return substr(str, 1, length(str)-3) "," substr(str, length(str)-2)
        }
    }
    return str
}
{
    if (NF > 1) {
        for (i=2; i<=NF; i++) {
            $i = addcommas($i)
        }
    }
    print
}' "$OUTPUT_FILE" > "${OUTPUT_FILE}.tmp" && mv "${OUTPUT_FILE}.tmp" "$OUTPUT_FILE"

# Print just the File and SUM lines to terminal
echo -e "\nSummary:"
awk -F'|' '/^File|^SUM:/ {gsub(/\|/, "\t"); print}' "$OUTPUT_FILE"

echo -e "\nReport generated in $OUTPUT_FILE"