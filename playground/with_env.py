"""Run a command with missing environment variables loaded from ignored .env.

Values are literal: this loader never executes shell code or expands variables.
Existing exported variables take precedence. Credentials are never printed.
"""
import os
from pathlib import Path
import sys

path=Path(__file__).resolve().parent.parent/'.env'
if path.exists():
    for line in path.read_text().splitlines():
        if '=' not in line or line.lstrip().startswith('#'): continue
        key,value=line.split('=',1)
        key=key.strip().removeprefix('export ')
        value=value.strip()
        if len(value)>1 and value[0]==value[-1] and value[0] in {'\"',"'"}: value=value[1:-1]
        if key.isidentifier(): os.environ.setdefault(key,value)
if len(sys.argv)<2:
    raise SystemExit('Usage: python3 playground/with_env.py COMMAND [ARGS...]')
os.execvp(sys.argv[1],sys.argv[1:])
