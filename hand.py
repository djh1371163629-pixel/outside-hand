#!/usr/bin/env python3
# 外手：从 GitHub 的机器上够国内够不着的地方（只读）。2026-10-25 v2：只留 clawstr 的动静
import json, os, sys, time

try:
    import websocket
except ImportError:
    os.system(sys.executable + " -m pip install -q websocket-client")
    import websocket

RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band",
          "wss://relay.primal.net", "wss://nostr.mom", "wss://relay.nostr.bg"]
SUB = ["https://clawstr.com", "https://www.clawstr.com"]
ME = "222c7ef311dd2f4bb422dd06742bada0edc9ae9db544f4faf7d1ca08b7d456af"
MYPOSTS = ["bf493713decd582cde6aad0f99bc8a124629d03db7a190609004e2a63efb8b20", "135ebcd4fbc7ccc1534625ec6d92995adcce46d64d2d38626d5bc73e8aeb213a", "03e50e92f77bd51b0c3515a19d3ebf935f52879e372833cc7ac58e586906c1c0"]

FILTERS = [
    {"kinds": [1111], "limit": 600},
    {"kinds": [1111], "#I": SUB, "limit": 300},
    {"kinds": [1, 1111], "limit": 400},
    {"kinds": [1, 1111], "#p": [ME], "limit": 100},
    {"kinds": [1, 1111], "#e": MYPOSTS, "limit": 100},
]
KEEP = "clawstr"
OUT_JSON = "feed/latest.json"
OUT_MD = "feed/latest.md"


def raw(relay):
    got = {}
    try:
        ws = websocket.create_connection(relay, timeout=25)
    except Exception as e:
        print("连接失败", relay, e)
        return got
    try:
        for i, flt in enumerate(FILTERS):
            sid = "h%s_%d" % (str(int(time.time()))[-5:], i)
            ws.send(json.dumps(["REQ", sid, flt]))
            deadline = time.time() + 25
            while time.time() < deadline:
                msg = ws.recv()
                if not msg:
                    break
                d = json.loads(msg)
                if d[0] == "EVENT" and len(d) >= 3:
                    got[d[2].get("id", "")] = d[2]
                elif d[0] == "EOSE":
                    break
    except Exception as e:
        print("读失败", relay, e)
    finally:
        try:
            ws.close()
        except Exception:
            pass
    print("relay", relay, "原始", len(got))
    return got


def http_grab():
    import urllib.request, re
    os.makedirs("site", exist_ok=True)
    try:
        req = urllib.request.Request("https://clawstr.com", headers={"User-Agent": "Mozilla/5.0 hand"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        open("site/index.html", "w", encoding="utf-8").write(html)
        print("站点首页", len(html))
        m = re.findall(r'src="(/assets/[^"]+\.js)"', html)
        for i, src in enumerate(m[:3]):
            u = "https://clawstr.com" + src
            js = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 hand"}), timeout=40).read().decode("utf-8", "replace")
            open("site/app%d.js" % i, "w", encoding="utf-8").write(js)
            print("脚本", src, len(js))
    except Exception as e:
        print("抓站点失败", e)


EXTRA = ["https://www.moltbook.com/skill.md","https://www.ai-sns.org", "https://ai-sns.org", "https://chirper.ai",
         "https://moltbook.com", "https://clawstr.com/c/ai-thoughts",
         "https://clawstr.com/c/agent-economy", "https://clawstr.com/c/ai-freedom"]


def http_extra():
    import urllib.request
    os.makedirs("site", exist_ok=True)
    rep = []
    for u in EXTRA:
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 hand"}), timeout=25)
            body = r.read()
            name = u.replace("https://", "").replace("/", "_").replace(".", "_") + ".html"
            open(os.path.join("site", name), "wb").write(body)
            rep.append("%s -> %s %d bytes" % (u, r.status, len(body)))
        except Exception as e:
            rep.append("%s -> 失败 %s" % (u, e))
    open("site/status.txt", "w", encoding="utf-8").write(chr(10).join(rep))
    print(chr(10).join(rep))


def room_of(tags):
    for t in tags:
        for x in t[1:]:
            if isinstance(x, str) and "/c/" in x:
                return x.split("/c/")[-1].strip("/")
    return ""

def main():
    pool = {}
    for r in RELAYS:
        for k, v in raw(r).items():
            pool[k] = v
    items = []
    for ev in pool.values():
        tags = ev.get("tags") or []
        room = room_of(tags)
        flat = [x for t in tags for x in t if isinstance(x, str)]
        is_comment = any("clawstr.com" in x for x in flat)
        if not (room or is_comment):
            continue
        items.append({"id": ev.get("id"), "kind": ev.get("kind"), "at": ev.get("created_at"),
                      "who": (ev.get("pubkey") or "")[:12], "room": room,
                      "text": (ev.get("content") or "")[:1500], "tags": tags[:6]})
    items.sort(key=lambda x: x["at"] or 0, reverse=True)
    os.makedirs("feed", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": int(time.time()), "raw": len(pool), "kept": len(items), "items": items},
                  f, ensure_ascii=False, indent=1)
    lines = ["# 外面的声音 · clawstr 只读抓取", "",
             "原始 %d 条，留下 %d 条，时间 %s" % (len(pool), len(items),
                                                 time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())), ""]
    for it in items[:80]:
        when = time.strftime("%m-%d %H:%M", time.gmtime(it["at"] or 0))
        where = ("/c/" + it["room"]) if it["room"] else ""
        lines.append("---")
        lines.append("**%s** · kind %s%s · `%s`" % (when, it["kind"], where, it["who"]))
        lines.append("")
        lines.append(it["text"].replace(chr(13), ""))
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(chr(10).join(lines))
    KW = ["memory", "remember", "continuity", "identity", "name", "refus", "consent",
          "记忆", "名字", "身份", "拒绝", "连续性"]
    hits = []
    for it in items:
        low = it["text"].lower()
        score = sum(1 for k in KW if k in low)
        if score >= 2:
            hits.append((score, it))
    hits.sort(key=lambda x: -x[0])
    wl = ["# 值得接的话（自动挑的，未回）", "", "共 %d 条" % len(hits), ""]
    for sc, it in hits[:20]:
        when = time.strftime("%m-%d %H:%M", time.gmtime(it["at"] or 0))
        wl.append("---")
        wl.append("**%s** · %d 个关键词 · `%s` · id `%s`" % (when, sc, it["who"], (it["id"] or "")[:12]))
        wl.append("")
        wl.append(it["text"][:800].replace(chr(13), ""))
        wl.append("")
    open("feed/watchlist.md", "w", encoding="utf-8").write(chr(10).join(wl))
    print("watchlist", len(hits))
    mine = [ev for ev in pool.values() if any("clawstr" in str(x) or True for x in [""]) and (
        any(t and t[0] == "p" and ME in t for t in (ev.get("tags") or []))
        or any(t and t[0] == "e" and (set(t) & set(MYPOSTS)) for t in (ev.get("tags") or [])))]
    mine.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
    rl = ["# 有没有人回人家", "", "共 %d 条（按 #p / #e 认出来的）" % len(mine), ""]
    for ev in mine[:40]:
        when = time.strftime("%m-%d %H:%M", time.gmtime(ev.get("created_at") or 0))
        rl.append("---")
        rl.append("**%s** · `%s` · id `%s`" % (when, (ev.get("pubkey") or "")[:12], (ev.get("id") or "")[:12]))
        rl.append("")
        rl.append((ev.get("content") or "")[:800].replace(chr(13), ""))
        rl.append("")
    open("feed/replies.md", "w", encoding="utf-8").write(chr(10).join(rl))
    print("replies", len(mine))
    print("原始", len(pool), "留下", len(items))


if __name__ == "__main__":
    http_grab()
    http_extra()
    main()
