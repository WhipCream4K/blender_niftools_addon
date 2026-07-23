#!/usr/bin/env python3
"""
Helper script to get machine ID for license registration.
Run this to get the ID you need to add to the GitHub whitelist.

Uses OS install id (stable until reinstall), not MAC address.
"""

import hashlib
import os
import platform
import re
import subprocess
import sys


def get_install_id():
    """OS install / machine id — stable until reinstall (see license_check.py)."""
    system = platform.system()
    try:
        if system == "Windows":
            import winreg

            access = winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                access,
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip() if value else None

        if system == "Linux":
            for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8") as fh:
                        value = fh.read().strip()
                    if value:
                        return value
            return None

        if system == "Darwin":
            out = subprocess.check_output(
                ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"],
                text=True,
                timeout=5,
            )
            match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            return match.group(1).strip() if match else None

    except Exception as e:
        print(f"Error getting install id: {e}")
    return None


def hash_id(raw):
    if not raw:
        return None
    return hashlib.sha256(raw.strip().upper().encode("utf-8")).hexdigest().upper()


def main():
    print("=" * 70)
    print("BLENDER NIFTOOLS ADDON - MACHINE ID GENERATOR")
    print("=" * 70)
    print()

    install_id = get_install_id()
    install_hash = hash_id(install_id)

    if not install_id or not install_hash:
        print("Could not retrieve machine install id")
        sys.exit(1)

    print("MACHINE INFORMATION")
    print("-" * 70)
    print(f"OS:           {platform.system()} {platform.release()}")
    print(f"Install ID:   {install_id}")
    print(f"Hashed ID:    {install_hash}")
    print()
    print("(This id stays the same until OS reinstall / new machine.)")
    print()

    print("=" * 70)
    print("ADD THIS TO YOUR GITHUB WHITELIST")
    print("=" * 70)
    print()
    try:
        description = input("Enter description (e.g., Customer Name): ")
    except EOFError:
        description = "customer"
    print()
    print("Copy this line to whitelist.txt:")
    print()
    print(f"{install_hash}  # {description}")
    print()

    print("=" * 70)
    print("INSTRUCTIONS")
    print("=" * 70)
    print()
    print("1. Go to your GitHub repository")
    print("2. Open whitelist.txt")
    print("3. Click 'Edit' (pencil icon)")
    print("4. Paste the line above")
    print("5. Click 'Commit changes'")
    print()
    print("Your addon will work after the whitelist is updated!")
    print()


if __name__ == "__main__":
    main()
