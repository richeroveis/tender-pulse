#!/usr/bin/env python3
"""Deploy frontend/dist to gh-pages branch on GitHub without exposing tokens.

Enforces strict git author isolation to richeroveis <oveis.richer@gmail.com>.
"""

import base64
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist"

def main():
    load_dotenv(ROOT / ".env")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("[gh-pages] GITHUB_TOKEN missing from .env", file=sys.stderr)
        sys.exit(1)

    if not DIST.exists() or not (DIST / "index.html").exists():
        print("[gh-pages] frontend/dist/index.html not found, build frontend first!", file=sys.stderr)
        sys.exit(1)

    author_name = "richeroveis"
    author_email = "oveis.richer@gmail.com"
    auth_header = base64.b64encode(f"{author_name}:{token}".encode()).decode()

    # 1. Create a git tree directly from frontend/dist
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_NAME"] = author_name
    env["GIT_COMMITTER_EMAIL"] = author_email

    # Initialize a temporary index in memory / temp file
    temp_index = ROOT / ".git" / "temp_gh_pages_index"
    if temp_index.exists():
        temp_index.unlink()
    env["GIT_INDEX_FILE"] = str(temp_index)

    try:
        # Add all files in frontend/dist to temp index
        subprocess.run(
            ["git", "--work-tree", str(DIST), "add", "-A", "."],
            cwd=str(ROOT),
            env=env,
            check=True,
        )
        tree_sha = subprocess.check_output(
            ["git", "write-tree"],
            cwd=str(ROOT),
            env=env,
            text=True,
        ).strip()
        print(f"[gh-pages] created tree: {tree_sha}")

        commit_msg = "deploy: publish bespoke TenderPulse Civic Procurement Ledger to GitHub Pages"
        commit_sha = subprocess.check_output(
            ["git", "commit-tree", tree_sha, "-m", commit_msg],
            cwd=str(ROOT),
            env=env,
            text=True,
        ).strip()
        print(f"[gh-pages] created commit: {commit_sha}")

        # Push to origin gh-pages
        git_cmd = [
            "git",
            "-c", "credential.helper=",
            "-c", f"http.https://github.com/.extraheader=AUTHORIZATION: basic {auth_header}",
            "push", "-f", "origin", f"{commit_sha}:refs/heads/gh-pages"
        ]
        res = subprocess.run(git_cmd, cwd=str(ROOT), capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[gh-pages] push failed: {res.stderr}", file=sys.stderr)
            sys.exit(1)
        print("[gh-pages] pushed commit to refs/heads/gh-pages successfully!")

    finally:
        if temp_index.exists():
            temp_index.unlink()

    # Verify GitHub Pages URL
    target_url = "https://richeroveis.github.io/tender-pulse/"
    print(f"[gh-pages] probing live site: {target_url}...")
    for attempt in range(12):
        try:
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (TenderPulse Deployment Prober)"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                if status == 200:
                    print(f"[gh-pages] Verified live HTTP 200 on {target_url}!")
                    return
        except Exception as exc:
            print(f"[gh-pages] attempt {attempt+1}: {exc}, waiting 5s...")
            time.sleep(5)

    print(f"[gh-pages] note: site published; GitHub Pages propagation may take 1-2 minutes.")

if __name__ == "__main__":
    main()
