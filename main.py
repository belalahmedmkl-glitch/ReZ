import time
import requests
import json
import re
import os
from datetime import datetime, date, timedelta
from urllib.parse import quote_plus
from pathlib import Path
import sqlite3
import telebot
from telebot import types
import threading
import traceback
import random
import itertools

BASE = "http://139.99.63.204"
AJAX_PATH = "/ints/agent/res/data_smscdr.php"
LOGIN_PAGE_URL = BASE + "/ints/login"
LOGIN_POST_URL = BASE + "/ints/signin"

# ======================
# 🖥️ إعداد لوحات (2 لوحة)
# ======================
DASHBOARD_CONFIGS = [
    {
        "name": "Ziad Panel",
        "api_url": "http://147.135.212.197/crapi/st/viewstats",
        "token": "R1BTQ0ZBUzRhYlhfQ0-LZV13holmcnhWe1BRZYiRi2F_eIRJfWOOfg==",
        "type": "old_list",
        "records": 10,
        "session": requests.Session(),
        "is_logged_in": True
    },
    {
        "name": "Ziad Panel",
        "api_url": "http://147.135.212.197/crapi/bo/viewstats",
        "token": "R1BTQ0ZBUzRhYlhfQ0-LZV13holmcnhWe1BRZYiRi2F_eIRJfWOOfg==",
        "type": "new_json",
        "records": 10,
        "session": requests.Session(),
        "is_logged_in": True
    }
]

# ======================
# 🚀 تهيئة الـ API والـ Headers
# ======================
COMMON_HEADERS = {
    "User-Agent": "Albrans-API-Monitor/2.0",
    "Accept": "application/json"
}

for dash in DASHBOARD_CONFIGS:
    dash["session"].headers.update(COMMON_HEADERS)
    dash["login_page_url"] = ""
    dash["login_post_url"] = ""
    dash["ajax_url"] = dash["api_url"]
    print(f"[{dash['name']}] 🚀 نظام الـ API جاهز للمراقبة...")

# ======================
# ⚙️ إعدادات البوت والتحكم
# ======================
BOT_TOKEN = "8505031797:AAGNJMM6NpbOVQIH0SDAYvXIVe8lFskH2XA"
CHAT_IDS = ["-1003551242784, -1003619685902"]
ADMIN_IDS = [8231420847, 7966354929, 1042225523]

# ⚡ تغيير من 5 إلى 0.2 ثانية
REFRESH_INTERVAL = 0.2  # ⚡ سرعة قصوى - 0.2 ثانية فقط
TIMEOUT = 5
MAX_RETRIES = 5
RETRY_DELAY = 5

# ======================
# 🗑️ إعدادات حذف الرسائل
# ======================
DELETE_MESSAGES_AFTER = 300  # 5 دقائق
messages_to_delete = []

# الفهارس بناءً على القائمة اللي السيرفر بيبعتها [Service, Num, Msg, Date]
IDX_SERVICE = 0  # الخدمة
IDX_NUMBER = 1   # الرقم
IDX_SMS = 2      # الرسالة
IDX_DATE = 3     # التاريخ

DB_PATH = "bot_database.db"
SENT_MESSAGES_FILE = "sent_messages.json"
BOT_ACTIVE = True

if not BOT_TOKEN:
    raise SystemExit("❌ BOT_TOKEN must be set in Secrets (Environment Variables)")
if not CHAT_IDS:
    raise SystemExit("❌ CHAT_IDS must be configured")

# ======================
# 🌍 أكواد الدول
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
# 🧰 دوال إدارة قاعدة البيانات
# ======================
def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM bot_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO bot_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# ======================
# 🧠 إنشاء قاعدة البيانات
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
        CREATE TABLE IF NOT EXISTS dashboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            base_url TEXT,
            ajax_path TEXT,
            login_page TEXT,
            login_post TEXT,
            username TEXT,
            password TEXT
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
    # جدول القنوات
    c.execute('''
        CREATE TABLE IF NOT EXISTS force_sub_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_url TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1
        )
    ''')
    # إعدادات حذف الرسائل
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('delete_after_seconds', '300')")
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('delete_messages_enabled', '1')")
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('force_sub_channel', '')")
    c.execute("INSERT OR IGNORE INTO bot_settings (key, value) VALUES ('force_sub_enabled', '0')")

    old_channel = get_setting('force_sub_channel')
    if old_channel and old_channel.strip():
        channel = old_channel.strip()
        c.execute("SELECT 1 FROM force_sub_channels WHERE channel_url = ?", (channel,))
        if not c.fetchone():
            enabled = 1 if get_setting("force_sub_enabled") == "1" else 0
            c.execute("INSERT INTO force_sub_channels (channel_url, description, enabled) VALUES (?, ?, ?)",
                      (channel, "القناة الأساسية", enabled))

    conn.commit()
    conn.close()

init_db()

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
    
def is_maintenance_mode():
    return not BOT_ACTIVE

def set_maintenance_mode(status):
    global BOT_ACTIVE
    BOT_ACTIVE = not status
    
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

def get_user_info(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

# ======================
# 🔐 دوال الاشتراك الإجباري
# ======================
def get_all_force_sub_channels(enabled_only=True):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if enabled_only:
        c.execute("SELECT id, channel_url, description FROM force_sub_channels WHERE enabled = 1 ORDER BY id")
    else:
        c.execute("SELECT id, channel_url, description FROM force_sub_channels ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows

def add_force_sub_channel(channel_url, description=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO force_sub_channels (channel_url, description, enabled) VALUES (?, ?, 1)",
                  (channel_url.strip(), description.strip()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_force_sub_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM force_sub_channels WHERE id = ?", (channel_id,))
    changed = c.rowcount > 0
    conn.commit()
    conn.close()
    return changed

def toggle_force_sub_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE force_sub_channels SET enabled = 1 - enabled WHERE id = ?", (channel_id,))
    conn.commit()
    conn.close()

def force_sub_check(user_id):
    channels = get_all_force_sub_channels(enabled_only=True)
    if not channels:
        return True

    for _, url, _ in channels:
        try:
            if url.startswith("https://t.me/"):
                ch = "@" + url.split("/")[-1]
            elif url.startswith("@"):
                ch = url
            else:
                continue
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"[!] خطأ في التحقق من القناة {url}: {e}")
            return False
    return True

def force_sub_markup():
    channels = get_all_force_sub_channels(enabled_only=True)
    if not channels:
        return None

    markup = types.InlineKeyboardMarkup()
    for _, url, desc in channels:
        text = f" {desc}" if desc else " اشترك في القناة"
        markup.add(types.InlineKeyboardButton(text, url=url))
    markup.add(types.InlineKeyboardButton("✅ Check your subscription", callback_data="check_sub"))
    return markup

# ======================
# 🤖 إنشاء بوت Telegram
# ======================
bot = telebot.TeleBot(BOT_TOKEN)

# ======================
# 🗑️ دوال حذف الرسائل
# ======================
def delete_message_after_delay(chat_id, message_id, delay=300):
    """تحذف الرسالة بعد مرور delay ثانية"""
    time.sleep(delay)
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
        payload = {"chat_id": chat_id, "message_id": message_id}
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"❌ فشل حذف الرسالة: {e}")

# ======================
# 🎮 وظائف البوت التفاعلي
# ======================
def is_admin(user_id):
    return user_id in ADMIN_IDS
    
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_maintenance_mode() and not is_admin(user_id):
        maintenance_caption = (
            "<b>❍─── <u>𝐖𝐞𝐥𝐜𝐨𝐦 𝐭𝐨 𝙋𝙍𝙄𝙈𝙀 𝙊𝙏𝙋 𝙃𝙐𝘽</u> ───❍</b>\n\n"
            "<b>⚠️ Sorry, dear user</b>\n"
            "<b>The bot is currently in maintenance mode to update services..</b>\n\n"
            "<b>⏳ Please try again later.</b>\n"
            "<b>────────────────────</b>"
        )
        maintenance_photo = "https://i.ibb.co/2352v1FN/file-000000004f20720aaa70039fcd26faab-1.png" 
        
        try:
            bot.send_photo(
                chat_id, 
                maintenance_photo, 
                caption=maintenance_caption, 
                parse_mode="HTML"
            )
        except:
            bot.send_message(chat_id, maintenance_caption, parse_mode="HTML")
        return

    if is_banned(user_id):
        bot.reply_to(message, "<b>🚫 عذراً، لقد تم حظرك من استخدام البوت.</b>", parse_mode="HTML")
        return

    if not force_sub_check(user_id):
        markup = force_sub_markup()
        if markup:
            bot.send_message(chat_id, "<b>🔒 You must subscribe to the channels to use the bot.</b>", parse_mode="HTML", reply_markup=markup)
        else:
            bot.send_message(chat_id, "<b>🔒 الاشتراك الإجباري مفعل لكن لم يتم تحديد قناة!</b>", parse_mode="HTML")
        return

    if not get_user(user_id):
        save_user(
            user_id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "",
            last_name=message.from_user.last_name or ""
        )
        for admin in ADMIN_IDS:
            try:
                caption = (
                    f"🆕 <b>مستخدم جديد دخل البوت:</b>\n"
                    f"<b>🆔:</b> <code>{user_id}</code>\n"
                    f"<b>👤:</b> @{message.from_user.username or 'None'}\n"
                    f"<b>الاسم:</b> {message.from_user.first_name or ''}"
                )
                bot.send_message(admin, caption, parse_mode="HTML")
            except:
                pass
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    user_data = get_user(user_id)
    private_combo = user_data[7] if user_data else None
    all_combos = get_all_combos()

    if private_combo and private_combo in COUNTRY_CODES:
        name, flag, _ = COUNTRY_CODES[private_combo]
        buttons.append(types.InlineKeyboardButton(f"{flag} {name} (Private)", callback_data=f"country_{private_combo}"))

    for code in all_combos:
        if code in COUNTRY_CODES and code != private_combo:
            name, flag, _ = COUNTRY_CODES[code]
            buttons.append(types.InlineKeyboardButton(f"{flag} {name}", callback_data=f"country_{code}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    if is_admin(user_id):
        markup.add(types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel"))

    fancy_text = (
        "<b><u>𝐖𝐞𝐥𝐜𝐨𝐦 𝐭𝐨 𝙋𝙍𝙄𝙈𝙀 𝙊𝙏𝙋 𝙃𝙐𝘽</u></b>\n\n"
        "<b>👨🏻‍💻 <u>𝑷𝑹𝑰𝑴𝑬 𝑯𝑼𝑩 𝑪𝑯𝑨𝑵𝑵𝑬𝑳</u>  • <a href='https://t.me/OV_20000'>𝑪𝑳𝑰𝑪𝑲 𝑯𝑬𝑹𝑬</a></b>\n\n"
        "<b>────────────────────</b>\n"
        "<b><u>: 𝐒𝐞𝐥𝐞𝐜𝐭 𝐂𝐨𝐮𝐧𝐭𝐫𝐲</u> ⬇️</b>"
    )

    bot.send_message(
        chat_id, 
        fancy_text, 
        parse_mode="HTML", 
        reply_markup=markup,
        disable_web_page_preview=True
    )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_subscription(call):
    if force_sub_check(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified, you can now use the bot.", show_alert=True)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ You haven't subscribed yet", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_selection(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if is_banned(user_id):
        bot.answer_callback_query(call.id, "🚫 You are banned.", show_alert=True)
        return
    if not force_sub_check(user_id):
        markup = force_sub_markup()
        bot.send_message(chat_id, "<b>🔒 You must subscribe to the channels to use the bot.</b>", parse_mode="HTML", reply_markup=markup)
        return

    country_code = call.data.split("_", 1)[1]
    available_numbers = get_available_numbers(country_code, user_id)
    
    if not available_numbers:
        error_msg = "<b>❌ نعتذر، جميع الأرقام قيد الاستخدام حالياً لهذه الدولة.</b>"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 العودة لاختيار دولة أخرى", callback_data="back_to_countries"))
        bot.edit_message_text(error_msg, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
        return

    assigned = random.choice(available_numbers)
    old_user = get_user(user_id)
    if old_user and old_user[5]:
        release_number(old_user[5])
    
    assign_number_to_user(user_id, assigned)
    save_user(user_id, country_code=country_code, assigned_number=assigned)
    
    name, flag, _ = COUNTRY_CODES.get(country_code, ("Unknown", "🌍", ""))
    msg_text = (
        f"<b>◈ Number:</b> <code>{assigned}</code>\n"
        f"<b>◈ Country:</b> {flag} {name}\n"
        f"<b>◈ Status :</b> ⏳ Waiting for SMS"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👥 OTP Group", url="https://t.me/spepepepdpdpd"))
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_num_{country_code}"))
    markup.add(types.InlineKeyboardButton("🔙 Change Country", callback_data="back_to_countries"))

    try:
        bot.edit_message_text(
            text=msg_text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        bot.answer_callback_query(call.id, "✅ The number was received successfully")
    except Exception as e:
        print(f"Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("change_num_"))
def change_number(call):
    user_id = call.from_user.id
    
    if is_banned(user_id):
        return
    if not force_sub_check(user_id):
        return
        
    country_code = call.data.split("_", 2)[2]
    available_numbers = get_available_numbers(country_code, user_id)
    
    if not available_numbers:
        bot.answer_callback_query(call.id, "❌ نعتذر، جميع الأرقام قيد الاستخدام حالياً.", show_alert=True)
        return

    old_user = get_user(user_id)
    if old_user and old_user[5]:
        release_number(old_user[5])
        
    assigned = random.choice(available_numbers)
    assign_number_to_user(user_id, assigned)
    save_user(user_id, assigned_number=assigned)
    
    name, flag, _ = COUNTRY_CODES.get(country_code, ("Unknown", "🌍", ""))
    
    msg_text = (
        f"<b>◈ Number:</b> <code>{assigned}</code>\n"
        f"<b>◈ Country:</b> {flag} {name}\n"
        f"<b>◈ Status :</b> ⏳ Waiting for SMS"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👥 OTP Group", url="https://t.me/spepepepdpdpd"))
    markup.add(types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_num_{country_code}"))
    markup.add(types.InlineKeyboardButton("🔙 Change Country", callback_data="back_to_countries"))

    try:
        bot.edit_message_text(
            text=msg_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        bot.answer_callback_query(call.id, "✅ The number was successfully changed.")
    except Exception as e:
        print(f"Error in change_number: {e}")
        bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_countries")
def back_to_countries(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    user = get_user(call.from_user.id)
    private_combo = user[7] if user else None
    all_combos = get_all_combos()

    if private_combo and private_combo in COUNTRY_CODES:
        name, flag, _ = COUNTRY_CODES[private_combo]
        buttons.append(types.InlineKeyboardButton(f"{flag} {name} (Private)", callback_data=f"country_{private_combo}"))

    for code in all_combos:
        if code in COUNTRY_CODES and code != private_combo:
            name, flag, _ = COUNTRY_CODES[code]
            buttons.append(types.InlineKeyboardButton(f"{flag} {name}", callback_data=f"country_{code}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    if is_admin(call.from_user.id):
        admin_btn = types.InlineKeyboardButton("🔐 Admin Panel", callback_data="admin_panel")
        markup.add(admin_btn)

    fancy_text = (
        "<b>❍<u>𝐖𝐞𝐥𝐜𝐨𝐦 𝐭𝐨 𝙋𝙍𝙄𝙈𝙀 𝙊𝙏𝙋 𝙃𝙐𝘽</u>❍</b>\n\n"
        "<b>👨🏻‍💻 <u>𝑷𝑹𝑰𝑴𝑬 𝑯𝑼𝑩 𝑪𝑯𝑨𝑵𝑵𝑬𝑳</u>  • <a href='https://t.me/𝑶𝑽20000'>𝑪𝑳𝑰𝑪𝑲 𝑯𝑬𝑹𝑬</a></b>\n\n"
        "<b>────────────────────</b>\n"
        "<b><u>𝐒𝐞𝐥𝐞𝐜𝐭 𝐂𝐨𝐮𝐧𝐭𝐫𝐲</u> ⬇️</b>"
    )

    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=fancy_text,
            parse_mode="HTML",
            reply_markup=markup,
            disable_web_page_preview=True
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
    
    status_icon = "🟢" if not is_maintenance_mode() else "🔴"
    status_text = "الآن: يعمل بنجاح" if not is_maintenance_mode() else "الآن: قيد الصيانة"
    markup.add(types.InlineKeyboardButton(f"{status_icon} {status_text} {status_icon}", callback_data="toggle_maintenance"))
    
    markup.row(
        types.InlineKeyboardButton("📥 إضافة كومبو", callback_data="admin_add_combo"),
        types.InlineKeyboardButton("🗑️ حذف كومبو", callback_data="admin_del_combo")
    )
    
    markup.row(
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
        types.InlineKeyboardButton("📄 تقرير شامل", callback_data="admin_full_report")
    )
    
    markup.row(
        types.InlineKeyboardButton("📢 إذاعة عامة", callback_data="admin_broadcast_all"),
        types.InlineKeyboardButton("📨 إذاعة مخصصة", callback_data="admin_broadcast_user")
    )
    
    markup.row(
        types.InlineKeyboardButton("🚫 حظر", callback_data="admin_ban"),
        types.InlineKeyboardButton("✅ إلغاء حظر", callback_data="admin_unban"),
        types.InlineKeyboardButton("👤 معلومات", callback_data="admin_user_info")
    )
    
    markup.row(
        types.InlineKeyboardButton("🔗 إشتراك", callback_data="admin_force_sub"),
        types.InlineKeyboardButton("🖥️ اللوحات", callback_data="admin_dashboards"),
        types.InlineKeyboardButton("🔑 برايفت", callback_data="admin_private_combo")
    )
    
    markup.add(types.InlineKeyboardButton("🗑️ حذف الرسائل", callback_data="admin_delete_settings"))
    markup.add(types.InlineKeyboardButton("🔙 مغادرة لوحة التحكم", callback_data="back_to_countries"))
    
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def show_admin_panel(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⚠️ عذراً، هذا القسم للمطورين فقط.", show_alert=True)
        return

    admin_text = (
        "<b>❍─── <u>𝐋𝐎𝐆𝐈𝐍 𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋</u> ───❍</b>\n\n"
        "<b>👋 مرحباً بك يا مطور في لوحة التحكم.</b>\n\n"
        "<b>⚙️ يمكنك التحكم في كامل وظائف البوت من هنا.</b>\n"
        "<b>⚠️ تنبيه: أي تغيير في الإعدادات يؤثر على المستخدمين فوراً.</b>\n\n"
        "<b>────────────────────</b>\n"
        "<b>إحصائيات سريعة:</b>\n"
        "<b>• حالة السيرفر: <u>Online</u> ✅</b>\n"
        f"<b>• الوقت الحالي: <u>{datetime.now().strftime('%H:%M')}</u></b>\n"
        "<b>────────────────────</b>"
    )
    
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=admin_text,
            parse_mode="HTML",
            reply_markup=admin_main_menu(),
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Admin Panel Error: {e}")

# ======================
# 🗑️ إعدادات حذف الرسائل في لوحة الإدارة
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
# 📨 دوال إرسال OTP المحسنة
# ======================
def send_otp_to_user_and_group(date_str, number, sms, service_api=None):
    try:
        time.sleep(random.uniform(0.5, 1.5))  # ⚡ وقت انتظار أقل

        otp_code = extract_otp(sms)
        country_name, country_flag, country_code = get_country_info(number)
        service = service_api if service_api else detect_service(sms)

        try:
            user_id = get_user_by_number(number)
            log_otp(number, otp_code, sms, user_id)
        except:
            user_id = None

        if user_id:
            try:
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton("👤 Owner", url="https://t.me/o_k_60"),
                    types.InlineKeyboardButton("📢 Channel", url="https://t.me/speed010speed")
                )
                bot.send_message(
                    user_id,
                    (f"<b><u>✨ SPEED OTP Received ✨</u></b>\n\n"
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
        
        for attempt in range(2):  # ⚡ محاولتين فقط
            try:
                if send_to_telegram_group(text, otp_code, sms):
                    print(f"✅ [SUCCESS] GROUP | {number}")
                    break
                else:
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

def send_to_telegram_group(text, otp_code, full_sms):
    keyboard = {
        "inline_keyboard": [
            [{"text": f"Click to Copy Code: {otp_code}", "copy_text": {"text": str(otp_code)}}],
            [{"text": "📋 Full Message", "copy_text": {"text": full_sms}}],
            [
                {"text": "Explanations Channel", "url": "https://t.me/OV201"},
                {"text": "🤖 Bot Panel", "url": "https://t.me/Rez_num_bor"}
            ],
            [{"text": "💬 Channel", "url": "https://t.me/OV20000"}]
        ]
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    success_count = 0
    
    for chat_id in CHAT_IDS:
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard)
            }
            
            resp = requests.post(url, json=payload, timeout=5)  # ⚡ وقت أقل
            
            if resp.status_code == 200:
                print(f"✅ [SUCCESS] تم إرسال الرسالة بنجاح إلى: {chat_id}")
                success_count += 1

                msg_id = resp.json().get("result", {}).get("message_id")
                if msg_id:
                    delete_enabled = get_setting('delete_messages_enabled') == '1'
                    delete_after_seconds = int(get_setting('delete_after_seconds') or 300)
                    
                    if delete_enabled and delete_after_seconds > 0:
                        threading.Thread(
                            target=delete_message_after_delay, 
                            args=(chat_id, msg_id, delete_after_seconds), 
                            daemon=True
                        ).start()
            else:
                print(f"⚠️ [FAILED] تليجرام رفض الطلب لآيدي {chat_id}: {resp.text}")
                
        except Exception as e:
            print(f"❌ [ERROR] خطأ غير متوقع مع آيدي {chat_id}: {e}")

    return success_count > 0

# ======================
# 📡 دوال الاتصال بالـ API (معدلة للسرعة)
# ======================
def retry_request(func, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    for attempt in range(max_retries):
        try:
            return func()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt < max_retries - 1:
                print(f"⚠️ محاولة {attempt + 1}/{max_retries} فشلت.. انتظار {retry_delay} ثانية")
                time.sleep(retry_delay)
            else:
                print(f"❌ فشلت جميع المحاولات بعد {max_retries} مرات.")
                raise
        except Exception as e:
            print(f"❌ خطأ غير متوقع: {e}")
            raise

def login_for_dashboard(dash):
    dash["is_logged_in"] = True
    return True

def build_api_url_for_dashboard(dash):
    start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
    
    params = {
        "token": dash["token"],
        "dt1": start_date,
        "dt2": "", 
        "records": dash["records"]
    }
    
    query_string = "&".join([f"{k}={quote_plus(str(v))}" for k, v in params.items()])
    return f"{dash['api_url']}?{query_string}"

def fetch_api_json_for_dashboard(dash, url):
    FETCH_TIMEOUT = 8  # ⚡ تقليل من 15 إلى 8 ثواني

    def do_fetch():
        r = dash["session"].get(url, timeout=FETCH_TIMEOUT)
        
        if r.status_code == 200:
            try:
                return r.json()
            except:
                print(f"[{dash['name']}] ❌ فشل في تحليل الـ JSON")
                return None
        elif r.status_code == 503:
            print(f"[{dash['name']}] ⚡ السيرفر مضغوط (503).")
            return None
        else:
            print(f"[{dash['name']}] ❌ خطأ سيرفر: {r.status_code}")
            return None

    try:
        return retry_request(do_fetch, max_retries=2, retry_delay=2)  # ⚡ تقليل وقت الانتظار
    except:
        return None

def extract_rows_from_json(j):
    if j is None:
        return []

    for key in ("data", "rows", "aaData", "aa_data"):
        if isinstance(j, dict) and key in j and isinstance(j[key], list):
            return j[key]

    if isinstance(j, list):
        return j

    if isinstance(j, dict):
        for v in j.values():
            if isinstance(v, list):
                return v

    return []

def fetch_data():
    if not DASHBOARD_CONFIGS:
        return []

    dash = DASHBOARD_CONFIGS[0]
    today = datetime.now().strftime('%Y-%m-%d 00:00:00')

    try:
        url = (
            f"{dash['api_url']}?"
            f"token={dash['token']}&"
            f"dt1={quote_plus(today)}&"
            f"records={dash['records']}"
        )
        r = requests.get(url, timeout=8)  # ⚡ تقليل من 15 إلى 8 ثواني
        if r.status_code == 200:
            return extract_rows_from_json(r.json())
    except Exception as e:
        print(f"❌ API Error: {e}")

    return []

def clean_html(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip()
    return text

def clean_number(number):
    if not number:
        return ""
    number = re.sub(r'\D', '', str(number))
    return number

def row_to_tuple(row, config_type="old_list"):
    date_str, number, sms = "", "", ""
    
    if config_type == "old_list":
        try:
            date_str = clean_html(str(row[0]))
            number = clean_number(str(row[1]))
            sms = clean_html(str(row[2]))
        except:
            pass

    elif config_type == "new_json":
        date_str = clean_html(str(row.get("dt", "")))
        number = clean_number(str(row.get("num", "")))
        sms = clean_html(str(row.get("message", "")))

    key = f"{number}|{sms}|{date_str}"
    return date_str, number, sms, key

def get_country_info(number):
    number = number.strip().replace("+", "").replace(" ", "").replace("-", "")

    for code, (name, flag, short) in COUNTRY_CODES.items():
        if number.startswith(code):
            return name, flag, short

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
    country_name, country_flag, country_code = get_country_info(number)
    masked_num = mask_number(number)
    otp_code = extract_otp(sms)
    service = detect_service(sms)

    message = (
        f"\n"
        f" {country_flag} #{country_code} [{service}] {masked_num} \n"
        f""
    )
    return message

# ======================
# 🔄 الحلقة الرئيسية (معدلة للسرعة القصوى)
# ======================
def main_loop():
    print("=" * 60)
    print("🚀 Monitoring started - Optimized Mode")
    print("⚡⚡⚡ سرعة قصوى: تحديث كل 0.2 ثانية")
    print("=" * 60)
    
    sent = set()
    error_count = 0
    sent_count = 0
    last_success_time = time.time()

    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        
        for dash in DASHBOARD_CONFIGS:
            try:
                # ⚡ جلب البيانات بسرعة
                response = dash["session"].get(
                    dash['api_url'], 
                    params={"token": dash['token'], "records": dash['records']}, 
                    timeout=3  # ⚡ تقليل من 5 إلى 3 ثواني
                )
                
                result = response.json()
                rows = result.get('data', []) if isinstance(result, dict) else result
                
                if not rows: 
                    continue

                # ⚡ معالجة الرسائل بسرعة
                for row in rows[-10:]:
                    try:
                        date_str, number, sms, key = row_to_tuple(row, dash.get('type', 'old_list'))

                        if key not in sent:
                            print(f"📩 [{dash['name']}] New: {number}")
                            
                            threading.Thread(
                                target=send_otp_to_user_and_group, 
                                args=(date_str, number, sms),
                                daemon=True
                            ).start()
                            
                            sent.add(key)
                            sent_count += 1
                            last_success_time = time.time()
                            
                            # ⚡ لا يوجد time.sleep هنا بين الرسائل
                            
                    except: 
                        continue

                error_count = 0
                
            except Exception as e:
                error_count += 1
                print(f"⚠️ {dash['name']} Error: {e}")
                
                if error_count > 5:
                    print("⚡ إعادة محاولة الاتصال...")
                    time.sleep(1)  # ⚡ استراحة قصيرة
                continue
        
        # تنظيف الذاكرة
        if len(sent) > 2000:
            sent = set(list(sent)[-1000:])
        
        # ⚡ وقت الانتظار بين اللفات
        time.sleep(REFRESH_INTERVAL)  # 0.2 ثانية فقط

# ======================
# 🚀 تشغيل البوت
# ======================
def run_bot():
    """تشغيل البوت في ثرياد منفصل"""
    print("[*] Starting Telegram Bot...")
    bot.polling(none_stop=True, interval=0.5)

if __name__ == "__main__":
    try:
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        # ⚡ وقت أقل للبدء
        time.sleep(1)
        
        print("=" * 60)
        print("🚀 Starting Main Loop...")
        print("⚡⚡⚡ سرعة التحديث: كل 0.2 ثانية")
        print("=" * 60)
        
        main_loop()
    except Exception as e:
        print(f"❌ خطأ في التشغيل: {e}")
        traceback.print_exc()