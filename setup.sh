#!/bin/bash
echo "=== Установка системных зависимостей ==="
apt-get update
apt-get install -y libgomp1 build-essential python3-dev libopenblas-dev liblapack-dev

echo "=== Обновление pip ==="
pip install --upgrade pip setuptools wheel

echo "=== Установка Python пакетов ==="
pip install --no-cache-dir streamlit pandas numpy plotly scikit-learn openpyxl

echo "=== Проверка установки ==="
python -c "import plotly; print(f'Plotly version: {plotly.__version__}')"
python -c "import sklearn; print(f'Scikit-learn version: {sklearn.__version__}')"

echo "=== Настройка Streamlit ==="
mkdir -p ~/.streamlit
echo "[server]
headless = true
port = \$PORT
enableCORS = false
" > ~/.streamlit/config.toml