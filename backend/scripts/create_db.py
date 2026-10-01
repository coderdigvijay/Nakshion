#!/usr/bin/env python3
"""Create the local PostgreSQL database for development."""
import subprocess
import sys


def main():
    db_name = "cosmic_intelligence"
    try:
        subprocess.run(
            ["createdb", db_name],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"Database '{db_name}' created successfully.")
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            print(f"Database '{db_name}' already exists.")
        else:
            print(f"Error creating database: {e.stderr}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
