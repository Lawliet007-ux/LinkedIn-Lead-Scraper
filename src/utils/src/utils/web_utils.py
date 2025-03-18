import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import urljoin, urlparse

class WebsiteAnalyzer:
    """
    Utility class for analyzing websites and extracting contact information.
    """
    
    def __init__(self, headers=None):
        """
        Initialize the website analyzer.
        
        Args:
            headers (dict, optional): Request headers
        """
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Define patterns for contact information
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.phone_pattern = r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
        
        # Social media patterns
        self.social_patterns = {
            "linkedin": r'linkedin\.com/(?:company|school)/([^/"\s]+)',
            "twitter": r'(?:twitter\.com|x\.com)/([^/"\s]+)',
            "facebook": r'facebook\.com/([^/"\s]+)',
            "instagram": r'instagram\.com/([^/"\s]+)',
            "youtube": r'youtube\.com/(?:channel|user|c)/([^/"\s]+)'
        }
        
        # Contact page keywords
        self.contact_keywords = ['contact', 'about', 'team', 'connect', 'reach', 'support']
        
    def analyze_website(self, website_url):
        """
        Analyze a website to extract contact information.
        
        Args:
            website_url (str): Website URL
            
        Returns:
            dict: Contact information
        """
        if not website_url:
            return {}
            
        contact_info = {
            "emails": [],
            "phone_numbers": [],
            "social_media": {}
        }
        
        try:
            # Get the main page
            response = self._make_request(website_url)
            if not response:
                return contact_info
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract emails from main page
            emails = self._extract_emails(response.text)
            contact_info["emails"].extend(emails)
            
            # Extract phone numbers from main page
            phone_numbers = self._extract_phone_numbers(response.text)
            contact_info["phone_numbers"].extend(phone_numbers)
            
            # Extract social media links
            social_media = self._extract_social_media(response.text)
            contact_info["social_media"].update(social_media)
            
            # Find and analyze contact pages
            contact_links = self._find_contact_pages(website_url, soup)
            
            for link in contact_links[:3]:  # Limit to first 3 contact pages for efficiency
                contact_page_info = self._analyze_contact_page(link)
                
                contact_info["emails"].extend(contact_page_info.get("emails", []))
                contact_info["phone_numbers"].extend(contact_page_info.get("phone_numbers", []))
                
                if contact_page_info.get("social_media"):
                    for platform, handle in contact_page_info["social_media"].items():
                        if platform not in contact_info["social_media"]:
                            contact_info["social_media"][platform] = handle
            
            # Remove duplicates
            contact_info["emails"] = list(set(contact_info["emails"]))
            contact_info["phone_numbers"] = list(set([self._format_phone_number(phone) for phone in contact_info["phone_numbers"]]))
            
        except Exception as e:
            print(f"Error analyzing website {website_url}: {e}")
            
        return contact_info
    
    def _make_request(self, url, timeout=10):
        """Make an HTTP request with error handling and rate limiting."""
        try:
            # Add random delay to avoid detection
            time.sleep(random.uniform(0.5, 2))
            
            response = requests.get(url, headers=self.headers, timeout=timeout)
            
            if response.status_code == 200:
                return response
            else:
                print(f"Failed to request {url}: Status code {response.status_code}")
                return None
        except Exception as e:
            print(f"Request error for {url}: {e}")
            return None
    
    def _extract_emails(self, text):
        """Extract email addresses from text."""
        if not text:
            return []
            
        # Find all email addresses
        emails = re.findall(self.email_pattern, text)
        
        # Filter out likely invalid emails
        filtered_emails = []
        for email in emails:
            # Skip common false positives
            if '@example' in email or '@domain' in email or '@email' in email:
                continue
                
            # Skip image URLs that might contain @ symbols
            if '.jpg@' in email or '.png@' in email or '.gif@' in email:
                continue
                
            filtered_emails.append(email)
            
        return filtered_emails
    
    def _extract_phone_numbers(self, text):
        """Extract phone numbers from text."""
        if not text:
            return []
            
        # Find potential phone numbers
        matches = re.findall(self.phone_pattern, text)
        
        # Process matches to get full phone numbers
        phone_numbers = []
        for match in matches:
            if len(match) >= 2:
                # Combine country code and local number if both exist
                phone = ''.join(part for part in match if part)
                phone_numbers.append(phone)
            
        return phone_numbers
    
    def _format_phone_number(self, phone):
        """Format a phone number consistently."""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Format based on length
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11:
            return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone  # Return original if can't format consistently
    
    def _extract_social_media(self, text):
        """Extract social media handles from text."""
        social_media = {}
        
        for platform, pattern in self.social_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                # Use the first match
                handle = matches[0]
                
                # Clean up handle
                handle = handle.strip('/')
                handle = re.sub(r'\?.*$', '',
