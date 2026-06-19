#!/bin/bash
echo "========================================"
echo "ParkIntel v2 — Starting Dashboard"
echo "========================================"
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""
echo "Starting Streamlit dashboard..."
echo "Dashboard will open at: http://localhost:8501"
echo ""
streamlit run dashboard.py
