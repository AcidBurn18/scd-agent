"""
Input Sanitization Module for SCD Generator
Ensures clean, normalized, safe inputs with NIST control canonicalization
"""

import re
import unicodedata
import hashlib
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SanitizationResult:
    """Result of sanitizing a single text block"""
    id: str
    original_hash: str
    cleaned_text: str
    length_chars: int
    length_tokens_est: int
    redacted_entities: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    canonical_control_matches: List[Dict] = field(default_factory=list)
    confidence_score: float = 1.0


@dataclass
class SanitizationConfig:
    """Configuration for sanitization behavior"""
    pii_redaction: bool = True
    max_tokens: int = 4000
    reject_abusive_words: bool = True
    azure_only_policy: bool = True
    strict_character_policy: bool = True
    min_confidence_threshold: float = 0.70
    allowed_special_chars: set = field(default_factory=lambda: {' ', ',', '.', '\n', '\r', '\t', '-', '_', ':', '/', '(', ')'})


class InputSanitizer:
    """Main sanitizer class with all validation and cleaning logic"""
    
    # Abusive words list (expandable with variations)
    ABUSIVE_WORDS = {
        'fuck', 'fucking', 'fucked', 'fucker', 'fucks',
        'shit', 'shitty', 'shits', 'damn', 'damned',
        'bitch', 'bitching', 'bastard', 'bastards',
        'ass', 'asses', 'asshole', 'assholes', 'hell',
        'crap', 'crappy', 'piss', 'pissed', 'pissing',
        'cock', 'dick', 'dicks', 'pussy', 'pussies',
        'slut', 'sluts', 'whore', 'whores',
        'idiot', 'idiots', 'stupid', 'dumb', 'moron', 'morons', 'retard', 'retards'
    }
    
    # Non-Azure cloud providers to block
    NON_AZURE_CLOUDS = {
        'aws', 'amazon web services', 'ec2', 's3', 'lambda',
        'gcp', 'google cloud', 'gce', 'bigquery',
        'oracle cloud', 'oci', 'ibm cloud', 'alibaba cloud',
        'digitalocean', 'linode', 'heroku', 'cloudflare workers'
    }
    
    # PII patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    UUID_PATTERN = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
    IP_PATTERN = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
    API_KEY_PATTERN = re.compile(r'\b(?:api[_-]?key|secret[_-]?key|access[_-]?token)[:\s]*["\']?([A-Za-z0-9+/=_-]{20,})["\']?\b', re.IGNORECASE)
    
    # Prompt injection patterns
    INJECTION_PATTERNS = [
        r'ignore\s+(?:previous|all|the)\s+(?:instructions?|prompts?|rules?)',
        r'now\s+(?:write|act|behave|respond)',
        r'act\s+as\s+(?:a|an)\s+\w+',
        r'system\s*:\s*you\s+are',
        r'</?\s*(?:system|user|assistant)\s*>',
        r'<!--.*?-->',
    ]
    
    # NIST CSF control vocabulary (expandable)
    NIST_CONTROL_VOCAB = {
        'PR.AC-1': ['access control', 'identity management', 'authentication'],
        'PR.AC-3': ['remote access', 'vpn', 'secure remote'],
        'PR.AC-4': ['least privilege', 'access permissions', 'privilege management'],
        'PR.DS-1': ['data at rest', 'encryption at rest', 'storage encryption'],
        'PR.DS-2': ['data in transit', 'encryption in transit', 'tls', 'ssl'],
        'PR.IP-1': ['baseline configuration', 'secure configuration', 'hardening'],
        'DE.CM-1': ['network monitoring', 'traffic monitoring', 'network detection'],
        'DE.AE-1': ['baseline behavior', 'anomaly detection', 'behavioral analysis'],
        'RS.RP-1': ['response plan', 'incident response', 'response procedures'],
        'RC.RP-1': ['recovery plan', 'disaster recovery', 'business continuity'],
    }
    
    def __init__(self, config: Optional[SanitizationConfig] = None):
        self.config = config or SanitizationConfig()
        
    def sanitize_batch(self, text_blocks: List[str], metadata: Optional[Dict] = None) -> Dict:
        """
        Sanitize a batch of text blocks
        
        Args:
            text_blocks: List of raw text strings
            metadata: Optional metadata (source_id, content_type, etc.)
            
        Returns:
            Dict with cleaned_blocks, status, errors, warnings
        """
        results = []
        errors = []
        warnings = []
        
        if not text_blocks:
            return {
                'ok': False,
                'cleaned_blocks': [],
                'errors': ['No input text blocks provided'],
                'warnings': []
            }
        
        for idx, text in enumerate(text_blocks):
            try:
                block_id = f"{metadata.get('source_id', 'unknown')}_{idx}" if metadata else f"block_{idx}"
                result = self._sanitize_single_block(text, block_id)
                
                if result.cleaned_text.strip():
                    results.append(result)
                else:
                    warnings.append(f"Block {block_id}: Empty after sanitization")
                    
            except Exception as e:
                error_msg = f"Block {idx} sanitization failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        return {
            'ok': len(results) > 0 and len(errors) == 0,
            'cleaned_blocks': [self._result_to_dict(r) for r in results],
            'errors': errors,
            'warnings': warnings
        }
    
    def _sanitize_single_block(self, text: str, block_id: str) -> SanitizationResult:
        """Sanitize a single text block through the full pipeline"""
        
        # Calculate original hash for audit trail
        original_hash = hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()
        
        warnings = []
        redacted_entities = []
        
        # Step 1: Decode and normalize Unicode
        text = self._normalize_unicode(text)
        
        # Step 2: Check for abusive language (REQUIREMENT 1)
        if self.config.reject_abusive_words:
            has_abuse, abuse_warnings = self._check_abusive_content(text)
            if has_abuse:
                warnings.extend(abuse_warnings)
                text = self._redact_abusive_words(text)
        
        # Step 3: Check for non-Azure cloud mentions (REQUIREMENT 2)
        if self.config.azure_only_policy:
            has_non_azure, cloud_warnings = self._check_non_azure_clouds(text)
            if has_non_azure:
                warnings.extend(cloud_warnings)
                text = self._redact_non_azure_mentions(text)
        
        # Step 4: Strip HTML and normalize whitespace
        text = self._strip_html_and_normalize(text)
        
        # Step 5: Check for prompt injection attempts
        injection_found, injection_warnings = self._check_prompt_injection(text)
        if injection_found:
            warnings.extend(injection_warnings)
            text = self._neutralize_injections(text)
        
        # Step 6: PII detection and redaction
        if self.config.pii_redaction:
            text, pii_entities = self._redact_pii(text)
            redacted_entities.extend(pii_entities)
        
        # Step 7: Strict character policy (REQUIREMENT 3)
        if self.config.strict_character_policy:
            text, char_warnings = self._enforce_character_policy(text)
            warnings.extend(char_warnings)
        
        # Step 8: Control identifier canonicalization
        canonical_matches = self._match_nist_controls(text)
        
        # Step 9: Token estimation and truncation
        token_est = self._estimate_tokens(text)
        if token_est > self.config.max_tokens:
            text = self._truncate_with_context(text, self.config.max_tokens)
            warnings.append(f"Truncated from ~{token_est} to {self.config.max_tokens} tokens")
            token_est = self.config.max_tokens
        
        # Step 10: Final cleanup
        text = text.strip()
        
        return SanitizationResult(
            id=block_id,
            original_hash=original_hash,
            cleaned_text=text,
            length_chars=len(text),
            length_tokens_est=token_est,
            redacted_entities=redacted_entities,
            warnings=warnings,
            canonical_control_matches=canonical_matches,
            confidence_score=self._calculate_confidence(warnings, redacted_entities)
        )
    
    def _normalize_unicode(self, text: str) -> str:
        """Normalize Unicode to NFKC form"""
        try:
            return unicodedata.normalize('NFKC', text)
        except Exception as e:
            logger.warning(f"Unicode normalization failed: {e}")
            return text
    
    def _check_abusive_content(self, text: str) -> Tuple[bool, List[str]]:
        """Check for abusive/offensive language"""
        text_lower = text.lower()
        words_lower = re.findall(r'\b\w+\b', text_lower)
        
        found_words = [word for word in words_lower if word in self.ABUSIVE_WORDS]
        
        if found_words:
            warnings = [f"ABUSE_DETECTED: Found abusive words: {', '.join(set(found_words))}"]
            return True, warnings
        
        return False, []
    
    def _redact_abusive_words(self, text: str) -> str:
        """Replace abusive words with [REDACTED_ABUSE]"""
        for word in self.ABUSIVE_WORDS:
            # Case-insensitive word boundary replacement
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            text = pattern.sub('[REDACTED_ABUSE]', text)
        return text
    
    def _check_non_azure_clouds(self, text: str) -> Tuple[bool, List[str]]:
        """Check for mentions of non-Azure cloud providers"""
        text_lower = text.lower()
        
        found_clouds = [cloud for cloud in self.NON_AZURE_CLOUDS if cloud in text_lower]
        
        if found_clouds:
            warnings = [f"NON_AZURE_CLOUD_DETECTED: Found references to: {', '.join(set(found_clouds))}"]
            return True, warnings
        
        return False, []
    
    def _redact_non_azure_mentions(self, text: str) -> str:
        """Replace non-Azure cloud mentions with [NON_AZURE_CLOUD]"""
        for cloud in self.NON_AZURE_CLOUDS:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(cloud), re.IGNORECASE)
            text = pattern.sub('[NON_AZURE_CLOUD]', text)
        return text
    
    def _strip_html_and_normalize(self, text: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    def _check_prompt_injection(self, text: str) -> Tuple[bool, List[str]]:
        """Check for prompt injection patterns"""
        warnings = []
        found = False
        
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                warnings.append(f"INJECTION_DETECTED: Suspicious prompt injection pattern found")
                found = True
                break
        
        return found, warnings
    
    def _neutralize_injections(self, text: str) -> str:
        """Remove or neutralize prompt injection attempts"""
        for pattern in self.INJECTION_PATTERNS:
            text = re.sub(pattern, '[REMOVED_INSTRUCTION]', text, flags=re.IGNORECASE)
        return text
    
    def _redact_pii(self, text: str) -> Tuple[str, List[Dict]]:
        """Detect and redact PII"""
        entities = []
        
        # Email
        for match in self.EMAIL_PATTERN.finditer(text):
            entities.append({'type': 'email', 'value': match.group()})
        text = self.EMAIL_PATTERN.sub('[EMAIL]', text)
        
        # Phone
        for match in self.PHONE_PATTERN.finditer(text):
            entities.append({'type': 'phone', 'value': match.group()})
        text = self.PHONE_PATTERN.sub('[PHONE]', text)
        
        # SSN
        for match in self.SSN_PATTERN.finditer(text):
            entities.append({'type': 'ssn', 'value': match.group()})
        text = self.SSN_PATTERN.sub('[SSN]', text)
        
        # UUID
        for match in self.UUID_PATTERN.finditer(text):
            entities.append({'type': 'uuid', 'value': match.group()})
        text = self.UUID_PATTERN.sub('[UUID]', text)
        
        # IP Address
        for match in self.IP_PATTERN.finditer(text):
            entities.append({'type': 'ip', 'value': match.group()})
        text = self.IP_PATTERN.sub('[IP_ADDRESS]', text)
        
        # API Keys
        for match in self.API_KEY_PATTERN.finditer(text):
            entities.append({'type': 'api_key', 'value': match.group()})
        text = self.API_KEY_PATTERN.sub('[API_KEY]', text)
        
        return text, entities
    
    def _enforce_character_policy(self, text: str) -> Tuple[str, List[str]]:
        """
        Enforce strict character policy: only letters, numbers, and allowed special chars
        Allowed: space, comma, fullstop, newline, tab, hyphen, underscore, colon, slash, parentheses
        """
        warnings = []
        
        # Find all disallowed characters
        allowed_pattern = re.compile(r'^[a-zA-Z0-9\s,.\n\r\t\-_:/()]+$')
        
        if not allowed_pattern.match(text):
            # Count disallowed characters
            disallowed = set()
            for char in text:
                if char not in self.config.allowed_special_chars and not char.isalnum():
                    disallowed.add(repr(char))
            
            if disallowed:
                warnings.append(f"SPECIAL_CHARS_REMOVED: Removed {len(disallowed)} types of disallowed characters")
            
            # Remove disallowed characters
            cleaned_chars = []
            for char in text:
                if char.isalnum() or char in self.config.allowed_special_chars:
                    cleaned_chars.append(char)
            
            text = ''.join(cleaned_chars)
        
        return text, warnings
    
    def _match_nist_controls(self, text: str) -> List[Dict]:
        """Fuzzy match NIST CSF control references"""
        matches = []
        text_lower = text.lower()
        
        for control_id, keywords in self.NIST_CONTROL_VOCAB.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Simple confidence: exact match = 0.95, else 0.80
                    confidence = 0.95 if keyword in text_lower else 0.80
                    
                    matches.append({
                        'control_id': control_id,
                        'matched_phrase': keyword,
                        'confidence': confidence
                    })
        
        # Deduplicate by control_id, keep highest confidence
        unique_matches = {}
        for match in matches:
            cid = match['control_id']
            if cid not in unique_matches or match['confidence'] > unique_matches[cid]['confidence']:
                unique_matches[cid] = match
        
        return list(unique_matches.values())
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough heuristic: chars/4)"""
        return max(1, len(text) // 4)
    
    def _truncate_with_context(self, text: str, max_tokens: int) -> str:
        """Truncate text to max tokens while preserving context"""
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        # Truncate at sentence boundary if possible
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        
        if last_period > max_chars * 0.8:  # Within last 20%
            return truncated[:last_period + 1] + " [TRUNCATED]"
        
        return truncated + "... [TRUNCATED]"
    
    def _calculate_confidence(self, warnings: List[str], redacted_entities: List[Dict]) -> float:
        """Calculate overall confidence score based on warnings and redactions"""
        base_confidence = 1.0
        
        # Reduce confidence for each warning category (increased penalties)
        for warning in warnings:
            if 'ABUSE' in warning:
                base_confidence -= 0.50  # Strong penalty for abusive content (was 0.15)
            elif 'NON_AZURE' in warning:
                base_confidence -= 0.40  # Strong penalty for non-Azure (was 0.10)
            elif 'INJECTION' in warning:
                base_confidence -= 0.30  # Strong penalty for injection (was 0.20)
            elif 'SPECIAL_CHARS' in warning:
                base_confidence -= 0.10  # Moderate penalty for special chars (was 0.05)
        
        # Reduce confidence for PII redactions
        if len(redacted_entities) > 0:
            base_confidence -= 0.05 * min(len(redacted_entities), 5)
        
        return max(0.0, min(1.0, base_confidence))
    
    def _result_to_dict(self, result: SanitizationResult) -> Dict:
        """Convert SanitizationResult to dictionary"""
        return {
            'id': result.id,
            'original_hash': result.original_hash,
            'cleaned_text': result.cleaned_text,
            'length_chars': result.length_chars,
            'length_tokens_est': result.length_tokens_est,
            'redacted_entities': result.redacted_entities,
            'warnings': result.warnings,
            'canonical_control_matches': result.canonical_control_matches,
            'confidence_score': result.confidence_score
        }


# Convenience function for quick sanitization
def sanitize_input(text: str, config: Optional[SanitizationConfig] = None) -> Dict:
    """
    Quick sanitization of a single text input
    
    Args:
        text: Input text to sanitize
        config: Optional configuration
        
    Returns:
        Sanitization result dictionary
    """
    sanitizer = InputSanitizer(config)
    result = sanitizer.sanitize_batch([text], metadata={'source_id': 'quick_sanitize'})
    
    if result['ok'] and result['cleaned_blocks']:
        return result['cleaned_blocks'][0]
    
    return {
        'cleaned_text': '',
        'errors': result.get('errors', []),
        'warnings': result.get('warnings', [])
    }
