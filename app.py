# app.py
import streamlit as st
import os
import sys
from dotenv import load_dotenv
import traceback
import re 

# --- Streamlit Page Configuration ---
try:
    st.set_page_config(page_title="AI Wall Street Analyst", layout="wide")
except st.errors.StreamlitAPIException as e:
    if "set_page_config() has already been called" in str(e): pass
    else: 
        print(f"[App Critical] Error setting page config: {e}", flush=True)
        st.error("Page configuration error. Please refresh.") # User-facing
        st.stop() # Stop execution if page config fails fundamentally

print("[App] VERY START of app.py execution...", flush=True)

# --- Load .env ---
# Ensure load_dotenv is called early, outside any conditional Streamlit logic if possible
# for consistent environment variable loading.
env_loaded_message = "[App] .env file not found or empty. Relying on environment variables or Streamlit secrets."
try:
    if load_dotenv(verbose=True, override=True):
        env_loaded_message = "[App] .env file processed."
    print(env_loaded_message, flush=True)
except Exception as e:
    print(f"[App] Error attempting to load .env file: {e}. {env_loaded_message}", flush=True)


# --- Import Local Modules ---
print("[App] Attempting to import local modules...", flush=True)
llm_handler_instance = None # Initialize globally for app session
fetcher_instance_cache = {} # Simple cache for StockDataFetcher instances per ticker

try:
    from llm_handler import LLMHandler 
    from data_fetcher import StockDataFetcher
    import report_generator as rg_funcs
    from fve_agent import FVEAgent
    # from app_utils import parse_rating_from_s1_text # IDEAL: if you move parser to utils
    print("[App] Successfully imported local modules.", flush=True)
except ImportError as e:
    print(f"[App] FATAL ERROR importing local modules: {e}", flush=True)
    st.error(f"Critical Application Error: Could not import necessary Python modules. Application cannot start. Details: {e}")
    traceback.print_exc(); st.stop()

# --- Configuration & Global Initialization ---
# These could be moved to a dedicated config.py later
APP_LLM_MODEL = os.getenv("APP_LLM_MODEL", "gemini-1.5-flash-latest") # Allow override via env
APP_RFR = float(os.getenv("APP_RFR", "0.045"))
APP_ERP = float(os.getenv("APP_ERP", "0.045"))
APP_STAGE1_YEARS = int(os.getenv("APP_STAGE1_YEARS", "5"))
APP_DEBUG_MODE = os.getenv("APP_DEBUG_MODE", "True").lower() == "true" # Read as bool

print(f"[App Config] LLM Model: {APP_LLM_MODEL}, RFR: {APP_RFR}, ERP: {APP_ERP}, Stage1Yrs: {APP_STAGE1_YEARS}, Debug: {APP_DEBUG_MODE}", flush=True)

try:
    print("[App] Initializing LLMHandler instance globally for the app session...", flush=True)
    llm_handler_instance = LLMHandler(model_name=APP_LLM_MODEL) # API key loaded within LLMHandler
    if not llm_handler_instance.is_configured() or not llm_handler_instance.model:
        # LLMHandler __init__ should print specifics if API key failed
        st.error("🔴 CRITICAL ERROR: LLM Handler could not be configured or model not initialized. Please check API key and application logs. The application cannot proceed.")
        print("🔴 CRITICAL ERROR in app.py: LLMHandler global instance setup failed. Halting.", flush=True)
        st.stop()
    print("[App] LLMHandler global instance ready.", flush=True)
except Exception as e:
    st.error(f"🔴 CRITICAL ERROR during global LLMHandler initialization: {e}. The application cannot proceed.")
    print(f"🔴 CRITICAL ERROR in app.py: LLMHandler global init exception: {e}\n{traceback.format_exc()}", flush=True)
    st.stop()

# --- Main App UI Setup ---
st.title(f"📈 AI Wall Street Analyst (v1.5 - FVE Agent)") 
st.markdown("Welcome! This application uses AI to generate a stock analysis report, featuring an independently calculated Fair Value Estimate (FVE). **Enter a valid U.S. stock ticker symbol and click \"Generate Report\".**")
st.warning("**⚠️ Disclaimer:** Proof-of-Concept. NOT financial advice. AI-generated content may contain inaccuracies. Data from Yahoo Finance. Always do your own research.")

# --- Helper Function for parsing rating (from test_full_report_flow.py) ---
# TODO (V1.6): Move this to a shared app_utils.py module
def parse_rating_from_s1_text_in_app(section_1_text: str) -> str | None:
    if APP_DEBUG_MODE: print(f"[App Parser] Attempting to parse Rating from S1 (first 300 chars):\n'''{section_1_text[:300]}'''")
    rating_value = None; patterns = [r"(?:Overall Rating|Investment Recommendation|Stock Rating)\s*[:\-is\s]*\s*(Strong Buy|Buy|Accumulate|Outperform|Overweight|Hold|Neutral|Equal-weight|Market Perform|Reduce|Underperform|Sell|Strong Sell)\b", r"\b(Strong Buy|Buy|Accumulate|Outperform|Overweight|Hold|Neutral|Equal-weight|Market Perform|Reduce|Underperform|Sell|Strong Sell)\b"]
    for pattern in patterns:
        match = re.search(pattern, section_1_text, re.IGNORECASE)
        if match: rating_value = (match.group(1) or match.group(0)).strip().title(); break 
    if not rating_value and APP_DEBUG_MODE: print("[App Parser] Rating not found or parsed from S1.")
    return rating_value

# --- Report Generation Orchestration ---
def run_report_generation_orchestration(ticker_symbol: str):
    print(f"[App Orchestration] Report generation process started for: {ticker_symbol.upper()}", flush=True)
    
    if not llm_handler_instance or not llm_handler_instance.is_configured() or not llm_handler_instance.model:
        st.error("LLM Service is not available. Cannot generate report. Please check logs or API key setup.")
        return

    try:
        with st.spinner(f"Hold on! Analyzing {ticker_symbol.upper()} and crafting your report... This can take 1-2 minutes..."):
            # --- 1. Data Fetching ---
            fetcher = None; fve_input_data = None; company_info_for_sections = None
            if APP_DEBUG_MODE: print(f"[App Orchestration] Attempting to fetch data for {ticker_symbol}...")
            try:
                # Using a simple cache for fetcher to avoid re-init for the same ticker if app reruns quickly
                if ticker_symbol not in fetcher_instance_cache:
                    fetcher_instance_cache[ticker_symbol] = StockDataFetcher(ticker_symbol, historical_years=APP_STAGE1_YEARS)
                fetcher = fetcher_instance_cache[ticker_symbol]
                
                fve_input_data = fetcher.get_fve_inputs() # Comprehensive data for FVEAgent
                company_info_for_sections = fetcher.get_company_info() # For descriptive sections

                if not fve_input_data or not fve_input_data.get('companyName'):
                    st.error(f"Failed to fetch sufficient FVE input data (e.g., company name) for {ticker_symbol}. Please try another ticker or check data source.")
                    return
                if not company_info_for_sections or not company_info_for_sections.get('longBusinessSummary'):
                    st.warning(f"Could not fetch detailed company summary for {ticker_symbol}. Business Description (Section 2) may be brief or unavailable.")
                if APP_DEBUG_MODE: print(f"[App Orchestration] Data fetched for {ticker_symbol}.")

            except ValueError as ve_data_fetcher: # From StockDataFetcher __init__ typically for bad tickers
                st.error(f"Data Error for {ticker_symbol}: {ve_data_fetcher}. Is the ticker valid and listed on Yahoo Finance?")
                return
            except Exception as e_data_fetcher:
                st.error(f"An unexpected error occurred while fetching data for {ticker_symbol}: {e_data_fetcher}")
                traceback.print_exc(); return

            company_name_for_title = fve_input_data.get('companyName', ticker_symbol)
            current_price = fve_input_data.get('currentPrice')

            # --- 2. Run FVE Agent ---
            if APP_DEBUG_MODE: print(f"[App Orchestration] Instantiating and running FVEAgent for {ticker_symbol}...")
            fve_agent_instance = FVEAgent(
                llm_generate_text_func=llm_handler_instance.generate_text,
                rfr=APP_RFR, erp=APP_ERP, stage1_years=APP_STAGE1_YEARS,
                debug_mode=APP_DEBUG_MODE
            )
            agent_fve, agent_methodology_text = fve_agent_instance.run_valuation_process(fve_input_data)
            if APP_DEBUG_MODE: print(f"[App Orchestration] FVEAgent Results: FVE={agent_fve}, Method='{fve_agent_instance.method_used}'")

            # --- Prepare other data for V1.0 rg_funcs compatibility ---
            quote_data_for_rg = fve_input_data
            news_for_rg = fve_input_data.get('news', [])
            hist_fin_for_rg = fve_input_data.get('historical_financials', {})
            financial_summary_for_rg_v1_style = {
                "latest_annual_earnings": hist_fin_for_rg.get('netIncome_list', [None])[0],
                "latest_annual_revenue": hist_fin_for_rg.get('totalRevenue_list', [None])[0],
                "financials_year": hist_fin_for_rg.get('years', ["N/A"])[0]
            }
            
            all_sections_content = []
            st.info("Generating report sections...") # Single spinner, individual info messages

            # --- 3. Generate Report Sections ---
            print("[App Orchestration] Generating Section 1: Executive Summary...")
            s1_content = rg_funcs.generate_section_1_exec_summary(
                ticker_symbol, company_info_for_sections, quote_data_for_rg, llm_handler_instance.generate_text,
                current_stock_price=current_price,             
                calculated_fve_from_agent=agent_fve,         
                fve_method_used_by_agent=fve_agent_instance.method_used 
            )
            all_sections_content.append(s1_content)
            parsed_rating_s1 = parse_rating_from_s1_text_in_app(s1_content) # Use the app's parser
            print(f"[App Orchestration] Section 1 generated. Parsed Rating: {parsed_rating_s1}")

            methodology_header = "\n## Valuation Methodology & Assumptions\n" # Clearer header
            all_sections_content.append(f"{methodology_header}\n{agent_methodology_text}\n\n---")
            print(f"[App Orchestration] Added FVE Agent Methodology section to report content.")

            # Loop for sections 2-8
            section_gen_map_app = {
                "2: Business Description": lambda: rg_funcs.generate_section_2_business_description(ticker_symbol, company_info_for_sections, llm_handler_instance.generate_text),
                "3: Strategy & Outlook": lambda: rg_funcs.generate_section_3_strategy_outlook(ticker_symbol, company_info_for_sections, news_for_rg, llm_handler_instance.generate_text),
                "4: Economic Moat": lambda: rg_funcs.generate_section_4_economic_moat(ticker_symbol, company_info_for_sections, llm_handler_instance.generate_text),
                "5: Financial Analysis": lambda: rg_funcs.generate_section_5_financial_analysis(ticker_symbol, company_info_for_sections, financial_summary_for_rg_v1_style, news_for_rg, llm_handler_instance.generate_text),
                # "6: Valuation Discussion": lambda: rg_funcs.generate_section_6_valuation(ticker_symbol, company_info_for_sections, quote_data_for_rg, llm_handler_instance.generate_text), # DECISION: Keep or remove S6
                "7: Risk & Uncertainty": lambda: rg_funcs.generate_section_7_risk_uncertainty(ticker_symbol, company_info_for_sections, news_for_rg, llm_handler_instance.generate_text),
                "8: Bulls Say / Bears Say": lambda: rg_funcs.generate_section_8_bulls_bears(ticker_symbol, company_info_for_sections, quote_data_for_rg, financial_summary_for_rg_v1_style, news_for_rg, llm_handler_instance.generate_text),
            }
            # Section 6 Decision Point:
            # If you want to remove Section 6 for V1.5 because FVE Agent methodology is more detailed:
            # Just comment out or delete the line for "6: Valuation Discussion" in section_gen_map_app above.
            # If kept, its prompt should be very general as discussed.
            # For this example, I've kept it but commented out the call for easy toggling. You might want to keep it for now.
            if "6: Valuation Discussion" in section_gen_map_app: # Only add if not commented out
                print("[App Orchestration] Note: Original Section 6 (Valuation Discussion) will be generated.")
            
            for section_name, func_call in section_gen_map_app.items():
                print(f"[App Orchestration] Generating Section {section_name}...")
                all_sections_content.append(func_call())

            print("[App Orchestration] Generating Section 9: Conclusion...")
            s9_content = rg_funcs.generate_section_9_conclusion_recommendation(
                ticker_symbol, company_info_for_sections, quote_data_for_rg, llm_handler_instance.generate_text,
                fve_value=agent_fve, rating_value=parsed_rating_s1, fve_method_used=fve_agent_instance.method_used 
            )
            all_sections_content.append(s9_content)
            
            print("[App Orchestration] Generating Section 10: References...")
            all_sections_content.append(rg_funcs.generate_section_10_references())
            
            final_report_md = rg_funcs.assemble_report(ticker_symbol, company_name_for_title, all_sections_content)
            print(f"[App Orchestration] Report assembled successfully for {ticker_symbol}.", flush=True)

        # --- Display Logic ---
        st.success(f"AI Analyst Report for {company_name_for_title} ({ticker_symbol}) Generated!")
        st.markdown("---")
        st.markdown(final_report_md, unsafe_allow_html=True) # unsafe_allow_html might be needed for complex markdown tables from LLM
            
    except Exception as e:
        st.error(f"A critical error occurred during the report generation process for {ticker_symbol}: {e}")
        print(f"[App Orchestration] UNHANDLED CRITICAL EXCEPTION: {e}\n{traceback.format_exc()}", flush=True)
        st.markdown("### Report Generation Failed")
        st.markdown("An unexpected error stopped the report generation. Please check the application logs or try a different ticker. If the issue persists, the service might be temporarily unavailable.")


# --- User Input and Trigger ---
print("[App] Setting up user input fields.", flush=True)
# Use session state to keep ticker input if app re-runs due to other interactions
if 'ticker_input_value' not in st.session_state:
    st.session_state.ticker_input_value = "MSFT" # Default or last used

ticker_input_from_user = st.text_input(
    "Enter Stock Ticker (e.g., AAPL, MSFT):", 
    value=st.session_state.ticker_input_value,
    key="ticker_input_main_field"
).strip().upper()
st.session_state.ticker_input_value = ticker_input_from_user # Update session state on change


if st.button("Generate Full AI Stock Report", key="generate_report_button_main"):
    if ticker_input_from_user: # Basic check that something is entered
        if llm_handler_instance and llm_handler_instance.is_configured(): # Check if LLM is ready
            print(f"[App Button] 'Generate Report' clicked for ticker: {ticker_input_from_user}", flush=True)
            run_report_generation_orchestration(ticker_input_from_user)
        else:
            st.error("LLM Service not ready. Please check API key and logs.")
            print("[App Button] LLM not ready when button clicked.", flush=True)
    else:
        st.warning("Please enter a stock ticker symbol to generate a report.")
        print("[App Button] No ticker entered.", flush=True)

print("[App] Reached end of app.py script execution or awaiting interaction.", flush=True)