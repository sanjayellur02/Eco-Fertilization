"""
ECO-FERTILIZATION — app.py (Upgraded v2.0)
===========================================
Changes from original:
  ✅ FIX 1: Secrets moved to .env file (no hardcoded API keys)
  ✅ FIX 2: Passwords hashed with Werkzeug (no plain text)
  ✅ FIX 3: Structured logging to eco_app.log + console
  ✅ FIX 4: Global error handlers for 404 and 500
  ✅ FIX 5: login_required decorator (no repeated if checks)
  ✅ FIX 6: Input validation on all API endpoints
  ✅ FIX 7: Database indexes for performance
  ✅ FIX 8: Session security (HttpOnly, SameSite)
  ✅ FIX 9: Auto-migrate plain-text passwords to hashed on login
"""

import sqlite3
import datetime
import logging
import os
import random
import smtplib
import string
import time
from email.mime.text import MIMEText
from functools import wraps
from collections import defaultdict
import secrets
import joblib
import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

from BestTimeToFertilizeModule import BestTimeToFertilize

load_dotenv()

# ===========================================================
# 1. LOGGING SETUP
# ===========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("eco_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===========================================================
# 2. FLASK APP & CONFIG
# ===========================================================
app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=7200,  # 2 hours
)

@app.before_request
def make_session_permanent():
    session.permanent = True
@app.context_processor
def inject_csrf():
    return {"csrf_token": generate_csrf_token()}
DATABASE = os.environ.get("DATABASE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db"))

# ===========================================================
# 3. API KEYS & CONFIGURATIONS  ← loaded from .env now
# ===========================================================
OPENWEATHER_API_KEY = os.environ["OPENWEATHER_API_KEY"]
SENDER_EMAIL        = os.environ["SENDER_EMAIL"]
SENDER_PASSWORD     = os.environ["SENDER_PASSWORD"]

# ===========================================================
# RATE LIMITER (no extra libraries needed)
# ===========================================================
_rate_limit_store = defaultdict(list)

def rate_limit(max_calls, window_seconds):
    """Blocks IPs that exceed max_calls within window_seconds."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip  = request.remote_addr or "unknown"
            key = f"{f.__name__}:{ip}"
            now = time.time()
            # Keep only recent calls within the window
            calls = [t for t in _rate_limit_store[key] if now - t < window_seconds]
            if len(calls) >= max_calls:
                return jsonify({
                    "success": False,
                    "message": f"Too many attempts. Please wait {window_seconds // 60} minute(s)."
                }), 429
            calls.append(now)
            _rate_limit_store[key] = calls
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ===========================================================
# CSRF PROTECTION
# ===========================================================
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def csrf_protect(f):
    """Rejects requests that don't include the correct CSRF token."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = (request.get_json(silent=True) or {}).get('csrf_token') or \
                request.headers.get('X-CSRF-Token') or \
                request.form.get('csrf_token')
        if not token or token != session.get('csrf_token'):
            if request.is_json or request.headers.get('X-CSRF-Token'):
                return jsonify({"success": False, "message": "Invalid CSRF token. Please refresh the page."}), 403
            return render_template("index.html", mode="scan",
                                   error="Session expired. Please refresh and try again.",
                                   is_logged_in=("user" in session)), 403
        return f(*args, **kwargs)
    return wrapper


# ===========================================================
# 4. AGRO-CLIMATIC ZONES DATABASE (unchanged from original)
# ===========================================================
AGRO_ZONES = {
    "andaman & nicobar": [
        "RICE", "COCONUT", "ARECANUT", "BANANA", "PAPAYA", "BLACK PEPPER", "RUBBER",
        "GINGER", "TURMERIC", "CLOVE", "CINNAMON", "NUTMEG", "SWEET POTATO",
        "TAPIOCA", "YAM", "PINEAPPLE", "MANGO", "LEMONGRASS", "ALOE VERA"
    ],
    "andhra pradesh": [
        "RICE", "COTTON", "CHILLI", "TOOR", "BENGAL GRAM", "GROUNDNUT", "SUNFLOWER",
        "SUGARCANE", "MAIZE", "JOWAR", "BAJRA", "RAGI", "CHICKPEA", "PIGEON PEA",
        "GREEN GRAM", "BLACK GRAM", "COWPEA", "TOBACCO", "TURMERIC", "ONION",
        "TOMATO", "BRINJAL", "OKRA", "MANGO", "BANANA", "PAPAYA", "SWEET POTATO",
        "YAM", "BEETROOT", "SUGAR BEET", "ALFALFA", "NAPIER GRASS", "CORIANDER",
        "COCONUT", "FODDER SORGHUM", "LEMONGRASS"
    ],
    "telangana": [
        "RICE", "COTTON", "CHILLI", "TOOR", "BENGAL GRAM", "GROUNDNUT", "SUNFLOWER",
        "SUGARCANE", "MAIZE", "JOWAR", "BAJRA", "RAGI", "CHICKPEA", "PIGEON PEA",
        "GREEN GRAM", "BLACK GRAM", "COWPEA", "TOBACCO", "TURMERIC", "ONION",
        "TOMATO", "BRINJAL", "OKRA", "MANGO", "BANANA", "PAPAYA", "SWEET POTATO",
        "YAM", "BEETROOT", "SUGAR BEET", "ALFALFA", "NAPIER GRASS", "CORIANDER",
        "COCONUT", "FODDER SORGHUM", "LEMONGRASS"
    ],
    "arunachal pradesh": [
        "RICE", "MAIZE", "MILLET", "POTATO", "GINGER", "TURMERIC", "ORANGE",
        "PINEAPPLE", "TEA", "CARDAMOM", "KIWI", "APPLE", "CABBAGE", "CAULIFLOWER",
        "RADISH", "BEANS", "MUSTARD", "SOYBEAN", "BLACK GRAM"
    ],
    "assam": [
        "RICE", "TEA", "JUTE", "SUGARCANE", "POTATO", "MUSTARD", "BANANA", "GINGER",
        "TURMERIC", "BLACK PEPPER", "ARECANUT", "COCONUT", "ORANGE", "PAPAYA",
        "PINEAPPLE", "JACKFRUIT", "GREEN GRAM", "BLACK GRAM", "LENTIL", "PEAS",
        "CABBAGE", "CAULIFLOWER", "BRINJAL", "OKRA", "TOOR", "LEMONGRASS"
    ],
    "bihar": [
        "RICE", "WHEAT", "MAIZE", "TOOR", "BENGAL GRAM", "JUTE", "SUGARCANE", "POTATO",
        "LENTIL", "PEAS", "CHICKPEA", "PIGEON PEA", "MUSTARD", "LINSEED", "SUNFLOWER",
        "BANANA", "MANGO", "GUAVA", "LITCHI", "BRINJAL", "CAULIFLOWER", "CABBAGE",
        "ONION", "TOMATO", "OKRA", "YAM", "BEETROOT", "FODDER MAIZE", "BERSEEM"
    ],
    "chandigarh": [
        "WHEAT", "RICE", "MAIZE", "MUSTARD", "POTATO", "CAULIFLOWER", "CABBAGE",
        "CARROT", "RADISH", "SPINACH", "FODDER MAIZE", "FODDER SORGHUM", "BERSEEM",
        "TULSI", "ALOE VERA", "MINT"
    ],
    "chhattisgarh": [
        "RICE", "MAIZE", "KODO MILLET", "TOOR", "BENGAL GRAM", "SOYBEAN", "GROUNDNUT",
        "SUNFLOWER", "PIGEON PEA", "CHICKPEA", "GREEN GRAM", "BLACK GRAM", "MUSTARD",
        "LINSEED", "WHEAT", "TOMATO", "BRINJAL", "OKRA", "CABBAGE", "CAULIFLOWER",
        "POTATO", "GINGER", "TURMERIC", "LEMONGRASS"
    ],
    "dadra & nagar haveli": [
        "RICE", "RAGI", "JOWAR", "TOOR", "PIGEON PEA", "BEANS", "BANANA", "MANGO",
        "CHICKPEA", "GROUNDNUT", "SUGARCANE", "BRINJAL", "TOMATO", "CABBAGE"
    ],
    "daman & diu": [
        "BAJRA", "JOWAR", "GROUNDNUT", "COCONUT", "BEANS", "SAPOTA", "BANANA",
        "MANGO", "VEGETABLES", "FODDER SORGHUM"
    ],
    "delhi": [
        "WHEAT", "MUSTARD", "JOWAR", "BAJRA", "PADDY", "CAULIFLOWER", "CABBAGE",
        "CARROT", "RADISH", "SPINACH", "OKRA", "TOMATO", "BRINJAL", "PEAS",
        "BERSEEM", "TULSI", "ALOE VERA", "MINT", "NEEM"
    ],
    "goa": [
        "RICE", "COCONUT", "CASHEW", "ARECANUT", "MANGO", "BANANA", "PINEAPPLE",
        "JACKFRUIT", "BLACK PEPPER", "SWEET POTATO", "RAGI", "COWPEA", "GROUNDNUT",
        "TURMERIC"
    ],
    "gujarat": [
        "COTTON", "GROUNDNUT", "CASTOR", "SESAME", "WHEAT", "RICE", "BAJRA", "JOWAR",
        "MAIZE", "TOOR", "PIGEON PEA", "CHICKPEA", "BENGAL GRAM", "GREEN GRAM",
        "BLACK GRAM", "MUSTARD", "CUMIN", "FENNEL", "ONION", "GARLIC", "POTATO",
        "BANANA", "MANGO", "PAPAYA", "POMEGRANATE", "GUAVA", "SUGARCANE", "TOBACCO",
        "SUGAR BEET", "ALFALFA", "ALOE VERA", "LEMONGRASS"
    ],
    "haryana": [
        "WHEAT", "RICE", "COTTON", "MUSTARD", "SUGARCANE", "BARLEY", "MAIZE", "BAJRA",
        "JOWAR", "CHICKPEA", "BENGAL GRAM", "SUNFLOWER", "GUAVA", "ORANGE", "KINNOW",
        "POTATO", "CAULIFLOWER", "CABBAGE", "BERSEEM", "FODDER MAIZE", "FODDER SORGHUM",
        "SUGAR BEET", "TULSI", "ALOE VERA", "MUSHROOM"
    ],
    "himachal pradesh": [
        "APPLE", "MAIZE", "WHEAT", "BARLEY", "POTATO", "PEAS", "GINGER", "TOMATO",
        "CABBAGE", "CAULIFLOWER", "BEANS", "PLUM", "PEACH", "APRICOT", "PEAR",
        "ORANGE", "MANGO", "LITCHI", "GUAVA", "POMEGRANATE", "TEA", "FLAX",
        "HEMP", "BEETROOT", "MINT"
    ],
    "jammu & kashmir": [
        "APPLE", "RICE", "MAIZE", "WHEAT", "BARLEY", "RAJMASH", "FODDER MAIZE",
        "WALNUT", "ALMOND", "CHERRY", "APRICOT", "PEAR", "PLUM", "SAFFRON",
        "MUSTARD", "POTATO", "CABBAGE", "CAULIFLOWER"
    ],
    "jharkhand": [
        "RICE", "MAIZE", "WHEAT", "CHICKPEA", "BENGAL GRAM", "TOOR", "PIGEON PEA",
        "BLACK GRAM", "GREEN GRAM", "MUSTARD", "GROUNDNUT", "POTATO", "BRINJAL",
        "TOMATO", "CABBAGE", "CAULIFLOWER", "OKRA", "MANGO", "GUAVA", "JACKFRUIT",
        "PAPAYA", "NIGER"
    ],
    "karnataka": [
        "RICE", "RAGI", "JOWAR", "MAIZE", "BAJRA", "WHEAT", "TOOR", "PIGEON PEA",
        "CHICKPEA", "BENGAL GRAM", "GREEN GRAM", "BLACK GRAM", "COWPEA", "GROUNDNUT",
        "SUNFLOWER", "SOYBEAN", "COTTON", "SUGARCANE", "TOBACCO", "COCONUT",
        "ARECANUT", "COFFEE", "CASHEW", "CARDAMOM", "BLACK PEPPER", "GRAPES",
        "POMEGRANATE", "MANGO", "BANANA", "TOMATO", "ONION", "POTATO", "GINGER",
        "TURMERIC", "SUGAR BEET", "NAPIER GRASS", "YAM", "BEETROOT", "COCOA",
        "ALOE VERA", "ASHWAGANDHA"
    ],
    "kerala": [
        "RICE", "COCONUT", "RUBBER", "TEA", "COFFEE", "BLACK PEPPER", "CARDAMOM",
        "ARECANUT", "GINGER", "TURMERIC", "BANANA", "TAPIOCA", "NUTMEG", "CLOVE",
        "CINNAMON", "CASHEW", "PINEAPPLE", "MANGO", "JACKFRUIT", "PAPAYA",
        "YAM", "BEETROOT", "NAPIER GRASS", "COCOA", "LEMONGRASS"
    ],
    "lakshadweep": [
        "COCONUT", "BANANA", "PAPAYA", "GUAVA", "SAPOTA", "CHILLI", "TOMATO",
        "BRINJAL", "SWEET POTATO", "DRUMSTICK", "BREADFRUIT"
    ],
    "madhya pradesh": [
        "SOYBEAN", "WHEAT", "CHICKPEA", "BENGAL GRAM", "MAIZE", "RICE", "JOWAR",
        "BAJRA", "TOOR", "PIGEON PEA", "LENTIL", "GREEN GRAM", "BLACK GRAM", "PEAS",
        "MUSTARD", "LINSEED", "SESAME", "GROUNDNUT", "COTTON", "SUGARCANE", "ONION",
        "GARLIC", "POTATO", "TOMATO", "CORIANDER", "CHILLI", "GINGER", "ORANGE",
        "GUAVA", "MANGO", "BANANA", "FLAX", "BEETROOT", "BERSEEM", "ASHWAGANDHA",
        "ALOE VERA", "LEMONGRASS"
    ],
    "maharashtra": [
        "COTTON", "SOYBEAN", "SUGARCANE", "JOWAR", "BAJRA", "WHEAT", "RICE", "MAIZE",
        "TOOR", "PIGEON PEA", "CHICKPEA", "BENGAL GRAM", "GREEN GRAM", "BLACK GRAM",
        "GROUNDNUT", "SUNFLOWER", "SAFFLOWER", "SESAME", "ONION", "GRAPES",
        "POMEGRANATE", "BANANA", "MANGO", "ORANGE", "CASHEW", "TOMATO", "BRINJAL",
        "TURMERIC", "GINGER", "SUGAR BEET", "ALFALFA", "NAPIER GRASS", "BEETROOT"
    ],
    "manipur": [
        "RICE", "MAIZE", "POTATO", "MUSTARD", "PEAS", "CABBAGE", "CAULIFLOWER",
        "PINEAPPLE", "ORANGE", "BANANA", "PASSION FRUIT", "GINGER", "TURMERIC",
        "CHILLI", "KING CHILLI", "SOYBEAN", "BLACK GRAM", "RICE BEAN"
    ],
    "meghalaya": [
        "RICE", "MAIZE", "POTATO", "GINGER", "TURMERIC", "BLACK PEPPER", "ARECANUT",
        "BETELVINE", "ORANGE", "PINEAPPLE", "BANANA", "PLUM", "PEAR", "PEACH",
        "CASHEW", "TEA", "TOMATO", "CABBAGE", "CAULIFLOWER"
    ],
    "mizoram": [
        "RICE", "MAIZE", "MUSTARD", "SESAME", "POTATO", "GINGER", "TURMERIC",
        "CHILLI", "SUGARCANE", "BANANA", "ORANGE", "PINEAPPLE", "PAPAYA",
        "PASSION FRUIT", "HATKORA", "OIL PALM", "COFFEE", "TEA"
    ],
    "nagaland": [
        "RICE", "MAIZE", "MILLET", "PEAS", "MUSTARD", "POTATO", "GINGER", "TURMERIC",
        "CHILLI", "CARDAMOM", "COFFEE", "TEA", "PINEAPPLE", "ORANGE", "PAPAYA",
        "BANANA", "PASSION FRUIT", "VEGETABLES", "BAMBOO"
    ],
    "odisha": [
        "RICE", "GREEN GRAM", "BLACK GRAM", "TOOR", "PIGEON PEA", "CHICKPEA",
        "BENGAL GRAM", "GROUNDNUT", "SESAME", "MUSTARD", "CASTOR", "SUNFLOWER",
        "JUTE", "MESTA", "SUGARCANE", "COTTON", "POTATO", "BRINJAL", "TOMATO",
        "CABBAGE", "CAULIFLOWER", "OKRA", "MANGO", "BANANA", "COCONUT", "CASHEW",
        "TURMERIC", "GINGER", "SWEET POTATO", "YAM"
    ],
    "pondicherry": [
        "RICE", "SUGARCANE", "GROUNDNUT", "COTTON", "BLACK GRAM", "GREEN GRAM",
        "COCONUT", "BANANA", "MANGO", "TAPIOCA", "BRINJAL", "OKRA", "FLOWERS",
        "ARECANUT"
    ],
    "punjab": [
        "WHEAT", "RICE", "COTTON", "MAIZE", "SUGARCANE", "POTATO", "MUSTARD",
        "SUNFLOWER", "BARLEY", "GREEN GRAM", "BLACK GRAM", "PEAS", "KINNOW",
        "GUAVA", "MANGO", "PEAR", "PEACH", "GRAPES", "BER", "CARROT", "RADISH",
        "MUSHROOM", "BERSEEM", "FODDER MAIZE", "FODDER SORGHUM", "BENGAL GRAM",
        "SUGAR BEET", "MINT"
    ],
    "rajasthan": [
        "BAJRA", "JOWAR", "MAIZE", "WHEAT", "BARLEY", "CHICKPEA", "BENGAL GRAM",
        "GREEN GRAM", "BLACK GRAM", "MOTH BEAN", "GROUNDNUT", "MUSTARD", "SOYBEAN",
        "SESAME", "CASTOR", "COTTON", "CUMIN", "CORIANDER", "FENNEL", "FENUGREEK",
        "ISABGOL", "GUAR", "ORANGE", "KINNOW", "POMEGRANATE", "GUAVA", "DATE PALM",
        "BER", "ONION", "GARLIC", "BERSEEM", "ALFALFA", "FODDER SORGHUM", "ALOE VERA"
    ],
    "sikkim": [
        "MAIZE", "RICE", "WHEAT", "BUCKWHEAT", "MILLET", "BARLEY", "BLACK GRAM",
        "RAJMASH", "SOYBEAN", "MUSTARD", "CARDAMOM", "GINGER", "TURMERIC",
        "ORANGE", "POTATO", "TEA", "CHERRY PEPPER", "CABBAGE"
    ],
    "tamil nadu": [
        "RICE", "JOWAR", "BAJRA", "RAGI", "MAIZE", "TOOR", "PIGEON PEA", "GREEN GRAM",
        "BLACK GRAM", "CHICKPEA", "BENGAL GRAM", "HORSE GRAM", "GROUNDNUT", "SESAME",
        "SUNFLOWER", "COCONUT", "COTTON", "SUGARCANE", "BANANA", "MANGO", "TAPIOCA",
        "COFFEE", "TEA", "RUBBER", "CASHEW", "TURMERIC", "CHILLI", "ONION", "TOMATO",
        "BRINJAL", "OKRA", "JASMINE", "SUGAR BEET", "YAM", "BEETROOT", "NAPIER GRASS",
        "COCOA", "ASHWAGANDHA"
    ],
    "tripura": [
        "RICE", "WHEAT", "MAIZE", "BLACK GRAM", "GREEN GRAM", "POTATO", "SUGARCANE",
        "JUTE", "MESTA", "TEA", "RUBBER", "PINEAPPLE", "ORANGE", "JACKFRUIT",
        "BANANA", "LITCHI", "LEMON", "CASHEW", "COCONUT", "ARECANUT", "GINGER",
        "TURMERIC", "CHILLI"
    ],
    "uttar pradesh": [
        "WHEAT", "RICE", "SUGARCANE", "MAIZE", "BAJRA", "JOWAR", "BARLEY",
        "CHICKPEA", "BENGAL GRAM", "TOOR", "PIGEON PEA", "LENTIL", "PEAS",
        "BLACK GRAM", "GREEN GRAM", "MUSTARD", "GROUNDNUT", "LINSEED", "SESAME",
        "SUNFLOWER", "POTATO", "ONION", "GARLIC", "TOMATO", "BRINJAL", "CABBAGE",
        "CAULIFLOWER", "OKRA", "MANGO", "GUAVA", "AONLA", "PAPAYA", "BANANA",
        "MENTHA", "BERSEEM", "FODDER MAIZE", "FODDER SORGHUM", "HEMP", "MINT",
        "BEETROOT", "TULSI", "ALOE VERA", "NEEM"
    ],
    "uttarakhand": [
        "RICE", "WHEAT", "MAIZE", "RAGI", "BARLEY", "LENTIL", "PEAS", "SOYBEAN",
        "MUSTARD", "GROUNDNUT", "SUGARCANE", "POTATO", "ONION", "CABBAGE", "TOMATO",
        "APPLE", "PEAR", "PEACH", "PLUM", "APRICOT", "WALNUT", "LITCHI", "MANGO",
        "ORANGE", "MALTA", "LEMON", "TEA", "HEMP", "FLAX", "BEETROOT", "MINT",
        "TULSI", "BENGAL GRAM"
    ],
    "west bengal": [
        "RICE", "JUTE", "POTATO", "WHEAT", "MAIZE", "LENTIL", "CHICKPEA", "BENGAL GRAM",
        "PEAS", "TOOR", "MUSTARD", "SESAME", "GROUNDNUT", "SUGARCANE", "TOBACCO",
        "TEA", "BETELVINE", "MANGO", "BANANA", "PINEAPPLE", "GUAVA", "LITCHI",
        "PAPAYA", "JACKFRUIT", "BRINJAL", "CABBAGE", "CAULIFLOWER", "OKRA", "TOMATO",
        "CHILLI", "GINGER", "TURMERIC", "BEETROOT", "YAM", "FODDER MAIZE"
    ]
}

# ===========================================================
# 5. DATABASE SETUP
# ===========================================================
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()

        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                gender TEXT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                otp TEXT,
                is_verified INTEGER DEFAULT 0
            )
        ''')

        db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                state TEXT,
                city TEXT,
                crop TEXT,
                ph REAL,
                moisture REAL,
                acres REAL,
                cost REAL,
                date_applied TEXT,
                npk_values TEXT
            )
        ''')

        # ✅ NEW: Indexes for faster queries
        db.execute("CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_history_email ON history(user_email)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_history_date  ON history(date_applied)")
        db.commit()
        logger.info("Database initialised successfully.")

init_db()

# ===========================================================
# 6. LOAD AI MODELS
# ===========================================================
model_N       = None
model_P       = None
model_K       = None
model_columns = None

try:
    model_N       = joblib.load('model_N.pkl')
    model_P       = joblib.load('model_P.pkl')
    model_K       = joblib.load('model_K.pkl')
    model_columns = joblib.load('model_columns.pkl')
    logger.info("✅ NPK Models (N, P, K) & Column Map Loaded Successfully")
except FileNotFoundError:
    logger.warning("❌ model_N/P/K.pkl not found. Please run train.py first.")
except Exception as e:
    logger.error("❌ Unexpected Error loading models: %s", e)

# ===========================================================
# 7. STATE NAME NORMALIZER
#    cities.js sends Title Case like "Karnataka", "Orissa"
#    AGRO_ZONES keys are lowercase like "karnataka", "odisha"
#    This map fixes ALL mismatches perfectly
# ===========================================================
STATE_NAME_MAP = {
    # Title case → AGRO_ZONES key
    "andaman & nicobar":    "andaman & nicobar",
    "andhra pradesh":       "andhra pradesh",
    "arunachal pradesh":    "arunachal pradesh",
    "assam":                "assam",
    "bihar":                "bihar",
    "chandigarh":           "chandigarh",
    "chhattisgarh":         "chhattisgarh",
    "dadra & nagar haveli": "dadra & nagar haveli",
    "daman & diu":          "daman & diu",
    "delhi":                "delhi",
    "goa":                  "goa",
    "gujarat":              "gujarat",
    "haryana":              "haryana",
    "himachal pradesh":     "himachal pradesh",
    "jammu & kashmir":      "jammu & kashmir",
    "jharkhand":            "jharkhand",
    "karnataka":            "karnataka",
    "kerala":               "kerala",
    "lakshadweep":          "lakshadweep",
    "madhya pradesh":       "madhya pradesh",
    "maharashtra":          "maharashtra",
    "manipur":              "manipur",
    "meghalaya":            "meghalaya",
    "mizoram":              "mizoram",
    "nagaland":             "nagaland",
    "orissa":               "odisha",       # ← cities.js uses old name
    "odisha":               "odisha",
    "pondicherry":          "pondicherry",
    "punjab":               "punjab",
    "rajasthan":            "rajasthan",
    "sikkim":               "sikkim",
    "tamil nadu":           "tamil nadu",
    "telangana":            "telangana",
    "tripura":              "tripura",
    "uttar pradesh":        "uttar pradesh",
    "uttaranchal":          "uttarakhand",  # ← cities.js uses old name
    "uttarakhand":          "uttarakhand",
    "west bengal":          "west bengal",

    # Nominatim GPS sometimes returns these variations
    "jammu and kashmir":         "jammu & kashmir",
    "jammu & kashmir":           "jammu & kashmir",
    "andaman and nicobar islands": "andaman & nicobar",
    "andaman & nicobar islands": "andaman & nicobar",
    "dadra and nagar haveli and daman and diu": "dadra & nagar haveli",
    "dadra and nagar haveli":    "dadra & nagar haveli",
    "daman and diu":             "daman & diu",
    "the nilgiris":              "tamil nadu",
    "national capital territory of delhi": "delhi",
    "nct of delhi":              "delhi",
    "puducherry":                "pondicherry",
    "telangana state":           "telangana",
}

def normalize_state(state_raw):
    """Convert any state name format to the correct AGRO_ZONES key."""
    return STATE_NAME_MAP.get(state_raw.strip().lower(), state_raw.strip().lower())

# ===========================================================
# 8. LOGIN REQUIRED DECORATOR
# ===========================================================
def login_required(f):
    """Redirects to login page if user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ===========================================================
# 8. GLOBAL ERROR HANDLERS  ← NEW
# ===========================================================
@app.errorhandler(404)
def not_found(e):
    logger.warning("404 Not Found: %s", request.url)
    if request.is_json:
        return jsonify({"success": False, "message": "Page not found."}), 404
    return render_template("index.html", mode="auth"), 404

@app.errorhandler(500)
def server_error(e):
    logger.error("500 Server Error: %s", e, exc_info=True)
    if request.is_json:
        return jsonify({"success": False, "message": "Server error. Please try again."}), 500
    return render_template("index.html", mode="auth",
                           error="Something went wrong. Please try again."), 500

# ===========================================================
# 9. HELPER FUNCTIONS
# ===========================================================
def send_email(to_addr, subject, body):
    """Centralised email sender. Returns True on success."""
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From']    = SENDER_EMAIL
        msg['To']      = to_addr
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info("Email sent to %s", to_addr)
        return True
    except Exception as e:
        logger.error("Email failed to %s: %s", to_addr, e)
        return False

def get_soil_health_tips(n, p, k, ph, moisture):
    """Generates eco-friendly soil advice based on NPK, pH, and Moisture."""
    tips = {
        "organic":        "Apply 5-10 tons of well-decomposed Farm Yard Manure (FYM) per acre to improve soil structure.",
        "compost":        "Incorporate Vermicompost to boost microbial activity and water retention.",
        "micronutrients": "Consider Zinc Sulphate (10kg/acre) if leaves show yellowing, typical in this region."
    }

    # pH Logic
    if ph < 5.5:
        tips["organic"] = "⚠️ Soil is ACIDIC. Apply 500kg of Lime (Calcium Carbonate) to neutralize pH before fertilizing."
    elif ph > 7.8:
        tips["organic"] = "⚠️ Soil is ALKALINE. Apply Gypsum (200kg/acre) to lower pH and improve nutrient uptake."
    elif n > 40:
        tips["organic"] = "Apply Neem Cake (100kg/acre). It acts as a natural nitrification inhibitor and pest repellent."

    # Moisture Logic
    if moisture < 30:
        tips["compost"] = "💧 Soil is DRY. Use Mulching (dry leaves/straw) to prevent evaporation and save water."
    elif moisture > 80:
        tips["compost"] = "🚫 High Moisture! Ensure proper drainage to prevent root rot and Nitrogen leaching."
    elif p > 25:
        tips["compost"] = "Use Phosphate Rich Organic Manure (PROM) as a sustainable alternative to DAP."

    return tips

def check_forecast_safety(city, api_key):
    """Checks weather for next 48 hours (16 blocks of 3-hour intervals)."""
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return True, None, []

        data = response.json()
        forecast_display    = []
        total_rain_expected = 0

        for i in range(min(len(data['list']), 16)):
            item         = data['list'][i]
            display_time = item['dt_txt'].split(" ")[1][:5]
            rain_val     = item.get('rain', {}).get('3h', 0)
            total_rain_expected += rain_val
            forecast_display.append({
                "time":      display_time,
                "temp":      int(item['main']['temp']),
                "rain_prob": int(item.get('pop', 0) * 100),
                "icon":      f"https://openweathermap.org/img/wn/{item['weather'][0]['icon']}.png"
            })

        if total_rain_expected > 5.0:
            reason = f"Heavy Rain ({round(total_rain_expected, 1)}mm) expected in next 48hrs."
            return False, reason, forecast_display

        return True, None, forecast_display
    except Exception as e:
        logger.warning("Forecast check failed for %s: %s", city, e)
        return True, None, []

# ===========================================================
# 10. ROUTES
# ===========================================================
@app.route("/", methods=["GET"])
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html", mode="auth")

@app.route("/scan", methods=["GET"])
def scan():
    return render_template("index.html", mode="scan", is_logged_in=('user' in session))

@app.route("/dashboard")
@login_required                          # ✅ using decorator now
def dashboard():
    db     = get_db()
    cursor = db.execute(
        'SELECT * FROM history WHERE user_email = ? ORDER BY id DESC',
        (session['user'],)
    )
    return render_template("dashboard.html", user=session['user'], history=cursor.fetchall())

@app.route("/logout")
def logout():
    session.clear()                      # ✅ clears ALL session data, not just 'user'
    return redirect(url_for('index'))

# ===========================================================
# 11. AUTHENTICATION APIs
# ===========================================================
@app.route("/signup_api", methods=["POST"])
@rate_limit(max_calls=5, window_seconds=300)
@csrf_protect  
def signup_api():
    data     = request.get_json(silent=True) or {}
    name     = (data.get("name")     or "").strip()
    gender   = (data.get("gender")   or "")
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    # ✅ Input validation
    if not name or not email or not password:
        return jsonify({"success": False, "message": "Name, email and password are required."})
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."})

    db = get_db()
    existing_user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if existing_user:
        return jsonify({"success": False, "message": "Email already exists."})

    otp  = str(random.randint(100000, 999999))
    sent = send_email(
        email,
        "Your Eco-Fertilization OTP Code",
        f"Hello {name},\n\nWelcome to Eco-Fertilization! Your sign up OTP is: {otp}"
    )
    if not sent:
        return jsonify({"success": False, "message": "Failed to send OTP. Check your email address."})

    # ✅ Password hashed before storing in session
    session['temp_name']     = name
    session['temp_gender']   = gender
    session['temp_email']    = email
    session['temp_password'] = generate_password_hash(password)
    session['expected_otp']  = otp
    session['otp_expires_at'] = time.time() + 600  # ✅ expires in 10 minutes

    return jsonify({"success": True, "require_otp": True})


@app.route("/verify_otp_api", methods=["POST"])
@rate_limit(max_calls=5, window_seconds=300)
@csrf_protect  
def verify_otp_api():
    data     = request.get_json(silent=True) or {}
    user_otp = (data.get("otp") or "").strip()

    if 'expected_otp' not in session or user_otp != session['expected_otp']:
        return jsonify({"success": False, "message": "Invalid OTP. Please try again."})
    if time.time() > session.get('otp_expires_at', 0):
       session.pop('expected_otp', None)
       session.pop('otp_expires_at', None)
       return jsonify({"success": False, "message": "OTP has expired. Please sign up again."})
   
   
    name     = session.pop('temp_name',     None)
    gender   = session.pop('temp_gender',   None)
    email    = session.pop('temp_email',    None)
    password = session.pop('temp_password', None)  # ✅ already hashed
    session.pop('expected_otp', None)

    try:
        db = get_db()
        db.execute('''
            INSERT INTO users (name, gender, email, password, is_verified)
            VALUES (?, ?, ?, ?, 1)
        ''', (name, gender, email, password))
        db.commit()

        session['user']        = email
        session['user_name']   = name
        session['user_gender'] = gender
        logger.info("New user registered: %s", email)
        return jsonify({"success": True})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "User already exists or database error."})


@app.route('/login_api', methods=['POST'])
@rate_limit(max_calls=10, window_seconds=300)
@csrf_protect  
def login_api():
    data     = request.get_json(silent=True) or {}
    email    = (data.get('email')    or "").strip().lower()
    password = (data.get('password') or "").strip()

    # ✅ Input validation
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required."})

    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if not user:
        return jsonify({"success": False, "message": "Invalid email or password."})
    if user['is_verified'] != 1:
        return jsonify({"success": False, "message": "Please verify your email first."})

    # ✅ Support both hashed and old plain-text passwords
    stored = user['password']
    if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
        # New hashed password
        valid = check_password_hash(stored, password)
    else:
        # Old plain-text — check then auto-migrate to hash
        valid = (stored == password)
        if valid:
            db.execute("UPDATE users SET password = ? WHERE email = ?",
                       (generate_password_hash(password), email))
            db.commit()
            logger.info("Auto-migrated password to hash for: %s", email)

    if not valid:
        return jsonify({"success": False, "message": "Invalid email or password."})

    session['user']        = user['email']
    session['user_name']   = user['name']
    session['user_gender'] = user['gender']
    return jsonify({"success": True})


@app.route("/forgot_password_api", methods=["POST"])
@rate_limit(max_calls=5, window_seconds=300)
@csrf_protect  
def forgot_password_api():
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email is required."})

    db   = get_db()
    user = db.execute('SELECT name FROM users WHERE email = ?', (email,)).fetchone()
    if not user:
        return jsonify({"success": False, "message": "Identity not found in database."})

    otp = str(random.randint(100000, 999999))
    session['reset_email'] = email
    session['reset_otp']   = otp
    session['reset_otp_expires_at'] = time.time() + 600  # ✅ expires in 10 minutes

    sent = send_email(
        email,
        "Reset Your Eco-Command Passkey",
        f"SECURITY OVERRIDE: Your Password Reset OTP is: {otp}"
    )
    if not sent:
        return jsonify({"success": False, "message": "Communication failure with mail server."})
    return jsonify({"success": True})


@app.route("/verify_reset_otp", methods=["POST"])
def verify_reset_otp():
    data     = request.get_json(silent=True) or {}
    user_otp = (data.get("otp") or "").strip()
    if user_otp == session.get('reset_otp'):
    # ✅ Check expiry
        if time.time() > session.get('reset_otp_expires_at', 0):
            session.pop('reset_otp', None)
            session.pop('reset_otp_expires_at', None)
            return jsonify({"success": False, "message": "OTP has expired. Please request a new one."})
        session.permanent       = True
        session['otp_verified'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid OTP."})


@app.route("/reset_password_final", methods=["POST"])
def reset_password_final():
    if not session.get('otp_verified'):
        return jsonify({"success": False, "message": "Unauthorized. Please verify OTP again."})

    data         = request.get_json(silent=True) or {}
    new_password = (data.get("password") or "").strip()
    email        = session.get('reset_email')

    if not new_password or len(new_password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."})
    if not email:
        return jsonify({"success": False, "message": "Session expired. Restart reset process."})

    db = get_db()
    # ✅ Save hashed password
    db.execute('UPDATE users SET password = ? WHERE email = ?',
               (generate_password_hash(new_password), email))
    db.commit()

    session.pop('reset_otp',    None)
    session.pop('otp_verified', None)
    session.pop('reset_email',  None)
    logger.info("Password reset successful for: %s", email)
    return jsonify({"success": True})

# ===========================================================
# 12. PROCESSING ROUTE
# ===========================================================
@app.route("/processing", methods=["POST"])
@csrf_protect
def processing():
    # ✅ Input validation with safe defaults
    try:
        ph       = float(request.form.get("ph",       7.0))
        moisture = float(request.form.get("moisture", 50))
        acres    = float(request.form.get("acres",    1) or 1)
    except ValueError:
        return render_template("index.html", mode="auth",
                               error="Invalid numeric input for pH, moisture or acres.")

    # ✅ Clamp values to valid range
    ph       = max(0.0,  min(14.0,  ph))
    moisture = max(0.0,  min(100.0, moisture))
    acres    = max(0.1,  acres)

    logger.info("Received → pH: %s, Moisture: %s", ph, moisture)

    forecast_list = []

    crop  = (request.form.get("crop",  "") or "").strip().upper()
    state = normalize_state(request.form.get("state", "") or "")
    city  = (request.form.get("city",  "") or "").strip()

    if crop == "CORN":
        crop = "MAIZE"

    # GPS Location Engine
    # Always use GPS coordinates if provided (live location button was clicked)
    lat = request.form.get("latitude")
    lon = request.form.get("longitude")

    if lat and lon:
        try:
            geo_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
            headers = {'User-Agent': 'Sanjay_EcoFert_Universal_Precision_v2'}
            geo_res = requests.get(geo_url, headers=headers, timeout=7).json()
            address = geo_res.get('address', {})

            # Always override state from GPS when coordinates are provided
            gps_state = normalize_state(address.get('state', ''))
            if gps_state:
                state = gps_state

            # Override city from GPS
            gps_city = (address.get('city') or
                        address.get('town') or
                        address.get('village') or
                        address.get('hamlet') or
                        address.get('suburb') or
                        address.get('neighbourhood') or
                        "")
            if gps_city:
                city = gps_city.replace(',', '').strip()

            logger.info("GPS resolved → state: %s | city: %s", state, city)
        except Exception as e:
            logger.warning("GPS geocode failed: %s", e)

    # Final fallback if city still empty
    if not city or city.strip() == "":
        city = "Local Region"

    # Agro-Zone Validation
    allowed_crops = AGRO_ZONES.get(state, [])
    if crop not in allowed_crops:
        logger.info("Zone mismatch: %s not valid in %s", crop, state)
        return render_template(
            "alert.html",
            alert_type="zone_mismatch",
            crop=crop,
            city=city,
            state=state.title(),
            is_logged_in=('user' in session)
        )

    # 48-Hour Forecast Safety Check
    is_safe, unsafe_reason, forecast_list = check_forecast_safety(city, OPENWEATHER_API_KEY)
    if not is_safe:
        return render_template(
            "alert.html",
            alert_type="forecast_unsafe",
            city=city.replace(',', ''),
            reason=unsafe_reason,
            forecast=forecast_list,
            is_logged_in=('user' in session)
        )

    # Real-Time Weather
    temperature, humidity, rainfall = 27.0, 60.0, 0.0
    weather_desc = "Clear Skies"
    try:
        bttf = BestTimeToFertilize(city_name=city, state_name=state, api_key=OPENWEATHER_API_KEY)
        bttf.api_caller()
        if bttf.is_api_call_success():
            weather      = bttf.weather_data
            temperature  = float(weather["main"]["temp"])
            humidity     = float(weather["main"]["humidity"])
            rainfall     = float(weather.get("rain", {}).get("1h", 0))
            weather_desc = weather['weather'][0]['description'].title()
    except Exception as e:
        logger.warning("Weather fetch failed for %s: %s", city, e)

    # AI Prediction Engine
    NPK        = [{"Label_N": 45, "Label_P": 20, "Label_K": 16}]
    soil_group = "default"

    if model_N and model_P and model_K and model_columns:
        try:
            input_df = pd.DataFrame(
                np.zeros((1, len(model_columns))),
                columns=model_columns
            )
            input_df['temperature'] = temperature
            input_df['humidity']    = humidity
            input_df['ph']          = ph
            input_df['rainfall']    = rainfall

            crop_col = f"label_{crop.lower()}"
            if crop_col in input_df.columns:
                input_df[crop_col] = 1
            else:
                logger.warning("Crop '%s' not in AI training data. Using fallback.", crop)
                raise ValueError("Crop not in model")

            raw_N = float(model_N.predict(input_df)[0])
            raw_P = float(model_P.predict(input_df)[0])
            raw_K = float(model_K.predict(input_df)[0])

            try:
                from soil_map import get_soil_group
                soil_group = get_soil_group(city, state)
            except ImportError:
                STATE_TO_SOIL_GROUP = {
                    'punjab': 'alluvial', 'haryana': 'alluvial',
                    'uttar pradesh': 'alluvial', 'bihar': 'alluvial',
                    'west bengal': 'alluvial', 'delhi': 'alluvial',
                    'chandigarh': 'alluvial', 'assam': 'alluvial',
                    'lakshadweep': 'coastal_sandy',
                    'maharashtra': 'black', 'gujarat': 'black',
                    'madhya pradesh': 'black',
                    'dadra & nagar haveli': 'red_laterite',
                    'daman & diu': 'coastal_sandy',
                    'karnataka': 'red_laterite', 'tamil nadu': 'red_laterite',
                    'andhra pradesh': 'alluvial', 'telangana': 'black',
                    'kerala': 'red_laterite', 'odisha': 'red_laterite', 'orissa': 'red_laterite',
                    'chhattisgarh': 'red_laterite', 'jharkhand': 'red_laterite',
                    'goa': 'red_laterite', 'pondicherry': 'alluvial',
                    'andaman & nicobar': 'red_laterite',
                    'himachal pradesh': 'mountain', 'jammu & kashmir': 'mountain',
                    'uttarakhand': 'mountain', 'sikkim': 'mountain',
                    'arunachal pradesh': 'mountain', 'nagaland': 'mountain',
                    'manipur': 'mountain', 'mizoram': 'mountain',
                    'meghalaya': 'mountain', 'tripura': 'mountain',
                    'ladakh': 'mountain', 'rajasthan': 'arid',
                }
                soil_group = STATE_TO_SOIL_GROUP.get(state.lower(), 'default')

            SOIL_BIAS_VALUES = {
                "alluvial":      {"N":  5, "P":  1, "K": -2},
                "black":         {"N":  1, "P":  2, "K":  1},
                "red_laterite":  {"N":  2, "P": -1, "K":  3},
                "mountain":      {"N": -2, "P":  3, "K":  1},
                "arid":          {"N":  6, "P":  0, "K":  4},
                "coastal_sandy": {"N":  0, "P": -2, "K":  5},
                "default":       {"N":  0, "P":  0, "K":  0},
            }
            bias    = SOIL_BIAS_VALUES.get(soil_group, SOIL_BIAS_VALUES["default"])
            final_N = max(0, int(round(raw_N + bias["N"])))
            final_P = max(0, int(round(raw_P + bias["P"])))
            final_K = max(0, int(round(raw_K + bias["K"])))
            NPK     = [{"Label_N": final_N, "Label_P": final_P, "Label_K": final_K}]
            logger.info("✅ Prediction → N:%d P:%d K:%d | Soil:%s | Crop:%s",
                        final_N, final_P, final_K, soil_group, crop)

        except Exception as e:
            logger.warning("Prediction error: %s — using fallback NPK", e)

    health_tips = get_soil_health_tips(
        NPK[0]['Label_N'],
        NPK[0]['Label_P'],
        NPK[0]['Label_K'],
        ph,
        moisture
    )

    return render_template(
        "update.html",
        NPK=NPK,
        tips=health_tips,
        forecast=forecast_list,
        weather_desc=weather_desc,
        temperature=temperature,
        humidity=humidity,
        rainfall=rainfall,
        soil_group=soil_group,
        city=city.replace(',', ''),
        ph=ph,
        moisture=moisture,
        state=state.title(),
        crop=crop,
        acres=acres,
        is_logged_in=('user' in session)
    )

# ===========================================================
# 13. SAVE RECORD API
# ===========================================================
@app.route("/record_application", methods=["POST"])
@login_required                          # ✅ using decorator
def record_application():
    data  = request.get_json(silent=True) or {}
    today = datetime.date.today().strftime("%Y-%m-%d")

    if 'status' in data:
        npk_str = data['status']
    else:
        npk_str = f"N:{data.get('N')} P:{data.get('P')} K:{data.get('K')}"

    db    = get_db()
    check = db.execute(
        'SELECT * FROM history WHERE user_email=? AND city=? AND crop=? AND date_applied=?',
        (session['user'], data.get('city'), data.get('crop'), today)
    ).fetchone()

    if not check:
        db.execute(
            '''INSERT INTO history
               (user_email, state, city, crop, ph, moisture, acres, cost, date_applied, npk_values)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                session['user'],
                data.get('state'),
                data.get('city'),
                data.get('crop'),
                data.get('ph'),
                data.get('moisture'),
                data.get("acres",  0),
                data.get("cost",   0),
                today,
                npk_str
            )
        )
        db.commit()

    return jsonify({"success": True})

# ===========================================================
# 14. SECURE DELETE API
# ===========================================================
@app.route("/secure_delete", methods=["POST"])
@login_required                          # ✅ using decorator
def secure_delete():
    data     = request.get_json(silent=True) or {}
    target   = str(data.get("target", ""))
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()

    db          = get_db()
    user_record = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

    if not user_record:
        return jsonify({"success": False, "message": "Incorrect Credentials."})

    # ✅ Support both hashed and plain-text passwords for delete
    stored = user_record['password']
    if stored.startswith("pbkdf2:") or stored.startswith("scrypt:"):
        valid = check_password_hash(stored, password)
    else:
        valid = (stored == password)

    if not valid:
        return jsonify({"success": False, "message": "Incorrect Credentials."})

    if target == "ACCOUNT_PERMANENT":
        db.execute('DELETE FROM history WHERE user_email = ?', (email,))
        db.execute('DELETE FROM users   WHERE email       = ?', (email,))
        db.commit()
        session.clear()
        logger.info("Account deleted: %s", email)
        return jsonify({"success": True})
    elif target == "all":
        db.execute('DELETE FROM history WHERE user_email = ?', (session['user'],))
    else:
        try:
            db.execute('DELETE FROM history WHERE id = ? AND user_email = ?',
                       (int(target), session['user']))
        except ValueError:
            return jsonify({"success": False, "message": "Invalid record ID."})

    db.commit()
    return jsonify({"success": True})

# ===========================================================
# 15. RESET PAGE
# ===========================================================
@app.route("/reset_page")
def reset_page():
    return render_template("reset_password.html")

# ===========================================================
# 16. RUN
# ===========================================================
if __name__ == "__main__":
    port  = int(os.environ.get("FLASK_PORT",  5001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting Eco-Fertilization on port %d", port)
    app.run(debug=debug, host="0.0.0.0", port=port)