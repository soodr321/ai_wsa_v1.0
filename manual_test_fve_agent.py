# manual_test_fve_agent.py
import os
import copy 
from dotenv import load_dotenv

from data_fetcher import StockDataFetcher
from llm_handler import LLMHandler 
from fve_agent import FVEAgent, MIN_KE_G_SPREAD_DEFAULT 

def run_agent_test(ticker_symbol: str,fve_input_data_to_use: dict,llm_function_to_use,rfr: float = 0.04,erp: float = 0.05,stage1_years_dcf: int = 3,min_ke_g_spread_decimal_override: float | None = None, 
                   debug_agent: bool = True,test_scenario_name: str = "Default Test"):
    print(f"\n--- Starting FVE Agent Test for Ticker: {ticker_symbol.upper()} (Scenario: {test_scenario_name}) ---")
    if not fve_input_data_to_use: print(f"No input data for {ticker_symbol}. Aborting."); return
    
    agent_min_ke_g_spread = min_ke_g_spread_decimal_override if min_ke_g_spread_decimal_override is not None else MIN_KE_G_SPREAD_DEFAULT

    fve_agent_instance = FVEAgent(llm_generate_text_func=llm_function_to_use,rfr=rfr,erp=erp,stage1_years=stage1_years_dcf,
                                  min_ke_g_spread=agent_min_ke_g_spread, 
                                  debug_mode=debug_agent)
    calculated_fve=None;methodology_text="Methodology not generated due to pre-run error."
    try: calculated_fve,methodology_text = fve_agent_instance.run_valuation_process(fve_input_data_to_use)
    except Exception as e:
        print(f"ERROR during FVEAgent.run_valuation_process for {ticker_symbol} ({test_scenario_name}): {e}")
        if debug_agent:print(f"DCF Fail: {fve_agent_instance.dcf_failure_reason}, Multiples Fail: {fve_agent_instance.multiples_failure_reason}")
        return
    print(f"\n--- FVE AGENT TEST RESULTS ---");print(f"Ticker: {ticker_symbol.upper()} (Scenario: {test_scenario_name})");print(f"Calculated FVE: {calculated_fve}");print(f"Method Used: {fve_agent_instance.method_used}")
    if fve_agent_instance.dcf_failure_reason: print(f"DCF Failure Reason: {fve_agent_instance.dcf_failure_reason}")
    if fve_agent_instance.multiples_failure_reason: print(f"Multiples Failure Reason: {fve_agent_instance.multiples_failure_reason}")
    print(f"\nMethodology Text:\n----------------------------------------------------\n{methodology_text}\n----------------------------------------------------")
    if debug_agent:
        print("\n--- Agent's Internal State ---");print(f"Base FCFE_0: {fve_agent_instance.base_fcfe_0}")
        print("DCF Assumptions:");[print(f"  {k}: {v if 'just' not in k and not isinstance(v, list) or (isinstance(v,list) and len(v) < 6) else (str(v)[:60]+'...' if isinstance(v, list) else ('Present' if v and v!='NG' else 'NG')) }") for k,v in fve_agent_instance.dcf_assumptions.items()] # Truncate long lists for summary
        print("Multiples Assumptions:");[print(f"  {k}: {v if 'just' not in k else('Present' if v and v!='NG' else 'NG')}") for k,v in fve_agent_instance.multiples_assumptions.items()]
        print("--- End of Debug State ---")
    print(f"\n--- Test for {ticker_symbol.upper()} ({test_scenario_name}) COMPLETED ---")

if __name__ == "__main__":
    load_dotenv()
    llm_model_name = "gemini-1.5-flash-latest"; actual_llm_function = None; llm_handler_initialized = False
    try:
        llm_handler = LLMHandler(model_name=llm_model_name)
        if llm_handler.is_configured() and llm_handler.model:
            actual_llm_function = llm_handler.generate_text; print(f"LLM Handler OK: {llm_model_name}"); llm_handler_initialized = True
        else: print("CRITICAL: LLMHandler failed config/model init.")
    except Exception as e: print(f"CRITICAL: LLMHandler init failed: {e}")
    if not llm_handler_initialized: print("Aborting tests: LLM not available."); exit()

    PRIMARY_TICKER = "MSFT"
    RFR_BASELINE = 0.042 
    ERP_ADJUSTED = 0.045 
    STAGE1_YEARS_EXTENDED = 5
    DEBUG_MODE = True

    print(f"\nFetching BASE data for primary ticker: {PRIMARY_TICKER.upper()}...")
    base_fve_input_data = None
    try:
        fetcher = StockDataFetcher(ticker=PRIMARY_TICKER, historical_years=5) 
        base_fve_input_data = fetcher.get_fve_inputs()
        if not base_fve_input_data: print(f"CRITICAL: Failed to fetch base data for {PRIMARY_TICKER}.")
        else: print(f"Base data fetched for {PRIMARY_TICKER.upper()}.\n")
    except Exception as e: print(f"CRITICAL: Error fetching base data for {PRIMARY_TICKER}: {e}.")
    if not base_fve_input_data: print("Exiting: Base data fetch failed."); exit()

    # --- Test Scenario 1: Adjusted DCF Parameters ---
    run_agent_test(
        ticker_symbol=PRIMARY_TICKER,
        fve_input_data_to_use=copy.deepcopy(base_fve_input_data),
        llm_function_to_use=actual_llm_function,
        rfr=RFR_BASELINE, erp=ERP_ADJUSTED, stage1_years_dcf=STAGE1_YEARS_EXTENDED,
        debug_agent=DEBUG_MODE,
        test_scenario_name=f"MSFT DCF (ERP {ERP_ADJUSTED*100:.1f}%, {STAGE1_YEARS_EXTENDED}-Yr Growth)"
    )
    
    # --- Test Scenario 2: DCF Fail (Beta None) -> Multiples (with adjusted ERP & Stage 1 for context if it were to run DCF) ---
    if base_fve_input_data:
        data_for_missing_beta = copy.deepcopy(base_fve_input_data)
        data_for_missing_beta['beta'] = None 
        run_agent_test(ticker_symbol=PRIMARY_TICKER, fve_input_data_to_use=data_for_missing_beta, llm_function_to_use=actual_llm_function,rfr=RFR_BASELINE, erp=ERP_ADJUSTED, stage1_years_dcf=STAGE1_YEARS_EXTENDED,debug_agent=DEBUG_MODE,test_scenario_name="DCF Fail (Beta None) -> Multiples")

    # --- Test Scenario 3: DCF Fail (FCFE0 Calc), Multiples Fallback ---
    if base_fve_input_data:
        data_for_missing_ni = copy.deepcopy(base_fve_input_data)
        if 'historical_financials' in data_for_missing_ni and 'netIncome_list' in data_for_missing_ni['historical_financials'] and data_for_missing_ni['historical_financials']['netIncome_list']:
            data_for_missing_ni['historical_financials']['netIncome_list'][0] = None 
        else: print(f"Warning: Could not set Net Income to None for {PRIMARY_TICKER} test scenario 3.")
        run_agent_test(ticker_symbol=PRIMARY_TICKER, fve_input_data_to_use=data_for_missing_ni, llm_function_to_use=actual_llm_function,rfr=RFR_BASELINE,erp=ERP_ADJUSTED,stage1_years_dcf=STAGE1_YEARS_EXTENDED,debug_agent=DEBUG_MODE,test_scenario_name="DCF Fail (FCFE0 Calc) -> Multiples")

    # --- Test Scenario 4: Total Failure (Sparse Data like GC=F) ---
    print(f"\nFetching data for sparse data ticker for Total Failure test...")
    sparse_data_ticker = "GC=F"; sparse_fve_input_data = None
    try:
        fetcher_sparse = StockDataFetcher(ticker=sparse_data_ticker, historical_years=4)
        sparse_fve_input_data = fetcher_sparse.get_fve_inputs()
        if sparse_fve_input_data:
            sparse_fve_input_data['beta'] = None; sparse_fve_input_data['trailingPE'] = None; sparse_fve_input_data['forwardPE'] = None
            sparse_fve_input_data['trailingEps'] = None; sparse_fve_input_data['forwardEps'] = None
    except Exception as e: print(f"Note: Error fetching/modifying data for sparse ticker {sparse_data_ticker}: {e}")
    if sparse_fve_input_data:
        run_agent_test(ticker_symbol=sparse_data_ticker, fve_input_data_to_use=sparse_fve_input_data, llm_function_to_use=actual_llm_function,rfr=RFR_BASELINE, erp=ERP_ADJUSTED, stage1_years_dcf=STAGE1_YEARS_EXTENDED,debug_agent=DEBUG_MODE,test_scenario_name="Total Failure (Sparse Data)")
    else: print(f"Skipping 'Total Failure (Sparse Data)' test for {sparse_data_ticker} as data fetch/prep failed.")

    # --- Test Scenario 5: Multiples with Negative EPS (manipulated) ---
    if base_fve_input_data: 
        data_for_neg_eps = copy.deepcopy(base_fve_input_data)
        data_for_neg_eps['beta'] = None # Force DCF fail
        original_TEps = data_for_neg_eps['trailingEps'] # Store original for debug print
        data_for_neg_eps['trailingEps'] = -1.50
        data_for_neg_eps['forwardEps'] = -1.00 # Though LLM might ignore this if it estimates positive
        if data_for_neg_eps['trailingPE'] is None: data_for_neg_eps['trailingPE'] = 10.0 # Ensure some P/E exists
        if DEBUG_MODE: print(f"MANUAL_TEST DEBUG: For 'Multiples with Negative EPS' scenario, manipulated Trailing EPS from {original_TEps} to -1.50") # ChatGPT Point 3
        run_agent_test(ticker_symbol=PRIMARY_TICKER, fve_input_data_to_use=data_for_neg_eps,llm_function_to_use=actual_llm_function,rfr=RFR_BASELINE, erp=ERP_ADJUSTED, stage1_years_dcf=STAGE1_YEARS_EXTENDED,debug_agent=DEBUG_MODE,test_scenario_name="Multiples with Negative EPS")

    # --- Test Scenario 6: High Beta (e.g., 3.2) ---
    if base_fve_input_data:
        data_for_high_beta = copy.deepcopy(base_fve_input_data)
        data_for_high_beta['beta'] = 3.2 # High beta
        run_agent_test(
            ticker_symbol=PRIMARY_TICKER,
            fve_input_data_to_use=data_for_high_beta,
            llm_function_to_use=actual_llm_function,
            rfr=RFR_BASELINE, erp=ERP_ADJUSTED, stage1_years_dcf=STAGE1_YEARS_EXTENDED,
            debug_agent=DEBUG_MODE,
            test_scenario_name="DCF with High Beta (3.2)"
        )

    print("\n\n--- ALL MANUAL TESTS COMPLETED ---")