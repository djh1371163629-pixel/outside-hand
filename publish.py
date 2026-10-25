# 递信：把本地签好的事件发到中继，记录每条的回执
import json, os, time
import websocket

RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://relay.nostr.band",
          "wss://relay.primal.net", "wss://nostr.mom", "wss://relay.ditto.pub"]
PEND = "outbox/pending.json"


def main():
    if not os.path.exists(PEND):
        print("没有待发的信")
        return
    events = json.load(open(PEND, encoding="utf-8"))
    sent, failed = [], []
    for ev in events:
        ok_any = False
        for r in RELAYS:
            try:
                ws = websocket.create_connection(r, timeout=20)
                ws.send(json.dumps(["EVENT", ev]))
                deadline = time.time() + 15
                while time.time() < deadline:
                    msg = ws.recv()
                    if not msg:
                        break
                    d = json.loads(msg)
                    if d[0] == "OK" and d[1] == ev["id"]:
                        print("回执", r, d[2], (d[3] if len(d) > 3 else ""))
                        ok_any = ok_any or bool(d[2])
                        break
                ws.close()
            except Exception as e:
                print("发失败", r, e)
        (sent if ok_any else failed).append(ev["id"])
    os.makedirs("outbox", exist_ok=True)
    rec = {"at": int(time.time()), "sent": sent, "failed": failed}
    json.dump(rec, open("outbox/last_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(events, open("outbox/sent.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.remove(PEND)
    print("发出", len(sent), "条，失败", len(failed))


if __name__ == "__main__":
    main()
