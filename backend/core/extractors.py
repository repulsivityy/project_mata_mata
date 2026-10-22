import ipaddress
import re
import urllib.parse
from typing import List, Dict

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
}
BLOCKED_SUFFIXES = (".internal", ".local", ".localhost", ".home.arpa")


def is_safe_public_host(hostname: str) -> bool:
    """Returns True unless hostname is an internal/metadata name or a literal private/loopback/link-local IP."""
    if not hostname:
        return False
    host = hostname.strip().lower().rstrip(".")
    if not host or host in BLOCKED_HOSTNAMES or host.endswith(BLOCKED_SUFFIXES):
        return False

    try:
        ip_obj = ipaddress.ip_address(host)
        return ip_obj.is_global and not (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        # Not a literal IP (e.g. a standard domain name) -> allow without DNS lookup
        return True


def is_safe_http_url(url: str) -> bool:
    """Validates that a URL uses http/https and does not target a literal internal/private host."""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme.lower() not in ("http", "https"):
            return False
        return is_safe_public_host(parsed.hostname or "")
    except Exception:
        return False


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
        # Reject explicit non-http(s) schemes in input text
        scheme_match = re.match(r'^\s*([a-zA-Z][a-zA-Z0-9+.-]*):', text)
        if scheme_match and scheme_match.group(1).lower() not in ('http', 'https'):
            return []

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
                if not is_safe_http_url(value):
                    continue
            else:
                item_type = 'domain'
                value = candidate
                if not is_safe_public_host(value):
                    continue
            
            item_tuple = (item_type, value)
            if item_tuple not in seen:
                final_results.append({'type': item_type, 'value': value})
                seen.add(item_tuple)
                
        for ip in standalone_ips:
            if ip not in seen:
                final_results.append({'type': 'ip_address', 'value': ip})
                seen.add(ip)

        return final_results
