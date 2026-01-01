"""
Local Model Manager
Handles downloading and running AI models directly without external tools.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Callable

# We treat downloads and inference as separate capabilities:
#  - huggingface_hub is needed for downloading GGUF files
#  - llama-cpp-python is needed only for running local inference

try:
    from huggingface_hub import hf_hub_download, snapshot_download
    HF_DOWNLOAD_AVAILABLE = True
except ImportError:
    HF_DOWNLOAD_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    # llama-cpp-python not available; keep type hints working with a stub
    LLAMA_AVAILABLE = False

    class Llama:  # type: ignore
        """Placeholder Llama class used when llama-cpp-python is unavailable.

        All runtime methods that rely on real local model support are
        gated on LLAMA_AVAILABLE, so this stub is never used for inference.
        It only prevents NameError from annotations like Optional[Llama].
        """

        pass


class LocalModelManager:
    """Manages local AI model downloads and inference"""
    
    def __init__(self, models_dir: Optional[str] = None):
        """Initialize the local model manager.

        Args:
            models_dir: Directory to store downloaded models.
                       If None, choose a sensible default that works both
                       when running from source and from a frozen/installed EXE.
        """
        if models_dir is None:
            # When running from a PyInstaller-frozen EXE in Program Files,
            # the application directory is typically not writable for
            # standard users. In that case, prefer a per-user data folder
            # under LOCALAPPDATA, falling back to a local ./local_models
            # directory only when write access is available.
            try:
                base_dir = Path(__file__).parent
            except Exception:
                base_dir = Path.cwd()

            default_dir = base_dir / "local_models"

            # Detect frozen (PyInstaller) environment
            is_frozen = getattr(sys, "frozen", False)
            if is_frozen:
                # Prefer a user-writable location, e.g. %LOCALAPPDATA%\LunaAI\local_models
                local_appdata = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
                if local_appdata:
                    user_base = Path(local_appdata) / "LunaAI"
                    candidate = user_base / "local_models"
                else:
                    # Fallback to home directory
                    candidate = Path.home() / ".lunaai" / "local_models"

                models_dir = candidate
            else:
                models_dir = default_dir

        self.models_dir = Path(models_dir)
        # Create parent directories if needed; ignore errors silently to avoid crashing UI
        try:
            self.models_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        
        self.config_file = self.models_dir / "models_config.json"
        self.loaded_models = {}  # Cache for loaded models
        
        # Model registry with HuggingFace repo IDs and filenames
        self.model_registry = {
            "local/mistral-7b-instruct": {
                "repo_id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
                "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
                "size_mb": 4370,
                "context_length": 4096
            },
            "local/llama-3.1-8b-instruct": {
                "repo_id": "bartowski/Meta-Llama-3.1-8B-Instruct-GGUF",
                "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
                "size_mb": 4920,
                "context_length": 8192
            },
            "local/qwen-2.5-7b-instruct": {
                "repo_id": "Qwen/Qwen2.5-7B-Instruct-GGUF",
                "filename": "qwen2.5-7b-instruct-q4_k_m.gguf",
                "size_mb": 4400,
                "context_length": 4096
            },
            "local/deepseek-coder-6.7b": {
                "repo_id": "TheBloke/deepseek-coder-6.7B-instruct-GGUF",
                "filename": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
                "size_mb": 3980,
                "context_length": 4096
            }
        }
        
        self._load_config()
    
    def _load_config(self):
        """Load model configuration from disk"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}
    
    def _save_config(self):
        """Save model configuration to disk"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is already downloaded"""
        if model_id not in self.model_registry:
            return False
        
        model_info = self.model_registry[model_id]
        model_path = self.models_dir / model_info["filename"]
        return model_path.exists()
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Get the file path for a downloaded model"""
        if not self.is_model_downloaded(model_id):
            return None
        
        model_info = self.model_registry[model_id]
        return self.models_dir / model_info["filename"]
    
    def download_model(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download a model from HuggingFace.
        
        Args:
            model_id: Model identifier (e.g., "local/mistral-7b-instruct")
            progress_callback: Optional callback function(current, total, status_msg)
        
        Returns:
            True if successful, False otherwise
        """
        if not HF_DOWNLOAD_AVAILABLE:
            print("[ERROR] huggingface_hub not available. Cannot download models.")
            return False
        
        if model_id not in self.model_registry:
            print(f"[ERROR] Unknown model: {model_id}")
            return False
        
        if self.is_model_downloaded(model_id):
            print(f"[INFO] Model {model_id} already downloaded")
            return True
        
        model_info = self.model_registry[model_id]
        
        try:
            print(f"[INFO] Downloading {model_id}...")
            print(f"[INFO] Size: ~{model_info['size_mb']}MB")
            
            if progress_callback:
                progress_callback(0, model_info['size_mb'], f"Starting download...")
            
            # Download the model file
            downloaded_path = hf_hub_download(
                repo_id=model_info["repo_id"],
                filename=model_info["filename"],
                cache_dir=str(self.models_dir),
                local_dir=str(self.models_dir),
                local_dir_use_symlinks=False
            )
            
            # Update config
            self.config[model_id] = {
                "downloaded": True,
                "path": str(downloaded_path),
                "repo_id": model_info["repo_id"],
                "filename": model_info["filename"]
            }
            self._save_config()
            
            if progress_callback:
                progress_callback(model_info['size_mb'], model_info['size_mb'], "Download complete!")
            
            print(f"[SUCCESS] Model {model_id} downloaded successfully!")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to download {model_id}: {e}")
            if progress_callback:
                progress_callback(0, 100, f"Error: {str(e)}")
            return False
    
    def load_model(self, model_id: str, n_ctx: int = 2048, n_gpu_layers: int = -1) -> Optional[Llama]:
        """
        Load a model into memory for inference.
        
        Args:
            model_id: Model identifier
            n_ctx: Context window size (default: 2048)
            n_gpu_layers: Number of layers to offload to GPU (-1 = all)
        
        Returns:
            Loaded Llama model or None if failed
        """
        if not LLAMA_AVAILABLE:
            print("[ERROR] llama-cpp-python not available; local inference disabled")
            return None
        
        # Check cache first
        if model_id in self.loaded_models:
            return self.loaded_models[model_id]
        
        model_path = self.get_model_path(model_id)
        if not model_path:
            print(f"[ERROR] Model {model_id} not downloaded. Download it first.")
            return None
        
        try:
            print(f"[INFO] Loading model {model_id}...")
            model = Llama(
                model_path=str(model_path),
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                verbose=False
            )
            
            # Cache the loaded model
            self.loaded_models[model_id] = model
            print(f"[SUCCESS] Model {model_id} loaded successfully!")
            return model
            
        except Exception as e:
            print(f"[ERROR] Failed to load {model_id}: {e}")
            return None
    
    def generate_response(self, model_id: str, prompt: str, max_tokens: int = 512, 
                         temperature: float = 0.7) -> Optional[str]:
        """
        Generate a response using a local model.
        
        Args:
            model_id: Model identifier
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
        
        Returns:
            Generated text or None if failed
        """
        model = self.load_model(model_id)
        if not model:
            return None
        
        try:
            response = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False
            )
            
            return response['choices'][0]['text'].strip()
            
        except Exception as e:
            print(f"[ERROR] Generation failed: {e}")
            return None
    
    def unload_model(self, model_id: str):
        """Unload a model from memory"""
        if model_id in self.loaded_models:
            del self.loaded_models[model_id]
            print(f"[INFO] Model {model_id} unloaded from memory")
    
    def delete_model(self, model_id: str) -> bool:
        """Delete a downloaded model from disk"""
        model_path = self.get_model_path(model_id)
        if not model_path:
            return False
        
        try:
            # Unload from memory first
            self.unload_model(model_id)
            
            # Delete file
            model_path.unlink()
            
            # Update config
            if model_id in self.config:
                del self.config[model_id]
                self._save_config()
            
            print(f"[SUCCESS] Model {model_id} deleted")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to delete {model_id}: {e}")
            return False
    
    def get_available_models(self) -> dict:
        """Get list of all available models with download status"""
        models = {}
        for model_id, info in self.model_registry.items():
            models[model_id] = {
                "downloaded": self.is_model_downloaded(model_id),
                "size_mb": info["size_mb"],
                "repo_id": info["repo_id"],
                "filename": info["filename"]
            }
        return models


# Global instance
_manager = None

def get_manager() -> LocalModelManager:
    """Get or create the global model manager instance"""
    global _manager
    if _manager is None:
        _manager = LocalModelManager()
    return _manager
