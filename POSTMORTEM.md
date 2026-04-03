# Dispatch AI Postmortem

## Summary

Dispatch AI started as a hackathon build focused on one idea:

route each prompt to the most appropriate Bedrock model instead of sending everything to a single expensive model.

The project did not place in the hackathon, but it still produced a working system with real technical value and a strong base for a personal project.

## What Worked

- Multi-model routing was implemented end to end
- AWS Bedrock integration worked with live model calls
- Qwen classification was gated instead of being overused
- The frontend exposed routing details, savings, latency, and model selection
- The app could run locally as one FastAPI service serving both backend and frontend
- Pricing comparisons made the system easier to explain

## What Was Strong

- The system was not just a wrapper around one model
- Routing decisions were explainable
- There was a real distinction between selected model and served model
- Debug output made failures and fallbacks visible
- The product felt more like infrastructure than a generic chatbot

## What Hurt The Project

- Bedrock integration details consumed a lot of time
- Model-specific request and timeout behavior created instability during demo prep
- Some product polish happened late, which reduced time for storytelling and simplification
- The project likely looked more complex than the judges could absorb quickly
- The pitch may not have made the user value obvious enough compared with the technical depth

## Main Lessons

### 1. Product clarity matters more than technical cleverness

The routing engine was interesting, but the clearest value proposition needed to be stated in one line:

"This system reduces AI cost by routing each request to the cheapest capable model."

### 2. Demo safety is a feature

Fallbacks, timeouts, and debug visibility were not optional. They were part of the product.

### 3. A smaller story may have landed better

A tighter version with fewer models and one crystal-clear use case might have been easier to judge quickly.

### 4. The work is still valuable

This repo now works better as a personal systems project than as a one-weekend competition entry.

## What This Project Becomes Now

Instead of treating this as a failed hackathon submission, the better framing is:

- a personal project in multi-model inference
- a portfolio piece showing backend, frontend, routing, pricing, and AWS integration
- a foundation for a future tool around AI cost control and explainable routing

## Recommended Next Steps

- make the repository public
- deploy a stable hosted version
- add a short product demo video or GIF
- simplify the homepage copy so the value is immediately obvious
- keep improving routing quality with real usage data

## Closing Note

Not winning the hackathon does not erase the engineering work. The project still demonstrates:

- FastAPI backend design
- AWS Bedrock integration
- multi-model orchestration
- cost-aware routing
- production-style fallback handling
- frontend analytics and explainability

That is real work, and it is worth keeping.
