"""
HairSync GitHub Push Helper
Push Module 1 commits to https://github.com/jaseel-nm21/hairSync.git
"""

import sys
import os
import getpass
from dulwich import porcelain
from dulwich.repo import Repo

REPO_URL = "https://github.com/jaseel-nm21/hairSync.git"

def main():
    repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    repo = Repo(repo_path)
    
    print("=" * 65)
    print("HairSync - Push Module 1 to GitHub")
    print(f"Target Repository: {REPO_URL}")
    print("Commit Date      : August 15, 2026 (15/08/2026)")
    print("=" * 65)

    token = None
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        print("\nGitHub requires a Personal Access Token (PAT) for HTTPS push.")
        print("How to get a token:")
        print("  1. Go to: https://github.com/settings/tokens")
        print("  2. Click 'Generate new token (classic)'")
        print("  3. Check the 'repo' scope and click Generate.")
        print("  4. Copy and paste your token below:\n")
        try:
            token = input("Enter your GitHub Personal Access Token: ").strip()
        except EOFError:
            token = None

    if not token:
        print("[-] No token provided. Push cancelled.")
        print("\nAlternatively, you can open this HairSync folder in VS Code and click 'Publish to GitHub' or use Git for Windows.")
        sys.exit(1)

    # Format authenticated URL
    auth_url = f"https://jaseel-nm21:{token}@github.com/jaseel-nm21/hairSync.git"

    print("\n[*] Pushing 'main' branch to GitHub...")
    try:
        porcelain.push(repo_path, auth_url, 'refs/heads/main')
        print("[+] SUCCESS! Module 1 has been uploaded to GitHub!")
        print(f"[+] View your repository at: {REPO_URL}")
    except Exception as e:
        print(f"[-] Push error: {e}")
        print("\nIf the remote already has existing files (e.g. an existing README), you may need to force push or ensure the remote repo is empty.")

if __name__ == '__main__':
    main()
