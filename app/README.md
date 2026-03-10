# 🌱 Eco-Fertilization System

AI-powered fertilizer recommendation for Indian farmers.
Predicts optimal NPK values using real-time weather, GPS, soil type and ML.

---

## 🚀 How to Run

### 1. Install dependencies
pip install -r requirements.txt

### 2. Setup environment variables
Copy .env.example to .env and fill in your values

### 3. Train ML models (first time only)
python train.py

### 4. Start the app
python app.py

### 5. Open browser
http://localhost:5001

---

## ⚙️ Environment Variables (.env)

| Variable              | Description                        |
|-----------------------|------------------------------------|
| FLASK_SECRET_KEY      | Any random secret string           |
| OPENWEATHER_API_KEY   | Get free key at openweathermap.org |
| SENDER_EMAIL          | Your Gmail address                 |
| SENDER_PASSWORD       | Gmail App Password (16 chars)      |
| DATABASE              | SQLite file name (users.db)        |
| FLASK_PORT            | Port number (default 5001)         |

---

## 🤖 ML Model Performance

| Model        | R² Score | MAE         |
|--------------|----------|-------------|
| Nitrogen (N) | 0.8744   | 10.57 kg/ha |
| Phosphorus(P)| 0.9318   | 7.12 kg/ha  |
| Potassium (K)| 0.9952   | 2.85 kg/ha  |
| Average      | 0.9338   | 6.84 kg/ha  |

---

## 📁 Project Structure

- app.py               → Main Flask app
- train.py             → ML model trainer
- BestTimeToFertilize  → Weather module
- soil_map.py          → 766 district soil database
- templates/           → HTML pages
- static/              → CSS and JS files
- requirements.txt     → Dependencies
- .env                 → Secret keys (never commit!)

---

## 🔒 Security

- Passwords hashed with Werkzeug PBKDF2-SHA256
- API keys loaded from .env file
- Session cookies use HttpOnly and SameSite flags
```

### Step 3: Create `.env.example`:
```
FLASK_SECRET_KEY=replace_with_random_string
OPENWEATHER_API_KEY=your_openweathermap_key
SENDER_EMAIL=your@gmail.com
SENDER_PASSWORD=your_16_char_app_password
DATABASE=users.db
FLASK_PORT=5001
FLASK_DEBUG=true
```

### Step 4: Create `.gitignore`:
```
.env
__pycache__/
*.pyc
*.db
venv/
.DS_Store
eco_app.log