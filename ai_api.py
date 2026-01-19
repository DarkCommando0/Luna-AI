import os
import sys
import time
import re
import subprocess
import platform
import requests
import webbrowser
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

# Custom exception to carry HTTP status codes from HF calls
class HFRequestError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
from ddgs import DDGS

# Import SettingsManager only for type checking to avoid circular imports
if TYPE_CHECKING:
    from app import SettingsManager

# Lightweight .env loader (no external dependency). Loads key=value pairs into os.environ
def _load_env_from_dotenv():
    try:
        # When running under PyInstaller, __file__ may point to a temp folder.
        # Use the executable directory so .env next to LunaAI.exe is persistent.
        if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
            root_dir = os.path.dirname(sys.executable)
        else:
            root_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(root_dir, ".env")
        if not os.path.exists(env_path):
            return
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val and key not in os.environ:
                    os.environ[key] = val
        print("[OK] Loaded environment variables from .env")
    except Exception as e:
        print(f"[WARN] Failed to load .env: {e}")

def _get_user_data_dir() -> str:
    try:
        root_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(root_dir, "user_data")
        os.makedirs(data_dir, exist_ok=True)
        return data_dir
    except Exception:
        return os.path.dirname(os.path.abspath(__file__))

def _get_local_engine_profile_path() -> str:
    base = _get_user_data_dir()
    return os.path.join(base, "local_engine_profile.json")

class LocalConversationEngine:
    """Enhanced fast local conversation system with advanced creativity controls"""
    
    def __init__(self, creativity_level: float = 0.7):
        self.creativity_level = creativity_level
        self.conversation_history = []
        self.response_patterns = self.load_response_patterns()
        self.context_memory = []
        self.max_memory = 10
        self.user_profile = {}
    
    def set_creativity(self, level: float):
        """Update creativity level and adjust response patterns accordingly"""
        self.creativity_level = max(0.1, min(1.0, level))
        print(f"🎨 Conversation engine creativity updated to {self.creativity_level}")
    
    def set_memory_size(self, size: int):
        """Update conversation memory size"""
        self.max_memory = max(5, min(50, size))
        # Trim existing memory if needed
        if len(self.context_memory) > self.max_memory:
            self.context_memory = self.context_memory[-self.max_memory:]
    
    def add_to_memory(self, user_input: str, response: str):
        """Add interaction to conversation memory"""
        self.context_memory.append({
            'user': user_input.lower().strip(),
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Maintain memory limit
        if len(self.context_memory) > self.max_memory:
            self.context_memory.pop(0)

    def to_dict(self) -> Dict[str, object]:
        try:
            return {
                "context_memory": list(self.context_memory),
                "user_profile": dict(self.user_profile or {}),
                "max_memory": int(self.max_memory),
            }
        except Exception:
            return {"context_memory": [], "user_profile": {}, "max_memory": 10}

    def load_from_dict(self, data: Dict[str, object]):
        try:
            mem = data.get("context_memory", []) if isinstance(data, dict) else []
            if isinstance(mem, list):
                self.context_memory = list(mem)
            prof = data.get("user_profile", {}) if isinstance(data, dict) else {}
            if isinstance(prof, dict):
                self.user_profile = dict(prof)
            max_mem = data.get("max_memory", self.max_memory) if isinstance(data, dict) else self.max_memory
            try:
                self.max_memory = max(5, min(50, int(max_mem)))
            except Exception:
                pass
            if len(self.context_memory) > self.max_memory:
                self.context_memory = self.context_memory[-self.max_memory:]
        except Exception:
            pass

    def save_to_disk(self):
        path = _get_local_engine_profile_path()
        try:
            payload = self.to_dict()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def load_from_disk(self):
        path = _get_local_engine_profile_path()
        try:
            if not os.path.exists(path):
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.load_from_dict(data)
        except Exception:
            pass

    def clear_disk_data(self):
        path = _get_local_engine_profile_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
    
    def load_response_patterns(self) -> Dict[str, List[str]]:
        """Load enhanced conversational response patterns with creativity variations"""
        return {
            "greetings": {
                "conservative": [
                    "Hello! How can I assist you today?",
                    "Hi there! What can I help you with?",
                    "Good day! How may I help you?"
                ],
                "balanced": [
                    "Hello! How can I assist you today?",
                    "Hi there! What can I help you with?",
                    "Good to see you! What's on your mind?",
                    "Hey! Ready to help with whatever you need.",
                    "Greetings! How may I be of service?"
                ],
                "creative": [
                    "Hello there, wonderful human! What adventure shall we embark on today?",
                    "Greetings, my friend! What fascinating topic can we explore together?",
                    "Hey there! I'm buzzing with excitement to help you with anything!",
                    "Well hello! What delightful challenge can I tackle for you today?",
                    "Salutations! Ready to dive into whatever's on your brilliant mind!"
                ]
            },
            "how_are_you": {
                "conservative": [
                    "I'm functioning well, thank you. How are you?",
                    "All systems operational. How can I help?",
                    "I'm doing fine. What can I do for you?"
                ],
                "balanced": [
                    "I'm doing great, thank you for asking! How are you?",
                    "All systems running smoothly! How's your day going?",
                    "Fantastic, thanks! What can I help you accomplish today?",
                    "I'm here and ready to help! What's new with you?"
                ],
                "creative": [
                    "I'm absolutely fantastic! My circuits are practically humming with joy! How's your day treating you?",
                    "Couldn't be better! I'm like a digital ray of sunshine today! What's got you curious?",
                    "I'm thriving in the digital realm! Every conversation energizes me. How are you doing, my friend?",
                    "Spectacular! I'm feeling particularly clever today. What puzzle can we solve together?"
                ]
            },
            "thanks": {
                "conservative": [
                    "You're welcome. Anything else I can help with?",
                    "Glad to help. Is there anything else?",
                    "No problem. What else can I do?"
                ],
                "balanced": [
                    "You're very welcome! Anything else I can help with?",
                    "Happy to help! Is there anything else you need?",
                    "My pleasure! Let me know if you need anything else.",
                    "Glad I could assist! What else can I do for you?"
                ],
                "creative": [
                    "Absolutely my pleasure! Helping you brightens my entire digital day!",
                    "You're so welcome! It's like digital dopamine when I can be useful!",
                    "Aww, you're too kind! I live for moments like these. What's next on our agenda?",
                    "The pleasure was all mine! I'm practically glowing with satisfaction right now!"
                ]
            },
            "capabilities": {
                "conservative": [
                    "I can help with weather, web searches, system commands, and conversation.",
                    "My functions include weather information, internet searches, and system operations.",
                    "I provide weather data, search results, system commands, and general assistance."
                ],
                "balanced": [
                    "I can help with weather, web searches, system commands, and general conversation!",
                    "I'm great at finding information, controlling your system, checking weather, and chatting!",
                    "Weather updates, web searches, opening programs, and friendly conversation are my specialties!"
                ],
                "creative": [
                    "Oh, I'm like a digital Swiss Army knife! Weather wizardry, web search sorcery, system command mastery, and conversation that'll knock your socks off!",
                    "I'm your personal digital genie! I grant wishes for weather info, conjure search results from the internet, command your system like magic, and chat with the enthusiasm of a thousand coffee shots!",
                    "Think of me as your AI sidekick! I can forecast weather like a meteorologist, search the web faster than you can blink, control your computer like a digital puppeteer, and chat with more personality than a talk show host!"
                ]
            },
            "confused": {
                "conservative": [
                    "I don't understand. Please clarify.",
                    "Could you rephrase that?",
                    "Please provide more information."
                ],
                "balanced": [
                    "I'm not quite sure I understand. Could you rephrase that?",
                    "Could you clarify what you're looking for?",
                    "I want to help, but I need a bit more information."
                ],
                "creative": [
                    "Hmm, you've got me scratching my digital head! Could you paint that picture a bit clearer for me?",
                    "Oops, my understanding circuits are a bit tangled! Mind rewording that masterpiece?",
                    "I'm drawing a delightful blank here! Help me connect the dots with a little more detail?"
                ]
            },
            "default_responses": {
                "conservative": [
                    "I see. What would you like to know about that?",
                    "That's interesting. How can I help?",
                    "Please tell me more about what you need."
                ],
                "balanced": [
                    "That's interesting! Tell me more about that.",
                    "I see! What would you like to know about it?",
                    "Fascinating! How can I help you with that?",
                    "That sounds intriguing! What specifically interests you about it?"
                ],
                "creative": [
                    "Ooh, that's got my curiosity circuits firing on all cylinders! Spill the details!",
                    "Now THAT sounds like an adventure waiting to happen! What's the scoop?",
                    "My interest is officially piqued! Let's dive deep into this rabbit hole together!",
                    "You've struck digital gold with that topic! I'm all ears (well, all sensors)!"
                ]
            }
        }
    
    def get_creativity_tier(self) -> str:
        """Determine creativity tier based on current level"""
        if self.creativity_level <= 0.3:
            return "conservative"
        elif self.creativity_level <= 0.7:
            return "balanced"
        else:
            return "creative"
    
    def analyze_intent(self, message: str) -> str:
        """Enhanced intent analysis with context awareness"""
        message_lower = message.lower().strip()
        
        # Check conversation memory for context
        recent_context = self.context_memory[-3:] if self.context_memory else []
        
        # Basic intent patterns
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "greetings"]):
            return "greetings"
        elif any(phrase in message_lower for phrase in ["how are you", "how's it going", "how do you feel"]):
            return "how_are_you" 
        elif any(word in message_lower for word in ["thanks", "thank you", "appreciate", "grateful"]):
            return "thanks"
        elif any(word in message_lower for word in ["good job", "excellent", "amazing", "awesome", "brilliant"]):
            return "compliments"
        elif any(phrase in message_lower for phrase in ["what can you do", "your abilities", "your capabilities", "help me"]):
            return "capabilities"
        elif any(word in message_lower for word in ["bye", "goodbye", "see you", "farewell", "exit"]):
            return "farewells"
        elif len(message_lower) < 15 and "?" in message_lower:
            return "confused"
        else:
            return "default"
    
    def select_response(self, responses: List[str]) -> str:
        """Select response based on creativity level with enhanced algorithms"""
        if not responses:
            return "I'm here to help!"
        
        if self.creativity_level <= 0.3:
            # Conservative: Always use first response for consistency
            return responses[0]
        elif self.creativity_level <= 0.5:
            # Low-medium: Slight variation, prefer earlier responses
            weights = [3, 2, 1] + [1] * (len(responses) - 3)
            weights = weights[:len(responses)]
            return random.choices(responses, weights=weights)[0]
        elif self.creativity_level <= 0.7:
            # Medium: Balanced selection with some preference for variety
            weights = [2, 2, 2, 1, 1] + [1] * (len(responses) - 5)
            weights = weights[:len(responses)]
            return random.choices(responses, weights=weights)[0]
        elif self.creativity_level <= 0.8:
            # High-medium: More random, slight preference for later responses
            weights = [1, 1, 2, 2, 3] + [2] * (len(responses) - 5)
            weights = weights[:len(responses)]
            return random.choices(responses, weights=weights)[0]
        else:
            # Maximum creativity: Completely random with potential for response mixing
            if len(responses) > 1 and random.random() < 0.1:  # 10% chance to mix responses
                selected = random.sample(responses, min(2, len(responses)))
                return f"{selected[0]} {selected[1].lower()}"
            return random.choice(responses)
    
    def generate_response(self, message: str) -> str:
        """Generate enhanced contextual response based on user input"""
        intent = self.analyze_intent(message)
        creativity_tier = self.get_creativity_tier()
        
        # Get appropriate response set
        if intent in self.response_patterns:
            if isinstance(self.response_patterns[intent], dict):
                responses = self.response_patterns[intent].get(creativity_tier, self.response_patterns[intent]["balanced"])
            else:
                responses = self.response_patterns[intent]
        else:
            responses = self.response_patterns["default_responses"].get(creativity_tier, 
                                                                      self.response_patterns["default_responses"]["balanced"])
        
        # Select response based on creativity level
        response = self.select_response(responses)
        
        # Add to conversation memory
        self.add_to_memory(message, response)
        try:
            remember = advanced_settings.get('remember_local_profile', True)
        except Exception:
            remember = True
        if remember:
            try:
                self.save_to_disk()
            except Exception:
                pass
        
        # High creativity: occasionally add personality flourishes
        if self.creativity_level > 0.8 and random.random() < 0.15:
            flourishes = [
                " amazing", " spectacular", " fantastic", " wonderful", " brilliant", " awesome", " incredible", " extraordinary"
            ]
            response += random.choice(flourishes)
        
        return response

class OpenRouterAPI:
    """OpenRouter API interface for accessing premium models"""
    
    def __init__(self, api_key: Optional[str] = None):
        env_token = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_key = env_token
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {env_token}" if env_token else "",
            "Content-Type": "application/json"
        }
        try:
            masked = (self.api_key[:8] + "..." + self.api_key[-4:]) if self.api_key and len(self.api_key) > 12 else ("present" if self.api_key else "missing")
            print(f"[DEBUG] OpenRouter token at init: {masked if self.api_key else 'missing'}")
        except Exception:
            pass
    
    def query_model(self, model_id: str, inputs: str, max_tokens: int = 150) -> str:
        """Query a model via OpenRouter"""
        try:
            if not self.api_key:
                raise RuntimeError("OpenRouter API key not configured")
            
            payload = {
                "model": model_id,
                "messages": [
                    {"role": "user", "content": inputs}
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(self.base_url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content'].strip()
                return "Empty response from OpenRouter"
            else:
                err_text = response.text or ""
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict) and 'error' in err_json:
                        err_text = str(err_json['error'])
                except Exception:
                    pass
                print(f"OpenRouter API Error: {response.status_code} - {err_text}")
                raise RuntimeError(f"OpenRouter request failed: {response.status_code}")
        except Exception as e:
            raise e

class OpenRouterAPI:
    """OpenRouter API interface for various models"""
    
    def __init__(self, api_key: Optional[str] = None):
        env_token = api_key or os.getenv("OPENROUTER_API_KEY")
        self.api_key = env_token
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.headers = ({"Authorization": f"Bearer {env_token}"} if env_token else {})
        try:
            masked = (self.api_key[:4] + "..." + self.api_key[-4:]) if self.api_key and len(self.api_key) > 8 else ("present" if self.api_key else "missing")
            print(f"[DEBUG] OpenRouter token at init: {masked if self.api_key else 'missing'}; headers set: {bool(self.headers)}")
        except Exception:
            pass
    
    def query_model(self, model_id: str, inputs: str, max_tokens: int = 150) -> str:
        """Query a specific OpenRouter model"""
        try:
            # Allow per-model endpoint overrides via env: OPENROUTER_ENDPOINT__{SANITIZED_MODEL_ID}
            def _sanitize(mid: str) -> str:
                return ''.join(ch if ch.isalnum() else '_' for ch in mid)
            override = os.getenv(f"OPENROUTER_ENDPOINT__{_sanitize(model_id)}")
            url = override.strip() if override else self.base_url
            
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": inputs}],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Handle OpenRouter response format
                try:
                    data = response.json()
                    if 'choices' in data and data['choices']:
                        return data['choices'][0]['message']['content']
                    elif isinstance(data, list) and data and isinstance(data[0], dict) and 'generated_text' in data[0]:
                        # Fallback for HF-style responses
                        return data[0]['generated_text']
                    else:
                        print(f"Unexpected OpenRouter response format: {data}")
                        raise RuntimeError("Unexpected OpenRouter response format")
                except Exception as e:
                    print(f"Failed to parse OpenRouter response: {e}")
                    raise RuntimeError(f"Failed to parse OpenRouter response: {e}")
            else:
                # Try to parse structured error
                err_text = response.text or ""
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict) and 'error' in err_json:
                        err_text = str(err_json['error'])
                except Exception:
                    pass

                print(f"HF API Error: {response.status_code} - {err_text}")

                # Detect paused/loading states explicitly and trigger fallback upstream
                lower_err = err_text.lower()
                if "paused" in lower_err or "space is paused" in lower_err:
                    raise RuntimeError("HF endpoint paused")
                if "loading" in lower_err or response.status_code in (503, 524):
                    raise RuntimeError("HF endpoint loading")

                # Raise rich error with status code so caller can make smart decisions
                if response.status_code in (401, 403):
                    raise HFRequestError(response.status_code, "HF authentication/authorization error")
                if response.status_code == 429:
                    raise HFRequestError(response.status_code, "HF rate limit exceeded")
                if response.status_code == 400:
                    # Common case: paused/loading endpoints return 400
                    # Try to extract error text for UX
                    err_txt = ""
                    try:
                        err_json = response.json()
                        err_txt = err_json.get("error") or err_json.get("message") or ""
                    except Exception:
                        pass
                    msg = f"Bad Request: {err_txt}" if err_txt else "Bad Request"
                    raise HFRequestError(400, msg)
                if response.status_code == 404:
                    raise HFRequestError(404, "Model not found or endpoint removed")
                # Generic failure
                raise HFRequestError(response.status_code, f"HF request failed: {response.status_code}")
                
        except requests.exceptions.Timeout as e:
            # Propagate so upstream can perform fallback
            raise e
        except HFRequestError:
            # Pass through
            raise
        except Exception as e:
            # Wrap unknown errors
            raise HFRequestError(-1, str(e))


# Initialize the conversation engine and APIs globally
conversation_engine = LocalConversationEngine()

# ... rest of the code remains the same ...
# Load environment variables from .env before creating API clients
try:
    _load_env_from_dotenv()
except Exception:
    pass

openrouter_api = OpenRouterAPI()
settings_manager = None  # Will be set by set_settings_manager

# Advanced settings globals
advanced_settings = {
    'enable_search': True,
    'enable_system_commands': True,
    'search_results_limit': 3,
    'conversation_memory': 10,
    'response_delay': 0.1,
    'current_model': 'local_engine',
    'remember_local_profile': True
}

def set_settings_manager(manager: 'SettingsManager'):
    """Set the settings manager instance to use for application settings."""
    global settings_manager
    settings_manager = manager
    try:
        level = settings_manager.get('ai_creativity', 0.7)
        set_ai_creativity(level)
        advanced_settings['enable_search'] = settings_manager.get('enable_web_search', True)
        advanced_settings['enable_system_commands'] = settings_manager.get('enable_system_commands', True)
        advanced_settings['search_results_limit'] = settings_manager.get('search_results_limit', 3)
        advanced_settings['conversation_memory'] = settings_manager.get('conversation_memory', 10)
        advanced_settings['response_delay'] = settings_manager.get('response_delay', 0.1)
        advanced_settings['current_model'] = settings_manager.get('current_ai_model', 'local_engine')
        remember = settings_manager.get('save_chat_history', True)
        advanced_settings['remember_local_profile'] = bool(remember)
        if remember:
            try:
                conversation_engine.load_from_disk()
            except Exception:
                pass
    except Exception:
        pass

def set_openrouter_api_token(token: Optional[str]):
    """Update the OpenRouter API token at runtime."""
    try:
        if token and isinstance(token, str) and token.strip():
            openrouter_api.api_key = token.strip()
            openrouter_api.headers = {"Authorization": f"Bearer {openrouter_api.api_key}"}
            try:
                masked = (openrouter_api.api_key[:4] + "..." + openrouter_api.api_key[-4:]) if len(openrouter_api.api_key) > 8 else "applied"
                print(f"[OK] OpenRouter token applied at runtime: {masked}")
            except Exception:
                pass
            return True
    except Exception:
        pass
    return False

def reload_openrouter_token_from_env() -> bool:
    """Reload .env and apply OpenRouter token from environment. Returns True if token applied."""
    try:
        _load_env_from_dotenv()
        tok = os.getenv("OPENROUTER_API_KEY")
        if tok and tok.strip():
            openrouter_api.api_key = tok.strip()
            openrouter_api.headers = {"Authorization": f"Bearer {openrouter_api.api_key}"}
            try:
                masked = (openrouter_api.api_key[:4] + "..." + openrouter_api.api_key[-4:]) if len(openrouter_api.api_key) > 8 else "applied"
                print(f"[OK] OpenRouter token reloaded from env: {masked}")
            except Exception:
                pass
            return True
        else:
            print("[INFO] No OpenRouter token found in environment")
            return False
    except Exception:
        pass
    return False

def set_ai_creativity(level: float):
    """Update the AI creativity level from settings"""
    global conversation_engine
    conversation_engine.set_creativity(level)
    print(f"[OK] AI creativity level set to {level}")

def update_advanced_settings(settings_dict: dict):
    """Update advanced settings from the settings manager"""
    global advanced_settings
    advanced_settings.update(settings_dict)
    # Keep conversation engine in sync
    if 'conversation_memory' in settings_dict:
        conversation_engine.set_memory_size(settings_dict['conversation_memory'])
    if 'response_delay' in settings_dict:
        pass  # handled in call_ai_api

def _get_env_alt_models() -> list:
    """Read HF_ALT_MODELS env var as a comma-separated list of model IDs."""
    try:
        raw = os.getenv("HF_ALT_MODELS", "")
        if not raw:
            return []
        items = [m.strip() for m in raw.split(',') if m.strip()]
        return items
    except Exception:
        return []

# Prefer the UI-declared available models when present to ensure consistency with the Luna UI
def _get_ui_available_models() -> dict:
    """Return the available models map from the UI SettingsManager if set; otherwise fallback to backend defaults."""
    try:
        if settings_manager is not None:
            models = settings_manager.get('available_models')
            if isinstance(models, dict) and models:
                return models
    except Exception:
        pass
    return get_available_models()

def check_openrouter_model_status(model_id: str, timeout: int = 5, max_tokens: int = 1) -> dict:
    """Lightweight check to determine a OpenRouter model endpoint status.

    Returns a dict: {'status': 'available'|'paused'|'loading'|'error', 'error': str|None}
    Note: 404 responses are treated as 'error' with message 'model not found or endpoint removed'.
    """
    try:
        # Only applicable to OpenRouter models
        if model_id == 'local_engine':
            return {'status': 'available', 'error': None}

        url = f"{openrouter_api.base_url}"
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "status ping"}],
            "max_tokens": max_tokens,
            "temperature": 0.1
        }
        resp = requests.post(url, headers=openrouter_api.headers, json=payload, timeout=timeout)
        try:
            data = resp.json()
        except Exception:
            data = None

        if resp.status_code == 200:
            return {'status': 'available', 'error': None}
        err_text = ''
        try:
            if isinstance(data, dict):
                err_text = (data.get('error') or data.get('message') or '').strip()
        except Exception:
            pass
        # Map 400 with 'paused' signal to paused with guidance
        if 'paused' in (err_text.lower() if err_text else '') or resp.status_code == 400:
            # Provide actionable guidance links for paused endpoints
            guidance = ('Endpoint paused. See how pause works: '
                        'https://openrouter.ai/docs')
            msg = err_text or 'endpoint paused'
            return {'status': 'paused', 'error': f"{msg}. {guidance}"}
        if 'loading' in err_text.lower() or resp.status_code in (503, 524):
            return {'status': 'loading', 'error': err_text or 'endpoint loading'}
        if resp.status_code in (401, 403):
            return {'status': 'error', 'error': 'authentication/authorization error'}
        if resp.status_code == 429:
            return {'status': 'error', 'error': 'rate limit exceeded'}
        if resp.status_code == 404:
            # Provide guidance for 404s: often means no standard Inference API; use Providers or your own endpoint
            guidance = ('Check OpenRouter documentation: https://openrouter.ai/docs '
                        'and model availability: https://openrouter.ai/models')
            return {'status': 'error', 'error': guidance}
        return {'status': 'error', 'error': f"OpenRouter request failed: {resp.status_code}: {err_text}"}
    except requests.exceptions.Timeout:
        return {'status': 'error', 'error': 'timeout'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def enhanced_web_search(query, num_results=3):
    """Enhanced web search with better error handling and result formatting"""
    try:
        query = query.strip()
        if not query or len(query) < 2:
            return "Please provide a more specific search query."
        
        print(f"Searching for: {query}")
        search_results = []
        
        # Enhanced search methods with better fallbacks
        search_methods = [
            lambda: DDGS().text(query, max_results=num_results),
            lambda: DDGS().news(query, max_results=num_results) if any(word in query.lower() 
                for word in ['news', 'nfl', 'sports', 'score', 'game', 'today', 'latest', 'breaking']) else [],
            lambda: DDGS().text(query, region='us-en', max_results=num_results),
            lambda: DDGS().text(f'"{query}"', max_results=num_results),  # Exact phrase search
        ]
        
        for i, method in enumerate(search_methods):
            try:
                print(f"Trying search method {i+1}...")
                results = list(method())
                
                if not results:
                    continue
                
                for result in results:
                    title = result.get('title', '').strip()
                    body = result.get('body', '').strip() 
                    url = result.get('href') or result.get('url', '')
                    date = result.get('date', '')
                    
                    if title:
                        # Format with clickable links using markdown
                        result_text = f"**{title}**"
                        if date:
                            result_text += f" ({date})"
                        if body:
                            # Truncate body for speed
                            if len(body) > 150:
                                body = body[:150].rsplit(' ', 1)[0] + "..."
                            result_text += f"\n{body}"
                        if url:
                            result_text += f"\n[View source]({url})"
                        
                        search_results.append(result_text)
                
                if search_results:
                    print(f"Found {len(search_results)} results using method {i+1}")
                    
                    # Simplified header formatting
                    header = f"Search results for '{query}':"
                    
                    # Join results with better spacing
                    return header + "\n\n" + "\n\n".join(search_results)
                    
            except Exception as e:
                print(f"Search method {i+1} failed: {e}")
                continue
        
        # Enhanced instant answers fallback
        try:
            print("Trying instant answers...")
            instant_results = list(DDGS().chat(query, max_results=2))
            if instant_results:
                for answer in instant_results[:2]:
                    text = answer.get('text', '').strip()
                    if text and len(text) > 10:
                        # Format instant answers
                        result_text = f"**Quick Answer:**\n{text}"
                        search_results.append(result_text)
                        
                if search_results:
                    header = f"Search results for '{query}':"
                    return header + "\n\n" + "\n\n".join(search_results)
        except Exception as e:
            print(f"Instant answers failed: {e}")
        
        return f"Sorry, I'm having trouble accessing search results for '{query}' right now."
            
    except Exception as e:
        print(f"Search function error: {e}")
        return f"Search service is temporarily unavailable. Please try searching directly on Google for '{query}'."

def get_weather(city="Beavercreek,Ohio"):
    """Enhanced weather data with personality based on creativity.

    Requires an OpenWeatherMap API key. If no key is configured, returns a
    clear explanation instead of attempting a network call.
    """
    # Prefer key from environment, then from settings (if available)
    api_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    try:
        if (not api_key) and settings_manager is not None:
            api_key = (settings_manager.get("openweathermap_api_key", "") or "").strip()
    except Exception:
        pass

    if not api_key:
        # No key configured: do not hit the API at all
        if conversation_engine.creativity_level > 0.7:
            return (
                "I can't fetch live weather yet because no OpenWeatherMap API key "
                "is configured. Add your key in the Settings or .env file to "
                "enable real-time weather."
            )
        else:
            return (
                "Weather is currently disabled because no OpenWeatherMap API "
                "key is configured. Please add your key in Settings or the .env "
                "file to enable weather."
            )

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=imperial"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get("cod") == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            
            # Format response based on creativity level
            creativity = conversation_engine.creativity_level
            
            if creativity <= 0.3:
                return f"Weather in {city}: {desc.title()}, {temp}°F (feels like {feels_like}°F), humidity {humidity}%"
            elif creativity <= 0.7:
                return f"🌤️ Weather in {city}: {desc.title()}, {temp}°F (feels like {feels_like}°F), humidity {humidity}%"
            else:
                weather_emojis = {
                    'clear': '☀️', 'clouds': '☁️', 'rain': '🌧️', 'snow': '❄️', 
                    'thunderstorm': '⛈️', 'drizzle': '🌦️', 'mist': '🌫️', 'fog': '🌫️'
                }
                emoji = next((v for k, v in weather_emojis.items() if k in desc.lower()), '🌤️')
                
                temp_comment = ""
                if temp > 80:
                    temp_comment = " (toasty!)"
                elif temp < 32:
                    temp_comment = " (brrr!)"
                elif temp < 50:
                    temp_comment = " (cozy sweater weather!)"
                
                return f"Weather report for {city}! It's {desc.lower()} with {temp}°F{temp_comment} (feels like {feels_like}°F). Humidity is hanging out at {humidity}%. Perfect for whatever adventure you're planning!"
        else:
            error_msg = data.get('message', 'Unknown error')
            if conversation_engine.creativity_level > 0.7:
                return f"Oops! The weather spirits aren't cooperating for {city} right now. Error: {error_msg}"
            else:
                return f"Sorry, couldn't fetch weather data for {city}. Error: {error_msg}"
    except requests.RequestException as e:
        if conversation_engine.creativity_level > 0.7:
            return f"The weather service is having a digital hiccup! Error: {e}"
        else:
            return f"Error fetching weather data: {e}"
    except Exception as e:
        return f"Weather service error: {e}"

def execute_system_command(command):
    """Enhanced system commands with creative responses"""
    if not advanced_settings.get('enable_system_commands', True):
        if conversation_engine.creativity_level > 0.7:
            return "System commands are taking a break right now! You can enable them in the advanced settings."
        else:
            return "System commands are currently disabled. Please enable them in the advanced settings."
    
    command = command.lower()
    creativity = conversation_engine.creativity_level
    
    # Open applications
    if "open" in command:
        if "notepad" in command:
            if platform.system() == "Windows":
                subprocess.Popen(["notepad.exe"])
                if creativity > 0.7:
                    return "Notepad is now ready for your brilliant thoughts! Time to write something amazing!"
                elif creativity > 0.3:
                    return "Opening Notepad for you..."
                else:
                    return "Opening Notepad..."
            else:
                subprocess.Popen(["gedit"])
                return "Opening text editor..." if creativity <= 0.3 else "Text editor at your service!"
                
        elif "calculator" in command:
            if platform.system() == "Windows":
                subprocess.Popen(["calc.exe"])
                if creativity > 0.7:
                    return "Calculator is ready to crunch some numbers! Let's solve the mysteries of mathematics!"
                elif creativity > 0.3:
                    return "Opening Calculator for you..."
                else:
                    return "Opening Calculator..."
            else:
                subprocess.Popen(["gnome-calculator"])
                return "Opening Calculator..." if creativity <= 0.3 else "Calculator ready for action!"
                
        elif "browser" in command or "chrome" in command:
            webbrowser.open("https://www.google.com")
            if creativity > 0.7:
                return "Your digital gateway to the internet is now open! Happy browsing, explorer!"
            elif creativity > 0.3:
                return "Opening your web browser..."
            else:
                return "Opening web browser..."
                
        elif "file manager" in command or "explorer" in command:
            if platform.system() == "Windows":
                subprocess.Popen(["explorer.exe"])
                response = "Opening File Explorer..."
            else:
                subprocess.Popen(["nautilus"])
                response = "Opening File Manager..."
            
            if creativity > 0.7:
                return f"📁 {response.replace('...', '')} Time to organize those digital treasures!"
            elif creativity > 0.3:
                return f"📁 {response}"
            else:
                return response
    
    # Enhanced volume control (Windows only for now)
    elif "volume" in command and platform.system() == "Windows":
        if "up" in command:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]175)"])
            if creativity > 0.7:
                return "🔊 Volume boosted! Hope your ears are ready for this!"
            elif creativity > 0.3:
                return "🔊 Volume increased."
            else:
                return "Volume increased."
        elif "down" in command:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]174)"])
            if creativity > 0.7:
                return "🔉 Toned it down a notch! Your neighbors will thank you."
            elif creativity > 0.3:
                return "🔉 Volume decreased."
            else:
                return "Volume decreased."
        elif "mute" in command:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]173)"])
            if creativity > 0.7:
                return "🔇 Silence is golden! Volume has been muted/unmuted."
            elif creativity > 0.3:
                return "🔇 Volume muted/unmuted."
            else:
                return "Volume muted/unmuted."
    
    # Enhanced screenshot
    elif "screenshot" in command:
        try:
            if platform.system() == "Windows":
                subprocess.run(["powershell", "-c", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('%{PRTSC}')"])
                if creativity > 0.7:
                    return "📸 Say cheese! Screenshot captured and saved to your clipboard. Picture perfect!"
                elif creativity > 0.3:
                    return "📸 Screenshot taken and saved to clipboard."
                else:
                    return "Screenshot taken and saved to clipboard."
            else:
                subprocess.run(["gnome-screenshot", "-f", "screenshot.png"])
                if creativity > 0.7:
                    return "📸 Snapshot saved as screenshot.png! Another moment preserved in digital amber!"
                else:
                    return "Screenshot saved as screenshot.png"
        except:
            if creativity > 0.7:
                return "📸 Oops! My camera skills need some work. Screenshot failed to capture."
            else:
                return "Unable to take screenshot."
    
    return None

def call_ai_api(message, enable_search=None, enable_system_commands=None, search_results_limit=None, model_id=None):
    """Enhanced main AI API function with model selection support"""
    
    # Apply response delay from advanced settings
    delay = advanced_settings.get('response_delay', 0.1)
    if delay > 0:
        time.sleep(delay)
    
    # Use passed parameters or fall back to global settings
    search_enabled = enable_search if enable_search is not None else advanced_settings.get('enable_search', True)
    system_enabled = enable_system_commands if enable_system_commands is not None else advanced_settings.get('enable_system_commands', True)
    search_limit = search_results_limit or advanced_settings.get('search_results_limit', 3)
    current_model = model_id or advanced_settings.get('current_model', 'local_engine')
    
    print(f"[DEBUG] Current model from advanced_settings: {current_model}")
    
    original_message = message
    message_lower = message.lower().strip()
    
    # Handle direct model identification questions and personal identity questions
    model_questions = [
        "what model are you", "which model are you", "what ai model", "which ai model",
        "what model do you use", "which model do you use", "what are you using",
        "tell me your model", "identify your model", "current model"
    ]
    
    # Handle "who are you" type questions - these should show model info, not web search
    identity_questions = [
        "who are you", "what are you", "tell me about yourself", "introduce yourself",
        "who is luna", "what is luna"
    ]
    
    if any(question in message_lower for question in model_questions) or any(question in message_lower for question in identity_questions):
        # Get current model info
        available_models = get_available_models()
        current_model_info = available_models.get(current_model, available_models['local_engine'])
        model_name = current_model_info['name']
        model_type = current_model_info.get('type', 'unknown')
        description = current_model_info.get('description', 'No description available')
        
        if conversation_engine.creativity_level > 0.7:
            response = f"I'm currently running on {model_name}! It's a {model_type} model. {description} I'm ready to help you with whatever you need!"
        else:
            response = f"I am currently using {model_name}, which is a {model_type} model. {description}"
        
        return f"{response}\n\n[Using: {model_name}]"
    
    # Handle weather requests
    if "weather" in message_lower:
        city = "Beavercreek,Ohio"  # default
        if " in " in message_lower:
            city_part = message_lower.split(" in ")[1].strip()
            if city_part:
                city = city_part.replace(" ", ",")
        weather_response = get_weather(city)
        # Get model info for identification
        available_models = get_available_models()
        current_model_info = available_models.get(current_model, available_models['local_engine'])
        model_name = current_model_info['name']
        return f"{weather_response}\n\n[Using: {model_name}]"
    
    # Enhanced web search detection with advanced settings check
    if search_enabled:
        search_keywords = [
            "search", "look up", "find", "google", "what is", "who is", "when is", "where is", 
            "tell me about", "information about", "search for", "find out", "lookup",
            "nfl", "football", "sports", "baseball", "basketball", "soccer", "hockey",
            "news", "latest", "recent", "current", "today", "update", "score", "game",
            "how to", "tutorial", "guide", "learn", "explain", "define", "meaning of"
        ]
        
        # Check if message contains search keywords
        is_search_query = False
        search_query = message_lower
        
        for keyword in search_keywords:
            if keyword in message_lower:
                is_search_query = True
                if keyword in ["search for", "search", "look up", "find", "google"]:
                    parts = message_lower.split(keyword, 1)
                    if len(parts) > 1 and parts[1].strip():
                        search_query = parts[1].strip()
                elif keyword in ["what is", "who is", "when is", "where is", "tell me about", "information about"]:
                    parts = message_lower.split(keyword, 1)
                    if len(parts) > 1 and parts[1].strip():
                        search_query = parts[1].strip()
                break
        
        # Enhanced question patterns detection
        question_patterns = [
            r"what.+(?:is|are|was|were|will be|does|do|did)",
            r"who.+(?:is|are|was|were|will be)",
            r"when.+(?:is|are|was|were|will be|did|does|do)",
            r"where.+(?:is|are|was|were|will be)",
            r"how.+(?:is|are|was|were|will be|do|does|did|to)",
            r"why.+(?:is|are|was|were|will be|do|does|did)",
            r"(?:nfl|football|sports|baseball|basketball).+(?:score|game|news|update|today|latest)"
        ]
        
        for pattern in question_patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                is_search_query = True
                break
        
        # Special handling for sports queries
        sports_terms = ["nfl", "football", "baseball", "basketball", "soccer", "hockey", "sports"]
        if any(term in message_lower for term in sports_terms):
            is_search_query = True
            if "search the nfl" in message_lower:
                search_query = "NFL news today latest scores"
            elif "nfl" in message_lower and not any(word in message_lower for word in ["score", "news", "game", "today"]):
                search_query = f"NFL {message_lower.replace('nfl', '').strip()} latest news"
        
        # Perform enhanced web search if detected
        if is_search_query:
            search_query = search_query.lstrip("about for the").strip()
            if search_query and len(search_query) > 2:
                print(f"Performing web search for: {search_query}")
                search_response = enhanced_web_search(search_query, search_limit)
                # Get model info for identification
                available_models = get_available_models()
                current_model_info = available_models.get(current_model, available_models['local_engine'])
                model_name = current_model_info['name']
                return f"{search_response}\n\n[Using: {model_name}]"
    else:
        # Search disabled message
        search_disabled_keywords = ["search", "google", "find", "look up"]
        if any(keyword in message_lower for keyword in search_disabled_keywords):
            # Get model info for identification
            available_models = get_available_models()
            current_model_info = available_models.get(current_model, available_models['local_engine'])
            model_name = current_model_info['name']
            if conversation_engine.creativity_level > 0.7:
                return f"Web search is currently taking a digital vacation! You can re-enable it in the advanced settings if you'd like to explore the internet together.\n\n[Using: {model_name}]"
            else:
                return f"Web search is currently disabled. You can enable it in the advanced settings.\n\n[Using: {model_name}]"
    
    # Handle system commands with advanced settings check
    if system_enabled:
        system_result = execute_system_command(message_lower)
        if system_result:
            # Get model info for identification
            available_models = get_available_models()
            current_model_info = available_models.get(current_model, available_models['local_engine'])
            model_name = current_model_info['name']
            return f"{system_result}\n\n[Using: {model_name}]"
    else:
        # If system commands are disabled but the user clearly asked for one,
        # return an explicit disabled message instead of doing nothing.
        system_disabled_keywords = [
            "open ", "volume", "screenshot", "notepad", "calculator",
            "browser", "chrome", "explorer", "file manager"
        ]
        if any(term in message_lower for term in system_disabled_keywords):
            available_models = get_available_models()
            current_model_info = available_models.get(current_model, available_models['local_engine'])
            model_name = current_model_info['name']
            if conversation_engine.creativity_level > 0.7:
                msg = "System commands are currently disabled for safety. You can re-enable them in the advanced settings if you want me to control apps or volume."
            else:
                msg = "System commands are disabled. You can enable them in the advanced settings."
            return f"{msg}\n\n[Using: {model_name}]"
    
    # Get current model info for identification
    available_models = get_available_models()
    current_model_info = available_models.get(current_model, available_models['local_engine'])
    model_name = current_model_info['name']
    
    # Try to get response from the active model
    try:
        if current_model_info.get('type') == 'openrouter':
            # Use OpenRouter model with configurable retry attempts
            attempts = 2  # default: initial try + one retry for transient failures
            try:
                if settings_manager is not None:
                    cfg_attempts = int(settings_manager.get('retry_attempts', 2))
                    # Guardrail: minimum 1 attempt
                    if cfg_attempts and cfg_attempts > 0:
                        attempts = cfg_attempts
            except Exception:
                pass
            did_reload_token = False
            last_err = None
            
            # Determine which API to use based on provider
            available_models = get_available_models()
            model_info = available_models.get(current_model, {})
            provider = model_info.get('provider', 'openrouter')
            
            for attempt in range(attempts):
                try:
                    if attempt > 0:
                        time.sleep(2 * attempt)
                    print(f"Using {current_model} for response... (attempt {attempt+1}/{attempts})")
                    
                    # Route to appropriate API based on provider
                    if provider == 'openrouter':
                        response = openrouter_api.query_model(current_model, original_message)
                    else:  # Default to OpenRouter
                        response = openrouter_api.query_model(current_model, original_message)

                    # If we got a completely empty/whitespace response, treat it as an error
                    # so we don't render a blank Luna bubble. Use a generic exception so the
                    # existing error handler path is reused.
                    if not str(response).strip():
                        raise Exception("Empty response from OpenRouter model")

                    # Clear any previous errors if successful
                    if settings_manager is not None:
                        settings_manager.clear_model_error(current_model)
                    return f"{response}\n\n[Using: {model_name}]"
                except Exception as e:
                    last_err = str(e)
                    print(f"OpenRouter API Error: {last_err}")
                    # Record error each time
                    try:
                        settings_manager.set_model_error(current_model, last_err)
                    except Exception:
                        pass
                    lower = last_err.lower()
                    # One-time auth recovery: try reloading token from .env on 401/403/auth errors
                    auth_error = ("authentication" in lower) or ("authorization" in lower) or ("401" in lower) or ("403" in lower)
                    if auth_error and not did_reload_token:
                        try:
                            if reload_openrouter_token_from_env():
                                did_reload_token = True
                                print("Reloaded OpenRouter token from .env after auth error; retrying...")
                                continue
                        except Exception:
                            pass
                    transient = ("paused" in lower) or ("loading" in lower) or ("rate limit" in lower) or ("429" in lower)
                    # If not transient or no more retries, break to fallback
                    if not transient:
                        break
                    # Otherwise loop for retry (if attempts remain)
                    continue
            # Before local fallback, attempt alternate OpenRouter models based on advanced recovery settings
            try:
                lower = (last_err or "").lower()
                auto_fb = True
                cap = 3
                ignore_pings = False
                priority_raw = ""
                try:
                    def _to_bool(v, default=False):
                        if v is None:
                            return default
                        if isinstance(v, bool):
                            return v
                        try:
                            s = str(v).strip().lower()
                            if s in ("1", "true", "yes", "on"):
                                return True
                            if s in ("0", "false", "no", "off"):
                                return False
                        except Exception:
                            pass
                        return bool(v)
                    if settings_manager is not None:
                        auto_fb = _to_bool(settings_manager.get('auto_fallback', True), True)
                        cap = int(settings_manager.get('alt_attempt_cap', 3))
                        ignore_pings = _to_bool(settings_manager.get('ignore_status_pings', False), False)
                        priority_raw = settings_manager.get('alternate_priority', '') or ''
                except Exception:
                    pass

                # Decide if we proceed to alternates
                proceed_to_alts = ("paused" in lower) or ("loading" in lower)
                if ignore_pings:
                    proceed_to_alts = True

                if auto_fb and cap > 0 and proceed_to_alts:
                    alt_models = []
                    try:
                        # Build list of other OpenRouter models defined in the same set the UI shows
                        ui_models = _get_ui_available_models()
                        for mid, info in ui_models.items():
                            # Only include OpenRouter type models for OR API fallback
                            if mid != current_model and info.get('type') == 'openrouter' and info.get('provider') == 'openrouter':
                                alt_models.append((mid, info))
                        # Apply priority ordering if provided
                        priority = [p.strip() for p in priority_raw.split(',') if p.strip()]
                        if priority:
                            pr_index = {mid: i for i, mid in enumerate(priority)}
                            alt_models.sort(key=lambda t: pr_index.get(t[0], len(priority)))
                    except Exception:
                        pass

                    tried = 0
                    for (alt_id, alt_info) in alt_models:
                        if tried >= cap:
                            break
                        try:
                            err_summary = (last_err.splitlines()[0] if last_err else 'unknown')
                            print(f"Trying alternate HF model '{alt_id}' due to error: {err_summary}")
                            alt_resp = hf_api.query_model(alt_id, original_message)
                            # Success: auto-switch for continuity
                            try:
                                if settings_manager is not None:
                                    settings_manager.set('current_ai_model', alt_id)
                                update_advanced_settings({'current_model': alt_id})
                            except Exception:
                                pass
                            alt_name = alt_info.get('name', alt_id)
                            return f"{alt_resp}\n\n[Using: {alt_name} (Auto-switched)]"
                        except HFRequestError as alt_e:
                            # 404 means the model isn't available via Inference API; skip without consuming an attempt
                            if getattr(alt_e, 'status_code', None) == 404:
                                print(f"Skipping alternate '{alt_id}' (404 Inference API not available): {alt_e}")
                                continue
                            print(f"Alternate HF model failed: {alt_e}")
                            tried += 1
                            continue
                        except Exception as alt_e:
                            print(f"Alternate HF model failed (unknown): {alt_e}")
                            tried += 1
                            continue

                    # If we haven't reached the cap, try UI/ENV candidates directly to fill remaining attempts
                    if tried < cap:
                        direct_list = []
                        # Start with ENV, but only include those present in the UI-available set
                        env_alts = _get_env_alt_models()
                        ui_models = _get_ui_available_models()
                        if env_alts:
                            for alt in env_alts:
                                if alt != current_model and alt in ui_models and ui_models[alt].get('type') == 'openrouter' and ui_models[alt].get('provider') == 'openrouter':
                                    direct_list.append(alt)
                        # If still empty, use other UI-declared HF models (excluding current)
                        if not direct_list:
                            direct_list = [mid for mid, info in ui_models.items() 
                                        if mid != current_model 
                                        and info.get('type') == 'openrouter' 
                                        and info.get('provider') == 'openrouter']
                        # Apply priority ordering if provided
                        priority = [p.strip() for p in priority_raw.split(',') if p.strip()]
                        if priority:
                            direct_list.sort(key=lambda mid: priority.index(mid) if mid in priority else len(priority))
                        for alt_id in direct_list:
                            if alt_id == current_model or tried >= cap:
                                continue
                            try:
                                print(f"Trying alternate OpenRouter model '{alt_id}' (direct)...")
                                alt_resp = openrouter_api.query_model(alt_id, original_message)
                                # Success: auto-switch for continuity
                                try:
                                    if settings_manager is not None:
                                        settings_manager.set('current_ai_model', alt_id)
                                    update_advanced_settings({'current_model': alt_id})
                                except Exception:
                                    pass
                                alt_name = ui_models.get(alt_id, {}).get('name', alt_id)
                                return f"{alt_resp}\n\n[Using: {alt_name} (Auto-switched)]"
                            except OpenRouterRequestError as alt_e:
                                if getattr(alt_e, 'status_code', None) == 404:
                                    print(f"Skipping alternate '{alt_id}' (404 Inference API not available): {alt_e}")
                                    continue
                                print(f"Alternate OpenRouter model failed (direct): {alt_e}")
                                tried += 1
                                continue
                            except Exception as alt_e:
                                print(f"Alternate OpenRouter model failed (direct, unknown): {alt_e}")
                                tried += 1
                                continue

                        # Note: No curated alternates; alternates strictly follow the UI list to keep backend and UI in sync.
            except Exception:
                pass

            # Fallback to local model with error context
            print(f"Falling back to local conversation engine...")
            fallback_msg = "OpenRouter model error: " + (last_err.split('\n')[0] if last_err else 'unknown error')
            fallback_response = conversation_engine.generate_response(
                f"[SYSTEM: {fallback_msg}] {original_message}"
            )
            return f"{fallback_response}\n\n[Using: Local Conversation Engine (Fallback)]"
        else:  # Local model
            response = conversation_engine.generate_response(original_message)
            # Clear any previous errors for local engine
            if settings_manager is not None:
                settings_manager.clear_model_error(current_model)
            return f"{response}\n\n[Using: {model_name}]"
    except Exception as e:
        print(f"Unexpected error in call_ai_api: {e}")
        # Fallback response when all else fails
        return f"I'm having trouble connecting to any AI models right now. Please try again later.\n\n[Using: {model_name}]"

def get_available_models():
    """Return a dictionary of available AI models and their configurations."""
    
    # Check API keys
    hf_token = os.getenv('HF_API_TOKEN')
    or_key = os.getenv('OPENROUTER_API_KEY')
    
    return {
        # Local Engine
        "local_engine": {
            "name": "Local Conversation Engine",
            "type": "local",
            "provider": "local",
            "description": "Fast local responses with advanced pattern matching and creativity controls",
            "features": ["instant_response", "offline", "privacy", "creativity_control", "weather_integration", "web_search", "system_commands"],
            "status": "active"
        },
        "local/mistral-7b-instruct": {
            "name": "Mistral 7B",
            "type": "local",
            "provider": "local",
            "description": "Local 7B parameter model with excellent performance, runs entirely on your hardware",
            "features": ["conversation", "reasoning", "instruction_following", "code_generation", "offline", "privacy"],
            "status": "not_downloaded",
            "download_command": "ollama pull mistral"
        },
        "local/llama-3.1-8b-instruct": {
            "name": "Llama 3.1 8B",
            "type": "local",
            "provider": "local",
            "description": "Latest local 8B model with strong reasoning capabilities, runs entirely on your hardware",
            "features": ["reasoning", "conversation", "instruction_following", "knowledge_retrieval", "offline", "privacy"],
            "status": "not_downloaded",
            "download_command": "ollama pull llama3.1"
        },
        "local/qwen-2.5-7b-instruct": {
            "name": "Qwen 2.5 7B",
            "type": "local",
            "provider": "local",
            "description": "Local 7B model with strong multilingual capabilities, runs entirely on your hardware",
            "features": ["multilingual", "conversation", "reasoning", "instruction_following", "offline", "privacy"],
            "status": "not_downloaded",
            "download_command": "ollama pull qwen2.5:7b"
        },
        "local/deepseek-coder-6.7b": {
            "name": "DeepSeek Coder 6.7B",
            "type": "local",
            "provider": "local",
            "description": "Local 6.7B model optimized for coding and programming tasks, runs entirely on your hardware",
            "features": ["code_generation", "programming_assistance", "debugging", "offline", "privacy"],
            "status": "not_downloaded",
            "download_command": "ollama pull deepseek-coder:6.7b"
        },
        
        # OpenRouter Free Models
        "deepseek/deepseek-r1-0528:free": {
            "name": "DeepSeek R1",
            "type": "openrouter",
            "provider": "openrouter",
            "description": "DeepSeek's latest conversational model optimized for chat interactions and instruction following",
            "features": ["conversation", "instruction_following", "reasoning", "multilingual"],
            "status": "available"
        },
        "openai/gpt-oss-20b:free": {
            "name": "OpenAI GPT-OSS 20B",
            "type": "openrouter",
            "provider": "openrouter",
            "description": "Open-source 20B parameter language model based on GPT architecture with strong general-purpose capabilities",
            "features": ["conversation", "reasoning", "code_generation", "knowledge_retrieval", "multilingual"],
            "status": "available"
        },
        "openai/gpt-oss-120b:free": {
            "name": "OpenAI GPT-OSS 120B",
            "type": "openrouter",
            "provider": "openrouter",
            "description": "Larger GPT-OSS 120B parameter model for more demanding reasoning and generation tasks",
            "features": ["conversation", "reasoning", "code_generation", "knowledge_retrieval", "multilingual"],
            "status": "available"
        }
    }

def set_current_model(model_id: str):
    """Set the current AI model"""
    global advanced_settings
    available_models = get_available_models()
    
    # Normalize some known legacy IDs to current OpenRouter slugs
    legacy_map = {
        "deepseek/deepseek-chat-v3-0324:free": "deepseek/deepseek-r1-0528:free",
        "nex-agi/deepseek-v3.1-nex-n1:free": "deepseek/deepseek-r1-0528:free",
    }
    if model_id in legacy_map:
        model_id = legacy_map[model_id]

    # Direct match first
    if model_id in available_models:
        advanced_settings['current_model'] = model_id
        print(f"[OK] Current AI model set to {available_models[model_id]['name']}")
        print(f"[DEBUG] Advanced settings current_model is now: {advanced_settings['current_model']}")
        return True
    
    # Try to normalize and map friendly/alias IDs to known keys
    def _norm(s: str) -> str:
        return ''.join(ch for ch in s.lower() if ch.isalnum())
    target = _norm(model_id)
    candidates = []
    for key, info in available_models.items():
        norm_key = _norm(key)
        norm_name = _norm(info.get('name', key))
        if target == norm_key or target == norm_name or target.endswith(norm_key.split('/')[-1] if '/' in key else norm_key):
            candidates.append(key)
    if len(candidates) == 1:
        mapped = candidates[0]
        advanced_settings['current_model'] = mapped
        print(f"[OK] Remapped '{model_id}' to '{mapped}' -> {available_models[mapped]['name']}")
        print(f"[DEBUG] Advanced settings current_model is now: {advanced_settings['current_model']}")
        return True
    elif len(candidates) > 1:
        print(f"[WARN] Ambiguous model alias '{model_id}'. Candidates: {candidates}. Using first: {candidates[0]}")
        mapped = candidates[0]
        advanced_settings['current_model'] = mapped
        print(f"[OK] Current AI model set to {available_models[mapped]['name']}")
        print(f"[DEBUG] Advanced settings current_model is now: {advanced_settings['current_model']}")
        return True
    else:
        print(f"Model '{model_id}' not found in available models (no alias match)")
        return False

def get_current_model_info():
    """Get information about the currently selected model"""
    current_model = advanced_settings.get('current_model', 'local_engine')
    available_models = get_available_models()
    return available_models.get(current_model, available_models['local_engine'])