import yfinance as yf
import requests
import sys
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from config import GROQ_API_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER
except ImportError:
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    EMAIL_SENDER = os.environ.get('EMAIL_SENDER')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
    EMAIL_RECEIVER = os.environ.get('EMAIL_RECEIVER')

PORTFOLIO = {
    "COALINDIA":  "COALINDIA.NS",
    "RVNL":       "RVNL.NS",
    "IREDA":      "IREDA.NS",
    "SJVN":       "SJVN.NS",
    "NBCC":       "NBCC.NS",
    "ZUARI":      "ZUARI.NS",
    "LICI":       "LICI.NS",
    "UNIONBANK":  "UNIONBANK.NS",
    "TATASTEEL":  "TATASTEEL.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "VEDL":       "VEDL.NS",
    "NHPC":       "NHPC.NS",
    "NIFTYBEES":  "NIFTYBEES.NS",
    "JUNIORBEES": "JUNIORBEES.NS",
    "GOLDBEES":   "GOLDBEES.NS",
    "NOVAAGRI":   "NOVAAGRI.NS",
    "AMARAJABAT": "ARE&M.NS",
}

BUY_PRICES = {
    "COALINDIA":  156.95,
    "RVNL":       376.44,
    "IREDA":      181.85,
    "SJVN":       28.50,
    "NBCC":       113.33,
    "ZUARI":      223.45,
    "LICI":       904.00,
    "UNIONBANK":  148.95,
    "TATASTEEL":  195.10,
    "BAJFINANCE": 862.75,
    "VEDL":       346.50,
    "NHPC":       82.85,
    "NIFTYBEES":  236.91,
    "JUNIORBEES": 606.20,
    "GOLDBEES":   110.51,
    "NOVAAGRI":   72.52,
    "AMARAJABAT": 897.00,
}

STOP_LOSSES = {
    "COALINDIA":  410,
    "RVNL":       265,
    "IREDA":      118,
    "SJVN":       72,
    "NBCC":       82,
    "ZUARI":      238,
    "LICI":       740,
    "UNIONBANK":  155,
    "TATASTEEL":  188,
    "BAJFINANCE": 820,
    "VEDL":       670,
    "NHPC":       73,
    "AMARAJABAT": 810,
}

TARGETS = {
    "COALINDIA":  480,
    "RVNL":       382,
    "IREDA":      175,
    "SJVN":       92,
    "NBCC":       113,
    "ZUARI":      284,
    "LICI":       920,
    "UNIONBANK":  200,
    "TATASTEEL":  240,
    "BAJFINANCE": 1050,
    "VEDL":       800,
    "NHPC":       95,
    "AMARAJABAT": 1050,
}

def get_indian_market_news():
    try:
        prompt = """You are an Indian stock market analyst. List the 5 most impactful Indian market news stories from TODAY or YESTERDAY that could affect stock prices.

Focus on: RBI decisions, government policy, FII/DII flows, major corporate results, global events affecting India, sector specific news.

For each story write:
📰 [HEADLINE]
💡 Impact: [1 sentence on how this affects Indian markets or specific sectors]

Be specific with actual news. No generic statements."""

        ai_resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800
            }
        )
        return ai_resp.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"News unavailable: {str(e)}"

def get_index_data():
    indices = {
        "Nifty 50":   "^NSEI",
        "Sensex":     "^BSESN",
        "Nifty Bank": "^NSEBANK",
    }
    results = {}
    for name, symbol in indices.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            if len(hist) >= 2:
                prev = hist['Close'].iloc[-2]
                curr = hist['Close'].iloc[-1]
                change = curr - prev
                results[name] = {
                    "price":  round(curr, 2),
                    "change": round(change, 2),
                    "pct":    round((change / prev) * 100, 2)
                }
        except:
            results[name] = {"price": "N/A", "change": 0, "pct": 0}
    return results


def get_portfolio_data():
    results = {}
    for stock, symbol in PORTFOLIO.items():
        try:
            hist = yf.Ticker(symbol).history(period="2d")
            if len(hist) >= 1:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) >= 2 else curr
                day_chg = curr - prev
                buy = BUY_PRICES.get(stock, curr)
                total_pct = ((curr - buy) / buy) * 100
                alert = ""
                if stock in STOP_LOSSES and curr <= STOP_LOSSES[stock]:
                    alert = "🚨 STOP LOSS TRIGGERED"
                elif stock in TARGETS and curr >= TARGETS[stock]:
                    alert = "🎯 TARGET HIT"
                results[stock] = {
                    "price":      round(curr, 2),
                    "day_change": round(day_chg, 2),
                    "day_pct":    round((day_chg / prev) * 100, 2),
                    "total_pct":  round(total_pct, 2),
                    "alert":      alert
                }
        except:
            results[stock] = {
                "price":      "N/A",
                "day_change": 0,
                "day_pct":    0,
                "total_pct":  0,
                "alert":      ""
            }
    return results


def get_ai_summary(index_data, portfolio_data, summary_type):
    index_text = "\n".join([
        f"{n}: {d['price']} ({'+' if d['pct'] > 0 else ''}{d['pct']}%)"
        for n, d in index_data.items()
    ])
    all_stocks_text = "\n".join([
        f"{s}: ₹{d['price']} | {'+' if d['day_pct'] > 0 else ''}{d['day_pct']}% today | {'+' if d['total_pct'] > 0 else ''}{d['total_pct']}% overall | SL={STOP_LOSSES.get(s, 'N/A')} | Target={TARGETS.get(s, 'N/A')} | Alert={d['alert'] if d['alert'] else 'None'}"
        for s, d in portfolio_data.items() if d['price'] != 'N/A'
    ])
    time_context = "market open" if summary_type == "open" else "market close"
    total_stocks = len([d for d in portfolio_data.values() if d['price'] != 'N/A'])

    prompt = f"""You are a concise Indian stock market analyst helping a retail investor in Bengaluru.
Today is a {time_context}. Market context: {index_text}

Here is the investor's full portfolio:
{all_stocks_text}

Your job: Write a per-stock AI summary ranked from MOST URGENT to LEAST URGENT action needed.

Urgency ranking rules:
1. Stop loss triggered = most urgent
2. Target hit = very urgent
3. Big loss overall below -15% = urgent
4. Big move today up or down more than 2% = watch closely
5. Stable profitable position = least urgent

For each stock write exactly this format:
[URGENCY EMOJI] [RANK]. [STOCK NAME] - [ONE LINE STATUS]
[2 sentences: why it moved today and what action to take]

Urgency emojis: use 🚨 for Act Now, ⚠️ for Watch Closely, 📊 for Stable, ✅ for Holding Well

Rank ALL {total_stocks} stocks. Be direct and actionable. No thinking steps. Just the ranked list."""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a concise stock market analyst. Never show your thinking process. Always respond with the final answer only. No think tags. No reasoning steps. Just the output."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2000
            }
        )
        result = response.json()
        content = result['choices'][0]['message']['content']
        return content
    except Exception as e:
        return f"AI summary unavailable: {str(e)}"


def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Market Digest <{EMAIL_SENDER}>"
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("  ✅ Email sent successfully!")
    except Exception as e:
        print(f"  ❌ Email failed: {str(e)}")


def build_summary(summary_type="open"):
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    label = "🌅 MARKET OPEN" if summary_type == "open" else "🌆 MARKET CLOSE"

    print(f"\n{'='*55}")
    print(f"  {label} SUMMARY — {now}")
    print(f"{'='*55}\n")

    # Fetch all data
    index_data = get_index_data()
    portfolio_data = get_portfolio_data()
    ai_summary = get_ai_summary(index_data, portfolio_data, summary_type)
    news = get_indian_market_news()

    # Print indices
    print("📊 MARKET INDICES")
    print("-" * 40)
    for name, data in index_data.items():
        arrow = "▲" if data['change'] > 0 else "▼"
        sign = "+" if data['change'] > 0 else ""
        print(f"  {name}: ₹{data['price']} {arrow} {sign}{data['change']} pts ({sign}{data['pct']}%)")

    # Print portfolio
    print(f"\n💼 YOUR PORTFOLIO")
    print("-" * 40)
    for stock, data in portfolio_data.items():
        if data['price'] == 'N/A':
            print(f"  ⚠️  {stock}: Could not fetch price")
            continue
        arrow = "▲" if data['day_change'] > 0 else "▼"
        overall = "🟢" if data['total_pct'] > 0 else "🔴"
        print(f"  {overall} {stock:12} ₹{data['price']:>8} {arrow} {data['day_pct']:>+6.2f}% today | {data['total_pct']:>+7.2f}% overall")
        if data['alert']:
            print(f"          ⚡ {data['alert']}")

    # Print AI summary
    print(f"\n🤖 AI STOCK SUMMARY — Most Urgent to Least")
    print("-" * 40)
    print(f"\n{ai_summary}")
    print(f"\n{'='*55}")
    print(f"  Next: {'Market Close 3:30 PM' if summary_type == 'open' else 'Market Open 9:30 AM tomorrow'}")
    print(f"{'='*55}\n")

    # Build email
    news_section = f"TODAY'S MARKET NEWS\n{'='*65}\n{news}\n\n"

    index_table = "MARKET INDICES\n" + "-" * 40 + "\n"
    for name, data in index_data.items():
        arrow = "▲" if data['change'] > 0 else "▼"
        index_table += f"{name}: ₹{data['price']} {arrow} {data['change']} pts ({data['pct']}%)\n"
    index_table += "\n"

    portfolio_table = "PORTFOLIO SNAPSHOT\n" + "=" * 65 + "\n"
    portfolio_table += f"{'Stock':<12} {'Price':>8} {'Today':>8} {'Overall':>9} {'Alert'}\n"
    portfolio_table += "-" * 65 + "\n"
    for stock, data in portfolio_data.items():
        if data['price'] == 'N/A':
            continue
        arrow = "▲" if data['day_change'] > 0 else "▼"
        alert = data['alert'] if data['alert'] else ""
        portfolio_table += f"{stock:<12} ₹{data['price']:>7} {arrow}{data['day_pct']:>+6.2f}% {data['total_pct']:>+8.2f}%  {alert}\n"
    portfolio_table += "=" * 65 + "\n"

    if summary_type == "open":
        full_email = f"{news_section}{index_table}{portfolio_table}\nAI STOCK SUMMARY — Most Urgent to Least\n{'='*65}\n{ai_summary}"
    else:
        full_email = f"{index_table}{portfolio_table}\n{news_section}\nAI STOCK SUMMARY — Most Urgent to Least\n{'='*65}\n{ai_summary}"

    subject = f"{'🌅 Market Open' if summary_type == 'open' else '🌆 Market Close'} Summary — {datetime.now().strftime('%d %B %Y')}"
    send_email(subject, full_email)


if __name__ == "__main__":
    summary_type = sys.argv[1] if len(sys.argv) > 1 else "open"
    if summary_type not in ["open", "close"]:
        print("Usage: python3 market_summary.py open")
        print("   or: python3 market_summary.py close")
        sys.exit(1)
    build_summary(summary_type)
