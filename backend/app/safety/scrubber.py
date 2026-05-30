"""
ALAS PII Scrubber (Phase 12)

A lightweight regex-based Personal Identifiable Information (PII) scrubber.
Ensures that sensitive data (emails, phones, SSNs, Credit Cards) is masked 
before leaving the local machine for cloud inference.
"""
import re
import logging

logger = logging.getLogger("alas.safety.scrubber")

class PIIScrubber:
    def __init__(self):
        # Regex patterns for common PII
        self.patterns = {
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "PHONE": r'\b(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\b',
            "SSN": r'\b\d{3}[-.\s]\d{2}[-.\s]\d{4}\b',
            "CREDIT_CARD": r'\b(?:\d[ -]*?){13,16}\b',
            "IPV4": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }
        
    def scrub_text(self, text: str) -> str:
        """
        Scan and redact PII from the text.
        Returns the scrubbed text.
        """
        if not text:
            return text
            
        scrubbed_text = text
        redaction_count = 0
        
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, scrubbed_text)
            if matches:
                # Count actual matches to log
                redaction_count += len(matches) if isinstance(matches[0], str) else len(matches)
                scrubbed_text = re.sub(pattern, f"[REDACTED_{pii_type}]", scrubbed_text)
                
        if redaction_count > 0:
            logger.info(f"🛡️ PII Scrubber activated: Redacted {redaction_count} sensitive fields before cloud routing.")
            
        return scrubbed_text

# Global singleton
_scrubber = PIIScrubber()

def get_scrubber() -> PIIScrubber:
    return _scrubber
