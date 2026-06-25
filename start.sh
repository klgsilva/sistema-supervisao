#!/usr/bin/env bash
set -e
python seed.py
gunicorn run:app
