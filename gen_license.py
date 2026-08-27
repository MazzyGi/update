#!/usr/bin/env python3
"""gen_license.py — 授权码生成器 (管理员用).
用法:
  python3 gen_license.py <机器码> [到期日 YYYY-MM-DD 默认 1 年]
输出授权码 (与 C++ derive_license_code 算法一致), 并可直接更新
GitHub 授权表 (需 GH_TOKEN 环境变量)."""
import hashlib
import json
import os
import sys
import time
import urllib.request

SALT = "msa.mail.2026.lic"
REPO = "MazzyGi/update"
ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def derive(mcode: str) -> str:
    sha = hashlib.sha256((mcode + SALT).encode()).digest()
    g = ""
    for i in range(4):
        v = (sha[i * 2] << 8) | sha[i * 2 + 1]
        for k in range(4):
            g += ALPHA[(v >> (k * 4)) & 31]
    return "-".join(g[i:i + 4] for i in range(0, 16, 4))


def gh_put(path: str, content: dict, msg: str, token: str):
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    req = urllib.request.Request(api)
    req.add_header("Authorization", f"token {token}")

    def run(r):
        try:
            return json.loads(urllib.request.urlopen(r, timeout=30).read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    cur = run(req)
    body = {
        "message": msg,
        "content": __import__("base64").b64encode(
            json.dumps(content, ensure_ascii=False,
                       indent=2).encode()).decode(),
    }
    if "sha" in cur:
        body["sha"] = cur["sha"]
    req2 = urllib.request.Request(
        api, data=json.dumps(body).encode(), method="PUT")
    req2.add_header("Authorization", f"token {token}")
    return run(req2)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    mcode = sys.argv[1].strip().lower()
    expire = sys.argv[2] if len(sys.argv) > 2 else time.strftime(
        "%Y-%m-%d", time.localtime(time.time() + 365 * 86400))
    code = derive(mcode)
    print(f"机器码: {mcode}")
    print(f"授权码: {code}")
    print(f"到期:   {expire}")
    tok = os.environ.get("GH_TOKEN", "")
    if tok:
        # 拉当前表 -> 合并 -> 推
        api = (f"https://api.github.com/repos/{REPO}/contents/"
               f"licenses.json")
        req = urllib.request.Request(api)
        req.add_header("Authorization", f"token {tok}")
        import base64
        try:
            cur = json.loads(
                urllib.request.urlopen(req, timeout=30).read())
            lic = json.loads(base64.b64decode(cur["content"]))
        except Exception:
            lic = {"licenses": {}}
        lic.setdefault("licenses", {})[mcode] = {
            "code": code, "expire": expire,
            "note": f"issued {time.strftime('%Y-%m-%d')}"}
        r = gh_put("licenses.json", lic,
                   f"license {mcode[:8]} -> {expire}", tok)
        print("授权表更新:", "ok" if r.get("content") else r)
    else:
        print("(设置 GH_TOKEN 环境变量可自动登记授权表)")


if __name__ == "__main__":
    main()
