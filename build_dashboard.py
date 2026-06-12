#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影片掛網進度追蹤 — 儀表板產生器
讀取 data.json → 計算驗檔完成到掛網完成的工作天數（跳過六日）→ 產出 index.html
並在 stdout 印出 JSON 摘要（含 wd 編號逾期清單），供排程任務判斷是否要發通知。

天數分級（工作天）：
  ≤2 天  綠色（正常）
  3–4 天 黃色（注意）
  5–6 天 橘色（偏慢）
  ≥7 天  紅色（嚴重延誤）
wd 開頭編號若超過 2 個工作天仍未掛網 → 列入逾期警示。
"""
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data.json"
OUT = BASE / "index.html"

WD_OVERDUE_LIMIT = 2  # wd 編號允許的工作天數


def business_days(start: date, end: date) -> int:
    """計算 (start, end] 之間的工作天數，週六日不算。end <= start 回傳 0。"""
    if end <= start:
        return 0
    n, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def level_of(days: int) -> str:
    if days <= 2:
        return "ok"
    if days <= 4:
        return "warn"
    if days <= 6:
        return "slow"
    return "late"


LEVEL_LABEL = {"ok": "正常", "warn": "注意", "slow": "偏慢", "late": "嚴重延誤"}


def parse_dt(s):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    today = date.today()
    pending, done = [], []

    for item in data.get("items", {}).values():
        v = parse_dt(item.get("verify_done"))
        u = parse_dt(item.get("upload_done"))
        if v is None:
            continue
        row = dict(item)
        row["is_wd"] = item["id"].upper().startswith("WD")
        if u:
            row["days"] = business_days(v.date(), u.date())
            row["status"] = "done"
            done.append(row)
        else:
            row["days"] = business_days(v.date(), today)
            row["status"] = "pending"
            row["overdue_wd"] = row["is_wd"] and row["days"] > WD_OVERDUE_LIMIT
            pending.append(row)

    pending.sort(key=lambda r: (-r["days"], r["id"]))
    done.sort(key=lambda r: r["upload_done"], reverse=True)
    overdue_wd = [r for r in pending if r.get("overdue_wd")]

    OUT.write_text(render(pending, done, overdue_wd, data), encoding="utf-8")

    print(json.dumps({
        "pending": len(pending),
        "done": len(done),
        "overdue_wd": [{"id": r["id"], "title": r["title"], "days": r["days"]} for r in overdue_wd],
    }, ensure_ascii=False))


def render(pending, done, overdue_wd, data):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def row_html(r):
        cls = level_of(r["days"])
        badge = f'<span class="badge {cls}">{r["days"]} 天</span>'
        wd_mark = '<span class="wdtag">WD</span>' if r["is_wd"] else ""
        alarm = ' <span class="alarm">⚠ 逾期未掛網</span>' if r.get("overdue_wd") else ""
        status = ("✅ " + (r.get("upload_done") or "")[:16]) if r["status"] == "done" \
                 else '<span class="pend">⏳ 待掛網</span>'
        return (f'<tr class="lv-{cls}">'
                f'<td class="id">{r["id"]}{wd_mark}{alarm}</td>'
                f'<td>{r.get("title") or ""}</td>'
                f'<td>{(r.get("verify_done") or "")[:16]}</td>'
                f'<td>{status}</td>'
                f'<td class="num">{badge}</td>'
                f'<td>{LEVEL_LABEL[cls]}</td></tr>')

    pending_rows = "\n".join(row_html(r) for r in pending) or \
        '<tr><td colspan="6" class="empty">目前沒有待掛網項目 🎉</td></tr>'
    done_rows = "\n".join(row_html(r) for r in done) or \
        '<tr><td colspan="6" class="empty">尚無已完成紀錄</td></tr>'

    alert_html = ""
    if overdue_wd:
        lis = "".join(f'<li><b>{r["id"]}</b>（{r["title"]}）— 驗檔完成已 <b>{r["days"]} 個工作天</b>，尚未掛網</li>'
                      for r in overdue_wd)
        alert_html = f'<div class="alertbox"><h2>🚨 WD 編號逾期警示（超過 {WD_OVERDUE_LIMIT} 個工作天未掛網）</h2><ul>{lis}</ul><p>請立即聯繫同事處理掛網。</p></div>'

    head = """<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--ok:#2e7d32;--warn:#b58900;--slow:#e65100;--late:#c62828;
--ok-bg:#e8f5e9;--warn-bg:#fff8e1;--slow-bg:#fff3e0;--late-bg:#ffebee;}
*{box-sizing:border-box}
body{font-family:"PingFang TC","Microsoft JhengHei",sans-serif;margin:0;background:#f5f6f8;color:#263238;}
.wrap{max-width:1000px;margin:0 auto;padding:24px 16px 60px;}
h1{font-size:26px;margin:8px 0 2px}
.sub{color:#78909c;font-size:13px;margin-bottom:18px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:18px}
.card{flex:1;min-width:140px;background:#fff;border-radius:12px;padding:14px 18px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card .n{font-size:30px;font-weight:700}.card .t{font-size:13px;color:#78909c}
.card.red .n{color:var(--late)}.card.green .n{color:var(--ok)}.card.blue .n{color:#1565c0}
.alertbox{background:var(--late-bg);border:2px solid var(--late);border-radius:12px;padding:14px 20px;margin-bottom:18px}
.alertbox h2{margin:0 0 8px;font-size:17px;color:var(--late)}
.alertbox ul{margin:0 0 6px;padding-left:20px}.alertbox p{margin:0;font-size:13px;color:var(--late)}
h2.sec{font-size:18px;margin:26px 0 10px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)}
th{background:#37474f;color:#fff;font-size:13px;padding:10px 12px;text-align:left;white-space:nowrap}
td{padding:10px 12px;font-size:14px;border-top:1px solid #eceff1}
tr.lv-ok{background:var(--ok-bg)}tr.lv-warn{background:var(--warn-bg)}
tr.lv-slow{background:var(--slow-bg)}tr.lv-late{background:var(--late-bg)}
td.id{font-weight:700;white-space:nowrap}
td.num{text-align:center}
.badge{display:inline-block;min-width:52px;text-align:center;padding:3px 10px;border-radius:99px;color:#fff;font-weight:700;font-size:13px}
.badge.ok{background:var(--ok)}.badge.warn{background:var(--warn)}
.badge.slow{background:var(--slow)}.badge.late{background:var(--late)}
.wdtag{background:#1565c0;color:#fff;border-radius:4px;font-size:11px;padding:1px 6px;margin-left:6px;vertical-align:1px}
.alarm{color:var(--late);font-size:12px;font-weight:700}
.pend{color:#e65100;font-weight:700}
.empty{text-align:center;color:#90a4ae;padding:22px}
.legend{margin-top:14px;font-size:13px;color:#546e7a}
.legend .badge{min-width:auto;margin:0 2px}
</style>"""

    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><title>影片掛網進度追蹤</title>{head}</head>
<body><div class="wrap">
<h1>📡 影片掛網進度追蹤</h1>
<div class="sub">資料來源：admin@hwadzan.com（amtbwork 工作進度通知信）｜最後更新：{now}｜天數均為工作天（不含六、日）</div>
<div class="cards">
<div class="card blue"><div class="n">{len(pending)}</div><div class="t">待掛網</div></div>
<div class="card red"><div class="n">{len(overdue_wd)}</div><div class="t">WD 逾期警示</div></div>
<div class="card green"><div class="n">{len(done)}</div><div class="t">已掛網完成</div></div>
</div>
{alert_html}
<h2 class="sec">⏳ 待掛網（驗檔完成、尚未掛網）</h2>
<table><thead><tr><th>編號</th><th>標題</th><th>驗檔完成</th><th>掛網狀態</th><th>已經過</th><th>分級</th></tr></thead>
<tbody>{pending_rows}</tbody></table>
<h2 class="sec">✅ 已完成（驗檔 → 掛網）</h2>
<table><thead><tr><th>編號</th><th>標題</th><th>驗檔完成</th><th>掛網完成</th><th>耗時</th><th>分級</th></tr></thead>
<tbody>{done_rows}</tbody></table>
<div class="legend">分級標準（工作天）：
<span class="badge ok">≤2 天 正常</span>
<span class="badge warn">3–4 天 注意</span>
<span class="badge slow">5–6 天 偏慢</span>
<span class="badge late">≥7 天 嚴重延誤</span>
｜ WD 編號超過 2 個工作天未掛網即觸發 🚨 警示通知</div>
</div></body></html>"""


if __name__ == "__main__":
    main()
