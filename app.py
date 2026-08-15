from flask import Flask, render_template, request, jsonify, redirect, url_for, session, abort, send_from_directory
import os, json, re, uuid
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from functools import wraps
import logging
from math import asin, cos, radians, sin, sqrt
import tempfile
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_dotenv_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

load_dotenv_file(os.path.join(BASE_DIR, ".env"))

DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

# --- Flask/Werkzeug logging suppression ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)  # only show warnings and errors

app = Flask(__name__)

# -----------------------------
# CONFIG
# -----------------------------
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
app.permanent_session_lifetime = timedelta(days=7)

DATA_DIR = os.path.join(BASE_DIR, "data")
DEALS_FILE = os.path.join(DATA_DIR, "deals.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")
GEOCODE_CACHE_FILE = os.path.join(DATA_DIR, "geocode_cache.json")
PASSWORD_FILE = os.path.join(BASE_DIR, "password.txt")
SITE_URL = os.environ.get("SITE_URL", "https://github.com/programmingrobot/Feast-Finder")
RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "").strip()
RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "").strip()
RECAPTCHA_MIN_SCORE = float(os.environ.get("RECAPTCHA_MIN_SCORE", "0.5"))
DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SECTIONS = ["General", "Breakfast", "Lunch", "Dinner"]
SEARCH_MIN_SCORE = 58
SEARCH_RESULT_LIMIT = 50
SEARCH_MIN_QUERY_LENGTH = 2
PRICE_FILTERS = {
    "under10": {"max": 10},
    "under15": {"max": 15},
    "under20": {"max": 20},
    "under25": {"max": 25},
    "under30": {"max": 30},
    "over30": {"min": 30},
}

# -----------------------------
# INIT FILES
# -----------------------------
def init_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DEALS_FILE):
        with open(DEALS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
    if not os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
    if not os.path.exists(GEOCODE_CACHE_FILE):
        with open(GEOCODE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
    if not os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
            f.write(generate_password_hash(DEFAULT_ADMIN_PASSWORD) if DEFAULT_ADMIN_PASSWORD else "")

init_files()

# -----------------------------
# HELPERS
# -----------------------------
def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        save_json_file(path, default)
        return default.copy() if isinstance(default, (dict, list)) else default
    if not isinstance(data, type(default)):
        save_json_file(path, default)
        return default.copy() if isinstance(default, (dict, list)) else default
    return data

def save_json_file(path, data):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.",
        suffix=".tmp",
        dir=directory,
        text=True
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except OSError:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise

def load_deals():
    return load_json_file(DEALS_FILE, {})

def save_deals(data):
    save_json_file(DEALS_FILE, data)

def load_messages():
    return load_json_file(MESSAGES_FILE, [])

def save_messages(data):
    save_json_file(MESSAGES_FILE, data)

def load_geocode_cache():
    return load_json_file(GEOCODE_CACHE_FILE, {})

def save_geocode_cache(data):
    save_json_file(GEOCODE_CACHE_FILE, data)

def load_password_hash():
    try:
        with open(PASSWORD_FILE, "r", encoding="utf-8") as f:
            password_hash = f.read().strip()
    except OSError:
        return ""
    return password_hash

def check_admin_password(password):
    if not password:
        return False

    password_hash = load_password_hash()
    if password_hash:
        try:
            if check_password_hash(password_hash, password):
                return True
        except ValueError:
            pass

    return bool(DEFAULT_ADMIN_PASSWORD) and password == DEFAULT_ADMIN_PASSWORD

def set_admin_password(password):
    with open(PASSWORD_FILE, "w", encoding="utf-8") as f:
        f.write(generate_password_hash(password))

def verify_recaptcha(token, remote_ip=None):
    if not RECAPTCHA_SITE_KEY or not RECAPTCHA_SECRET_KEY:
        return True

    if not token:
        return False

    data = {
        "secret": RECAPTCHA_SECRET_KEY,
        "response": token
    }
    if remote_ip:
        data["remoteip"] = remote_ip

    payload = urllib_parse.urlencode(data).encode("utf-8")
    verification_request = urllib_request.Request(
        "https://www.google.com/recaptcha/api/siteverify",
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
    )

    try:
        with urllib_request.urlopen(verification_request, timeout=5) as response:
            result = json.load(response)
    except (urllib_error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False

    if not result.get("success"):
        return False

    if result.get("action") and result.get("action") != "admin_login":
        return False

    score = result.get("score")
    try:
        return score is None or float(score) >= RECAPTCHA_MIN_SCORE
    except (TypeError, ValueError):
        return False

def geocode_address(location):
    cache = load_geocode_cache()
    cached = cache.get(location)
    if isinstance(cached, dict) and cached.get("lat") is not None and cached.get("lon") is not None:
        return cached

    params = urllib_parse.urlencode({
        "q": location,
        "format": "jsonv2",
        "limit": 1
    })
    geocode_request = urllib_request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={
            "User-Agent": os.environ.get("GEOCODER_USER_AGENT", "LatrobeValleyDeals/1.0"),
            "Accept": "application/json"
        }
    )

    with urllib_request.urlopen(geocode_request, timeout=10) as response:
        results = json.load(response)

    if not results:
        return None

    best_match = results[0]
    coordinates = {
        "lat": float(best_match["lat"]),
        "lon": float(best_match["lon"])
    }
    cache[location] = coordinates
    save_geocode_cache(cache)
    return coordinates

def calculate_distance_km(lat1, lon1, lat2, lon2):
    earth_radius_km = 6371.0
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)

    delta_lat = lat2_rad - lat1_rad
    delta_lon = lon2_rad - lon1_rad

    a_value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    )
    c_value = 2 * asin(sqrt(a_value))
    return earth_radius_km * c_value

def get_today_name():
    return datetime.now().strftime("%A")

def get_today_stamp():
    return datetime.now().strftime("%Y-%m-%d")

def extract_lowest_price(text):
    prices = re.findall(r"\$\s*(\d+(?:\.\d{1,2})?)", text or "")
    if not prices:
        return None
    return min(float(price) for price in prices)

def format_price(price):
    if price is None:
        return ""
    if price.is_integer():
        return f"${int(price)}"
    return f"${price:.2f}"

def normalize_deal_type(raw_type):
    deal_type = (raw_type or "").strip().capitalize()
    return deal_type if deal_type in SECTIONS else "General"

def find_deal_context(deal_id):
    wanted_id = str(deal_id or "").strip()
    if not wanted_id:
        return {}

    for company, info in load_deals().items():
        location = info.get("Details", {}).get("location", "")
        for deal in info.get("Deals", []):
            if str(deal.get("id")) == wanted_id:
                return {
                    "company": company,
                    "location": location,
                    "text": deal.get("text", "")
                }
    return {}

def get_report_display_text(report):
    report_text = report.get("deals", "")
    old_format = re.match(r"^Correction for deal ([^:]+):\s*(.*)$", report_text)
    if not old_format:
        return report_text

    deal_context = find_deal_context(old_format.group(1))
    deal_text = deal_context.get("text")
    if not deal_text:
        return report_text

    message = old_format.group(2).strip()
    return f"{deal_text}: {message}" if message else deal_text

def parse_custom_price(raw_price):
    try:
        price = float(raw_price)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return min(price, 500)

def price_matches_filter(lowest_price, price_filter, custom_price):
    if not price_filter:
        return True

    if lowest_price is None:
        return False

    if price_filter == "custom":
        return custom_price is not None and lowest_price <= custom_price

    rule = PRICE_FILTERS.get(price_filter)
    if not rule:
        return True

    if "min" in rule and lowest_price < rule["min"]:
        return False
    if "max" in rule and lowest_price > rule["max"]:
        return False
    return True

def tokenize_search_text(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())

def score_search_match(search_query, search_text):
    query = (search_query or "").strip()
    text = search_text or ""
    if not query:
        return 0
    if len(query) < SEARCH_MIN_QUERY_LENGTH:
        return 0

    if query in text:
        return 100

    query_lower = query.lower()
    text_lower = text.lower()
    if query_lower in text_lower:
        return 90

    query_words = tokenize_search_text(query)
    text_words = tokenize_search_text(text)
    if not query_words or not text_words:
        return 0

    word_scores = []
    for query_word in query_words:
        best_score = 0
        for text_word in text_words:
            if query_word == text_word:
                best_score = 1
                break
            if text_word.startswith(query_word) or query_word.startswith(text_word):
                best_score = max(best_score, 0.86)
                continue
            best_score = max(best_score, SequenceMatcher(None, query_word, text_word).ratio())
        word_scores.append(best_score)

    if min(word_scores) < 0.62:
        return 0

    average_word_score = sum(word_scores) / len(word_scores)
    phrase_score = SequenceMatcher(None, query_lower, text_lower).ratio()
    score = int(round((average_word_score * 0.82 + phrase_score * 0.18) * 100))
    return score if score >= SEARCH_MIN_SCORE else 0

def deal_matches_filters(deal, company, location, meal_filter, price_filter, custom_price, tag_filter, search_query):
    description = deal.get("text", "")
    deal_type = normalize_deal_type(deal.get("type", ""))
    haystack = f"{description} {company} {location} {deal_type} {' '.join(deal.get('days', []))}"
    haystack_lower = haystack.lower()

    if meal_filter != "All" and deal_type != meal_filter:
        return False, 0

    lowest_price = extract_lowest_price(description)
    if not price_matches_filter(lowest_price, price_filter, custom_price):
        return False, 0

    if tag_filter == "kids" and "kid" not in haystack_lower:
        return False, 0

    search_score = score_search_match(search_query, haystack)
    if search_query and search_score == 0:
        return False, 0

    return True, search_score

def build_grouped_deals(deals_data, selected_day, meal_filter, price_filter, custom_price, tag_filter, search_query):
    grouped_results = {section: [] for section in SECTIONS}
    matched_deals = []
    data_changed = False

    for company in sorted(deals_data.keys(), key=lambda x: (x or "").lower()):
        info = deals_data[company]
        location = info.get("Details", {}).get("location", "")

        for deal in sorted(info.get("Deals", []), key=lambda d: (d.get("text") or "").lower()):
            if "id" not in deal:
                deal["id"] = str(uuid.uuid4())
                data_changed = True

            if selected_day not in deal.get("days", []):
                continue

            matches_filters, search_score = deal_matches_filters(
                deal,
                company,
                location,
                meal_filter,
                price_filter,
                custom_price,
                tag_filter,
                search_query
            )
            if not matches_filters:
                continue

            lowest_price = extract_lowest_price(deal.get("text", ""))
            deal_type = normalize_deal_type(deal.get("type", ""))
            matched_deals.append({
                "id": deal["id"],
                "company": company,
                "description": deal.get("text", ""),
                "location": location,
                "type": deal_type,
                "days": deal.get("days", []),
                "price": format_price(lowest_price),
                "updated_at": deal.get("updated_at", "Current listing"),
                "search_score": search_score
            })

    if data_changed:
        save_deals(deals_data)

    if search_query:
        matched_deals = sorted(
            matched_deals,
            key=lambda deal: (-deal["search_score"], deal["company"].lower(), deal["description"].lower())
        )[:SEARCH_RESULT_LIMIT]

    for deal in matched_deals:
        grouped_results[deal["type"]].append(deal)

    return grouped_results

def render_deals(default_meal="All", default_tag="", default_q="", page_title="Latrobe Valley Food Deals", meta_description=None):
    deals_data = load_deals()
    today = get_today_name()
    selected_day = request.args.get("day", today)

    if selected_day == "Today" or selected_day not in DAYS_ORDER:
        selected_day = today

    meal_filter = request.args.get("meal", default_meal)
    if meal_filter not in ["All"] + SECTIONS:
        meal_filter = "All"

    price_filter = request.args.get("price", "")
    if price_filter not in ["", "custom"] + list(PRICE_FILTERS.keys()):
        price_filter = ""
    custom_price = parse_custom_price(request.args.get("custom_price", ""))
    if price_filter != "custom":
        custom_price = None

    tag_filter = request.args.get("tag", default_tag)
    if tag_filter not in ["", "kids"]:
        tag_filter = ""

    search_query = request.args.get("q", default_q).strip()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    if per_page not in [10, 20, 50, 100, 200]:
        per_page = 10

    grouped_results = build_grouped_deals(
        deals_data,
        selected_day,
        meal_filter,
        price_filter,
        custom_price,
        tag_filter,
        search_query
    )

    total_deals = sum(len(deals) for deals in grouped_results.values())
    active_businesses = len({
        deal["company"]
        for deals in grouped_results.values()
        for deal in deals
    })

    paginated_results = {}
    total_pages_per_section = {}

    for section, deals in grouped_results.items():
        total = len(deals)
        total_pages = max((total + per_page - 1) // per_page, 1)
        total_pages_per_section[section] = total_pages

        current_page = max(1, min(page, total_pages))
        start = (current_page - 1) * per_page
        end = start + per_page
        paginated_results[section] = deals[start:end]

    return render_template(
        "index.html",
        grouped_results=paginated_results,
        selected_day=selected_day,
        today_real=today,
        days_order=DAYS_ORDER,
        sections=SECTIONS,
        meal_filter=meal_filter,
        price_filter=price_filter,
        custom_price=custom_price,
        tag_filter=tag_filter,
        search_query=search_query,
        total_deals=total_deals,
        active_businesses=active_businesses,
        page=page,
        per_page=per_page,
        total_pages_per_section=total_pages_per_section,
        max_pages=max(total_pages_per_section.values()),
        page_title=page_title,
        meta_description=meta_description or "Find cheap food deals in Traralgon and the Latrobe Valley. Browse today's lunch, dinner, breakfast, and family meal specials near you.",
        site_url=SITE_URL
    )

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def block_bots(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        ua = (request.headers.get("User-Agent") or "").lower()
        blocked = [
            "googlebot","bingbot","gptbot","openai","anthropic",
            "claudebot","perplexitybot","ahrefsbot","semrushbot"
        ]
        if any(bot in ua for bot in blocked):
            abort(403)
        return view(*args, **kwargs)
    return wrapped


# -----------------------------
# PUBLIC ROUTES
# -----------------------------
@app.route("/")
def home():
    return render_deals()

@app.route("/traralgon-lunch-deals")
def traralgon_lunch_deals():
    return render_deals(
        default_meal="Lunch",
        default_q="Traralgon",
        page_title="Traralgon Lunch Deals",
        meta_description="Find lunch specials and cheap eats in Traralgon and nearby Latrobe Valley towns."
    )

@app.route("/morwell-food-deals")
def morwell_food_deals():
    return render_deals(
        default_q="Morwell",
        page_title="Morwell Food Deals",
        meta_description="Browse affordable food deals and meal specials around Morwell and the Latrobe Valley."
    )

@app.route("/kids-eat-free-latrobe-valley")
def kids_eat_free_latrobe_valley():
    return render_deals(
        default_tag="kids",
        page_title="Kids Eat Free Latrobe Valley",
        meta_description="Find family food deals and kids eat free specials around Traralgon, Morwell, and the Latrobe Valley."
    )

@app.route("/submit_deal", methods=["POST"])
def submit_deal():
    data = request.get_json(silent=True) or {}
    if not all(data.get(k) for k in ("name","address","email","deals")):
        return jsonify(success=False, error="All fields required")

    messages = load_messages()
    messages.append({
        "id": str(uuid.uuid4()),
        "business_name": data["name"].strip(),
        "business_address": data["address"].strip(),
        "business_email": data["email"].strip(),
        "deals": data["deals"].strip(),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "approved": False
    })
    save_messages(messages)
    return jsonify(success=True)

@app.route("/suggest_correction", methods=["POST"])
def suggest_correction():
    data = request.get_json(silent=True) or {}
    if not all(data.get(k) for k in ("deal_id", "message")):
        return jsonify(success=False, error="Tell us what you want to report"), 400

    deal_context = find_deal_context(data.get("deal_id"))
    company = (deal_context.get("company") or data.get("company") or "Deal report").strip()
    location = (deal_context.get("location") or data.get("location") or "").strip()
    deal_text = (deal_context.get("text") or data.get("deal_text") or "Unknown deal").strip()
    report_text = f"{deal_text}: {data['message'].strip()}"

    messages = load_messages()
    messages.append({
        "id": str(uuid.uuid4()),
        "business_name": company,
        "business_address": location,
        "business_email": data.get("email", "correction@visitor.local").strip(),
        "deals": report_text,
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "approved": False,
        "type": "correction"
    })
    save_messages(messages)
    return jsonify(success=True)

@app.route("/about")
def about_us():
    return render_template("about_us.html")

# -----------------------------
# JSON endpoint for all deals
# -----------------------------
@app.route("/collect_deals")
def collect_deals():
    """
    Returns the entire deals database as JSON.
    """
    deals = load_deals()
    return jsonify(deals)

@app.route("/distance_lookup", methods=["POST"])
def distance_lookup():
    data = request.get_json(silent=True) or {}
    try:
        user_lat = float(data.get("latitude"))
        user_lon = float(data.get("longitude"))
    except (TypeError, ValueError):
        return jsonify(success=False, error="Valid coordinates are required"), 400

    locations = data.get("locations", [])
    if not isinstance(locations, list) or not locations:
        return jsonify(success=False, error="Locations are required"), 400

    results = {}
    for raw_location in locations:
        location = str(raw_location).strip()
        if not location:
            continue

        try:
            coordinates = geocode_address(location)
        except (urllib_error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
            return jsonify(success=False, error="Distance lookup is unavailable right now"), 502

        if not coordinates:
            results[location] = None
            continue

        results[location] = round(
            calculate_distance_km(
                user_lat,
                user_lon,
                coordinates["lat"],
                coordinates["lon"]
            ),
            2
        )

    return jsonify(success=True, distances=results)

@app.route("/robots.txt")
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt")

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        password = request.form.get("password", "")
        recaptcha_token = request.form.get("g-recaptcha-response", "")

        if not verify_recaptcha(recaptcha_token, request.remote_addr):
            error = "reCAPTCHA verification failed. Please try again."
        elif check_admin_password(password):
            session.permanent = True
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "Incorrect password."

    return render_template("login.html", error=error, recaptcha_site_key=RECAPTCHA_SITE_KEY)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/change_password", methods=["GET", "POST"])
@admin_required
@block_bots
def change_password():
    error = None

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not check_admin_password(current_password):
            error = "Current password is incorrect."
        elif new_password != confirm_password:
            error = "New passwords do not match."
        else:
            set_admin_password(new_password)
            return redirect(url_for("admin_panel"))

    return render_template("change_password.html", error=error)

# -----------------------------
# ADMIN
# -----------------------------
@app.route("/admin")
@admin_required
@block_bots
def admin_panel():
    companies = load_deals()
    all_messages = sorted(load_messages(), key=lambda m: m.get("submitted_at", ""), reverse=True)
    reports = [message for message in all_messages if message.get("type") == "correction"]
    messages = [message for message in all_messages if message.get("type") != "correction"]
    for report in reports:
        report["display_deals"] = get_report_display_text(report)

    companies = dict(sorted(companies.items(), key=lambda i: (i[0] or "").lower()))
    for c in companies:
        companies[c]["Deals"] = sorted(
            companies[c]["Deals"],
            key=lambda d: (d.get("text") or "").lower()
        )

    return render_template("admin.html", companies=companies, messages=messages, reports=reports)

@app.route("/admin/add_company", methods=["POST"])
@admin_required
@block_bots
def add_company():
    data = request.get_json(silent=True) or {}
    supplier = data.get("supplier","").strip()
    location = data.get("location","").strip()

    if not supplier:
        return jsonify(error="Company name required"), 400

    if not location:
        return jsonify(error="Location required"), 400

    deals = load_deals()
    if supplier in deals:
        return jsonify(error="Company already exists"), 400

    deals[supplier] = {"Details":{"location":location},"Deals":[]}
    save_deals(deals)
    return jsonify(success=True)

@app.route("/admin/edit_company", methods=["POST"])
@admin_required
@block_bots
def edit_company():
    data = request.get_json(silent=True) or {}
    old_supplier = data.get("old_supplier","").strip()
    new_supplier = data.get("new_supplier","").strip()
    location = data.get("location","").strip()

    if not new_supplier:
        return jsonify(error="Company name required"), 400
    if not location:
        return jsonify(error="Location required"), 400

    deals = load_deals()

    if old_supplier not in deals:
        return jsonify(error="Original company not found"), 404
    if old_supplier != new_supplier and new_supplier in deals:
        return jsonify(error="Company name already exists"), 400

    # Update company name if changed
    if old_supplier != new_supplier:
        deals[new_supplier] = deals.pop(old_supplier)

    # Update location
    deals[new_supplier]["Details"]["location"] = location

    save_deals(deals)
    return jsonify(success=True)

@app.route("/admin/delete_company", methods=["POST"])
@admin_required
@block_bots
def delete_company():
    data = request.get_json(silent=True) or {}
    deals = load_deals()
    deals.pop(data.get("supplier"), None)
    save_deals(deals)
    return jsonify(success=True)

@app.route("/admin/add_deal", methods=["POST"])
@admin_required
@block_bots
def add_deal():
    data = request.get_json(silent=True) or {}
    supplier = data.get("supplier", "").strip()
    text = data.get("deal","").strip()
    deal_type = data.get("type","").strip()
    days = data.get("days", [])

    if not all([supplier, text, deal_type, days]):
        return jsonify(error="All fields required"), 400

    deals = load_deals()
    if supplier not in deals:
        return jsonify(error="Company not found"), 404

    new_deal = {
        "id": str(uuid.uuid4()),
        "text": text,
        "type": deal_type,
        "days": days,
        "updated_at": get_today_stamp()
    }

    deals[supplier]["Deals"].append(new_deal)
    save_deals(deals)
    return jsonify(success=True)

@app.route("/admin/edit_deal", methods=["POST"])
@admin_required
@block_bots
def edit_deal():
    data = request.get_json(silent=True) or {}

    supplier = data.get("supplier", "").strip()
    deal_id = str(data.get("deal_id", "")).strip()
    new_deal = data.get("new_deal", "").strip()
    deal_type = data.get("type", "").strip()
    days = data.get("days", [])

    if not supplier or not deal_id or not new_deal or not deal_type or not isinstance(days, list) or not days:
        return jsonify(error="Missing or invalid required fields"), 400

    deals = load_deals()

    if supplier not in deals:
        return jsonify(error="Company not found"), 404

    for deal in deals[supplier]["Deals"]:
        if str(deal.get("id")) == deal_id:
            deal["text"] = new_deal
            deal["type"] = deal_type
            deal["days"] = days
            deal["updated_at"] = get_today_stamp()
            save_deals(deals)
            return jsonify(success=True)

    return jsonify(error="Deal not found"), 404

@app.route("/admin/delete_deal", methods=["POST"])
@admin_required
@block_bots
def delete_deal():
    data = request.get_json(silent=True) or {}
    deals = load_deals()
    supplier = data.get("supplier", "").strip()
    deal_id = str(data.get("deal_id", "")).strip()

    if not supplier or not deal_id:
        return jsonify(error="Missing required fields"), 400

    if supplier not in deals:
        return jsonify(error="Supplier not found"), 404

    deals[supplier]["Deals"] = [
        d for d in deals[supplier]["Deals"]
        if str(d.get("id")) != deal_id
    ]
    save_deals(deals)
    return jsonify(success=True)

@app.route("/admin/delete_message", methods=["POST"])
@admin_required
@block_bots
def delete_message():
    data = request.get_json(silent=True) or {}
    message_id = str(data.get("id", "")).strip()
    if not message_id:
        return jsonify(error="Missing required fields"), 400

    messages = [m for m in load_messages() if str(m.get("id")) != message_id]
    save_messages(messages)
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(debug=False)
