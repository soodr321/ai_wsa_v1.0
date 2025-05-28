# report_generator.py
import textwrap
import re 

# --- Section 1: Executive Summary (REVISED FOR FVE AGENT) ---
def generate_section_1_exec_summary(
    ticker: str, 
    company_info: dict, 
    quote_data: dict, 
    llm_handler_generate: callable,
    current_stock_price: float | None, 
    calculated_fve_from_agent: float | None, 
    fve_method_used_by_agent: str | None 
) -> str:
    """
    Generates the Executive Summary / Snapshot section (Section 1).
    Uses FVE and method from FVEAgent as input. LLM determines stock rating.
    """
    print(f"-> RG: Generating Section 1: Executive Summary for {ticker} using Agent FVE...")

    company_name = company_info.get('longName', ticker)
    sector = company_info.get('sector', 'N/A')
    industry = company_info.get('industry', 'N/A')
    
    price_str = f"${current_stock_price:.2f}" if current_stock_price is not None else "N/A"
    agent_fve_str = f"${calculated_fve_from_agent:.2f}" if calculated_fve_from_agent is not None else "Not Calculated"
    
    price_fve_ratio_str = "N/A"
    if current_stock_price is not None and calculated_fve_from_agent is not None and calculated_fve_from_agent > 0:
        price_fve_ratio = current_stock_price / calculated_fve_from_agent
        price_fve_ratio_str = f"{price_fve_ratio:.2f}"

    market_cap = quote_data.get('marketCap', 'N/A') # quote_data is from fve_input_data which should have this
    pe_ratio = quote_data.get('trailingPE', 'N/A')
    # Assuming dividendYield_pct might come from quote_data via fve_input_data or original quote_data fetch
    dividend_yield_raw = quote_data.get('dividendYield') # Check if key from fve_input_data/get_quote_data is different
    if dividend_yield_raw is None: # Fallback check if 'dividendYield_pct' was the key used in your V1.0 fetcher
        dividend_yield_raw = quote_data.get('dividendYield_pct')
        
    dividend_yield_str = f"{dividend_yield_raw:.2f}%" if isinstance(dividend_yield_raw, (int, float)) else "N/A"
    
    market_cap_str = "N/A"
    if isinstance(market_cap, (int, float)):
      if market_cap >= 1e12: market_cap_str = f"${market_cap / 1e12:.2f} Trillion"
      elif market_cap >= 1e9: market_cap_str = f"${market_cap / 1e9:.2f} Billion"
      elif market_cap >= 1e6: market_cap_str = f"${market_cap / 1e6:.2f} Million"
      else: market_cap_str = f"${market_cap:,.0f}"

    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Generate ONLY the 'Executive Summary / Snapshot' for {company_name} ({ticker}).

        **Company & Market Context:**
        *   Company: {company_name} ({ticker}), Sector: {sector}, Industry: {industry}
        *   Current Stock Price: {price_str}
        *   Market Capitalization: {market_cap_str}
        *   P/E Ratio (Trailing): {pe_ratio if pe_ratio is not None else 'N/A'}
        *   Dividend Yield: {dividend_yield_str}

        **Valuation Agent Output (Key Inputs for Your Summary):**
        *   Independently Calculated Fair Value Estimate (FVE) by our agent: **{agent_fve_str}**
        *   Primary Methodology used by Agent for this FVE: **{fve_method_used_by_agent or 'Not specified'}**
        *   Calculated Price/FVE Ratio (Current Price / Agent's FVE): **{price_fve_ratio_str}**

        **Your Task & Required Output Structure:**
        Based on ALL information above, generate an Executive Summary. It MUST include:
        1.  **Header:** "{company_name} ({ticker})".
        2.  **Your Stock Rating:** Based on your analysis of the provided data (especially the Agent's FVE vs. Current Price), determine a stock rating (e.g., Strong Buy, Buy, Hold, Sell, Strong Sell).
        3.  **Agent's FVE Restatement:** Clearly state the agent's FVE: {agent_fve_str}.
        4.  **Price/FVE Ratio Restatement:** State the Price/FVE ratio: {price_fve_ratio_str}.
        5.  **Economic Moat Assessment:** Briefly assess the company's economic moat (e.g., None, Narrow, Wide), using your general knowledge.
        6.  **Summary Table/Bullets:** Include a *standard markdown table* or bulleted list summarizing: Your Stock Rating, Agent FVE, Current Price, Price/FVE Ratio.
            *Example Markdown Table:*
            | Metric          | Value     |
            |-----------------|-----------|
            | Stock Rating    | [Your Rating] |
            | Agent FVE       | {agent_fve_str} |
            | Current Price   | {price_str} |
            | Price/FVE Ratio | {price_fve_ratio_str} |
        7.  **Brief Rationale (1-2 sentences):** Explain YOUR stock rating, referencing the agent's FVE vs. current price.

        **Constraint:** Start response directly with analysis text (the header "{company_name} ({ticker})"). NO other preamble.
        **Crucial for Parsing - Output your rating like this:**
        **Overall Rating:** [Your Actual Rating Here e.g., Buy]
    """)
    
    try:
        generated_text = llm_handler_generate(prompt)
        # print(f"\nDEBUG RG S1: Raw LLM Output:\n>>>\n{generated_text}\n<<<\n") # Keep for debugging
        if generated_text is None or not generated_text.strip():
             print("RG Error: LLM returned empty for S1.")
             return "## 1. Executive Summary / Snapshot\n\nError: Failed to generate content (LLM response empty/None).\n"
        # No specific Python cleanup, rely on prompt for good formatting
        cleaned_text = generated_text 
    except Exception as e:
        print(f"RG Error during LLM call for S1: {e}")
        return f"## 1. Executive Summary / Snapshot\n\nError generating content: {e}\n"

    section_content = f"## 1. Executive Summary / Snapshot\n\n{cleaned_text.strip()}\n"
    print(f"<- RG: Section 1 generated successfully for {ticker}.")
    return section_content

# --- Section 9: Conclusion & Recommendation (REVISED FOR FVE AGENT) ---
def generate_section_9_conclusion_recommendation(
    ticker: str,
    company_info: dict,
    quote_data: dict, 
    llm_handler_generate: callable,
    fve_value: float | None,        # This is agent_fve from app.py
    rating_value: str | None,       # This is parsed_rating_s1 from app.py
    fve_method_used: str | None     # Method used by FVEAgent
) -> str:
    """
    Generates the Conclusion & Investment Thesis section (Section 9).
    Takes FVE and Rating directly as arguments for consistency.
    """
    print(f"-> RG: Generating Section 9: Conclusion for {ticker} (FVE: {fve_value}, Rating: {rating_value})...")

    company_name = company_info.get('longName', ticker)
    current_price = quote_data.get('currentPrice') # For context
    price_context_str = f" (Current Price context: ${current_price:.2f})" if current_price is not None else ""
    
    fve_display_str = f"${fve_value:.2f}" if fve_value is not None else "Not determined by valuation agent"
    rating_display_str = rating_value if rating_value else "Not explicitly rated in summary"
    method_context_str = f" (derived via {fve_method_used})" if fve_method_used else ""

    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Generate ONLY the 'Conclusion & Investment Thesis' section for {company_name} ({ticker}).

        **Key Inputs for this Conclusion (Previously Determined in Report):**
        *   Fair Value Estimate (FVE) by our valuation agent: **{fve_display_str}**{method_context_str}
        *   Overall Stock Rating from Executive Summary: **{rating_display_str}**
        *   Context: Current Stock Price is approximately {price_context_str}.

        **Your Task:**
        Based on these key inputs and synthesizing the overall analysis performed (business, strategy, financials, risks), generate the 'Conclusion & Investment Thesis'. It MUST:
        1.  Provide a concise summary of your overall investment thesis for {company_name} (1-2 paragraphs).
        2.  Clearly **restate** the Fair Value Estimate (FVE): **{fve_display_str}**.
        3.  Clearly **restate** the Overall Stock Rating: **{rating_display_str}**.
        4.  Offer a brief final thought or outlook.

        **Constraint:** Start response directly with analysis text. NO section header.
        **Output Format:** Professional, conclusive tone. Standard paragraphs.
    """)

    try:
        generated_text = llm_handler_generate(prompt)
        # print(f"\nDEBUG RG S9: Raw LLM Output:\n>>>\n{generated_text}\n<<<\n")
        if generated_text is None or not generated_text.strip():
            print("RG Error: LLM returned empty for S9.")
            return "## 9. Conclusion & Investment Thesis\n\nError: Failed to generate content (LLM response empty/None).\n"
        cleaned_text = generated_text
    except Exception as e:
        print(f"RG Error during LLM call for S9: {e}")
        return f"## 9. Conclusion & Investment Thesis\n\nError generating content: {e}\n"

    section_content = f"## 9. Conclusion & Investment Thesis\n\n{cleaned_text.strip()}\n"
    print(f"<- RG: Section 9 generated successfully for {ticker}.")
    return section_content

# --- OTHER SECTIONS (2-8, 10 - Assuming V1.0 versions are mostly fine for now) ---
# Copied from your provided version, with minor print statement updates for RG prefix.

def generate_section_2_business_description(ticker: str, company_info: dict, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 2: Business Description for {ticker}...")
    company_name = company_info.get('longName', ticker); summary = company_info.get('longBusinessSummary', 'N/A')
    sector = company_info.get('sector', 'N/A'); industry = company_info.get('industry', 'N/A')
    if summary == 'N/A' or not summary: 
        print(f"RG Warning: 'longBusinessSummary' missing for S2 of {ticker}.")
        return f"## 2. Business Description\n\nError: Company business summary not available for {ticker}.\n"
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Business Description' for {company_name} ({ticker}), Sector: {sector}, Industry: {industry}. Provided Summary: --- {summary} ---. Instructions: Based primarily on summary: 1. Concise overview. 2. Key products/services/markets if in summary. 3. Competitors ONLY if in summary. 4. Factual tone. 5. Normal paragraphs. Constraint: ONLY section content, no header. Start directly with text.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S2."); return "## 2. Business Description\n\nError: LLM response empty.\n"
        return f"## 2. Business Description\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S2: {e}"); return f"## 2. Business Description\n\nError: {e}\n"

def generate_section_3_strategy_outlook(ticker: str, company_info: dict, news: list, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 3: Strategy & Outlook for {ticker}...")
    company_name = company_info.get('longName', ticker); summary = company_info.get('longBusinessSummary', 'N/A')
    news_h = [item.get('title', 'N/A') for item in news[:5] if item.get('title')]; news_str = "Recent News:\n" + "\n".join([f"- {h}" for h in news_h]) if news_h else "No recent news headlines provided."
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Business Strategy & Outlook' for {company_name} ({ticker}). Summary (context): {summary if summary != 'N/A' else 'Not available.'}. {news_str}. Instructions: Based on summary, news, general knowledge: 1. Likely strategy. 2. Industry trends & positioning. 3. Growth drivers. 4. Challenges/risks. 5. Insights from news if relevant. Analytical, forward-looking. Constraint: ONLY section content, no header.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S3."); return "## 3. Business Strategy & Outlook\n\nError: LLM response empty.\n"
        return f"## 3. Business Strategy & Outlook\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S3: {e}"); return f"## 3. Business Strategy & Outlook\n\nError: {e}\n"

def generate_section_4_economic_moat(ticker: str, company_info: dict, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 4: Economic Moat for {ticker}...")
    company_name = company_info.get('longName', ticker); summary = company_info.get('longBusinessSummary', 'N/A')
    sum_ctx = f"Business Summary (context): {summary}" if summary != 'N/A' else "Business summary not available. Base analysis on general knowledge."
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Economic Moat Analysis' for {company_name} ({ticker}). {sum_ctx}. Instructions: Based on summary (if any) & general knowledge: 1. Analyze competitive advantages (network effects, switching costs, intangibles, cost adv., efficient scale). 2. Identify moat sources. 3. Comment on moat sustainability (widening, narrowing, stable). Focus on *reasons*, do NOT state a final moat rating here. Constraint: ONLY section content, no header.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S4."); return "## 4. Economic Moat Analysis\n\nError: LLM response empty.\n"
        return f"## 4. Economic Moat Analysis\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S4: {e}"); return f"## 4. Economic Moat Analysis\n\nError: {e}\n"

def generate_section_5_financial_analysis(ticker: str, company_info: dict, financial_summary: dict, news: list, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 5: Financial Analysis for {ticker}...")
    company_name = company_info.get('longName', ticker)
    revenue = financial_summary.get('latest_annual_revenue'); earnings = financial_summary.get('latest_annual_earnings'); fin_year = financial_summary.get('financials_year', 'N/A')
    rev_str = f"${revenue:,.0f}" if revenue is not None else "N/A"; earn_str = f"${earnings:,.0f}" if earnings is not None else "N/A"
    news_h = [item.get('title', 'N/A') for item in news[:3] if item.get('title')]; news_str = "News:\n"+"\n".join([f"- {h}" for h in news_h]) if news_h else "No news."
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Financial Analysis' for {company_name} ({ticker}). Financials (Year: {fin_year}): Revenue: {rev_str}, Earnings: {earn_str}. {news_str}. Instructions: Based on data, news, general knowledge: 1. Analyze recent financial performance. 2. Qualitative commentary on profitability/margins. 3. Perception of balance sheet/cash flow. 4. Key financial takeaways. Concise (2-4 paras). Constraint: ONLY section content, no header. IMPORTANT: Use correct spacing for numbers and words.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S5."); return "## 5. Financial Analysis\n\nError: LLM response empty.\n"
        return f"## 5. Financial Analysis\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S5: {e}"); return f"## 5. Financial Analysis\n\nError: {e}\n"

def generate_section_6_valuation(ticker: str, company_info: dict, quote_data: dict, llm_handler_generate: callable) -> str:
    # This section is now more of a general discussion as FVEAgent handles specific valuation.
    # Prompt should be adjusted to reflect it's not calculating an FVE here.
    print(f"-> RG: Generating Section 6: Valuation Discussion for {ticker}...")
    company_name = company_info.get('longName', ticker)
    trailing_pe = quote_data.get('trailingPE', 'N/A'); forward_pe = quote_data.get('forwardPE', 'N/A')
    pe_context = f"Context: Trailing P/E: {trailing_pe if trailing_pe else 'N/A'}, Forward P/E: {forward_pe if forward_pe else 'N/A'}."
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Valuation Discussion' for {company_name} ({ticker}). {pe_context} Instructions: 1. Briefly explain that detailed valuation (DCF/Multiples) is covered elsewhere. 2. Discuss general valuation considerations for this type of company. 3. Comment on what the provided P/E ratios might generally indicate about market perception or growth expectations, without stating a new FVE. 4. Mention key factors typically influencing its valuation. Constraint: ONLY section content, no header. Do NOT provide a specific FVE.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S6."); return "## 6. Valuation Discussion\n\nError: LLM response empty.\n"
        return f"## 6. Valuation Discussion\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S6: {e}"); return f"## 6. Valuation Discussion\n\nError: {e}\n"

def generate_section_7_risk_uncertainty(ticker: str, company_info: dict, news: list, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 7: Risk & Uncertainty for {ticker}...")
    company_name = company_info.get('longName', ticker)
    news_h = [item.get('title', 'N/A') for item in news[:5] if item.get('title')]; news_str = "News context:\n" + "\n".join([f"- {h}" for h in news_h]) if news_h else "No specific recent news headlines provided for context."
    prompt = textwrap.dedent(f"Act as Analyst. Generate 'Risk and Uncertainty Assessment' for {company_name} ({ticker}). {news_str}. Instructions: Based on news (if any) and general knowledge: 1. Identify key risks (categorize: Business-Specific, Market, Technological, Regulatory). 2. Briefly explain potential impact of 2-3 most significant risks. 3. Qualitatively assess overall uncertainty (Low/Med/High) & justify. Use bullets for risks if suitable. Constraint: ONLY section content, no header.")
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S7."); return "## 7. Risk and Uncertainty Assessment\n\nError: LLM response empty.\n"
        return f"## 7. Risk and Uncertainty Assessment\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S7: {e}"); return f"## 7. Risk and Uncertainty Assessment\n\nError: {e}\n"

def generate_section_8_bulls_bears(ticker: str, company_info: dict, quote_data: dict, financial_summary: dict, news: list, llm_handler_generate: callable) -> str:
    print(f"-> RG: Generating Section 8: Bulls Say / Bears Say for {ticker}...")
    company_name = company_info.get('longName', ticker)
    # Adding more context for Bulls/Bears summary
    current_price = quote_data.get('currentPrice', 'N/A')
    pe_ratio = quote_data.get('trailingPE', 'N/A')
    revenue = financial_summary.get('latest_annual_revenue')
    rev_str = f"${revenue:,.0f}" if revenue is not None else "N/A"
    context_summary = f"Current Price: ${current_price if current_price else 'N/A'}, Trailing P/E: {pe_ratio if pe_ratio else 'N/A'}, Recent Revenue: {rev_str}."

    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Generate ONLY the 'Bulls Say / Bears Say' section for {company_name} ({ticker}).
        Contextual Snapshot: {context_summary}
        Instructions: Synthesizing the overall analysis context (business, strategy, moat, financials, general valuation perception from P/E, risks), generate:
        1.  `**Bulls Say:**` (header) followed by 2-3 concise bullet points of key positive arguments.
        2.  `**Bears Say:**` (header) followed by 2-3 concise bullet points of key negative arguments/risks.
        Start response directly with `**Bulls Say:**`. Constraint: ONLY this section's content, no main header.
    """)
    try:
        txt = llm_handler_generate(prompt)
        if not txt or not txt.strip(): print("RG Warning: LLM returned empty for S8."); return "## 8. Bulls Say / Bears Say\n\nError: LLM response empty.\n"
        # Basic check for structure, though LLM might vary
        if "**Bulls Say:**" not in txt or "**Bears Say:**" not in txt: 
            print("RG Warning: S8 LLM output might be missing standard 'Bulls Say' or 'Bears Say' sub-headers. Using raw output.")
        return f"## 8. Bulls Say / Bears Say\n\n{txt.strip()}\n"
    except Exception as e: print(f"RG Error S8: {e}"); return f"## 8. Bulls Say / Bears Say\n\nError: {e}\n"

def generate_section_10_references() -> str:
    print("-> RG: Generating Section 10: References (Static)...")
    references_content = textwrap.dedent("""\
        ## 10. References

        *   Financial data primarily sourced from Yahoo Finance via the `yfinance` library.
        *   Valuation, analysis, and narrative content generated with assistance from Google Gemini Large Language Models.
        *   Disclaimer: This report is a Proof of Concept generated by an AI and should not be considered financial advice. Always conduct your own thorough research.
    """)
    return references_content + "\n"

def assemble_report(ticker: str, company_name: str, all_sections: list[str]) -> str:
    print(f"-> RG: Assembling final report for {ticker}...")
    if not company_name or not isinstance(company_name, str): company_name = ticker
    report_title = f"# Equity Research Report: {company_name} ({ticker.upper()})\n\n"
    # Each section should already end with a newline. Join them with one additional newline for spacing.
    report_body = "\n".join(all_sections) 
    print(f"<- RG: Report assembly completed for {ticker}.")
    return report_title + report_body