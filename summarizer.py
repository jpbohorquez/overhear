import os
import logging
import toml
import threading
import litellm
from typing import Optional, List, Dict
from datetime import datetime

# Silence a known litellm bug where TranscriptionCreateParams.__annotations__
# raises AttributeError during internal logging, flooding stderr with noise.
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
litellm.suppress_debug_info = True

class Summarizer:
    """
    Handles meeting transcript summarization using LiteLLM for provider agnosticism.
    Supports Gemini, OpenAI, Anthropic, Ollama, etc.
    Uses .secrets.toml for key management.
    """
    def __init__(self, config_path="config.toml", secrets_path=".secrets.toml"):
        self.config_path = config_path
        self.secrets_path = secrets_path
        self.load_config()
        self._load_secrets()

    def load_config(self):
        if os.path.exists(self.config_path):
            config = toml.load(self.config_path)
            sum_cfg = config.get("summarization", {})
            self.model_name = sum_cfg.get("model_name", "gemini/gemini-1.5-flash")
            self.system_prompt = sum_cfg.get("system_prompt", "Summarize this meeting transcript.")
            self.summaries_dir = sum_cfg.get("summaries_dir", "summaries")
            
            trans_cfg = config.get("transcription", {})
            self.transcriptions_dir = trans_cfg.get("output_dir", "transcriptions")
            self.model_size = trans_cfg.get("model_size", "base")
            
            audio_cfg = config.get("audio", {})
            self.sample_rate = audio_cfg.get("sample_rate", 16000)
            self.chunk_duration = audio_cfg.get("chunk_duration", 30)
        else:
            self.model_name = "gemini/gemini-1.5-flash"
            self.system_prompt = "Summarize this meeting transcript."
            self.summaries_dir = "summaries"
            self.transcriptions_dir = "transcriptions"
            self.model_size = "base"
            self.sample_rate = 16000
            self.chunk_duration = 30

        os.makedirs(self.summaries_dir, exist_ok=True)

    def reload_config(self):
        """Reloads configuration from disk."""
        self.load_config()

    def save_config(self, transcription_settings: Dict, audio_settings: Dict, summarization_settings: Dict):
        """Persists all settings to config.toml."""
        config = {}
        if os.path.exists(self.config_path):
            try:
                config = toml.load(self.config_path)
            except:
                pass
        
        config.setdefault("transcription", {}).update(transcription_settings)
        config.setdefault("audio", {}).update(audio_settings)
        config.setdefault("summarization", {}).update(summarization_settings)

        # Ensure directories exist
        os.makedirs(config["transcription"].get("output_dir", "transcriptions"), exist_ok=True)
        os.makedirs(config["summarization"].get("summaries_dir", "summaries"), exist_ok=True)

        with open(self.config_path, "w") as f:
            toml.dump(config, f)
        
        # Refresh current instance
        self.load_config()

    def _load_secrets(self):
        """Loads .secrets.toml keys into environment variables for LiteLLM."""
        if os.path.exists(self.secrets_path):
            try:
                secrets = toml.load(self.secrets_path)
                # LiteLLM looks for environment variables like GEMINI_API_KEY, OPENAI_API_KEY
                for key, value in secrets.items():
                    if key.endswith("_API_KEY"):
                        os.environ[key.upper()] = value
            except Exception as e:
                print(f"Error loading secrets: {e}")

    def save_api_key(self, provider_prefix: str, api_key: str):
        """
        Saves API key to .secrets.toml.
        Example: provider_prefix='GEMINI' -> saves 'GEMINI_API_KEY = "..."'
        """
        key_name = f"{provider_prefix.upper()}_API_KEY"
        secrets = {}
        if os.path.exists(self.secrets_path):
            try:
                secrets = toml.load(self.secrets_path)
            except:
                pass
        
        secrets[key_name] = api_key
        with open(self.secrets_path, "w") as f:
            toml.dump(secrets, f)
        
        # Set it in current session too
        os.environ[key_name] = api_key

    def get_api_key(self, provider_prefix: str) -> str:
        """Retrieves key from environment or secrets file."""
        key_name = f"{provider_prefix.upper()}_API_KEY"
        val = os.environ.get(key_name, "")
        if not val and os.path.exists(self.secrets_path):
            try:
                secrets = toml.load(self.secrets_path)
                val = secrets.get(key_name, "")
            except:
                pass
        return val

    def fetch_live_models(self, provider: str, api_key: str) -> List[str]:
        """Fetch models actually available for the given provider and API key."""
        import requests
        provider = provider.upper()

        if provider == "GEMINI":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")          # "models/gemini-2.5-flash"
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    short = name.removeprefix("models/")
                    models.append(f"gemini/{short}")
            return sorted(models)

        elif provider == "OPENAI":
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            chat_prefixes = ("gpt-4", "gpt-3.5", "o1", "o3", "o4")
            models = [
                f"openai/{m['id']}" for m in data.get("data", [])
                if any(m["id"].startswith(p) for p in chat_prefixes)
            ]
            return sorted(models)

        elif provider == "ANTHROPIC":
            url = "https://api.anthropic.com/v1/models"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            models = [f"anthropic/{m['id']}" for m in data.get("data", [])]
            return sorted(models)

        return []

    def get_available_models(self, provider_prefix: str) -> List[str]:
        """Dynamically fetch models for a given provider using LiteLLM."""
        try:
            # provider_prefix is expected to be 'gemini', 'openai', etc.
            provider_models = litellm.models_by_provider.get(provider_prefix.lower(), [])
            
            # For Gemini, LiteLLM usually expects gemini/model_name
            formatted_models = []
            for m in provider_models:
                # Add the provider prefix if it's not already there
                if not m.startswith(f"{provider_prefix.lower()}/"):
                    formatted_models.append(f"{provider_prefix.lower()}/{m}")
                else:
                    formatted_models.append(m)
            
            # If nothing found, provide some defaults as fallback
            if not formatted_models:
                defaults = {
                    "gemini": ["gemini/gemini-1.5-flash", "gemini/gemini-1.5-pro"],
                    "openai": ["openai/gpt-4o", "openai/gpt-4o-mini"],
                    "anthropic": ["anthropic/claude-3-5-sonnet-20240620"]
                }
                return defaults.get(provider_prefix.lower(), [])
                
            return formatted_models
        except Exception as e:
            print(f"Error fetching models: {e}")
            return []

    def summarize(self, transcript_path: str, custom_prompt: Optional[str] = None, callback=None):
        """Runs summarization in a background thread."""
        thread = threading.Thread(
            target=self._summarize_worker, 
            args=(transcript_path, custom_prompt, callback),
            daemon=True
        )
        thread.start()

    def _summarize_worker(self, transcript_path: str, custom_prompt: str, callback):
        try:
            # Read transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Prepare Messages (Standard OpenAI-style format used by LiteLLM)
            prompt = custom_prompt if custom_prompt else self.system_prompt
            TRANSCRIPT_PLACEHOLDER = "$transcript$"
            if TRANSCRIPT_PLACEHOLDER in prompt:
                # Inline the transcript where the prompt tells us to put it
                messages = [
                    {"role": "user", "content": prompt.replace(TRANSCRIPT_PLACEHOLDER, content)}
                ]
            else:
                # No placeholder: use system + user message format
                messages = [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Please summarize the following meeting transcript:\n\n{content}"}
                ]

            # LiteLLM completion (Latest syntax)
            response = litellm.completion(
                model=self.model_name,
                messages=messages
            )
            
            summary_text = response.choices[0].message.content

            # Save File
            base_name = os.path.basename(transcript_path)
            summary_path = os.path.join(self.summaries_dir, f"Summary_{base_name}")
            
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# Summary of {base_name}\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(summary_text)

            if callback:
                callback(True, summary_path)

        except Exception as e:
            if callback:
                callback(False, str(e))

    def get_latest_transcript(self) -> Optional[str]:
        if not os.path.exists(self.transcriptions_dir):
            return None
        all_files = []
        for root, _, files in os.walk(self.transcriptions_dir):
            for f in files:
                if f.endswith(".md"):
                    p = os.path.join(root, f)
                    all_files.append((p, os.path.getmtime(p)))
        if not all_files: return None
        all_files.sort(key=lambda x: x[1], reverse=True)
        return all_files[0][0]
