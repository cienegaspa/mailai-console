"""Text processing utilities for email content."""

import re
import html
from typing import List, Optional
from bs4 import BeautifulSoup
import html2text


class TextProcessor:
    """Text processing utilities for email content normalization and chunking."""
    
    def __init__(self):
        self.html_to_text = html2text.HTML2Text()
        self.html_to_text.ignore_links = True
        self.html_to_text.ignore_images = True
        self.html_to_text.body_width = 0  # Don't wrap lines
    
    def clean_email_body(self, body: str) -> str:
        """Clean and normalize email body text."""
        if not body:
            return ""
        
        # Convert HTML to text if needed
        if '<html>' in body.lower() or '<div>' in body.lower():
            body = self.html_to_text.handle(body)
        
        # Decode HTML entities
        body = html.unescape(body)
        
        # Remove email signatures (simple heuristic)
        body = self._remove_signatures(body)
        
        # Remove quoted email chains
        body = self._remove_quoted_content(body)
        
        # Normalize whitespace
        body = re.sub(r'\n\s*\n', '\n\n', body)  # Multiple newlines to double
        body = re.sub(r'[ \t]+', ' ', body)      # Multiple spaces/tabs to single space
        body = body.strip()
        
        return body
    
    def _remove_signatures(self, text: str) -> str:
        """Remove email signatures using common patterns."""
        # Common signature patterns
        signature_patterns = [
            r'\n--\s*\n.*',  # Standard -- signature delimiter
            r'\nBest regards,?\s*\n[^\n]*\n[^\n]*\n[^\n]*$',
            r'\nSincerely,?\s*\n[^\n]*\n[^\n]*\n[^\n]*$',
            r'\nThanks?,?\s*\n[^\n]*\n[^\n]*$',
            r'\nRegards,?\s*\n[^\n]*\n[^\n]*$',
        ]
        
        for pattern in signature_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text
    
    def _remove_quoted_content(self, text: str) -> str:
        """Remove quoted email content (replies/forwards)."""
        lines = text.split('\n')
        cleaned_lines = []
        
        skip_quoted = False
        for line in lines:
            # Check for common quote indicators
            if any(indicator in line.lower() for indicator in [
                'on ', ' wrote:', 'from:', 'sent:', '-----original message-----',
                '________________________________', 'begin forwarded message'
            ]):
                skip_quoted = True
                break
            
            # Skip lines that start with > (quoted)
            if line.strip().startswith('>'):
                continue
                
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def chunk_text(
        self, 
        text: str, 
        chunk_size: int = 800, 
        overlap: int = 100
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        words = text.split()
        if len(words) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            chunks.append(chunk_text)
            
            # Move start position with overlap
            if end >= len(words):
                break
            start = max(start + chunk_size - overlap, start + 1)
        
        return chunks
    
    def extract_entities(self, text: str) -> dict:
        """Extract structured entities from text (dates, amounts, serials, etc.)."""
        entities = {
            'dates': [],
            'amounts': [],
            'serials': [],
            'rma_numbers': [],
            'emails': [],
            'phone_numbers': []
        }
        
        if not text:
            return entities
        
        # Date patterns
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
        ]
        
        for pattern in date_patterns:
            entities['dates'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Amount patterns
        amount_patterns = [
            r'\$[\d,]+\.?\d*',
            r'\b\d+\.\d{2}\b'
        ]
        
        for pattern in amount_patterns:
            entities['amounts'].extend(re.findall(pattern, text))
        
        # Serial number patterns (CoolSculpting specific)
        serial_patterns = [
            r'\bCS-\d{4}-\d{3,}\b',
            r'\bSerial:?\s*([A-Z0-9-]+)\b'
        ]
        
        for pattern in serial_patterns:
            entities['serials'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # RMA numbers
        rma_patterns = [
            r'\bRMA[#:\s-]*(\d{4}-\d{4,})\b',
            r'\bRMA[#:\s-]*([A-Z0-9-]+)\b'
        ]
        
        for pattern in rma_patterns:
            entities['rma_numbers'].extend(re.findall(pattern, text, re.IGNORECASE))
        
        # Email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, text)
        
        # Phone numbers
        phone_patterns = [
            r'\(\d{3}\)\s*\d{3}-\d{4}',
            r'\d{3}-\d{3}-\d{4}',
            r'\d{3}\.\d{3}\.\d{4}'
        ]
        
        for pattern in phone_patterns:
            entities['phone_numbers'].extend(re.findall(pattern, text))
        
        return entities
    
    def highlight_text(self, text: str, highlights: List[str]) -> str:
        """Add HTML highlighting to specific text spans."""
        if not highlights:
            return text
        
        highlighted = text
        for highlight in highlights:
            if highlight in highlighted:
                highlighted = highlighted.replace(
                    highlight,
                    f'<mark>{highlight}</mark>'
                )
        
        return highlighted
    
    def extract_quotes(self, text: str, min_length: int = 10) -> List[str]:
        """Extract meaningful quoted sentences from text."""
        if not text:
            return []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        quotes = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Filter out short or meaningless sentences
            if (len(sentence) >= min_length and 
                not sentence.lower().startswith(('hi', 'hello', 'thank', 'please', 'best')) and
                any(word in sentence.lower() for word in [
                    'return', 'rma', 'issue', 'problem', 'error', 'defect',
                    'credit', 'refund', 'shipping', 'freight', 'packaging'
                ])):
                quotes.append(sentence.strip() + '.')
        
        return quotes[:5]  # Return top 5 quotes
    
    def normalize_query_terms(self, terms: List[str]) -> List[str]:
        """Normalize and clean query terms."""
        normalized = []
        
        for term in terms:
            if not term:
                continue
                
            # Clean term
            term = term.strip().lower()
            
            # Skip very short terms
            if len(term) < 3:
                continue
            
            # Skip common stop words
            if term in ['the', 'and', 'or', 'but', 'for', 'with', 'from', 'to']:
                continue
            
            normalized.append(term)
        
        return list(set(normalized))  # Deduplicate