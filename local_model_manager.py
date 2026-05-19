"""
Local Model Manager
Handles downloading and running AI models directly without external tools.
"""

import os
import sys
import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Union

# We treat downloads and inference as separate capabilities:
#  - huggingface_hub is needed for downloading GGUF files
#  - llama-cpp-python is needed only for running local inference

try:
    from huggingface_hub import hf_hub_download, snapshot_download  # type: ignore[import-not-found]
    HF_DOWNLOAD_AVAILABLE = True
except ImportError:
    HF_DOWNLOAD_AVAILABLE = False

try:
    from llama_cpp import Llama  # type: ignore[import-not-found]
    LLAMA_AVAILABLE = True
except ImportError:
    # llama-cpp-python not available; keep type hints working with a stub
    LLAMA_AVAILABLE = False

    class Llama:  # type: ignore[no-redef]
        """Placeholder Llama class used when llama-cpp-python is unavailable.

        All runtime methods that rely on real local model support are
        gated on LLAMA_AVAILABLE, so this stub is never used for inference.
        It only prevents NameError from annotations like Optional[Llama].
        """

        def __init__(self, **kwargs: Any) -> None:
            pass

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            pass


class LocalModelManager:
    """Manages local AI model downloads and inference"""
    
    def __init__(self, models_dir: Union[str, Path, None] = None):
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
        self.loaded_models: Dict[str, Any] = {}  # Cache for loaded models
        self.config: Dict[str, Any] = {}  # Model config, populated by _load_config
        
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

        # Concurrency guard: only one hf_hub_download may run at a time.
        # download_model acquires this with blocking=False so concurrent callers
        # get an immediate False return instead of silently queuing up.
        self._download_lock = threading.Lock()
        self._active_download_id: Optional[str] = None
    
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

    # ------------------------------------------------------------------
    # Concurrency helpers
    # ------------------------------------------------------------------

    def is_downloading(self) -> bool:
        """Return True if a download is currently in progress."""
        return self._download_lock.locked()

    @staticmethod
    def _make_tqdm_class(progress_callback: Callable) -> Optional[type]:
        """Return a tqdm-compatible class that fires *progress_callback* on
        every chunk update so the frontend gets byte-level granularity.

        The callback signature matches the existing contract:
            progress_callback(current_bytes: int, total_bytes: int, msg: str)

        Returns None when tqdm is not importable so the caller can fall back
        gracefully.
        """
        try:
            from tqdm import tqdm as _BaseTqdm  # type: ignore[import-not-found]
        except ImportError:
            return None

        class _ProgressTqdm(_BaseTqdm):
            """tqdm subclass that mirrors update() calls into progress_callback."""

            def update(self, n: int = 1) -> bool:  # type: ignore[override]
                result = super().update(n)
                try:
                    progress_callback(
                        int(self.n),
                        int(self.total) if self.total else 0,
                        "",
                    )
                except Exception:
                    pass
                return result  # type: ignore[return-value]

        return _ProgressTqdm
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """Check if a model is already downloaded"""
        if model_id not in self.model_registry:
            return False
        
        model_info = self.model_registry[model_id]
        model_path = self.models_dir / str(model_info["filename"])
        return model_path.exists()
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """Get the file path for a downloaded model"""
        if not self.is_model_downloaded(model_id):
            return None
        
        model_info = self.model_registry[model_id]
        return self.models_dir / str(model_info["filename"])
    
    def download_model(self, model_id: str, progress_callback: Optional[Callable] = None, force: bool = False) -> bool:
        """
        Download a model from HuggingFace.

        Acquires a non-blocking threading.Lock so that a second concurrent call
        (e.g. from a race between the frontend queue and a stale retry) is
        rejected immediately with return False instead of spawning a second
        hf_hub_download process.

        Chunk-by-chunk progress is delivered via a custom tqdm subclass so
        the frontend progress_callback receives byte-level updates rather than
        just the start/finish events.

        Args:
            model_id: Model identifier (e.g., "local/mistral-7b-instruct")
            progress_callback: Optional callback(current_bytes, total_bytes, msg)
            force: If True, re-download even if the model file already exists.

        Returns:
            True if successful, False otherwise
        """
        if not HF_DOWNLOAD_AVAILABLE:
            print("[ERROR] huggingface_hub not available. Cannot download models.")
            return False

        if model_id not in self.model_registry:
            print(f"[ERROR] Unknown model: {model_id}")
            return False

        # --- Concurrency guard -------------------------------------------
        # blocking=False means a second caller gets False immediately rather
        # than silently queuing behind the active download.
        acquired = self._download_lock.acquire(blocking=False)
        if not acquired:
            print(
                f"[WARN] download_model: download already in progress for "
                f"'{self._active_download_id}'. Rejecting concurrent request "
                f"for '{model_id}'."
            )
            if progress_callback:
                try:
                    progress_callback(
                        0, 0,
                        f"Download already in progress for '{self._active_download_id}'"
                    )
                except Exception:
                    pass
            return False

        self._active_download_id = model_id
        try:
            return self._run_download(model_id, progress_callback, force)
        finally:
            self._active_download_id = None
            self._download_lock.release()

    def _run_download(self, model_id: str, progress_callback: Optional[Callable], force: bool) -> bool:
        """Internal: performs the actual hf_hub_download (runs under lock).

        Progress delivery strategy
        --------------------------
        huggingface_hub >= 0.20 removed the `tqdm_class` kwarg from
        hf_hub_download, and the internal module path for tqdm changes
        between versions, so static module-path patching is fragile.

        Instead we iterate sys.modules at call-time and patch every
        huggingface_hub.* submodule that exposes a `tqdm` attribute.
        This catches whichever import path the installed version actually
        uses.  All patches are reversed in a `finally` block so the
        process-wide state is never left dirty.
        """
        if self.is_model_downloaded(model_id):
            if not force:
                print(f"[INFO] Model {model_id} already downloaded")
                if progress_callback:
                    try:
                        mi = self.model_registry[model_id]
                        sz = mi['size_mb'] * 1024 * 1024
                        progress_callback(sz, sz, "Already downloaded")
                    except Exception:
                        pass
                return True
            # Force re-download: remove the existing file first
            print(f"[INFO] Force re-downloading model {model_id}...")
            try:
                existing_path = self.get_model_path(model_id)
                if existing_path and existing_path.exists():
                    self.unload_model(model_id)
                    existing_path.unlink()
            except Exception as e:
                print(f"[WARN] Could not remove existing model file: {e}")

        model_info = self.model_registry[model_id]

        try:
            print(f"[INFO] Downloading {model_id}...")
            print(f"[INFO] Size: ~{model_info['size_mb']} MB")

            if progress_callback:
                try:
                    progress_callback(0, model_info['size_mb'] * 1024 * 1024, "Starting download...")
                except Exception:
                    pass

            # ------------------------------------------------------------------
            # Dynamically patch every huggingface_hub submodule that holds a
            # `tqdm` attribute so chunk-level progress reaches the callback,
            # regardless of which internal import path the installed version uses.
            #
            # Each patched class inherits from the module's OWN tqdm class
            # (not the base tqdm.tqdm) so custom __init__ signatures — e.g. the
            # `name` kwarg in huggingface_hub.xet_get — are fully preserved.
            # ------------------------------------------------------------------
            patched_modules: Dict[str, Any] = {}  # {module_name: original_tqdm}

            if progress_callback is not None:
                try:
                    import tqdm as _tqdm_root
                    orig_tqdm_base = _tqdm_root.tqdm

                    _cb = progress_callback  # closure capture

                    # Scan all already-imported huggingface_hub submodules.
                    for mod_name, mod in list(sys.modules.items()):
                        if not mod_name.startswith("huggingface_hub"):
                            continue
                        if mod is None:
                            continue
                        if not hasattr(mod, "tqdm"):
                            continue

                        orig = getattr(mod, "tqdm")

                        # Only patch if it's actually a tqdm subclass; skip
                        # plain functions, strings, or unrelated objects.
                        if not (isinstance(orig, type) and issubclass(orig, orig_tqdm_base)):
                            continue

                        try:
                            patched_modules[mod_name] = orig

                            # Subclass the module's OWN tqdm so its custom
                            # __init__ (e.g. xet_get's `name` kwarg) is kept.
                            class _DynamicPatchedTqdm(orig):  # type: ignore[valid-type]
                                def update(self, n: int = 1) -> None:  # type: ignore[override]
                                    super().update(n)
                                    try:
                                        _cb(
                                            int(self.n),
                                            int(self.total) if self.total else 0,
                                            "",
                                        )
                                    except Exception:
                                        pass

                            setattr(mod, "tqdm", _DynamicPatchedTqdm)
                        except Exception:
                            pass  # read-only attribute or other error — skip silently

                    if patched_modules:
                        print(f"[DEBUG] _run_download: patched tqdm in "
                              f"{len(patched_modules)} huggingface_hub module(s): "
                              f"{list(patched_modules.keys())}")
                    else:
                        print("[WARN] _run_download: no huggingface_hub modules with "
                              "a tqdm subclass found; stderr capture is the fallback.")
                except Exception as patch_err:
                    print(f"[WARN] _run_download: sys.modules patch failed: {patch_err}")

            hf_kwargs: Dict[str, Any] = {
                "repo_id": model_info["repo_id"],
                "filename": model_info["filename"],
                "local_dir": str(self.models_dir),
                "local_dir_use_symlinks": False,
            }

            try:
                downloaded_path = hf_hub_download(**hf_kwargs)
            finally:
                # Restore every patched module unconditionally.
                for mod_name, orig_tqdm in patched_modules.items():
                    mod = sys.modules.get(mod_name)
                    if mod is not None:
                        try:
                            setattr(mod, "tqdm", orig_tqdm)
                        except Exception:
                            pass
                if patched_modules:
                    print(f"[DEBUG] _run_download: tqdm restored in "
                          f"{len(patched_modules)} module(s).")

            # Persist metadata
            self.config[model_id] = {
                "downloaded": True,
                "path": str(downloaded_path),
                "repo_id": model_info["repo_id"],
                "filename": model_info["filename"],
            }
            self._save_config()

            if progress_callback:
                try:
                    sz = model_info['size_mb'] * 1024 * 1024
                    progress_callback(sz, sz, "Download complete!")
                except Exception:
                    pass

            print(f"[SUCCESS] Model {model_id} downloaded successfully!")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to download {model_id}: {e}")
            if progress_callback:
                try:
                    progress_callback(0, 0, f"Error: {e}")
                except Exception:
                    pass
            return False
    
    def load_model(self, model_id: str, n_ctx: int = 2048, n_gpu_layers: int = -1) -> Optional[Llama]:
        """
        Load a model into memory for inference.

        Path resolution is a pure filesystem check (model_registry filename +
        models_dir); no HuggingFace API calls are made here.  The in-memory
        cache means repeated calls for the same model_id are O(1) dict lookups.

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

        # Fast path: already loaded in this session
        if model_id in self.loaded_models:
            return self.loaded_models[model_id]

        # Filesystem-only check — no network/HF API involved
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
            self.loaded_models.pop(model_id)
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
                self.config.pop(model_id)
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
