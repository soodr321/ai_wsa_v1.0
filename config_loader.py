# config_loader.py (Modified for Streamlit/Cloud Shell)
import os
import streamlit as st
# Import load_dotenv, but note that load_dotenv() should be called
# early in your main app.py, not here.
# from dotenv import load_dotenv

def get_api_key(key_name: str) -> str | None:
    """
    Retrieves a secret value, checking Streamlit secrets first,
    then environment variables. Assumes dotenv.load_dotenv() is called
    in the main application script (e.g., app.py) for local/Cloud Shell development.

    Args:
        key_name: The name of the secret key to retrieve (e.g., 'GOOGLE_API_KEY').

    Returns:
        The secret value as a string if found, otherwise None.
        Prints an error message if the key is not found.
    """
    key_value = None

    # 1. Try to get the key from Streamlit secrets (for deployed app)
    try:
        # Check if running in a Streamlit environment and st.secrets is available
        if hasattr(st, 'secrets') and key_name in st.secrets:
            key_value = st.secrets[key_name]
            # print(f"[*] Config: Found key '{key_name}' in st.secrets.") # Optional debug
            return key_value
    except Exception:
        # This might happen if 'st' is not fully initialized or 'secrets' isn't there.
        # Pass silently and try the next method.
        pass

    # 2. Fallback to environment variables (for Cloud Shell / local with .env)
    #    Assumes load_dotenv() has been called in app.py
    key_value = os.environ.get(key_name)
    if key_value:
        # print(f"[*] Config: Found key '{key_name}' in environment variables.") # Optional debug
        return key_value

    # 3. If not found anywhere, print an informative error
    #    This error will be visible in the Streamlit app if it occurs there,
    #    or in the Cloud Shell console.
    error_message = f"""
    --- [!] Error: Secret key '{key_name}' not found ---
        - If deployed on Streamlit Community Cloud:
          Ensure '{key_name}' is set in the application's secrets via the dashboard.
        - If running in Cloud Shell or locally:
          Ensure '{key_name}' is defined in your '.env' file in the project root,
          and that `load_dotenv()` is called in your main `app.py`.
    -----------------------------------------------------
    """
    # Using st.error if available, otherwise print to console
    try:
        if hasattr(st, 'error'):
            st.error(error_message)
        else:
            print(error_message)
    except Exception:
        print(error_message) # Fallback print

    return None

# Example Usage (Optional: for testing this script directly if needed,
# but primary use is through import and call from app.py)
if __name__ == "__main__":
    print("Testing config_loader.py directly...")
    # For direct testing in Cloud Shell, you'd need to ensure .env is loaded somehow,
    # or manually set the environment variable for the test.
    # Example:
    # from dotenv import load_dotenv
    # load_dotenv() # Load .env for this direct test

    api_key = get_api_key('GOOGLE_API_KEY')
    if api_key:
        print(f"Test: GOOGLE_API_KEY found (first 5 chars): {api_key[:5]}...")
    else:
        print("Test: GOOGLE_API_KEY not found.")

    non_existent_key = get_api_key('A_KEY_THAT_DOES_NOT_EXIST')
    if not non_existent_key:
        print("Test: Correctly handled non-existent key.")