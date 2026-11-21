# Research notes

Research checked 2026-11-21 against official project documentation and source.

## OpenJarvis

- OpenJarvis provides CLI setup (`jarvis init`, `jarvis doctor`, `jarvis ask`, `jarvis serve`), built-in agent presets such as `chat-simple`, agents, tools, and persistent memory. `jarvis serve` exposes an OpenAI-compatible API, but the documented server configuration sets an engine/model and does not document a custom Groq provider/base URL.
- The `cloud` engine is for OpenAI, Anthropic, and Google SDKs. OpenJarvis separately ships a `litellm` engine. Its API reference says LiteLLM supports Groq and reads `GROQ_API_KEY`; the provider/model convention is `groq/<model>` and it accepts an `api_base` override.
- Integration selected: use OpenJarvis Python SDK `Jarvis` with its `LiteLLMEngine` and built-in `simple` agent, in-process from `brain.py`. Construct `JarvisConfig` directly and set `OPENJARVIS_HOME` to this project’s ignored `.openjarvis/` directory so startup does not write into the user profile or silently alter global settings. This keeps OpenJarvis's agent layer in the request path and uses its supported Groq integration. `jarvis serve` is not selected because its documented direct cloud engine does not include Groq; an additional proxy would add a separate service.
- OpenJarvis documents local-first capabilities including agents, tools, and memory; persistent memory requires index/config setup and will be described as optional. The gateway's trusted time tool will answer time/date requests deterministically in Asia/Manila.
- Install documentation currently recommends the official install script on macOS/Linux/WSL2 and the PowerShell installer for native Windows. `jarvis init` creates `~/.openjarvis/config.toml`; `jarvis doctor` checks installation/runtime status.

## Groq

- OpenAI-compatible base URL is `https://api.groq.com/openai/v1`; credentials are passed via `GROQ_API_KEY`.
- Current Groq model documentation lists `llama-3.3-70b-versatile` as a production model and the models endpoint `GET /openai/v1/models` for live validation. Model availability/rate limits are account- and time-dependent; the gateway pins the configured model and checks connectivity with the models endpoint.

## Fish Audio

- Official Fish API docs and its official Python SDK document `POST https://api.fish.audio/v1/tts`, bearer authentication, `model` request header, JSON fields `text`, optional `reference_id`, and `format`. MP3 is a supported response format.
- The prompt's `s2-pro` model remains listed in current Fish documentation. This project defaults to the current production model `s2.1-pro`; `FISH_MODEL` can select another supported model, including `s2.1-pro-free`.
- The implementation will use the documented HTTP API via async `httpx`, and send the configured speed as `prosody.speed` (the current API shape). Fish voice-model listing is public, so the authenticated health check uses `GET /wallet/self/api-credit` instead. Voice reference IDs can be public or user-owned; cloning should only use a voice with the speaker's consent.

## Sources

- OpenJarvis README and setup: https://github.com/open-jarvis/OpenJarvis and https://open-jarvis.github.io/OpenJarvis/getting-started/install/
- OpenJarvis quickstart and configuration: https://open-jarvis.github.io/OpenJarvis/getting-started/quickstart/ and https://open-jarvis.github.io/OpenJarvis/getting-started/configuration/
- OpenJarvis engine docs and LiteLLM API: https://open-jarvis.github.io/OpenJarvis/architecture/engine/ and https://open-jarvis.github.io/OpenJarvis/api-reference/openjarvis/engine/litellm/
- Groq compatibility and models: https://console.groq.com/docs/openai and https://console.groq.com/docs/models
- Fish TTS API and SDK: https://github.com/fishaudio/docs/blob/main/api-reference/endpoint/openapi-v1/text-to-speech.mdx and https://github.com/fishaudio/fish-audio-python


