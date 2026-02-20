
# Oura Ring Data Exporter

A small, focused utility for exporting personal data from the **Oura Ring**
via the **Oura Cloud API** so you can analyze it yourself.

This project uses the community-maintained Python client:

https://github.com/hedgertronic/oura-ring

Note: This is not an official Oura SDK. It is a third‑party wrapper around the
Oura Cloud v2 REST API.

---

## Purpose

This tool exists for one reason:

To export your own Oura Ring data from the Oura Cloud API into structured
JSON files so you can:

- Perform your own analysis
- Build custom dashboards
- Run statistical modeling
- Correlate sleep, HR, HRV, stress, or readiness with other datasets
- Maintain your own historical archive

It does not perform analytics. It exports raw and lightly summarized data so
you remain in control of interpretation.

---

## What Gets Exported

From the Oura Cloud API (v2):

- Daily sleep summaries
- Sleep period details (HR, HRV, stages, latency, efficiency)
- Heart rate (5‑minute resolution)
- Daily heart-rate aggregates
- Readiness (optional)
- Activity (optional)
- Stress (optional)
- SpO₂ (optional)
- Sessions / tags (optional)

Default export window: **last 7 days**  
Adjust with `--days`.

---

## Requirements

- Python 3.9+
- Oura Ring account
- Oura Cloud Personal Access Token
- Internet access

---

## Personal Access Token

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

The `*_summary.jsonl` files provide flattened daily records designed to make
downstream analysis simple.

---

## License

This project is licensed under the GNU General Public License v3.0.

See the `LICENSE` file for full details.
