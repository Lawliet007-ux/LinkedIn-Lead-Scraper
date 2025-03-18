import re
import itertools

class EmailExtractor:
    """
    Utility class for extracting and generating email addresses.
    """
    
    def __init__(self):
        # Standard email pattern
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        # Common email formats for generation
        self.email_formats = [
            "{first}.{last}@{domain}",
            "{first_initial}{last}@{domain}",
            "{first}@{domain}",
            "{last}@{domain}",
            "{first_initial}.{last}@{domain}",
            "{first}{last_initial}@{domain}",
            "{first}_{last}@{domain}"
        ]
    
    def extract_emails_from_text(self, text):
        """
        Extract all email addresses from text.
        
        Args:
            text (str): Text to extract emails from
            
        Returns:
            list: List of extracted email addresses
        """
        if not text:
            return []
            
        return list(set(re.findall(self.email_pattern, text)))
    
    def extract_email_from_text(self, text):
        """
        Extract the first email address from text.
        
        Args:
            text (str): Text to extract email from
            
        Returns:
            str or None: First extracted email address or None
        """
        emails = self.extract_emails_from_text(text)
        return emails[0] if emails else None
    
    def detect_email_pattern(self, emails):
        """
        Detect common email pattern from a list of emails.
        
        Args:
            emails (list): List of email addresses
            
        Returns:
            str or None: Detected email pattern or None
        """
        if not emails or len(emails) < 2:
            return None
            
        # Extract domains and usernames
        domains = set()
        usernames = []
        
        for email in emails:
            parts = email.split('@')
            if len(parts) != 2:
                continue
                
            username, domain = parts
            domains.add(domain)
            usernames.append(username)
            
        # If multiple domains, can't determine a pattern
        if len(domains) != 1:
            return None
            
        domain = list(domains)[0]
        
        # Analyze username patterns
        patterns = []
        for username in usernames:
            if '.' in username:
                pattern = "first.last"
            elif '_' in username:
                pattern = "first_last"
            elif len(username) <= 2:
                pattern = "initials"
            else:
                # Check if it's first initial + last name
                if re.match(r'^[a-z][a-z]{2,}$', username):
                    pattern = "firstinitiallast"
                else:
                    pattern = "unknown"
            
            patterns.append(pattern)
            
        # Count pattern frequencies
        pattern_counts = {}
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
        # Find most common pattern
        most_common = max(pattern_counts.items(), key=lambda x: x[1])
        
        return most_common[0]
    
    def generate_likely_email(self, name, company_name, company_website, known_emails=None):
        """
        Generate likely email address based on name and company information.
        
        Args:
            name (str): Person's full name
            company_name (str): Company name
            company_website (str): Company website URL
            known_emails (list, optional): List of known email addresses from the company
            
        Returns:
            str or None: Generated email address or None
        """
        if not name or name == "Unknown" or not company_website:
            return None
            
        # Extract domain from website
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', company_website)
        if not domain_match:
            return None
            
        domain = domain_match.group(1)
        
        # Extract first and last name
        name_parts = name.lower().split()
        if len(name_parts) < 2:
            return None
            
        first_name = name_parts[0]
        last_name = name_parts[-1]
        
        # Get first initials
        first_initial = first_name[0] if first_name else ""
        last_initial = last_name[0] if last_name else ""
        
        # Detect pattern from known emails if available
        if known_emails and len(known_emails) > 0:
            pattern = self.detect_email_pattern(known_emails)
            if pattern:
                if pattern == "first.last":
                    return f"{first_name}.{last_name}@{domain}"
                elif pattern == "first_last":
                    return f"{first_name}_{last_name}@{domain}"
                elif pattern == "initials":
                    return f"{first_initial}{last_initial}@{domain}"
                elif pattern == "firstinitiallast":
                    return f"{first_initial}{last_name}@{domain}"
        
        # Try common formats
        email_candidates = []
        
        for format_str in self.email_formats:
            email = format_str.format(
                first=first_name,
                last=last_name,
                first_initial=first_initial,
                last_initial=last_initial,
                domain=domain
            )
            email_candidates.append(email)
            
        # For now, just return the most common format
        return email_candidates[0] if email_candidates else None
