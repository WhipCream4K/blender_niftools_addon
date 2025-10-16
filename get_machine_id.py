#!/usr/bin/env python3
"""
Helper script to get machine ID for license registration.
Run this to get the ID you need to add to the GitHub whitelist.
"""

import hashlib
import uuid
import sys

def get_mac_address():
    """Get the MAC address of the primary network interface."""
    try:
        mac = uuid.getnode()
        mac_str = ':'.join(['{:02x}'.format((mac >> elements) & 0xff) 
                           for elements in range(0, 8*6, 8)][::-1])
        return mac_str.upper()
    except Exception as e:
        print(f"Error getting MAC address: {e}")
        return None

def get_mac_hash():
    """Get SHA256 hash of MAC address."""
    mac = get_mac_address()
    if mac:
        return hashlib.sha256(mac.encode()).hexdigest()
    return None

def main():
    print("=" * 70)
    print("BLENDER NIFTOOLS ADDON - MACHINE ID GENERATOR")
    print("=" * 70)
    print()
    
    mac = get_mac_address()
    mac_hash = get_mac_hash()
    
    if not mac or not mac_hash:
        print("❌ Could not retrieve machine information")
        sys.exit(1)
    
    print("📋 MACHINE INFORMATION")
    print("-" * 70)
    print(f"MAC Address:  {mac}")
    print(f"Hashed ID:    {mac_hash}")
    print()
    
    print("=" * 70)
    print("📝 ADD THIS TO YOUR GITHUB WHITELIST")
    print("=" * 70)
    print()
    print("Copy this line to whitelist.txt:")
    print()
    print(f"{mac_hash}  # {input('Enter description (e.g., Your Name): ')}")
    print()
    
    print("=" * 70)
    print("📖 INSTRUCTIONS")
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
