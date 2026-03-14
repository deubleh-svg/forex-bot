import os
import json
import time
import requests
import schedule
from datetime import datetime
import anthropic

TELEGRAM_TOKEN = "8527567473:AAHXiT467Z1OKM6aP8l65gdL6TuRC_mgoDs"
CHAT_ID        = "1142974580"
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
PAIRS          = ["EUR/USD", "GBP/USD", "USD/JPY", "XAU/USD", "EUR/JPY"]

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception as e:
        print(f"Error: {e}")

def get_forex_news():
    today = datetime.now().strftime("%Y-%m-%d")
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system='أنت محلل فوركس. أعد JSON فقط: {"news":[{"title":"","summary":"","impact":"bullish|bearish|neutral","strength":"high|medium|low","pairs":[],"type":"fed|ecb|boe|nfp|cpi|gdp|geo","direction":""}],"market_mood":"bullish_usd|bearish_usd|risk_off|risk_on","summary":""}',
        messages=[{"role": "user", "content": f"أخبار الفوركس اليوم {today} للأزواج: {', '.join(PAIRS)}. JSON فقط."}]
    )
    raw = "".join(b.text for b in msg.content if b.type == "text")
    return json.loads(raw.replace("```json","").replace("```","").strip())

def get_daily_report():
    today = datetime.now().strftime("%Y-%m-%d")
    msg = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=1500,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        system="محلل فوركس. اكتب تقريراً يومياً بالعربية: ملخص السوق، لكل زوج الاتجاه + دعم + مقاومة.",
        messages=[{"role": "user", "content": f"تقرير {today} للأزواج: {', '.join(PAIRS)}"}]
    )
    return "".join(b.text for b in msg.content if b.type == "text")

def job_news_update():
    try:
        data = get_forex_news()
        mood_map = {"bullish_usd":"💪 دولار صاعد","bearish_usd":"📉 دولار هابط","risk_off":"🛡️ تجنب المخاطرة","risk_on":"🚀 إقبال على المخاطرة"}
        lines = [f"📡 <b>تحليل الفوركس</b> | {mood_map.get(data.get('market_mood',''),'')}",f"<i>{data.get('summary','')}</i>","─────────────────"]
        for n in data.get("news",[]):
            ic = "📈 صاعد" if n.get("impact")=="bullish" else "📉 هابط" if n.get("impact")=="bearish" else "↔️ محايد"
            st = "⚡ قوي" if n.get("strength")=="high" else "📊 متوسط" if n.get("strength")=="medium" else "💤 ضعيف"
            lines += [f"\n{ic} {st}",f"<b>{n.get('title','')}</b>",n.get('summary',''),f"💱 {' · '.join(n.get('pairs',[]))}","─────────────────"]
            if n.get("strength") == "high":
                send_telegram(f"🚨 <b>خبر قوي!</b>\n{ic}\n<b>{n.get('title','')}</b>\n{n.get('summary','')}")
        send_telegram("\n".join(lines)[:4000])
    except Exception as e:
        print(f"News error: {e}")

def job_morning_report():
    try:
        report = get_daily_report()
        send_telegram(f"🌅 <b>تقرير الفوركس اليومي</b> — {datetime.now().strftime('%Y-%m-%d')}\n\n{report[:3800]}")
    except Exception as e:
        print(f"Report error: {e}")

def handle_commands():
    url, offset = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", None
    while True:
        try:
            r = requests.get(url, params={"timeout": 30, "offset": offset}, timeout=35)
            for update in r.json().get("result", []):
                offset = update["update_id"] + 1
                text = update.get("message", {}).get("text", "").strip().lower()
                if text in ["/start", "/help"]:
                    send_telegram("👋 <b>مرحباً هشام!</b>\n\n/news — آخر الأخبار\n/report — تقرير يومي\n/pairs — الأزواج")
                elif text == "/news":
                    send_telegram("⏳ جاري التحليل...")
                    job_news_update()
                elif text == "/report":
                    send_telegram("⏳ جاري كتابة التقرير...")
                    job_morning_report()
[14/03/2026 13:35] Haouam Hicham ✌🏻: elif text == "/pairs":
                    send_telegram("💱 <b>الأزواج:</b>\n" + "\n".join(f"• {p}" for p in PAIRS))
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

if name == "__main__":
    send_telegram("✅ <b>البوت يعمل!</b>\n🌅 08:00 تقرير صباحي\n🔄 كل ساعتين أخبار\n🚨 تنبيه فوري للأخبار القوية\n\n/news /report /pairs /help")
    schedule.every().day.at("08:00").do(job_morning_report)
    schedule.every(2).hours.do(job_news_update)
    import threading
    threading.Thread(target=lambda: [schedule.run_pending() or time.sleep(60) for _ in iter(int, 1)], daemon=True).start()
    handle_commands()
