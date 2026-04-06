import json
import os
import re
import subprocess
import urllib.request
import urllib.error

OWNER = "SLedgehammer-dev12"
REPO = "BLOW-DOWN-PSV"
TAG = "v2.3.1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_PATH = os.path.join(BASE_DIR, "dist", "Blowdown Studio_v2.3.1.exe")


def resolve_github_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token

    try:
        remote_url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=BASE_DIR,
            text=True,
        ).strip()
        match = re.search(r"https://([^@]+)@github\.com/", remote_url)
        if match:
            return match.group(1)
    except Exception:
        pass

    raise RuntimeError("GitHub token bulunamadı. GITHUB_TOKEN tanımlayın veya yetkili bir origin URL kullanın.")


TOKEN = resolve_github_token()

def github_request(url, data=None, method="GET", content_type="application/json"):
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": content_type
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            res_content = response.read().decode('utf-8')
            if not res_content:
                return {}
            return json.loads(res_content)
    except urllib.error.HTTPError as e:
        print(f"Error: {e.code} - {e.read().decode('utf-8')}")
        return None

def delete_release():
    print(f"Checking for existing release {TAG}...")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}"
    release = github_request(url)
    if release:
        print(f"Deleting release {release['id']}...")
        del_url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{release['id']}"
        github_request(del_url, method="DELETE")
        
        print(f"Deleting tag {TAG}...")
        tag_url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/refs/tags/{TAG}"
        github_request(tag_url, method="DELETE")

def create_release():
    print(f"Creating new release {TAG}...")
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"
    data = json.dumps({
        "tag_name": TAG,
        "name": f"Release {TAG} (Blowdown Studio)",
        "body": "Changes in this release: 1. Fixed HydDown packaging/import in the bundled executable. 2. Restored the expanded blowdown and PSV plotting set that had regressed in the first v2.3 build. 3. Published the hotfix under a new version tag so in-app update detection works correctly for existing v2.3 users.",
        "draft": False,
        "prerelease": False
    }).encode('utf-8')
    return github_request(url, data=data, method="POST")

def upload_asset(upload_url):
    print(f"Uploading {EXE_PATH}...")
    asset_name = f"Blowdown_Studio_{TAG}.exe"
    url = upload_url.split('{')[0] + f"?name={asset_name}"
    
    with open(EXE_PATH, 'rb') as f:
        data = f.read()
        
    headers = {
        "Authorization": f"token {TOKEN}",
        "Content-Type": "application/octet-stream",
        "Content-Length": str(len(data))
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print("Upload successful!")
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"Upload failed: {e.code} - {e.read().decode('utf-8')}")
        return None

if __name__ == "__main__":
    delete_release()
    release = create_release()
    if release:
        upload_asset(release['upload_url'])
    else:
        print("Failed to create release.")
