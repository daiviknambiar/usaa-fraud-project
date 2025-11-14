#!/bin/bash

# FTC Press Releases Scrapy Spider Runner
# Usage: ./run_spider.sh [options]

cd "$(dirname "$0")"

# Default values
LOG_LEVEL="INFO"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug)
            LOG_LEVEL="DEBUG"
            shift
            ;;
        --help)
            echo "Usage: ./run_spider.sh [options]"
            echo ""
            echo "Options:"
            echo "  --debug        Enable debug logging"
            echo "  --help         Show this help message"
            echo ""
            echo "The spider will scrape the first 4 pages of FTC press releases."
            echo ""
            echo "Examples:"
            echo "  ./run_spider.sh          # Run spider"
            echo "  ./run_spider.sh --debug  # Run with debug logging"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build the command
CMD="python3 -m scrapy crawl press_releases -L $LOG_LEVEL"

echo "Running: $CMD"
echo "Spider will scrape the first 4 pages"
echo "Output will be saved to: data/ftc_press_releases_scrapy.json"
echo ""

# Run the spider
eval $CMD
