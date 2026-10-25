# ///////////////////////////////////////////////////////////////
# CHECK_MERGE_CONFLICT - Pre-commit hook: merge conflict marker detector
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Pre-commit hook: detect merge conflict markers in staged files."""

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library
import re
import sys

# ///////////////////////////////////////////////////////////////
# CONSTANTS
# ///////////////////////////////////////////////////////////////
# Git writes markers of *exactly* seven characters, followed by a space (the
# branch name) or by the end of the line. The trailing lookahead is what keeps
# this from firing on the `====...` rules used in docstrings and help text.
PATTERN = re.compile(r"^(<{7}|>{7}|={7}|\|{7})(?=[ \t]|$)", re.MULTILINE)

# ///////////////////////////////////////////////////////////////

rc = 0
for path in sys.argv[1:]:
    try:
        with open(path, errors="replace") as fh:
            text = fh.read()
    except OSError:
        continue
    if PATTERN.search(text):
        print(f"Merge conflict marker found: {path}")
        rc = 1

sys.exit(rc)
