# Luna AI Assistant

<p align="center">
  <img src="assets/luna_banner.png" alt="Luna AI logo" width="480">
</p>

Luna AI Assistant is a desktop chatbot and assistant for Windows with:

- **Local conversation engine** that runs entirely on your machine.
- **OpenRouter cloud models** (optional, with your own API key).
- **Built-in local model downloading** for GGUF models (Mistral, Llama, Qwen, DeepSeek Coder, etc.).
- **Web search**, **weather**, and **system commands** (all user-toggleable in Settings).
- A modern Qt-based UI with model management, system info, and performance metrics.

This README is safe for distribution: it assumes a clean clone of the repo and **does not include any API keys, downloaded models, or personal data**.

---

## 1. Requirements

- **OS**: Windows 10/11
- **Python**: 3.10+ recommended
- **RAM**: At least 8 GB (16 GB recommended for local models)
- **GPU**: Optional, but a recent NVIDIA GPU (RTX 2060+) is recommended for local GGUF models

Python packages are managed via `requirements.txt`.

Luna is designed to run **from source in dev mode**; there is currently **no bundled installer**. Users clone the repo, install dependencies, and run `app.py` directly.

---

## 2. Getting Started (Dev Mode)

Follow these steps on Windows:

1. **Download the code**
   - On GitHub, click **Code → Download ZIP** and unzip it somewhere (for example, `C:\Luna AI`).

2. **Open PowerShell in the Luna folder**
   - Open **File Explorer** and browse to the folder where you unzipped Luna (for example, `C:\Luna AI`).
   - Right-click an empty area inside the folder and choose **Open in Terminal** or **Open PowerShell window here** (wording depends on your Windows version).
   - A PowerShell (or terminal) window will open with its current directory set to the Luna folder.

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run Luna**
   ```powershell
   python app.py
   ```

Luna will create local files in the project folder (settings, `user_data/`, `local_models/`). These are **ignored by .gitignore** and should not be committed.

---

## 3. API Keys and Configuration

Luna uses a simple `.env` file in the project root to load API keys at runtime. **This file is not shipped** and is created/managed on your machine only.

The easiest way to set this up is:

- Run Luna (`python app.py`).
- Open **Settings → API Keys** inside the app.
- Enter your OpenRouter and/or OpenWeatherMap keys.
- Click **Save**.

Luna will create or update the `.env` file for you automatically.

If you prefer to create it manually, make a new `.env` file next to `app.py` with your own keys:

```ini
# Luna AI API Keys Configuration

# OpenRouter API Configuration (optional - for cloud models)
# Get your API key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_openrouter_key_here

# OpenWeatherMap API Configuration (optional - for weather)
# Get your API key from: https://home.openweathermap.org/api_keys
OPENWEATHERMAP_API_KEY=your_openweathermap_key_here
```
---

## 4. Local Models (Built-in Download System)

Luna includes a built-in manager for local GGUF models (see `local_model_manager.py` and `BUILTIN_MODELS_README.md`).

- Local models are stored under:
  - `./local_models/`
- Luna’s UI shows:
  - `💻` icons for local models.
  - `☁️` icons for OpenRouter models.

Basic workflow:

1. Start Luna (`python app.py`).
2. Go to the **Models** tab.
3. Use the built-in controls to **download** supported local models.
4. Select a model and click **Apply Selected Model**.
5. Chat normally; the active model is shown in the top-right badge.

For more details, including Python-only usage, see:

- `BUILTIN_MODELS_README.md`

---

## 5. Privacy and Local Data

Luna is designed so that **your data stays on your machine**:

- All local model files live under `./local_models/`.
- Local conversation memory and profile data for the built-in engine live under:
  - `./user_data/local_engine_profile.json`
- Settings are stored in:
  - `./luna_settings.json`

Controls:

- In **Settings → Advanced** you can toggle:
  - `Save chat history` (controls whether local engine memory is persisted to disk).
  - `Enable Web Search`.
  - `Enable System Commands`.
- In **Settings** there is a **Delete Local Data** button that:
  - Clears local conversation memory and profile.
  - Deletes the `user_data/local_engine_profile.json` file.

If a user deletes the entire **Luna AI** folder, all local data, models, and settings are removed with it.

---

## 6. Support and Further Documentation

- Project plan & change log: `plan.md`
- Built-in local model system: `BUILTIN_MODELS_README.md`

For questions about packaging or extending Luna AI (new models, providers, or features), consult the source files:

- `app.py` — main GUI and Qt widgets.
- `ai_api.py` — AI routing, OpenRouter integration, local engine, search, weather, and system commands.
- `local_model_manager.py` — local GGUF model management.
- `luna.py` — command-line interface.
