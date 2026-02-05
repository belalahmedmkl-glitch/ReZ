import time
import requests
import json
import re
import os
import hashlib
import concurrent.futures
from datetime import datetime, date, timedelta
from pathlib import Path
import sqlite3
import telebot
from telebot import types
import threading
import random
import traceback

# ======================
# 🔐 إعدادات API (من الملف الأول)
# ======================
API_URL = "http://51.77.216.195/crapi/dgroup/viewstats"
API_TOKEN = "QlJSRTRSQmJ_g2F1houCR19Rj1Z2aIpafG2QiUZUlkdYY3dbapV4"

# ======================
# 🔗 إعدادات البوت (من الملف الثاني)
# ======================
BOT_TOKEN = "8336904025:AAEo6o696ij2CbE4bx00kfyA4SUYG4rYaFQ"
CHAT_IDS = ["-1003551242784"]
REFRESH_INTERVAL = 0.2  # ⚡ سرعة قصوى - 0.2 ثانية فقط
ADMIN_IDS = [7966354929, 7645594609, 7946718662, 8231420847]
DB_PATH = "bot.db"
DELETE_MESSAGES_AFTER = 300  # 5 دقائق

print(f"[INIT] 🔑 API Token: {API_TOKEN[:10]}...")
print(f"[INIT] 🤖 Bot Token: {BOT_TOKEN[:10]}...")
print(f"[INIT] 👥 Admins: {len(ADMIN_IDS)}")
print(f"[INIT] ⚡⚡⚡ سرعة التحديث القصوى: {REFRESH_INTERVAL} ثانية")
print(f"[INIT] ⏱️ Auto Delete: {DELETE_MESSAGES_AFTER//60} minutes")

# ======================
# 🚀 ذاكرة تخزين مؤقت جديدة
# ======================
sent_messages_cache = {}
CACHE_CLEAN_INTERVAL = 60
last_cache_clean = time.time()

def cleanup_cache():
    global sent_messages_cache, last_cache_clean
    current_time = time.time()
    if current_time - last_cache_clean > CACHE_CLEAN_INTERVAL:
        ten_minutes_ago = current_time - 600
        to_delete = [k for k, v in sent_messages_cache.items() if v < ten_minutes_ago]
        for key in to_delete:
            del sent_messages_cache[key]
        last_cache_clean = current_time

def add_to_cache(message_key):
    sent_messages_cache[message_key] = time.time()
    if len(sent_messages_cache) > 1000:
        oldest_keys = sorted(sent_messages_cache.items(), key=lambda x: x[1])[:200]
        for key, _ in oldest_keys:
            del sent_messages_cache[key]

def is_in_cache(message_key):
    return message_key in sent_messages_cache

# ======================
# 🌍 أكواد الدول (من الملف الثاني)
# ======================
COUNTRY_CODES = {
    "1": ("USA/Canada", "🇺🇸", "US"),
    "7": ("Russia", "🇷🇺", "RU"),
    "20": ("Egypt", "🇪🇬", "EG"),
    "27": ("South Africa", "🇿🇦", "ZA"),
    "30": ("Greece", "🇬🇷", "GR"),
    "31": ("Netherlands", "🇳🇱", "NL"),
    "32": ("Belgium", "🇧🇪", "BE"),
    "33": ("France", "🇫🇷", "FR"),
    "34": ("Spain", "🇪🇸", "ES"),
    "36": ("Hungary", "🇭🇺", "HU"),
    "39": ("Italy", "🇮🇹", "IT"),
    "40": ("Romania", "🇷🇴", "RO"),
    "41": ("Switzerland", "🇨🇭", "CH"),
    "43": ("Austria", "🇦🇹", "AT"),
    "44": ("United Kingdom", "🇬🇧", "UK"),
    "45": ("Denmark", "🇩🇰", "DK"),
    "46": ("Sweden", "🇸🇪", "SE"),
    "47": ("Norway", "🇳🇴", "NO"),
    "48": ("Poland", "🇵🇱", "PL"),
    "49": ("Germany", "🇩🇪", "DE"),
    "51": ("Peru", "🇵🇪", "PE"),
    "52": ("Mexico", "🇲🇽", "MX"),
    "53": ("Cuba", "🇨🇺", "CU"),
    "54": ("Argentina", "🇦🇷", "AR"),
    "55": ("Brazil", "🇧🇷", "BR"),
    "56": ("Chile", "🇨🇱", "CL"),
    "57": ("Colombia", "🇨🇴", "CO"),
    "58": ("Venezuela", "🇻🇪", "VE"),
    "60": ("Malaysia", "🇲🇾", "MY"),
    "61": ("Australia", "🇦🇺", "AU"),
    "62": ("Indonesia", "🇮🇩", "ID"),
    "63": ("Philippines", "🇵🇭", "PH"),
    "64": ("New Zealand", "🇳🇿", "NZ"),
    "65": ("Singapore", "🇸🇬", "SG"),
    "66": ("Thailand", "🇹🇭", "TH"),
    "81": ("Japan", "🇯🇵", "JP"),
    "82": ("South Korea", "🇰🇷", "KR"),
    "84": ("Vietnam", "🇻🇳", "VN"),
    "86": ("China", "🇨🇳", "CN"),
    "90": ("Turkey", "🇹🇷", "TR"),
    "91": ("India", "🇮🇳", "IN"),
    "92": ("Pakistan", "🇵🇰", "PK"),
    "93": ("Afghanistan", "🇦🇫", "AF"),
    "94": ("Sri Lanka", "🇱🇰", "LK"),
    "95": ("Myanmar", "🇲🇲", "MM"),
    "98": ("Iran", "🇮🇷", "IR"),
    "211": ("South Sudan", "🇸🇸", "SS"),
    "212": ("Morocco", "🇲🇦", "MA"),
    "213": ("Algeria", "🇩🇿", "DZ"),
    "216": ("Tunisia", "🇹🇳", "TN"),
    "218": ("Libya", "🇱🇾", "LY"),
    "220": ("Gambia", "🇬🇲", "GM"),
    "221": ("Senegal", "🇸🇳", "SN"),
    "222": ("Mauritania", "🇲🇷", "MR"),
    "223": ("Mali", "🇲🇱", "ML"),
    "224": ("Guinea", "🇬🇳", "GN"),
    "225": ("Ivory Coast", "🇨🇮", "CI"),
    "226": ("Burkina Faso", "🇧🇫", "BF"),
    "227": ("Niger", "🇳🇪", "NE"),
    "228": ("Togo", "🇹🇬", "TG"),
    "229": ("Benin", "🇧🇯", "BJ"),
    "230": ("Mauritius", "🇲🇺", "MU"),
    "231": ("Liberia", "🇱🇷", "LR"),
    "232": ("Sierra Leone", "🇸🇱", "SL"),
    "233": ("Ghana", "🇬🇭", "GH"),
    "234": ("Nigeria", "🇳🇬", "NG"),
    "235": ("Chad", "🇹🇩", "TD"),
    "236": ("Central African Rep", "🇨🇫", "CF"),
    "237": ("Cameroon", "🇨🇲", "CM"),
    "238": ("Cape Verde", "🇨🇻", "CV"),
    "239": ("Sao Tome", "🇸🇹", "ST"),
    "240": ("Equatorial Guinea", "🇬🇶", "GQ"),
    "241": ("Gabon", "🇬🇦", "GA"),
    "242": ("Congo", "🇨🇬", "CG"),
    "243": ("DR Congo", "🇨🇩", "CD"),
    "244": ("Angola", "🇦🇴", "AO"),
    "245": ("Guinea-Bissau", "🇬🇼", "GW"),
    "248": ("Seychelles", "🇸🇨", "SC"),
    "249": ("Sudan", "🇸🇩", "SD"),
    "250": ("Rwanda", "🇷🇼", "RW"),
    "251": ("Ethiopia", "🇪🇹", "ET"),
    "252": ("Somalia", "🇸🇴", "SO"),
    "253": ("Djibouti", "🇩🇯", "DJ"),
    "254": ("Kenya", "🇰🇪", "KE"),
    "255": ("Tanzania", "🇹🇿", "TZ"),
    "256": ("Uganda", "🇺🇬", "UG"),
    "257": ("Burundi", "🇧🇮", "BI"),
    "258": ("Mozambique", "🇲🇿", "MZ"),
    "260": ("Zambia", "🇿🇲", "ZM"),
    "261": ("Madagascar", "🇲🇬", "MG"),
    "262": ("Reunion", "🇷🇪", "RE"),
    "263": ("Zimbabwe", "🇿🇼", "ZW"),
    "264": ("Namibia", "🇳🇦", "NA"),
    "265": ("Malawi", "🇲🇼", "MW"),
    "266": ("Lesotho", "🇱🇸", "LS"),
    "267": ("Botswana", "🇧🇼", "BW"),
    "268": ("Eswatini", "🇸🇿", "SZ"),
    "269": ("Comoros", "🇰🇲", "KM"),
    "350": ("Gibraltar", "🇬🇮", "GI"),
    "351": ("Portugal", "🇵🇹", "PT"),
    "352": ("Luxembourg", "🇱🇺", "LU"),
    "353": ("Ireland", "🇮🇪", "IE"),
    "354": ("Iceland", "🇮🇸", "IS"),
    "355": ("Albania", "🇦🇱", "AL"),
    "356": ("Malta", "🇲🇹", "MT"),
    "357": ("Cyprus", "🇨🇾", "CY"),
    "358": ("Finland", "🇫🇮", "FI"),
    "359": ("Bulgaria", "🇧🇬", "BG"),
    "370": ("Lithuania", "🇱🇹", "LT"),
    "371": ("Latvia", "🇱🇻", "LV"),
    "372": ("Estonia", "🇪🇪", "EE"),
    "373": ("Moldova", "🇲🇩", "MD"),
    "374": ("Armenia", "🇦🇲", "AM"),
    "375": ("Belarus", "🇧🇾", "BY"),
    "376": ("Andorra", "🇦🇩", "AD"),
    "377": ("Monaco", "🇲🇨", "MC"),
    "378": ("San Marino", "🇸🇲", "SM"),
    "380": ("Ukraine", "🇺🇦", "UA"),
    "381": ("Serbia", "🇷🇸", "RS"),
    "382": ("Montenegro", "🇲🇪", "ME"),
    "383": ("Kosovo", "🇽🇰", "XK"),
    "385": ("Croatia", "🇭🇷", "HR"),
    "386": ("Slovenia", "🇸🇮", "SI"),
    "387": ("Bosnia", "🇧🇦", "BA"),
    "389": ("North Macedonia", "🇲🇰", "MK"),
    "420": ("Czech Republic", "🇨🇿", "CZ"),
    "421": ("Slovakia", "🇸🇰", "SK"),
    "423": ("Liechtenstein", "🇱🇮", "LI"),
    "500": ("Falkland Islands", "🇫🇰", "FK"),
    "501": ("Belize", "🇧🇿", "BZ"),
    "502": ("Guatemala", "🇬🇹", "GT"),
    "503": ("El Salvador", "🇸🇻", "SV"),
    "504": ("Honduras", "🇭🇳", "HN"),
    "505": ("Nicaragua", "🇳🇮", "NI"),
    "506": ("Costa Rica", "🇨🇷", "CR"),
    "507": ("Panama", "🇵🇦", "PA"),
    "509": ("Haiti", "🇭🇹", "HT"),
    "591": ("Bolivia", "🇧🇴", "BO"),
    "592": ("Guyana", "🇬🇾", "GY"),
    "593": ("Ecuador", "🇪🇨", "EC"),
    "595": ("Paraguay", "🇵🇾", "PY"),
    "597": ("Suriname", "🇸🇷", "SR"),
    "598": ("Uruguay", "🇺🇾", "UY"),
    "670": ("Timor-Leste", "🇹🇱", "TL"),
    "673": ("Brunei", "🇧🇳", "BN"),
    "674": ("Nauru", "🇳🇷", "NR"),
    "675": ("Papua New Guinea", "🇵🇬", "PG"),
    "676": ("Tonga", "🇹🇴", "TO"),
    "677": ("Solomon Islands", "🇸🇧", "SB"),
    "678": ("Vanuatu", "🇻🇺", "VU"),
    "679": ("Fiji", "🇫🇯", "FJ"),
    "680": ("Palau", "🇵🇼", "PW"),
    "685": ("Samoa", "🇼🇸", "WS"),
    "686": ("Kiribati", "🇰🇮", "KI"),
    "687": ("New Caledonia", "🇳🇨", "NC"),
    "688": ("Tuvalu", "🇹🇻", "TV"),
    "689": ("French Polynesia", "🇵🇫", "PF"),
    "691": ("Micronesia", "🇫🇲", "FM"),
    "692": ("Marshall Islands", "🇲🇭", "MH"),
    "850": ("North Korea", "🇰🇵", "KP"),
    "852": ("Hong Kong", "🇭🇰", "HK"),
    "853": ("Macau", "🇲🇴", "MO"),
    "855": ("Cambodia", "🇰🇭", "KH"),
    "856": ("Laos", "🇱🇦", "LA"),
    "960": ("Maldives", "🇲🇻", "MV"),
    "961": ("Lebanon", "🇱🇧", "LB"),
    "962": ("Jordan", "🇯🇴", "JO"),
    "963": ("Syria", "🇸🇾", "SY"),
    "964": ("Iraq", "🇮🇶", "IQ"),
    "965": ("Kuwait", "🇰🇼", "KW"),
    "966": ("Saudi Arabia", "🇸🇦", "SA"),
    "967": ("Yemen", "🇾🇪", "YE"),
    "968": ("Oman", "🇴🇲", "OM"),
    "970": ("Palestine", "🇵🇸", "PS"),
    "971": ("UAE", "🇦🇪", "AE"),
    "972": ("Israel", "🇮🇱", "IL"),
    "973": ("Bahrain", "🇧🇭", "BH"),
    "974": ("Qatar", "🇶🇦", "QA"),
    "975": ("Bhutan", "🇧🇹", "BT"),
    "976": ("Mongolia", "🇲🇳", "MN"),
    "977": ("Nepal", "🇳🇵", "NP"),
    "992": ("Tajikistan", "🇹🇯", "TJ"),
    "993": ("Turkmenistan", "🇹🇲", "TM"),
    "994": ("Azerbaijan", "🇦🇿", "AZ"),
    "995": ("Georgia", "🇬🇪", "GE"),
    "996": ("Kyrgyzstan", "🇰🇬", "KG"),
    "998": ("Uzbekistan", "🇺🇿", "UZ"),
}

# ======================
# 🗄️ دوال قاعدة البيانات
# ======================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            country_code TEXT,
            assigned_number TEXT,
            is_banned INTEGER DEFAULT 0,
            private_combo_country TEXT DEFAULT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS combos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT UNIQUE,
            numbers TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS otp_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT,
            otp TEXT,
            full_message TEXT,
            timestamp TEXT,
            assigned_to INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS private_combos (
            user_id INTEGER,
            country_code TEXT,
            numbers TEXT,
            PRIMARY KEY (user_id, country_code)
        )
    ''')
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('delete_after_seconds', '300')")
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('delete_messages_enabled', '1')")
    conn.commit()
    conn.close()

init_db()

def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def save_user(user_id, username="", first_name="", last_name="", country_code=None, assigned_number=None, private_combo_country=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    existing_data = get_user(user_id)
    if existing_data:
        if country_code is None:
            country_code = existing_data[4]
        if assigned_number is None:
            assigned_number = existing_data[5]
        if private_combo_country is None:
            private_combo_country = existing_data[7]

    c.execute("""
        REPLACE INTO users (user_id, username, first_name, last_name, country_code, assigned_number, is_banned, private_combo_country)
        VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT is_banned FROM users WHERE user_id=?), 0), ?)
    """, (
        user_id,
        username,
        first_name,
        last_name,
        country_code,
        assigned_number,
        user_id,
        private_combo_country
    ))
    conn.commit()
    conn.close()

def ban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id):
    user = get_user(user_id)
    return user and user[6] == 1

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE is_banned=0")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_combo(country_code, user_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        c.execute("SELECT numbers FROM private_combos WHERE user_id=? AND country_code=?", (user_id, country_code))
        row = c.fetchone()
        if row:
            conn.close()
            return json.loads(row[0])
    c.execute("SELECT numbers FROM combos WHERE country_code=?", (country_code,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def save_combo(country_code, numbers, user_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        c.execute("REPLACE INTO private_combos (user_id, country_code, numbers) VALUES (?, ?, ?)",
                  (user_id, country_code, json.dumps(numbers)))
    else:
        c.execute("REPLACE INTO combos (country_code, numbers) VALUES (?, ?)",
                  (country_code, json.dumps(numbers)))
    conn.commit()
    conn.close()

def delete_combo(country_code, user_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        c.execute("DELETE FROM private_combos WHERE user_id=? AND country_code=?", (user_id, country_code))
    else:
        c.execute("DELETE FROM combos WHERE country_code=?", (country_code,))
    conn.commit()
    conn.close()

def get_all_combos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT country_code FROM combos")
    combos = [row[0] for row in c.fetchall()]
    conn.close()
    return combos

def assign_number_to_user(user_id, number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET assigned_number=? WHERE user_id=?", (number, user_id))
    conn.commit()
    conn.close()

def get_user_by_number(number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE assigned_number=?", (number,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def log_otp(number, otp, full_message, assigned_to=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO otp_logs (number, otp, full_message, timestamp, assigned_to) VALUES (?, ?, ?, ?, ?)",
              (number, otp, full_message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), assigned_to))
    conn.commit()
    conn.close()

def release_number(old_number):
    if not old_number:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET assigned_number=NULL WHERE assigned_number=?", (old_number,))
    conn.commit()
    conn.close()

def get_otp_logs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM otp_logs")
    logs = c.fetchall()
    conn.close()
    return logs

def get_available_numbers(country_code, user_id=None):
    all_numbers = get_combo(country_code, user_id)
    if not all_numbers:
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT assigned_number FROM users WHERE assigned_number IS NOT NULL AND assigned_number != ''")
    used_numbers = set(row[0] for row in c.fetchall())
    conn.close()
    available = [num for num in all_numbers if num not in used_numbers]
    return available

# ======================
# 🤖 إنشاء بوت Telegram
# ======================
bot = telebot.TeleBot(BOT_TOKEN)

# ======================
# 🔄 API Class (محسنة للسرعة)
# ======================
class CRAPI:
    """فئة للتعامل مع CR API مع تحسينات السرعة"""
    
    def __init__(self):
        self.api_url = API_URL
        self.api_token = API_TOKEN
        self.session = requests.Session()
        self.session.timeout = 5  # ⚡ وقت أقل للاتصال
        self.connection_errors = 0
        self.last_connection_test = 0
        
    def fetch_messages(self, records=150, hours_back=0.08):  # ⚡ زيادة العدد وتقليل الوقت
        """جلب الرسائل من API"""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)  # ⚡ 5 دقائق فقط
            
            dt1 = start_time.strftime("%Y-%m-%d %H:%M:%S")
            dt2 = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            params = {
                'token': self.api_token,
                'dt1': dt1,
                'dt2': dt2,
                'records': records
            }
            
            response = self.session.get(self.api_url, params=params, timeout=8)  # ⚡ وقت أقل
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    self.connection_errors = 0
                    return data.get('data', [])
                else:
                    self.connection_errors += 1
            else:
                self.connection_errors += 1
                
            return []
            
        except Exception as e:
            self.connection_errors += 1
            print(f"[API] ❌ خطأ في جلب البيانات: {e}")
            return []
    
    def check_token_valid(self):
        """التحقق من صحة التوكن"""
        try:
            params = {'token': self.api_token, 'records': 1}
            response = self.session.get(self.api_url, params=params, timeout=5)  # ⚡ وقت أقل
            if response.status_code == 200:
                data = response.json()
                status = data.get('status') != 'error'
                self.last_connection_test = time.time()
                return status
            return False
        except Exception as e:
            print(f"[API] ❌ خطأ في التحقق: {e}")
            return False
    
    def force_reconnect(self):
        """إعادة الاتصال القسري بالـ API"""
        try:
            print("[API] 🔄 محاولة إعادة الاتصال القسري...")
            # إنشاء session جديد
            self.session = requests.Session()
            self.session.timeout = 5  # ⚡ وقت أقل
            self.connection_errors = 0
            
            # اختبار الاتصال
            success = self.check_token_valid()
            
            if success:
                print("[API] ✅ إعادة الاتصال ناجحة")
                return True, "✅ تم إعادة الاتصال بنجاح"
            else:
                print("[API] ❌ فشل إعادة الاتصال")
                return False, "❌ فشل إعادة الاتصال - تأكد من صحة التوكن"
                
        except Exception as e:
            print(f"[API] ❌ خطأ في إعادة الاتصال: {e}")
            return False, f"❌ خطأ: {str(e)}"
    
    def test_connection(self):
        """اختبار الاتصال بالـ API"""
        try:
            start_time = time.time()
            params = {'token': self.api_token, 'records': 1}
            response = self.session.get(self.api_url, params=params, timeout=5)  # ⚡ وقت أقل
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return True, f"✅ الاتصال نشط\n⏱️ وقت الاستجابة: {response_time}ms"
                else:
                    return False, f"❌ الرد غير متوقع\n⏱️ وقت الاستجابة: {response_time}ms"
            else:
                return False, f"❌ كود الخطأ: {response.status_code}\n⏱️ وقت الاستجابة: {response_time}ms"
                
        except Exception as e:
            return False, f"❌ خطأ في الاتصال: {str(e)}"

crapi = CRAPI()

# ======================
# 🗑️ نظام حذف الرسائل
# ======================
messages_to_delete = []

def delete_old_messages():
    """حذف الرسائل القديمة تلقائياً"""
    while True:
        try:
            delete_enabled = get_setting('delete_messages_enabled') == '1'
            if not delete_enabled:
                time.sleep(60)
                continue
                
            current_time = datetime.now()
            to_delete = []
            delete_after_seconds = int(get_setting('delete_after_seconds') or 300)
            
            for msg in messages_to_delete:
                if current_time >= msg['delete_time']:
                    to_delete.append(msg)
            
            for msg in to_delete:
                try:
                    bot.delete_message(msg['chat_id'], msg['message_id'])
                    print(f"[🗑️] تم حذف الرسالة {msg['message_id']} من الجروب {msg['chat_id']}")
                    messages_to_delete.remove(msg)
                except Exception as e:
                    print(f"[❌] فشل حذف الرسالة {msg['message_id']}: {e}")
                    if msg in messages_to_delete:
                        messages_to_delete.remove(msg)
            
            time.sleep(60)
            
        except Exception as e:
            print(f"[❌] خطأ في وظيفة حذف الرسائل: {e}")
            time.sleep(60)

# ======================
# 📨 دوال الإرسال والتحويل (محسنة من الملف الثاني)
# ======================
def get_country_info(number):
    number = number.strip().replace("+", "").replace(" ", "").replace("-", "")
    for code, (name, flag, upper_name) in COUNTRY_CODES.items():
        if number.startswith(code):
            return name, flag, upper_name
    return "Unknown", "🌍", "UN"

def mask_number(number):
    number = number.strip()
    if len(number) > 8:
        return number[:4] + "⁦⁦•••" + number[-4:]
    return number

def extract_otp(message):
    patterns = [
        r'(?:code|رمز|كود|verification|تحقق|otp|pin)[:\s]+[‎]?(\d{3,8}(?:[- ]\d{3,4})?)',
        r'(\d{3})[- ](\d{3,4})',
        r'\b(\d{4,8})\b',
        r'[‎](\d{3,8})',
    ]
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if len(match.groups()) > 1:
                return ''.join(match.groups())
            return match.group(1).replace(' ', '').replace('-', '')
    all_numbers = re.findall(r'\d{4,8}', message)
    if all_numbers:
        return all_numbers[0]
    return "N/A"

def detect_service(message):
    message_lower = message.lower()

    services = {
        "#WP": ["whatsapp", "واتساب", "واتس"],
        "#FB": ["facebook", "فيسبوك", "fb"],
        "#IG": ["instagram", "انستقرام", "انستا"],
        "#TG": ["telegram", "تيليجرام", "تلي"],
        "#TW": ["twitter", "تويتر", "x"],
        "#GG": ["google", "gmail", "جوجل", "جميل"],
        "#DC": ["discord", "ديسكورد"],
        "#LN": ["line", "لاين"],
        "#VB": ["viber", "فايبر"],
        "#SK": ["skype", "سكايب"],
        "#SC": ["snapchat", "سناب"],
        "#TT": ["tiktok", "تيك توك", "تيك"],
        "#AMZ": ["amazon", "امازون"],
        "#APL": ["apple", "ابل", "icloud"],
        "#MS": ["microsoft", "مايكروسوفت"],
        "#IN": ["linkedin", "لينكد"],
        "#UB": ["uber", "اوبر"],
        "#AB": ["airbnb", "ايربنب"],
        "#NF": ["netflix", "نتفلكس"],
        "#SP": ["spotify", "سبوتيفاي"],
        "#YT": ["youtube", "يوتيوب"],
        "#GH": ["github", "جيت هاب"],
        "#PT": ["pinterest", "بنتريست"],
        "#PP": ["paypal", "باي بال"],
        "#BK": ["booking", "بوكينج"],
        "#TL": ["tala", "تالا"],
        "#OLX": ["olx", "اوليكس"],
        "#STC": ["stcpay", "stc"],
    }

    for service_code, keywords in services.items():
        for keyword in keywords:
            if keyword in message_lower:
                return service_code

    if "code" in message_lower or "verification" in message_lower:
        if "telegram" in message_lower:
            return "#TG"
        if "whatsapp" in message_lower:
            return "#WP"
        if "facebook" in message_lower:
            return "#FB"
        if "instagram" in message_lower:
            return "#IG"
        if "google" in message_lower or "gmail" in message_lower:
            return "#GG"
        if "twitter" in message_lower or "x.com" in message_lower:
            return "#TW"

    return "Unknown"

def html_escape(text):
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def format_message(date_str, number, sms):
    """تنسيق الرسالة (معدلة من الملف الثاني)"""
    country_name, country_flag, country_code = get_country_info(number)
    masked_num = mask_number(number)
    otp_code = extract_otp(sms)
    service = detect_service(sms)

    # النص المنسق من الملف الثاني
    message = (
        f"\n"
        f" {country_flag} #{country_code} [{service}] {masked_num} \n"
        f""
    )
    return message

def send_telegram_with_delete(text, otp_code, full_sms=""):
    """إرسال الرسالة (معدلة من الملف الثاني)"""
    try:
        keyboard = {
            "inline_keyboard": [
                [{"text": f"Click to Copy Code: {otp_code}", "copy_text": {"text": str(otp_code)}}],
                [{"text": "📋 Full Message", "copy_text": {"text": full_sms}}] if full_sms else [],
                [
                    {"text": "Explanation Channel", "url": "https://t.me/OV201"},
                    {"text": "🤖 Bot Panel", "url": "https://t.me/Rez_num_bot"}
                ],
                [{"text": "💬 Channel ", "url": "https://t.me/OV20000"}]
            ]
        }

        success_count = 0
        message_ids = []
        delete_after_seconds = int(get_setting('delete_after_seconds') or 300)
        delete_enabled = get_setting('delete_messages_enabled') == '1'
        
        for chat_id in CHAT_IDS:
            try:
                response = requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "reply_markup": json.dumps(keyboard)
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("ok") and "result" in response_data:
                        message_id = response_data["result"]["message_id"]
                        message_ids.append((chat_id, message_id))
                        
                        if delete_enabled and delete_after_seconds > 0:
                            delete_time = datetime.now() + timedelta(seconds=delete_after_seconds)
                            messages_to_delete.append({
                                'chat_id': chat_id,
                                'message_id': message_id,
                                'delete_time': delete_time
                            })
                        success_count += 1
                else:
                    print(f"[!] فشل إرسال إلى {chat_id}: {response.status_code}")
            except Exception as e:
                print(f"[!] خطأ Telegram لـ {chat_id}: {e}")
        
        return success_count > 0, message_ids
        
    except Exception as e:
        print(f"خطأ في إعداد الرسالة: {e}")
        return False, []

def send_otp_to_user_and_group(date_str, number, sms):
    """إرسال OTP للمستخدم والجروب (من الملف الثاني)"""
    try:
        time.sleep(random.uniform(0.5, 1.5))

        otp_code = extract_otp(sms)
        country_name, country_flag, country_code = get_country_info(number)
        service = detect_service(sms)

        try:
            user_id = get_user_by_number(number)
            log_otp(number, otp_code, sms, user_id)
        except:
            user_id = None

        if user_id:
            try:
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("👤 Owner", url="https://t.me/OV20000"),
                    types.InlineKeyboardButton("📢 Channel", url="https://t.me/OV2001")
                )
                bot.send_message(
                    user_id,
                    (f"<b><u>✨ 𝙋𝙍𝙄𝙈𝙀 𝙊𝙏𝙋 𝙃𝙐𝘽 OTP Received ✨</u></b>\n\n"
                     f"🌍 <b>Country:</b> {country_name} {country_flag}\n"
                     f"⚙ <b>Service:</b> {service}\n"
                     f"☎ <b>Number:</b> <code>{number}</code>\n"
                     f"🕒 <b>Time:</b> {date_str}\n\n"
                     f"🔐 <b>Code:</b> <code>{otp_code}</code>"),
                    reply_markup=markup, parse_mode="HTML"
                )
            except Exception as e:
                if "Too Many Requests" in str(e):
                    print(f"⚠️ ضغط إرسال للمستخدم {user_id}.. سيتم التخطي للجروب")

        text = format_message(date_str, number, sms)
        
        for attempt in range(2):
            try:
                send_telegram_with_delete(text, otp_code, sms)
                print(f"✅ [SUCCESS] GROUP | {number}")
                break
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    print(f"⚠️ تليجرام مضغوط.. محاولة {attempt+1} للرقم {number} بعد 4 ثواني")
                    time.sleep(4)
                    continue
                else:
                    print(f"❌ [ERROR] GROUP | {e}")
                    break

    except Exception as e:
        print(f"⚠️ Error in sending Thread: {e}")

# ======================
# 🎯 دوال المساعدة
# ======================
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ======================
# 🎮 أوامر البوت الرئيسية
# ======================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 You are banned.")
        return
    
    if not get_user(message.from_user.id):
        for admin in ADMIN_IDS:
            try:
                caption = f"🆕 مستخدم جديد دخل البوت:\n🆔: `{message.from_user.id}`\n👤: @{message.from_user.username or 'None'}\nالاسم: {message.from_user.first_name or ''} {message.from_user.last_name or ''}"
                bot.send_message(admin, caption, parse_mode="Markdown")
            except:
                pass
    
    save_user(
        message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or ""
    )
    
    markup = types.InlineKeyboardMarkup()
    user = get_user(message.from_user.id)
    private_combo = user[7] if user else None
    all_combos = get_all_combos()
    
    if private_combo and private_combo in COUNTRY_CODES:
        name, flag, _ = COUNTRY_CODES[private_combo]
        markup.add(types.InlineKeyboardButton(f"{flag} {name} (Private)", callback_data=f"country_{private_combo}"))

    for code in all_combos:
        if code in COUNTRY_CODES and code != private_combo:
            name, flag, _ = COUNTRY_CODES[code]
            markup.add(types.InlineKeyboardButton(f"{flag} {name}", callback_data=f"country_{code}"))

    if is_admin(message.from_user.id):
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))

    bot.send_message(message.chat.id, "🌍 Select your country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_selection(call):
    if is_banned(call.from_user.id):
        bot.answer_callback_query(call.id, "🚫 You are banned.", show_alert=True)
        return
    
    country_code = call.data.split("_", 1)[1]
    available_numbers = get_available_numbers(country_code, call.from_user.id)
    if not available_numbers:
        bot.edit_message_text("❌ جميع الأرقام قيد الاستخدام حاليًا.", call.message.chat.id, call.message.message_id)
        return
    
    assigned = random.choice(available_numbers)
    old_user = get_user(call.from_user.id)
    if old_user and old_user[5]:
        release_number(old_user[5])
    
    assign_number_to_user(call.from_user.id, assigned)
    save_user(call.from_user.id, country_code=country_code, assigned_number=assigned)
    
    name, flag, _ = COUNTRY_CODES.get(country_code, ("Unknown", "🌍", ""))
    msg_text = f"📞*Your Number From {flag} {name}* : `{assigned}`\n\n *Waiting for OTP.…🔑*\n\n_🚨 The OTP will be sent to you here_"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_num_{country_code}"))
    markup.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="back_to_countries"))
    
    bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_num_"))
def change_number(call):
    if is_banned(call.from_user.id):
        return
    
    country_code = call.data.split("_", 2)[2]
    available_numbers = get_available_numbers(country_code, call.from_user.id)
    if not available_numbers:
        bot.answer_callback_query(call.id, "❌ جميع الأرقام قيد الاستخدام.", show_alert=True)
        return
    
    old_user = get_user(call.from_user.id)
    if old_user and old_user[5]:
        release_number(old_user[5])
    
    assigned = random.choice(available_numbers)
    assign_number_to_user(call.from_user.id, assigned)
    save_user(call.from_user.id, assigned_number=assigned)
    
    name, flag, _ = COUNTRY_CODES.get(country_code, ("Unknown", "🌍", ""))
    msg_text = f"📞*Your Number From {flag} {name}* : `{assigned}`\n\n *Waiting for OTP.…🔑*\n\n_🚨 The OTP will be sent to you here_"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_num_{country_code}"))
    markup.add(types.InlineKeyboardButton("🌍 Change Country", callback_data="back_to_countries"))
    
    bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_countries")
def back_to_countries(call):
    markup = types.InlineKeyboardMarkup()
    user = get_user(call.from_user.id)
    private_combo = user[7] if user else None
    all_combos = get_all_combos()

    if private_combo and private_combo in COUNTRY_CODES:
        name, flag, _ = COUNTRY_CODES[private_combo]
        markup.add(types.InlineKeyboardButton(f"{flag} {name} (Private)", callback_data=f"country_{private_combo}"))

    for code in all_combos:
        if code in COUNTRY_CODES and code != private_combo:
            name, flag, _ = COUNTRY_CODES[code]
            markup.add(types.InlineKeyboardButton(f"{flag} {name}", callback_data=f"country_{code}"))

    if is_admin(call.from_user.id):
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🌍 Select your country:",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error editing message: {e}")
        bot.answer_callback_query(call.id)

# ======================
# 🔐 لوحة التحكم الإدارية
# ======================
user_states = {}

def admin_main_menu():
    markup = types.InlineKeyboardMarkup()
    btns = [
        types.InlineKeyboardButton("📥 Add Combo", callback_data="admin_add_combo"),
        types.InlineKeyboardButton("🗑️ Delete Combo", callback_data="admin_del_combo"),
        types.InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        types.InlineKeyboardButton("📄 Full Report", callback_data="admin_full_report"),
        types.InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ Unban User", callback_data="admin_unban"),
        types.InlineKeyboardButton("📢 Broadcast All", callback_data="admin_broadcast_all"),
        types.InlineKeyboardButton("📨 Broadcast User", callback_data="admin_broadcast_user"),
        types.InlineKeyboardButton("👤 User Info", callback_data="admin_user_info"),
        types.InlineKeyboardButton("🗑️ حذف الرسائل", callback_data="admin_delete_settings"),
        types.InlineKeyboardButton("👤 كومبو برايفت", callback_data="admin_private_combo"),
        types.InlineKeyboardButton("🔌 إتصال API", callback_data="admin_reconnect_api"),
    ]
    for i in range(0, len(btns), 2):
        markup.row(*btns[i:i+2])
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel(call):
    if not is_admin(call.from_user.id):
        return
    bot.edit_message_text("🔐 Admin Panel", call.message.chat.id, call.message.message_id, reply_markup=admin_main_menu())

# ======================
# 🔌 زر إعادة الاتصال بالـ API
# ======================
@bot.callback_query_handler(func=lambda call: call.data == "admin_reconnect_api")
def admin_reconnect_api(call):
    if not is_admin(call.from_user.id):
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 إعادة الاتصال الآن", callback_data="force_reconnect"))
    markup.add(types.InlineKeyboardButton("📊 اختبار الاتصال", callback_data="test_api_connection"))
    markup.add(types.InlineKeyboardButton("🔄 إعادة تشغيل البوت", callback_data="restart_bot"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
    
    token_valid = crapi.check_token_valid()
    api_status = "🟢 نشط" if token_valid else "🔴 غير نشط"
    
    last_test = "غير معروف"
    if crapi.last_connection_test > 0:
        elapsed = int(time.time() - crapi.last_connection_test)
        if elapsed < 60:
            last_test = f"قبل {elapsed} ثانية"
        else:
            last_test = f"قبل {elapsed//60} دقيقة"
    
    text = f"🔌 **إعدادات اتصال API**\n\n"
    text += f"📡 **الحالة الحالية:** {api_status}\n"
    text += f"⏰ **آخر اختبار:** {last_test}\n"
    text += f"❌ **أخطاء الاتصال:** {crapi.connection_errors}\n"
    text += f"🔗 **URL:** `{API_URL[:30]}...`\n"
    text += f"🔑 **Token:** `{API_TOKEN[:15]}...`\n"
    text += f"⚡ **سرعة التحديث:** {REFRESH_INTERVAL} ثانية\n\n"
    text += "استخدم الأزرار أدناه للتحكم في الاتصال:"
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "force_reconnect")
def force_reconnect(call):
    if not is_admin(call.from_user.id):
        return
    
    bot.answer_callback_query(call.id, "🔄 جاري إعادة الاتصال بالـ API...", show_alert=False)
    
    try:
        success, message = crapi.force_reconnect()
        
        if success:
            test_success, test_message = crapi.test_connection()
            
            response = f"✅ **تم إعادة الاتصال بنجاح**\n\n"
            response += f"📡 **حالة الاتصال:** {test_message}\n"
            response += f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            response += "سيبدأ البوت في استقبال الأكواد فوراً."
            
            bot.send_message(call.from_user.id, response, parse_mode="Markdown")
            
        else:
            bot.send_message(call.from_user.id, 
                           f"❌ **فشل إعادة الاتصال**\n\n{message}\n\n"
                           f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}",
                           parse_mode="Markdown")
        
        admin_reconnect_api(call)
        
    except Exception as e:
        bot.send_message(call.from_user.id, 
                       f"❌ **خطأ غير متوقع**\n\n{str(e)}",
                       parse_mode="Markdown")
        admin_reconnect_api(call)

@bot.callback_query_handler(func=lambda call: call.data == "test_api_connection")
def test_api_connection(call):
    if not is_admin(call.from_user.id):
        return
    
    bot.answer_callback_query(call.id, "📊 جاري اختبار الاتصال...", show_alert=False)
    
    try:
        success, message = crapi.test_connection()
        
        if success:
            response = f"✅ **اختبار الاتصال ناجح**\n\n"
            response += f"📡 **النتيجة:** {message}\n"
            response += f"🔗 **API URL:** `{API_URL}`\n"
            response += f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}"
        else:
            response = f"❌ **اختبار الاتصال فاشل**\n\n"
            response += f"📡 **السبب:** {message}\n"
            response += f"🔗 **API URL:** `{API_URL}`\n"
            response += f"⏰ **الوقت:** {datetime.now().strftime('%H:%M:%S')}\n\n"
            response += "يمكنك محاولة إعادة الاتصال باستخدام الزر أدناه."
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 إعادة الاتصال", callback_data="force_reconnect"))
        markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_reconnect_api"))
        
        bot.edit_message_text(response, call.message.chat.id, call.message.message_id,
                             reply_markup=markup, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(call.from_user.id, 
                       f"❌ **خطأ في اختبار الاتصال**\n\n{str(e)}",
                       parse_mode="Markdown")
        admin_reconnect_api(call)

@bot.callback_query_handler(func=lambda call: call.data == "restart_bot")
def restart_bot(call):
    if not is_admin(call.from_user.id):
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ نعم، أعد التشغيل", callback_data="confirm_restart"))
    markup.add(types.InlineKeyboardButton("❌ لا، إلغاء", callback_data="admin_reconnect_api"))
    
    bot.edit_message_text("🔄 **إعادة تشغيل البوت**\n\n"
                         "هل أنت متأكد أنك تريد إعادة تشغيل البوت؟\n"
                         "هذا سيوقف مؤقتاً استقبال الأكواد لمدة 5 ثواني.",
                         call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "confirm_restart")
def confirm_restart(call):
    if not is_admin(call.from_user.id):
        return
    
    bot.answer_callback_query(call.id, "🔄 جاري إعادة تشغيل البوت...", show_alert=True)
    
    try:
        global crapi
        crapi = CRAPI()
        
        bot.send_message(call.from_user.id, 
                       "✅ **تم إعادة تشغيل البوت بنجاح**\n\n"
                       "📡 **تمت إعادة تهئة اتصال API**\n"
                       "⏰ **الوقت:** " + datetime.now().strftime('%H:%M:%S') + "\n\n"
                       "البوت يعمل الآن بشكل طبيعي.",
                       parse_mode="Markdown")
        
        admin_reconnect_api(call)
        
    except Exception as e:
        bot.send_message(call.from_user.id,
                       f"❌ **خطأ في إعادة التشغيل**\n\n{str(e)}",
                       parse_mode="Markdown")
        admin_reconnect_api(call)

# ======================
# 🗑️ إعدادات حذف الرسائل
# ======================
@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_settings")
def admin_delete_settings(call):
    if not is_admin(call.from_user.id):
        return
    
    delete_after_seconds = int(get_setting('delete_after_seconds') or 300)
    delete_enabled = get_setting('delete_messages_enabled') == '1'
    minutes = delete_after_seconds // 60
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⏱️ تغيير وقت الحذف", callback_data="change_delete_time"))
    
    if delete_enabled:
        markup.add(types.InlineKeyboardButton("❌ تعطيل الحذف التلقائي", callback_data="disable_auto_delete"))
    else:
        markup.add(types.InlineKeyboardButton("✅ تفعيل الحذف التلقائي", callback_data="enable_auto_delete"))
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
    
    text = f"⚙️ **إعدادات حذف الرسائل**\n\n"
    text += f"🔧 الحالة: {'✅ مفعل' if delete_enabled else '❌ معطل'}\n"
    text += f"⏱️ وقت الحذف: {minutes} دقيقة ({delete_after_seconds} ثانية)\n\n"
    text += "الرسائل المراد حذفها: " + str(len(messages_to_delete))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "change_delete_time")
def change_delete_time_step1(call):
    if not is_admin(call.from_user.id):
        return
    
    user_states[call.from_user.id] = "waiting_delete_time"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_delete_settings"))
    
    bot.edit_message_text(
        "⏱️ **تغيير وقت حذف الرسائل**\n\n"
        "أرسل عدد الدقائق التي تريدها:\n"
        "• مثال: 5 (لخمس دقائق)\n"
        "• مثال: 10 (لعشر دقائق)\n"
        "• أدخل 0 لتعطيل الحذف التلقائي",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda msg: user_states.get(msg.from_user.id) == "waiting_delete_time")
def change_delete_time_step2(message):
    if not is_admin(message.from_user.id):
        return
    
    try:
        minutes = int(message.text.strip())
        seconds = minutes * 60
        
        if seconds < 0:
            bot.reply_to(message, "❌ الوقت يجب أن يكون عدداً موجباً!")
            return
        
        set_setting('delete_after_seconds', str(seconds))
        
        if seconds == 0:
            time_text = "معطل"
        else:
            time_text = f"{minutes} دقيقة"
        
        bot.reply_to(
            message,
            f"✅ **تم تحديث وقت الحذف**\n\n"
            f"⏱️ **الوقت الجديد:** {time_text}\n"
            f"📅 **الوقت:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode="Markdown"
        )
        
        del user_states[message.from_user.id]
        
    except ValueError:
        bot.reply_to(message, "❌ وقت غير صحيح! يجب أن يكون رقماً.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ غير متوقع: {str(e)}")
        if message.from_user.id in user_states:
            del user_states[message.from_user.id]

@bot.callback_query_handler(func=lambda call: call.data == "enable_auto_delete")
def enable_auto_delete(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('delete_messages_enabled', '1')
    bot.answer_callback_query(call.id, "✅ تم تفعيل الحذف التلقائي!", show_alert=True)
    admin_delete_settings(call)

@bot.callback_query_handler(func=lambda call: call.data == "disable_auto_delete")
def disable_auto_delete(call):
    if not is_admin(call.from_user.id):
        return
    
    set_setting('delete_messages_enabled', '0')
    bot.answer_callback_query(call.id, "❌ تم تعطيل الحذف التلقائي!", show_alert=True)
    admin_delete_settings(call)

# ======================
# 📊 باقي أوامر الأدمن
# ======================
@bot.callback_query_handler(func=lambda call: call.data == "admin_add_combo")
def admin_add_combo(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = "waiting_combo_file"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    bot.edit_message_text("📤 أرسل ملف الكومبو بصيغة TXT", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(content_types=['document'])
def handle_combo_file(message):
    if not is_admin(message.from_user.id):
        return
    if user_states.get(message.from_user.id) != "waiting_combo_file":
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        content = downloaded_file.decode('utf-8')
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            bot.reply_to(message, "❌ الملف فارغ!")
            return
        
        first_num = re.sub(r'\D', '', lines[0])
        country_code = None
        for code in COUNTRY_CODES:
            if first_num.startswith(code):
                country_code = code
                break
        
        if not country_code:
            bot.reply_to(message, "❌ لا يمكن تحديد الدولة من الأرقام!")
            return
        
        save_combo(country_code, lines)
        name, flag, _ = COUNTRY_CODES[country_code]
        bot.reply_to(message, f"✅ تم حفظ الكومبو لدولة {flag} {name}\n🔢 عدد الأرقام: {len(lines)}")
        del user_states[message.from_user.id]
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_del_combo")
def admin_del_combo(call):
    if not is_admin(call.from_user.id):
        return
    combos = get_all_combos()
    if not combos:
        bot.answer_callback_query(call.id, "لا توجد كومبوهات!", show_alert=True)
        return
    markup = types.InlineKeyboardMarkup()
    for code in combos:
        if code in COUNTRY_CODES:
            name, flag, _ = COUNTRY_CODES[code]
            markup.add(types.InlineKeyboardButton(f"{flag} {name}", callback_data=f"del_combo_{code}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    bot.edit_message_text("اختر الكومبو للحذف:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_combo_"))
def confirm_del_combo(call):
    if not is_admin(call.from_user.id):
        return
    code = call.data.split("_", 2)[2]
    delete_combo(code)
    name, flag, _ = COUNTRY_CODES.get(code, ("Unknown", "🌍", ""))
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    bot.edit_message_text(f"✅ تم حذف الكومبو: {flag} {name}", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    if not is_admin(call.from_user.id):
        return
    total_users = len(get_all_users())
    combos = get_all_combos()
    total_numbers = sum(len(get_combo(c)) for c in combos)
    otp_count = len(get_otp_logs())
    token_valid = crapi.check_token_valid()
    api_status = "🟢 Active" if token_valid else "🔴 Inactive"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="admin_panel"))
    
    bot.edit_message_text(
        f"📊 **Bot Statistics:**\n\n"
        f"👥 **Active Users:** {total_users}\n"
        f"🌐 **Countries Added:** {len(combos)}\n"
        f"📞 **Total Numbers:** {total_numbers:,}\n"
        f"🔑 **Total OTPs:** {otp_count}\n"
        f"📡 **API Status:** {api_status}\n"
        f"🗑️ **Messages to Delete:** {len(messages_to_delete)}",
        call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_full_report")
def admin_full_report(call):
    if not is_admin(call.from_user.id):
        return
    try:
        report = "📊 تقرير شامل عن البوت\n" + "="*40 + "\n\n"
        
        report += "👥 المستخدمون:\n"
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        for u in users:
            status = "محظور" if u[6] else "نشط"
            report += f"ID: {u[0]} | @{u[1] or 'N/A'} | الرقم: {u[5] or 'N/A'} | الحالة: {status}\n"
        report += "\n" + "="*40 + "\n\n"
        
        report += "🔑 سجل الأكواد:\n"
        c.execute("SELECT * FROM otp_logs")
        logs = c.fetchall()
        for log in logs:
            user_info = get_user(log[5]) if log[5] else None
            user_tag = f"@{user_info[1]}" if user_info and user_info[1] else f"ID:{log[5] or 'N/A'}"
            report += f"الرقم: {log[1]} | الكود: {log[2]} | المستخدم: {user_tag} | الوقت: {log[4]}\n"
        
        conn.close()
        report += "\n" + "="*40 + "\n\n"
        report += "تم إنشاء التقرير في: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open("bot_report.txt", "w", encoding="utf-8") as f:
            f.write(report)
        
        with open("bot_report.txt", "rb") as f:
            bot.send_document(call.from_user.id, f)
        
        os.remove("bot_report.txt")
        bot.answer_callback_query(call.id, "✅ تم إرسال التقرير!", show_alert=True)
        
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}", show_alert=True)

# ======================
# 🔄 الحلقة الرئيسية باستخدام API - محسنة للسرعة القصوى
# ======================
def api_main_loop():
    """الحلقة الرئيسية باستخدام API - محسنة للسرعة القصوى"""
    print("=" * 60)
    print("🚀 Starting OTP Bot - API Version")
    print("⚡⚡⚡ سرعة قصوى: تحديث كل 0.2 ثانية")
    print("=" * 60)
    
    error_count = 0
    sent_count = 0
    last_success_time = time.time()
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # تنظيف الذاكرة المؤقتة
            cleanup_cache()
            
            # التحقق من أخطاء الاتصال المتتالية
            if crapi.connection_errors > 10:
                print(f"⚠️  Many API errors ({crapi.connection_errors}), checking connection...")
                token_valid = crapi.check_token_valid()
                if not token_valid:
                    print("🔌 API connection lost! Attempting to reconnect...")
                    crapi.force_reconnect()
                crapi.connection_errors = 0
            
            print(f"[{current_time}] 🔍 Fetching messages from API...")
            
            messages = crapi.fetch_messages(records=150, hours_back=0.08)  # ⚡ 5 دقائق فقط
            
            if messages:
                print(f"[API] 📨 Received {len(messages)} messages")
                
                for msg in messages:
                    # إنشاء مفتاح فريد للرسالة باستخدام الـ hash
                    msg_content = f"{msg.get('num', '')}_{msg.get('message', '')}_{msg.get('dt', '')}"
                    msg_hash = hashlib.md5(msg_content.encode()).hexdigest()[:12]
                    
                    # التحقق إذا كانت الرسالة مرسلة مسبقاً
                    if is_in_cache(msg_hash):
                        continue
                    
                    # معالجة الرسالة
                    date_str = msg.get('dt', '')
                    number = msg.get('num', '')
                    message_text = msg.get('message', '')
                    
                    if not date_str or not number or not message_text:
                        continue
                    
                    # إرسال OTP للمستخدم والجروب (من الملف الثاني)
                    threading.Thread(
                        target=send_otp_to_user_and_group, 
                        args=(date_str, number, message_text),
                        daemon=True
                    ).start()
                    
                    # إضافة للذاكرة المؤقتة
                    add_to_cache(msg_hash)
                    
                    sent_count += 1
                    last_success_time = time.time()
                    
                    print(f"[✅] تم إرسال: {get_country_info(number)[0]} | {extract_otp(message_text)}")
                    
                    # ⚡ إزالة الـ sleep بين الرسائل تماماً
                    # لا يوجد time.sleep هنا - أسرع ما يمكن
                    
            else:
                print(f"[{current_time}] ⏳ No new messages")
                
                # ⚡ تقليل وقت الانتظار عند عدم وجود رسائل
                time.sleep(REFRESH_INTERVAL)  # ⚡ 0.2 ثانية فقط
            
            error_count = 0
            
        except requests.exceptions.RequestException as e:
            error_count += 1
            crapi.connection_errors += 1
            print(f"[!] ❌ Network error: {e}")
            time.sleep(2)  # ⚡ وقت انتظار أقل عند الأخطاء
            
        except Exception as e:
            error_count += 1
            print(f"[!] ❌ Error in main loop: {e}")
            traceback.print_exc()
            time.sleep(1)  # ⚡ وقت انتظار أقل عند الأخطاء

# ======================
# 🚀 تشغيل البوت
# ======================
def run_bot():
    """تشغيل البوت في ثرياد منفصل"""
    print("[*] Starting Telegram Bot...")
    bot.polling(none_stop=True, interval=0.5)

if __name__ == "__main__":
    # تشغيل وظيفة حذف الرسائل
    delete_thread = threading.Thread(target=delete_old_messages)
    delete_thread.daemon = True
    delete_thread.start()
    
    # تشغيل البوت
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # إعطاء البوت وقت للبدء
    time.sleep(1)  # ⚡ تقليل من 3 إلى 1 ثانية
    
    # تشغيل الحلقة الرئيسية
    print("=" * 60)
    print("🚀 Starting API Loop...")
    print("⚡⚡⚡ سرعة التحديث: كل 0.2 ثانية")
    print("=" * 60)
    
    api_main_loop()