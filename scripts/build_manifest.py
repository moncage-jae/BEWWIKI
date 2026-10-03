#!/usr/bin/env python3
"""wiki/ 폴더의 md 파일을 읽어 사이트가 쓰는 wiki/manifest.json을 만든다.

GitHub Actions가 push 때마다 실행한다. 직접 실행해도 된다:
    python3 scripts/build_manifest.py
"""
import json
import os
import subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def git(*args):
    try:
        out = subprocess.run(["git", "-c", "core.quotepath=false", *args], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8")
        return out.stdout.strip()
    except Exception:
        return ""


def split_front_matter(text):
    """맨 위의 --- 사이 속성(분류, 상태, 순서)을 떼어 낸다."""
    meta = {}
    if text.startswith("---"):
        lines = text.split("\n")
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for line in lines[1:i]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")
                return meta, "\n".join(lines[i + 1:])
    return meta, text


def main():
    pages, images = [], []
    for dirpath, dirnames, filenames in os.walk(WIKI):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, WIKI).replace(os.sep, "/")
            if name.lower().endswith(IMAGE_EXT):
                images.append(rel)
                continue
            if not name.lower().endswith(".md"):
                continue
            with open(full, encoding="utf-8") as f:
                raw = f.read().replace("\r\n", "\n")
            meta, body = split_front_matter(raw)
            log = git("log", "-1", "--format=%aI\t%an", "--", "wiki/" + rel)
            updated, author = (log.split("\t") + ["", ""])[:2] if log else ("", "")
            try:
                order = float(meta.get("순서", meta.get("order", 999)))
            except ValueError:
                order = 999
            pages.append({
                "file": rel,
                "title": os.path.splitext(name)[0],
                "category": meta.get("분류", meta.get("category", "")) or "분류 없음",
                "status": meta.get("상태", meta.get("status", "")),
                "order": order,
                "updated": updated,
                "author": author,
                "md": body,
            })

    recent = []
    log = git("log", "-n", "40", "--format=@@%aI\t%an\t%s", "--name-only", "--", "wiki/")
    cur = None
    for line in log.split("\n"):
        if line.startswith("@@"):
            d, a, s = (line[2:].split("\t") + ["", "", ""])[:3]
            cur = {"date": d, "author": a, "message": s, "files": []}
            recent.append(cur)
        elif line.strip() and cur is not None and line.endswith(".md"):
            cur["files"].append(line.strip()[len("wiki/"):] if line.startswith("wiki/") else line.strip())

    repo = os.environ.get("GITHUB_REPOSITORY", "moncage-jae/BEWWIKI")
    owner, name = repo.split("/", 1)
    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "repo": {"owner": owner, "name": name, "branch": os.environ.get("GITHUB_REF_NAME", "main")},
        "pages": pages,
        "images": images,
        "recent": recent,
    }
    with open(os.path.join(WIKI, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    print(f"문서 {len(pages)}개, 이미지 {len(images)}개를 manifest.json에 기록했습니다.")


if __name__ == "__main__":
    main()
