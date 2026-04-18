import cloudscraper
from bs4 import BeautifulSoup
import requests
import time

# معلوماتك الشخصية (ممنوع الخطأ)
TOKEN = "8642375967:AAF06Pr2xdZeY1zB3joWd1Q0NweebezJEhY"
CHAT_ID = "7816097184"

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def track_all_sports():
    scraper = cloudscraper.create_scraper()
    sports = {
        "كرة القدم": "https://www.arbworld.net/en/money-drop/football",
        "كرة السلة": "https://www.arbworld.net/en/money-drop/basketball",
        "التنس": "https://www.arbworld.net/en/money-drop/tennis"
    }
    
    found_any = False
    for sport_name, url in sports.items():
        try:
            response = scraper.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'items'})
            if not table: continue

            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 5: continue
                
                match_name = cols[1].text.strip()
                market = cols[2].text.strip()
                amount_str = cols[3].text.strip().replace('$', '').replace(',', '')
                percent_str = cols[4].text.strip().replace('%', '')

                try:
                    amount = float(amount_str)
                    percentage = float(percent_str)
                except: continue

                # الفلتر القاسي (المضمون): مبلغ فوق 100k وسيولة فوق 90%
                if amount >= 100000 and percentage >= 90:
                    msg = (
                        f"🚨 *إشارة ذكية - {sport_name}*\n\n"
                        f"🏟️ الماتش: {match_name}\n"
                        f"🎯 التوقع: {market}\n"
                        f"💰 السيولة: ${amount:,.0f}\n"
                        f"📊 النسبة: {percentage}%\n\n"
                        f"✅ *مضمونة:* العب Double Chance (فوز أو تعادل)"
                    )
                    send_telegram_msg(msg)
                    found_any = True
        except:
            continue
    return found_any

if __name__ == "__main__":
    track_all_sports()
          
