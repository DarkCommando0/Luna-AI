# Built-in Local Model Downloading

Luna now has **built-in model downloading** for local GGUF models. No external tools are required.

## Quick Start

### 1. Install Dependencies

First time setup only:
```powershell
pip install huggingface_hub llama-cpp-python
```

Or install all requirements:
```powershell
pip install -r requirements.txt
```

### 2. Download a Model

Use Python to download models directly:

```python
from local_model_manager import get_manager

# Get the model manager
manager = get_manager()

# Download Mistral 7B (~4.4GB)
manager.download_model("local/mistral-7b-instruct")

# Or download other models:
# manager.download_model("local/llama-3.1-8b-instruct")  # ~4.9GB
# manager.download_model("local/qwen-2.5-7b-instruct")   # ~4.4GB
# manager.download_model("local/deepseek-coder-6.7b")    # ~4.0GB
```

### 3. Use the Model in Luna

1. Open Luna
2. Go to **Models** tab
3. Select your downloaded model (marked with [LOCAL])
4. Click **Apply Selected Model**
5. Start chatting!

## Available Models

| Model | Size | Best For | RAM Needed |
|-------|------|----------|------------|
| Mistral 7B | 4.4GB | General conversation | 8GB |
| Llama 3.1 8B | 4.9GB | Reasoning & logic | 8GB |
| Qwen 2.5 7B | 4.4GB | Multilingual | 8GB |
| DeepSeek Coder 6.7B | 4.0GB | Programming | 8GB |

## How It Works

1. **Downloads from HuggingFace** - Models stored in `./local_models/`
2. **GGUF format** - Optimized, quantized (Q4_K_M) for speed
3. **GPU accelerated** - Automatically uses your NVIDIA GPU
4. **No external tools** - Everything built into Luna

## Check Download Status

```python
from local_model_manager import get_manager

manager = get_manager()

# Check if model is downloaded
if manager.is_model_downloaded("local/mistral-7b-instruct"):
    print("Model ready!")
else:
    print("Model not downloaded yet")

# Get all models status
models = manager.get_available_models()
for model_id, info in models.items():
    status = "✅ Downloaded" if info['downloaded'] else "❌ Not downloaded"
    print(f"{model_id}: {status} ({info['size_mb']}MB)")
```

## Manage Models

```python
from local_model_manager import get_manager

manager = get_manager()

# Delete a model to free up space
manager.delete_model("local/mistral-7b-instruct")

# Unload from memory (keeps file on disk)
manager.unload_model("local/mistral-7b-instruct")
```

## Test Model Directly

```python
from local_model_manager import get_manager

manager = get_manager()

# Generate a response
response = manager.generate_response(
    model_id="local/mistral-7b-instruct",
    prompt="Hello! How are you?",
    max_tokens=100,
    temperature=0.7
)

print(response)
```

## System Requirements

- **Python**: 3.8 or newer
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 5GB free space per model
- **GPU**: NVIDIA GPU recommended (RTX 2060+)
  - Any reasonably recent NVIDIA GPU will work well
  - CPU-only mode is also available (slower but works on more machines)

## Troubleshooting

### Installation Issues

**llama-cpp-python fails to install:**
```powershell
# Try installing with pre-built wheels
pip install llama-cpp-python --prefer-binary
```

**GPU not detected:**
```powershell
# Reinstall with CUDA support
pip uninstall llama-cpp-python
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Download Issues

**Download fails or is slow:**
- Check your internet connection
- Download happens only once per model
- Files cached in `./local_models/` directory

**Not enough disk space:**
- Each model is 4-5GB
- Delete unused models: `open output folder and delete the .gguf file(s)`

### Performance Issues

**Model runs slowly:**
- Ensure GPU is being used (check NVIDIA GPU Activity)
- Close other GPU-heavy applications
- Try a smaller model (DeepSeek Coder 6.7B is smallest)

**Out of memory errors:**
- Close other applications
- Reduce context window: `manager.load_model(model_id, n_ctx=1024)`
- Try CPU mode if GPU memory insufficient

## Technical Details

### Models Source
All models downloaded from HuggingFace in GGUF format (quantized).

### Model Locations
- **Storage**: `./local_models/` directory
- **Config**: `./local_models/models_config.json`

### Quantization
Models use Q4_K_M quantization:
- 4-bit quantization
- ~4-5GB per 7B model
- Minimal quality loss
- 4x smaller than full precision

## Future Features (Coming Soon)

- [ ] Download queue for multiple models
- [ ] Model update checker
- [ ] Custom model import

## Need Help?

If you prefer using external tools instead of the built-in downloader, you can still manage models with third-party tools such as:
- Ollama
- LM Studio
- GPT4All
- llama.cpp
- Text Generation WebUI
