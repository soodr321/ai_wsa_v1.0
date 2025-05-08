# app.py (V1.0 - Restored Full Functionality with Diagnostics)

print("[App] VERY START of app.py execution...", flush=True) # Keep flush for this first one

import streamlit as st
import os
import sys # Needed for traceback and flushing specific prints if desired
from dotenv import load_dotenv
import traceback # For detailed error logging
import re # For parsing FVE/Rating in Section 1

# Add an early UI write to test responsiveness
# We put this *after* initial imports but *before* local module imports
try:
    st.write("App Script: Standard imports complete...")
except Exception as initial_st_error:
    # This is unlikely but could happen if streamlit itself has issues
    print(f"[App] ERROR during initial st.write: {initial_st_error}", flush=True)

print("[App] Imports completed.", flush=True)


# --- Load environment variables from .env file ---
print("[App] Attempting to load .env file...", flush=True)
dotenv_loaded = load_dotenv() # *** UNCOMMENTED ***
if dotenv_loaded:
    print("[App] .env file found and loaded successfully.", flush=True)
else:
    # This is expected behavior when deployed to SCC (uses st.secrets)
    print("[App] .env file not found or load failed. Will rely on environment variables or Streamlit secrets.", flush=True)
# Explicit flush after potentially slow file operation
sys.stdout.flush()

# --- Import your other modules ---
MODULES_LOADED = False # Flag to track if imports worked
print("[App] Attempting to import local modules...", flush=True)
try:
    import config_loader     # *** UNCOMMENTED ***
    import llm_handler         # *** UNCOMMENTED ***
    import data_fetcher      # *** UNCOMMENTED ***
    import report_generator  # *** UNCOMMENTED ***
    MODULES_LOADED = True
    print("[App] Successfully imported local modules: config_loader, llm_handler, data_fetcher, report_generator.", flush=True)
except ImportError as e:
    MODULES_LOADED = False # Ensure flag is False on failure
    print(f"[App] CRITICAL ERROR importing local modules: {e}", flush=True)
    traceback.print_exc() # Log full traceback to console
    # Display error in Streamlit UI AFTER basic UI setup
    # We defer st.error until the main UI block to avoid potential issues if st fails early
except Exception as e:
    MODULES_LOADED = False # Ensure flag is False on failure
    print(f"[App] CRITICAL UNEXPECTED error importing local modules: {e}", flush=True)
    traceback.print_exc() # Log full traceback to console
    # Defer st.error

print(f"[App] Local modules loaded status: {MODULES_LOADED}", flush=True)
sys.stdout.flush()

# --- Main App UI Setup ---
print("[App] Setting up Streamlit page config and title...", flush=True)
st.set_page_config(page_title="AI Stock Analyst", layout="wide")
st.title("📈 AI Wall Street Analyst (v1.0 POC)")
print("[App] Streamlit page config and title SET.", flush=True)

# Display module loading error message HERE if necessary
if not MODULES_LOADED:
    st.error("""
    **CRITICAL ERROR: Failed to load essential Python code modules.**

    The application cannot continue. Please check the Cloud Shell terminal logs for detailed error messages related to module imports (`config_loader`, `llm_handler`, `data_fetcher`, `report_generator`).

    Possible causes:
    - Files are missing or have incorrect names.
    - Syntax errors within the module files.
    - Missing dependencies within the virtual environment.
    - Issues with file permissions.
    """)
    print("[App] Halting UI setup because local modules failed to load.")
    st.stop() # Stop the script here if modules are missing

# If modules loaded, continue with the rest of the UI
st.markdown("""
Enter a valid US stock ticker symbol below to generate a basic equity research report using Google Gemini.
""")

st.warning("""
**Disclaimer:** This is a Proof-of-Concept application using AI (Google Gemini).
The generated analysis is based on publicly available data (Yahoo Finance) and may have limitations or inaccuracies.
Data may be delayed. The AI may make mistakes. **This is NOT financial advice.**
Always conduct your own thorough research or consult with a qualified financial advisor before making investment decisions.
""", icon="⚠️")

# --- Report Generation Function (Orchestration Logic) ---
# Make sure this is defined before it's called by the button logic
def run_report_generation(ticker_symbol):
    print(f"\n[App:run_report_generation] FUNCTION CALLED for ticker: {ticker_symbol}", flush=True)
    """Orchestrates the report generation process."""
    # Add a write inside the function start
    st.write("Starting report generation process...")

    # 1. Configure LLM
    st.write("Step 1: Configuring LLM...")
    if not hasattr(llm_handler, 'configure_llm') or not hasattr(llm_handler, 'generate_text'):
        st.error("LLM handler functions not found. Please check llm_handler.py.")
        print("[App:run_report_generation] LLM handler function(s) missing.")
        return
    
    llm_config_success = llm_handler.configure_llm() # Store result
    if not llm_config_success:
        st.error("LLM configuration failed. Check API Key setup (.env file or Streamlit secrets) and console logs.")
        print("[App:run_report_generation] LLM configuration returned false.")
        # Display message from config_loader if available (requires modification to config_loader to store/return messages)
        # config_message = config_loader.get_last_message() # Example - requires changes in config_loader
        # if config_message: st.info(f"Configuration Loader Message: {config_message}")
        return # Stop if LLM fails
    st.write("   ✓ LLM Configured")
    print("[App:run_report_generation] LLM Configured.", flush=True)

    # 2. Fetch Data
    st.write(f"Step 2: Fetching data for {ticker_symbol}...")
    fetcher = None
    company_info = None
    quote_data = None
    financial_summary = None
    news = None
    company_name = ticker_symbol
    data_fetched_successfully = False

    try:
        if not hasattr(data_fetcher, 'StockDataFetcher'):
            st.error("StockDataFetcher class not found. Please check data_fetcher.py.")
            print("[App:run_report_generation] StockDataFetcher class missing.")
            return

        print("[App:run_report_generation] Initializing StockDataFetcher...", flush=True)
        fetcher = data_fetcher.StockDataFetcher(ticker_symbol)
        print("[App:run_report_generation] Fetching company info...", flush=True)
        company_info = fetcher.get_company_info()
        print("[App:run_report_generation] Fetching quote data...", flush=True)
        quote_data = fetcher.get_quote_data()
        print("[App:run_report_generation] Fetching financial summary...", flush=True)
        financial_summary = fetcher.get_financial_summary()
        print("[App:run_report_generation] Fetching news...", flush=True)
        news = fetcher.get_news()

        if company_info and company_info.get('longName'):
            company_name = company_info['longName']
        st.write(f"   -> Fetched data for: {company_name}")
        
        if not company_info or not quote_data:
             st.warning("Warning: Could not retrieve essential company or quote data. Report quality may be impacted.")
        
        if news is None:
            news = []
            st.info("No news items found or news fetching might have failed.")

        data_fetched_successfully = True
        st.write("   ✓ Data Fetched")
        print("[App:run_report_generation] Data Fetched.", flush=True)

    except ValueError as ve:
        st.error(f"Error fetching data: {ve}. Likely an invalid ticker ('{ticker_symbol}'). Please check and try again.")
        print(f"[App:run_report_generation] ValueError during data fetching for {ticker_symbol}: {ve}", flush=True)
        return
    except Exception as e:
        st.error(f"An unexpected error occurred during data fetching for {ticker_symbol}:")
        st.exception(e)
        print(f"[App:run_report_generation] Data fetching error for {ticker_symbol}: {e}", flush=True)
        traceback.print_exc()
        return

    # 3. Generate Sections
    st.write("Step 3: Generating report sections with AI...")
    print("\n[App:run_report_generation] Starting section generation...", flush=True)
    report_sections = []
    parsed_fve = None
    parsed_rating = None

    # --- Internal Helper ---
    def generate_and_append(section_func_obj, section_name_str, *args_for_func, **kwargs_for_func):
        nonlocal report_sections
        st.write(f"   - Generating {section_name_str}...")
        print(f"[App:run_report_generation]   - Generating {section_name_str}...", flush=True)
        try:
            if not callable(section_func_obj):
                 raise TypeError(f"Object for {section_name_str} is not callable.")
            output = section_func_obj(*args_for_func, **kwargs_for_func)
            if output and isinstance(output, str):
                 report_sections.append(output)
                 st.write(f"     ✓ {section_name_str} generated.")
                 print(f"[App:run_report_generation]     ✓ {section_name_str} Success.", flush=True)
                 return output
            else:
                 st.warning(f"Section {section_name_str} generation returned empty or invalid data.")
                 report_sections.append(f"## {section_name_str}\n\nError: Failed to generate content (empty/invalid response).\n")
                 print(f"[App:run_report_generation]     ! {section_name_str} returned empty/invalid.", flush=True)
                 return None
        except Exception as e_section:
             error_msg = f"Error generating {section_name_str}: {e_section}"
             st.error(error_msg) # Show specific error in UI
             st.exception(e_section) # Show traceback in UI
             print(f"[App:run_report_generation]   ! ERROR in {section_name_str}: {e_section}", flush=True)
             traceback.print_exc()
             report_sections.append(f"## {section_name_str}\n\nError generating content for this section: {e_section}\n")
             return None
    # --- End Helper ---

    # --- Check Required Modules Loaded Before Calling ---
    if not MODULES_LOADED: # Redundant check, but safe
         st.error("Cannot generate sections because code modules failed to load.")
         return

    # --- Section 1 & Parse ---
    if hasattr(report_generator, 'generate_section_1_exec_summary'):
        section_1_output = generate_and_append(
            report_generator.generate_section_1_exec_summary, "Section 1: Executive Summary",
            ticker=ticker_symbol, company_info=company_info, quote_data=quote_data,
            llm_handler_generate=llm_handler.generate_text
        )
        if section_1_output and "Error generating content" not in section_1_output:
            st.write("   - Parsing FVE/Rating from Section 1...")
            print("[App:run_report_generation]   - Parsing S1...", flush=True)
            try:
                fve_match = re.search(r"(?:Fair\sValue\sEstimate|FVE)\s*[:\-]?\s*\$?([\d,]+\.\d{2})\b", section_1_output, re.IGNORECASE)
                rating_match = re.search(r"(?:Stock\sRating|Recommendation|Rating)\s*[:\-]?\s*(\b(?:Buy|Hold|Sell|Neutral|Outperform|Underperform|Accumulate|Reduce|Strong\sBuy|Moderate\sBuy)\b)", section_1_output, re.IGNORECASE | re.MULTILINE)
                if fve_match:
                    try:
                        parsed_fve = float(fve_match.group(1).replace(',', ''))
                        st.write(f"     ✓ Parsed FVE: {parsed_fve}")
                        print(f"[App:run_report_generation]     ✓ Parsed FVE: {parsed_fve}", flush=True)
                    except ValueError:
                        st.warning("     - Found FVE pattern but failed to convert number.")
                        print(f"[App:run_report_generation] FVE conversion error. Match: {fve_match.group(1)}", flush=True)
                else:
                     st.warning("     - Could not parse FVE from Section 1.")
                     print(f"[App:run_report_generation] FVE not found in S1.", flush=True)
                if rating_match:
                    parsed_rating = rating_match.group(1).strip().capitalize()
                    st.write(f"     ✓ Parsed Rating: {parsed_rating}")
                    print(f"[App:run_report_generation]     ✓ Parsed Rating: {parsed_rating}", flush=True)
                else:
                     st.warning("     - Could not parse Rating from Section 1.")
                     print(f"[App:run_report_generation] Rating not found in S1.", flush=True)
            except Exception as parse_e:
                st.warning(f"     - Error during parsing Section 1: {parse_e}")
                print(f"[App:run_report_generation] S1 parsing error: {parse_e}", flush=True)
                traceback.print_exc()
    else:
         print("[App:run_report_generation] generate_section_1 function missing.")


    # --- Sections 2-8 ---
    section_generators = [
        ("generate_section_2_business_description", "Section 2: Business Description", {"ticker": ticker_symbol, "company_info": company_info, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_3_strategy_outlook", "Section 3: Strategy & Outlook", {"ticker": ticker_symbol, "company_info": company_info, "news": news, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_4_economic_moat", "Section 4: Economic Moat", {"ticker": ticker_symbol, "company_info": company_info, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_5_financial_analysis", "Section 5: Financial Analysis", {"ticker": ticker_symbol, "company_info": company_info, "financial_summary": financial_summary, "news": news, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_6_valuation", "Section 6: Valuation Analysis", {"ticker": ticker_symbol, "company_info": company_info, "quote_data": quote_data, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_7_risk_uncertainty", "Section 7: Risk Assessment", {"ticker": ticker_symbol, "company_info": company_info, "news": news, "llm_handler_generate": llm_handler.generate_text}),
        ("generate_section_8_bulls_bears", "Section 8: Bulls vs Bears", {"ticker": ticker_symbol, "company_info": company_info, "quote_data": quote_data, "financial_summary": financial_summary, "news": news, "llm_handler_generate": llm_handler.generate_text}),
    ]
    for func_name, title, kwargs_for_func in section_generators:
        if hasattr(report_generator, func_name):
            generate_and_append(getattr(report_generator, func_name), title, **kwargs_for_func)
        else:
            st.error(f"{func_name} not found. Please check report_generator.py.")
            report_sections.append(f"## {title}\n\nError: Report generation function missing.\n")
            print(f"[App:run_report_generation] Report generator function {func_name} missing.")

    # --- Section 9 ---
    if hasattr(report_generator, 'generate_section_9_conclusion_recommendation'):
        generate_and_append(
            report_generator.generate_section_9_conclusion_recommendation, "Section 9: Conclusion",
            ticker=ticker_symbol, company_info=company_info, quote_data=quote_data,
            llm_handler_generate=llm_handler.generate_text,
            fve_value=parsed_fve,
            rating_value=parsed_rating
        )
    else:
         print("[App:run_report_generation] generate_section_9 function missing.")


    # --- Section 10 ---
    if hasattr(report_generator, 'generate_section_10_references'):
        generate_and_append(report_generator.generate_section_10_references, "Section 10: References")
    else:
         print("[App:run_report_generation] generate_section_10 function missing.")


    # 4. Assemble Report
    st.write("Step 4: Assembling final report...")
    print("\n[App:run_report_generation] Assembling report...", flush=True)
    final_report_markdown = None
    try:
        if not hasattr(report_generator, 'assemble_report'):
            st.error("assemble_report function not found. Please check report_generator.py.")
            error_title_md = f"# REPORT ASSEMBLY FAILED: {company_name} ({ticker_symbol})"
            error_body_md = "\n\n**Error:** `assemble_report` function is missing from `report_generator.py`.\n\n"
            if report_sections:
                error_body_md += "Partial sections generated:\n\n---\n\n" + "\n\n---\n\n".join(s for s in report_sections if s)
            final_report_markdown = error_title_md + error_body_md
            print("[App:run_report_generation] assemble_report function missing.")
        elif report_sections:
            final_report_markdown = report_generator.assemble_report(
                ticker=ticker_symbol,
                company_name=company_name,
                all_sections=report_sections
            )
            st.write("   ✓ Report Assembled")
            print("[App:run_report_generation]   ✓ Report Assembled.", flush=True)
        else:
             st.error("No report sections were successfully generated. Cannot assemble report.")
             print("[App:run_report_generation] No sections to assemble.", flush=True)
             return
    except Exception as assemble_e:
        st.error(f"Error assembling final report: {assemble_e}")
        print(f"[App:run_report_generation] Error assembling report: {assemble_e}", flush=True)
        traceback.print_exc()
        partial_report_content = "\n\n---\n\n".join(s for s in report_sections if s)
        final_report_markdown = f"# PARTIAL REPORT: {company_name} ({ticker_symbol})\n\n**Error during final assembly:** {assemble_e}\n\n{partial_report_content}"

    # 5. Display Report
    print("[App:run_report_generation] Displaying report...", flush=True)
    if final_report_markdown:
         st.success("Report generation complete!")
         st.markdown("---")
         st.markdown(final_report_markdown, unsafe_allow_html=False)
         print("[App:run_report_generation] Report displayed in UI.", flush=True)
    else:
         st.error("Failed to generate or assemble the final report. Check logs for details.")
         print("[App:run_report_generation] Final markdown is None or empty.", flush=True)
    # --- End of run_report_generation(ticker_symbol) body ---


# --- UI Input and Trigger ---
# This block should only execute if modules loaded successfully.
if MODULES_LOADED:
    print("[App] Setting up Streamlit input elements.", flush=True) # Confirm UI setup proceeds
    if 'ticker_input' not in st.session_state:
        st.session_state.ticker_input = ""

    ticker = st.text_input(
        "Enter US Stock Ticker Symbol:",
        value=st.session_state.ticker_input,
        placeholder="e.g., MSFT, NVDA, AAPL",
        help="Enter a ticker like 'GOOGL', 'AAPL', etc."
        ).strip().upper()
    st.session_state.ticker_input = ticker

    generate_button = st.button("Generate Report", type="primary") # No need for disabled check here if protected by MODULES_LOADED

    if generate_button:
        if ticker:
            print(f"[App] 'Generate Report' button clicked for ticker: {ticker}", flush=True)
            # Clear previous report area (optional)
            # Find a way to target the report output area if needed, or just let it overwrite
            with st.spinner(f'Generating report for {ticker}... Please wait. This may take 1-2 minutes.'):
                try:
                    run_report_generation(ticker)
                except Exception as e: # Catch errors within the generation call itself
                     st.error(f"An unexpected error occurred during the report generation process for {ticker}:")
                     st.exception(e)
                     print(f"[App] Error during run_report_generation call for {ticker}: {e}", flush=True)
                     traceback.print_exc()
        else:
            st.warning("Please enter a stock ticker symbol.", icon="⚠️")
            print("[App] 'Generate Report' button clicked, but no ticker symbol was entered.", flush=True)

    st.markdown("---")
    st.caption("Powered by Google Gemini & Yahoo Finance data. Developed in Google Cloud Shell. Deployed on Streamlit Community Cloud.")

print("[App] End of app.py execution.", flush=True) # Add a final print
sys.stdout.flush()