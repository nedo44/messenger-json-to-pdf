#!/bin/bash
# Quick start script for Messenger JSON to PDF Converter

set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
    .venv/bin/playwright install chromium
fi

echo "🚀 Launching Streamlit Web App..."
.venv/bin/streamlit run app.py
