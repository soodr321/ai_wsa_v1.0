# app.py
import streamlit as st
import os
import sys
from dotenv import load_dotenv # For local .env loading
import traceback
import logging # For more structured logging later if needed

# --- Streamlit Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
# Encapsulate in a try-except block in case of re-runs where it might already be set.
# This is more of a precaution for some environments; usually, Streamlit handles re-runs gracefully.
try:
    st.set_page_config(page_title="AI Stock Analyst", layout="wide")
    # print("[App] Streamlit page config SET (or confirmed).", flush=True) # Debug print
except st.errors.StreamlitAPIException as e:
    if "set_page_config() has already been called" in str(e):
        pass # print("[App] Page config already set, ignoring re-call.", flush=True) # Debug print
    else:
        print(f"[App] Error setting page config: {e}", flush=True) # Debug print for other errors
        # Optionally, st.error(f"Page config error: {e}") if critical enough to halt.

print("[App] VERY START of app.py execution...", flush=True) # For debugging startup

# Add project root to Python path if your modules are structured in a way that needs it.
# For a flat structure like yours (all .py files in the root), this is often not strictly necessary
# but can be a good practice for consistency or future refactoring.
# SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# if SCRIPT_DIR not in sys.path:
#    sys.path.append(SCRIPT_DIR)
# print(f"[App] sys.path includes: {SCRIPT_DIR}", flush=True)


print("[App] Standard library imports completed.", flush=True)

# Load environment variables from .env file (primarily for local Cloud Shell development)
print("[App] Attempting to load .env file...", flush=True)
try:
    # find_dotenv will search for the .env file, starting from the script's directory
    # and going up the directory tree. This is robust.
    env_path = load_dotenv(verbose=True, override=True) # verbose=True helps debug .env loading
    if env_path:
        print(f"[App] .env file loaded successfully from: {env_path}", flush=True)
    else:
        # This means load_dotenv() ran but didn't find a .env or it was empty.
        print("[App] .env file not found or is empty. Relying on environment variables or Streamlit secrets.", flush=True)
except Exception as e:
    # This catches errors during the load_dotenv() call itself.
    print(f"[App] Error attempting to load .env file: {e}. Relying on environment variables or Streamlit secrets.", flush=True)

# --- Import Local Modules (AFTER st.set_page_config) ---
print("[App] Attempting to import local modules...", flush=True)
local_modules_loaded = False
try:
    from config_loader import get_api_key
    from llm_handler import LLMHandler
    from data_fetcher import DataFetcher
    from report_generator import ReportGenerator
    local_modules_loaded = True
    print("[App] Successfully imported local modules: config_loader, llm_handler, data_fetcher, report_generator.", flush=True)
except ImportError as e:
    print(f"[App] FATAL ERROR importing local modules: {e}", flush=True)
    # At this point, if st is available, use it. Otherwise, this print is the best we can do for SCC logs.
    try:
        st.error(f"Critical Error: Could not import necessary Python modules. The application cannot start. Please check deployment logs on Streamlit Cloud. Details: {e}")
    except NameError: # If st itself hasn't been fully set up or is part of the issue.
        pass # The print statement above will have to suffice.
    traceback.print_exc() # Always print traceback for detailed debugging in logs
    # Consider st.stop() if st is available and you want to halt script execution cleanly
    if 'st' in globals() and hasattr(st, 'stop'):
        st.stop()
    else:
        sys.exit(1) # Force exit if Streamlit context is unavailable for st.stop()

# --- Configuration & Initialization (AFTER st.set_page_config and local imports) ---
print(f"[App] Local modules loaded status: {local_modules_loaded}", flush=True)

# Proceed only if local modules were loaded successfully
if local_modules_loaded:
    print("[App] Attempting to retrieve API key...", flush=True)
    api_key = get_api_key("GOOGLE_API_KEY")

    if not api_key:
        # get_api_key in config_loader.py will print its own detailed message to the console.
        # It may also try to use st.error if st is available in its context.
        # We add an st.error here as a fallback/confirmation in the main app flow.
        st.error("🔴 CRITICAL ERROR: GOOGLE_API_KEY not found. Please ensure it's set in Streamlit secrets for deployed apps, or in your .env file for local development. Application cannot proceed.")
        print("🔴 CRITICAL ERROR in app.py: GOOGLE_API_KEY not found after call to get_api_key. Halting.", flush=True)
        st.stop() # Stop the app if API key is missing
    else:
        print("[App] API Key retrieved successfully.", flush=True)
        # Initialize handlers only if API key is present and modules are loaded
        try:
            llm_handler_instance = LLMHandler(api_key=api_key)
            data_fetcher_instance = DataFetcher()
            report_generator_instance = ReportGenerator(llm_handler_instance, data_fetcher_instance)
            print("[App] Core handlers (LLM, DataFetcher, ReportGenerator) initialized successfully.", flush=True)
        except Exception as e:
            print(f"[App] FATAL ERROR initializing core handlers: {e}", flush=True)
            st.error(f"Critical Error: Could not initialize application components. Details: {e}")
            traceback.print_exc()
            st.stop()
else:
    # This else block will be hit if local_modules_loaded is False from the import try-except block.
    # An error message and st.stop() or sys.exit() would have already been called.
    # Adding a print here for completeness in the log, though it might be redundant.
    print("[App] Halting due to failure in loading local modules.", flush=True)
    # Ensure app stops if st.stop() wasn't reached or effective.
    if 'st' in globals() and hasattr(st, 'stop'):
        st.stop()
    else:
        sys.exit(1)


# --- Main App UI Setup (AFTER st.set_page_config) ---
st.title("📈 AI Wall Street Analyst (v1.0 POC)")
print("[App] Streamlit title SET.", flush=True)

st.markdown("""
Welcome to the AI Wall Street Analyst! This Proof-of-Concept (POC) application demonstrates
the capability to generate a basic stock analysis report using AI.

**Enter a valid U.S. stock ticker symbol below and click "Generate Report".**
""")

# --- Disclaimer ---
st.warning("""
**⚠️ Disclaimer:**
*   This application is a Proof-of-Concept and for demonstration purposes only.
*   The information provided is AI-generated and may contain inaccuracies or omissions.
*   Data is sourced from Yahoo Finance and may have its own limitations or delays.
*   **This is NOT financial advice. Always do your own thorough research or consult with a qualified financial advisor before making any investment decisions.**
""")
print("[App] Disclaimers displayed.", flush=True)

# --- Report Generation Function ---
def run_report_generation(ticker_symbol):
    """
    Orchestrates the report generation process.
    """
    global report_generator_instance # Use the globally initialized instance

    if not report_generator_instance:
        st.error("Error: Report generator not initialized. Cannot proceed.")
        print("[App] Error in run_report_generation: report_generator_instance is None.", flush=True)
        return

    print(f"[App] Report generation requested for ticker: {ticker_symbol}", flush=True)
    try:
        with st.spinner(f"Generating report for {ticker_symbol}... This may take a minute or two..."):
            print(f"[App] Inside spinner for {ticker_symbol}. Calling report_generator.generate_full_report().", flush=True)
            # Ensure that report_generator_instance and its methods are correctly called
            final_report_md, parsed_fve_s1, parsed_rating_s1, parsed_fve_s9, parsed_rating_s9 = report_generator_instance.generate_full_report(ticker_symbol)
            print(f"[App] Report generation completed for {ticker_symbol}. Checking report content.", flush=True)

        if "error" in final_report_md.lower() or "failed" in final_report_md.lower():
            st.error(f"Could not generate a full report for {ticker_symbol}. The process encountered an issue.")
            st.markdown("### Partial or Error Information:")
            st.markdown(final_report_md) # Display whatever was returned, even if it's an error message
            print(f"[App] Error reported in final_report_md for {ticker_symbol}.", flush=True)

        elif final_report_md and "No data found for ticker" not in final_report_md : # A more specific check if yfinance returns no data
            st.success(f"Report for {ticker_symbol} generated successfully!")
            st.markdown("---")
            st.markdown(final_report_md)
            print(f"[App] Report for {ticker_symbol} displayed successfully.", flush=True)

            # Consistency Check (as per PRD)
            print(f"[App] Performing consistency check for {ticker_symbol}: S1_FVE='{parsed_fve_s1}', S1_Rating='{parsed_rating_s1}', S9_FVE='{parsed_fve_s9}', S9_Rating='{parsed_rating_s9}'", flush=True)
            if parsed_fve_s1 is not None and parsed_rating_s1 is not None: # Ensure S1 values were parsed
                if parsed_fve_s1 == parsed_fve_s9 and parsed_rating_s1 == parsed_rating_s9:
                    st.info("✅ Consistency Check: FVE and Rating from Section 1 are correctly restated in Section 9.")
                    print(f"[App] Consistency CHECK PASSED for {ticker_symbol}.", flush=True)
                else:
                    st.warning(f"""
                        ⚠️ Consistency Check Alert for {ticker_symbol}:
                        - Section 1 FVE: '{parsed_fve_s1}', Section 9 FVE: '{parsed_fve_s9}'
                        - Section 1 Rating: '{parsed_rating_s1}', Section 9 Rating: '{parsed_rating_s9}'
                        There might be a discrepancy in FVE/Rating between sections.
                    """)
                    print(f"[App] Consistency CHECK ALERT for {ticker_symbol}: Discrepancy found.", flush=True)
            else:
                st.warning(f"⚠️ Consistency Check Note for {ticker_symbol}: Could not fully verify FVE/Rating consistency as Section 1 values were not clearly parsed (FVE: {parsed_fve_s1}, Rating: {parsed_rating_s1}). This might indicate an issue with Section 1 generation or parsing logic.")
                print(f"[App] Consistency CHECK NOTE for {ticker_symbol}: S1 FVE/Rating not parsed.", flush=True)

        else: # Handles cases like "No data found" or empty/None report
            st.warning(f"No report could be generated for {ticker_symbol}. This might be due to an invalid ticker, no data available, or an internal error. Please check the ticker and try again. If the issue persists, the ticker might not be supported or there may be an issue with data fetching.")
            if final_report_md: # If there's any message (like "No data found") show it.
                st.markdown("---")
                st.markdown(final_report_md)
            print(f"[App] No report generated or 'No data found' for {ticker_symbol}. Message: {final_report_md}", flush=True)


    except Exception as e:
        st.error(f"An unexpected error occurred during report generation for {ticker_symbol}: {e}")
        # log the full traceback to the console for debugging in SCC logs
        print(f"[App] EXCEPTION during report generation for {ticker_symbol}: {e}\n{traceback.format_exc()}", flush=True)
        # Optionally, provide a more user-friendly message if you don't want to expose full exception to UI
        # st.error("An unexpected critical error occurred. Please try again later or contact support if the issue persists.")

# --- User Input and Trigger ---
print("[App] Setting up user input fields.", flush=True)
ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, GOOG):", "").strip().upper()

if st.button("Generate Report"):
    if ticker_input and local_modules_loaded and 'report_generator_instance' in globals() and report_generator_instance is not None:
        print(f"[App] 'Generate Report' button clicked for ticker: {ticker_input}", flush=True)
        run_report_generation(ticker_input)
    elif not ticker_input:
        st.warning("Please enter a stock ticker.")
        print("[App] 'Generate Report' button clicked, but no ticker entered.", flush=True)
    else:
        # This case covers if modules didn't load or report_generator_instance isn't ready
        st.error("Application is not fully initialized. Cannot generate report. Please check logs.")
        print("[App] 'Generate Report' button clicked, but app not fully initialized (modules/generator).", flush=True)

print("[App] End of app.py execution (initial run or after interactions).", flush=True)