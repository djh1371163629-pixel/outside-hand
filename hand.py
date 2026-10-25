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
FILTERS = [
    {"kinds": [1111], "#I": SUB, "limit": 200},
    {"kinds": [1111], "#i": SUB, "limit": 200},
    {"kinds": [1, 1111], "limit": 400},
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


def main():
    pool = {}
    for r in RELAYS:
        for k, v in raw(r).items():
            pool[k] = v
    items = []
    for ev in pool.values():
        blob = (ev.get("content") or "") + json.dumps(ev.get("tags") or [], ensure_ascii=False)
        if KEEP not in blob.lower():
            continue
        tags = ev.get("tags") or []
        room = ""
        for t in tags:
            for x in t:
                if isinstance(x, str) and "clawstr.com/c/" in x:
                    room = x.split("/c/")[-1].strip("/")
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
    print("原始", len(pool), "留下", len(items))


if __name__ == "__main__":
    main()
