import textwrap
import re # Keep import just in case needed later, but not used now

def generate_section_1_exec_summary(ticker: str, company_info: dict, quote_data: dict, llm_handler_generate: callable) -> str:
    """
    Generates the Executive Summary / Snapshot section (Section 1).
    NO Python cleanup applied post-LLM. Relies on prompt for formatting.
    """
    print(f"-> Generating Section 1: Executive Summary for {ticker}...")

    # --- Construct the Prompt ---
    # (Using the last version of the prompt which seemed effective)
    company_name = company_info.get('longName', ticker)
    sector = company_info.get('sector', 'N/A')
    industry = company_info.get('industry', 'N/A')
    current_price = quote_data.get('currentPrice', 'N/A')
    market_cap = quote_data.get('marketCap', 'N/A')
    pe_ratio = quote_data.get('trailingPE', 'N/A')
    dividend_yield = quote_data.get('dividendYield_pct', 'N/A')

    if isinstance(dividend_yield, (int, float)) and dividend_yield != 'N/A':
         dividend_yield_str = f"{dividend_yield:.2f}%"
    else:
         dividend_yield_str = "N/A"

    if isinstance(market_cap, (int, float)) and market_cap != 'N/A':
      if market_cap >= 1e12: market_cap_str = f"${market_cap / 1e12:.2f} Trillion"
      elif market_cap >= 1e9: market_cap_str = f"${market_cap / 1e9:.2f} Billion"
      elif market_cap >= 1e6: market_cap_str = f"${market_cap / 1e6:.2f} Million"
      else: market_cap_str = f"${market_cap:,.0f}"
    else: market_cap_str = "N/A"

    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Executive Summary / Snapshot' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})
        **Sector:** {sector}
        **Industry:** {industry}

        **Key Data Points:**
        *   Current Stock Price: ${current_price}
        *   Market Capitalization: {market_cap_str}
        *   P/E Ratio (Trailing): {pe_ratio if pe_ratio else 'N/A'}
        *   Dividend Yield: {dividend_yield_str}

        **Instructions:**
        Based *only* on the data provided above and your general knowledge of financial analysis, generate the Executive Summary / Snapshot section. This section MUST include the following elements, clearly formatted:
        1.  **Company/Ticker Header:** Start with "{company_name} ({ticker})".
        2.  **Concise Stock Rating:** Provide a rating (e.g., Buy, Hold, Sell).
        3.  **Fair Value Estimate (FVE):** Provide a *single* numeric fair value per share (e.g., $150.00).
        4.  **Price/FVE Ratio:** Calculate and state the ratio of Current Price (${current_price}) to *your* FVE.
        5.  **Economic Moat Assessment:** Assess the company's economic moat (e.g., None, Narrow, Wide).
        6.  **Summary Table/Bullets:** Include a small *standard* markdown table or bulleted list summarizing key metrics... **Use correct markdown format like:\n| Header | Value |\n|---|---|\n| Data | Data |\nfor tables.**
        7.  **Brief Rationale:** Add 1-2 sentences briefly explaining the rationale behind your rating and FVE.

        **Constraint:** Generate *ONLY* the content required for this "Executive Summary / Snapshot" section. Do *not* include the header '## 1. Executive Summary / Snapshot' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text... Ensure any tables use standard markdown formatting **without extra characters like `|` within cells.**
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        print(f"\nDEBUG: Raw LLM Output (Section 1):\n>>>\n{generated_text}\n<<<\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation failed for Section 1.")
             return "## 1. Executive Summary / Snapshot\\n\\nError: Failed to generate content for this section.\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 1.")
             return "## 1. Executive Summary / Snapshot\\n\\nError: Failed to generate content for this section (empty response received).\\n"

        # ----- CLEANUP BLOCK REMOVED -----
        print("-> NO Python cleanup applied to Section 1 text.")
        cleaned_text = generated_text # Use raw text directly

    except Exception as e:
        print(f"Error during LLM call for Section 1: {e}") # Removed "or cleanup"
        return f"## 1. Executive Summary / Snapshot\\n\\nError generating content: {e}\\n"

    # --- Format Output ---
    section_content = f"## 1. Executive Summary / Snapshot\n\n{cleaned_text.strip()}\n" # Use cleaned (raw) text, strip outer whitespace
    print(f"<- Section 1 generated (no cleanup) successfully for {ticker}.")
    return section_content

print("Created/Overwrote report_generator.py with Section 1 (NO cleanup)")
# No imports needed if done in first cell

import textwrap # Ensure textwrap is available
# Make sure 'import re' is NOT present here if it was added

def generate_section_5_financial_analysis(ticker: str, company_info: dict, financial_summary: dict, news: list, llm_handler_generate: callable) -> str:
    """
    Generates the Financial Analysis section (Section 5).
    NO Python cleanup applied post-LLM. Relies on prompt for formatting.
    """
    print(f"-> Generating Section 5: Financial Analysis for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    revenue = financial_summary.get('latest_annual_revenue')
    earnings = financial_summary.get('latest_annual_earnings')
    fin_year = financial_summary.get('financials_year', 'N/A')
    revenue_str = f"${revenue:,.0f}" if revenue is not None else "N/A"
    earnings_str = f"${earnings:,.0f}" if earnings is not None else "N/A"
    news_headlines = [item.get('title', 'No Title Available') for item in news[:3]]
    news_context_str = "\\n".join([f"- {h}" for h in news_headlines]) if news_headlines else "No recent news headlines provided."

    # --- Construct the Prompt ---
    # Using the strong formatting prompt just in case, but won't rely on it fully
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Financial Analysis' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        **Provided Financial Data (Year Ending: {fin_year}):**
        *   Latest Annual Revenue: {revenue_str}
        *   Latest Annual Earnings (Net Income): {earnings_str}

        **Recent News Headlines (for context):**
        {news_context_str}

        **Instructions:**
        Based *only* on the provided financial data, recent news headlines, and your general knowledge:
        1.  Analyze recent financial performance using the provided revenue and earnings. Comment on the scale.
        2.  Provide qualitative commentary on likely profitability or margin situation.
        3.  Briefly comment on your *perception* of balance sheet strength and cash flow capability.
        4.  Summarize key financial takeaways.
        5.  Keep the analysis concise (approx. 2-4 paragraphs).

        **Constraint:** Generate *ONLY* the content for this 'Financial Analysis' section. Do *not* include the header '## 5. Financial Analysis'. Start the response directly with the analysis text.

        **VERY IMPORTANT FORMATTING:**
        *   Use standard English text with normal paragraph breaks (double newline).
        *   **MUST USE CORRECT SPACING.** Do **NOT** combine numbers and words without spaces. For example, write "Revenue exceeded $245 billion" or "net income of $88.1 billion", **NOT** "Revenueexceeded245billion" or "netincomeof88.1billion".
        *   Ensure standard spacing after punctuation (e.g., "portfolio. Coupled with...").
        *   Avoid unnecessary special characters or markdown within the paragraphs.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        # Keep the debug print to verify raw output if needed later
        print(f"\\nDEBUG: Raw LLM Output (Section 5):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 5.")
             return "## 5. Financial Analysis\\n\\nError: Failed to generate content for this section due to LLM failure.\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 5.")
             return "## 5. Financial Analysis\\n\\nError: Failed to generate content for this section (empty response received).\\n"

        # ----- NO Python Cleanup -----
        # Use the raw text directly after stripping outer whitespace
        cleaned_text = generated_text
        print("-> NO Python cleanup applied to Section 5 text.")


    except Exception as e:
        # Error during LLM call itself
        print(f"Error during LLM call for Section 5: {e}")
        return f"## 5. Financial Analysis\\n\\nError generating content: {e}\\n"

    # --- Format Output ---
    # Use strip() on the final output string just before adding header
    section_content = f"## 5. Financial Analysis\n\n{cleaned_text.strip()}\n"
    print(f"<- Section 5 generated (NO cleanup) successfully for {ticker}.")
    return section_content

# Ensure no extra print statement here

# =========================================
# Section 2: Business Description Function
# =========================================

import textwrap
import re # Keep import just in case needed later, but not used now

def generate_section_2_business_description(ticker: str, company_info: dict, llm_handler_generate: callable) -> str:
    """
    Generates the Business Description section (Section 2) of the report.
    Relies on the LLM prompt for content generation based on provided company info.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information, expected to have
                      keys like 'longName', 'longBusinessSummary', 'sector', 'industry'.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 2, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 2: Business Description for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    summary = company_info.get('longBusinessSummary', 'N/A')
    sector = company_info.get('sector', 'N/A')
    industry = company_info.get('industry', 'N/A')

    if summary == 'N/A' or not summary:
        print(f"Warning: 'longBusinessSummary' is missing or empty for {ticker}. Section 2 content may be limited.")
        # Return a placeholder section indicating missing data
        return f"## 2. Business Description\\n\\nError: Company business summary not available for {ticker}. Cannot generate this section.\\n"

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Business Description' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})
        **Sector:** {sector}
        **Industry:** {industry}

        **Provided Business Summary:**
        --- START SUMMARY ---
        {summary}
        --- END SUMMARY ---

        **Instructions:**
        Based *primarily* on the provided business summary text above:
        1.  Write a concise overview of the company's business.
        2.  Mention key products/services and markets/segments *if they are clearly identifiable* within the provided summary text. Do *not* invent products/services not mentioned.
        3.  Identify the main competitors *only if they are explicitly mentioned* in the provided summary text. Do *not* guess competitors.
        4.  Keep the tone factual and descriptive.
        5.  Ensure the output is well-formatted standard English text with normal paragraph breaks.

        **Constraint:** Generate *ONLY* the content required for this "Business Description" section. Do *not* include the header '## 2. Business Description' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters.
    """)

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        print(f"\\nDEBUG: Raw LLM Output (Section 2):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 2.")
             return "## 2. Business Description\\n\\nError: Failed to generate content for this section due to LLM failure.\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 2.")
             return "## 2. Business Description\\n\\nError: Failed to generate content for this section (empty response received).\\n"

        # ----- Minimal Cleanup -----
        # Primarily trim whitespace. Relying on prompt for good formatting.
        cleaned_text = generated_text.strip()
        print("-> Minimal Python cleanup applied to Section 2 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 2: {e}")
        return f"## 2. Business Description\\n\\nError generating content: {e}\\n"

    # --- Format Output ---
    section_content = f"## 2. Business Description\n\n{cleaned_text}\n" # Add header and trailing newline
    print(f"<- Section 2 generated successfully for {ticker}.")
    return section_content

# <<< End of generated code >>>


import textwrap
# import re # Already imported usually, but uncomment if running this cell standalone first

def generate_section_2_business_description(ticker: str, company_info: dict, llm_handler_generate: callable) -> str:
    """
    Generates the Business Description section (Section 2) of the report.
    Relies on the LLM prompt for content generation based on provided company info.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information, expected to have
                      keys like 'longName', 'longBusinessSummary', 'sector', 'industry'.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 2, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 2: Business Description for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    summary = company_info.get('longBusinessSummary', 'N/A')
    sector = company_info.get('sector', 'N/A')
    industry = company_info.get('industry', 'N/A')

    if summary == 'N/A' or not summary:
        print(f"Warning: 'longBusinessSummary' is missing or empty for {ticker}. Section 2 content may be limited.")
        # Return a placeholder section indicating missing data
        return f"## 2. Business Description\\n\\nError: Company business summary not available for {ticker}. Cannot generate this section.\\n"

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Business Description' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})
        **Sector:** {sector}
        **Industry:** {industry}

        **Provided Business Summary:**
        --- START SUMMARY ---
        {summary}
        --- END SUMMARY ---

        **Instructions:**
        Based *primarily* on the provided business summary text above:
        1.  Write a concise overview of the company's business.
        2.  Mention key products/services and markets/segments *if they are clearly identifiable* within the provided summary text. Do *not* invent products/services not mentioned.
        3.  Identify the main competitors *only if they are explicitly mentioned* in the provided summary text. Do *not* guess competitors.
        4.  Keep the tone factual and descriptive.
        5.  Ensure the output is well-formatted standard English text with normal paragraph breaks.

        **Constraint:** Generate *ONLY* the content required for this "Business Description" section. Do *not* include the header '## 2. Business Description' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        print(f"\\nDEBUG: Raw LLM Output (Section 2):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 2.")
             return "## 2. Business Description\\n\\nError: Failed to generate content for this section due to LLM failure.\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 2.")
             return "## 2. Business Description\\n\\nError: Failed to generate content for this section (empty response received).\\n"

        # ----- Minimal Cleanup -----
        # Primarily trim whitespace. Relying on prompt for good formatting.
        cleaned_text = generated_text.strip()
        print("-> Minimal Python cleanup applied to Section 2 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 2: {e}")
        return f"## 2. Business Description\\n\\nError generating content: {e}\\n"

    # --- Format Output ---
    section_content = f"## 2. Business Description\n\n{cleaned_text}\n" # Add header and trailing newline
    print(f"<- Section 2 generated successfully for {ticker}.")
    return section_content

print("\\nAppended Section 2 function to report_generator.py")

# =========================================
# Section 3: Business Strategy & Outlook Function
# =========================================

import textwrap
import re # Keep import just in case

def generate_section_3_strategy_outlook(ticker: str, company_info: dict, news: list, llm_handler_generate: callable) -> str:
    """
    Generates the Business Strategy & Outlook section (Section 3) of the report.
    Relies on the LLM prompt for content generation based on provided company info and news.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information, expected to have
                      keys like 'longName', 'longBusinessSummary'.
        news: A list of dictionaries, where each dict represents a news article
              and is expected to have a 'title' key.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 3, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 3: Business Strategy & Outlook for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    summary = company_info.get('longBusinessSummary', 'N/A') # Use summary for context

    # Format news headlines for the prompt
    news_headlines = [item.get('title', 'No Title Available') for item in news[:5]] # Get top 5 headlines
    if news_headlines:
        news_context_str = "Recent News Headlines:\n" + "\n".join([f"- {h}" for h in news_headlines])
    else:
        news_context_str = "No recent news headlines provided."

    if summary == 'N/A' or not summary:
        print(f"Warning: 'longBusinessSummary' is missing or empty for {ticker}. Section 3 context may be limited.")
        # We can still proceed, but the LLM will have less context.

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Business Strategy & Outlook' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        **Company Business Summary (for context):**
        --- START SUMMARY ---
        {summary if summary != 'N/A' else 'Business summary not available.'}
        --- END SUMMARY ---

        **Context from Recent News:**
        {news_context_str}

        **Instructions:**
        Based on the provided business summary, recent news headlines, and your general knowledge of the company and its industry:
        1.  Interpret the company's likely **business strategy** (e.g., key focus areas, growth initiatives, market positioning).
        2.  Discuss relevant **industry trends** and how the company appears to be positioned relative to them.
        3.  Identify potential future **growth drivers** for the company.
        4.  Identify significant **challenges or risks** to the company's strategy and future outlook.
        5.  Incorporate insights or context suggested by the provided news headlines where relevant and appropriate.
        6.  Keep the tone analytical and forward-looking.

        **Constraint:** Generate *ONLY* the content required for this "Business Strategy & Outlook" section. Do *not* include the header '## 3. Business Strategy & Outlook' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        print(f"\\nDEBUG: Raw LLM Output (Section 3):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 3.")
             # Ensure a default error message format
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             return f"## 3. Business Strategy & Outlook\\n\\n{error_message}\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 3.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             return f"## 3. Business Strategy & Outlook\\n\\n{error_message}\\n"

        # ----- Minimal Cleanup -----
        # Primarily trim whitespace. Relying on prompt for good formatting.
        cleaned_text = generated_text.strip()
        print("-> Minimal Python cleanup applied to Section 3 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 3: {e}")
        error_message = f"Error generating content: {e}"
        return f"## 3. Business Strategy & Outlook\\n\\n{error_message}\\n"

    # --- Format Output ---
    section_content = f"## 3. Business Strategy & Outlook\n\n{cleaned_text}\n" # Add header and trailing newline
    print(f"<- Section 3 generated successfully for {ticker}.")
    return section_content

print("\\nAppended Section 3 function to report_generator.py")

# =========================================
# Section 4: Economic Moat Analysis Function
# =========================================

import textwrap
import re # Keep import just in case needed later

def generate_section_4_economic_moat(ticker: str, company_info: dict, llm_handler_generate: callable) -> str:
    """
    Generates the Economic Moat Analysis section (Section 4) of the report.
    Relies on the LLM prompt for content generation based on provided company info.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information, expected to have
                      keys like 'longName', 'longBusinessSummary'.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 4, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 4: Economic Moat Analysis for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    summary = company_info.get('longBusinessSummary', 'N/A')

    if summary == 'N/A' or not summary:
        print(f"Warning: 'longBusinessSummary' is missing or empty for {ticker}. Section 4 content will be based on general knowledge only.")
        summary_context = "Business summary not available. Base analysis on general knowledge of the company and its industry."
    else:
        summary_context = f"""
        **Provided Business Summary:**
        --- START SUMMARY ---
        {summary}
        --- END SUMMARY ---
        """

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Economic Moat Analysis' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        {summary_context}

        **Instructions:**
        Based on the provided business summary (if available) and your general knowledge of economic moats:
        1.  Analyze the company's competitive advantages. Consider sources like network effects, switching costs, intangible assets (brands, patents), cost advantages, and efficient scale.
        2.  Identify the likely *sources* of the company's economic moat.
        3.  Comment briefly on the perceived *sustainability* (e.g., widening, narrowing, stable) of these advantages.
        4.  The analysis should be conceptually consistent with standard moat assessments (None, Narrow, Wide), but do *not* explicitly state the final rating here (that's for the Exec Summary). Focus on the *reasons* behind the moat.

        **Constraint:** Generate *ONLY* the content required for this "Economic Moat Analysis" section. Do *not* include the header '## 4. Economic Moat Analysis' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters. Ensure proper spacing after punctuation.
    """) # Added "Ensure proper spacing after punctuation." to prompt
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        print(f"\\nDEBUG: Raw LLM Output (Section 4):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 4.")
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             # Return the error message wrapped in the section header
             return f"## 4. Economic Moat Analysis\\n\\n{error_message}\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 4.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             # Return the error message wrapped in the section header
             return f"## 4. Economic Moat Analysis\\n\\n{error_message}\\n"

        # ----- Minimal Cleanup -----
        # Primarily trim whitespace. Relying on prompt for good formatting.
        cleaned_text = generated_text.strip() # Keep strip() here
        print("-> Minimal Python cleanup applied to Section 4 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 4: {e}")
        error_message = f"Error generating content: {e}"
        # Return the error message wrapped in the section header
        return f"## 4. Economic Moat Analysis\\n\\n{error_message}\\n"

    # --- Format Output ---
    # Ensure the header is followed by two newlines before the cleaned text
    section_content = f"## 4. Economic Moat Analysis\n\n{cleaned_text}\n" # Use cleaned_text directly after header + \n\n
    print(f"<- Section 4 generated successfully for {ticker}.")
    return section_content

# No need for the extra print statement here if it was added previously
# print("\nAppended Section 4 function to report_generator.py")

# =========================================
# Section 6: Valuation Analysis Function (CORRECTED VERSION)
# =========================================
# This block corrects the final formatting line in the previous definition.

import textwrap
import re

def generate_section_6_valuation(ticker: str, company_info: dict, quote_data: dict, llm_handler_generate: callable) -> str:
    """
    Generates the Valuation Analysis section (Section 6) of the report.
    Relies on the LLM prompt for content generation based on provided quote data.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information (primarily for name/context).
        quote_data: A dictionary containing quote data, expected to have keys like
                    'trailingPE', 'forwardPE'.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 6, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 6: Valuation Analysis for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)
    trailing_pe = quote_data.get('trailingPE', 'N/A')
    forward_pe = quote_data.get('forwardPE', 'N/A')

    pe_context = f"Trailing P/E: {trailing_pe if trailing_pe else 'N/A'}\\nForward P/E: {forward_pe if forward_pe else 'N/A'}" # Using \\n here is fine for the LLM prompt itself

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Valuation Analysis' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        **Provided Valuation Context:**
        *   {pe_context}

        **Instructions:**
        Based on the provided valuation context and your general financial knowledge:
        1.  Briefly explain that valuation is complex and involves various methods.
        2.  Describe *plausible high-level* valuation approaches an analyst *might* use for a company like this (e.g., mentioning concepts like peer multiples/comparables analysis using metrics like P/E, discounted cash flow (DCF) analysis, precedent transactions). **Do NOT perform any calculations.**
        3.  Discuss how metrics like the provided P/E ratios generally fit into the context of valuation (e.g., what high or low P/E might suggest relative to growth or risk).
        4.  Identify key *factors* or *drivers* that generally influence a company's valuation (e.g., growth expectations, profitability, industry trends, risk profile, market sentiment, interest rates).
        5.  Optionally, name 1-2 major, well-known potential peer companies for general comparison context (e.g., if analyzing Apple, mention Samsung or Google). Do *not* perform a comparative analysis.
        6.  **CRITICAL CONSTRAINT:** Do **NOT** state a specific Fair Value Estimate (FVE) or price target in this section. Focus only on the *concepts and drivers* of valuation.

        **Constraint:** Generate *ONLY* the content required for this "Valuation Analysis" section. Do *not* include the header '## 6. Valuation Analysis' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters. Ensure proper spacing after punctuation.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        # print(f"\\nDEBUG: Raw LLM Output (Section 6):\\n>>>\\n{generated_text}\\n<<<\\n") # Keep debug commented unless needed
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 6.")
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             return f"## 6. Valuation Analysis\n\n{error_message}\n" # Use \n\n here
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 6.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             return f"## 6. Valuation Analysis\n\n{error_message}\n" # Use \n\n here

        # ----- Minimal Cleanup -----
        cleaned_text = generated_text.strip()
        print("-> Minimal Python cleanup applied to Section 6 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 6: {e}")
        error_message = f"Error generating content: {e}"
        return f"## 6. Valuation Analysis\n\n{error_message}\n" # Use \n\n here

    # --- Format Output (CORRECTED LINE) ---
    # Ensure the header is followed by two single-backslash newlines before the cleaned text
    section_content = f"## 6. Valuation Analysis\n\n{cleaned_text}\n" # Use \n\n (single backslashes)
    print(f"<- Section 6 generated successfully for {ticker}.")
    return section_content

# Add a print statement to confirm the file write/append
print("\nAppended CORRECTED Section 6 function to report_generator.py")

# =========================================
# Section 7: Risk and Uncertainty Assessment Function
# =========================================

import textwrap
# import re # Already imported usually, uncomment if needed

def generate_section_7_risk_uncertainty(ticker: str, company_info: dict, news: list, llm_handler_generate: callable) -> str:
    """
    Generates the Risk and Uncertainty Assessment section (Section 7) of the report.
    Relies on the LLM prompt for content generation based on provided company info and news.
    Applies minimal Python cleanup post-LLM.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT").
        company_info: A dictionary containing company information (primarily for name/context).
        news: A list of dictionaries, where each dict represents a news article
              and is expected to have a 'title' key.
        llm_handler_generate: A callable function (like llm_handler.generate_text)
                             that takes a prompt string and returns the LLM's response.

    Returns:
        A formatted markdown string for Section 7, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 7: Risk and Uncertainty Assessment for {ticker}...")

    # --- Extract Data for Prompt ---
    company_name = company_info.get('longName', ticker)

    # Format news headlines for the prompt
    news_headlines = [item.get('title', 'No Title Available') for item in news[:5]] # Get top 5 headlines
    if news_headlines:
        news_context_str = "Recent News Headlines (for context):\\n" + "\\n".join([f"- {h}" for h in news_headlines]) # Using \\n for LLM prompt readability
    else:
        news_context_str = "No recent news headlines provided."

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Risk and Uncertainty Assessment' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        {news_context_str}

        **Instructions:**
        Based on the provided news headlines (if any) and your general knowledge of the company, its industry, and common financial risks:
        1.  Identify key risks relevant to the company. Aim to categorize them broadly where possible (e.g., Business-Specific Risks like competition, product execution, supply chain; Market Risks like economic downturns, interest rate changes; Technological Risks like obsolescence, cybersecurity; Regulatory Risks).
        2.  Briefly explain the potential impact or implications of 2-3 of the most significant risks identified.
        3.  Provide a qualitative assessment of the overall uncertainty surrounding the company's future outlook (e.g., Low, Medium, High). Briefly justify this assessment based on the nature and severity of the identified risks, company stability, or market volatility.
        4.  Use bullet points for listing the identified risks if appropriate for clarity.

        **Constraint:** Generate *ONLY* the content required for this "Risk and Uncertainty Assessment" section. Do *not* include the header '## 7. Risk and Uncertainty Assessment' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Use bullet points (* or -) if listing risks. Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters. Ensure proper spacing after punctuation.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        # Keep debug print commented unless needed during development
        # print(f"\\nDEBUG: Raw LLM Output (Section 7):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 7.")
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             return f"## 7. Risk and Uncertainty Assessment\\n\\n{error_message}\\n" # Use \n\n here
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 7.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             return f"## 7. Risk and Uncertainty Assessment\\n\\n{error_message}\\n" # Use \n\n here

        # ----- Minimal Cleanup -----
        cleaned_text = generated_text.strip()
        print("-> Minimal Python cleanup applied to Section 7 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 7: {e}")
        error_message = f"Error generating content: {e}"
        return f"## 7. Risk and Uncertainty Assessment\\n\\n{error_message}\\n" # Use \n\n here

    # --- Format Output ---
    # Ensure the header is followed by two single-backslash newlines before the cleaned text
    # CORRECTED LINE
    section_content = f"## 7. Risk and Uncertainty Assessment\n\n{cleaned_text}\n" # Use \n\n (single backslashes for actual newlines)
    print(f"<- Section 7 generated successfully for {ticker}.")
    return section_content

# Add a print statement to confirm the file write/append
print("\\nAppended Section 7 function to report_generator.py")

# =========================================
# Section 8: Bulls Say / Bears Say Function
# =========================================

import textwrap
# import re # Ensure re is imported if needed by other sections, but not needed here

def generate_section_8_bulls_bears(ticker: str, company_info: dict, quote_data: dict, financial_summary: dict, news: list, llm_handler_generate: callable) -> str:
    """
    Generates the Bulls Say / Bears Say section (Section 8) of the report.
    Relies on the LLM prompt to synthesize context from previous analysis areas.

    Args:
        ticker: The stock ticker symbol.
        company_info: Dictionary with company info (needs 'longName').
        quote_data: Dictionary with quote data (for context, e.g., P/E).
        financial_summary: Dictionary with financial summary (for context).
        news: List of news dictionaries (for context).
        llm_handler_generate: Callable function to generate text via LLM.

    Returns:
        A formatted markdown string for Section 8, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 8: Bulls Say / Bears Say for {ticker}...")

    # --- Extract Minimal Data for Prompt Focus ---
    # The prompt primarily asks the LLM to synthesize, so we provide basic identity.
    company_name = company_info.get('longName', ticker)
    # We could add a few key metrics if testing shows the LLM needs more explicit grounding
    # e.g., trailing_pe = quote_data.get('trailingPE', 'N/A')

    # --- Construct the Prompt ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Bulls Say / Bears Say' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})

        **Instructions:**
        Synthesizing the overall analysis context (considering business description, strategy, economic moat, financial performance, valuation metrics like P/E, and identified risks/outlook), generate the following:

        1.  **Bulls Say:** Create a section starting exactly with `**Bulls Say:**`. Under this heading, list 2-3 concise bullet points summarizing the key positive arguments or investment thesis points for this stock. Examples: strong market position, robust growth drivers, attractive valuation aspect, positive industry trends, strong financials, effective strategy. Use `* ` or `- ` for bullet points.
        2.  **Bears Say:** Create a section starting exactly with `**Bears Say:**`. Under this heading, list 2-3 concise bullet points summarizing the key negative arguments or risks to the investment thesis. Examples: significant competitive threats, execution risks, upcoming challenges, unattractive valuation aspect, industry headwinds, slowing growth. Use `* ` or `- ` for bullet points.

        Keep the bullet points concise and distinct. Focus on the *arguments* rather than just restating data points.

        **Constraint:** Generate *ONLY* the content required for this "Bulls Say / Bears Say" section, including the specified bold headers and bullet points. Start the response directly with `**Bulls Say:**`.
        **IMPORTANT FORMATTING:** Use standard English text. Use bullet points (`* ` or `- `) under the specified bold headers (`**Bulls Say:**`, `**Bears Say:**`). Ensure normal paragraph breaks between the two sections if needed, but the primary structure is the headers followed by bullets. Do NOT insert extra spaces between letters of words. Avoid other unnecessary special characters.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        # Keep debug print commented unless needed during development
        # print(f"\\nDEBUG: Raw LLM Output (Section 8):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 8.")
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             # Return the error message wrapped in the section header
             return f"## 8. Bulls Say / Bears Say\\n\\n{error_message}\\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 8.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             # Return the error message wrapped in the section header
             return f"## 8. Bulls Say / Bears Say\\n\\n{error_message}\\n"
        # Validate if the required headers are present (basic check)
        if "**Bulls Say:**" not in generated_text or "**Bears Say:**" not in generated_text:
            print("Warning: LLM output for Section 8 might be missing required 'Bulls Say' or 'Bears Say' headers.")
            # Still return the text, but flag the potential issue

        # ----- Minimal Cleanup -----
        cleaned_text = generated_text.strip() # Trim outer whitespace
        print("-> Minimal Python cleanup applied to Section 8 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 8: {e}")
        error_message = f"Error generating content: {e}"
        # Return the error message wrapped in the section header
        return f"## 8. Bulls Say / Bears Say\n\n{error_message}\n"

    # --- Format Output ---
    # Ensure the header is followed by two single-backslash newlines before the cleaned text
    section_content = f"## 8. Bulls Say / Bears Say\n\n{cleaned_text}\n" # Use \n\n
    print(f"<- Section 8 generated successfully for {ticker}.")
    return section_content

# Add a print statement to confirm the file write/append
print("\\nAppended Section 8 function to report_generator.py")

# =========================================
# Section 9: Conclusion & Investment Recommendation Function (REVISED)
# =========================================
# Accepts FVE and Rating as arguments to ensure consistency

import textwrap
# import re # Ensure re is imported if needed by other sections

def generate_section_9_conclusion_recommendation(
    ticker: str,
    company_info: dict,
    quote_data: dict,
    llm_handler_generate: callable,
    fve_value: float | None, # <-- New argument
    rating_value: str | None  # <-- New argument
) -> str:
    """
    Generates the Conclusion & Investment Recommendation section (Section 9) of the report.
    Relies on the LLM prompt to synthesize information and RESTATE the provided FVE/Rating.

    Args:
        ticker: The stock ticker symbol.
        company_info: Dictionary with company info (needs 'longName').
        quote_data: Dictionary with quote data (needs 'currentPrice' for context).
        llm_handler_generate: Callable function to generate text via LLM.
        fve_value: The Fair Value Estimate parsed from Section 1's output.
        rating_value: The Investment Recommendation parsed from Section 1's output.

    Returns:
        A formatted markdown string for Section 9, or an error message string
        if generation fails.
    """
    print(f"-> Generating Section 9: Conclusion & Recommendation (using parsed FVE/Rating) for {ticker}...")

    # --- Extract Data and Format Inputs for Prompt ---
    company_name = company_info.get('longName', ticker)
    current_price = quote_data.get('currentPrice', 'N/A')
    price_context = f"${current_price}" if current_price != 'N/A' else "N/A"

    # Prepare FVE and Rating strings for the prompt, handling None cases
    fve_display = f"${fve_value:.2f}" if fve_value is not None else "Not Available"
    rating_display = rating_value if rating_value is not None else "Not Available"

    # --- Construct the Prompt (Revised Instructions) ---
    prompt = textwrap.dedent(f"""
        Act as a Wall Street Financial Analyst. Your task is to generate ONLY the 'Conclusion & Investment Recommendation' section for an equity research report on the following company:

        **Company:** {company_name} ({ticker})
        **Current Stock Price Context:** {price_context}

        **Previously Determined Assessment:**
        *   Investment Recommendation: {rating_display}
        *   Fair Value Estimate (FVE): {fve_display}

        **Instructions:**
        Based on your overall synthesized analysis of this company (considering its business, strategy, moat, financials, valuation context, and risks):
        1.  Briefly summarize the key findings and your overall assessment of the company's investment profile (1-2 paragraphs).
        2.  Conclude by **restating** the final **Investment Recommendation**, which is **'{rating_display}'**.
        3.  Also **restate** the final **Fair Value Estimate (FVE)**, which is **'{fve_display}'**.
        4.  Ensure the summary logically leads into the restated recommendation and FVE.

        **Constraint:** Generate *ONLY* the content required for this "Conclusion & Investment Recommendation" section. Do *not* include the header '## 9. Conclusion & Investment Recommendation' in your response. Start the response directly with the analysis text.
        **IMPORTANT FORMATTING:** Use standard English text with normal paragraph breaks (double newline). Do NOT insert extra spaces between letters of words. Avoid unnecessary special characters. Ensure proper spacing after punctuation.
    """)
    # --- END OF PROMPT ---

    # --- Call LLM ---
    try:
        generated_text = llm_handler_generate(prompt)
        # --- DEBUG ---
        # Keep debug print commented unless needed during development
        # print(f"\\nDEBUG: Raw LLM Output (Section 9 - Revised):\\n>>>\\n{generated_text}\\n<<<\\n")
        # --- END DEBUG ---

        if generated_text is None:
             print("Error: LLM generation returned None for Section 9.")
             error_message = "Error: Failed to generate content for this section due to LLM failure."
             return f"## 9. Conclusion & Investment Recommendation\n\n{error_message}\n"
        if not generated_text.strip():
             print("Warning: LLM generation returned an empty string for Section 9.")
             error_message = "Error: Failed to generate content for this section (empty response received)."
             return f"## 9. Conclusion & Investment Recommendation\n\n{error_message}\n"

        # ----- Minimal Cleanup -----
        cleaned_text = generated_text.strip() # Trim outer whitespace
        print("-> Minimal Python cleanup applied to Section 9 text (trimming whitespace).")

    except Exception as e:
        print(f"Error during LLM call or minimal cleanup for Section 9: {e}")
        error_message = f"Error generating content: {e}"
        return f"## 9. Conclusion & Investment Recommendation\n\n{error_message}\n"

    # --- Format Output ---
    section_content = f"## 9. Conclusion & Investment Recommendation\n\n{cleaned_text}\n" # Use \n\n
    print(f"<- Section 9 generated successfully for {ticker}.")
    return section_content

# Add a print statement to confirm the file write/append
print("\\nAppended REVISED Section 9 function to report_generator.py")

# =========================================
# Section 10: References Function
# =========================================
import textwrap # Keep imports in case this section is run independently

def generate_section_10_references() -> str:
    """
    Generates a static markdown section listing primary data sources and the LLM.

    Returns:
        A formatted markdown string for Section 10.
    """
    print("-> Generating Section 10: References (Static)...")
    # Using textwrap.dedent for clean multiline string definition
    references_content = textwrap.dedent("""\
        ## 10. References

        *   Data primarily sourced from Yahoo Finance via the `yfinance` library.
        *   Analysis and narrative generated by Google Gemini Large Language Model.
        *   Disclaimer: This report is a Proof of Concept generated by an AI and should not be considered financial advice.
    """)
    print("<- Section 10 generated successfully.")
    return references_content + "\n" # Add trailing newline

# =========================================
# Report Assembly Function
# =========================================

def assemble_report(ticker: str, company_name: str, all_sections: list[str]) -> str:
    """
    Combines all generated report sections into a single markdown string
    with a main title.

    Args:
        ticker: The stock ticker symbol.
        company_name: The long name of the company.
        all_sections: A list where each element is the formatted markdown
                      string for one report section (sections 1-10 in order).

    Returns:
        The complete report as a single markdown string.
    """
    print(f"-> Assembling final report for {ticker}...")

    # Ensure company_name is a non-empty string, fallback to ticker if needed
    if not company_name or not isinstance(company_name, str):
        print(f"Warning: Invalid company name ('{company_name}'). Using ticker as fallback for title.")
        company_name = ticker

    # Create the main title
    report_title = f"# Equity Research Report: {company_name} ({ticker.upper()})\n\n"

    # Join all the sections. Ensure each section already ends with \n.
    # The join adds \n\n between sections.
    report_body = "\n".join(all_sections) # Using single \n join as sections should end with \n

    # Combine title and body
    full_report = report_title + report_body

    print(f"<- Report assembly completed for {ticker}.")
    return full_report

# Add a print statement to confirm the file write/append
print("\nAppended Section 10 and Assembly functions to report_generator.py")
