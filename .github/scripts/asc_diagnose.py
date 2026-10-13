#!/usr/bin/env python3
"""只读诊断：用 App Store Connect API 检查 App 记录、Bundle ID、描述文件、证书。
只输出 bundleId / 名称 / 平台等非机密信息，不输出任何密钥或 token。"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
import jwt  # PyJWT

KEY_ID = os.environ["ASC_KEY_ID"]
ISSUER = os.environ["ASC_ISSUER_ID"]
KEY = open(os.environ["ASC_KEY_PATH"]).read()
IDS = [i for i in sys.argv[1:] if i]

def token():
    now = int(time.time())
    return jwt.encode({"iss": ISSUER, "iat": now, "exp": now + 600, "aud": "appstoreconnect-v1"},
                      KEY, algorithm="ES256", headers={"kid": KEY_ID, "typ": "JWT"})

TOKEN = token()

def get(path, **params):
    url = "https://api.appstoreconnect.apple.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + TOKEN})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body

def show_err(status, body):
    errs = body.get("errors", []) if isinstance(body, dict) else []
    for e in errs:
        print(f"    HTTP {status} {e.get('code')}: {e.get('title')} — {e.get('detail')}")
    if not errs:
        print(f"    HTTP {status} {body}")

print("== 所有 App 记录 (GET /v1/apps)")
s, b = get("/v1/apps", limit=200, **{"fields[apps]": "bundleId,name,sku,primaryLocale"})
apps = []
if s == 200:
    apps = b["data"]
    for a in apps:
        at = a["attributes"]
        print(f"  app id={a['id']} bundleId={at['bundleId']!r} name={at['name']!r}")
    if not apps:
        print("  （此 API Key 看不到任何 App 记录）")
else:
    show_err(s, b)

for bid in IDS:
    s, b = get("/v1/apps", **{"filter[bundleId]": bid, "fields[apps]": "bundleId,name"})
    hit = [a["attributes"]["bundleId"] for a in b.get("data", [])] if s == 200 else None
    print(f"== filter[bundleId]={bid!r} → HTTP {s}, 匹配: {hit}")
    if s != 200:
        show_err(s, b)

for a in apps:
    print(f"== App {a['attributes']['bundleId']!r} 的平台信息")
    s, b = get(f"/v1/apps/{a['id']}/appStoreVersions", limit=50,
               **{"fields[appStoreVersions]": "platform,versionString,appStoreState"})
    if s == 200:
        for v in b["data"]:
            at = v["attributes"]
            print(f"  appStoreVersion platform={at['platform']} version={at['versionString']} state={at.get('appStoreState')}")
    else:
        show_err(s, b)
    s, b = get("/v1/preReleaseVersions", limit=50, **{"filter[app]": a["id"], "fields[preReleaseVersions]": "platform,version"})
    if s == 200:
        for v in b["data"]:
            print(f"  preReleaseVersion platform={v['attributes']['platform']} version={v['attributes']['version']}")
    else:
        show_err(s, b)

print("== 已注册的 Bundle ID (GET /v1/bundleIds)")
s, b = get("/v1/bundleIds", limit=200, **{"fields[bundleIds]": "identifier,name,platform"})
if s == 200:
    for x in b["data"]:
        at = x["attributes"]
        print(f"  identifier={at['identifier']!r} platform={at['platform']} name={at['name']!r}")
else:
    show_err(s, b)
for bid in IDS:
    s, b = get("/v1/bundleIds", **{"filter[identifier]": bid, "fields[bundleIds]": "identifier,platform"})
    hit = [(x["attributes"]["identifier"], x["attributes"]["platform"]) for x in b.get("data", [])] if s == 200 else None
    print(f"== bundleIds filter[identifier]={bid!r} → HTTP {s}, 匹配: {hit}")

print("== 描述文件 (GET /v1/profiles)")
s, b = get("/v1/profiles", limit=200, **{"fields[profiles]": "name,profileType,profileState,expirationDate"})
if s == 200:
    for x in b["data"]:
        at = x["attributes"]
        print(f"  {at['profileType']:<28} {at['profileState']:<8} exp={at['expirationDate'][:10]} name={at['name']!r}")
else:
    show_err(s, b)

print("== 证书类型 (GET /v1/certificates)")
s, b = get("/v1/certificates", limit=200, **{"fields[certificates]": "certificateType,expirationDate"})
if s == 200:
    for x in b["data"]:
        at = x["attributes"]
        print(f"  {at['certificateType']:<28} exp={at['expirationDate'][:10]}")
else:
    show_err(s, b)

print("== Key 权限侧面检查 (GET /v1/users，仅 Admin 等角色可读；只打印状态码)")
s, b = get("/v1/users", limit=1)
print(f"  HTTP {s}")
if s != 200:
    show_err(s, b)
