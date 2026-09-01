# FireWise AI

A small Flask web app that turns local fire-weather and fuel conditions into an explainable wildfire prevention-priority score. It is intended for education and planning, not emergency decision-making.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

## API

`POST /api/assess` accepts JSON with `temperature`, `humidity`, `wind_speed`, `vegetation_dryness`, `drought_index`, and `ignition_risk`. Values are validated and the response includes a 0–100 score, risk level, drivers, and recommended prevention actions.

`POST /api/chat` accepts `{ "message": "..." }` and returns an educational, safety-first prevention response for common questions.
