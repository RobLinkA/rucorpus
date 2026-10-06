"""Check tracked publication files; a guardrail, not a general secret detector."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
issues = []
private_key = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')
github_token = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b')
banned_dirs = {'data', 'media', 'recovery', 'backups', '.venv', 'node_modules', 'dist',
               '__pycache__', 'staticfiles'}
banned_suffixes = ('.pem', '.key', '.p12', '.pfx', '.sql', '.dump', '.xlsx', '.xls',
                   '.csv', '.jsonl', '.db', '.tar', '.tar.gz', '.zip')
allowed_json = {'frontend/package.json', 'frontend/package-lock.json',
                'frontend/tsconfig.json', 'frontend/tsconfig.app.json', 'frontend/tsconfig.node.json'}
for name in filter(None, paths):
    path = PurePosixPath(name)
    if (set(path.parts) & banned_dirs or '.sqlite3' in name
            or name.endswith(banned_suffixes)
            or path.name.startswith('.env') and path.name != '.env.example'
            or path.suffix == '.json' and name not in allowed_json):
        issues.append(name + ': runtime/data/secret file')
    content = (root / name).read_text(encoding='utf-8', errors='replace')
    if private_key.search(content) or github_token.search(content):
        issues.append(name + ': credential pattern')
if issues:
    print('\n'.join(issues))
    sys.exit(1)
print(f'Source boundary passed: {len(list(filter(None, paths)))} tracked files.')
