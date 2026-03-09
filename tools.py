from duckduckgo_search import DDGS
from datetime import datetime
import json, os, requests, random

def search_web(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        return "\n\n".join([f"{r['title']}\n{r['body']}" for r in results])
    except Exception as e:
        return f"Search error: {e}"

def get_current_time():
    return datetime.now().strftime("%d %B %Y, %H:%M:%S")

def save_note(title, content):
    notes_file = "notes.json"
    notes = {}
    if os.path.exists(notes_file):
        with open(notes_file, "r", encoding="utf-8") as f:
            notes = json.load(f)
    notes[title] = {"content": content, "date": get_current_time()}
    with open(notes_file, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)
    return f"Note saved: '{title}'"

def read_notes():
    notes_file = "notes.json"
    if not os.path.exists(notes_file):
        return "No notes saved yet."
    with open(notes_file, "r", encoding="utf-8") as f:
        notes = json.load(f)
    return "\n\n".join([f"📌 {k} ({v['date']})\n{v['content']}" for k, v in notes.items()])

def parse_weather(text):
    return text

def get_weather(city="Istanbul"):
    try:
        url = f"https://wttr.in/{city}?format=City:+%l,+Condition:+%C,+Temp:+%t,+Feels+like:+%f,+Humidity:+%h"
        response = requests.get(url, timeout=5)
        return parse_weather(response.text.strip())
    except Exception as e:
        return f"Weather error: {e}"

def get_weather_by_coords(lat, lon):
    try:
        url = f"https://wttr.in/{lat},{lon}?format=City:+%l,+Condition:+%C,+Temp:+%t,+Feels+like:+%f,+Humidity:+%h"
        response = requests.get(url, timeout=5)
        return parse_weather(response.text.strip())
    except Exception as e:
        return f"Weather error: {e}"

def get_news():
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news("world news today", max_results=5))
        return "Today's news:\n\n" + "\n\n".join([f"• {r['title']}" for r in results])
    except Exception as e:
        return f"News error: {e}"

def osint_ip(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = response.json()
        if data["status"] == "success":
            return (
                f"IP: {data.get('query')}\n"
                f"Country: {data.get('country')}\n"
                f"City: {data.get('city')}\n"
                f"Region: {data.get('regionName')}\n"
                f"ISP: {data.get('isp')}\n"
                f"Org: {data.get('org')}\n"
                f"Coordinates: {data.get('lat')}, {data.get('lon')}\n"
                f"Timezone: {data.get('timezone')}\n"
                f"Zip: {data.get('zip')}"
            )
        return "IP info not found."
    except Exception as e:
        return f"IP query error: {e}"

def osint_domain(domain):
    try:
        # WHOIS via iana
        whois_response = requests.get(f"https://www.whois.com/whois/{domain}", timeout=5)
        # DNS lookup
        dns_response = requests.get(f"https://dns.google/resolve?name={domain}&type=A", timeout=5)
        dns_data = dns_response.json()
        ips = [a['data'] for a in dns_data.get('Answer', [])] if 'Answer' in dns_data else []
        
        result = f"Domain: {domain}\n"
        if ips:
            result += f"IP Addresses: {', '.join(ips)}\n"
            # Get info about first IP
            if ips:
                ip_info = requests.get(f"http://ip-api.com/json/{ips[0]}", timeout=5).json()
                result += f"Server Country: {ip_info.get('country', 'Unknown')}\n"
                result += f"Server ISP: {ip_info.get('isp', 'Unknown')}\n"
                result += f"Server Org: {ip_info.get('org', 'Unknown')}"
        return result
    except Exception as e:
        return f"Domain query error: {e}"

def osint_phone(phone):
    try:
        # numverify free tier
        response = requests.get(
            f"http://apilayer.net/api/validate?access_key=free&number={phone}&country_code=&format=1",
            timeout=5
        )
        data = response.json()
        return (
            f"Phone: {phone}\n"
            f"Valid: {'Yes' if data.get('valid') else 'No'}\n"
            f"Country: {data.get('country_name', 'Unknown')}\n"
            f"Carrier: {data.get('carrier', 'Unknown')}\n"
            f"Line type: {data.get('line_type', 'Unknown')}\n"
            f"International format: {data.get('international_format', phone)}"
        )
    except Exception as e:
        return f"Phone query error: {e}"

def osint_breach(email):
    try:
        headers = {
            "User-Agent": "Asena-OSINT-Bot",
            "hibp-api-key": "free"
        }
        response = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}?truncateResponse=false",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            breaches = response.json()
            names = [b['Name'] for b in breaches]
            return f"⚠️ {email} found in {len(names)} breaches:\n" + "\n".join([f"• {n}" for n in names])
        elif response.status_code == 404:
            return f"✅ Good news! {email} was not found in any known data breaches."
        return f"Could not check. Status: {response.status_code}"
    except Exception as e:
        return f"Breach check error: {e}"

def osint_username(username):
    try:
        platforms = {
            "Twitter": f"https://twitter.com/{username}",
            "Instagram": f"https://instagram.com/{username}",
            "GitHub": f"https://github.com/{username}",
            "Reddit": f"https://reddit.com/user/{username}",
            "TikTok": f"https://tiktok.com/@{username}",
            "LinkedIn": f"https://linkedin.com/in/{username}",
            "Pinterest": f"https://pinterest.com/{username}",
            "Twitch": f"https://twitch.tv/{username}",
            "YouTube": f"https://youtube.com/@{username}",
            "Spotify": f"https://open.spotify.com/user/{username}",
        }
        found = []
        for platform, url in platforms.items():
            try:
                r = requests.get(url, timeout=3, allow_redirects=True)
                if r.status_code == 200:
                    found.append(f"✅ {platform}: {url}")
                else:
                    found.append(f"❌ {platform}: Not found")
            except:
                found.append(f"⚠️ {platform}: Could not check")
        
        return f"Username search for '{username}':\n\n" + "\n".join(found)
    except Exception as e:
        return f"Username search error: {e}"

def osint_email(email):
    try:
        # Email validation and info
        response = requests.get(f"https://api.mailcheck.ai/email/{email}", timeout=5)
        data = response.json()
        return (
            f"Email: {email}\n"
            f"Valid: {'Yes' if data.get('valid') else 'No'}\n"
            f"Disposable: {'Yes' if data.get('disposable') else 'No'}\n"
            f"Domain: {data.get('domain', 'Unknown')}\n"
            f"MX Records: {'Yes' if data.get('mx') else 'No'}"
        )
    except Exception as e:
        return f"Email check error: {e}"

def fake_profile():
    import random, string
    name = random.choice(["Emma","Olivia","Sophia","Ava","Mia"]) + " " + random.choice(["Smith","Johnson","Davis","Wilson","Moore"])
    age = random.randint(20, 45)
    email = name.lower().replace(" ", ".") + str(random.randint(1,999)) + "@gmail.com"
    phone = f"+1{random.randint(2000000000, 9999999999)}"
    return f"Name: {name}\nAge: {age}\nEmail: {email}\nPhone: {phone}"
