# TouchGrass

TouchGrass is a local-first outdoor activity planner designed to make planning
the shortest part of going outside. It asks about your available time,
preferred activity, energy, surroundings, and interests, then uses a locally
running open-weight AI model to create a practical outdoor mission.

## Project status

The MVP includes a working preferences form, a FastAPI mission endpoint, local
Ollama integration, structured mission validation, and a glanceable phone-free
view. Safety safeguards are prompt-based and are not a guarantee that a
suggestion is safe for every person or situation.

## Tech stack

- FastAPI backend
- Static HTML, CSS, and JavaScript frontend
- Ollama local inference for mission generation (default model:
  `qwen2.5-coder:3b`)

## Run locally

Requirements: Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Open <http://127.0.0.1:8000>. The health endpoint is available at
<http://127.0.0.1:8000/api/health>.

## Run tests

```bash
pytest
```

## Ollama setup

Install Ollama and download the default model:

```bash
ollama pull qwen2.5-coder:3b
```

Keep Ollama running while using TouchGrass. If it is not already running,
start it in a separate terminal with `ollama serve`. The backend sends mission
preferences to the Ollama server configured below; with the default URL, that
server is on the same machine. There is no cloud AI fallback. Model download
requires internet, but generation runs locally after installation.

## Configuration

Copy `.env.example` to `.env` and edit the values as needed. The app loads that
file from the project root; process environment variables take precedence:

| Variable | Default | Description |
| --- | --- | --- |
| `TOUCHGRASS_APP_NAME` | `TouchGrass` | FastAPI application title |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama server base URL |
| `OLLAMA_MODEL` | `qwen2.5-coder:3b` | Model tag installed in Ollama |
| `OLLAMA_TIMEOUT_SECONDS` | `90` | Maximum wait for a model response |

For example:

```bash
export OLLAMA_MODEL=qwen2.5-coder:3b
uvicorn app.main:app --app-dir backend --reload
```

Generate a mission at `POST /api/missions`. Requests are validated and
responses include the mission title, summary, estimated duration, preparation,
time-boxed steps, optional challenge, safety notes, and completion message.
Step durations are validated to add up exactly to the selected mission length;
the backend retries once if the model returns an invalid mission. Ollama
unavailable, missing model, timeout, and invalid model output errors are
returned explicitly.

## Privacy and limitations

The app does not store preferences or make telemetry requests. Preferences go
from the browser to the local FastAPI backend, then to the Ollama server in
`OLLAMA_BASE_URL`. Use a trusted local Ollama instance; setting a remote URL
will send preferences there. The model may produce unsuitable suggestions, so
check local conditions, accessibility needs, and rules before heading out.
