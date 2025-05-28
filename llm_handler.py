# llm_handler.py
# This file handles interactions with the LLM (Google Gemini) using a class structure.

import os
import google.generativeai as genai
from dotenv import load_dotenv

class LLMHandler:
    _is_configured = False 

    def __init__(self, model_name: str = "gemini-1.5-flash-latest", api_key: str | None = None):
        self.model_name = model_name
        self.model = None 

        if not LLMHandler._is_configured:
            current_api_key = api_key
            if not current_api_key:
                # Standardize to GEMINI_API_KEY from .env first for consistency
                load_dotenv() # Ensure .env is loaded if called from anywhere
                current_api_key = os.getenv("GEMINI_API_KEY")
                
            if not current_api_key: # Fallback to GOOGLE_API_KEY if GEMINI_API_KEY isn't found
                current_api_key = os.getenv("GOOGLE_API_KEY") # For V1.0 config_loader style if it set env var

            if not current_api_key: # Fallback to trying config_loader directly
                try:
                    from config_loader import get_api_key as cl_get_api_key
                    current_api_key = cl_get_api_key('GEMINI_API_KEY') # Prefer GEMINI_API_KEY
                    if not current_api_key:
                         current_api_key = cl_get_api_key('GOOGLE_API_KEY') # Then try GOOGLE_API_KEY
                    print("LLMHandler Info: API key loaded via config_loader.")
                except ImportError:
                    # print("LLMHandler Warning: config_loader not found or failed to load key.")
                    pass # Pass silently if config_loader isn't there or fails

            if current_api_key:
                self._configure_with_key(current_api_key)
            else:
                print("LLMHandler Error: API key not provided and not found. LLM will not be configured.")
        
        if LLMHandler._is_configured:
            try:
                self.model = genai.GenerativeModel(self.model_name)
                if self.model:
                    # print(f"LLMHandler: Model '{self.model_name}' initialized successfully for this instance.")
                    pass
            except Exception as e:
                print(f"LLMHandler Error: Failed to initialize model '{self.model_name}' after configuration: {e}")
                self.model = None

    def _configure_with_key(self, api_key: str) -> bool:
        if LLMHandler._is_configured:
            return True
        # print("LLMHandler: Attempting to configure Gemini globally...")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                print("LLMHandler Info: Gemini configured successfully globally.")
                LLMHandler._is_configured = True
                return True
            except Exception as e:
                print(f"LLMHandler Error: Error configuring Gemini: {e}")
                LLMHandler._is_configured = False; return False
        else:
            print("LLMHandler Error: Configuration failed - API Key was not provided.")
            LLMHandler._is_configured = False; return False

    def generate_text(self, prompt: str) -> str | None:
        if not LLMHandler._is_configured: print("LLMHandler Error: LLM not configured globally."); return None
        if not self.model: print(f"LLMHandler Error: Model '{self.model_name}' not initialized."); return None
        try:
            response = self.model.generate_content(prompt)
            if response and hasattr(response, 'text') and response.text: return response.text
            elif response and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                print(f"LLMHandler Error: Blocked. Reason: {response.prompt_feedback.block_reason}"); return None
            else: print("LLMHandler Error: Empty/unexpected response."); return None
        except Exception as e: print(f"LLMHandler Error during generation: {e}"); return None

    @staticmethod
    def is_configured() -> bool: return LLMHandler._is_configured

if __name__ == "__main__":
    print("\nRunning llm_handler.py directly for testing...")
    load_dotenv() 
    
    # Explicitly fetch API key for the test setup messages
    api_key_for_test_message = os.getenv("GEMINI_API_KEY")
    if not api_key_for_test_message:
        api_key_for_test_message = os.getenv("GOOGLE_API_KEY") # Check V1.0 name

    if api_key_for_test_message:
        print(f"API key (GEMINI_API_KEY or GOOGLE_API_KEY) found in .env for llm_handler.py direct test.")
    else:
        print("Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in .env for direct test message, but constructor will try fallbacks.")

    print("\nTest 1: Initializing LLMHandler (gemini-1.5-flash-latest)...")
    # Let constructor handle API key loading logic internally
    handler_instance1 = LLMHandler(model_name="gemini-1.5-flash-latest") 
    
    if handler_instance1.is_configured() and handler_instance1.model:
        print("-" * 20)
        sample_prompt = "What is the capital of France?"
        print(f"Sending sample prompt to handler_instance1 ({handler_instance1.model_name}):\n\"{sample_prompt}\"")
        generated_content = handler_instance1.generate_text(prompt=sample_prompt)
        print("-" * 20)
        if generated_content: print(f"\nGenerated Response:\n{generated_content}")
        else: print("\nFailed to generate response from handler_instance1.")
    else:
        print("\nSkipping Test 1 generation due to configuration/model init failure.")

    print("\nTest 2: Initializing another LLMHandler instance (gemini-1.5-pro-latest)...")
    # Use another known working model for the second instance test
    handler_instance2 = LLMHandler(model_name="gemini-1.5-pro-latest") 
    if handler_instance2.is_configured() and handler_instance2.model:
        print("-" * 20)
        sample_prompt_2 = "Briefly explain what a stock market is."
        print(f"Sending sample prompt to handler_instance2 ({handler_instance2.model_name}):\n\"{sample_prompt_2}\"")
        generated_content_2 = handler_instance2.generate_text(prompt=sample_prompt_2)
        print("-" * 20)
        if generated_content_2: print(f"\nGenerated Response:\n{generated_content_2}")
        else: print("\nFailed to generate response from handler_instance2.")
    else:
        print("\nSkipping Test 2 generation due to configuration/model init failure.")