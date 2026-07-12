# 🚆 TransitAI

> An AI-powered multimodal journey planner for Kerala that intelligently combines Kochi Metro, Indian Railways, KSRTC buses, and walking routes to provide optimized travel recommendations.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-green)
![SQLite](https://img.shields.io/badge/SQLite-Database-blue)
![Status](https://img.shields.io/badge/Build-Complete-success)

---

## 📌 Overview

TransitAI is a smart public transport planning application built to simplify travel across Kerala.

Instead of searching metro schedules, railway timings, and bus routes separately, TransitAI combines all supported transport providers into a single intelligent routing engine.

Users can either perform traditional searches or use natural language queries such as:

> "Reach Thrissur before 6 PM under ₹300"

or

> "Aluva ninn Kaloor pokanam"

The AI parser extracts travel constraints and recommends the best routes based on multiple optimization strategies.

---

## ✨ Features

### 🚇 Multi-Modal Journey Planning

- Kochi Metro
- Indian Railways
- KSRTC Bus Services
- Walking Connections

---

### 🤖 AI-Powered Search

Supports conversational travel queries including:

- Natural language
- Manglish
- Partial location names
- Typographical errors
- Time constraints
- Budget constraints
- Transport preferences
- Missing source/destination suggestions

Example:

```
Reach Thrissur before 6 PM under ₹300
```

```
Tomorrow morning Ernakulam to Palakkad train preferred

```

```
aluva ninn kaloor pokanam
```

---

### 🧠 Smart Recommendation Engine

Routes are ranked using weighted scoring based on:

- Duration
- Fare
- Transfers
- Waiting Time
- Walking Distance

Recommendations include:

- ⚡ Fastest
- 💰 Cheapest
- ⏳ Fewest Transfers


---

### 🗺 Interactive Route Visualization

- Interactive map
- Route visualization
- Multi-modal journey display
- Optimized recommendations

---

## 🏗 Project Structure

```
TransitAI/
│
├── app.py
├── ai_parser.py
├── recommendation_engine.py
├── route_engine.py
├── scheduler.py
│
├── database/
│   ├── schema.sql
│   ├── transit.db
│   └── ...
│
├── ingestion/
│   ├── data/
│   │   ├── metro_routes.json
│   │   ├── railway_routes.json
│   │   ├── bus_routes.json
│   │   └── locations.json
│   │
│   ├── metro_importer.py
│   ├── railway_importer.py
│   └── bus_importer.py
│
├── static/
├── templates/
│
├── test_parser.py
├── test_recommendation.py
└── test_transit.py
```

---

# 🛠 Tech Stack

### Backend

- Python
- Flask
- SQLite

### Frontend

- HTML5
- CSS3
- JavaScript

### AI / NLP

- Custom NLP Parser
- Fuzzy Matching
- Manglish Translation
- Weighted Recommendation Engine

---

# 🚀 Getting Started

## Clone the repository

```bash
git clone https://github.com/neegau-codes/TransitAI.git

cd TransitAI
```

---

## Create a Virtual Environment

Windows

```bash
python -m venv .venv
```

Activate it

```bash
.venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Build the Database

```bash
python rebuild_database.py
```

This imports:

- Kochi Metro
- Indian Railways
- KSRTC
- Walking Network

into the SQLite database.

---

## Run the Application

After activating the virtual environment:

```bash
.venv\Scripts\activate
```

Run the application:

```bash
python app.py
```

Open your browser and visit:

```
http://127.0.0.1:5000
```

---

# 🧪 Running Tests

Execute the complete test suite:

```bash
pytest -v
```

Current Results

```
90 Tests Passed
```

Includes:

- Routing Engine
- AI Parser
- Recommendation Engine
- Flask APIs
- Database Validation
- Backward Compatibility

---

# 📊 Supported Providers

| Provider | Status |
|-----------|--------|
| Kochi Metro | ✅ |
| Indian Railways | ✅ |
| KSRTC | ✅ |
| Walking Network | ✅ |

---

# 🧠 AI Capabilities

TransitAI understands:

✔ Manglish

✔ Time constraints

✔ Budget constraints

✔ Partial names

✔ Typographical errors

✔ Route preferences

✔ Missing information

✔ Conversational queries

---

# 📸 Screenshots
<img width="1475" height="906" alt="Home Page" src="https://github.com/user-attachments/assets/768de57c-5d1c-435b-abd9-7279b4299e46" />
<img width="642" height="802" alt="AI search" src="https://github.com/user-attachments/assets/ef3d2139-0b76-4fae-bdaa-4dfb811c34cf" />
<img width="896" height="895" alt="Routing and Maps" src="https://github.com/user-attachments/assets/81138540-06e6-4529-bf0f-226adee8cf5c" />



- Home Page
- AI Search
- Route Results & Interactive Map


---

# 👥 Team

Developed as part of the **Build a Project** initiative.

Team Members:

- Neeraja Rajesh - https://github.com/neegau-codes
- Shreya V Nathan - https://github.com/Shreyavnathan273
- Shweta Devan - https://github.com/devanshweta0-arch

---

# 🌟 Future Improvements

- Live GTFS integration
- Real-time vehicle tracking
- Delay prediction
- User accounts
- Saved trips
- Fare estimation using live data
- Route history
- Offline support

---

# 📄 License

This project is developed for educational purposes under the **Build a Project** program conducted by IEEE SB ASIET.
