
import yfinance as yf
import pandas as pd  # yfinance often returns pandas DataFrames/Series

class StockDataFetcher:
    """
    Fetches various stock data points for a given ticker symbol using the yfinance library.
    """
    def __init__(self, ticker: str):
        """
        Initializes the StockDataFetcher with a ticker symbol.

        Args:
            ticker (str): The stock ticker symbol (e.g., "AAPL", "MSFT").
        """
        if not isinstance(ticker, str) or not ticker:
            raise ValueError("Ticker symbol must be a non-empty string.")

        self.ticker_symbol = ticker.upper()
        self.stock = yf.Ticker(self.ticker_symbol)

        # Basic validation: Check if the ticker likely exists by attempting to fetch info
        try:
            # Accessing .info can be slow, sometimes .fast_info is enough for a quick check
            # However, .info is needed for most data points anyway.
            if not self.stock.info or self.stock.info.get('regularMarketPrice') is None:
                # Check if marketCap is 0, often indicating no data or delisted
                if self.stock.info.get('marketCap') == 0:
                     raise ValueError(f"No data found for ticker '{self.ticker_symbol}'. It might be invalid, delisted, or lack recent info.")
                # If market cap isn't 0 but price is missing, could be temp issue or less common stock type
                print(f"Warning: Could not retrieve complete basic info for ticker '{self.ticker_symbol}'. Data might be limited.")

            # Store info after validation to avoid fetching it repeatedly if needed quickly later
            self._info = self.stock.info

        except Exception as e:
            # Catch broader exceptions during initial fetch which might indicate network issues or truly invalid tickers
             raise ValueError(f"Could not initialize StockDataFetcher for '{self.ticker_symbol}'. Error: {e}")

    def get_company_info(self) -> dict:
        """
        Retrieves general company information.

        Returns:
            dict: A dictionary containing company profile data (e.g., sector, industry, summary).
                  Returns an empty dictionary if info is unavailable.
        """
        try:
            # Return the stored info if available
            if self._info:
                # Filter out potentially very large fields if needed, but for now return all
                return self._info
            else:
                # Attempt to fetch again if somehow _info wasn't populated but constructor didn't fail
                 info = self.stock.info
                 if info:
                     self._info = info # Store it now
                     return self._info
                 else:
                     print(f"Warning: Could not retrieve company info for {self.ticker_symbol}.")
                     return {}
        except Exception as e:
            print(f"Error fetching company info for {self.ticker_symbol}: {e}")
            return {}

    def get_quote_data(self) -> dict:
        """
        Retrieves essential quote data for the stock.
        Handles potential inconsistency in dividendYield formatting from yfinance.
        """
        quote_data = {}
        try:
            info = self._info if self._info else self.stock.info

            if not info:
                 print(f"Warning: Could not retrieve detailed info dictionary for {self.ticker_symbol} in get_quote_data.")
                 return {'currentPrice': None, 'marketCap': None, 'trailingPE': None, 'forwardPE': None, 'dividendYield': None}

            quote_data['currentPrice'] = info.get('currentPrice') or info.get('regularMarketPrice')
            quote_data['marketCap'] = info.get('marketCap')
            quote_data['trailingPE'] = info.get('trailingPE')
            quote_data['forwardPE'] = info.get('forwardPE')

            # --- MODIFIED SECTION for dividendYield ---
            div_yield_raw = info.get('dividendYield') # Get the raw value
            processed_yield = None # Initialize variable for the final percentage value

            if div_yield_raw is not None:
                # **Correction Logic:** Based on observation for MSFT, assume if the raw value is
                # between 0 and ~50 (unlikely yields above 50%), it might already be the percentage.
                # If it's less than 1, it *could* be a decimal fraction.
                # Let's prioritize the Yahoo display format: If 'dividendYield' is 0.90, we want 0.90.
                # For now, let's trust the MSFT case and *don't* multiply by 100, but round for consistency.
                # We should use the value directly if it seems plausible as a percentage.
                if 0 <= div_yield_raw < 1:
                     # It *could* be a decimal like 0.009 or the percentage number like 0.9.
                     # Since MSFT returned 0.9 for 0.9%, let's check trailing yield too.
                     trailing_yield_raw = info.get('trailingAnnualDividendYield') # Usually a decimal
                     if trailing_yield_raw is not None and round(div_yield_raw, 4) == round(trailing_yield_raw * 100, 4):
                         # If div_yield_raw matches trailing yield * 100, assume raw is the percentage.
                         processed_yield = round(div_yield_raw, 2)
                         print(f"Debug: 'dividendYield' ({div_yield_raw}) matches trailing yield % ({round(trailing_yield_raw * 100, 4)}), assuming it's already percentage.")
                     elif div_yield_raw < 0.20: # Heuristic: If less than 20%, maybe it's a decimal fraction?
                         processed_yield = round(div_yield_raw * 100, 2)
                         print(f"Debug: 'dividendYield' ({div_yield_raw}) is small, assuming decimal fraction. Converting to {processed_yield}%.")
                     else: # Otherwise, assume it's the percentage number directly
                         processed_yield = round(div_yield_raw, 2)
                         print(f"Debug: 'dividendYield' ({div_yield_raw}) >= 0.20, assuming it's already percentage.")
                elif div_yield_raw >= 1: # If >= 1, it's almost certainly the percentage already.
                     processed_yield = round(div_yield_raw, 2)
                     print(f"Debug: 'dividendYield' ({div_yield_raw}) >= 1, assuming it's already percentage.")
                else: # Handle zero or unexpected cases
                     processed_yield = div_yield_raw # Store as is or None
            else: # Handle case where key is missing
                 processed_yield = None

            # Store the processed value. Let's call the key 'dividendYield_pct'
            quote_data['dividendYield_pct'] = processed_yield

            # Let's also fetch and store the trailing yield for comparison (usually more reliable format)
            trailing_yield_raw = info.get('trailingAnnualDividendYield')
            processed_trailing_yield = None
            if trailing_yield_raw is not None:
                 # Assume trailing yield is consistently a decimal fraction
                 processed_trailing_yield = round(trailing_yield_raw * 100, 2)
            quote_data['trailingAnnualDividendYield_pct'] = processed_trailing_yield

            # --- END MODIFIED SECTION ---

            return quote_data

        except Exception as e:
            print(f"Error fetching quote data for {self.ticker_symbol}: {e}")
            return quote_data
    def get_financial_summary(self) -> dict:
        """
        Retrieves a summary of the latest annual financial data (Revenue and Earnings).

        Returns:
            dict: A dictionary with keys like 'latest_annual_revenue', 'latest_annual_earnings'.
                  Values are based on the most recent year in yfinance financials. Returns empty if unavailable.
        """
        summary = {}
        try:
            financials = self.stock.financials
            if financials.empty:
                 print(f"Warning: Annual financial data not available for {self.ticker_symbol}.")
                 return summary

            # Financials columns are timestamps representing year-end. Get the latest column (most recent year).
            latest_financials = financials.iloc[:, 0] # First column is typically the most recent year

            # Common names for revenue and earnings line items in yfinance
            revenue_keys = ['Total Revenue', 'Revenue', 'TotalRevenue']
            earnings_keys = ['Net Income', 'NetIncome'] # Net Income is a common measure for earnings

            summary['latest_annual_revenue'] = None
            for key in revenue_keys:
                if key in latest_financials.index:
                    summary['latest_annual_revenue'] = latest_financials[key]
                    break # Found one

            summary['latest_annual_earnings'] = None
            for key in earnings_keys:
                 if key in latest_financials.index:
                     summary['latest_annual_earnings'] = latest_financials[key]
                     break # Found one

            # You could add quarterly data similarly using self.stock.quarterly_financials if needed

            # Optionally format large numbers for readability later (but keep raw numbers for now)
            # summary['latest_annual_revenue_formatted'] = f"${summary['latest_annual_revenue']:,.0f}" if summary['latest_annual_revenue'] else "N/A"
            # summary['latest_annual_earnings_formatted'] = f"${summary['latest_annual_earnings']:,.0f}" if summary['latest_annual_earnings'] else "N/A"

            summary['financials_year'] = latest_financials.name.year # Add the year the data pertains to


            return summary

        except Exception as e:
            print(f"Error fetching financial summary for {self.ticker_symbol}: {e}")
            return {} # Return empty dict on error

    def get_news(self) -> list:
        """
        Retrieves recent news headlines related to the stock.

        Returns:
            list: A list of dictionaries, where each dictionary represents a news article
                  with keys like 'title', 'link', 'publisher', 'providerPublishTime'.
                  Returns an empty list if news is unavailable or an error occurs.
        """
        try:
            news = self.stock.news
            if not news:
                 print(f"No recent news found for {self.ticker_symbol}.")
                 return []

            # Ensure structure consistency, although yfinance usually provides this
            formatted_news = []
            for item in news:
                formatted_news.append({
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'publisher': item.get('publisher'),
                    # Convert Unix timestamp to readable format if needed, otherwise keep raw
                    'providerPublishTime': item.get('providerPublishTime')
                })
            return formatted_news

        except Exception as e:
            print(f"Error fetching news for {self.ticker_symbol}: {e}")
            return []

# --- Example Usage Block ---
if __name__ == "__main__":
    # Use input() in a real script, but hardcode for easier Colab testing
    # test_ticker = input("Enter a Ticker Symbol (e.g., AAPL): ")
    test_ticker = "NVDA" # Example: Try NVDA, AAPL, MSFT, GOOGL or an invalid one like "XYZABC"

    print(f"\n--- Attempting to fetch data for: {test_ticker} ---")

    try:
        fetcher = StockDataFetcher(test_ticker)

        print("\n1. Company Info:")
        company_info = fetcher.get_company_info()
        # Print selected items for brevity
        print(f"   Name: {company_info.get('longName', 'N/A')}")
        print(f"   Sector: {company_info.get('sector', 'N/A')}")
        print(f"   Industry: {company_info.get('industry', 'N/A')}")
        print(f"   Description Snippet: {company_info.get('longBusinessSummary', 'N/A')[:150]}...") # First 150 chars

        print("\n2. Quote Data:")
        quote_data = fetcher.get_quote_data()
        print(f"   Current Price: {quote_data.get('currentPrice', 'N/A')}")
        print(f"   Market Cap: {quote_data.get('marketCap', 'N/A'):,}") # Format with commas
        print(f"   Trailing P/E: {quote_data.get('trailingPE', 'N/A')}")
        print(f"   Forward P/E: {quote_data.get('forwardPE', 'N/A')}")
        print(f"   Dividend Yield Pct (Processed): {quote_data.get('dividendYield_pct', 'N/A')}")
        print(f"   Trailing Annual Dividend Yield Pct: {quote_data.get('trailingAnnualDividendYield_pct', 'N/A')}")

        print("\n3. Financial Summary (Latest Annual):")
        financial_summary = fetcher.get_financial_summary()
        fin_year = financial_summary.get('financials_year', 'N/A')
        revenue = financial_summary.get('latest_annual_revenue')
        earnings = financial_summary.get('latest_annual_earnings')
        print(f"   Year: {fin_year}")
        print(f"   Revenue: {revenue:,.0f}" if revenue is not None else "N/A")
        print(f"   Net Income (Earnings): {earnings:,.0f}" if earnings is not None else "N/A")


        print("\n4. Recent News Headlines:")
        news_list = fetcher.get_news()
        if news_list:
            for i, article in enumerate(news_list[:3]): # Print first 3 news items
                print(f"   - {article.get('title', 'No Title')} ({article.get('publisher', 'N/A')})")
        else:
            print("   No news articles retrieved.")

    except ValueError as ve:
        print(f"\nError initializing fetcher or fetching data: {ve}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

    print(f"\n--- Data fetching example finished for: {test_ticker} ---")
