# Campus Commander Backend

An autonomous AI agent for campus facility management.

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials:
   ```
   cp .env.example .env
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the plan generation test:
   ```
   python test_plan.py
   ```

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your Google Gemini API key |
| `GEMINI_MODEL` | Gemini model name (e.g. `gemini-1.5-flash`) |

## Demo Scenario

> "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."
