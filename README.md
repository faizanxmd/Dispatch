# Dispatch AI

Dispatch AI is an explainable multi-model routing system built with FastAPI and AWS Bedrock. It routes prompts across multiple foundation models based on task type, complexity, ambiguity, and cost, while exposing the routing path, latency, token usage, and savings in the UI.

Built with teammates for **HACK 'A' WAR 2026** at **MSRIT**.

## Resume-Friendly Description

Dispatch AI is a cost-aware multi-model inference system that routes prompts across Bedrock models using deterministic rules, ambiguity scoring, and Qwen-assisted classification. It includes a FastAPI backend, a built-in frontend, model fallback handling, and live analytics for routing transparency.

## What It Does

- Routes prompts to different Bedrock models instead of using one model for everything
- Uses Qwen only when a prompt is ambiguous enough to justify classification
- Tracks latency, tokens, model choice, routing path, and pricing
- Exposes both router-selected and actually served models when fallback happens
- Serves the frontend and backend from one FastAPI app

## Model Stack

- Amazon Nova Micro
- Mistral
- Moonshot Kimi K2.5
- Amazon Nova Pro
- Z.AI GLM 5
- Qwen3 Next 80B A3B
- Claude Sonnet 4.6 benchmark for savings comparison

## Tech Stack

- FastAPI
- AWS Bedrock
- Python
- HTML, CSS, JavaScript

## Quick Start

```bash
git clone https://github.com/faizanxmd/hackathon.git
cd hackathon
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Set your AWS credentials before running:

```bash
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
export AWS_SESSION_TOKEN=YOUR_SESSION_TOKEN
```

Then start the app:

```bash
./run_dispatch.sh
```

Open:

```text
http://127.0.0.1:8000/app/
```

Health check:

```text
http://127.0.0.1:8000/health
```

If port `8000` is busy:

```bash
PORT=8010 ./run_dispatch.sh
```

## API

### `POST /ask`

```json
{
  "prompt": "write a fastapi endpoint",
  "refinement": "brief"
}
```

Supported refinement modes:

- `brief`
- `bullet`
- `detailed`

The response includes:

- `response`
- `model_used`
- `debug.task`
- `debug.complexity`
- `debug.uncertainty`
- `debug.used_qwen`
- `debug.decision_path`
- `debug.latency_ms`
- token metadata
- pricing and savings metadata

## Project Structure

```text
hackathon/
├── backend/
│   ├── main.py
│   ├── model.py
│   ├── router.py
│   ├── routing_pipeline.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── analytics.html
│   ├── history.html
│   ├── models.html
│   ├── profile.html
│   ├── settings.html
│   ├── script.js
│   └── style.css
├── render.yaml
└── run_dispatch.sh
```

## Notes

- If you only see `{"status":"Backend running"}`, open `/app/` instead of `/`
- Bedrock access must be enabled in your AWS account for the models used here
- `AWS_SESSION_TOKEN` is only needed for temporary credentials

## Postmortem

[POSTMORTEM.md](POSTMORTEM.md)
