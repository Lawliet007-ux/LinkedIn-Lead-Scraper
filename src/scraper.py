import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import yaml

from utils.email_utils import EmailExtractor
from utils.web_utils import WebsiteAnalyzer
from utils.export_utils import DataExporter

class LinkedInLeadScraper:
    """
    A tool to scrape LinkedIn and company websites for lead generation.
    Features:
    - LinkedIn profile data extraction
    - Company website contact information extraction
    - Email pattern recognition
    - Data export to CSV/Excel
    - API integration capability
    """
    
    def __init__(self, config_file=None):
        """
        Initialize the scraper with optional configuration.
        
        Args:
            config_file (str, optional): Path to YAML configuration file
        """
        # Load config if provided
        self.config = {}
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        
        # Set default headers
        self.headers = {
            'User-Agent': self.config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        }
        
        # Initialize data storage
        self.leads_data = []
        
        # Initialize utilities
        self.email_extractor = EmailExtractor()
        self.website_analyzer = WebsiteAnalyzer(self.headers)
        self.data_exporter = DataExporter()
        
        # Set up Selenium WebDriver
        self.setup_driver()
        
    def setup_driver(self):
        """Set up the Selenium WebDriver with appropriate options."""
        chrome_options = Options()
        
        # Apply headless mode if configured
        if self.config.get('headless', True):
            chrome_options.add_argument("--headless")
            
        # Add standard options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Add any custom options from config
        for option in self.config.get('chrome_options', []):
            chrome_options.add_argument(option)
            
        # Initialize the driver
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Set default timeout
        self.driver.implicitly_wait(self.config.get('timeout', 10))
        
    def search_linkedin(self, keywords, location=None, industry=None, company_size=None, limit=10):
        """
        Search LinkedIn for profiles matching the given criteria.
        
        Args:
            keywords (str): Search keywords
            location (str, optional): Location filter
            industry (str, optional): Industry filter
            company_size (str, optional): Company size filter
            limit (int, optional): Maximum number of results to return
            
        Returns:
            list: List of LinkedIn profile URLs
        """
        print(f"Searching LinkedIn for: {keywords}")
        
        # Construct search URL with parameters
        search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords.replace(' ', '%20')}"
        if location:
            search_url += f"&location={location.replace(' ', '%20')}"
        if industry:
            search_url += f"&industry={industry.replace(' ', '%20')}"
        if company_size:
            search_url += f"&companySize={company_size.replace(' ', '%20')}"
            
        # Navigate to search page
        self.driver.get(search_url)
        
        # Check if login is required
        if "login" in self.driver.current_url or "signup" in self.driver.current_url:
            raise Exception("LinkedIn login required. Please add authentication handling.")
            
        # Wait for search results to load
        time.sleep(self.config.get('search_delay', 2))
        
        # Extract profile links
        profile_elements = self.driver.find_elements(By.CSS_SELECTOR, ".search-result__info .search-result__result-link")
        
        # Handle pagination if needed and configured
        if len(profile_elements) < limit and self.config.get('use_pagination', True):
            pages_to_check = min(limit // 10 + 1, self.config.get('max_pages', 5))
            
            for page in range(2, pages_to_check + 1):
                # Click next page or navigate to next page URL
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-pagination__button--next")
                    next_button.click()
                    time.sleep(self.config.get('pagination_delay', 2))
                    
                    # Get additional profile elements
                    additional_elements = self.driver.find_elements(By.CSS_SELECTOR, ".search-result__info .search-result__result-link")
                    profile_elements.extend(additional_elements)
                    
                    # Break if we have enough profiles
                    if len(profile_elements) >= limit:
                        break
                except:
                    break
        
        # Extract profile URLs
        profile_urls = []
        for element in profile_elements[:limit]:
            try:
                href = element.get_attribute("href")
                if href and "/in/" in href:
                    profile_urls.append(href.split("?")[0])  # Remove query parameters
            except:
                continue
                
        return profile_urls
    
    def extract_linkedin_profile(self, profile_url):
        """
        Extract information from a LinkedIn profile.
        
        Args:
            profile_url (str): LinkedIn profile URL
            
        Returns:
            dict: Profile information
        """
        print(f"Extracting data from: {profile_url}")
        
        # Navigate to profile page
        self.driver.get(profile_url)
        
        # Add random delay to avoid detection
        time.sleep(random.uniform(
            self.config.get('min_delay', 2),
            self.config.get('max_delay', 4)
        ))
        
        # Initialize profile data dictionary
        profile_data = {
            "name": "Unknown",
            "title": "Unknown",
            "company": "Unknown",
            "location": "Unknown",
            "linkedin_url": profile_url,
            "company_website": None,
            "email": None
        }
        
        # Extract basic profile information
        try:
            profile_data["name"] = self.driver.find_element(By.CSS_SELECTOR, ".pv-top-card--list .text-heading-xlarge").text
        except:
            pass
            
        try:
            profile_data["title"] = self.driver.find_element(By.CSS_SELECTOR, ".pv-top-card--list .text-body-medium").text
        except:
            pass
            
        try:
            profile_data["company"] = self.driver.find_element(By.CSS_SELECTOR, ".pv-top-card--experience-list-item .pv-entity__secondary-title").text
        except:
            pass
            
        try:
            profile_data["location"] = self.driver.find_element(By.CSS_SELECTOR, ".pv-top-card--list-bullet .t-16").text
        except:
            pass
            
        # Find company website if available
        if profile_data["company"] != "Unknown":
            profile_data["company_website"] = self.find_company_website(profile_data["company"])
        
        # Extract email using pattern matching
        profile_data["email"] = self.email_extractor.extract_email_from_text(self.driver.page_source)
        
        # Try to find contact info section if available
        try:
            # Look for contact info link
            contact_info_link = self.driver.find_element(By.CSS_SELECTOR, "a[data-control-name='contact_see_more']")
            contact_info_link.click()
            
            # Wait for modal to appear
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pv-contact-info"))
            )
            
            # Extract email from contact info
            try:
                email_element = self.driver.find_element(By.CSS_SELECTOR, ".pv-contact-info__contact-type.ci-email .pv-contact-info__contact-link")
                profile_data["email"] = email_element.text
            except:
                pass
                
            # Close the modal
            try:
                close_button = self.driver.find_element(By.CSS_SELECTOR, "button.artdeco-modal__dismiss")
                close_button.click()
            except:
                pass
        except:
            pass
        
        return profile_data
    
    def find_company_website(self, company_name):
        """
        Find company website using search engine.
        
        Args:
            company_name (str): Company name
            
        Returns:
            str: Company website URL or None
        """
        # Try LinkedIn company search first if configured
        if self.config.get('use_linkedin_company_search', True):
            try:
                company_search_url = f"https://www.linkedin.com/company/{company_name.lower().replace(' ', '-')}/"
                self.driver.get(company_search_url)
                time.sleep(1)
                
                # Check if we landed on a company page
                if "/company/" in self.driver.current_url and not "search" in self.driver.current_url:
                    # Try to find website link
                    try:
                        website_element = self.driver.find_element(By.CSS_SELECTOR, ".org-top-card-primary-actions__inner a[data-control-name='page_details_website']")
                        return website_element.get_attribute("href")
                    except:
                        pass
            except:
                pass
        
        # Fall back to search engine
        search_url = f"https://www.google.com/search?q={company_name.replace(' ', '+')}+official+website"
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=self.config.get('request_timeout', 10))
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract the first search result
            search_results = soup.select(".yuRUbf a")
            if search_results:
                website_url = search_results[0].get("href")
                
                # Basic validation of URL
                if website_url and website_url.startswith("http"):
                    return website_url
        except Exception as e:
            print(f"Error finding company website: {e}")
            
        return None
    
    def extract_contact_info_from_website(self, website_url):
        """
        Extract contact information from a company website.
        
        Args:
            website_url (str): Company website URL
            
        Returns:
            dict: Contact information
        """
        if not website_url:
            return {}
            
        return self.website_analyzer.analyze_website(website_url)
    
    def generate_leads(self, keywords, location=None, industry=None, company_size=None, limit=10):
        """
        Generate leads based on search criteria.
        
        Args:
            keywords (str): Search keywords
            location (str, optional): Location filter
            industry (str, optional): Industry filter
            company_size (str, optional): Company size filter
            limit (int, optional): Maximum number of results
            
        Returns:
            list: List of lead data
        """
        profile_urls = self.search_linkedin(keywords, location, industry, company_size, limit)
        
        leads = []
        for url in profile_urls:
            try:
                # Extract LinkedIn profile data
                profile_data = self.extract_linkedin_profile(url)
                
                # Extract company website information if available
                if profile_data["company_website"]:
                    contact_info = self.extract_contact_info_from_website(profile_data["company_website"])
                    
                    # Merge contact info into profile data
                    if contact_info.get("emails") and not profile_data["email"]:
                        profile_data["email"] = contact_info["emails"][0]
                    
                    profile_data["additional_emails"] = contact_info.get("emails", [])
                    profile_data["phone_numbers"] = contact_info.get("phone_numbers", [])
                    profile_data["social_media"] = contact_info.get("social_media", {})
                    
                    # Try to generate email if still not found
                    if not profile_data["email"] and profile_data["name"] != "Unknown":
                        generated_email = self.email_extractor.generate_likely_email(
                            profile_data["name"], 
                            profile_data["company"],
                            profile_data["company_website"],
                            contact_info.get("emails", [])
                        )
                        if generated_email:
                            profile_data["email"] = generated_email
                            profile_data["email_confidence"] = "Generated"
                
                leads.append(profile_data)
            except Exception as e:
                print(f"Error processing profile {url}: {e}")
                continue
            
        self.leads_data = leads
        return leads
    
    def export_to_csv(self, filename="leads_data.csv"):
        """Export leads data to CSV."""
        return self.data_exporter.export_to_csv(self.leads_data, filename)
        
    def export_to_excel(self, filename="leads_data.xlsx"):
        """Export leads data to Excel."""
        return self.data_exporter.export_to_excel(self.leads_data, filename)
        
    def export_to_json(self, filename="leads_data.json"):
        """Export leads data to JSON."""
        return self.data_exporter.export_to_json(self.leads_data, filename)
        
    def close(self):
        """Close the WebDriver."""
        self.driver.quit()


# Example usage
if __name__ == "__main__":
    scraper = LinkedInLeadScraper()
    
    try:
        # Generate leads
        leads = scraper.generate_leads(
            keywords="CTO startup",
            location="San Francisco",
            limit=5
        )
        
        # Print results
        for lead in leads:
            print(f"Name: {lead['name']}")
            print(f"Title: {lead['title']}")
            print(f"Company: {lead['company']}")
            print(f"Email: {lead['email']}")
            print(f"Website: {lead['company_website']}")
            print("---")
        
        # Export data
        scraper.export_to_csv()
        scraper.export_to_excel()
        
    finally:
        scraper.close()
