"""
License verification system using MAC address whitelist hosted on GitHub.
This module checks if the user's MAC address is authorized to use the addon.
"""

import uuid
import urllib.request
import urllib.error
import hashlib
import json
from io_scene_niftools.utils.logging import NifLog

# Configuration
GITHUB_WHITELIST_URL = "https://raw.githubusercontent.com/WhipCream4K/license_me/main/whitelist.txt"
# For private repos, use a token:
# GITHUB_TOKEN = "ghp_YOUR_PERSONAL_ACCESS_TOKEN"  # Keep this secret!

# Cache license check result to avoid repeated network calls
_license_valid = None
_license_checked = False


def get_mac_address():
    """
    Get the MAC address of the primary network interface.
    Returns a normalized MAC address string.
    """
    try:
        # Get MAC address as integer
        mac = uuid.getnode()
        
        # Convert to standard MAC format (XX:XX:XX:XX:XX:XX)
        mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                           for elements in range(0, 8*6, 8)][::-1])
        
        return mac_str.upper()
    except Exception as e:
        NifLog.warn(f"Could not retrieve MAC address: {e}")
        return None


def get_mac_hash():
    """
    Get a SHA256 hash of the MAC address for privacy.
    This way you don't store actual MAC addresses in the whitelist.
    """
    mac = get_mac_address()
    if mac:
        # Hash the MAC address (return uppercase hex for consistent comparison)
        return hashlib.sha256(mac.encode()).hexdigest().upper()
    return None


def fetch_whitelist(use_hash=True):
    """
    Fetch the whitelist from GitHub.
    
    Args:
        use_hash: If True, expect hashed MAC addresses in whitelist
    
    Returns:
        set: Set of whitelisted MAC addresses (or hashes)
    """
    try:
        # Create request
        req = urllib.request.Request(GITHUB_WHITELIST_URL)
        
        # Add authentication for private repos (optional)
        # req.add_header('Authorization', f'token {GITHUB_TOKEN}')
        
        # Set timeout
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            
            # Parse whitelist (one MAC/hash per line, ignore comments and empty lines)
            whitelist = set()
            for line in content.split('\n'):
                line = line.strip()
                # Skip empty lines and full-line comments
                if not line or line.startswith('#'):
                    continue
                
                # Remove inline comments (text after #)
                if '#' in line:
                    line = line.split('#')[0].strip()
                
                # Add the hash to whitelist (convert to uppercase for comparison)
                if line:
                    whitelist.add(line.upper())
            
            return whitelist
            
    except urllib.error.URLError as e:
        NifLog.warn(f"Could not fetch license whitelist: {e}")
        # In case of network error, you can choose to:
        # Option 1: Fail open (allow usage) - good for development
        # Option 2: Fail closed (deny usage) - more secure
        return set()  # Fail closed
    except Exception as e:
        NifLog.warn(f"Error checking license: {e}")
        return set()


def check_license(use_hash=True):
    """
    Check if the current machine is licensed to use the addon.
    
    Args:
        use_hash: If True, use hashed MAC addresses (more privacy-friendly)
    
    Returns:
        bool: True if licensed, False otherwise
    """
    global _license_valid, _license_checked
    
    # Return cached result if already checked
    if _license_checked:
        return _license_valid
    
    # Get MAC address or hash
    if use_hash:
        identifier = get_mac_hash()
    else:
        identifier = get_mac_address()
    
    if not identifier:
        NifLog.error("Could not retrieve machine identifier for license check")
        _license_valid = False
        _license_checked = True
        return False
    
    # Fetch whitelist from GitHub
    whitelist = fetch_whitelist(use_hash=use_hash)
    
    # Check if identifier is in whitelist (case-insensitive)
    ident_norm = identifier.upper()
    _license_valid = ident_norm in whitelist
    _license_checked = True
    
    if _license_valid:
        NifLog.info("License check passed")
    else:
        NifLog.error("License check failed: Machine not authorized")
        NifLog.error(f"Your identifier: {identifier}")
        NifLog.error("Please contact the developer to obtain a license")
    
    return _license_valid


def get_machine_identifier(use_hash=True):
    """
    Get the machine identifier for license registration.
    Users send this to you, and you add it to the whitelist.
    
    Args:
        use_hash: If True, return hashed MAC address
    
    Returns:
        str: Machine identifier
    """
    if use_hash:
        return get_mac_hash()
    else:
        return get_mac_address()


def require_license(func):
    """
    Decorator to require license check before executing a function.
    Use this on export/import operators.
    
    Example:
        @require_license
        def execute(self, context):
            # Your code here
    """
    from functools import wraps

    @wraps(func)
    def wrapper(self, context, *args, **kwargs):
        if not check_license():
            NifLog.error("This addon requires a valid license")
            NifLog.error("Please contact the developer")
            return {'CANCELLED'}
        return func(self, context, *args, **kwargs)

    return wrapper


# Optional: More sophisticated license info with expiration dates
def fetch_license_info():
    """
    Fetch detailed license information from GitHub (JSON format).
    This allows for expiration dates, feature flags, etc.
    
    Expected JSON format:
    {
        "licenses": [
            {
                "identifier": "HASHED_MAC_ADDRESS",
                "expires": "2026-12-31",
                "features": ["export", "import"],
                "note": "Customer Name"
            }
        ]
    }
    """
    try:
        # Use a different URL for JSON license file
        json_url = GITHUB_WHITELIST_URL.replace('whitelist.txt', 'licenses.json')
        
        req = urllib.request.Request(json_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode('utf-8')
            return json.loads(content)
    except Exception as e:
        NifLog.warn(f"Could not fetch license info: {e}")
        return None


def check_license_advanced():
    """
    Advanced license check with expiration dates and feature flags.
    """
    from datetime import datetime
    
    identifier = get_mac_hash()
    if not identifier:
        return False
    
    license_data = fetch_license_info()
    if not license_data or 'licenses' not in license_data:
        return False
    
    # Find matching license
    for lic in license_data['licenses']:
        if lic.get('identifier') == identifier:
            # Check expiration
            if 'expires' in lic:
                expiry = datetime.strptime(lic['expires'], '%Y-%m-%d')
                if datetime.now() > expiry:
                    NifLog.error(f"License expired on {lic['expires']}")
                    return False
            
            NifLog.info("License check passed")
            return True
    
    NifLog.error("No valid license found for this machine")
    return False
