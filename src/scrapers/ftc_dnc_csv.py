"""
FTC Do Not Call CSV Data Scraper
Alternative method using weekly CSV files from FTC
"""

import requests
import csv
import json
from pathlib import Path
from datetime import datetime
import io


def save_jsonl(data, filename):
    """Save data to JSONL file"""
    filepath = Path(filename)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def is_fraud(text):
    """Simple fraud keyword detection"""
    fraud_keywords = [
        'fraud', 'scam', 'phishing', 'identity theft', 'robocall',
        'impersonat', 'deceptive', 'unauthorized', 'fake', 'illegal',
        'telemarket', 'spam', 'spoofing', 'theft', 'debt', 'medicare',
        'social security', 'irs', 'warranty', 'prize', 'sweepstakes'
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in fraud_keywords)


class DNCCSVScraper:
    """Scraper for FTC DNC CSV files"""
    
    def __init__(self, csv_file=None):
        self.csv_file = csv_file
        self.csv_url = "https://www.ftc.gov/sites/default/files/DNC%20Complaints%20Data.csv"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def fetch_csv_data(self):
        """Load CSV data from local file or download"""
        
        # If local file provided, use that
        if self.csv_file:
            print(f"Loading DNC complaints from local file: {self.csv_file}")
            try:
                with open(self.csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    complaints = list(reader)
                print(f"✓ Loaded {len(complaints)} complaints from local file")
                return complaints
            except FileNotFoundError:
                print(f"✗ Error: File not found: {self.csv_file}")
                return []
            except Exception as e:
                print(f"✗ Error reading file: {e}")
                return []
        
        # Otherwise try to download
        print(f"Downloading DNC complaints CSV from FTC...")
        print(f"URL: {self.csv_url}")
        
        try:
            response = self.session.get(self.csv_url, timeout=60)
            response.raise_for_status()
            
            # Parse CSV
            csv_content = response.content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_content))
            
            complaints = list(reader)
            print(f"Downloaded {len(complaints)} complaints from CSV")
            
            return complaints
            
        except requests.exceptions.Timeout:
            print("Error: Request timed out")
            print("The FTC website may be slow. Try again later.")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error downloading CSV: {e}")
            return []
        except Exception as e:
            print(f"Error parsing CSV: {e}")
            return []
    
    def process_complaints(self, complaints):
        """Process CSV complaints into standardized format"""
        processed = []
        
        for complaint in complaints:
            # Use exact column names from your CSV
            phone_number = complaint.get('Company_Phone_Number', 'Unknown')
            created_date = complaint.get('Created_Date', '')
            violation_date = complaint.get('Violation_Date', '')
            city = complaint.get('Consumer_City', '')
            state = complaint.get('Consumer_State', '')
            area_code = complaint.get('Consumer_Area_Code', '')
            subject = complaint.get('Subject', 'Unknown')
            is_robocall = complaint.get('Recorded_Message_Or_Robocall', 'N').upper() == 'Y'
            
            # Create descriptive body
            body = f"""
Do Not Call Complaint Report

Phone Number: {phone_number}
Date Reported: {created_date}
Violation Date: {violation_date}
Location: {city}, {state} (Area Code: {area_code})
Subject: {subject}
Robocall: {'Yes' if is_robocall else 'No'}

This complaint was filed with the FTC regarding unwanted calls. 
The caller used number {phone_number} and the subject was related to {subject}.
{'This was reported as an automated robocall.' if is_robocall else 'This was reported as a live caller.'}
            """.strip()
            
            title = f"DNC Complaint: {subject} - {phone_number}"
            
            # Create standardized record
            record = {
                'title': title,
                'url': f"https://www.ftc.gov/policy/public-comments/do-not-call-complaint",
                'published': created_date,
                'body': body,
                'source': 'FTC DNC Complaints',
                'metadata': {
                    'phone_number': phone_number,
                    'violation_date': violation_date,
                    'location': f"{city}, {state}",
                    'area_code': area_code,
                    'subject': subject,
                    'is_robocall': is_robocall
                }
            }
            
            # Check if fraud-related
            if is_fraud(body) or is_fraud(subject):
                processed.append(record)
        
        return processed
    
    def run(self, output_file='data/dnc_complaints.jsonl', limit=None):
        """Main method to download and save DNC complaints"""
        # Fetch CSV data
        complaints = self.fetch_csv_data()
        
        if not complaints:
            print("No complaints retrieved")
            return []
        
        # Limit if specified
        if limit:
            complaints = complaints[:limit]
            print(f"Limited to {limit} complaints")
        
        # Process complaints
        processed = self.process_complaints(complaints)
        
        print(f"Filtered to {len(processed)} fraud-related complaints")
        
        # Save to JSONL
        if processed:
            save_jsonl(processed, output_file)
            print(f"✅ Saved {len(processed)} complaints to {output_file}")
        
        return processed


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape FTC DNC CSV Data')
    parser.add_argument('--file', help='Path to local CSV file')
    parser.add_argument('--limit', type=int, help='Limit number of complaints to process')
    parser.add_argument('--output', default='data/dnc_complaints.jsonl', help='Output file')
    
    args = parser.parse_args()
    
    scraper = DNCCSVScraper(csv_file=args.file)
    scraper.run(output_file=args.output, limit=args.limit)


if __name__ == "__main__":
    main()