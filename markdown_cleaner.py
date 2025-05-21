import re
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote


class MarkdownCleaner:
    """Clean sports article content that has been converted to markdown for LLM consumption."""

    def __init__(self, verbose=False):
        self.verbose = verbose

    def clean(self, text):
        """Main cleaning method for sports articles converted to markdown."""
        if self.verbose:
            print("Starting sports article cleaning process...")
            original_length = len(text)

        # Apply cleaning methods in sequence
        cleaned_text = text
        cleaned_text = self._normalize_line_breaks(cleaned_text)
        cleaned_text = self._extract_article_date(cleaned_text)
        cleaned_text = self._clean_image_references(cleaned_text)
        cleaned_text = self._remove_logos(cleaned_text)
        cleaned_text = self._remove_general_links(cleaned_text)
        cleaned_text = self._fix_text_formatting(cleaned_text)
        cleaned_text = self._remove_betting_promotions(cleaned_text)
        cleaned_text = self._remove_social_media_promotions(cleaned_text)
        cleaned_text = self._remove_other_article_promotions(cleaned_text)
        cleaned_text = self._remove_footer_elements(cleaned_text)
        cleaned_text = self._fix_bold_formatting(cleaned_text)
        cleaned_text = self._fix_heading_structure(cleaned_text)
        cleaned_text = self._clean_whitespace(cleaned_text)
        
        # Report statistics if verbose
        if self.verbose:
            final_length = len(cleaned_text)
            reduction = (1 - final_length / original_length) * 100
            print(f"Cleaning complete. Text reduced by {reduction:.2f}%")
            print(f"Original: {original_length} chars -> Final: {final_length} chars")
        
        return cleaned_text

    def _normalize_line_breaks(self, text):
        """Normalize line breaks to ensure consistent processing."""
        # Convert all types of line breaks to standard unix line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text

    def _extract_article_date(self, text):
        """Extract and format the article date."""
        # Look for date patterns like "08 May, 2025 • 7:52 pm UTC"
        date_pattern = r'(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+(\d{4})\s*(?:•|·)?\s*(\d{1,2}):(\d{2})\s*([ap]m)?\s*([A-Z]{2,4})?'
        
        date_match = re.search(date_pattern, text)
        if date_match:
            # Get entire match
            original_date_str = date_match.group(0)
            
            # Format the date more cleanly
            day, month, year, hour, minute, ampm, timezone = date_match.groups()
            
            # Build a clean date format
            clean_date = f"Published on {day} {month} {year}"
            if hour and minute:
                time_str = f"{hour}:{minute}"
                if ampm:
                    time_str += f" {ampm}"
                clean_date += f" at {time_str}"
            if timezone:
                clean_date += f" {timezone}"
                
            # Replace with cleaner format
            text = text.replace(original_date_str, clean_date)
            
            # Move the date to the beginning of the article after any title
            # First, remove it from its current position
            text = text.replace(clean_date, '')
            
            # Find the first paragraph after potential image
            text_parts = text.split('\n\n', 2)
            if len(text_parts) >= 2:
                # If there's an image in the first part, insert after image and before content
                if '![' in text_parts[0]:
                    text = text_parts[0] + '\n\n' + clean_date + '\n\n' + '\n\n'.join(text_parts[1:])
                else:
                    # Otherwise insert after first paragraph which is likely the title
                    text = text_parts[0] + '\n\n' + clean_date + '\n\n' + '\n\n'.join(text_parts[1:])
            else:
                # If splitting didn't work well, just add at beginning
                text = clean_date + '\n\n' + text
        
        return text

    def _clean_image_references(self, text):
        """Clean image references in markdown format."""
        # Pattern for markdown images: ![alt text](url)
        img_pattern = r'!\[(.*?)\]\((.*?)\)'
        
        def clean_image_ref(match):
            alt_text = match.group(1).strip()
            url = match.group(2).strip()
            
            # Clean up alt text
            alt_text = re.sub(r'\s+image$', '', alt_text)  # Remove " image" suffix
            alt_text = re.sub(r'\bimage\b\s+', '', alt_text)  # Remove "image" word
            
            # Clean up URL: remove tracking parameters, unescape URL-encoded chars
            url_parts = urlparse(url)
            clean_url = url_parts.scheme + '://' + url_parts.netloc + url_parts.path
            
            # Clean up image path
            clean_url = clean_url.replace(' ', '%20')  # Fix spaces in URLs
            clean_url = re.sub(r'\.\s+', '.', clean_url)  # Fix "image. jpg" to "image.jpg"
            
            # Format the image reference properly
            return f"![{alt_text}]({clean_url})"
        
        text = re.sub(img_pattern, clean_image_ref, text)
        
        return text

    def _fix_text_formatting(self, text):
        """Fix text formatting issues."""
        # Fix spacing in dates and times within text
        text = re.sub(r'(\w+)\s*\*\*\s*,\s*\*\*\s*(\w+)', r'\1, \2', text)
        text = re.sub(r'(\d+)\s*\*\*\s*:\s*\*\*\s*(\d+)', r'\1:\2', text)
        
        # Fix spacing with punctuation
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Fix location formatting - common in sports articles
        text = re.sub(r'in\s+\*\*\s*(\w+)\s*\*\*\s*,\s*\*\*\s*(\w+)\s*\*\*', r'in **\1, \2**', text)
        
        # Fix team names with parentheses
        text = re.sub(r'(\w+)\s+Super\s+Giants\s+\(\s*LSG\s*\)', r'Lucknow Super Giants (LSG)', text)
        text = re.sub(r'Royal\s+Challengers\s+Bengaluru\s+\(\s*RCB\s*\)', r'Royal Challengers Bengaluru (RCB)', text)
        
        # Fix match numbers
        text = re.sub(r'match\s+no\.\s+(\d+)', r'match no. \1', text)
        
        # Fix stadium names
        text = re.sub(r'at\s+the\s+\*\*\s*(\w+(?:\s+\w+)*)\s+Stadium\s*\*\*', r'at the **\1 Stadium**', text)
        
        return text

    def _remove_betting_promotions(self, text):
        """Remove betting promotions and affiliate links."""
        # Betting promotion pattern
        betting_patterns = [
            r'\*\*\s*BET\s+NOW\s*:\s*\*\*\s*\[.*?\]\(https?:\/\/(?:bit\.ly|tinyurl\.com|goo\.gl)\/[^\s)]+\)',
            r'\[(?:Bet|Claim|Get|Grab|Win).*?(?:bonus|offer|promotion|bet|sign[\s-]?up).*?\]\(https?:\/\/(?:bit\.ly|tinyurl\.com|goo\.gl)\/[^\s)]+\)',
            r'\*\*.*?WIN\s+WELCOME\s+BONUS.*?\*\*',
            r'\[.*?(?:bet|claim|win|bonus|offer).*?\]\(https?:\/\/.*?\)',
        ]
        
        for pattern in betting_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        # Remove entire lines containing betting keywords
        betting_keywords = [
            'bet now', 'welcome bonus', 'sign up', 'click', 'sign-up', 'bonus code', 
            'free bet', 'promo code', 'deposit', 'betting', 'wagering', 'sportsbook'
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if not any(keyword in line_lower for keyword in betting_keywords):
                cleaned_lines.append(line)
                
        text = '\n'.join(cleaned_lines)
        
        return text

    def _remove_social_media_promotions(self, text):
        """Remove social media promotional content."""
        # Social media promotion patterns
        social_patterns = [
            r'\[Follow\s+(?:The\s+)?(?:\w+\s+)+on\s+(?:Twitter|Facebook|Instagram|WhatsApp|Telegram)\]\(https?:\/\/.*?\)',
            r'\[Subscribe\s+to\s+our\s+(?:YouTube|Facebook|Telegram)\s+channel\]\(https?:\/\/.*?\)',
            r'Follow\s+(?:us|The\s+\w+)\s+on\s+(?:Twitter|Facebook|Instagram|WhatsApp|Telegram)',
            r'https?:\/\/(?:sn-now\.com|bit\.ly)\/\w+(?:WhatsApp|Facebook|Twitter|Instagram)\w*',
        ]
        
        for pattern in social_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        # Remove lines with common social media promotional phrases
        social_keywords = [
            'follow us', 'join us', 'subscribe', 'like our', 'share this', 
            'connect with us', 'stay updated', 'don\'t miss', 'for more updates'
        ]
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if not any(keyword in line_lower for keyword in social_keywords):
                cleaned_lines.append(line)
                
        text = '\n'.join(cleaned_lines)
        
        return text

    def _remove_other_article_promotions(self, text):
        """Remove promotions for other articles."""
        # Article promotion patterns
        article_patterns = [
            r'\*\*\s*READ\s+MORE\s*:\s*\*\*\s*\[.*?\]\(https?:\/\/.*?\)',
            r'\[ALSO\s+READ:.*?\]\(https?:\/\/.*?\)',
            r'\*\*\s*RELATED:?\s*\*\*\s*\[.*?\]\(https?:\/\/.*?\)',
            r'\*\*\s*CHECK\s+OUT:?\s*\*\*\s*\[.*?\]\(https?:\/\/.*?\)',
        ]
        
        for pattern in article_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        return text

    def _remove_footer_elements(self, text):
        """Remove footer elements from the article."""
        # Footer patterns
        footer_patterns = [
            r'For\s+more\s+(?:updates|news|information)\s+on.*?visit\s+our\s+website',
            r'Don\'t\s+forget\s+to\s+(?:follow|subscribe|check)\s+us\s+on',
            r'Copyright\s+©\s+\d{4}.*?All\s+rights\s+reserved',
            r'© \d{4}(?:–\d{4})?\s+(?:\w+\s+)+\.\s+All\s+rights\s+reserved\.',
        ]
        
        for pattern in footer_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        return text

    def _fix_bold_formatting(self, text):
        """Fix bold formatting issues in the text."""
        # Fix multiple adjacent bold sections
        text = re.sub(r'\*\*\s+\*\*', ' ', text)
        text = re.sub(r'\*\*\)\s+\*\*', '**) ', text)
        text = re.sub(r'\*\*\s*,\s*\*\*', ', ', text)
        
        # Handle cases like ** Friday** to make it properly bold
        text = re.sub(r'\*\*\s+(\w+)\*\*', r'**\1**', text)
        text = re.sub(r'(\w+)\s+\*\*', r'\1**', text)
        
        # Fix bold formatting around punctuation
        text = re.sub(r'\*\*\s*([,.;:!?])', r'\1', text)
        
        # Fix double bold
        text = re.sub(r'\*\*\*\*', '**', text)
        
        return text

    def _fix_heading_structure(self, text):
        """Fix and normalize heading structure."""
        # Convert emphasized team matchups to headings
        team_match_pattern = r'(\w+(?:\s+\w+)*)\s+\((\w+)\)\s+(?:vs|versus|v\/s|will\s+(?:face|play|meet))\s+(\w+(?:\s+\w+)*)\s+\((\w+)\)'
        
        def team_to_heading(match):
            team1, abbr1, team2, abbr2 = match.groups()
            return f"## {team1} ({abbr1}) vs {team2} ({abbr2})"
        
        text = re.sub(team_match_pattern, team_to_heading, text)
        
        # Convert emphasized stadium locations to subheadings
        stadium_pattern = r'at\s+the\s+\*\*\s*([\w\s]+Stadium[\w\s]*)\s*\*\*\s+in\s+\*\*\s*([\w\s,]+)\s*\*\*'
        
        def stadium_to_heading(match):
            stadium, location = match.groups()
            return f"### Venue: {stadium} in {location}"
        
        text = re.sub(stadium_pattern, stadium_to_heading, text)
        
        # Add heading for important match information
        if 'match no.' in text.lower():
            match_info_pattern = r'(match\s+no\.\s+(\d+)[\s\S]*?IPL[\s\S]*?\d{4})'
            match = re.search(match_info_pattern, text, re.IGNORECASE)
            if match:
                match_info = match.group(1)
                text = text.replace(match_info, f"### Match Information\n{match_info}")
        
        return text

    def _remove_logos(self, text):
        """Remove logo images that are typically found in articles."""
        # Logo patterns - usually small images with "logo", "icon", "badge" in name
        logo_patterns = [
            r'!\[.*?(?:logo|icon|badge|emblem|symbol).*?\]\(.*?\)',  # Images with logo-related terms
            r'!\[.*?\]\(.*?(?:logo|icon|badge|emblem|symbol).*?\)',  # URLs with logo-related terms
            r'!\[.*?\]\(.*?(?:width|height)="?(?:20|30|40|50|60|70|80|90|100)"?.*?\)',  # Small sized images
            r'!\[\]\(.*?\)',  # Empty alt text images (often logos)
            r'<img[^>]*?(?:logo|icon|badge|emblem|symbol)[^>]*?>',  # HTML img with logo terms
            r'<img[^>]*?(?:width|height)="?(?:20|30|40|50|60|70|80|90|100)"?[^>]*?>',  # Small HTML images
        ]
        
        for pattern in logo_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
        return text
        
    def _remove_general_links(self, text: str) -> str:
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'

        # Replace markdown links with just the link text (remove the URL)
        text = re.sub(link_pattern, lambda m: m.group(1), text)

        return text

    def _clean_whitespace(self, text):
        """Clean excessive whitespace while preserving structure."""
        # Remove multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing whitespace on lines
        text = re.sub(r' +\n', '\n', text)
        
        # Ensure proper spacing around headings
        text = re.sub(r'(\n#{1,3} .+)\n(?!$|#|\n)', '\\1\n\n', text)
        
        # Remove repeated spaces within lines
        text = re.sub(r' {2,}', ' ', text)
        
        # Ensure document starts and ends cleanly
        text = text.strip()
        
        return text


def main():
    parser = argparse.ArgumentParser(description='Clean sports article markdown for LLM consumption')
    parser.add_argument('input', help='Input markdown text or file path')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--from-file', '-f', action='store_true', help='Read input from file instead of direct text')
    parser.add_argument('--keep-images', '-ki', action='store_true', help='Keep main content images')
    parser.add_argument('--keep-links', '-kl', action='store_true', help='Keep main content links')
    
    args = parser.parse_args()
    
    # Get input text
    if args.from_file:
        try:
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading input file: {e}")
            return
    else:
        text = args.input
    
    # Clean the text
    cleaner = MarkdownCleaner(verbose=args.verbose)
    
    cleaned_text = cleaner.clean(text)
    
    # Output the result
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            if args.verbose:
                print(f"Cleaned text saved to {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
    else:
        print(cleaned_text)


if __name__ == "__main__":
    main()