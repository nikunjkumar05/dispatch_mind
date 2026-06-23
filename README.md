# ClearLane - Gridlock 2.0 Hackathon

ClearLane shifts the paradigm from "counting cars" to measuring **capacity loss**. Built for the BTP (Bengaluru Traffic Police), this solution leverages historical lag analysis, anomaly detection, and Flipkart Scout crowdsourcing to detect hidden congestion and prevent cascading gridlock.

## 🚀 Quick Start (How to Run)

Choose one of the three options below to run the project locally.

### Option 1: Double-Click (easiest for Windows dev)
Double-click the **`start.bat`** file in the root project folder.
* This script automatically installs dependencies, boots the FastAPI backend, waits for its health check to pass, and opens the frontend UI at `http://localhost:3000`.

### Option 2: Docker Container (simulates production)
Build and run the unified container where FastAPI serves both frontend static assets and backend APIs:
```bash
# 1. Build the production Docker image
docker build -t dispatchmind .

# 2. Run the container
docker run -p 8000:8000 --env-file .env dispatchmind
```
*Access the live project at `http://localhost:8000`.*

### Option 3: Manual Development Mode (requires two terminal windows)

**Terminal 1: Backend (FastAPI + SQLite)**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the FastAPI server
uvicorn backend.api:app --reload --port 8000
```
*The backend API will run at `http://127.0.0.1:8000`*

**Terminal 2: Frontend (React + Vite)**
```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Vite development server
npm run dev
```
*The dev UI will run at `http://localhost:3000` (Vite automatically proxies `/api` calls to the backend).*

---

## 🧹 Pre-Pitch Setup

Before beginning your live demo for the judges, ensure you run the reset script to clear any test reports and reset offline cameras to a clean state:

```bash
python scripts/reset_demo.py
```

---

## 🔐 Environment Variables

The system operates securely out-of-the-box using **Local Dispatch Mode** (saving API keys and preventing spam). To connect real SMS/WhatsApp webhooks for production, duplicate the `.env.example` file to `.env` and configure your credentials.
