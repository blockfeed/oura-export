
# Oura Export Utility

Simple exporter for sleep and heart‑rate data from the Oura Cloud API.

This project uses the third‑party Python client maintained at:

https://github.com/hedgertronic/oura-ring

Note: This is not an official Oura SDK. It is a community-maintained wrapper around the Oura Cloud v2 REST API.

---

## What This Does

- Exports sleep data
- Exports sleep period details (HR, HRV, stages, efficiency, etc.)
- Exports heart rate data
- Produces clean JSON + JSONL summary files for analysis
- Defaults to exporting the last **7 days**
- Adjustable via `--days`

---

## Requirements

- Python 3.9+
- An Oura Personal Access Token
- Internet access

### Personal Access Token

Generate your token here:

https://cloud.ouraring.com/personal-access-tokens

Set it as an environment variable:

```bash
export OURA_TOKEN="your_token_here"
```

The token is read from the environment and is never written to disk.

---

## Installation (Recommended)

Create a virtual environment inside the project directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install oura-ring
```

---

## Usage

Export last 7 days (default):

```bash
python export_oura.py
```

Export last 14 days:

```bash
python export_oura.py --days 14
```

Export 30 days into a different directory:

```bash
python export_oura.py --days 30 --out-dir data_30d
```

Include raw 5‑minute heart rate samples:

```bash
python export_oura.py --days 14 --include-raw-heartrate
```

---

## Output Structure

```
oura_export/
  meta.json
  daily_sleep.json
  sleep_periods.json
  sleep_daily_summary.jsonl
  sleep_periods_summary.jsonl
  heartrate_daily_summary.jsonl
  heartrate_5m.jsonl.gz (optional)
  personal_info.json
  ring_configuration.json
  daily_readiness.json
  readiness_daily_summary.jsonl
  daily_activity.json
  daily_stress.json
  daily_spo2.json
  sleep_time.json
  sessions.json
  enhanced_tag.json
  rest_mode_period.json
```

The `*_summary.jsonl` files contain flattened daily records intended for analysis.

---

## License

This project is licensed under the GNU General Public License v3.0.

See the `LICENSE` file for details.
