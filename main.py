#!/usr/bin/env python
"""
Main entry point for FTC Fraud Scrapers.

Usage:
    python main.py scrape [scraper_name] [options]
    python main.py load
    python main.py all

Examples:
    python main.py scrape press --limit 20 --pages 3
    python main.py scrape legal --specific-only
    python main.py scrape scams --limit 30
    python main.py load
    python main.py all
"""
import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

SCRAPERS = {
    "press": "src/scrapers/ftc_press_releases.py",
    "legal": "src/scrapers/ftc_legal_cases.py",
    "scams": "src/scrapers/ftc_consumer_scams.py",
}

def run_scraper(scraper_name, args):
    """Run a specific scraper."""
    if scraper_name not in SCRAPERS:
        print(f"Error: Unknown scraper '{scraper_name}'")
        print(f"Available scrapers: {', '.join(SCRAPERS.keys())}")
        sys.exit(1)

    script_path = Path(__file__).parent / SCRAPERS[scraper_name]
    cmd = [sys.executable, str(script_path)] + args
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def run_all_scrapers():
    """Run all scrapers with default settings."""
    root = Path(__file__).parent
    scrapers = [
        (root / "src/scrapers/ftc_press_releases.py", ["--limit", "20", "--pages", "3"]),
        (root / "src/scrapers/ftc_legal_cases.py", ["--limit", "20"]),
        (root / "src/scrapers/ftc_consumer_scams.py", ["--limit", "20"]),
    ]

    print("="*60)
    print("Running all FTC scrapers")
    print("="*60)

    failed = []
    for script, args in scrapers:
        cmd = [sys.executable, str(script)] + args
        print(f"\nRunning: {' '.join(cmd)}")
        if subprocess.run(cmd).returncode != 0:
            failed.append(script.name)

    if failed:
        print(f"\nFailed scrapers: {', '.join(failed)}")
        return 1
    else:
        print("\nAll scrapers completed successfully!")
        return 0

def load_to_database():
    """Load scraped data to Supabase."""
    script = Path(__file__).parent / "src/database/supabase_load.py"
    cmd = [sys.executable, str(script)]
    print(f"Running: {' '.join(cmd)}")
    return subprocess.run(cmd).returncode

def run_all():
    """Run all scrapers and load to database."""
    print("="*60)
    print("FTC Fraud Scrapers - Full Pipeline")
    print("="*60)

    # Run scrapers
    if run_all_scrapers() != 0:
        print("\nError: Some scrapers failed. Skipping database load.")
        return 1

    # Load to database
    print("\n" + "="*60)
    print("Loading data to Supabase")
    print("="*60)
    return load_to_database()

def print_help():
    """Print usage information."""
    print(__doc__)
    print("\nAvailable scrapers:")
    for name, path in SCRAPERS.items():
        print(f"  {name:10s} - {path}")

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1]

    if command == "scrape":
        if len(sys.argv) < 3:
            print("Error: scrape command requires a scraper name")
            print_help()
            sys.exit(1)
        scraper_name = sys.argv[2]
        args = sys.argv[3:]
        sys.exit(run_scraper(scraper_name, args))

    elif command == "load":
        sys.exit(load_to_database())

    elif command == "all":
        sys.exit(run_all())

    elif command in ["-h", "--help", "help"]:
        print_help()
        sys.exit(0)

    else:
        print(f"Error: Unknown command '{command}'")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
