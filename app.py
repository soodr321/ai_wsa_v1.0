# app.py
import streamlit as st
import os
import sys
from dotenv import load_dotenv # For local .env loading
import traceback
import logging # For more structured logging later if needed
import re # For parsing FVE/Rating

# --- Streamlit Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
try:
    st.set_page_config(page_title="AI Wall Street Analyst", layout="wide")
except st.errors.StreamlitAPIException as e:
    if "set_page_config() has already been called" in str(e):
        pass
    else:
        print(f"[App] Error setting page config: {e}", flush=True)

print("[App] VERY START of app.py execution...", flush=True)
print("[App] Standard library imports completed.", flush=True)

print("[App] Attempting to load .env file...", flush=True)
try:
    env_path = load_dotenv(verbose=True, override=True)
    if env_path:
        print(f"[App] .env file loaded successfully from: {env_path}", flush=True)
    else:
        print("[App] .env file not found or is empty. Relying on environment variables or Streamlit secrets.", flush=True)
except Exception as e:
    print(f"[App] Error attempting to load .env file: {e}. Relying on environment variables or Streamlit secrets.", flush=True)

# --- Import Local Modules (AFTER st.set_page_config) ---
print("[App] Attempting to import local modules...", flush=True)
local_modules_loaded = False
try:
    from config_loader import get_api_key
    import llm_handler # Import the module itself
    from data_fetcher import StockDataFetcher # CORRECTED IMPORT
    import report_generator as rg_funcs # Import the module with an alias

    local_modules_loaded = True
    print("[App] Successfully imported local modules.", flush=True)
except ImportError as e:
    print(f"[App] FATAL ERROR importing local modules: {e}", flush=True)
    try:
        st.error(f"Critical Error: Could not import necessary Python modules. Application cannot start. Details: {e}")
    except NameError: pass
    traceback.print_exc()
    if 'st' in globals() and hasattr(st, 'stop'): st.stop()
    else: sys.exit(1)

# --- Configuration & Initialization (AFTER st.set_page_config and local imports) ---
print(f"[App] Local modules loaded status: {local_modules_loaded}", flush=True)

# We will initialize StockDataFetcher inside the orchestration function once we have the ticker

if local_modules_loaded:
    print("[App] Attempting to retrieve API key...", flush=True)
    api_key = get_api_key("GOOGLE_API_KEY")

    if not api_key:
        st.error("🔴 CRITICAL ERROR: GOOGLE_API_KEY not found. Please set it in Streamlit secrets or .env file. Application cannot proceed.")
        print("🔴 CRITICAL ERROR in app.py: GOOGLE_API_KEY not found. Halting.", flush=True)
        st.stop()
    else:
        print("[App] API Key retrieved successfully.", flush=True)
        print("[App] Attempting to configure LLM via llm_handler.configure_llm()...", flush=True)
        if llm_handler.configure_llm():
            print("[App] LLM configured successfully via llm_handler.configure_llm().", flush=True)
            # StockDataFetcher will be initialized later, when ticker is available
        else:
            print("[App] FATAL ERROR: Failed to configure LLM. Application cannot proceed.", flush=True)
            st.error("Critical Error: LLM configuration failed. Please check API key and logs. Application cannot proceed.")
            st.stop()
else:
    print("[App] Halting due to failure in loading local modules.", flush=True)
    if 'st' in globals() and hasattr(st, 'stop'): st.stop()
    else: sys.exit(1)


# --- Main App UI Setup (AFTER st.set_page_config) ---
st.title("📈 AI Wall Street Analyst (v1.0 POC)")
print("[App] Streamlit title SET.", flush=True)

st.markdown("""
Welcome to the AI Wall Street Analyst! This Proof-of-Concept (POC) application demonstrates
the capability to generate a basic stock analysis report using AI.

**Enter a valid U.S. stock ticker symbol below and click "Generate Report".**
""")

st.warning("""
**⚠️ Disclaimer:**
*   This application is a Proof-of-Concept and for demonstration purposes only.
*   The information provided is AI-generated and may contain inaccuracies or omissions.
*   Data is sourced from Yahoo Finance and may have its own limitations or delays.
*   **This is NOT financial advice. Always do your own thorough research or consult with a qualified financial advisor before making any investment decisions.**
""")
print("[App] Disclaimers displayed.", flush=True)


def parse_fve_and_rating_from_s1(section_1_text: str) -> tuple[float | str | None, str | None]:
    print(f"[App Parser] Attempting to parse FVE/Rating from S1 text (first 300 chars):\n'''{section_1_text[:300]}'''") # Log more for context
    fve_value = None
    rating_value = None

    # FVE Parsing:
    # Pattern to match "Fair Value Estimate (FVE): $150.00" or "FVE: $150.00" or "Fair Value Estimate: $150.00"
    # It also handles numbers with or without commas, and with or without cents.
    fve_pattern_text = r"(?:Fair Value Estimate(?:\s*\(FVE\))?|FVE)\s*:\s*\$?((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?)"
    # Explanation of the number part: ((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?)
    # 1. (?:\d{1,3}(?:,\d{3})*|\d+)  -- Matches whole numbers:
    #    - \d{1,3}(?:,\d{3})*  -- Like 1,234,567 or 123
    #    - |\d+                 -- Or simple numbers like 12345
    # 2. (?:\.\d+)?                  -- Optionally matches decimal part like .00 or .5

    fve_match = re.search(fve_pattern_text, section_1_text, re.IGNORECASE)
    if fve_match:
        fve_str = fve_match.group(1).replace(',', '') # Get captured number string, remove commas
        try:
            fve_value = float(fve_str)
            print(f"[App Parser] Parsed FVE (float): {fve_value}")
        except ValueError:
            fve_value = fve_str # Store as string if not convertible (e.g., if LLM includes non-numeric chars)
            print(f"[App Parser] Parsed FVE (string, could not convert to float): '{fve_value}'")
    else:
        # Fallback FVE search if the primary one fails - more general search for a dollar amount near "Fair Value"
        fve_fallback_match = re.search(r"Fair Value.*?\$?((?:\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?)", section_1_text, re.IGNORECASE)
        if fve_fallback_match:
            fve_str = fve_fallback_match.group(1).replace(',', '')
            try:
                fve_value = float(fve_str)
                print(f"[App Parser] Parsed FVE (float - fallback): {fve_value}")
            except ValueError:
                fve_value = fve_str
                print(f"[App Parser] Parsed FVE (string - fallback, could not convert to float): '{fve_value}'")

    # Rating Parsing (seems to be working, but let's keep it robust)
    rating_keywords = r"(?:Concise Stock Rating|Investment Recommendation|Rating|Recommendation)\s*[:\-is\s]*"
    common_ratings_capture = r"(Strong Buy|Buy|Accumulate|Outperform|Overweight|Hold|Neutral|Equal-weight|Market Perform|Reduce|Underperform|Sell|Strong Sell)"

    # Pattern 1: Keyword followed by rating
    rating_match_1 = re.search(rating_keywords + common_ratings_capture, section_1_text, re.IGNORECASE)
    if rating_match_1:
        rating_value = rating_match_1.group(1).strip().title() # .group(1) is the rating itself
        print(f"[App Parser] Parsed Rating (Pattern 1): '{rating_value}'")
    else:
        # Pattern 2: Rating mentioned broadly (less precise, used as fallback)
        # Ensure it's a whole word match for the rating.
        rating_match_2 = re.search(r"\b" + common_ratings_capture + r"\b", section_1_text, re.IGNORECASE)
        if rating_match_2:
            # Check if this rating isn't part of a sentence that negates it, e.g., "Not a Buy"
            # This requires more complex context checking, for now, we accept it.
            rating_value = rating_match_2.group(1).strip().title()
            print(f"[App Parser] Parsed Rating (Pattern 2 - broad): '{rating_value}'")

    if not fve_value: print("[App Parser] FVE not found or parsed from S1 after attempts.")
    if not rating_value: print("[App Parser] Rating not found or parsed from S1 after attempts.")
    return fve_value, rating_value


# --- Report Generation Orchestration ---
def run_report_generation_orchestration(ticker_symbol: str):
    # StockDataFetcher is now initialized here
    print(f"[App Orchestration] Report generation requested for ticker: {ticker_symbol}", flush=True)
    all_sections_content = []
    parsed_fve_s1 = None
    parsed_rating_s1 = None

    try:
        with st.spinner(f"Initializing data fetcher and generating report for {ticker_symbol}... This may take a minute or two..."):
            print(f"[App Orchestration] Initializing StockDataFetcher for {ticker_symbol}...")
            try:
                fetcher = StockDataFetcher(ticker_symbol) # INSTANTIATE HERE
                print(f"[App Orchestration] StockDataFetcher initialized for {ticker_symbol}.")
            except ValueError as ve_data_fetcher: # Catch specific ValueError from StockDataFetcher constructor
                st.error(f"Error initializing data for {ticker_symbol}: {ve_data_fetcher}")
                print(f"[App Orchestration] StockDataFetcher init error: {ve_data_fetcher}")
                return # Stop if fetcher cannot be initialized (e.g., invalid ticker)
            except Exception as e_data_fetcher: # Catch any other exception during fetcher init
                st.error(f"An unexpected error occurred while setting up data for {ticker_symbol}: {e_data_fetcher}")
                print(f"[App Orchestration] StockDataFetcher generic init error: {e_data_fetcher}\n{traceback.format_exc()}")
                return

            print(f"[App Orchestration] Fetching data for {ticker_symbol} using fetcher instance...")
            company_info = fetcher.get_company_info()
            quote_data = fetcher.get_quote_data()
            financial_summary = fetcher.get_financial_summary()
            news = fetcher.get_news()
            company_name_for_title = company_info.get('longName', ticker_symbol)

            # Check if essential data could be fetched after successful fetcher initialization
            if not company_info or not company_info.get('longName') or quote_data.get('currentPrice') is None :
                st.error(f"Failed to fetch essential data for {ticker_symbol} (e.g., name, price) even after fetcher initialization. The ticker might be valid but data is incomplete on yfinance. Cannot generate full report.")
                print(f"[App Orchestration] Essential data (name/price) missing post-fetch for {ticker_symbol}.")
                # Optionally display any partial data available:
                if company_info: st.json({"company_info_partial": company_info})
                if quote_data: st.json({"quote_data_partial": quote_data})
                return

            print(f"[App Orchestration] Data fetched. Proceeding to generate sections...")

            # Section 1: Executive Summary
            s1_content = rg_funcs.generate_section_1_exec_summary(
                ticker_symbol, company_info, quote_data, llm_handler.generate_text
            )
            all_sections_content.append(s1_content)
            parsed_fve_s1, parsed_rating_s1 = parse_fve_and_rating_from_s1(s1_content)
            print(f"[App Orchestration] Section 1 generated. Parsed FVE: {parsed_fve_s1}, Parsed Rating: {parsed_rating_s1}")

            # Section 2: Business Description
            s2_content = rg_funcs.generate_section_2_business_description(
                ticker_symbol, company_info, llm_handler.generate_text
            )
            all_sections_content.append(s2_content)
            print(f"[App Orchestration] Section 2 generated.")

            # Section 3: Business Strategy & Outlook
            s3_content = rg_funcs.generate_section_3_strategy_outlook(
                ticker_symbol, company_info, news, llm_handler.generate_text
            )
            all_sections_content.append(s3_content)
            print(f"[App Orchestration] Section 3 generated.")

            # Section 4: Economic Moat Analysis
            s4_content = rg_funcs.generate_section_4_economic_moat(
                ticker_symbol, company_info, llm_handler.generate_text
            )
            all_sections_content.append(s4_content)
            print(f"[App Orchestration] Section 4 generated.")

            # Section 5: Financial Analysis
            s5_content = rg_funcs.generate_section_5_financial_analysis(
                ticker_symbol, company_info, financial_summary, news, llm_handler.generate_text
            )
            all_sections_content.append(s5_content)
            print(f"[App Orchestration] Section 5 generated.")

            # Section 6: Valuation Analysis
            s6_content = rg_funcs.generate_section_6_valuation(
                ticker_symbol, company_info, quote_data, llm_handler.generate_text
            )
            all_sections_content.append(s6_content)
            print(f"[App Orchestration] Section 6 generated.")

            # Section 7: Risk and Uncertainty Assessment
            s7_content = rg_funcs.generate_section_7_risk_uncertainty(
                ticker_symbol, company_info, news, llm_handler.generate_text
            )
            all_sections_content.append(s7_content)
            print(f"[App Orchestration] Section 7 generated.")

            # Section 8: Bulls Say / Bears Say
            s8_content = rg_funcs.generate_section_8_bulls_bears(
                ticker_symbol, company_info, quote_data, financial_summary, news, llm_handler.generate_text
            )
            all_sections_content.append(s8_content)
            print(f"[App Orchestration] Section 8 generated.")

            # Section 9: Conclusion & Investment Recommendation
            s9_content = rg_funcs.generate_section_9_conclusion_recommendation(
                ticker_symbol, company_info, quote_data, llm_handler.generate_text,
                fve_value=parsed_fve_s1, rating_value=parsed_rating_s1
            )
            all_sections_content.append(s9_content)
            print(f"[App Orchestration] Section 9 generated.")

            # Section 10: References
            s10_content = rg_funcs.generate_section_10_references()
            all_sections_content.append(s10_content)
            print(f"[App Orchestration] Section 10 generated.")

            final_report_md = rg_funcs.assemble_report(ticker_symbol, company_name_for_title, all_sections_content)
            print(f"[App Orchestration] Report assembled for {ticker_symbol}.", flush=True)

        # Display logic
        if any("error generating content" in str(section).lower() for section in all_sections_content if isinstance(section, str)) or \
           any("failed to generate content" in str(section).lower() for section in all_sections_content if isinstance(section, str)):
            st.error(f"Could not generate a full report for {ticker_symbol}. Some sections encountered issues.")
            st.markdown("### Generated Report (may be incomplete or contain errors):")
            st.markdown(final_report_md if 'final_report_md' in locals() else "Report assembly failed.")
            print(f"[App Orchestration] Error detected in one or more sections for {ticker_symbol}.", flush=True)
        elif 'final_report_md' in locals() and final_report_md:
            st.success(f"Report for {ticker_symbol} generated successfully!")
            st.markdown("---")
            st.markdown(final_report_md)
            print(f"[App Orchestration] Report for {ticker_symbol} displayed successfully.", flush=True)

            # Consistency check
            if parsed_fve_s1 is not None and parsed_rating_s1 is not None:
                st.info("ℹ️ Consistency Note: Section 1 FVE & Rating values were passed to Section 9 for restatement. Verify actual S9 text for confirmation.")
                print(f"[App Orchestration] S1 FVE/Rating passed to S9 for {ticker_symbol}.", flush=True)
            else:
                st.warning(f"⚠️ Consistency Check Note for {ticker_symbol}: Section 1 FVE/Rating were not clearly parsed. FVE: '{parsed_fve_s1}', Rating: '{parsed_rating_s1}'.")
                print(f"[App Orchestration] Consistency NOTE for {ticker_symbol}: S1 FVE/Rating not fully parsed.", flush=True)
        else:
            st.warning(f"No report content could be generated for {ticker_symbol}, or report assembly failed.")
            print(f"[App Orchestration] No report content generated for {ticker_symbol}.", flush=True)

    except Exception as e: # Catch-all for the orchestration function itself
        st.error(f"An unexpected error occurred during report orchestration for {ticker_symbol}: {e}")
        print(f"[App Orchestration] UNEXPECTED EXCEPTION: {e}\n{traceback.format_exc()}", flush=True)


# --- User Input and Trigger ---
print("[App] Setting up user input fields.", flush=True)
ticker_input = st.text_input("Enter Stock Ticker (e.g., AAPL, MSFT, GOOG):", key="ticker_input_main").strip().upper()

if st.button("Generate Report", key="generate_report_button"):
    if ticker_input and local_modules_loaded: # Basic check
        print(f"[App] 'Generate Report' button clicked for ticker: {ticker_input}", flush=True)
        run_report_generation_orchestration(ticker_input)
    elif not ticker_input:
        st.warning("Please enter a stock ticker.")
        print("[App] 'Generate Report' button clicked, but no ticker entered.", flush=True)
    else: # Should not be hit if local_modules_loaded is true, but good fallback
        st.error("Application is not fully initialized or ticker is missing. Cannot generate report. Please check logs or enter a ticker.")
        print("[App] 'Generate Report' button clicked, but app not fully initialized or ticker missing.", flush=True)

print("[App] End of app.py execution (initial run or after interactions).", flush=True)