#!/usr/bin/env bash
# Phase 2 only. Installs Freqtrade in its own venv and starts the OKX futures dry-run.
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -U pip && pip install -q freqtrade
set -a; [ -f ../.env ] && . ../.env; set +a
freqtrade trade --config config.dryrun.json --userdir user_data --strategy VibeForecastStrategy
