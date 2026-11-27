"""Push the CarePulse Hospital project to GitHub using the provided PAT.
This script:
1. Checks if the repo exists; if not, creates it.
2. Creates blobs for each file we want to push (skipping virtual env, __pycache__, instance folder, .git, and the SQLite DB).
3. Builds a tree, commits, and updates the main branch.
"""
import os, json, base64, sys, pathlib, urllib.request, urllib.error

# Read PAT from environment variable passed at runtime
PAT = os.getenv('GITHUB_PAT')
if not PAT:
    print('Error: GITHUB_PAT environment variable not set')
    sys.exit(1)

REPO = 'ziyangupta777/carepulsehospital'
API = 'https://api.github.com'
HEADERS = {'Authorization': f'token {PAT}', 'Accept': 'application/vnd.github+json'}

def repo_exists():
    req = urllib.request.Request(f'{API}/repos/{REPO}', headers=HEADERS, method='GET')
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise

def create_repo():
    data = json.dumps({'name': 'carepulsehospital', 'private': False}).encode()
    req = urllib.request.Request(f'{API}/user/repos', data=data, headers=HEADERS, method='POST')
    with urllib.request.urlopen(req) as resp:
        print('Repo created')

def get_ref_sha(ref='heads/main'):
    req = urllib.request.Request(f'{API}/repos/{REPO}/git/ref/{ref}', headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)['object']['sha']

def create_blob(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    data = json.dumps({'content': base64.b64encode(content).decode(), 'encoding': 'base64'}).encode()
    req = urllib.request.Request(f'{API}/repos/{REPO}/git/blobs', data=data, headers=HEADERS, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)['sha']

def create_tree(blobs, base_tree=None):
    tree = []
    for path, sha in blobs.items():
        rel_path = os.path.relpath(path, start='C:/Users/ASUS/.gemini/antigravity/scratch/carepulse-hospital')
        tree.append({'path': rel_path.replace('\\', '/'), 'mode': '100644', 'type': 'blob', 'sha': sha})
    payload = {'tree': tree}
    if base_tree:
        payload['base_tree'] = base_tree
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f'{API}/repos/{REPO}/git/trees', data=data, headers=HEADERS, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)['sha']

def create_commit(message, tree_sha, parent_sha):
    payload = json.dumps({'message': message, 'tree': tree_sha, 'parents': [parent_sha]}).encode()
    req = urllib.request.Request(f'{API}/repos/{REPO}/git/commits', data=payload, headers=HEADERS, method='POST')
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)['sha']

def update_ref(commit_sha, ref='heads/main'):
    data = json.dumps({'sha': commit_sha, 'force': True}).encode()
    req = urllib.request.Request(f'{API}/repos/{REPO}/git/refs/{ref}', data=data, headers=HEADERS, method='PATCH')
    with urllib.request.urlopen(req) as resp:
        print('Reference updated')

def main():
    if not repo_exists():
        create_repo()
    root = pathlib.Path('C:/Users/ASUS/.gemini/antigravity/scratch/carepulse-hospital')
    ignore_parts = {'.venv', '__pycache__', 'instance', '.git'}
    blobs = {}
    for path in root.rglob('*'):
        if path.is_dir():
            continue
        if any(part in path.parts for part in ignore_parts):
            continue
        if path.suffix == '.db':
            continue
        blobs[str(path)] = create_blob(str(path))
    # Get the current main commit SHA if it exists
    try:
        parent_sha = get_ref_sha('heads/main')
    except Exception:
        parent_sha = None
    tree_sha = create_tree(blobs, base_tree=parent_sha)
    commit_sha = create_commit('Initial commit from Antigravity', tree_sha, parent_sha or '')
    update_ref(commit_sha)
    print('Push complete')

if __name__ == '__main__':
    main()
