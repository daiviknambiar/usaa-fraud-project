#!/usr/bin/env python
"""
Run all FTC scrapers in sequence.
Usage: python scripts/run_all_scrapers.py
"""
import subprocess
from pathlib import Path

def run_scraper(script_path, *args):
    """Run a scraper script with the given arguments."""
    cmd = ["python", str(script_path)] + list(args)
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print('='*60)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Warning: {script_path} exited with code {result.returncode}")
    return result.returncode

def main():
    root = Path(__file__).parent.parent.parent

    # Run all scrapers with default settings
    scrapers = [
        (root / "src/scrapers/ftc_press_releases.py", "--limit", "20", "--pages", "3"),
        (root / "src/scrapers/ftc_legal_cases.py", "--limit", "20"),
        (root / "src/scrapers/ftc_consumer_scams.py", "--limit", "20"),
    ]

    failed = []
    for scraper_args in scrapers:
        script = scraper_args[0]
        args = scraper_args[1:]
        if run_scraper(script, *args) != 0:
            failed.append(script.name)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    if failed:
        print(f"Failed scrapers: {', '.join(failed)}")
    else:
        print("All scrapers completed successfully!")

    # Show data directory contents
    data_dir = root / "data"
    if data_dir.exists():
        print(f"\nData files created:")
        for file in sorted(data_dir.glob("*.jsonl")):
            size = file.stat().st_size
            print(f"  {file.name:40s} ({size:,} bytes)")

if __name__ == "__main__":
    main()
