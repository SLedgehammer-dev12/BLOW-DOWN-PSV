import urllib.request
import urllib.error
import json
import os
import re
import subprocess

OWNER = "SLedgehammer-dev12"
REPO = "BLOW-DOWN-PSV"


def resolve_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token

    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            text=True,
        ).strip()
        match = re.search(r"https://([^@]+)@github\\.com/", remote_url)
        if match:
            return match.group(1)
    except Exception:
        pass

    raise RuntimeError("GitHub token bulunamadı. GITHUB_TOKEN tanımlayın veya yetkili bir origin URL kullanın.")


TOKEN = resolve_github_token()

def github_request(url, method="GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 204:
                return {}
            data = response.read()
            if data:
                return json.loads(data)
            return {}
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} for {url}")
        return None

def main():
    tags_to_delete = ["v1.1", "v1.2", "v1.2.1", "v1.2.2"]
    
    # Get all releases
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
    releases = github_request(url)
    
    if releases:
        for rel in releases:
            tag = rel['tag_name']
            if tag in tags_to_delete:
                rel_id = rel['id']
                print(f"Deleting release {tag} (ID: {rel_id})...")
                del_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{rel_id}"
                github_request(del_url, method="DELETE")
                
                print(f"Deleting tag {tag}...")
                tag_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs/tags/{tag}"
                github_request(tag_url, method="DELETE")
                print("Done.")

if __name__ == "__main__":
    main()
