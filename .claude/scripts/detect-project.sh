#!/bin/bash
# Project Detection Script
# Detects current project name for use by sentinel agents

# Try git repository name first (most reliable)
PROJECT_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null)

# Fallback to directory name if not a git repo
if [ -z "$PROJECT_NAME" ] || [ "$PROJECT_NAME" = "." ]; then
    PROJECT_NAME=$(basename "$PWD")
fi

# Output project name
echo "$PROJECT_NAME"
