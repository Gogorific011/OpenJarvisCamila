# J.A.R.V.I.S. local assistant

A localhost-only voice-first assistant UI backed by OpenJarvis, Groq, and Fish Audio. The gateway serves the supplied interface and keeps API keys in `.env` on the server.

## Requirements

Python 3.11–3.13 (the current OpenJarvis release requires Python 3.11+, though older documentation said 3.10+), `uv`, and an OpenJarvis installation. You need API keys from [Groq Console](https://console.groq.com) and [Fish Audio](https://fish.audio/app/api-keys).

## Install

Run the commands from the project directory.

### macOS / Linux

```sh
curl -fsSL https://open-jarvis.github.io/OpenJarvis/install.sh | bash -s -- --no-analytics
jarvis init --preset chat-simple --no-analytics
jarvis doctor
cp .env.example .env
uv venv
uv pip install -r requirements.txt
./run.sh
```

### Windows native PowerShell

The native installer is currently documented as an advanced path and may require Visual Studio C++ build tools. WSL2 is the smoother setup if the native build fails.


```powershell
irm https://open-jarvis.github.io/OpenJarvis/install.ps1 | iex
jarvis init --preset chat-simple --no-analytics
jarvis doctor
Copy-Item .env.example .env
uv venv
uv pip install -r requirements.txt
.\run.ps1
```

### Windows with WSL2

Open Ubuntu and follow the macOS/Linux steps there. Open the printed localhost URL in Windows Edge or Chrome.

Set `GROQ_API_KEY` and `FISH_API_KEY` in `.env`. Optionally set `FISH_VOICE_ID`, `FISH_MODEL`, `FISH_SPEED`, and `JARVIS_ACCESS_TOKEN`. When access token is enabled, set it in the UI using the browser console: `localStorage.setItem('jarvisAccessToken', 'your-token')`; reload afterward. The token is not embedded in this HTML.

The gateway listens on `http://127.0.0.1:8787` by default. Keep `JARVIS_HOST` on `127.0.0.1` for local use.

## OpenJarvis integration

The gateway runs OpenJarvis's Python `Jarvis` SDK with its `litellm` engine and `groq/<model>`. Groq uses the OpenAI-compatible API at `https://api.groq.com/openai/v1` underneath LiteLLM. OpenJarvis's documented direct `cloud` engine currently targets OpenAI, Anthropic, and Google; LiteLLM is its supported path for Groq. The model is selected by `JARVIS_MODEL`; the browser model is ignored. Default: `llama-3.3-70b-versatile`.

`jarvis serve` is not required for this setup. The gateway uses an isolated OpenJarvis configuration and data directory at `.openjarvis/`; it does not read or change your global OpenJarvis config. OpenJarvis memory can be enabled with `JARVIS_ENABLE_MEMORY=1` after its Rust extension is available in the gateway environment; the PyPI package alone does not ship that extension. The default stays off and chat works without it. Skills can be installed/synced with `jarvis skill --help`; use only skills you trust.

The time/date tool is deterministic and uses Asia/Manila. Morning digest returns a clear disabled response (501) until OAuth connectors are configured; it is not silently simulated.

## Fish Audio voice

Set `FISH_VOICE_ID` to a public Fish Audio voice model `reference_id` or a model you own. Clone a voice only with the speaker's consent. The current default model is `s2.1-pro`; choose another current model with `FISH_MODEL`. Tune `FISH_SPEED` from `0.5` to `2.0`. MP3 responses are cached locally by text and voice under `.cache/tts/`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Microphone unavailable | Grant microphone permission. Browser SpeechRecognition generally requires HTTPS or a trusted localhost origin. |
| First audio does not autoplay | Click or send a message once to grant the browser an audio gesture. |
| Groq or Fish returns 401 | Check the matching key in `.env`; never paste it into the HTML. |
| Groq or Fish returns 429 | Review provider rate limits and wait before retrying. |
| CORS errors | Open the page from the gateway URL, not as a `file://` page. |
| Port 8787 is occupied | Set `JARVIS_PORT` to another free port in `.env`. |
| Windows firewall prompt | Allow Python on private networks only; the gateway binds to loopback by default. |

## Security

Keys stay server-side in `.env`, excluded from git. The gateway binds to localhost by default. Do not expose it publicly without an access token and HTTPS. Rotate any key that may have leaked. OpenJarvis local telemetry and external anonymous analytics are disabled for gateway calls. Request logs omit message content by default; `JARVIS_DEBUG=1` opts into logging chat text for troubleshooting.

## Checks and known constraints

Automated API tests are in `tests/`. `GET /api/health` authenticates lightweight model-list checks and caches results for 60 seconds. Health checks reveal only booleans. This project cannot verify live chat or playable TTS without valid user API keys. OpenJarvis install/doctor commands are documented for setup, but the gateway has its own isolated SDK configuration. Fish API model naming evolves; use a model ID currently enabled for your account. The original UI's weather widget calls Open-Meteo directly, and browser device metrics remain browser-reported estimates.


