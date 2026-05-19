# Gideon API Bridge Service

The `gideon_api.py` file serves as a high-performance HTTP/JSON bridge interface that exposes the **Luna AI** backend engine directly to external client applications—specifically the in-game HUD and terminal systems of **Project Speedster (ITSFV4)**.

This integration allows the game to communicate directly and securely with your local AI engine.

---

## ⚡ Key Functions & Endpoints

The API is built using **FastAPI** and runs a local server on port `8008` (`http://127.0.0.1:8008`). It exposes the following key routes:

1. **`GET /status`**
   * **Purpose:** Allows the game client to poll the status of the AI engine.
   * **Response:** Returns JSON confirming the system (`Gideon`) and the underlying orchestration engine (`Luna AI`) are operational.
   
2. **`POST /chat`**
   * **Purpose:** Main entrypoint for character interaction, mission guidance, and system override prompts.
   * **Implementation:** Receives a prompt and `model_id` (defaulting to the local engine), then handles downstream model routing by calling `ai_api.call_ai_api()`.

3. **`POST /transcribe`**
   * **Purpose:** Handles voice recognition and speech-to-text pipeline simulation.
   * **Implementation:** Receives raw/base64 audio data and passes it to the Speech-to-Text handler (designed for Whisper models).

---

## 🧠 Powered by Luna AI

This service is a developer-managed custom integration built directly upon the open-source **[Luna AI](https://github.com/DarkCommando0/Luna-AI)** engine. 

Luna AI provides the underlying infrastructure for local LLM routing, conversation memory management, dynamic system diagnostics, and hardware compatibility checks that power the character of **Gideon** in Project Speedster.
