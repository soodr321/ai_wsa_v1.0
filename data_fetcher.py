import yfinance as yf
import pandas as pd

class StockDataFetcher:
    """
    Fetches various stock data points for a given ticker symbol using the yfinance library.
    Enhanced for V1.5 to provide comprehensive inputs for FVEAgent, including historical financials
    structured as a dictionary of lists (e.g., {'netIncome': [val_yr1, val_yr2, ...]}).
    """
    def __init__(self, ticker: str, historical_years: int = 4):
        if not isinstance(ticker, str) or not ticker:
            raise ValueError("Ticker symbol must be a non-empty string.")
        if not isinstance(historical_years, int) or historical_years <= 0:
            raise ValueError("Historical years must be a positive integer.")

        self.ticker_symbol = ticker.upper()
        self.stock = yf.Ticker(self.ticker_symbol)
        self.historical_years = historical_years

        self._info = None
        self._annual_income_statement_df = None
        self._annual_cash_flow_df = None
        self._annual_balance_sheet_df = None
        self._news = None

        try:
            self._info = self.stock.info
            if not self._info or self._info.get('regularMarketPrice') is None:
                if self._info.get('marketCap') == 0 and self._info.get('regularMarketPrice') is None:
                     raise ValueError(f"No data found for ticker '{self.ticker_symbol}'. It might be invalid, delisted, or lack recent info.")
                print(f"Warning: Could not retrieve complete basic info for ticker '{self.ticker_symbol}'. Data might be limited.")
        except Exception as e:
             raise ValueError(f"Could not initialize StockDataFetcher for '{self.ticker_symbol}'. Error fetching .info: {e}")

    def _get_historical_financial_statement(self, statement_type: str) -> pd.DataFrame | None:
        # Same as previous version (fetches and caches the DataFrame)
        statement_attr_map = {
            'income': ('_annual_income_statement_df', self.stock.financials),
            'cashflow': ('_annual_cash_flow_df', self.stock.cashflow),
            'balancesheet': ('_annual_balance_sheet_df', self.stock.balance_sheet)
        }
        if statement_type not in statement_attr_map:
            raise ValueError(f"Invalid statement type: {statement_type}")
        cached_attr_df, statement_data_call_df = statement_attr_map[statement_type]
        if getattr(self, cached_attr_df) is not None:
            return getattr(self, cached_attr_df)
        try:
            statement_df = statement_data_call_df
            if statement_df is None or statement_df.empty:
                setattr(self, cached_attr_df, pd.DataFrame())
                return pd.DataFrame()
            num_available_years = statement_df.shape[1]
            years_to_fetch = min(num_available_years, self.historical_years)
            historical_df = statement_df.iloc[:, :years_to_fetch]
            setattr(self, cached_attr_df, historical_df) # Cache the sliced df
            return historical_df
        except Exception as e:
            print(f"Error fetching {statement_type} DataFrame for {self.ticker_symbol}: {e}")
            setattr(self, cached_attr_df, pd.DataFrame())
            return pd.DataFrame()

    def _find_financial_item_in_series(self, series: pd.Series | None, possible_keys: list[str]) -> float | None:
        # Simplified helper for single series
        if series is None or series.empty:
            return None
        for key in possible_keys:
            if key in series.index:
                value = series[key]
                return float(value) if not pd.isna(value) else None
        return None

    def get_historical_annual_financial_data_dict_of_lists(self) -> dict:
        """
        Retrieves key items from annual Income Stmts, Cash Flow, and Balance Sheets
        for 'self.historical_years', structured as a dictionary of lists.
        Each list contains values for a financial item over the years, most recent first.
        Includes a 'years' list [year1, year2, ...].
        """
        historical_data_dict = {
            'years': [], 'netIncome_list': [], 'depreciationIncomeStmt_list': [],
            'cashFlowFromOperations_list': [], 'capitalExpenditures_list': [],
            'changeInWorkingCapital_list': [], 'depreciationAndAmortizationCF_list': [],
            'totalDebt_list': [], 'totalRevenue_list': []
        }

        income_stmt_df = self._get_historical_financial_statement('income')
        cash_flow_df = self._get_historical_financial_statement('cashflow')
        balance_sheet_df = self._get_historical_financial_statement('balancesheet')

        # Determine common years available across all relevant statements (using income as primary)
        # yfinance DFs have columns as timestamps (years). We want to iterate up to self.historical_years
        # or the minimum number of available columns if less.
        
        num_years_to_process = 0
        if not income_stmt_df.empty:
            num_years_to_process = income_stmt_df.shape[1]
        elif not cash_flow_df.empty:
             num_years_to_process = cash_flow_df.shape[1]
        elif not balance_sheet_df.empty:
            num_years_to_process = balance_sheet_df.shape[1]
        
        if num_years_to_process == 0:
            print(f"No historical financial data columns found for {self.ticker_symbol}.")
            return historical_data_dict # Return empty lists

        processed_years_count = 0
        for i in range(num_years_to_process):
            # Assume columns are sorted most recent first by yfinance
            # Year extraction from income statement is prioritized
            year_val = None
            if not income_stmt_df.empty and i < income_stmt_df.shape[1]:
                year_val = income_stmt_df.columns[i].year
            elif not cash_flow_df.empty and i < cash_flow_df.shape[1]:
                year_val = cash_flow_df.columns[i].year
            elif not balance_sheet_df.empty and i < balance_sheet_df.shape[1]:
                year_val = balance_sheet_df.columns[i].year
            
            if year_val is None: # Should not happen if num_years_to_process > 0
                continue

            historical_data_dict['years'].append(year_val)

            # Income Statement Items
            inc_series = income_stmt_df.iloc[:, i] if not income_stmt_df.empty and i < income_stmt_df.shape[1] else pd.Series(dtype=float)
            historical_data_dict['netIncome_list'].append(self._find_financial_item_in_series(inc_series, ['Net Income', 'NetIncome', 'NetIncomeContinuousOperations']))
            historical_data_dict['depreciationIncomeStmt_list'].append(self._find_financial_item_in_series(inc_series, ['Depreciation', 'DepreciationAndAmortization', 'DepreciationAmortizationDepletion']))
            historical_data_dict['totalRevenue_list'].append(self._find_financial_item_in_series(inc_series, ['Total Revenue', 'Revenue', 'TotalRevenue']))

            # Cash Flow Statement Items
            cf_series = cash_flow_df.iloc[:, i] if not cash_flow_df.empty and i < cash_flow_df.shape[1] else pd.Series(dtype=float)
            historical_data_dict['cashFlowFromOperations_list'].append(self._find_financial_item_in_series(cf_series, ['Total Cash From Operating Activities', 'Cash Flow From Continuing Operating Activities', 'Operating Cash Flow', 'CashFlowFromOperatingActivities']))
            historical_data_dict['capitalExpenditures_list'].append(self._find_financial_item_in_series(cf_series, ['Capital Expenditures', 'CapitalExpenditures', 'Purchase Of Property Plant And Equipment', 'Net PPE Purchase And Sale']))
            historical_data_dict['changeInWorkingCapital_list'].append(self._find_financial_item_in_series(cf_series, ['Change In Working Capital', 'Change To Working Capital', 'ChangeInWorkingCapital', 'Effect Of Exchange Rate ChangesOnCash']))
            historical_data_dict['depreciationAndAmortizationCF_list'].append(self._find_financial_item_in_series(cf_series, ['Depreciation And Amortization', 'Depreciation', 'DepreciationAmortizationDepletion', 'DepreciationAndAmortizationTotal']))
            
            # Balance Sheet Items
            bs_series = balance_sheet_df.iloc[:, i] if not balance_sheet_df.empty and i < balance_sheet_df.shape[1] else pd.Series(dtype=float)
            historical_data_dict['totalDebt_list'].append(self._find_financial_item_in_series(bs_series, ['Total Debt', 'Net Debt', 'Long Term Debt', 'LongTermDebtAndCapitalLeaseObligation', 'TotalLiabilitiesNetMinorityInterest', 'Total Liab']))
            
            processed_years_count += 1
            if processed_years_count >= self.historical_years : # Ensure we don't exceed requested years
                break
                
        return historical_data_dict

    def get_company_info(self) -> dict:
        # Same as previous version
        if self._info: return self._info
        try:
            self._info = self.stock.info
            return self._info if self._info else {}
        except Exception: return {}

    def get_quote_data(self) -> dict:
        # Same as previous version
        quote_data = {}
        try:
            info = self.get_company_info()
            if not info:
                 return {'currentPrice': None, 'marketCap': None, 'trailingPE': None, 'forwardPE': None, 'trailingEps': None, 'forwardEps': None}
            quote_data['currentPrice'] = info.get('currentPrice') or info.get('regularMarketPrice')
            quote_data['marketCap'] = info.get('marketCap')
            quote_data['trailingPE'] = info.get('trailingPE')
            quote_data['forwardPE'] = info.get('forwardPE')
            quote_data['trailingEps'] = info.get('trailingEps')
            quote_data['forwardEps'] = info.get('forwardEps')
            return quote_data
        except Exception as e:
            print(f"Error fetching quote data for {self.ticker_symbol}: {e}")
            return quote_data # Return partial if error

    def get_news(self, max_articles: int = 5) -> list:
        # Same as previous version
        if self._news is not None: return self._news[:max_articles]
        try:
            news_data = self.stock.news
            if not news_data: self._news = []; return []
            self._news = [{'title': item.get('title'), 'link': item.get('link'),
                           'publisher': item.get('publisher'), 'providerPublishTime': item.get('providerPublishTime')}
                          for item in news_data]
            return self._news[:max_articles]
        except Exception as e:
            print(f"Error fetching news for {self.ticker_symbol}: {e}")
            self._news = []; return []

    def get_fve_inputs(self) -> dict:
        """
        Gathers and structures all necessary data for the FVEAgent.
        Historical financials are a dict of lists (e.g., {'netIncome_list': [val_y1, val_y2,...]}).
        """
        print(f"Starting get_fve_inputs for {self.ticker_symbol} (up to {self.historical_years} years)...")
        info_data = self.get_company_info()
        quote_data = self.get_quote_data()
        
        historical_fin_dict_of_lists = self.get_historical_annual_financial_data_dict_of_lists()

        fve_inputs = {
            'ticker': self.ticker_symbol,
            'companyName': info_data.get('longName'),
            'currentPrice': quote_data.get('currentPrice'),
            'marketCap': quote_data.get('marketCap'),
            'sharesOutstanding': info_data.get('sharesOutstanding'),
            'beta': info_data.get('beta'),
            'trailingPE': quote_data.get('trailingPE'),
            'forwardPE': quote_data.get('forwardPE'),
            'trailingEps': quote_data.get('trailingEps'),
            'forwardEps': quote_data.get('forwardEps'),
            'historical_financials': historical_fin_dict_of_lists, # Dict of lists
            'news': self.get_news(max_articles=5)
        }
        
        print(f"Data collection complete for FVE inputs for {self.ticker_symbol}.")
        if fve_inputs['beta'] is None:
            print(f"Warning for {self.ticker_symbol}: Beta is None. DCF may not be feasible.")
        if fve_inputs['sharesOutstanding'] is None:
            print(f"CRITICAL WARNING for {self.ticker_symbol}: Shares Outstanding is None. FVE per share calculation will fail.")
        
        years_fetched = len(historical_fin_dict_of_lists.get('years', []))
        if years_fetched == 0:
            print(f"Warning for {self.ticker_symbol}: Historical financials are empty.")
        elif years_fetched < self.historical_years:
            print(f"Warning for {self.ticker_symbol}: Fetched {years_fetched} years of financials, less than requested {self.historical_years}.")

        # Check critical data for FCFE_0 in the most recent year (first element of lists)
        ni_list = historical_fin_dict_of_lists.get('netIncome_list', [])
        da_cf_list = historical_fin_dict_of_lists.get('depreciationAndAmortizationCF_list', [])
        capex_list = historical_fin_dict_of_lists.get('capitalExpenditures_list', [])

        most_recent_ni = ni_list[0] if ni_list and ni_list[0] is not None else None
        most_recent_da_cf = da_cf_list[0] if da_cf_list and da_cf_list[0] is not None else None
        most_recent_capex = capex_list[0] if capex_list and capex_list[0] is not None else None # Capex can be 0

        if most_recent_ni is None or most_recent_da_cf is None or most_recent_capex is None:
            print(f"Warning for {self.ticker_symbol}: Critical data for FCFE_0 (NI, D&A_CF, Capex) might be missing or None in the most recent financial year.")

        print(f"Finished get_fve_inputs for {self.ticker_symbol}.")
        return fve_inputs

# --- Example Usage Block (Updated for dict of lists) ---
if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "NFLX", "NONEXISTENTTICKER"] 

    for test_ticker in test_tickers:
        print(f"\n--- Attempting to fetch FVE inputs for: {test_ticker} (Max 4 years) ---")
        try:
            fetcher = StockDataFetcher(ticker=test_ticker, historical_years=4) 
            fve_data = fetcher.get_fve_inputs()

            print(f"\n--- FVE Inputs for {test_ticker} ---")
            print(f"Company Name: {fve_data.get('companyName', 'N/A')}")
            # ... print other scalar values like ticker, currentPrice, sharesOutstanding, beta ...

            hist_fin = fve_data.get('historical_financials', {})
            print("\nHistorical Financials (Dictionary of Lists, up to 4 years, most recent first):")
            print(f"  Years Reported: {hist_fin.get('years', [])}")
            print(f"  Net Income List: {hist_fin.get('netIncome_list', [])}")
            print(f"  D&A (CFS) List: {hist_fin.get('depreciationAndAmortizationCF_list', [])}")
            print(f"  Capex List: {hist_fin.get('capitalExpenditures_list', [])}")
            print(f"  CFO List: {hist_fin.get('cashFlowFromOperations_list', [])}")
            print(f"  Change in NWC List: {hist_fin.get('changeInWorkingCapital_list', [])}")
            print(f"  Total Revenue List: {hist_fin.get('totalRevenue_list', [])}")
            print(f"  Total Debt List: {hist_fin.get('totalDebt_list', [])}")
            
            # ... print news ...

        except ValueError as ve:
            print(f"\nInput Error or Critical Fetch Failure for {test_ticker}: {ve}")
        except Exception as e:
            print(f"\nAn unexpected error occurred for {test_ticker}: {e}")
        print(f"\n--- Data fetching example finished for: {test_ticker} ---")