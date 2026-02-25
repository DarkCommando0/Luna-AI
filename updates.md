# Luna AI Updates

## Version 1.0

### Key Updates & Features
- **Local Model Manager**:
  - Created a built-in system to download and manage GGUF models directly from HuggingFace.
  - Integrated `llama-cpp-python` for high-performance local inference with GPU support.
  - Supported models include Mistral 7B, Llama 3.1 8B, Qwen 2.5 7B, and DeepSeek Coder.
- **Resilience & Reliability**:
  - Implemented smart auto-fallback logic for cloud models.
  - Added background health monitoring for OpenRouter endpoints.
  - Added advanced recovery settings (Retry attempts, Status check intervals).
- **Modern Chat Interface**:
  - Added typewriter-style typing animation for AI responses.
  - Improved chat bubble layouts for better readability.
  - Enhanced web search results with clickable links and clean formatting.
- **Privacy & Settings**:
  - Moved API keys to session-only storage or `.env` files.
  - Added "Delete Local Data" functionality to clear chat history and profiles.
  - Improved System Information and Performance monitoring tabs.

## Version 1.0.1

### UI Optimization & Logic Fixes
- Modified `app.py`'s `update_selected_model_download_info` to correctly toggle the visibility (`setVisible()`) of the "Download Selected Local Model" and "Open Model Folder" buttons depending on the type of the active model.
-  **Cloud Models**: Both buttons are now completely hidden.
-  **Local Conversation Engine**: The Download button is hidden, while the Open Folder button remains visible.
-  **Local Conversation Engine Folder Logic**: Modified `open_selected_model_folder` so that when the Local Engine is selected, clicking the Open Folder button routes directly to the `user_data` directory instead of the normal local models directory.
-  **Other Local Models**: Both buttons remain visible and function normally.
-  **UI Model Sync Fix**: Fixed a bug where `app.py` would forcefully reset the backend model to the Local Engine on system startup, causing the top-right model status badge to desync from the "Active AI Model" card displaying the actually selected model.

## Current Goal
- [ ] Download queue for multiple models
- [ ] Model update checker
- [ ] Custom model import

