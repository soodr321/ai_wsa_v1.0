# AI Wall Street Analyst (V1.5 - Agentified FVE)

**Live Application (V1.5):** [https://aiwsav10-fh8pkwqjqhy6gkzyzrttev.streamlit.app/](https://aiwsav10-fh8pkwqjqhy6gkzyzrttev.streamlit.app/) 

## 📋 Project Overview

The AI Wall Street Analyst is a web application that leverages Large Language Models (LLMs) and fundamental financial analysis techniques to automatically generate equity research reports for U.S. stock tickers. Users can input a valid ticker symbol, and the application will fetch relevant financial data, perform a valuation using an independent Fair Value Estimate (FVE) Agent, and render a comprehensive analytical report.

This project has evolved from an initial proof-of-concept (V1.0) to a more robust version (V1.5) that significantly enhances the credibility and analytical depth of the generated FVE. V1.5 introduces an **`FVEAgent`**, which performs its own Discounted Cash Flow (DCF) and Multiples-based valuations, with Python handling calculations and an LLM assisting in assumption generation and justification.

## ✨ Key Features (V1.5)

*   **Web-Based Ticker Input:** Simple UI for entering a U.S. stock ticker.
*   **Automated & Enhanced Data Fetching:** Utilizes the `yfinance` library to retrieve:
    *   Company information (profile, sector, industry).
    *   Real-time quote data.
    *   **Multi-year historical annual financial statements** (Income, Balance Sheet, Cash Flow) for DCF inputs.
    *   Key metrics like Beta, Shares Outstanding, P/E ratios, EPS.
    *   Recent news headlines.
*   **Independent Fair Value Estimate (FVE) Agent (`FVEAgent`):**
    *   **Primary Method: Two-Stage FCFE DCF Valuation:**
        *   Calculates base FCFE_0 using Python from yfinance data.
        *   LLM (Google Gemini) assists in generating and justifying assumptions for Stage 1 FCFE growth rates, a perpetual growth rate (g), and Cost of Equity (Ke) components (Beta from data; RFR & ERP are configurable).
        *   All actual DCF calculations (projections, discounting, terminal value, FVE per share) are performed by Python code within the agent.
        *   Includes internal validation (e.g., Ke > g + minimum spread).
    *   **Backup Method: P/E Multiples-Based Valuation:**
        *   Used if DCF fails (e.g., Beta unavailable, Ke <= g, critical data missing).
        *   LLM assists in selecting and justifying an appropriate P/E multiple and EPS base.
        *   Python code performs the FVE calculation (P/E * EPS).
    *   **Transparent Methodology Output:** The `FVEAgent` clearly states its chosen methodology (DCF or Multiples), key inputs, LLM-assisted assumptions with justifications, and a summary of the Python-executed calculation steps.
*   **AI-Powered Report Generation:** Employs Google's Gemini (`gemini-1.5-flash-latest`) for generating narrative text for report sections.
*   **Comprehensive Multi-Section Report:**
    1.  **Executive Summary / Snapshot:** (LLM generates rating based on agent's FVE vs. current price; restates agent's FVE & method).
    2.  **Valuation Methodology Deep Dive:** (Direct output from `FVEAgent` explaining its FVE calculation).
    3.  Business Description
    4.  Business Strategy & Outlook
    5.  Economic Moat Analysis
    6.  Financial Analysis (summary of latest annuals and trends).
    7.  Valuation Discussion (general context, distinct from FVEAgent's specific methodology).
    8.  Risk and Uncertainty Assessment
    9.  Bulls Say / Bears Say
    10. **Conclusion & Investment Recommendation:** (Restates agent's FVE & rating from Section 1).
    11. References
*   **Dynamic Report Display:** Renders the generated markdown report in the Streamlit UI.
*   **API Key Security:** Secure management of the Google Gemini API key using Streamlit Community Cloud secrets.
*   **Enhanced FVE/Rating Consistency:** FVE is now an independent calculation, and the overall rating in Section 1 is informed by this agent-derived FVE. Section 9 restates these values.

## 🛠️ Technologies Used

*   **Language:** Python 3.12
*   **Core Libraries:**
    *   Streamlit (Web UI framework)
    *   `google-generativeai` (for Google Gemini API)
    *   `yfinance` (for stock data)
    *   `pandas` (for data manipulation)
    *   `python-dotenv` (for local environment variable management)
    *   `re` (for parsing)
*   **Development Environment:** Google Cloud Shell
*   **Version Control:** Git & GitHub
*   **Deployment Platform:** Streamlit Community Cloud (SCC)
*   **LLM:** Google Gemini (`gemini-1.5-flash-latest`)

## 🚀 How to Use / Test (V1.5 - When Deployed)

1.  Visit the live V1.5 application link (to be updated upon deployment).
2.  Enter a valid U.S. stock ticker symbol (e.g., AAPL, MSFT, NVDA, GOOG) into the input field.
3.  Click the "Generate Report" button.
4.  Please allow 1-2 minutes for the report to generate due to data fetching, FVE agent calculations (including multiple LLM calls within the agent), and report section generation.

## 📁 Project Structure (Key Files for V1.5)

*   `app.py`: Main Streamlit application; UI, orchestration of data fetching, `FVEAgent`, and report section generation.
*   `fve_agent.py`: **New in V1.5.** Contains the `FVEAgent` class responsible for independent Fair Value Estimate calculation (DCF & Multiples).
*   `data_fetcher.py`: Enhanced `StockDataFetcher` class to retrieve comprehensive data including multi-year financials for `FVEAgent`.
*   `llm_handler.py`: Class (`LLMHandler`) for configuring and interacting with the Google Gemini API.
*   `report_generator.py`: Functions for generating each specific section of the report; prompts for Section 1 & 9 now consume output from `FVEAgent`.
*   `config_loader.py`: (Legacy from V1.0 for API key loading, `LLMHandler` now has more direct env var handling, but `config_loader` might still be used as a fallback by `LLMHandler` if `get_api_key` is called).
*   `requirements.txt`: Lists Python dependencies.
*   `.env` (local only, not committed): Stores `GEMINI_API_KEY` for local development.
*   `manual_test_fve_agent.py`: Script for detailed testing of `FVEAgent` logic with manipulated inputs or specific scenarios.
*   `test_full_report_flow.py`: Script for testing the end-to-end report generation pipeline in Python (without UI).

## 📈 Agentic Roadmap & Future Enhancements

This project aims to evolve towards a more comprehensive agentic architecture.

**V1.5 Achieved:**
*   Independent, agentified Fair Value Estimate (FVE) Agent (`FVEAgent`) with DCF (Python calc, LLM assumptions) and Multiples fallback.
*   Clear FVE methodology output.

**Planned for V1.6 and Beyond:**
*   **Configuration File:** Centralize parameters like RFR, ERP, default years into `app_config.py`.
*   **Refactor `app.py`:** Modularize the main orchestration logic.
*   **Financial Analysis Agent:** Deeper historical financial analysis, ratio calculation, and trend identification to feed into other agents or report sections. (PRD V1.6 target)
*   **Moat Assessment Agent:** An independent agent to assess economic moat, providing a rating and justification to be used in Section 1 and Section 4.
*   **Sentiment-Informed FVE Assumptions:** Enhance `FVEAgent` or a new "SentimentAgent" to incorporate news sentiment into the justification or selection of FVE assumptions (e.g., growth rates, multiples). (PRD V1.7 target)
*   **Enhanced Risk Assessment Agent.**
*   **Refined Valuation Models:**
    *   3-Stage DCF model.
    *   FCFF (WACC-based) models.
    *   Adjustments for excess cash, non-operating assets.
*   **Analyst Override/User Input:** Allow users or a "supervisory analyst" to adjust key assumptions for the FVE.
*   **Improved UI/UX:** More granular loading, charts, report download.
*   **Broader Data Sources & International Stocks.**
*   **Orchestration & Tool Use:** Explore frameworks like LangChain/LlamaIndex for more complex agent interactions if needed.

## ⚠️ Disclaimer

This application is a Proof-of-Concept (POC) created for demonstration and learning purposes. The information provided, including financial data and AI-generated text, may contain inaccuracies or omissions. Data is sourced from Yahoo Finance and is subject to its own limitations. **This application does NOT provide financial advice.** Always conduct your own thorough research or consult with a qualified financial advisor before making any investment decisions.