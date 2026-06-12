#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LINE 推播工具（透過「資訊日報」官方帳號的 Messaging API）
用法：python3 line_notify.py "訊息文字"

金鑰設定檔存在本機（不在 git repo 內）：~/.config/hwadzan-line/config.json
格式：{"channel_access_token": "（長效 token）", "user_id": "U開頭的使用者ID"}
"""
import json
import sys
import urllib.request
from pathlib import Path

CONFIG = Path.home() / ".config" / "hwadzan-line" / "config.json"
API = "https://api.line.me/v2/bot/message/push"


def send(text: str) -> None:
    if not CONFIG.exists():
        sys.exit(f"找不到設定檔 {CONFIG}，請先建立（含 channel_access_token 與 user_id）")
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    body = json.dumps({
        "to": cfg["user_id"],
        "messages": [{"type": "text", "text": text}],
    }).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {cfg['channel_access_token']}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"LINE 推播成功（HTTP {resp.status}）")
    except urllib.error.HTTPError as e:
        sys.exit(f"LINE 推播失敗 HTTP {e.code}: {e.read().decode('utf-8', 'replace')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('用法：python3 line_notify.py "訊息文字"')
    send(sys.argv[1])
