#!/usr/bin/env python
"""
Main runner script for FTC scrapers.
Usage: python scripts/run_scraper.py [scraper_name] [options]
"""
import sys
import subprocess
from pathlib import Path

SCRAPERS = {
    "press": "src/scrapers/ftc_press_releases.py",
    "legal": "src/scrapers/ftc_legal_cases.py",
    "scams": "src/scrapers/ftc_consumer_scams.py",
}

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_scraper.py [scraper] [options]")
        print("\nAvailable scrapers:")
        for name, path in SCRAPERS.items():
            print(f"  {name:10s} - {path}")
        print("\nExamples:")
        print("  python scripts/run_scraper.py press --limit 20 --pages 3")
        print("  python scripts/run_scraper.py legal --specific-only")
        print("  python scripts/run_scraper.py scams --limit 30")
        sys.exit(1)

    scraper = sys.argv[1]
    if scraper not in SCRAPERS:
        print(f"Error: Unknown scraper '{scraper}'")
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}")
        sys.exit(1)

    script_path = Path(__file__).parent.parent.parent / SCRAPERS[scraper]
    args = sys.argv[2:]

    cmd = ["python", str(script_path)] + args
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
