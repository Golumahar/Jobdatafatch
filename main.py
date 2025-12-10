import feedparser
import requests
import time
import re
import hashlib # Unique ID banane ke liye
import os  # <-- Ye line zaroor jodna

# --- 1. CONFIGURATION ---
# Ab ye URL system ke secret se uthayega
FIREBASE_DB_URL = os.environ.get("FIREBASE_") 


# --- 2. MASTER RSS SOURCES ---
RSS_SOURCES = [
    {"category": "JOBS_CIVIL", "url": "https://news.google.com/rss/search?q=UPSC+IAS+SSC+CGL+CHSL+MTS+State+PSC+UPPSC+BPSC+sarkari+result&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "JOBS_BANKING", "url": "https://news.google.com/rss/search?q=IBPS+PO+Clerk+SBI+RBI+LIC+AAO+NABARD+SEBI+Bank+Recruitment&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "JOBS_DEFENCE", "url": "https://news.google.com/rss/search?q=Indian+Army+Navy+Airforce+AFCAT+CDS+NDA+DRDO+Police+Constable+SI+CRPF&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "JOBS_RAILWAY", "url": "https://news.google.com/rss/search?q=Railway+RRB+NTPC+Group+D+RRC+ALP+Technician+Metro+Rail&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "JOBS_PSU", "url": "https://news.google.com/rss/search?q=GATE+Exam+PSU+Recruitment+ONGC+NTPC+BHEL+ISRO+BARC+Scientist&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "JOBS_TEACHING", "url": "https://news.google.com/rss/search?q=CTET+UPTET+REET+KVS+NVS+Teacher+Vacancy+NEET+AIIMS+Nursing&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "EDUCATION", "url": "https://news.google.com/rss/search?q=CBSE+ICSE+Board+Result+CUET+IGNOU+DU+University+Exam+Admission&hl=en-IN&gl=IN&ceid=IN:en"},
    {"category": "GK", "url": "https://news.google.com/rss/search?q=India+Current+Affairs+General+Knowledge+Awards+Sports+Schemes+Yojna&hl=en-IN&gl=IN&ceid=IN:en"}
]

# --- 3. INTELLIGENT LOGIC ---

def generate_unique_id(title):
    """Title ka hash banata hai taaki duplicate na ho"""
    # Title se spaces aur special chars hata kar ek unique string banayenge
    clean_title = "".join(e for e in title if e.isalnum()).lower()
    # Iska MD5 hash banayenge (Short unique code)
    return hashlib.md5(clean_title.encode()).hexdigest()

def detect_qualification(text):
    text = text.lower()
    quals = []
    if "10th" in text or "matric" in text: quals.append("10th Pass")
    if "12th" in text or "inter" in text: quals.append("12th Pass")
    if "graduate" in text or "degree" in text: quals.append("Graduate")
    if "b.tech" in text or "engineering" in text: quals.append("B.Tech")
    if "diploma" in text: quals.append("Diploma")
    if "mbbs" in text or "nursing" in text: quals.append("Medical/Nursing")
    if "bed" in text or "b.ed" in text: quals.append("B.Ed/TET")
    return ", ".join(quals) if quals else "Check Notice"

def generate_dynamic_folder_name(title):
    title_upper = title.upper()
    year_match = re.search(r'202[4-6]', title)
    year = year_match.group(0) if year_match else "LATEST"
    
    name = "MISC_JOBS"
    
    # --- LEVEL 1: EXAMS ---
    if "UPSC" in title_upper: name = "UPSC_CIVIL_SERVICES"
    elif "SSC" in title_upper: name = "SSC_JOBS"
    elif "IBPS" in title_upper: name = "BANK_IBPS"
    elif "SBI" in title_upper: name = "BANK_SBI"
    elif "RBI" in title_upper: name = "BANK_RBI"
    elif "LIC" in title_upper: name = "LIC_INSURANCE"
    elif "RRB" in title_upper or "RAILWAY" in title_upper: name = "RAILWAY_JOBS"
    elif "GATE" in title_upper: name = "GATE_PSU"
    elif "CTET" in title_upper or "TET" in title_upper: name = "TEACHING_TET"
    elif "NEET" in title_upper: name = "NEET_MEDICAL"
    elif "CUET" in title_upper: name = "CUET_EXAM"
    elif "IGNOU" in title_upper: name = "IGNOU_UNIV"
    
    # --- LEVEL 2: FORCES/DEPT ---
    elif any(x in title_upper for x in ["ARMY", "NAVY", "AIRFORCE", "AFCAT", "NDA", "CDS"]):
        name = "DEFENCE_FORCES"
    elif any(x in title_upper for x in ["POLICE", "CONSTABLE", "SI ", "BSF", "CRPF"]):
        name = "POLICE_PARAMILITARY"
    elif any(x in title_upper for x in ["ISRO", "DRDO", "BARC", "SCIENTIST"]):
        name = "ISRO_DRDO_SCIENCE"
    elif any(x in title_upper for x in ["ONGC", "IOCL", "NTPC", "BHEL", "PSU"]):
        name = "PSU_JOBS"
    elif any(x in title_upper for x in ["CBSE", "ICSE", "BOARD"]):
        name = "BOARD_EXAMS"
        
    # --- LEVEL 3: FALLBACK (Garbage Filter) ---
    else:
        ignore_words = ["RECRUITMENT", "VACANCY", "RESULT", "ONLINE", "APPLY", "GOVT", "INDIA", "LATEST", "WITHOUT", "CRACK", "HOW", "LIST", "BEST", "WHAT", "PRELIMS", "MAINS", "SHIFT", "CUTOFF"]
        words = title_upper.split(' ')
        for w in words:
            clean = ''.join(e for e in w if e.isalnum())
            if len(clean) > 2 and clean not in ignore_words:
                name = clean
                break
    
    return f"{name}_{year}"

def get_update_tag(title):
    t = title.lower()
    if "result" in t or "merit" in t: return "🏆 RESULT"
    if "admit card" in t or "hall ticket" in t: return "🎫 ADMIT CARD"
    if "answer key" in t: return "🔑 ANSWER KEY"
    if "syllabus" in t: return "📖 SYLLABUS"
    if "apply" in t or "notification" in t: return "🔔 NOTIFICATION"
    if "date sheet" in t: return "📅 DATESHEET"
    return "📢 UPDATE"

# --- 4. FIREBASE ENGINE (Duplicate Proof) ---

def save_data(entry, source_category):
    try:
        timestamp = time.time()
        # Unique ID banate hain title se
        unique_id = generate_unique_id(entry.title)
        
        # --- A. GK LOGIC ---
        if source_category == "GK":
            # PUT request use karenge unique_id ke sath (POST nahi)
            target_url = f"{FIREBASE_DB_URL}/current_affairs/{unique_id}.json"
            data = {"title": entry.title, "link": entry.link, "date": entry.published, "timestamp": timestamp}
            
            requests.put(target_url, json=data)
            print(f"🌍 GK: {entry.title[:20]}...")
            return

        # --- B. JOBS/EDU LOGIC ---
        folder_name = generate_dynamic_folder_name(entry.title)
        tag = get_update_tag(entry.title)
        qual = "N/A"
        
        if "JOBS" in source_category:
            qual = detect_qualification(entry.title + " " + entry.description)

        # 1. Update Header (Isme ID ki zarurat nahi, ye overwrite hona chahiye)
        header_url = f"{FIREBASE_DB_URL}/categories/{folder_name}.json"
        requests.patch(header_url, json={
            "display_name": folder_name.replace("_", " "),
            "category_type": source_category,
            "last_updated": timestamp
        })
        
        # 2. Update Timeline (Duplicate Proof)
        # Hum unique_id use karenge taaki same khabar dobara add na ho
        timeline_url = f"{FIREBASE_DB_URL}/categories/{folder_name}/timeline/{unique_id}.json"
        
        data = {
            "title": entry.title,
            "link": entry.link,
            "date": entry.published,
            "tag": tag,
            "qualification": qual,
            "timestamp": timestamp
        }
        
        # POST ki jagah PUT use kiya
        requests.put(timeline_url, json=data)
        print(f"✅ {tag}: {entry.title[:20]} -> [{folder_name}]")

    except Exception as e:
        print(f"❌ Error: {e}")

# --- 5. RUNNER ---

def start_final_fetcher():
    print("--- 🚀 Starting DUPLICATE-PROOF SCRAPER ---")
    for source in RSS_SOURCES:
        print(f"\nScanning: {source['category']}...")
        feed = feedparser.parse(source['url'])
        if feed.bozo: continue 
        for entry in feed.entries[:8]:
            save_data(entry, source['category'])
    print("\n--- 🎉 Database Updated (No Duplicates) ---")

if __name__ == "__main__":
    start_final_fetcher()
  
