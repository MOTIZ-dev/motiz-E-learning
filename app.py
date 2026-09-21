from flask import Flask, render_template_string, request, redirect, session, Response
from markupsafe import Markup
from datetime import date, datetime, timedelta
import json, os, urllib.parse, csv, math, random
from io import StringIO
from functools import wraps
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "motiz_secret_key_2026_v33")
app.config['PROPAGATE_EXCEPTIONS'] = True

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = sa.create_engine(DATABASE_URL)
DBSession = sessionmaker(bind=engine)

PALMPAY_ACCOUNT = "8908025244"
PALMPAY_NAME = "HAMZAT KOLADE AJIMOTI"
PALMPAY_BANK = "PALMPAY"
LESSON_PRICE = 1000
QUESTION_PRICE = 500
ADMIN_PASS = os.environ.get('ADMIN_PASS', "24434")
FREE_Q = 10
PAID_Q = 90
BATCH_SIZE = 10
NIGERIA_TZ = pytz.timezone('Africa/Lagos')
FAVICON_URL = "https://i.imgur.com/5TCBgkN.png"
SEND_BTN_URL = "https://i.imgur.com/ADGwy5l.png"
BASE_URL = "https://motiz-e-learning-institution.onrender.com"
FIXED_AD_KEY = "f0869e31689755e244912b438511f4a9"
AD_REFRESH_MAIN = 60
AD_REFRESH_CBT = 30
FRIENDS_BATCH = 5
TICK_SENT = "✓ Sent"
TICK_DELIVERED = "✓✓ Delivered"
TICK_SEEN = "✓✓ Seen"
CALC_SUBJECTS = ["Mathematics", "Physics", "Chemistry", "Further Mathematics", "Financial Accounting", "Economics", "Biology", "Basic Science", "Basic Technology"]

JSS_SUBJECTS = ["English Language", "Mathematics", "Basic Science", "Basic Technology", "Social Studies", "Civic Education", "Business Studies", "Agricultural Science", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Physical and Health Education (PHE)"]
CLASSES = ["JSS1", "JSS2", "JSS3", "SS1", "SS2", "SS3"]
SUBJECTS = {
    "JSS1": JSS_SUBJECTS, "JSS2": JSS_SUBJECTS, "JSS3": JSS_SUBJECTS,
    "SS1_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS1_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS1_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS2_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS2_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "History", "Computer Studies / ICT", "Marketing"],
    "SS2_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"],
    "SS3_Science": ["English Language", "Mathematics", "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "ICT", "Agricultural Science", "Geography"],
    "SS3_Commercial": ["English Language", "Mathematics", "Civic Education", "Economics", "Financial Accounting", "Commerce", "Business Management", "Government", "Computer Studies / ICT", "Marketing"],
    "SS3_Art": ["English Language", "Mathematics", "Civic Education", "Literature in English", "Government", "Christian Religious Studies (CRS)", "Islamic Religious Studies (IRS)", "Yoruba", "Economics", "Computer Studies / ICT", "Craft"]
}
ADMIN_LEVELS = {
    "jss1": ["JSS1"], "jss2": ["JSS2"], "jss3": ["JSS3"],
    "sss1": ["SS1_Science","SS1_Commercial","SS1_Art"],
    "sss2": ["SS2_Science","SS2_Commercial","SS2_Art"],
    "sss3": ["SS3_Science","SS3_Commercial","SS3_Art"]
}
SUBJECT_EMOJI = {"Mathematics":"📐","Further Mathematics":"📏","Physics":"⚛️","Chemistry":"🧑‍🔬","Biology":"🧬","English Language":"📝","Economics":"📊","Financial Accounting":"💰","Commerce":"🏪","Business Management":"📈","Literature in English":"📚","Government":"🏛️","Christian Religious Studies":"✝️","Christian Religious Studies (CRS)":"✝️","Islamic Religious Studies":"☪️","Islamic Religious Studies (IRS)":"☪️","Yoruba":"🗣️","ICT":"💻","Computer Studies / ICT":"💻","Agricultural Science":"🌾","Geography":"🌍","Basic Science":"🔬","Basic Technology":"🔧","Social Studies":"🌐","Civic Education":"⚖️","Business Studies":"💼","Physical and Health Education":"⚽","Marketing":"📢","History":"📜","Craft":"🎨"}

def subj_emoji(s):
    for k,v in SUBJECT_EMOJI.items():
        if k.lower() in s.lower() or s.lower() in k.lower(): return v
    return "📖"

def init_db():
    with engine.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, nickname TEXT UNIQUE, name TEXT, password TEXT, class TEXT, dept TEXT, q_cycle TEXT DEFAULT 'free', q_used INTEGER DEFAULT 0, free_questions_used INTEGER DEFAULT 0, lesson_expiry DATE, correct INTEGER DEFAULT 0, wrong INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', blocked TEXT DEFAULT '[]', referred_by TEXT DEFAULT NULL, referral_count INTEGER DEFAULT 0, free_days INTEGER DEFAULT 0, is_verified BOOLEAN DEFAULT FALSE, payment_verified_date TEXT, last_seen TIMESTAMP, push_sub TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS payments (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, type TEXT, status TEXT, bank_used TEXT, account_name TEXT, date_paid TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, likes TEXT DEFAULT '[]', comments TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, bg TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS dms (id SERIAL PRIMARY KEY, from_nickname TEXT, to_nickname TEXT, text TEXT, time TEXT, read_by TEXT DEFAULT '[]', delivered_to TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS groups (id SERIAL PRIMARY KEY, name TEXT, creator TEXT, members TEXT DEFAULT '[]', messages TEXT DEFAULT '[]');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS lessons (id SERIAL PRIMARY KEY, class TEXT, dept TEXT, subject TEXT, title TEXT, notes TEXT, date TEXT, media_link TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS questions (id SERIAL PRIMARY KEY, key TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer TEXT, referred TEXT, paid BOOLEAN DEFAULT FALSE, bonus_given BOOLEAN DEFAULT FALSE);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS cbt_progress (id SERIAL PRIMARY KEY, nickname TEXT, subject_key TEXT, used INTEGER DEFAULT 0, UNIQUE(nickname, subject_key));"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS notices (id SERIAL PRIMARY KEY, title TEXT, text TEXT, media_link TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS complaints (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, text TEXT, reply TEXT DEFAULT '', status TEXT DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS daily_challenge (id SERIAL PRIMARY KEY, day DATE, subject TEXT, q TEXT, options TEXT, ans TEXT);"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS daily_scores (id SERIAL PRIMARY KEY, nickname TEXT, name TEXT, score INTEGER DEFAULT 0, day DATE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"))
        conn.commit()
init_db()

def fix_old_users():
    with DBSession() as db:
        cols = [("users","free_questions_used","INTEGER DEFAULT 0"),("users","q_used","INTEGER DEFAULT 0"),("users","correct","INTEGER DEFAULT 0"),("users","wrong","INTEGER DEFAULT 0"),("users","referral_count","INTEGER DEFAULT 0"),("users","free_days","INTEGER DEFAULT 0"),("users","friends","TEXT DEFAULT '[]'"),("users","blocked","TEXT DEFAULT '[]'"),("users","referred_by","TEXT"),("users","payment_verified_date","TEXT"),("users","lesson_expiry","DATE"),("users","is_verified","BOOLEAN DEFAULT FALSE"),("users","last_seen","TIMESTAMP"),("users","push_sub","TEXT DEFAULT ''"),("dms","delivered_to","TEXT DEFAULT '[]'"),("lessons","media_link","TEXT DEFAULT ''"),("posts","bg","TEXT DEFAULT ''")]
        for table,col,typ in cols:
            try:
                db.execute(sa.text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typ}"))
                db.commit()
            except: db.rollback()
fix_old_users()

def ensure_motiz_support():
    with DBSession() as db:
        exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname='motiz_support'")).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,friends,is_verified,last_seen) VALUES ('motiz_support','MOTIZ SUPPORT','motiz_support_2026','SS3','Science','[]',TRUE,NOW()) ON CONFLICT (nickname) DO NOTHING"))
            db.commit()
        all_users = db.execute(sa.text("SELECT nickname, friends FROM users WHERE nickname!='motiz_support'")).mappings().all()
        for u in all_users:
            try:
                fr = json.loads(u['friends'] or '[]')
                if 'motiz_support' not in fr:
                    fr.append('motiz_support')
                    db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(fr), "u": u['nickname']})
            except: pass
        db.commit()
        all_nicks = db.execute(sa.text("SELECT nickname FROM users WHERE nickname!='motiz_support'")).scalars().all()
        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname='motiz_support'"), {"f": json.dumps(all_nicks)})
        db.commit()
ensure_motiz_support()

def seed_data():
    with DBSession() as db:
        count_q = db.execute(sa.text("SELECT COUNT(*) FROM questions")).scalar() or 0
        if count_q >= 1000:
            return
        # === WAEC STANDARD BANKS ===
        WAEC_SS3_MATH = [
            ("If log₁₀2 =0.3010 and log₁₀3=0.4771, evaluate log₁₀ 6", "0.7781", "0.1761", "0.3010", "1.3010", "0.7781"),
            ("Solve: 3x² - 5x - 2 =0", "2 and -1/3", "2 and 1/3", "-2 and 1/3", "3 and -2", "2 and -1/3"),
            ("The sum of first 5 terms of AP 2,5,8... is?", "40", "32", "35", "45", "40"),
            ("If sinθ=3/5, find cosθ (θ acute)", "4/5", "3/4", "5/4", "5/3", "4/5"),
            ("Factorize completely: 6x² +7x -20", "(3x-4)(2x+5)", "(3x+4)(2x-5)", "(6x-4)(x+5)", "(2x+4)(3x-5)", "(3x-4)(2x+5)"),
            ("Find the inverse of matrix [[2,3],[1,2]]", "[[2,-3],[-1,2]]", "[[-2,3],[1,-2]]", "[[2,3],[-1,-2]]", "[[3,2],[2,1]]", "[[2,-3],[-1,2]]"),
            ("WAEC 2022: The probability of picking a defective bulb is 0.02. In a batch of 500, how many defective?", "10", "20", "25", "50", "10"),
            ("Find x if 2^(x+1)=8", "2", "3", "1", "4", "2"),
            ("Mean deviation of 2,4,6,8,10", "2.4", "3.0", "2.0", "4.0", "2.4"),
            ("If y = x³ -3x², find dy/dx", "3x² -6x", "x² -6x", "3x² -3x", "x³ -6", "3x² -6x"),
        ]
        WAEC_SS3_ENGLISH = [
            ("Choose the word with correct stress: 'photograph'", "PHOtograph", "phoTOgraph", "photoGRAPH", "photograPH", "PHOtograph"),
            ("WAEC 2021: He ___ since morning", "has been reading", "is reading", "reads", "had read", "has been reading"),
            ("Synonym of 'gregarious' as used in WAEC", "sociable", "aggressive", "generous", "dangerous", "sociable"),
            ("Choose correct idiom: He was caught ___ handed", "red", "blue", "black", "white", "red"),
            ("Which is correct? 'The number of students ___ absent'", "is", "are", "were", "have been", "is"),
            ("Antonym of 'ephemeral' (WAEC 2023)", "permanent", "brief", "fragile", "temporary", "permanent"),
            ("The figure 'The classroom was a zoo' is", "metaphor", "simile", "personification", "hyperbole", "metaphor"),
            ("After the meeting, he was asked to ___ the proposal", "expatiate on", "expatiate", "expatiate with", "expatiate about", "expatiate on"),
            ("Choose correct: Neither John nor his friends ___ there", "was", "were", "is", "has been", "was"),
            ("WAEC: 'to turn a deaf ear' means", "to ignore", "to listen carefully", "to be deaf", "to hear faintly", "to ignore"),
        ]
        WAEC_SS3_PHYSICS = [
            ("WAEC 2022: A car accelerates from rest at 2m/s² for 5s. Distance covered?", "25m", "10m", "20m", "50m", "25m"),
            ("The dimension of power is", "ML²T⁻³", "MLT⁻²", "ML²T⁻²", "MLT⁻³", "ML²T⁻³"),
            ("Half-life of element is 5 days. Fraction remaining after 15 days?", "1/8", "1/4", "1/2", "1/16", "1/8"),
            ("Critical angle for glass n=1.5 is?", "41.8°", "30°", "60°", "45°", "41.8°"),
            ("In photoelectric effect, stopping potential depends on", "frequency", "intensity", "time", "work function only", "frequency"),
            ("WAEC: Which is vector?", "momentum", "work", "energy", "power", "momentum"),
            ("A transformer has 200 turns primary, 1000 secondary. If primary 20V, secondary?", "100V", "40V", "4V", "200V", "100V"),
            ("Unit of inductance is", "Henry", "Farad", "Ohm", "Tesla", "Henry"),
            ("Escape velocity formula is", "√(2gR)", "gR", "2gR", "√(gR)", "√(2gR)"),
            ("De Broglie wavelength λ =?", "h/p", "p/h", "h×p", "E/h", "h/p"),
        ]
        # JSS1 VERY EASY
        JSS1_MATH = [
            ("What is 5 + 7?", "12", "10", "13", "11", "12"),
            ("What is half of 20?", "10", "5", "15", "20", "10"),
            ("How many sides does triangle have?", "3", "4", "5", "6", "3"),
            ("10 x 2 =?", "20", "12", "18", "22", "20"),
            ("Which is even? 3,5,8,9", "8", "3", "5", "9", "8"),
        ]
        # Default for other classes
        DEFAULT_EASY = [
            ("What is 2+2?", "4", "3", "5", "6", "4"),
            ("Capital of Nigeria is?", "Abuja", "Lagos", "Kano", "Ibadan", "Abuja"),
            ("LCM of 4 and 6 is?", "12", "6", "8", "24", "12"),
        ]
        def get_bank(class_key, subject):
            ck = class_key.upper()
            subj = subject.lower()
            if "SS3" in ck:
                if "math" in subj: return WAEC_SS3_MATH
                if "english" in subj: return WAEC_SS3_ENGLISH
                if "physics" in subj: return WAEC_SS3_PHYSICS
                if "chemistry" in subj: return [("WAEC 2023: Electronic config of Na (11)?", "2,8,1", "2,8,2", "2,7,2", "2,8,3", "2,8,1"), ("pH of 0.01M HCl?", "2", "1", "3", "12", "2"), ("Alkanes general formula?", "CnH2n+2", "CnH2n", "CnH2n-2", "CnH2n+1", "CnH2n+2")] + WAEC_SS3_MATH[:7]
                if "biology" in subj: return [("WAEC: Site of photosynthesis?", "Chloroplast", "Mitochondrion", "Nucleus", "Ribosome", "Chloroplast"), ("Blood group O can donate to?", "All", "A only", "B only", "O only", "All")] + WAEC_SS3_PHYSICS[:8]
                if "economics" in subj: return [("WAEC: Scale of preference means?", "Listing wants in order of importance", "Want for money", "Desire for goods", "Need for choice", "Listing wants in order of importance"), ("Demand curve slopes?", "Downwards", "Upwards", "Horizontal", "Vertical", "Downwards")] + WAEC_SS3_ENGLISH[:8]
                return WAEC_SS3_MATH
            elif "SS2" in ck:
                # SS2 = medium WAEC
                return [("Solve: x+5=12, x=?", "7", "5", "12", "17", "7"), ("Mean of 4,6,8?", "6", "5", "7", "8", "6"), ("LCM 8,12?", "24", "12", "36", "48", "24")] + WAEC_SS3_MATH[:7]
            elif "SS1" in ck:
                return [("What is 3²?", "9", "6", "3", "12", "9"), ("Solve 2x=10", "5", "2", "10", "20", "5"), ("Area of square side 4?", "16", "8", "12", "20", "16")] + DEFAULT_EASY
            elif "JSS3" in ck:
                return [("What is 10% of 200?", "20", "10", "30", "200", "20"), ("Angle in triangle sum?", "180°", "90°", "360°", "270°", "180°")] + JSS1_MATH
            elif "JSS1" in ck or "JSS2" in ck:
                return JSS1_MATH + DEFAULT_EASY
            else:
                return DEFAULT_EASY

        inserted = 0
        batch_counter = 0
        for class_key, subjects in SUBJECTS.items():
            cls_parts = class_key.split("_")
            cls = cls_parts[0]
            dept = cls_parts[1] if len(cls_parts) > 1 else ""
            for subj in subjects:
                key = f"{class_key}_{subj}"
                existing = db.execute(sa.text("SELECT COUNT(*) FROM questions WHERE key=:k"), {"k": key}).scalar() or 0
                if existing >= 100:
                    continue
                bank = get_bank(class_key, subj)
                for i in range(100):
                    if i < len(bank):
                        q,a,b,c,d,ans = bank[i]
                    else:
                        base = bank[i % len(bank)]
                        q,a,b,c,d,ans = base
                        q = f"{q} (Q{i+1})"
                    # Add class tag
                    q_full = f"[{class_key} WAEC] {q}" if "SS3" in class_key else f"[{class_key}] {q}"
                    db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k, :q, :o, :a)"),
                               {"k": key, "q": q_full, "o": json.dumps([a,b,c,d]), "a": ans})
                    inserted += 1
                    batch_counter += 1
                    if batch_counter % 500 == 0:
                        db.commit()
                exist_l = db.execute(sa.text("SELECT id FROM lessons WHERE class=:c AND dept=:d AND subject=:s"), {"c": cls, "d": dept, "s": subj}).scalar()
                if not exist_l:
                    notes = f"""MOTIZ WAEC LESSON: {subj} for {class_key}
LEVEL: {'WAEC STANDARD - Past Questions 2015-2025' if 'SS3' in class_key else 'Graded for '+cls}
1. Definition & WAEC syllabus
2. Key formulas & examples (WAEC style)
3. Solved past questions
4. Assignment: Practice 100 CBT WAEC questions
Prepared by MOTIZ SUPPORT - WAEC Standard"""
                    db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c, :d, :s, :t, :n, :date, :m)"),
                               {"c": cls, "d": dept, "s": subj, "t": f"{subj} WAEC Complete {class_key}", "n": notes, "date": str(date.today()), "m": ""})
                    if batch_counter % 100 == 0:
                        db.commit()
        db.commit()

try:
    seed_data()
except Exception as e:
    print(f"Seed error: {e}")

def get_setting(k, d=""):
    with DBSession() as db:
        v = db.execute(sa.text("SELECT value FROM settings WHERE key=:k"), {"k": k}).scalar()
        return v if v is not None else d
def set_setting(k, v):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO UPDATE SET value=:v"), {"k": k, "v": v})
        db.commit()
ADMIN_PASS = get_setting("admin_pass", ADMIN_PASS)
NOTICES = json.loads(get_setting("notices", json.dumps([{"title":"Welcome","text":"Welcome to MOTIZ E-LEARNING! WAEC STANDARD FOR SS3","created_at": str(datetime.now(pytz.timezone('Africa/Lagos'))), "media_link": ""}])))
PINNED_NOTICE = get_setting("pinned_notice", "")

def get_user():
    nickname = session.get("nickname")
    if not nickname: return None, None
    with DBSession() as db:
        user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        if user:
            user = dict(user)
            user['friends'] = json.loads(user.get('friends', '[]') or '[]')
            user['blocked'] = json.loads(user.get('blocked', '[]') or '[]')
        return nickname, user

def delete_old_posts_and_notices():
    global NOTICES
    cutoff = datetime.now(pytz.timezone('Africa/Lagos')) - timedelta(hours=24)
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM posts WHERE created_at < :c"), {"c": cutoff})
        db.commit()
    new_notices = []
    for n in NOTICES:
        try:
            notice_time = datetime.fromisoformat(n.get('created_at').replace('Z','+00:00'))
            if notice_time > cutoff: new_notices.append(n)
        except: new_notices.append(n)
    if len(new_notices)!= len(NOTICES):
        NOTICES = new_notices
        set_setting("notices", json.dumps(NOTICES))

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        nickname, user = get_user()
        if not user: return redirect("/login")
        delete_old_posts_and_notices()
        return f(nickname, user, *args, **kwargs)
    return wrapper

def format_last_seen(dt):
    if not dt: return "Never"
    try:
        now = datetime.now(pytz.utc) if dt and dt.tzinfo else datetime.now()
        diff = now - dt
        secs = diff.total_seconds()
        if secs < 300: return "<span style='color:green;font-weight:bold'>● Online now</span>"
        mins = int(secs // 60)
        if mins < 60: return f"{mins}m ago"
        hours = mins // 60
        if hours < 24: return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except: return "Unknown"
def format_12h(time_str):
    try:
        if not time_str: return ""
        s = str(time_str)
        import re
        m = re.search(r'(\d{1,2}):(\d{2})', s)
        if m:
            h = int(m.group(1)); mm = m.group(2)
            ampm = "AM" if h < 12 else "PM"
            h12 = h % 12
            if h12 == 0: h12 = 12
            return f"{h12}:{mm} {ampm}"
        return s[:16]
    except: return str(time_str)[:16]

def is_user_paid(user):
    if not user.get('is_verified'): return False
    if not user.get('payment_verified_date'): return True
    try:
        vd = datetime.strptime(user['payment_verified_date'], "%Y-%m-%d").date()
        return date.today() <= vd + timedelta(days=30)
    except:
        return user.get('is_verified', False)

def get_unread_count(nickname):
    with DBSession() as db:
        all_dms = db.execute(sa.text("SELECT read_by FROM dms WHERE to_nickname=:u"), {"u": nickname}).mappings().all()
        count = 0
        for m in all_dms:
            try: rb = json.loads(m['read_by'] or '[]')
            except: rb = []
            if nickname not in rb: count += 1
        return count

def get_unread_per_friend(nickname, friend):
    with DBSession() as db:
        all_dms = db.execute(sa.text("SELECT read_by FROM dms WHERE from_nickname=:f AND to_nickname=:u"), {"f": friend, "u": nickname}).mappings().all()
        c=0
        for m in all_dms:
            try: rb=json.loads(m['read_by'] or '[]')
            except: rb=[]
            if nickname not in rb: c+=1
        return c

BASE = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="icon" type="image/png" href="{FAVICON_URL}">
<link rel="manifest" href="/manifest.json">
<title>{{{{title}}}}</title><style>
:root{{--bg:#f0f2f5;--card:white;--text:#333;--primary:#0f3460}} body{{font-family:Segoe UI;background:var(--bg);color:var(--text);margin:0;padding:0;padding-bottom:90px}}
body.dark{{--bg:#121212;--card:#1e1e1e;--text:#eee}} body.light{{--bg:#f0f2f5;--card:white;--text:#333}}
.header{{background:var(--primary);color:white;padding:6px 10px;text-align:center;position:fixed;top:0;width:100%;z-index:1000;display:flex;justify-content:space-between;align-items:center;height:70px;box-sizing:border-box}}
.header h1{{margin:0;font-size:0.80rem;flex:1;text-align:center;color:white!important;display:flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap;overflow:hidden}}
.header img.logo{{width:75px!important;height:75px!important;border-radius:50%;object-fit:contain;max-height:70px}}
.theme-btn{{border:none;background:transparent;color:white;font-size:1.2rem;cursor:pointer}}
.exit-btn{{background:transparent;color:white;border:none;padding:5px 10px;font-size:1.3rem;cursor:pointer}}
.nav{{display:flex;gap:5px;background:#16213e;padding:6px 5px;flex-wrap:wrap;position:fixed;top:70px;width:100%;z-index:999}}
.nav a{{color:white!important;text-decoration:none;padding:5px 8px;border-radius:10px;border:1px solid #fff3;font-size:0.8rem;white-space:nowrap}}
.nav a:visited{{color:white!important}}
.container{{padding:10px;padding-top:135px;padding-bottom:130px}}
.card{{background:var(--card);padding:12px;margin:8px 0;border-radius:10px;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.card:last-child{{margin-bottom:130px!important}}
.btn{{background:#28a745;color:white!important;padding:10px;display:block;margin:8px auto;text-align:center;font-weight:bold;border:none;width:95%;max-width:350px;border-radius:8px;cursor:pointer}}
.btn.red{{background:#e94560!important}}.btn.blue{{background:#0f3460!important;border:1px solid white}}.btn.orange{{background:#ff9800!important}}.btn.gray{{background:#555!important;width:90%;max-width:300px;font-size:0.85rem}}
input,select,textarea{{width:100%;padding:10px;margin:5px 0;border-radius:5px;border:1px solid #ccc;box-sizing:border-box;background:var(--card);color:var(--text)}}
.badge{{background:#1DA1F2;color:white;padding:3px 8px;border-radius:10px;font-size:0.7rem;white-space:nowrap;display:inline-flex;align-items:center;line-height:1;max-width:100%}}
.badge.gold{{background:gold;color:#0f3460;font-weight:bold;white-space:nowrap}}.badge.verified-paid{{background:#28a745;color:white;white-space:nowrap}}
.timer{{background:#e94560;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;position:sticky;top:68px;z-index:998;margin-bottom:10px}}
.option{{background:#e8eaed;padding:16px 18px;margin-bottom:12px;border-radius:12px;color:#000;display:flex;gap:12px;align-items:center;justify-content:flex-start;text-align:left;width:100%;box-sizing:border-box;cursor:pointer}}
.option input[type="radio"]{{margin-right:12px;width:20px;height:20px;flex-shrink:0}}
.option span{{flex:1;text-align:left;font-size:0.95rem}}
.chat-msg{{display:flex;margin:8px 0;gap:8px}}.chat-msg.me{{justify-content:flex-end}}.chat-msg.other{{justify-content:flex-start}}
.bubble{{padding:10px 14px;border-radius:18px;max-width:70%}}.me.bubble{{background:#2196f3!important;color:white!important}}.other.bubble{{background:#e0e0e0;color:#333}}
.bubble-time{{font-size:11px;opacity:0.8;align-self:flex-end;margin-top:2px;display:flex;gap:6px}}
.tick-seen{{color:#4fc3f7;font-weight:bold}}.tick-delivered{{color:#e0e0e0}}.tick-sent{{color:#ccc}}
.friend-card{{display:flex;align-items:center;gap:10px;padding:12px;background:var(--card);border-radius:10px;margin:8px 0;text-decoration:none;color:var(--text)}}
.friend-avatar{{width:45px;height:45px;border-radius:50%;background:var(--primary);color:white;display:flex;align-items:center;justify-content:center;font-weight:bold}}
.readonly-box{{width:100%;padding:12px;background:#eee;border:1px dashed #999;text-align:center}}
.chat-input-fixed{{position:fixed;bottom:65px;left:10px;right:10px;display:flex;flex-direction:column;gap:5px;background:var(--card);padding:10px;border-radius:15px;z-index:999}}
.reply-preview{{background:#f0f2f5;border-left:4px solid #2196f3;padding:6px 10px;border-radius:5px;display:flex;justify-content:space-between;color:#333}}
.send-img-btn{{background:transparent;border:none}}.send-img-btn img{{height:40px;width:40px}}
#fixedAdBar{{position:fixed;bottom:0;left:0;width:100%;height:60px;background:white;z-index:99999;border-top:1px solid #ddd;display:flex;justify-content:center;align-items:center}}
#cbtSmallAd{{position:fixed;bottom:65px;left:50%;transform:translateX(-50%);width:320px;height:50px;background:white;z-index:9999;border:1px solid #ddd;display:none;justify-content:center;align-items:center;border-radius:8px}}
#updateBanner{{display:none;position:fixed;top:0;left:0;width:100%;background:#ff9800;color:white;padding:10px;text-align:center;z-index:100001}}
.cbt-btn-fix{{display:block;width:95%;max-width:340px;white-space:normal;line-height:1.3;padding:10px;font-size:0.85rem;margin:8px auto}}
.calc-float{{position:fixed;bottom:85px;right:10px;background:#222;color:white;padding:10px;border-radius:10px;z-index:9998;width:240px;display:none;border:2px solid #ff9800}}
.community-bg-post{{padding:30px 15px;text-align:center;border-radius:15px;color:white;font-size:1.4rem;font-weight:bold;min-height:120px;display:flex;align-items:center;justify-content:center}}
.bg-option{{width:35px;height:35px;border-radius:50%;display:inline-block;margin:4px;border:2px solid #fff;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,0.3)}}
.bg-option.selected{{border:3px solid #0f3460;transform:scale(1.2)}}
.like-row{{display:flex;gap:8px;justify-content:flex-start;align-items:center;margin-top:8px}}
.dm-actions-top{{display:flex;flex-direction:row;gap:8px;justify-content:flex-end;padding:6px 10px;margin-bottom:5px}}
.dm-actions-top a{{padding:4px 10px!important;font-size:12px!important;height:28px;border-radius:6px;width:auto!important;max-width:110px;margin:0!important;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;color:white}}
.unread-badge-fix{{white-space:nowrap!important;display:inline-flex!important;align-items:center;line-height:1!important;max-width:fit-content}}
</style></head><body>
<div id="updateBanner">🔄 New version - <button onclick="location.reload(true)" style="background:white;color:#ff9800;border:none;padding:5px 10px;border-radius:5px">Update now</button></div>
{{{{header}}}}<div class="container">{{{{content}}}}</div>
<div id="fixedAdBar"><button onclick="document.getElementById('fixedAdBar').style.display='none'" style="position:absolute;top:2px;right:5px;background:#000;color:#fff;border:none;border-radius:50%;width:20px;height:20px">X</button><div id="adContainer" style="width:728px;max-width:100%;height:60px;display:flex;align-items:center;justify-content:center;"><script>atOptions = {{'key' : '{FIXED_AD_KEY}','format' : 'iframe','height' : 60,'width' : 728,'params' : {{}} }};</script><script src="https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js"></script></div></div>
<div id="cbtSmallAd"><button onclick="document.getElementById('cbtSmallAd').style.display='none'" style="position:absolute;top:2px;right:5px;background:#000;color:#fff;border:none;border-radius:50%;width:18px;height:18px;font-size:10px">X</button><div id="cbtAdInner" style="width:320px;height:50px;display:flex;align-items:center;justify-content:center;"><script>atOptions = {{'key' : '{FIXED_AD_KEY}','format' : 'iframe','height' : 50,'width' : 320,'params' : {{}} }};</script><script src="https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js"></script></div></div>
<div id="calcFloat" class="calc-float"><div style="display:flex;justify-content:space-between"><b>🧮 Calculator</b><button onclick="document.getElementById('calcFloat').style.display='none'" style="background:red;color:white;border:none;border-radius:50%;width:20px">X</button></div><input id="calcDisplay" readonly style="background:#111;color:#0f0;text-align:right;font-size:1.2rem"><div style="display:grid;grid-template-columns:repeat(4,1fr);gap:5px;margin-top:5px"><button class="btn gray" onclick="calcPress('7')">7</button><button class="btn gray" onclick="calcPress('8')">8</button><button class="btn gray" onclick="calcPress('9')">9</button><button class="btn orange" onclick="calcPress('/')">/</button><button class="btn gray" onclick="calcPress('4')">4</button><button class="btn gray" onclick="calcPress('5')">5</button><button class="btn gray" onclick="calcPress('6')">6</button><button class="btn orange" onclick="calcPress('*')">*</button><button class="btn gray" onclick="calcPress('1')">1</button><button class="btn gray" onclick="calcPress('2')">2</button><button class="btn gray" onclick="calcPress('3')">3</button><button class="btn orange" onclick="calcPress('-')">-</button><button class="btn gray" onclick="calcPress('0')">0</button><button class="btn gray" onclick="calcPress('.')">.</button><button class="btn blue" onclick="calcEval()">=</button><button class="btn orange" onclick="calcPress('+')">+</button><button class="btn red" onclick="calcClear()" style="grid-column:span 4">Clear</button></div></div>
<button id="calcBtn" onclick="document.getElementById('calcFloat').style.display='block'" style="position:fixed;bottom:85px;right:15px;background:#ff9800;color:white;border:none;border-radius:50%;width:55px;height:55px;font-size:1.5rem;z-index:9997;display:none;box-shadow:0 4px 10px rgba(0,0,0,0.3)">🧮</button>
<script>
{{{{timer_script}}}}
if(window.location.pathname.startsWith('/cbt/')){{
  document.getElementById('fixedAdBar').style.display='none';
  document.getElementById('cbtSmallAd').style.display='flex';
}} else {{
  document.getElementById('fixedAdBar').style.display='flex';
  document.getElementById('cbtSmallAd').style.display='none';
}}
let mainAdInterval = {AD_REFRESH_MAIN} * 1000;
let cbtAdInterval = {AD_REFRESH_CBT} * 1000;
setInterval(function(){{
 let adBar=document.getElementById('fixedAdBar');
 if(adBar && adBar.style.display!=='none' &&!document.hidden){{
  try{{ let ns=document.createElement('script'); ns.src='https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js'; document.getElementById('adContainer').appendChild(ns); }}catch(e){{}}
 }}
}}, mainAdInterval);
setInterval(function(){{
 let cbtAd=document.getElementById('cbtSmallAd');
 if(cbtAd && cbtAd.style.display!=='none'){{
  try{{ let ns=document.createElement('script'); ns.src='https://www.highrevenueformat.com/{FIXED_AD_KEY}/invoke.js'; document.getElementById('cbtAdInner').appendChild(ns); }}catch(e){{}}
 }}
}}, cbtAdInterval);
function calcPress(v){{ document.getElementById('calcDisplay').value += v; }}
function calcClear(){{ document.getElementById('calcDisplay').value = ''; }}
function calcEval(){{ try{{ document.getElementById('calcDisplay').value = eval(document.getElementById('calcDisplay').value); }}catch(e){{ document.getElementById('calcDisplay').value='Error'; }} }}
(function(){{
 let saved = localStorage.getItem('motiz_theme') || 'dark';
 document.body.classList.remove('light','dark');
 document.body.classList.add(saved);
 let btn=document.getElementById('themeToggle');
 if(btn) btn.innerText = saved==='light'? '☀️ Light' : '🌙 Dark';
}})();
function toggleTheme(){{
 playClickSound();
 let isLight = document.body.classList.contains('light');
 document.body.classList.remove('light','dark');
 if(isLight){{ document.body.classList.add('dark'); localStorage.setItem('motiz_theme','dark'); document.getElementById('themeToggle').innerText='🌙 Dark'; }}
 else {{ document.body.classList.add('light'); localStorage.setItem('motiz_theme','light'); document.getElementById('themeToggle').innerText='☀️ Light'; }}
}}
function playClickSound(){{ try{{ let ctx=new (window.AudioContext||window.webkitAudioContext)(); let o=ctx.createOscillator(); o.frequency.value=600; o.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.08); }}catch(e){{}} }}
document.addEventListener('click', function(e){{ if(e.target.closest('.btn, a, button,.friend-card,.bg-option')) playClickSound(); }});
</script>
</body></html>"""

def get_header(nickname,user, show_nav=True, show_favicon=False, is_home=False):
    if not user: return ""
    if is_home:
        exit_html = ""
    else:
        exit_html = f'<button onclick="location.href=\'/main\'" class="exit-btn">⬅️</button>'
    favicon_html = f'<img src="{FAVICON_URL}" class="logo">' if show_favicon else ""
    theme_html = f'<button class="theme-btn" id="themeToggle" onclick="toggleTheme()">🌙</button>'
    unread = get_unread_count(nickname) if nickname!='motiz_support' else 0
    bell = f" 🔔({unread})" if unread>0 else ""
    is_support = nickname=='motiz_support'
    verified = '<span class=badge gold>✓ MOTIZ SUPPORT</span>' if is_support else ('<span class=badge verified-paid>✓ Verified Paid</span>' if is_user_paid(user) else "")
    nav_html = f"""<div class="nav"><a href="/main">🏠 Home</a><a href="/exam">✍️ CBT</a><a href="/daily">🏆 Daily</a><a href="/lessons">🎓 Lessons</a><a href="/community">🌍 Community</a><a href="/chat">💬 Chat{bell}</a><a href="/me">👤 Me</a><a href="/complain">📩 Complain</a></div>""" if show_nav else ""
    return f"""<div class="header">{favicon_html}{exit_html}<h1 style="color:white!important">MOTIZ {verified}</h1>{theme_html}</div>{nav_html}"""

@app.route('/manifest.json')
def manifest():
    return Response(json.dumps({"name":"MOTIZ E-LEARNING","short_name":"MOTIZ","start_url":"/main","display":"standalone","background_color":"#0f3460","theme_color":"#0f3460","icons":[{"src":FAVICON_URL,"sizes":"192x192","type":"image/png"}]}), mimetype='application/json')

@app.route('/sw.js')
def sw():
    return Response("""
self.addEventListener('install', e=>self.skipWaiting());
self.addEventListener('activate', e=>self.clients.claim());
self.addEventListener('fetch', e=>{ e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))) });
self.addEventListener('push', function(event){
  const data = event.data? event.data.json() : {title:'MOTIZ E-LEARNING', body:'New message from friend'};
  event.waitUntil(self.registration.showNotification(data.title, {body:data.body, icon:'https://i.imgur.com/5TCBgkN.png', badge:'https://i.imgur.com/5TCBgkN.png', vibrate:[200,100,200]}));
});
self.addEventListener('notificationclick', function(event){ event.notification.close(); event.waitUntil(clients.openWindow('/chat')); });
""", mimetype='application/javascript')

@app.route('/save-subscription', methods=["POST"])
@login_required
def save_sub(nickname, user):
    try:
        sub = request.get_json()
        with DBSession() as db:
            db.execute(sa.text("UPDATE users SET push_sub=:s WHERE nickname=:u"), {"s": json.dumps(sub), "u": nickname})
            db.commit()
        return {"ok": True}
    except:
        return {"ok": False}

@app.route('/check_unread')
@login_required
def check_unread(nickname, user):
    return Response(json.dumps({"count": get_unread_count(nickname)}), mimetype="application/json")

@app.route('/')
def splash():
    return render_template_string(f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Welcome</title><link rel="icon" type="image/png" href="{FAVICON_URL}"><meta http-equiv="refresh" content="10;url=/login">
<style>body{{margin:0;background:linear-gradient(135deg,#0f3460,#16213e);color:white;font-family:Segoe UI;display:flex;justify-content:center;align-items:center;height:100vh;flex-direction:column;text-align:center}}.logo{{font-size:2.2rem;font-weight:bold;line-height:1.3}}.progress-bar{{width:200px;height:8px;background:#fff3;border-radius:10px;overflow:hidden;margin-top:20px}}.progress-fill{{height:100%;width:0%;background:white;animation:load 10s linear forwards}} @keyframes load{{0%{{width:0%}}100%{{width:100%}}}} </style></head><body>
<audio id="bgMusic" loop preload="auto"><source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg"></audio>
<div class="logo">MOTIZ<br>E-LEARNING<br>INSTITUTION</div><div class="subtext" style="margin-top:10px">Learn. Practice. Excel. WAEC STANDARD</div><div class="progress-bar"><div class="progress-fill"></div></div>
<script>
document.addEventListener('click', function(){{
  var a=document.getElementById('bgMusic');
  if(a){{ a.play().catch(()=>{{}}); }}
}}, {{once:true}});
window.addEventListener('load', function(){{
  var a=document.getElementById('bgMusic');
  if(a){{ a.play().catch(()=>{{}}); }}
}});
</script>
</body></html>""")

@app.route('/register', methods=["GET","POST"])
def register():
    if get_user()[1]: return redirect("/main")
    error = ""; ref = request.args.get('ref')
    if request.method == "POST":
        nickname = request.form.get("nickname","").strip().lower()
        if nickname == 'motiz_support':
            error = "<div class=error>Nickname reserved</div>"
        else:
            with DBSession() as db:
                exists = db.execute(sa.text("SELECT nickname FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
                if exists: error = "<div class=error>Nickname taken</div>"
                else:
                    name = f"{request.form['surname']} {request.form['other']}"
                    db.execute(sa.text("INSERT INTO users (nickname,name,password,class,dept,referred_by,last_seen) VALUES (:u,:n,:p,:c,:d,:r,NOW())"), {"u": nickname, "n": name, "p": request.form['password'], "c": request.form['class'], "d": request.form.get('dept',''), "r": ref})
                    if ref: db.execute(sa.text("INSERT INTO referrals (referrer, referred) VALUES (:r, :ref)"), {"r": ref, "ref": nickname})
                    db.commit()
                    session["nickname"] = nickname; return redirect("/main")
    js = """<script>function d(){let c=document.getElementById('class').value;let x=document.getElementById('deptBox');x.innerHTML='';if(['SS1','SS2','SS3'].includes(c)){x.innerHTML='<label>Department *</label><select name=dept required><option value="">Select Department</option><option>Science</option><option>Commercial</option><option>Art</option></select>'}else{x.innerHTML='<input type=hidden name=dept value=>';}}</script>"""
    form = f"<div class='card'><h2>Register - WAEC Standard for SS3</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input name=surname placeholder='Surname' required><input name=other placeholder='Other Name' required><input type=password name=password placeholder='Password' required><select name=class id=class onchange=d() required><option value=''>Select Class</option>{''.join([f'<option>{c}</option>' for c in CLASSES])}</select><div id=deptBox></div><button class=btn>Register</button><p>Already have account? <a href=/login>Login</a></p></form></div>{js}"
    return render_template_string(BASE, title="Register", header="", content=Markup(form), timer_script="")

@app.route('/login', methods=["GET","POST"])
def login():
    if get_user()[1]: return redirect("/main")
    error = ""
    if request.method == "POST":
        nickname = request.form["nickname"].strip().lower()
        pwd = request.form["password"]
        with DBSession() as db:
            u = db.execute(sa.text("SELECT * FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
            if u and u["password"] == pwd: session["nickname"] = nickname; return redirect("/main")
            else: error = "<div class=error>Invalid Nickname or Password</div>"
    return render_template_string(BASE, title="Login", header="", content=Markup(f"<div class='card'><h2>Login</h2>{error}<form method=POST><input name=nickname placeholder='Nickname' required><input type=password name=password placeholder=Password required><button class=btn>Login</button><p style='text-align:center;margin-top:15px;font-size:0.9rem'>Don't have an account? <a href=/register style='color:#0f3460;font-weight:bold;text-decoration:underline'>Click to Register</a></p></form></div>"), timer_script="")

@app.route('/main')
@login_required
def main(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname})
        db.commit()
    pinned_html = ""
    if PINNED_NOTICE:
        try: pin = json.loads(PINNED_NOTICE); pinned_html = f"<div class='card' style='border:2px solid gold'><div class=notice-title>📌 {pin['title']}</div>{pin['text']}</div>"
        except: pinned_html = f"<div class='card' style='border:2px solid gold'><b>📌 PINNED:</b> {PINNED_NOTICE}</div>"
    notices_html = ""
    for n in NOTICES:
        media = ""
        if n.get('media_link'):
            link = n['media_link']
            if any(x in link.lower() for x in ['.mp4','.webm','video']):
                media = f"<video src='{link}' controls class='lesson-media'></video>"
            else:
                media = f"<img src='{link}' class='lesson-media'>"
        time_12 = format_12h(n.get('created_at',''))
        notices_html += f"<div class='card'><div class=notice-title>📢 {n['title']}</div>{n['text']}{media}<small style='float:right'>{time_12}</small></div>"
    return render_template_string(BASE, title="Home", header=Markup(get_header(nickname,user, show_nav=True, show_favicon=True, is_home=True)), content=Markup(f"<div class='card'><h2>Welcome {user['name']}</h2><p><b>Class:</b> {user['class']} {user.get('dept','')}</p><p><b>Standard:</b> {'WAEC PAST QUESTIONS' if 'SS3' in user['class'] else 'Graded for '+user['class']}</p></div>{pinned_html}<h3>General Notice</h3>{notices_html}<a class=btn href=/exam>Start CBT Exam (WAEC Standard)</a><a class=btn orange href=/daily>🏆 Daily Challenge (FREE)</a>"), timer_script="")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/login")
@app.route('/exam')
@login_required
def exam(nickname, user):
    key = f"{user['class']}_{user['dept']}" if user['dept'] else user['class']
    subs = SUBJECTS.get(key, [])
    if not subs:
        return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=error>No subjects for your class yet</div>"), timer_script="")
    if user.get('payment_verified_date'):
        try:
            verified_date = datetime.strptime(user['payment_verified_date'], "%Y-%m-%d").date()
            if date.today() > verified_date + timedelta(days=30):
                with DBSession() as db:
                    db.execute(sa.text("UPDATE users SET is_verified=FALSE, q_cycle='free' WHERE nickname=:u"), {"u": nickname})
                    db.commit()
                user['is_verified'] = False
        except: pass
    sub_btns = ""
    with DBSession() as db:
        for s in subs:
            full_key = f"{key}_{s}"
            prog = db.execute(sa.text("SELECT used FROM cbt_progress WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key}).scalar()
            if prog is None: prog = 0
            total_q = db.execute(sa.text("SELECT COUNT(*) FROM questions WHERE key=:k"), {"k": full_key}).scalar() or 0
            limit = FREE_Q if not is_user_paid(user) else FREE_Q + PAID_Q
            done = min(prog, total_q, limit)
            emoji = subj_emoji(s)
            waec_tag = " WAEC" if "SS3" in key else ""
            if done >= limit or (total_q>0 and done >= total_q):
                btn = f"<div class='card' style='border:2px solid #28a745'><b>{emoji} {s}{waec_tag}</b><br><small>✅ Completed {done}/{min(limit,total_q)}</small><br><a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}?redo=1'>🔄 Redo / Reset</a></div>"
            else:
                if not is_user_paid(user) and prog >= FREE_Q:
                    btn = f"<div class='card cbt-btn-fix' style='border:2px solid #e94560'><b>{emoji} {s}{waec_tag}</b><br><small>🔒 Pay to continue (10/{FREE_Q} free done) - WAEC Standard</small><br><a class='btn red cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'>Unlock - Pay ₦{QUESTION_PRICE}</a></div>"
                else:
                    btn = f"<a class='btn blue cbt-btn-fix' href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(s)}'><span>{emoji} {s}{waec_tag}</span><br><small>{done}/{min(limit,total_q)} done - {'WAEC' if 'SS3' in key else 'Graded'}</small></a>"
            sub_btns += btn
    content = f"<div class='card'><h2>Subjects for {user['class']} {user.get('dept','')} - {'WAEC STANDARD' if 'SS3' in key else 'Graded'}</h2>{sub_btns}</div>"
    return render_template_string(BASE, title="CBT", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/cbt/<path:key>/<path:sub>', methods=["GET","POST"])
@login_required
def cbt_exam(nickname, user, key, sub):
    key = urllib.parse.unquote(key); sub = urllib.parse.unquote(sub)
    full_key = f"{key}_{sub}"
    redo = request.args.get('redo')
    with DBSession() as db:
        if redo:
            db.execute(sa.text("UPDATE cbt_progress SET used=0 WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key})
            db.commit()
            return redirect(f"/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}")
        all_count = db.execute(sa.text("SELECT COUNT(*) FROM questions WHERE key=:k"), {"k": full_key}).scalar() or 0
        if all_count == 0:
            return render_template_string(BASE, title="Error", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>😕 No Questions Yet for {subj_emoji(sub)} {sub}</h2><p>Admin will upload 100 WAEC questions</p></div>"), timer_script="")
        prog = db.execute(sa.text("SELECT used FROM cbt_progress WHERE nickname=:u AND subject_key=:k"), {"u": nickname, "k": full_key}).scalar()
        if prog is None:
            db.execute(sa.text("INSERT INTO cbt_progress (nickname, subject_key, used) VALUES (:u, :k, 0) ON CONFLICT (nickname, subject_key) DO NOTHING"), {"u": nickname, "k": full_key})
            db.commit()
            prog = 0
    total_limit = FREE_Q + PAID_Q if is_user_paid(user) else FREE_Q
    if prog >= total_limit or prog >= all_count:
        if not is_user_paid(user) and prog >= FREE_Q:
            with DBSession() as db: pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='questions' AND status='Pending'"), {"u": nickname}).scalar()
            if pending:
                content = "<div class=card><h2>⏳ Payment Under Review</h2><p>Admin verifying.</p></div>"
            else:
                content = f'<div class=card><h2>🔒 Unlock 90 More WAEC for {subj_emoji(sub)} {sub}</h2><p>Total 100 Qs WAEC Standard: 10 free + 90 paid</p><p><b>Pay &#8358;{QUESTION_PRICE} for 30 days</b></p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Account:</b><input class=readonly-box readonly value="{PALMPAY_ACCOUNT}"><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/questions><input name=bank_used placeholder="Bank you used" required><input name=account_name placeholder="Account Name" required><button class=btn>Submit</button></form><a class=btn blue href="/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1">🔄 Redo Free 10</a></div>'
            return render_template_string(BASE, title="Paywall", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    start_index = prog
    end_index = min(start_index + BATCH_SIZE, total_limit, all_count)
    with DBSession() as db:
        batch_q = db.execute(sa.text(f"SELECT * FROM questions WHERE key=:k ORDER BY id ASC LIMIT :limit OFFSET :off"), {"k": full_key, "limit": end_index-start_index, "off": start_index}).mappings().all()
    questions = [dict(q) for q in batch_q]
    for q in questions:
        try: q['options'] = json.loads(q['options'])
        except: q['options'] = []
    if not questions:
        return render_template_string(BASE, title="Done", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>✅ Completed {sub} WAEC</h2><a class=btn href=/exam>Back to Subjects</a><a class=btn blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo</a></div>"), timer_script="")
    time_per_q = 60 if sub in CALC_SUBJECTS else 45 if "SS3" in key else 30
    batch_time = len(questions) * time_per_q
    calc_script = "document.getElementById('calcBtn').style.display='block';" if sub in CALC_SUBJECTS else "document.getElementById('calcBtn').style.display='none';"
    if request.method == "POST":
        score = 0; result_html = ""
        for i,q in enumerate(questions):
            user_ans = request.form.get(f"q{i}")
            if user_ans == q["ans"]: score += 1
            display_ans = user_ans if user_ans else "Not Answered (Marked WRONG)"
            result_html += f"<div class='card'><h4>Q{start_index + i + 1}: {q['q']}</h4><p><b>Your Answer:</b> {display_ans}</p><p><b>Correct:</b> {q['ans']}</p></div>"
        total = len(questions); wrong = total - score
        new_done = prog + total
        with DBSession() as db:
            db.execute(sa.text("UPDATE cbt_progress SET used=:u WHERE nickname=:n AND subject_key=:k"), {"u": new_done, "n": nickname, "k": full_key})
            db.execute(sa.text("UPDATE users SET q_used=q_used+:t, correct=correct+:c, wrong=wrong+:w WHERE nickname=:u"), {"t": total, "c": score, "w": wrong, "u": nickname})
            db.commit()
        remaining = min(total_limit, all_count) - new_done
        next_btn = f"<a class=btn href=/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}>Next 10 - {remaining} left - WAEC</a>" if remaining>0 else f"<a class=btn blue href='/cbt/{urllib.parse.quote(key)}/{urllib.parse.quote(sub)}?redo=1'>🔄 Redo {sub} WAEC</a>"
        sound_js = "let ctx=new (window.AudioContext||window.webkitAudioContext)(); let notes=[523,659,784,1046]; notes.forEach((f,i)=>{let o=ctx.createOscillator(); o.frequency.value=f; o.connect(ctx.destination); o.start(ctx.currentTime+i*0.15); o.stop(ctx.currentTime+i*0.15+0.3);});" if score/total >=0.5 else "let ctx=new (window.AudioContext||window.webkitAudioContext)(); let o=ctx.createOscillator(); o.type='sawtooth'; o.frequency.value=150; o.connect(ctx.destination); o.start(); o.stop(ctx.currentTime+0.6);"
        content = f"<div class='card'><h2>🎉 RESULT {subj_emoji(sub)} {sub} {'WAEC' if 'SS3' in key else ''}</h2><p><b>Score: {score}/{total}</b> - {'WAEC Standard' if 'SS3' in key else 'Graded'}</p><p>Completed: {new_done}/{min(total_limit,all_count)}</p></div>{result_html}{next_btn}<a class=btn blue href=/exam>Back to Subjects</a><script>setTimeout(()=>{{try{{{sound_js}}}catch(e){{}}}},500)</script>"
        return render_template_string(BASE, title="Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")
    q_html = ""
    for i,q in enumerate(questions):
        options = "".join([f"<label class=option><input type=radio name=q{i} value=\"{opt}\" required><span>{opt}</span></label>" for opt in q["options"]])
        q_html += f"<div class=card id=q{i}><p><b>Question {start_index + i + 1} {'WAEC' if 'SS3' in key else ''}</b></p><p>{q['q']}</p>{options}</div>"
    timer_js = Markup(f"""
    let timeLeft = {batch_time};
    let timerInterval = null;
    const timerEl = document.createElement('div');
    timerEl.className = 'timer';
    document.querySelector('.container').prepend(timerEl);
    function updateTimer(){{
        if(timeLeft < 0) timeLeft = 0;
        let m = Math.floor(timeLeft / 60); let s = timeLeft % 60; s = s < 10? '0' + s : s;
        timerEl.innerHTML = '⏰ TIME LEFT: ' + m + ':' + s + ' | {subj_emoji(sub)} {sub} {'WAEC' if 'SS3' in key else ''} - {time_per_q}s per Q';
        if(timeLeft <= 0){{
            clearInterval(timerInterval);
            timerEl.innerHTML = '⏰ TIME UP! Auto-submitting... Unanswered = WRONG';
            document.getElementById('cbt_form').submit();
            return;
        }}
        timeLeft--;
    }}
    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);
    {calc_script}
    """)
    content = f"<form method=POST id=cbt_form><h2 style='background:#0f3460;color:white;text-align:center;padding:10px;border-radius:8px'>{subj_emoji(sub)} {sub} {'WAEC STANDARD' if 'SS3' in key else ''} - Batch {math.floor(prog/BATCH_SIZE)+1}</h2><p style='text-align:center'>{time_per_q}s per Q WAEC (Total {batch_time//60}:{batch_time%60:02d})</p>{q_html}<button class='btn orange'>Submit WAEC</button></form>"
    return render_template_string(BASE, title=f"{sub} WAEC", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/confirm/<t>', methods=["POST"])
@login_required
def confirm(nickname, user, t):
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO payments (nickname, name, type, status, bank_used, account_name, date_paid) VALUES (:u, :n, :t, 'Pending', :b, :a, :d)"),
        {"u": nickname, "n": user["name"], "t": t, "b": request.form["bank_used"], "a": request.form["account_name"], "d": str(date.today())});
        db.commit()
    return render_template_string(BASE, title="Sent", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class='card'><h2>✅ Request Sent - WAEC Access</h2><p>Admin will verify within 24hrs</p></div>"), timer_script="")
@app.route('/lessons')
@login_required
def lessons(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if user.get('lesson_expiry'):
            try:
                exp = datetime.strptime(str(user['lesson_expiry']), "%Y-%m-%d").date()
                if date.today() > exp:
                    db.execute(sa.text("UPDATE users SET lesson_expiry=NULL WHERE nickname=:u"), {"u": nickname}); db.commit()
                    user['lesson_expiry']=None
            except: pass
        if is_user_paid(user) or user.get('lesson_expiry'):
            all_lessons = db.execute(sa.text("SELECT * FROM lessons WHERE class=:c AND (dept=:d OR dept='' OR dept IS NULL) ORDER BY subject ASC"), {"c": user['class'], "d": user.get('dept','')}).mappings().all()
            if not all_lessons:
                return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🎓 No lessons yet for {user['class']} {user.get('dept','')} - WAEC Standard loading...</h2></div>"), timer_script="")
            by_subject = {}
            for l in all_lessons:
                if l['subject'] not in by_subject:
                    by_subject[l['subject']] = l
            html = f"<div class=card><h2>🎓 Lessons for {user['class']} {user.get('dept','')} - {len(by_subject)} Subjects - {'WAEC STANDARD' if 'SS3' in user['class'] else 'Graded'}</h2></div>"
            for subj, l in by_subject.items():
                media = ""
                if l.get('media_link'):
                    link = l['media_link']
                    if any(x in link.lower() for x in ['.mp4','.webm','video']):
                        media = f"<video src='{link}' controls style='width:100%;border-radius:8px;max-height:300px'></video>"
                    else:
                        media = f"<img src='{link}' style='width:100%;border-radius:8px;max-height:300px'>"
                d12 = format_12h(l['date'])
                waec_badge = " <span style='background:gold;color:#0f3460;padding:2px 6px;border-radius:5px;font-size:0.7rem'>WAEC</span>" if "SS3" in l['class'] else ""
                html += f"<div class=card style='border-left:5px solid #0f3460'><h3>{subj_emoji(l['subject'])} {l['subject']}{waec_badge}</h3><h4>{l['title']}</h4><p>{l['notes']}</p>{media}<small>📅 {d12}</small></div>"
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")
        pending = db.execute(sa.text("SELECT * FROM payments WHERE nickname=:u AND type='lessons' AND status='Pending'"), {"u": nickname}).scalar()
        if pending:
            return render_template_string(BASE, title="Lessons", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>⏳ Payment Under Review - WAEC Lessons</h2></div>"), timer_script="")
    return render_template_string(BASE, title="Pay Lesson", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🔒 Unlock WAEC Lessons - ₦{LESSON_PRICE}/30days</h2><p>WAEC Standard for SS3</p><p><b>Bank:</b> {PALMPAY_BANK}<br><b>Acct:</b><input class=readonly-box readonly value={PALMPAY_ACCOUNT}><br><b>Name:</b> {PALMPAY_NAME}</p><form method=POST action=/confirm/lessons><input name=bank_used placeholder='Bank you used' required><input name=account_name placeholder='Account Name' required><button class=btn>Submit</button></form></div>"), timer_script="")

@app.route('/daily', methods=["GET","POST"])
@login_required
def daily_challenge_page(nickname, user):
    today = date.today()
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        todays = db.execute(sa.text("SELECT * FROM daily_challenge WHERE day=:d ORDER BY id ASC LIMIT 10"), {"d": str(today)}).mappings().all()
        leaderboard = db.execute(sa.text("SELECT nickname, name, score FROM daily_scores WHERE day=:d ORDER BY score DESC, created_at ASC LIMIT 10"), {"d": str(today)}).mappings().all()
        leader_html = "<div class=card style='border:2px solid gold'><h3>🏆 Leaderboard Today - Top 10 WAEC</h3>"
        if not leaderboard:
            leader_html += "<p>No scores today yet. Be first!</p>"
        else:
            for i, lb in enumerate(leaderboard, 1):
                medal = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}."
                leader_html += f"<p>{medal} <b>{lb['name']} (@{lb['nickname']})</b> - {lb['score']}/10</p>"
        leader_html += "</div>"
        if not todays:
            return render_template_string(BASE, title="Daily Challenge", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🏆 Daily Challenge FREE WAEC Mix</h2><p>10 WAEC Questions Per Day</p><p>😕 No challenge for today yet.</p></div>{leader_html}"), timer_script="")
        if request.method == "POST":
            score = 0
            for i, q in enumerate(todays):
                ans = request.form.get(f"q{i}")
                if ans == q['ans']: score += 1
            exists = db.execute(sa.text("SELECT id FROM daily_scores WHERE nickname=:u AND day=:d"), {"u": nickname, "d": str(today)}).scalar()
            if exists:
                db.execute(sa.text("UPDATE daily_scores SET score=:s, created_at=NOW() WHERE nickname=:u AND day=:d"), {"s": score, "u": nickname, "d": str(today)})
            else:
                db.execute(sa.text("INSERT INTO daily_scores (nickname, name, score, day) VALUES (:u, :n, :s, :d)"), {"u": nickname, "n": user['name'], "s": score, "d": str(today)})
            db.commit()
            return render_template_string(BASE, title="Daily Result", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🎉 Daily WAEC Score: {score}/10</h2></div>{leader_html}"), timer_script="")
        q_html = ""
        for i, q in enumerate(todays):
            try: opts = json.loads(q['options'])
            except: opts = []
            options = "".join([f"<label class=option><input type=radio name=q{i} value=\"{opt}\" required><span>{opt}</span></label>" for opt in opts])
            q_html += f"<div class=card><p><b>Q{i+1} [{q['subject']}] WAEC</b> {q['q']}</p>{options}</div>"
        content = f"<div class=card><h2>🏆 Daily Challenge FREE WAEC - {today}</h2></div>{leader_html}<form method=POST>{q_html}<button class=btn orange>Submit Daily WAEC</button></form>"
        return render_template_string(BASE, title="Daily Challenge", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/complain', methods=["GET","POST"])
@login_required
def complain_page(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method=="POST" and request.form.get("text"):
            cnt = db.execute(sa.text("SELECT COUNT(*) FROM complaints WHERE nickname=:u AND created_at > NOW() - INTERVAL '7 days'"), {"u": nickname}).scalar() or 0
            if cnt >= 3:
                return render_template_string(BASE, title="Complain Limit", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><div class=error>❌ 3 complains per week only.</div></div>"), timer_script="")
            db.execute(sa.text("INSERT INTO complaints (nickname, name, text) VALUES (:u,:n,:t)"), {"u": nickname, "n": user["name"], "t": request.form["text"][:700]})
            db.commit()
            return redirect("/complain")
        my = db.execute(sa.text("SELECT * FROM complaints WHERE nickname=:u ORDER BY id DESC LIMIT 20"), {"u": nickname}).mappings().all()
    html = "<div class=card><h2>📩 Complain to Admin (3 per week)</h2><form method=POST><textarea name=text placeholder='Write complaint...' required maxlength=700></textarea><button class=btn>Send</button></form></div><h3>My Complaints</h3>"
    for c in my:
        ct12 = format_12h(str(c['created_at']))
        reply = f"<div style='background:#d4edda;padding:8px;margin-top:5px;border-radius:5px'><b>Admin Reply:</b> {c['reply']}</div>" if c['reply'] else "<small>⏳ Pending...</small>"
        html+=f"<div class=card><b>📝 {c['text']}</b><br><small>{ct12} - {c['status']}</small>{reply}</div>"
    return render_template_string(BASE, title="Complain", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/community', methods=["GET","POST"])
@login_required
def community(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        del_id = request.args.get('del_post')
        if del_id:
            p = db.execute(sa.text("SELECT nickname FROM posts WHERE id=:i"), {"i": int(del_id)}).scalar()
            if p == nickname or nickname == 'motiz_support':
                db.execute(sa.text("DELETE FROM posts WHERE id=:i"), {"i": int(del_id)}); db.commit()
            return redirect("/community")
        if request.method=="POST" and request.form.get("text"):
            txt = request.form["text"][:700]
            bg = request.form.get("bg","").strip()[:100]
            if nickname!= 'motiz_support' and ('http://' in txt.lower() or 'https://' in txt.lower() or 'www.' in txt.lower()):
                txt = txt.replace('http://','').replace('https://','').replace('www.','')
            db.execute(sa.text("INSERT INTO posts (nickname, name, text, bg) VALUES (:u,:n,:t,:bg)"), {"u": nickname, "n": user["name"], "t": txt, "bg": bg})
            db.commit(); return redirect("/community")
        posts = db.execute(sa.text("SELECT * FROM posts ORDER BY created_at DESC LIMIT 50")).mappings().all()
    bg_options = ["", "linear-gradient(135deg,#ff9a9e,#fecfef)", "linear-gradient(135deg,#a18cd1,#fbc2eb)", "linear-gradient(135deg,#ff6a00,#ee0979)", "linear-gradient(135deg,#667eea,#764ba2)", "linear-gradient(135deg,#f7971e,#ffd200)", "linear-gradient(135deg,#000000,#434343)", "linear-gradient(135deg,#11998e,#38ef7d)", "linear-gradient(135deg,#fc5c7d,#6a82fb)", "linear-gradient(135deg,#0f3460,#e94560)"]
    bg_html = ""
    for b in bg_options:
        if b == "":
            bg_html += f"<div class='bg-option' data-bg='' style='background:white;border:1px solid #ccc' onclick=\"selectBg(this,'')\"></div>"
        else:
            safe_b = b.replace('"', '&quot;')
            bg_html += f"<div class='bg-option' data-bg=\"{safe_b}\" style='background:{b}' onclick=\"selectBg(this, '{b}')\"></div>"
    html = f"""<div class=card>
    <form method=POST id=communityForm>
    <textarea name=text id=communityText placeholder='What is on your mind........ WAEC gist?' required maxlength=700 oninput="previewBg()"></textarea>
    <input type=hidden name=bg id=selectedBg value=''>
    <div style='margin:8px 0'><small>🎨 Choose background:</small><br>{bg_html}</div>
    <div id=bgPreview style='display:none;margin:8px 0;border-radius:12px;padding:20px;text-align:center;color:white;font-weight:bold;min-height:60px;align-items:center;justify-content:center'></div>
    <button class=btn>Post WAEC</button>
    </form>
    <script>
    function selectBg(el, bg){{
        document.querySelectorAll('.bg-option').forEach(x=>x.classList.remove('selected'));
        el.classList.add('selected');
        document.getElementById('selectedBg').value = bg;
        previewBg();
    }}
    function previewBg(){{
        let txt=document.getElementById('communityText').value;
        let bg=document.getElementById('selectedBg').value;
        let prev=document.getElementById('bgPreview');
        if(bg && txt){{ prev.style.display='flex'; prev.style.background=bg; prev.innerText=txt; }}
        else {{ prev.style.display='none'; }}
    }}
    </script>
    </div>"""
    for p in posts:
        try: likes = json.loads(p['likes'] or '[]')
        except: likes=[]
        try: comments = json.loads(p['comments'] or '[]')
        except: comments=[]
        is_motiz = p['nickname']=='motiz_support'
        is_author = p['nickname']==nickname
        if is_motiz:
            style = "style='border:3px solid gold;background:linear-gradient(135deg,#fff8e1,#ffe082)'"
            badge_html = " <span class=badge gold>✓ MOTIZ SUPPORT VERIFIED</span>"
        else:
            style = ""
            badge_html = ""
        bg_val = p.get('bg','') if isinstance(p, dict) else (p['bg'] if 'bg' in p else '')
        t12 = format_12h(str(p['created_at']))
        del_btn = f"<a class=btn red href='/community?del_post={p['id']}' onclick=\"return confirm('Delete?')\" style='padding:6px;font-size:0.8rem;margin:5px 0;width:90%;max-width:280px'>🗑️ Delete</a>" if (is_author or nickname=='motiz_support') else ""
        text_html = f"<div class='community-bg-post' style='background:{bg_val}'>{p['text']}</div>" if bg_val else f"<p>{p['text']}</p>"
        html+=f"<div class=card {style}><b>{p['name']}</b>{badge_html}<br><small>{t12}</small>{text_html}{del_btn}<div class=like-row><a class='btn gray' href='/like/{p['id']}' style='flex:1;padding:6px 8px;font-size:0.8rem;margin:0'>👍 Like ({len(likes)})</a><a class='btn gray' href='/post/{p['id']}' style='flex:1;padding:6px 8px;font-size:0.8rem;margin:0'>💬 Comment ({len(comments)})</a></div></div>"
    return render_template_string(BASE, title="Community", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/like/<int:pid>')
@login_required
def like_post(nickname, user, pid):
    with DBSession() as db:
        p = db.execute(sa.text("SELECT likes FROM posts WHERE id=:i"), {"i": pid}).scalar()
        if p is not None:
            try: likes=json.loads(p or '[]')
            except: likes=[]
            if nickname in likes: likes.remove(nickname)
            else: likes.append(nickname)
            db.execute(sa.text("UPDATE posts SET likes=:l WHERE id=:i"), {"l": json.dumps(likes), "i": pid}); db.commit()
    return redirect("/community")

@app.route('/post/<int:pid>', methods=["GET","POST"])
@login_required
def post_detail(nickname, user, pid):
    with DBSession() as db:
        p = db.execute(sa.text("SELECT * FROM posts WHERE id=:i"), {"i": pid}).mappings().first()
        if not p: return redirect("/community")
        if request.method=="POST" and request.form.get("comment"):
            try: comments=json.loads(p['comments'] or '[]')
            except: comments=[]
            comments.append({"user": nickname, "name": user["name"], "text": request.form["comment"][:300], "time": str(datetime.now(NIGERIA_TZ))})
            db.execute(sa.text("UPDATE posts SET comments=:c WHERE id=:i"), {"c": json.dumps(comments), "i": pid}); db.commit()
            return redirect(f"/post/{pid}")
        try: comments=json.loads(p['comments'] or '[]')
        except: comments=[]
        bg_val = p.get('bg','') if isinstance(p, dict) else ''
        t12 = format_12h(str(p['created_at']))
        post_display = f"<div class='community-bg-post' style='background:{bg_val}'>{p['text']}</div>" if bg_val else f"<p>{p['text']}</p>"
        html = f"<div class=card><b>{p['name']}</b><br><small>{t12}</small>{post_display}</div><h3>Comments ({len(comments)})</h3>"
        for c in comments:
            ct12 = format_12h(c.get('time',''))
            html+=f"<div class=card><b>{c['name']}</b><p>{c['text']}</p><small>{ct12}</small></div>"
        html+=f"<div class=card><form method=POST><textarea name=comment placeholder='Add comment WAEC' required></textarea><button class=btn>Comment</button></form></div>"
    return render_template_string(BASE, title="Post", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/chat')
@login_required
def chat(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        friends = user.get('friends', [])
        blocked = user.get('blocked', [])
        friend_cards = ""
        for f in friends:
            if f in blocked: continue
            if f == 'motiz_support':
                friend_cards+=f"<a href=/dm/{f} class=friend-card style='border:3px solid gold;background:linear-gradient(135deg,#fff8e1,#ffe082)'><div class=friend-avatar style='background:gold;color:#0f3460'>✓</div><div><b>MOTIZ SUPPORT</b> <span class=badge style='background:gold;color:#0f3460;white-space:nowrap'>✓ VERIFIED</span><br><small>Official Support</small></div></a>"
                continue
            u = db.execute(sa.text("SELECT name,last_seen FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
            if u:
                last = format_last_seen(u['last_seen']) if u.get('last_seen') else "Unknown"
                unread = get_unread_per_friend(nickname, f)
                bell = f" <span class='unread-badge-fix' style='background:red;color:white;padding:2px 6px;border-radius:10px;font-size:0.7rem;white-space:nowrap;display:inline-flex'>🔔{unread}</span>" if unread>0 else ""
                friend_cards+=f"<a href=/dm/{f} class=friend-card><div class=friend-avatar>{f[0].upper()}</div><div><b>{u['name']}</b>{bell}<br><small>{last}</small></div></a>"
        groups = db.execute(sa.text("SELECT * FROM groups")).mappings().all()
        group_html = ""
        for g in groups:
            try: members=json.loads(g['members'] or '[]')
            except: members=[]
            if nickname in members:
                group_html+=f"<a href=/group/{g['id']} class=friend-card><div class=friend-avatar>👥</div><div><b>{g['name']}</b><br><small>{len(members)} members</small></div></a>"
    content = f"<h3>Friends ({len([x for x in friends if x!='motiz_support' and x not in blocked])})</h3>{friend_cards or '<div class=card><p>No friends yet</p><a class=btn blue href=/me>👤 Go to Me</a></div>'}<h3>Groups</h3>{group_html or '<p>No groups</p>'}<a class=btn blue href=/create_group>➕ Create Group</a>"
    return render_template_string(BASE, title="Chat", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script="")

@app.route('/block/<f>')
@login_required
def block_friend(nickname, user, f):
    if f == 'motiz_support' or f == nickname: return redirect("/chat")
    with DBSession() as db:
        u = db.execute(sa.text("SELECT friends, blocked FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        try: friends = json.loads(u['friends'] or '[]')
        except: friends = []
        try: blocked = json.loads(u['blocked'] or '[]')
        except: blocked = []
        if f in friends: friends.remove(f)
        if f not in blocked: blocked.append(f)
        db.execute(sa.text("UPDATE users SET friends=:f, blocked=:b WHERE nickname=:u"), {"f": json.dumps(friends), "b": json.dumps(blocked), "u": nickname})
        other = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
        if other:
            try: of = json.loads(other['friends'] or '[]')
            except: of = []
            if nickname in of: of.remove(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(of), "u": f})
        db.commit()
    return redirect("/chat")

@app.route('/unfriend/<f>')
@login_required
def unfriend(nickname, user, f):
    if f == 'motiz_support': return redirect("/chat")
    with DBSession() as db:
        u = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": nickname}).mappings().first()
        try: friends = json.loads(u['friends'] or '[]')
        except: friends = []
        if f in friends: friends.remove(f)
        db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(friends), "u": nickname})
        other = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).mappings().first()
        if other:
            try: of = json.loads(other['friends'] or '[]')
            except: of = []
            if nickname in of: of.remove(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(of), "u": f})
        db.commit()
    return redirect("/chat")

@app.route('/me')
@login_required
def me_page(nickname, user):
    offset = int(request.args.get('offset', 0))
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        reqs = db.execute(sa.text("SELECT * FROM friend_requests WHERE to_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()
        req_html = ""
        for r in reqs:
            req_html+=f"<div class=card><b>{r['from_nickname']}</b> sent request<br><div style='display:flex;gap:8px;justify-content:center'><a class=btn blue href=/accept/{r['from_nickname']} style='width:44%;max-width:160px'>✅ Accept</a><a class=btn red href=/reject/{r['from_nickname']} style='width:44%;max-width:160px'>❌ Reject</a></div></div>"
        all_users = db.execute(sa.text("SELECT nickname, name, class, is_verified FROM users WHERE nickname!=:u AND nickname!='motiz_support' ORDER BY RANDOM()"), {"u": nickname}).mappings().all()
        friends = user.get('friends', [])
        blocked = user.get('blocked', [])
        pending_to = [r['to_nickname'] for r in db.execute(sa.text("SELECT to_nickname FROM friend_requests WHERE from_nickname=:u AND status='Pending'"), {"u": nickname}).mappings().all()]
        filtered = [u for u in all_users if u['nickname'] not in friends and u['nickname'] not in blocked and u['nickname'] not in pending_to]
        batch = filtered[offset:offset+FRIENDS_BATCH]
        is_verified_badge = " <span class=badge style='background:#28a745;white-space:nowrap'>✓ Verified Paid</span>" if is_user_paid(user) else ""
        html = f"{req_html}<div class=card style='border:2px solid #28a745'><h2>{user['name']}{is_verified_badge} - {subj_emoji(user['class'])}</h2><p><b>Nickname:</b> {nickname}</p><p><b>Class:</b> {user['class']} {user.get('dept','')} - {'WAEC STANDARD' if 'SS3' in user['class'] else 'Graded'}</p><p><b>Referral Link:</b><input class=readonly-box readonly value='{BASE_URL}/register?ref={nickname}'></p><p><b>Bonus:</b> 5 days free per paid referral</p></div><h3>🔍 Add Friends (5)</h3>"
        for u in batch:
            html+=f"<div class=friend-card><div class=friend-avatar>{u['nickname'][0].upper()}</div><div style='flex:1'><b>{u['name']}</b><br><small>{u['nickname']} - {u['class']}</small></div><a class=btn blue href=/add_friend/{u['nickname']}?offset={offset} style='width:auto;padding:8px 15px;max-width:80px'>Add</a></div>"
        next_offset = offset + FRIENDS_BATCH
        if next_offset < len(filtered):
            html+=f"<a class='btn orange' href=/me?offset={next_offset}>🔍 Scout Next 5</a>"
        else:
            html+=f"<a class=btn gray href=/me?offset=0>🔄 Scout Again</a>"
        html+=f"<a class=btn red href=/logout style='margin-top:20px'>🚪 Logout</a>"
    return render_template_string(BASE, title="Me", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(html), timer_script="")

@app.route('/accept/<f>')
@login_required
def accept_friend(nickname, user, f):
    with DBSession() as db:
        req = db.execute(sa.text("SELECT * FROM friend_requests WHERE from_nickname=:f AND to_nickname=:u AND status='Pending'"), {"f": f, "u": nickname}).mappings().first()
        if req:
            db.execute(sa.text("UPDATE friend_requests SET status='Accepted' WHERE id=:i"), {"i": req['id']})
            u1 = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
            u2 = db.execute(sa.text("SELECT friends FROM users WHERE nickname=:u"), {"u": f}).scalar()
            try: f1=json.loads(u1 or '[]')
            except: f1=[]
            try: f2=json.loads(u2 or '[]')
            except: f2=[]
            if f not in f1: f1.append(f)
            if nickname not in f2: f2.append(nickname)
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f1), "u": nickname})
            db.execute(sa.text("UPDATE users SET friends=:f WHERE nickname=:u"), {"f": json.dumps(f2), "u": f})
            db.commit()
    return redirect("/me")

@app.route('/reject/<f>')
@login_required
def reject_friend(nickname, user, f):
    with DBSession() as db:
        db.execute(sa.text("UPDATE friend_requests SET status='Rejected' WHERE from_nickname=:f AND to_nickname=:u AND status='Pending'"), {"f": f, "u": nickname})
        db.commit()
    return redirect("/me")

@app.route('/add_friend/<f>')
@login_required
def add_friend(nickname, user, f):
    if f == nickname or f=='motiz_support': return redirect("/me")
    if f in user.get('blocked', []): return redirect("/me")
    with DBSession() as db:
        if f in user.get('friends', []): return redirect("/me")
        exists = db.execute(sa.text("SELECT * FROM friend_requests WHERE from_nickname=:u AND to_nickname=:f AND status='Pending'"), {"u": nickname, "f": f}).scalar()
        if not exists:
            db.execute(sa.text("INSERT INTO friend_requests (from_nickname, to_nickname) VALUES (:u,:f)"), {"u": nickname, "f": f})
            db.commit()
    return redirect("/me?offset="+request.args.get('offset','0'))

@app.route('/dm/<other>', methods=["GET","POST"])
@login_required
def dm_page(nickname, user, other):
    with DBSession() as db:
        if other in user.get('blocked', []):
            return render_template_string(BASE, title="Blocked", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🚫 You blocked {other}</h2></div>"), timer_script="")
        other_user = db.execute(sa.text("SELECT * FROM users WHERE nickname=:o"), {"o": other}).mappings().first()
        if not other_user: return redirect("/chat")
        try: other_blocked = json.loads(other_user.get('blocked','[]') or '[]')
        except: other_blocked = []
        if nickname in other_blocked:
            return render_template_string(BASE, title="Blocked", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<div class=card><h2>🚫 {other} blocked you</h2></div>"), timer_script="")
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        del_id = request.args.get('del_msg')
        if del_id:
            msg = db.execute(sa.text("SELECT from_nickname FROM dms WHERE id=:i"), {"i": int(del_id)}).scalar()
            if msg == nickname or nickname == 'motiz_support':
                db.execute(sa.text("DELETE FROM dms WHERE id=:i"), {"i": int(del_id)}); db.commit()
            return redirect(f"/dm/{other}")
        all_dms = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u) ORDER BY id ASC"), {"u": nickname, "o": other}).mappings().all()
        for m in all_dms:
            if m['to_nickname']==nickname:
                try: read_by=json.loads(m['read_by'] or '[]')
                except: read_by=[]
                try: delivered=json.loads(m['delivered_to'] or '[]')
                except: delivered=[]
                changed=False
                if nickname not in delivered: delivered.append(nickname); changed=True
                if nickname not in read_by: read_by.append(nickname); changed=True
                if changed:
                    db.execute(sa.text("UPDATE dms SET read_by=:r, delivered_to=:d WHERE id=:i"), {"r": json.dumps(read_by), "d": json.dumps(delivered), "i": m['id']})
        db.commit()
        if request.method=="POST" and request.form.get("text"):
            txt = request.form["text"][:700]
            reply_to = request.form.get("reply_to","")[:200]
            full_text = f"Reply to: {reply_to}\n{txt}" if reply_to else txt
            db.execute(sa.text("INSERT INTO dms (from_nickname, to_nickname, text, time) VALUES (:f,:t,:txt,:tm)"), {"f": nickname, "t": other, "txt": full_text, "tm": str(datetime.now(NIGERIA_TZ))})
            db.commit()
            return redirect(f"/dm/{other}")
        dms = db.execute(sa.text("SELECT * FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u) ORDER BY id ASC"), {"u": nickname, "o": other}).mappings().all()
    chat_html = ""
    for m in dms:
        is_me = m['from_nickname']==nickname
        try: read_by=json.loads(m['read_by'] or '[]')
        except: read_by=[]
        try: delivered=json.loads(m['delivered_to'] or '[]')
        except: delivered=[]
        if is_me:
            if m['to_nickname'] in read_by:
                tick = f"<span class=tick-seen>{TICK_SEEN}</span>"
            elif m['to_nickname'] in delivered:
                tick = f"<span class=tick-delivered>{TICK_DELIVERED}</span>"
            else:
                tick = f"<span class=tick-sent>{TICK_SENT}</span>"
        else:
            tick = ""
        cls = "me" if is_me else "other"
        t12 = format_12h(m['time'])
        text_display = m['text'].replace("\n","<br>")
        if "Reply to:" in m['text']:
            parts = m['text'].split("\n",1)
            text_display = f"<div style='background:rgba(0,0,0,0.1);padding:5px;border-radius:5px;margin-bottom:5px;font-size:0.8rem;border-left:3px solid #0f3460'>{parts[0]}</div>{parts[1] if len(parts)>1 else ''}"
        safe_text = m['text'][:80].replace("'","").replace('"',"").replace("\n"," ")
        chat_html+=f"""<div class='chat-msg {cls}' oncontextmenu="showMenu(event,{m['id']},'{safe_text}'); return false;" onclick="showMenu(event,{m['id']},'{safe_text}')">
        <div class='bubble {cls}' id='msg-{m['id']}'><div class='bubble-text'>{text_display}</div><div class='bubble-time'>{t12} {tick}</div></div></div>"""
    timer_js = Markup(f"""
    setTimeout(()=>{{ window.scrollTo(0, document.body.scrollHeight); }}, 300);
    let exitBtn = document.querySelector('.exit-btn');
    if(exitBtn) exitBtn.setAttribute('onclick', "location.replace('/chat')");
    let lastCount = {len(dms)};
    setInterval(()=>{{
        fetch('/check_dm/{other}').then(r=>r.json()).then(data=>{{
            if(data.count > lastCount){{ location.reload(); }}
        }});
    }}, 3000);
    let replyText = '';
    function showMenu(e, id, text){{
        e.preventDefault();
        let menu = document.getElementById('msgMenu');
        if(!menu){{
            menu = document.createElement('div');
            menu.id='msgMenu';
            menu.style='position:fixed;background:white;border:1px solid #ccc;border-radius:8px;padding:5px;z-index:10000;box-shadow:0 4px 10px rgba(0,0,0,0.2)';
            document.body.appendChild(menu);
        }}
        menu.innerHTML = `<button onclick="doReply(${{id}},'${{text}}')" class=btn blue style='padding:5px;margin:2px'>↩️ Reply</button><button onclick="doCopy('${{text}}')" class=btn gray style='padding:5px;margin:2px'>📋 Copy</button><button onclick="doDelete(${{id}})" class=btn red style='padding:5px;margin:2px'>🗑️ Delete</button><button onclick="this.parentElement.style.display='none'" class=btn gray style='padding:5px;margin:2px'>X</button>`;
        menu.style.left = e.pageX+'px'; menu.style.top = e.pageY+'px'; menu.style.display='block';
    }}
    function doReply(id, text){{ document.getElementById('replyPreview').style.display='flex'; document.getElementById('replyPreviewText').innerText=text.substring(0,50); document.getElementById('replyToInput').value=text; document.getElementById('msgMenu').style.display='none'; }}
    function doCopy(text){{ navigator.clipboard.writeText(text); document.getElementById('msgMenu').style.display='none'; }}
    function doDelete(id){{ if(confirm('Delete?')){{ window.location.href='/dm/{other}?del_msg='+id; }} }}
    function cancelReply(){{ document.getElementById('replyPreview').style.display='none'; document.getElementById('replyToInput').value=''; }}
    document.addEventListener('click', function(e){{ if(!e.target.closest('#msgMenu') &&!e.target.closest('.bubble')){{ let m=document.getElementById('msgMenu'); if(m) m.style.display='none'; }} }});
    """)
    verified_badge = " <span class=badge style='background:gold;color:#0f3460;white-space:nowrap'>✓ VERIFIED SUPPORT</span>" if other == 'motiz_support' else ""
    content = f"<div class=dm-actions-top><a href=/block/{other} style='background:#e94560'>🚫 Block</a><a href=/unfriend/{other} style='background:#555'>👋 Unfriend</a></div><h3>💬 {other_user['name']}{verified_badge} ({format_last_seen(other_user.get('last_seen'))})</h3><div id=chatBox>{chat_html or '<div class=card><p>💬 No messages yet</p></div>'}</div><form method=POST class=chat-input-fixed><div id=replyPreview class=reply-preview style='display:none'><span id=replyPreviewText></span><button type=button onclick='cancelReply()' style='background:red;color:white;border:none;border-radius:50%;width:20px'>X</button></div><input type=hidden name=reply_to id=replyToInput><div style='display:flex;gap:5px'><input name=text id=chatInput placeholder='Type...' required maxlength=700 style='flex:1'><button class=send-img-btn><img src={SEND_BTN_URL}></button></div></form><div id=msgMenu style='display:none'></div>"
    return render_template_string(BASE, title=f"Chat {other}", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(content), timer_script=timer_js)

@app.route('/check_dm/<other>')
@login_required
def check_dm(nickname, user, other):
    with DBSession() as db:
        cnt = db.execute(sa.text("SELECT COUNT(*) FROM dms WHERE (from_nickname=:u AND to_nickname=:o) OR (from_nickname=:o AND to_nickname=:u)"), {"u": nickname, "o": other}).scalar()
    return Response(json.dumps({"count": cnt}), mimetype="application/json")
@app.route('/create_group', methods=["GET","POST"])
@login_required
def create_group(nickname, user):
    with DBSession() as db:
        db.execute(sa.text("UPDATE users SET last_seen=NOW() WHERE nickname=:u"), {"u": nickname}); db.commit()
        if request.method=="POST" and request.form.get("name"):
            db.execute(sa.text("INSERT INTO groups (name, creator, members) VALUES (:n,:c,:m)"), {"n": request.form["name"][:50], "c": nickname, "m": json.dumps([nickname])})
            db.commit(); return redirect("/chat")
    return render_template_string(BASE, title="Create Group", header=Markup(get_header(nickname,user, show_nav=False)), content=Markup("<div class=card><h2>👥 Create WAEC Group</h2><form method=POST><input name=name placeholder='Group Name e.g SS3 WAEC Science' required><button class=btn>Create</button></form></div>"), timer_script="")

@app.route('/group/<int:gid>', methods=["GET","POST"])
@login_required
def group_chat(nickname, user, gid):
    with DBSession() as db:
        g = db.execute(sa.text("SELECT * FROM groups WHERE id=:i"), {"i": gid}).mappings().first()
        if not g: return redirect("/chat")
        try: members=json.loads(g['members'] or '[]')
        except: members=[]
        if nickname not in members: return redirect("/chat")
        if request.method=="POST" and request.form.get("text"):
            try: msgs=json.loads(g['messages'] or '[]')
            except: msgs=[]
            msgs.append({"user": nickname, "name": user["name"], "text": request.form["text"][:700], "time": str(datetime.now(NIGERIA_TZ))})
            db.execute(sa.text("UPDATE groups SET messages=:m WHERE id=:i"), {"m": json.dumps(msgs), "i": gid}); db.commit()
            return redirect(f"/group/{gid}")
        try: msgs=json.loads(g['messages'] or '[]')
        except: msgs=[]
        chat_html=""
        for m in msgs:
            chat_html+=f"<div class=card><b>{m['name']}</b><p>{m['text']}</p><small>{format_12h(m.get('time',''))}</small></div>"
        return render_template_string(BASE, title=g['name'], header=Markup(get_header(nickname,user, show_nav=False)), content=Markup(f"<h2>{g['name']} WAEC Group</h2>{chat_html}<form method=POST class=chat-input-fixed><div style='display:flex;gap:5px'><input name=text placeholder='Message WAEC group...' required style='flex:1'><button class=send-img-btn><img src={SEND_BTN_URL}></button></div></form>"), timer_script="")

@app.route('/admin/<password>')
def admin_dashboard(password):
    if password!= ADMIN_PASS: return "❌ Wrong Admin Password"
    with DBSession() as db:
        pending_payments = db.execute(sa.text("SELECT * FROM payments WHERE status='Pending' ORDER BY id DESC")).mappings().all()
        all_users = db.execute(sa.text("SELECT * FROM users ORDER BY id DESC LIMIT 100")).mappings().all()
        complaints = db.execute(sa.text("SELECT * FROM complaints WHERE status='Pending' ORDER BY id DESC")).mappings().all()
        notices = db.execute(sa.text("SELECT * FROM notices ORDER BY created_at DESC LIMIT 10")).mappings().all()
        today = str(date.today())
        daily_q = db.execute(sa.text("SELECT COUNT(*) FROM daily_challenge WHERE day=:d"), {"d": today}).scalar() or 0
        html = f"<div class=card><h2>🔑 MOTIZ ADMIN - WAEC STANDARD</h2><p>Daily WAEC Qs today: {daily_q}/10</p></div>"
        html += "<div class=card><h3>💰 Pending Payments</h3>"
        for p in pending_payments:
            html += f"<div class=card style='border:1px solid orange'><b>{p['name']} @{p['nickname']}</b> - {p['type']} - {p['bank_used']} {p['account_name']}<br><small>{p['date_paid']}</small><br><div style='display:flex;gap:5px'><a class=btn blue href=/admin/{password}/approve/{p['id']}>✅ Approve</a><a class=btn red href=/admin/{password}/reject/{p['id']}>❌ Reject</a></div></div>"
        if not pending_payments: html += "<p>No pending</p>"
        html += "</div><div class=card><h3>📩 Complaints</h3>"
        for c in complaints:
            html += f"<div class=card><b>{c['name']} @{c['nickname']}</b>: {c['text']}<br><form method=POST action=/admin/{password}/reply/{c['id']}><textarea name=reply placeholder='Reply...' required></textarea><button class=btn>Reply & Resolve</button></form></div>"
        if not complaints: html += "<p>No complaints</p>"
        html += f"</div><div class=card><h3>📢 Upload Notice + Set Daily WAEC Challenge (FREE)</h3><form method=POST action=/admin/{password}/notice><input name=title placeholder='Notice Title' required><textarea name=text placeholder='Notice text' required></textarea><input name=media_link placeholder='Optional Image/Video Link (https://)'><button class=btn>Upload Notice</button></form><hr><h4>🏆 Set Today's 10 WAEC Daily Challenge (Auto WAEC Mix)</h4><form method=POST action=/admin/{password}/set_daily><input name=day type=date value={today} required><button class=btn orange>Auto-Generate 10 WAEC Daily Challenge</button></form><p><small>Will pick 10 random from SS3 WAEC bank mix</small></p><h4>📌 Pin Notice</h4><form method=POST action=/admin/{password}/pin_notice><input name=title placeholder='Pinned Title' required><textarea name=text placeholder='Pinned text' required></textarea><button class=btn>Pin Notice</button></form><form method=POST action=/admin/{password}/unpin_notice><button class=btn gray>Unpin Notice</button></form></div>"
        html += "<div class=card><h3>📚 Upload WAEC Lesson</h3><form method=POST action=/admin/{}/upload_lesson><select name=class required><option value=''>Select Class</option>".format(password)
        for c in CLASSES: html+=f"<option>{c}</option>"
        html += "</select><input name=dept placeholder='Dept e.g Science (leave blank for JSS)'><select name=subject required><option value=''>Select Subject</option>"
        all_subjs = set(sum([v for v in SUBJECTS.values()], []))
        for s in sorted(all_subjs): html+=f"<option>{s}</option>"
        html += f"</select><input name=title placeholder='Lesson Title e.g WAEC Past Q 2022' required><textarea name=notes placeholder='Lesson Notes WAEC Standard' required></textarea><input name=media_link placeholder='Media Link'><button class=btn>Upload WAEC Lesson</button></form></div>"
        html += f"<div class=card><h3>📤 Upload WAEC Questions CSV</h3><p>CSV columns: key, q, option1, option2, option3, option4, ans<br>Key example: SS3_Science_Physics (Must match WAEC bank)</p><form method=POST action=/admin/{password}/upload_csv enctype=multipart/form-data><input type=file name=csv_file accept=.csv required><button class=btn>Upload WAEC CSV</button></form><a class=btn blue href=/admin/{password}/export_csv>📥 Export All Questions CSV</a><a class=btn orange href=/admin/{password}/reset_progress>🔄 Reset ALL User Progress (Redo)</a></div>"
        html += "<div class=card><h3>👥 Users (100 latest) - Referral & Scores</h3><table style='width:100%;font-size:0.8rem'><tr><th>Nick</th><th>Name</th><th>Class</th><th>Correct/Wrong</th><th>Verified</th></tr>"
        for u in all_users:
            html += f"<tr><td>@{u['nickname']}</td><td>{u['name']}</td><td>{u['class']}</td><td>{u['correct']}/{u['wrong']}</td><td>{'✅' if u['is_verified'] else '❌'}</td></tr>"
        html += "</table></div>"
    return render_template_string(BASE, title="Admin WAEC", header=Markup(""), content=Markup(html), timer_script="")

@app.route('/admin/<password>/approve/<int:pid>')
def admin_approve(password, pid):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        pay = db.execute(sa.text("SELECT * FROM payments WHERE id=:i"), {"i": pid}).mappings().first()
        if not pay: return redirect(f"/admin/{password}")
        nickname = pay['nickname']; ptype = pay['type']
        db.execute(sa.text("UPDATE payments SET status='Approved' WHERE id=:i"), {"i": pid})
        if ptype == 'questions':
            db.execute(sa.text("UPDATE users SET is_verified=TRUE, payment_verified_date=:d, q_cycle='paid' WHERE nickname=:u"), {"d": str(date.today()), "u": nickname})
            ref = db.execute(sa.text("SELECT referred_by FROM users WHERE nickname=:u"), {"u": nickname}).scalar()
            if ref:
                existing = db.execute(sa.text("SELECT id FROM referrals WHERE referrer=:r AND referred=:re"), {"r": ref, "re": nickname}).scalar()
                if existing:
                    db.execute(sa.text("UPDATE referrals SET paid=TRUE WHERE referrer=:r AND referred=:re"), {"r": ref, "re": nickname})
                else:
                    db.execute(sa.text("INSERT INTO referrals (referrer, referred, paid) VALUES (:r,:re,TRUE)"), {"r": ref, "re": nickname})
                ref_user = db.execute(sa.text("SELECT free_days, referral_count FROM users WHERE nickname=:u"), {"u": ref}).mappings().first()
                if ref_user:
                    already_bonus = db.execute(sa.text("SELECT bonus_given FROM referrals WHERE referrer=:r AND referred=:re"), {"r": ref, "re": nickname}).scalar()
                    if not already_bonus:
                        new_days = (ref_user['free_days'] or 0) + 5
                        new_count = (ref_user['referral_count'] or 0) + 1
                        db.execute(sa.text("UPDATE users SET free_days=:d, referral_count=:c, lesson_expiry=:exp WHERE nickname=:u"), {"d": new_days, "c": new_count, "u": ref, "exp": str(date.today() + timedelta(days=new_days))})
                        db.execute(sa.text("UPDATE referrals SET bonus_given=TRUE WHERE referrer=:r AND referred=:re"), {"r": ref, "re": nickname})
        elif ptype == 'lessons':
            db.execute(sa.text("UPDATE users SET lesson_expiry=:e WHERE nickname=:u"), {"e": str(date.today() + timedelta(days=30)), "u": nickname})
        db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/reject/<int:pid>')
def admin_reject(password, pid):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        db.execute(sa.text("UPDATE payments SET status='Rejected' WHERE id=:i"), {"i": pid}); db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/notice', methods=["POST"])
def admin_notice(password):
    if password!= ADMIN_PASS: return "❌"
    global NOTICES
    title = request.form.get('title',''); text = request.form.get('text',''); media = request.form.get('media_link','')
    new_notice = {"title": title, "text": text, "media_link": media, "created_at": str(datetime.now(NIGERIA_TZ))}
    NOTICES.insert(0, new_notice)
    set_setting("notices", json.dumps(NOTICES))
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO notices (title, text, media_link) VALUES (:t,:tx,:m)"), {"t": title, "tx": text, "m": media}); db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/pin_notice', methods=["POST"])
def admin_pin_notice(password):
    if password!= ADMIN_PASS: return "❌"
    title = request.form.get('title',''); text = request.form.get('text','')
    pin = {"title": title, "text": text, "created_at": str(datetime.now(NIGERIA_TZ))}
    set_setting("pinned_notice", json.dumps(pin))
    global PINNED_NOTICE
    PINNED_NOTICE = json.dumps(pin)
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/unpin_notice', methods=["POST"])
def admin_unpin(password):
    if password!= ADMIN_PASS: return "❌"
    set_setting("pinned_notice", "");
    global PINNED_NOTICE; PINNED_NOTICE = ""
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/upload_lesson', methods=["POST"])
def admin_upload_lesson(password):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        db.execute(sa.text("INSERT INTO lessons (class, dept, subject, title, notes, date, media_link) VALUES (:c,:d,:s,:t,:n,:dt,:m)"),
        {"c": request.form['class'], "d": request.form.get('dept',''), "s": request.form['subject'], "t": request.form['title'], "n": request.form['notes'], "dt": str(date.today()), "m": request.form.get('media_link','')})
        db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/set_daily', methods=["POST"])
def admin_set_daily(password):
    if password!= ADMIN_PASS: return "❌"
    day = request.form.get('day', str(date.today()))
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM daily_challenge WHERE day=:d"), {"d": day})
        # Auto WAEC mix: pick 10 random SS3 WAEC questions
        waec_qs = db.execute(sa.text("SELECT * FROM questions WHERE key LIKE 'SS3_%' ORDER BY RANDOM() LIMIT 10")).mappings().all()
        if not waec_qs:
            waec_qs = db.execute(sa.text("SELECT * FROM questions ORDER BY RANDOM() LIMIT 10")).mappings().all()
        for q in waec_qs:
            parts = q['key'].split('_',2)
            subj = parts[2] if len(parts)>2 else "General"
            db.execute(sa.text("INSERT INTO daily_challenge (day, subject, q, options, ans) VALUES (:d,:s,:q,:o,:a)"),
            {"d": day, "s": subj, "q": q['q'], "o": q['options'], "a": q['ans']})
        db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/reply/<int:cid>', methods=["POST"])
def admin_reply(password, cid):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        db.execute(sa.text("UPDATE complaints SET reply=:r, status='Resolved' WHERE id=:i"), {"r": request.form['reply'][:700], "i": cid}); db.commit()
    return redirect(f"/admin/{password}")

@app.route('/admin/<password>/upload_csv', methods=["POST"])
def admin_upload_csv(password):
    if password!= ADMIN_PASS: return "❌"
    file = request.files.get('csv_file')
    if not file: return "No file"
    content = file.read().decode('utf-8')
    reader = csv.DictReader(StringIO(content))
    count = 0
    with DBSession() as db:
        for row in reader:
            key = row.get('key','').strip()
            q = row.get('q','').strip()
            o1 = row.get('option1','').strip()
            o2 = row.get('option2','').strip()
            o3 = row.get('option3','').strip()
            o4 = row.get('option4','').strip()
            ans = row.get('ans','').strip()
            if key and q and o1 and ans:
                db.execute(sa.text("INSERT INTO questions (key, q, options, ans) VALUES (:k,:q,:o,:a)"),
                {"k": key, "q": q, "o": json.dumps([o1,o2,o3,o4]), "a": ans})
                count+=1
                if count % 200 ==0: db.commit()
        db.commit()
    return f"✅ Uploaded {count} WAEC Questions <a href=/admin/{password}>Back</a>"

@app.route('/admin/<password>/export_csv')
def admin_export_csv(password):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        qs = db.execute(sa.text("SELECT * FROM questions ORDER BY key ASC, id ASC")).mappings().all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['key','q','option1','option2','option3','option4','ans'])
    for q in qs:
        try: opts = json.loads(q['options'])
        except: opts = ["","","",""]
        while len(opts)<4: opts.append("")
        writer.writerow([q['key'], q['q'], opts[0], opts[1], opts[2], opts[3], q['ans']])
    csv_data = output.getvalue()
    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=motiz_waec_questions.csv"})

@app.route('/admin/<password>/reset_progress')
def admin_reset_progress(password):
    if password!= ADMIN_PASS: return "❌"
    with DBSession() as db:
        db.execute(sa.text("DELETE FROM cbt_progress"))
        db.execute(sa.text("UPDATE users SET q_used=0, correct=0, wrong=0"))
        db.commit()
    return f"✅ All progress reset - Users will redo WAEC <a href=/admin/{password}>Back</a>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)