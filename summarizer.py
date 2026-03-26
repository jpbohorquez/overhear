import os
import toml
import threading
import litellm
from typing import Optional, List, Dict
from datetime import datetime

class Summarizer:
    """
    Handles meeting transcript summarization using LiteLLM for provider agnosticism.
    Supports Gemini, OpenAI, Anthropic, Ollama, etc.
    Uses .secrets.toml for key management.
    """
    def __init__(self, config_path="config.toml", secrets_path=".secrets.toml"):
        self.config_path = config_path
        self.secrets_path = secrets_path
        self._load_config()
        self._load_secrets()

    def _load_config(self):
        if os.path.exists(self.config_path):
            config = toml.load(self.config_path)
            sum_cfg = config.get("summarization", {})
            self.model_name = sum_cfg.get("model_name", "gemini/gemini-1.5-flash")
            self.system_prompt = sum_cfg.get("system_prompt", "Summarize this meeting transcript.")
            self.summaries_dir = sum_cfg.get("summaries_dir", "summaries")
            self.transcriptions_dir = config.get("transcription", {}).get("output_dir", "transcriptions")
        else:
            self.model_name = "gemini/gemini-1.5-flash"
            self.system_prompt = "Summarize this meeting transcript."
            self.summaries_dir = "summaries"
            self.transcriptions_dir = "transcriptions"

        os.makedirs(self.summaries_dir, exist_ok=True)

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
