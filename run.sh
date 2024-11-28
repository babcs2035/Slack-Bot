#!/bin/bash

cd ~/bots/Slack-Bot/
source ./venv/bin/activate
pip3 install -r requirements.txt
python3 -u ./src/main.py
deactivate
