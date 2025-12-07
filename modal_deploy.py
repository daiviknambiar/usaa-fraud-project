"""
Modal deployment script for FTC Streamlit Dashboard
"""
import modal
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = modal.App("ftc-streamlit-dashboard")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "streamlit==1.39.0",
        "pandas==2.2.3",
        "plotly==5.24.1",
        "python-dotenv==1.0.1",
        "supabase==2.10.0",
        "beautifulsoup4==4.12.3",
        "requests==2.32.3",
    )
    .add_local_dir("dashboard", "/root/dashboard")
    .add_local_dir("src", "/root/src")
    .add_local_dir("data", "/root/data")
    .add_local_dir("visualizations", "/root/visualizations")  # ← ADD THIS LINE
)

# Get secrets from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

# Create secrets for Modal deployment
@app.function(
    image=image,
    secrets=[modal.Secret.from_dict({
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_KEY": SUPABASE_KEY,
    })],
)
@modal.concurrent(max_inputs=10)
@modal.web_server(8501, startup_timeout=60)
def run_streamlit():
    """Run the Streamlit dashboard"""
    import subprocess
    import sys

    # Set working directory to /root
    subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "/root/dashboard/pages/app.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
        ]
    )