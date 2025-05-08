# This file handles interactions with the LLM (Google Gemini).

import google.generativeai as genai
import sys # To check if config_loader was imported correctly

# Attempt to import the function from the config_loader module we created
try:
    from config_loader import get_api_key
except ImportError:
    print("Error: Could not import 'get_api_key' from config_loader.")
    print("Ensure 'config_loader.py' exists in the same directory and the cell creating it was run.")
    # Define a dummy function to prevent NameError later, but it won't work
    def get_api_key(key_name: str) -> None:
        print("Error: get_api_key function is not available due to import failure.")
        return None

# Global variable to track configuration status
_is_configured = False

def configure_llm() -> bool:
    """
    Configures the Google Generative AI client using the API key
    retrieved from Colab Secrets via config_loader.

    Returns:
        True if configuration is successful, False otherwise.
    """
    global _is_configured
    if _is_configured:
        print("Gemini is already configured.")
        return True

    print("Attempting to configure Gemini...")
    api_key = get_api_key('GOOGLE_API_KEY')

    if api_key:
        try:
            genai.configure(api_key=api_key)
            print("Gemini configured successfully.")
            _is_configured = True
            return True
        except Exception as e:
            print(f"Error configuring Gemini: {e}")
            _is_configured = False
            return False
    else:
        print("Configuration failed: API Key 'GOOGLE_API_KEY' not found or retrieval failed.")
        _is_configured = False
        return False

def generate_text(prompt: str, model_name: str = "gemini-1.5-flash") -> str | None:
    """
    Generates text content using the specified Google Gemini model.

    Assumes that configure_llm() has been successfully called beforehand.

    Args:
        prompt: The text prompt to send to the model.
        model_name: The name of the Gemini model to use
                    (e.g., "gemini-1.5-flash", "gemini-1.0-pro").

    Returns:
        The generated text content as a string, or None if generation fails
        or if the LLM is not configured.
    """
    global _is_configured
    if not _is_configured:
        print("Error: LLM is not configured. Please call configure_llm() first.")
        return None

    print(f"\nAttempting to generate text using model: {model_name}...")
    try:
        # Initialize the model (consider generation config for advanced control)
        model = genai.GenerativeModel(model_name)

        # Generate content
        response = model.generate_content(prompt)

        # Extract and return the text
        if response and response.text:
             print("Text generation successful.")
             return response.text
        elif response and hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
             print(f"Text generation blocked. Reason: {response.prompt_feedback.block_reason}")
             print(f"Safety Ratings: {response.prompt_feedback.safety_ratings}")
             return None
        else:
            print("Text generation failed: Received an empty or unexpected response.")
            # print("Full Response:", response) # Uncomment for debugging
            return None

    except Exception as e:
        print(f"An error occurred during text generation: {e}")
        return None

# Example Usage (only runs when the script is executed directly)
if __name__ == "__main__":
    print("\nRunning llm_handler directly for testing...")

    # 1. Configure the LLM
    config_success = configure_llm()

    # 2. If configuration is successful, try generating text
    if config_success:
        print("-" * 20)
        sample_prompt = "Explain the concept of Price-to-Earnings (P/E) ratio in simple terms for a beginner investor."
        print(f"Sending sample prompt:\n\"{sample_prompt}\"")

        generated_content = generate_text(prompt=sample_prompt, model_name="gemini-1.5-flash") # Or "gemini-1.0-pro"

        print("-" * 20)
        if generated_content:
            print("\nGenerated Response:")
            print(generated_content)
        else:
            print("\nFailed to generate response for the sample prompt.")
    else:
        print("\nSkipping text generation test due to configuration failure.")
