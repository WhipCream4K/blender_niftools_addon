"""
License verification system using a stable machine install ID whitelist on GitHub.

Primary identifier: OS install ID (stays until OS reinstall)
  - Windows: HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid
  - Linux:   /etc/machine-id (or /var/lib/dbus/machine-id)
  - macOS:   IOPlatformUUID

Legacy fallback: MAC via uuid.getnode() (unstable; kept so old whitelist rows still work).
"""

import hashlib
import json
import os
import platform
import re
import subprocess
import urllib.error
import urllib.request
import uuid

from io_scene_niftools.utils.logging import NifLog

# Configuration
GITHUB_WHITELIST_URL = "https://raw.githubusercontent.com/WhipCream4K/license_me/main/whitelist.txt"
# For private repos, use a token:
# GITHUB_TOKEN = "ghp_YOUR_PERSONAL_ACCESS_TOKEN"  # Keep this secret!

# Cache license check result to avoid repeated network calls
_license_valid = None
_license_checked = False


def _hash_identifier(raw):
    """SHA256 of a normalized raw identifier (uppercase hex)."""
    if not raw:
        return None
    normalized = str(raw).strip().upper()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest().upper()


def get_install_id():
    """
    OS install / machine identity that stays stable through NIC / VPN / Wi-Fi
    MAC changes. Typically only changes after OS reinstall (or motherboard
    swap on macOS, where the platform UUID is hardware-bound).

    Returns:
        str | None: Raw install id string, or None if unavailable.
    """
    system = platform.system()

    try:
        if system == "Windows":
            import winreg

            # KEY_WOW64_64KEY: always read the 64-bit view (Blender is 64-bit;
            # avoids empty/missing key under WOW64 redirection on some setups).
            access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                access,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
            if value:
                return str(value).strip()

        elif system == "Linux":
            for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as fh:
                        value = fh.read().strip()
                    if value:
                        return value

        elif system == "Darwin":
            # Hardware/platform UUID; stable for the Mac, not just the install.
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                text=True,
                timeout=5,
            )
            match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            if match:
                return match.group(1).strip()

    except Exception as e:
        NifLog.warn(f"Could not retrieve install id ({system}): {e}")

    return None


def get_install_id_hash():
    """SHA256 hash of the OS install id (preferred license identifier)."""
    return _hash_identifier(get_install_id())


def get_mac_address():
    """
    Legacy: MAC from uuid.getnode() (can change with VPN / Wi-Fi privacy / adapters).
    Kept for fallback checks against old whitelist entries.
    """
    try:
        mac = uuid.getnode()
        mac_str = ":".join(
            ["{:02x}".format((mac >> elements) & 0xFF) for elements in range(0, 8 * 6, 8)][::-1]
        )
        return mac_str.upper()
    except Exception as e:
        NifLog.warn(f"Could not retrieve MAC address: {e}")
        return None


def get_mac_hash():
    """Legacy: SHA256 of MAC address (uppercase hex)."""
    return _hash_identifier(get_mac_address())


def fetch_whitelist(use_hash=True):
    """
    Fetch the whitelist from GitHub.

    Args:
        use_hash: Unused (kept for call-site compatibility). Whitelist entries
                  are hashed identifiers (install id and/or legacy MAC).

    Returns:
        set: Set of whitelisted identifier hashes (uppercase).
    """
    try:
        req = urllib.request.Request(GITHUB_WHITELIST_URL)
        # req.add_header('Authorization', f'token {GITHUB_TOKEN}')

        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode("utf-8")

            whitelist = set()
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "#" in line:
                    line = line.split("#")[0].strip()
                if line:
                    whitelist.add(line.upper())

            return whitelist

    except urllib.error.URLError as e:
        NifLog.warn(f"Could not fetch license whitelist: {e}")
        return set()  # Fail closed
    except Exception as e:
        NifLog.warn(f"Error checking license: {e}")
        return set()


def check_license(use_hash=True):
    """
    Check if the current machine is licensed to use the addon.

    Prefer stable install-id hash; fall back to legacy MAC hash so existing
    whitelist rows keep working until customers re-register.

    Args:
        use_hash: If True (default), compare hashed identifiers.
                  If False, compare raw install id / MAC (not used for whitelist).

    Returns:
        bool: True if licensed, False otherwise
    """
    global _license_valid, _license_checked

    if _license_checked:
        return _license_valid

    if use_hash:
        primary = get_install_id_hash()
        legacy = get_mac_hash()
        candidates = [c for c in (primary, legacy) if c]
    else:
        primary = get_install_id()
        legacy = get_mac_address()
        candidates = [c for c in (primary, legacy) if c]

    if not candidates:
        NifLog.error("Could not retrieve machine identifier for license check")
        _license_valid = False
        _license_checked = True
        return False

    whitelist = fetch_whitelist(use_hash=use_hash)

    matched = None
    for ident in candidates:
        if ident.upper() in whitelist:
            matched = ident
            break

    _license_valid = matched is not None
    _license_checked = True

    if _license_valid:
        NifLog.info("License check passed")
    else:
        # Always show the stable id customers should send you going forward
        show = primary or candidates[0]
        NifLog.error("License check failed: Machine not authorized")
        NifLog.error(f"Your identifier: {show}")
        NifLog.error("Please contact the developer to obtain a license")

    return _license_valid


def get_machine_identifier(use_hash=True):
    """
    Identifier for license registration (what customers send you).

    Uses the stable OS install id (not MAC).

    Args:
        use_hash: If True, return SHA256 hash (recommended for whitelist).

    Returns:
        str | None: Machine identifier
    """
    if use_hash:
        return get_install_id_hash()
    return get_install_id()


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
            return {"CANCELLED"}
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
                "identifier": "HASHED_INSTALL_ID",
                "expires": "2026-12-31",
                "features": ["export", "import"],
                "note": "Customer Name"
            }
        ]
    }
    """
    try:
        json_url = GITHUB_WHITELIST_URL.replace("whitelist.txt", "licenses.json")

        req = urllib.request.Request(json_url)
        with urllib.request.urlopen(req, timeout=5) as response:
            content = response.read().decode("utf-8")
            return json.loads(content)
    except Exception as e:
        NifLog.warn(f"Could not fetch license info: {e}")
        return None


def check_license_advanced():
    """
    Advanced license check with expiration dates and feature flags.
    """
    from datetime import datetime

    identifier = get_install_id_hash() or get_mac_hash()
    if not identifier:
        return False

    license_data = fetch_license_info()
    if not license_data or "licenses" not in license_data:
        return False

    for lic in license_data["licenses"]:
        if lic.get("identifier", "").upper() == identifier.upper():
            if "expires" in lic:
                expiry = datetime.strptime(lic["expires"], "%Y-%m-%d")
                if datetime.now() > expiry:
                    NifLog.error(f"License expired on {lic['expires']}")
                    return False

            NifLog.info("License check passed")
            return True

    NifLog.error("No valid license found for this machine")
    return False
