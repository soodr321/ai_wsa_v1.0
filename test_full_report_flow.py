# test_full_report_flow.py

import os
import traceback
import re # For parsing rating
from dotenv import load_dotenv

# Import your project modules
from llm_handler import LLMHandler
from data_fetcher import StockDataFetcher
from fve_agent import FVEAgent 
import report_generator as rg_funcs

# --- Configuration ---
RFR_APP = 0.045
ERP_APP = 0.045
STAGE1_YEARS_APP = 5
DEBUG_FVE_AGENT_IN_FLOW = True 
DEBUG_FLOW_SCRIPT = True     

# --- Helper Function for parsing rating ---
def parse_rating_from_s1_text_local(section_1_text: str) -> str | None:
    if DEBUG_FLOW_SCRIPT: print(f"[FlowTest Parser] Attempting to parse Rating from S1 (first 300 chars):\n'''{section_1_text[:300]}'''")
    rating_value = None
    patterns = [
        r"(?:Overall Rating|Investment Recommendation|Stock Rating)\s*[:\-is\s]*\s*(Strong Buy|Buy|Accumulate|Outperform|Overweight|Hold|Neutral|Equal-weight|Market Perform|Reduce|Underperform|Sell|Strong Sell)\b",
        r"\b(Strong Buy|Buy|Accumulate|Outperform|Overweight|Hold|Neutral|Equal-weight|Market Perform|Reduce|Underperform|Sell|Strong Sell)\b"
    ]
    for pattern in patterns:
        match = re.search(pattern, section_1_text, re.IGNORECASE)
        if match:
            rating_value = (match.group(1) or match.group(0)).strip().title() 
            if DEBUG_FLOW_SCRIPT: print(f"[FlowTest Parser] Parsed Rating using pattern: '{rating_value}'")
            break 
    if not rating_value and DEBUG_FLOW_SCRIPT: print("[FlowTest Parser] Rating not found or parsed from S1.")
    return rating_value

def run_full_report_flow_for_ticker(ticker_symbol: str):
    print(f"\n\n--- RUNNING FULL REPORT FLOW TEST FOR: {ticker_symbol.upper()} ---")
    
    if DEBUG_FLOW_SCRIPT: print("Initializing LLMHandler...")
    llm_handler = LLMHandler(model_name="gemini-1.5-flash-latest")
    if not llm_handler.is_configured() or not llm_handler.model:
        print("CRITICAL: LLMHandler failed to configure. Aborting flow test.")
        return
    llm_func = llm_handler.generate_text
    if DEBUG_FLOW_SCRIPT: print("LLMHandler initialized and configured.")

    if DEBUG_FLOW_SCRIPT: print(f"Fetching data for {ticker_symbol}...")
    fve_input_data = None
    fetcher = None
    company_info_for_sections = None # For general company details
    
    try:
        fetcher = StockDataFetcher(ticker_symbol, historical_years=STAGE1_YEARS_APP)
        fve_input_data = fetcher.get_fve_inputs() 
        company_info_for_sections = fetcher.get_company_info() # Explicitly get full company_info
        
        # More robust check: Ensure both critical data structures are populated
        if not fve_input_data or not fve_input_data.get('companyName'): 
            print(f"Failed to get essential fve_input_data for {ticker_symbol}. Aborting flow test.")
            return
        if not company_info_for_sections or not company_info_for_sections.get('longBusinessSummary'):
             # This check specifically addresses the S2 issue if longBusinessSummary is vital
            print(f"Warning: 'longBusinessSummary' missing in company_info_for_sections for {ticker_symbol}. Some report sections may be impacted.")
            # We can decide to proceed or abort based on how critical this is for *all* sections
            # For now, let's proceed but be aware S2 might generate an error message from rg_funcs

        if DEBUG_FLOW_SCRIPT: print(f"Data fetched for {ticker_symbol}.")
    except Exception as e:
        print(f"Data fetching failed for {ticker_symbol}: {e}. Aborting flow test.")
        traceback.print_exc()
        return
        
    company_name_for_title = fve_input_data.get('companyName', ticker_symbol)
    current_price = fve_input_data.get('currentPrice')

    if DEBUG_FLOW_SCRIPT: print(f"Instantiating and running FVEAgent for {ticker_symbol}...")
    fve_agent = FVEAgent(
        llm_generate_text_func=llm_func,
        rfr=RFR_APP, erp=ERP_APP, stage1_years=STAGE1_YEARS_APP,
        debug_mode=DEBUG_FVE_AGENT_IN_FLOW
    )
    agent_fve, agent_methodology_text = fve_agent.run_valuation_process(fve_input_data)
    if DEBUG_FLOW_SCRIPT: print(f"Flow Test - FVEAgent Results: FVE={agent_fve}, Method Used='{fve_agent.method_used}', DCF Fail='{fve_agent.dcf_failure_reason}', Multiples Fail='{fve_agent.multiples_failure_reason}'")

    # Prepare data for other report sections
    quote_data_for_rg = fve_input_data # Contains necessary quote items like P/E, currentPrice etc.
    news_for_rg = fve_input_data.get('news', [])
    hist_fin_for_rg = fve_input_data.get('historical_financials', {})
    financial_summary_for_rg = { # Simplified for V1.0 rg_funcs compatibility
        "latest_annual_earnings": hist_fin_for_rg.get('netIncome_list', [None])[0],
        "latest_annual_revenue": hist_fin_for_rg.get('totalRevenue_list', [None])[0],
        "financials_year": hist_fin_for_rg.get('years', ["N/A"])[0]
    }

    all_sections_content_test = []
    try:
        if DEBUG_FLOW_SCRIPT: print("\nGenerating Section 1: Executive Summary...")
        s1_text = rg_funcs.generate_section_1_exec_summary(
            ticker_symbol, 
            company_info_for_sections, # *** USE THE FULL company_info_for_sections HERE ***
            quote_data_for_rg, 
            llm_func,
            current_stock_price=current_price,
            calculated_fve_from_agent=agent_fve,
            fve_method_used_by_agent=fve_agent.method_used
        )
        all_sections_content_test.append(s1_text)
        parsed_rating_s1 = parse_rating_from_s1_text_local(s1_text)
        if DEBUG_FLOW_SCRIPT: print(f"Flow Test - S1 Generated. Parsed Rating: {parsed_rating_s1}")

        methodology_section_header = "## Valuation Methodology Deep Dive"
        all_sections_content_test.append(f"\n{methodology_section_header}\n\n{agent_methodology_text}\n\n---")
        if DEBUG_FLOW_SCRIPT: print("Flow Test - Added FVE Agent Methodology Text to report sections.")

        section_generators = {
            "2: Business Description": lambda: rg_funcs.generate_section_2_business_description(ticker_symbol, company_info_for_sections, llm_func),
            "3: Strategy & Outlook": lambda: rg_funcs.generate_section_3_strategy_outlook(ticker_symbol, company_info_for_sections, news_for_rg, llm_func),
            "4: Economic Moat": lambda: rg_funcs.generate_section_4_economic_moat(ticker_symbol, company_info_for_sections, llm_func),
            "5: Financial Analysis": lambda: rg_funcs.generate_section_5_financial_analysis(ticker_symbol, company_info_for_sections, financial_summary_for_rg, news_for_rg, llm_func),
            "6: Valuation Discussion": lambda: rg_funcs.generate_section_6_valuation(ticker_symbol, company_info_for_sections, quote_data_for_rg, llm_func),
            "7: Risk & Uncertainty": lambda: rg_funcs.generate_section_7_risk_uncertainty(ticker_symbol, company_info_for_sections, news_for_rg, llm_func),
            "8: Bulls Say / Bears Say": lambda: rg_funcs.generate_section_8_bulls_bears(ticker_symbol, company_info_for_sections, quote_data_for_rg, financial_summary_for_rg, news_for_rg, llm_func),
        }
        
        for name, func in section_generators.items():
            if DEBUG_FLOW_SCRIPT: print(f"Generating Section {name}...")
            # Ensure company_info_for_sections is passed if the function expects a full company_info dict
            all_sections_content_test.append(func()) 
            if DEBUG_FLOW_SCRIPT: print(f"Flow Test - Section {name} Generated.")
        
        if DEBUG_FLOW_SCRIPT: print("Generating Section 9: Conclusion...")
        all_sections_content_test.append(rg_funcs.generate_section_9_conclusion_recommendation(
            ticker_symbol, 
            company_info_for_sections, # *** USE THE FULL company_info_for_sections HERE ***
            quote_data_for_rg, 
            llm_func,
            fve_value=agent_fve,
            rating_value=parsed_rating_s1,
            fve_method_used=fve_agent.method_used
        ))
        if DEBUG_FLOW_SCRIPT: print("Flow Test - Section 9 Generated.")

        if DEBUG_FLOW_SCRIPT: print("Generating Section 10: References...")
        all_sections_content_test.append(rg_funcs.generate_section_10_references())
        if DEBUG_FLOW_SCRIPT: print("Flow Test - Section 10 Generated.")

        final_report_md_test = rg_funcs.assemble_report(ticker_symbol, company_name_for_title, all_sections_content_test)
        
        print("\n\n--- FULL REPORT FLOW TEST - FINAL MARKDOWN OUTPUT ---")
        print(final_report_md_test) 
        print("--- END OF FULL REPORT FLOW TEST MARKDOWN ---")
        print(f"\nFull report flow test for {ticker_symbol} COMPLETED.")

    except Exception as e:
        print(f"ERROR during report section generation for {ticker_symbol}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    load_dotenv() 
    tickers_to_test_flow = ["MSFT"] 
    # tickers_to_test_flow = ["MSFT", "AAPL", "GC=F"] # For more comprehensive testing
    
    for ticker in tickers_to_test_flow:
        run_full_report_flow_for_ticker(ticker)
        print("\n" + "="*70 + "\n") 
    print("--- ALL SCRIPTED FLOW TESTS COMPLETED ---")