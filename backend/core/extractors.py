import re
from typing import List, Dict

class URLExtractor:
    """Extracts and classifies URLs, Domains, and IP Addresses from text."""
    LINK_REGEX = re.compile(
        r'((?:https?://)?'
        r'((?:(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,24})|'
        r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))'
        r'(?::\d{1,5})?'
        r'(?:[/?#][^\s]*)?)',
        re.IGNORECASE
    )
    STANDALONE_IP_REGEX = re.compile(
        r'\b((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b'
    )

    @staticmethod
    def extract_urls_and_domains(text: str) -> List[Dict[str, str]]:
        candidates = URLExtractor.LINK_REGEX.findall(text)
        standalone_ips = set(URLExtractor.STANDALONE_IP_REGEX.findall(text))
        
        final_results = []
        seen = set()

        for candidate_tuple in candidates:
            candidate = candidate_tuple[0]
            
            if candidate in standalone_ips and "://" not in candidate and "/" not in candidate:
                final_results.append({'type': 'ip_address', 'value': candidate})
                seen.add(candidate)
                continue

            if "://" in candidate or "/" in candidate or (":" in candidate and "://" not in candidate):
                item_type = 'url'
                value = 'http://' + candidate if not candidate.startswith('http') else candidate
            else:
                item_type = 'domain'
                value = candidate
            
            item_tuple = (item_type, value)
            if item_tuple not in seen:
                final_results.append({'type': item_type, 'value': value})
                seen.add(item_tuple)
                
        for ip in standalone_ips:
            if ip not in seen:
                final_results.append({'type': 'ip_address', 'value': ip})
                seen.add(ip)

        return final_results
