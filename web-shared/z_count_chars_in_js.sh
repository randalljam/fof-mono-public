# ===== START OF FILE z_count_chars_in_js.sh =====
# file_path: web-shared/z_count_chars_in_js.sh

#!/usr/bin/env bash

# ==================================================================
# This script takes a single JavaScript file as input and calculates:
# - Total number of characters in the file
# - Number of comment characters (// and /* ... */)
# - Number of characters remaining after removing comments
# - Run this to give execute permission: chmod +x web-shared/z_count_chars_in_js.sh
#
# Usage:
#   web-shared/z_count_chars_in_js.sh apps/qrag/web/webflow-rag-devpage.js
#
# Notes:
# - This script attempts to remove both single-line (//) and block (/* */) comments.
# - Output is printed with commas for readability.
# ==================================================================

set -euo pipefail

# Enable thousands separator in printf
export LC_NUMERIC="en_US.UTF-8"

if [ $# -ne 1 ]; then
    echo "Usage: $0 path/to/file.js"
    exit 1
fi

input_file="$1"
if [ ! -f "$input_file" ]; then
    echo "Error: File '$input_file' not found."
    exit 1
fi

# Read the entire input file
file_content="$(cat "$input_file")"

# Count total characters
total_chars=$(echo -n "$file_content" | wc -c)

# Remove single-line comments: //...
# Remove block comments: /* ... */
# Note: This is a simplified approach and may not handle all comment edge cases.
no_comments="$(echo "$file_content" \
    | sed -E 's/\/\/.*//g' \
    | sed -E ':a;/\/*/!{N;ba};s|/\*[^*]*\*+([^/*][^*]*\*+)*/||g;ta')"

no_comment_chars=$(echo -n "$no_comments" | wc -c)
comment_chars=$(( total_chars - no_comment_chars ))

# Print results using printf's built-in thousands separator
printf "Total characters:           %'15d\n" "$total_chars"
printf "Comment characters:         %'15d\n" "$comment_chars"
printf "Characters without comments:%'15d\n" "$no_comment_chars"

# ===== END OF FILE z_count_chars_in_js.sh =====
