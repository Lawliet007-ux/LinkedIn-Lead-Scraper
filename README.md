# LinkedIn-Lead-Scraper

LinkedIn Lead Scraper
A powerful tool to generate business leads by combining data from LinkedIn profiles and company websites.
Features

Search LinkedIn profiles based on keywords, location, industry, and company size
Extract comprehensive profile information including names, titles, and companies
Find and verify contact information from company websites
Smart email pattern recognition
Export data to CSV or Excel formats
Clean, intuitive user interface

Installation

Clone this repository

bashCopygit clone https://github.com/yourusername/linkedin-lead-scraper.git
cd linkedin-lead-scraper

Create a virtual environment (recommended)

bashCopypython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies

bashCopypip install -r requirements.txt

Install Chrome WebDriver (required for Selenium)

Download the appropriate version for your Chrome browser from ChromeDriver website
Place the executable in your PATH or in the project directory



Usage
Command Line Interface
bashCopypython src/main.py --keywords "CTO startup" --location "San Francisco" --limit 10
Web Interface
bashCopypython src/app.py
Then open your browser and navigate to http://localhost:5000
Python API
pythonCopyfrom src.scraper import LinkedInLeadScraper

scraper = LinkedInLeadScraper()
leads = scraper.generate_leads(
    keywords="CTO startup",
    location="San Francisco",
    limit=5
)
scraper.export_to_csv("leads.csv")
Configuration
You can configure various settings in config.yml:

Rate limiting to avoid detection
Proxy settings for distributed scraping
Default search parameters
Output formatting
