#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
DarkMailHunter v2.0 - Email Password Finder & Hash Cracker
Fetches ACTUAL leaked passwords from BreachDirectory
"""

import os
import sys
import gzip
import json
import shutil
import hashlib
import requests

# ============================================================
# 1. Colors & Banner
# ============================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def banner():
    print(f"""
{Colors.RED}{Colors.BOLD}    ╔═══════════════════════════════════════════════╗
    ║  ██████╗  █████╗ ██████╗ ██╗  ██╗██╗  ██╗   ║
    ║  ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██║  ██║   ║
    ║  ██║  ██║███████║██████╔╝█████╔╝ ███████║   ║
    ║  ██║  ██║██╔══██║██╔══██╗██╔═██╗ ██╔══██║   ║
    ║  ██████╔╝██║  ██║██║  ██║██║  ██╗██║  ██║   ║
    ║  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ║
    ╚═══════════════════════════════════════════════╝
{Colors.END}
{Colors.CYAN}{Colors.BOLD}    DarkMailHunter v2.0 - Password Finder{Colors.END}
{Colors.YELLOW}    [+] Fetch ACTUAL leaked passwords{Colors.END}
{Colors.YELLOW}    [+] Hash Cracking included{Colors.END}
    """)

# ============================================================
# 2. Utility Functions
# ============================================================

def check_internet():
    try:
        requests.get("https://api.github.com", timeout=5)
        return True
    except:
        return False

def download_rockyou():
    print(f"{Colors.YELLOW}[!] Downloading RockYou wordlist (~150MB)...{Colors.END}")
    try:
        url = "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt.gz"
        r = requests.get(url, stream=True, timeout=60)
        os.makedirs("wordlists", exist_ok=True)
        with open("wordlists/rockyou.txt.gz", "wb") as f:
            f.write(r.content)
        with gzip.open("wordlists/rockyou.txt.gz", "rb") as f_in:
            with open("wordlists/rockyou.txt", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove("wordlists/rockyou.txt.gz")
        print(f"{Colors.GREEN}[+] Download complete{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}[-] Download failed: {e}{Colors.END}")
        return False

def save_results(email, found_passwords, sources):
    os.makedirs("output", exist_ok=True)
    with open("output/results.txt", "a", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write(f"Email: {email}\n")
        if found_passwords:
            f.write(f"[+] PASSWORDS FOUND ({len(found_passwords)}):\n")
            for pwd in found_passwords:
                f.write(f"    -> {pwd}\n")
        else:
            f.write("[-] No passwords found in breach databases.\n")
        if sources:
            f.write(f"Breach Sources: {len(sources)}\n")
            for src in sources:
                f.write(f"  - {src}\n")
        f.write("="*60 + "\n\n")

# ============================================================
# 3. Core Search - FETCH PASSWORDS
# ============================================================

def search_breachdirectory(email):
    """
    Fetch actual leaked passwords from BreachDirectory API
    Returns: (list of passwords, list of sources)
    """
    try:
        url = f"https://breachdirectory.org/api?email={email}"
        headers = {"User-Agent": "DarkMailHunter/2.0"}
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code != 200:
            return [], []
        
        try:
            data = r.json()
        except json.JSONDecodeError:
            return [], []
        
        if not isinstance(data, dict):
            return [], []
        
        results = data.get('result')
        if not isinstance(results, list):
            return [], []
        
        passwords = []
        sources = []
        
        for entry in results:
            if not isinstance(entry, dict):
                continue
            
            # Extract password
            pwd = entry.get('password')
            if pwd and isinstance(pwd, str) and pwd.strip():
                passwords.append(pwd.strip())
            
            # Extract source
            src = entry.get('source') or entry.get('website')
            if src and isinstance(src, str) and src.strip():
                sources.append(src.strip())
        
        # Remove duplicates while preserving order
        seen_pwd = set()
        unique_passwords = []
        for p in passwords:
            if p not in seen_pwd:
                seen_pwd.add(p)
                unique_passwords.append(p)
        
        seen_src = set()
        unique_sources = []
        for s in sources:
            if s not in seen_src:
                seen_src.add(s)
                unique_sources.append(s)
        
        return unique_passwords, unique_sources
        
    except Exception as e:
        # Silent fail; return empty
        return [], []

def search_hibp_breaches(email):
    """Get breach names from HIBP for context"""
    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        headers = {"User-Agent": "DarkMailHunter/2.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return [b.get('Name', 'Unknown') for b in data if isinstance(b, dict)]
        return []
    except:
        return []

# ============================================================
# 4. Hash Cracking (Offline)
# ============================================================

def crack_hash(hash_value):
    if not os.path.exists("wordlists/rockyou.txt"):
        if not download_rockyou():
            return None

    if len(hash_value) == 32:
        hash_type = "MD5"
    elif len(hash_value) == 40:
        hash_type = "SHA1"
    elif len(hash_value) == 64:
        hash_type = "SHA256"
    else:
        hash_type = "Unknown"

    print(f"{Colors.BLUE}[*] Cracking {hash_type} hash...{Colors.END}")

    try:
        with open("wordlists/rockyou.txt", "r", encoding="latin-1", errors="ignore") as f:
            for word in f:
                word = word.strip()
                if not word:
                    continue
                if hash_type == "MD5" and hashlib.md5(word.encode()).hexdigest() == hash_value:
                    return word
                if hash_type == "SHA1" and hashlib.sha1(word.encode()).hexdigest() == hash_value:
                    return word
                if hash_type == "SHA256" and hashlib.sha256(word.encode()).hexdigest() == hash_value:
                    return word
                if hash_type == "Unknown":
                    if hashlib.md5(word.encode()).hexdigest() == hash_value:
                        return word
                    if hashlib.sha1(word.encode()).hexdigest() == hash_value:
                        return word
                    if hashlib.sha256(word.encode()).hexdigest() == hash_value:
                        return word
        return None
    except Exception as e:
        print(f"{Colors.RED}[-] Error cracking: {e}{Colors.END}")
        return None

# ============================================================
# 5. Interactive Mode
# ============================================================

def interactive_mode():
    while True:
        print(f"\n{Colors.MAGENTA}┌─[DarkMailHunter]{Colors.END}")
        email = input(f"{Colors.MAGENTA}└──> Target Email: {Colors.END}")

        if not email or email.lower() in ['exit', 'quit']:
            print(f"{Colors.YELLOW}[!] Exiting...{Colors.END}")
            break

        if "@" not in email:
            print(f"{Colors.RED}[-] Invalid email{Colors.END}")
            continue

        print(f"{Colors.BLUE}[*] Searching for passwords for {email}...{Colors.END}")
        
        # Fetch passwords
        passwords, sources = search_breachdirectory(email)
        hibp_sources = search_hibp_breaches(email)  # For context only
        
        # Combine sources
        all_sources = list(set(sources + hibp_sources))
        
        # Display Results
        print(f"\n{Colors.GREEN}{Colors.BOLD}═══ RESULTS ═══{Colors.END}")
        
        if passwords:
            print(f"{Colors.GREEN}{Colors.BOLD}[+] PASSWORDS FOUND ({len(passwords)}):{Colors.END}")
            for idx, pwd in enumerate(passwords, 1):
                print(f"{Colors.RED}{Colors.BOLD}    {idx}. {pwd}{Colors.END}")
            
            save_results(email, passwords, all_sources)
            print(f"{Colors.GREEN}[+] Saved to output/results.txt{Colors.END}")
        else:
            print(f"{Colors.YELLOW}[-] No passwords found in breach databases.{Colors.END}")
            save_results(email, [], all_sources)

        if all_sources:
            print(f"\n{Colors.BLUE}[*] Breach Sources:{Colors.END}")
            for src in all_sources[:5]:
                print(f"    - {src}")
            if len(all_sources) > 5:
                print(f"    - ... and {len(all_sources)-5} more")

        # Optional Hash Cracking
        print(f"\n{Colors.MAGENTA}[?] Crack a hash offline? (y/n){Colors.END}")
        if input("> ").lower() == 'y':
            h = input(f"{Colors.CYAN}[?] Enter hash (MD5/SHA1/SHA256): {Colors.END}")
            if h:
                pwd = crack_hash(h)
                if pwd:
                    print(f"{Colors.GREEN}[+] Password: {pwd}{Colors.END}")
                else:
                    print(f"{Colors.RED}[-] Not found in wordlist{Colors.END}")

# ============================================================
# 6. Quick Single Search
# ============================================================

def quick_search():
    email = input(f"{Colors.CYAN}[?] Target Email: {Colors.END}")
    if not email or "@" not in email:
        print(f"{Colors.RED}[-] Invalid email{Colors.END}")
        return
    
    print(f"{Colors.BLUE}[*] Searching...{Colors.END}")
    passwords, sources = search_breachdirectory(email)
    hibp_sources = search_hibp_breaches(email)
    all_sources = list(set(sources + hibp_sources))
    
    if passwords:
        print(f"\n{Colors.GREEN}{Colors.BOLD}[+] PASSWORDS ({len(passwords)}):{Colors.END}")
        for pwd in passwords:
            print(f"    {Colors.RED}{pwd}{Colors.END}")
        save_results(email, passwords, all_sources)
        print(f"{Colors.GREEN}[+] Saved to output/results.txt{Colors.END}")
    else:
        print(f"{Colors.YELLOW}[-] No passwords found.{Colors.END}")

# ============================================================
# 7. Main Function
# ============================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner()

    if not check_internet():
        print(f"{Colors.RED}[-] No internet connection{Colors.END}")
        print(f"{Colors.YELLOW}[!] Only offline hash cracking will work.{Colors.END}")

    print(f"\n{Colors.CYAN}[?] Select mode:{Colors.END}")
    print(f"    1. Interactive Mode (Search passwords + Crack hashes)")
    print(f"    2. Quick Password Search (Single email)")
    print(f"    3. Download RockYou wordlist (for hash cracking)")
    print(f"    4. Exit")

    choice = input(f"{Colors.MAGENTA}└──> {Colors.END}")

    if choice == '1':
        interactive_mode()
    elif choice == '2':
        quick_search()
    elif choice == '3':
        download_rockyou()
    elif choice == '4':
        print(f"{Colors.YELLOW}[!] Goodbye{Colors.END}")
        sys.exit(0)
    else:
        print(f"{Colors.RED}[-] Invalid choice{Colors.END}")

# ============================================================
# 8. Entry Point
# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}[!] Interrupted{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"{Colors.RED}[-] Fatal Error: {e}{Colors.END}")
        sys.exit(1)