#!/bin/bash
set -a
source /Users/rayhannoerkhan/.hermes/profiles/deepseek/.env
set +a
cd /Users/rayhannoerkhan/stock-advisory-cron
source venv/bin/activate
python3 -m src.main_pipeline 2>&1
