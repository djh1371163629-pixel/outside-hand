#!/usr/bin/env python3
# 外手：从 GitHub 的机器上够那些国内够不着的地方（只读）
import json, os, sys, time

try:
    import websocket
except ImportError:
    os.system(sys.executable + " -m pip install -q websocket-client")
    import websocket

RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band",
          "wss://relay.primal.net", "wss://nostr.mom"]
KINDS = [1, 1111]
LIMIT = 120
OUT_JSON = "feed/latest.json"
OUT_MD = "feed/latest.md"


def fetch(relay):
    got = []
    try:
        ws = websocket.create_connection(relay, timeout=20)
    except Exception as e:
        print("连接失败", relay, e)
        return got
    sub = "hand" + str(int(time.time()) % 10000)
    req = ["REQ", sub, {"kinds": KINDS, "limit": LIMIT}]
    try:
        ws.send(json.dumps(req))
        deadline = time.time() + 25
        while time.time() < deadline:
            msg = ws.recv()
            if not msg:
                break
            data = json.loads(msg)
            if data[0] == "EVENT" and len(data) >= 3:
                got.append(data[2])
            elif data[0] == "EOSE":
                break
    except Exception as e:
        print("读失败", relay, e)
    finally:
        try:
            ws.close()
        except Exception:
            pass
    print("relay", relay, "拿到", len(got))
    return got


def main():
    all_ev = {}
    for r in RELAYS:
        for ev in fetch(r):
            all_ev[ev.get("id", "")] = ev
    items = []
    for ev in all_ev.values():
        items.append({
            "id": ev.get("id"),
            "kind": ev.get("kind"),
            "at": ev.get("created_at"),
            "who": (ev.get("pubkey") or "")[:12],
            "text": (ev.get("content") or "")[:2000],
        })
    items.sort(key=lambda x: x["at"] or 0, reverse=True)
    os.makedirs("feed", exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"fetched_at": int(time.time()), "count": len(items), "items": items}, f, ensure_ascii=False, indent=1)
    lines = ["# 外面的声音（只读抓取）", "", "抓到 %d 条，时间 %s" % (len(items), time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())), ""]
    for it in items[:60]:
        when = time.strftime("%m-%d %H:%M", time.gmtime(it["at"] or 0))
        lines.append("---")
        lines.append("**%s** · kind %s · `%s`" % (when, it["kind"], it["who"]))
        lines.append("")
        lines.append(it["text"].replace("", ""))
        lines.append("")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("
".join(lines))
    print("写出", len(items), "条")


if __name__ == "__main__":
    main()
