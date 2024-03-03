# https://github.com/JerBouma/FinanceToolkit
from financetoolkit import Toolkit
import os
import pandas as pd
from sharkfin.util.cache import RedisCache
from sharkfin.util.logger import Log

logger = Log().get_logger()

# Load API Key from environment
API_KEY = os.getenv('FMP_API_KEY')
CACHE = RedisCache()
CACHE_TTL_1H = 60 * 60
CACHE_TTL_1DAY = 24 * CACHE_TTL_1H
CACHE_TTL_1WEEK = 7 * CACHE_TTL_1DAY
CACHE_TTL_1MONTH = 30 * CACHE_TTL_1DAY

# Change this to invalidate all cache
CACHE_VERSION = '24.2.19.e'


class FMP_CONSTANTS:
    """
    Cashflow statement indices:
    ['Net Income', 'Depreciation and Amortization', 'Deferred Income Tax',
       'Stock Based Compensation', 'Change in Working Capital',
       'Accounts Receivables', 'Inventory', 'Accounts Payables',
       'Other Working Capital', 'Other Non Cash Items',
       'Cash Flow from Operations', 'Property, Plant and Equipment',
       'Acquisitions', 'Purchases of Investments', 'Sales of Investments',
       'Other Investing Activities', 'Cash Flow from Investing',
       'Debt Repayment', 'Common Stock Issued', 'Common Stock Purchased',
       'Dividends Paid', 'Other Financing Activities',
       'Cash Flow from Financing', 'Forex Changes on Cash',
       'Net Change in Cash', 'Cash End of Period', 'Cash Beginning of Period',
       'Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow']

    Profit ratio indices:
    'Gross Margin', 'Operating Margin', 'Net Profit Margin',
       'Interest Coverage Ratio', 'Income Before Tax Profit Margin',
       'Effective Tax Rate', 'Return on Assets', 'Return on Equity',
       'Return on Invested Capital', 'Return on Capital Employed',
       'Return on Tangible Assets', 'Income Quality Ratio',
       'Net Income per EBT', 'Free Cash Flow to Operating Cash Flow Ratio',
       'EBT to EBIT Ratio', 'EBIT to Revenue']
    """
    FREE_CASH_FLOW = "Free Cash Flow"
    OPERATING_CASH_FLOW = "Operating Cash Flow"
    ROIC = 'Return on Invested Capital'
    ROCE = 'Return on Capital Employed'

    # My constants
    FCF_GROWTH = 'FCF Growth'
    OCF_GROWTH = 'OCF Growth'


class StockUtil:
    def get_cashflow_growth_rate(ticker) -> list:
        toolkit = Toolkit(tickers=[ticker], api_key=API_KEY, quarterly=True)
        cashflow_growth_ttm = toolkit.get_cash_flow_statement(
            trailing=4, growth=True)
        df = cashflow_growth_ttm.loc[['Free Cash Flow']]

        # get the average yoy FCF growth rate over 1y, 3y and 5y
        last1 = df.iloc[:, -1:].mean(axis=1)
        last3 = df.iloc[:, -13:].mean(axis=1)
        last5 = df.iloc[:, -21:].mean(axis=1)

        # Call me crazy but I'm returning all these averages for 1-5y of FCF and OCF growth
        # This lets the calling function to choose the number they want
        result = [
            last1[FMP_CONSTANTS.FREE_CASH_FLOW],
            last3[FMP_CONSTANTS.FREE_CASH_FLOW],
            last5[FMP_CONSTANTS.FREE_CASH_FLOW],
        ]
        logger.info(f'get_cashflow_growth_rate: {result}')
        return result


class StockData:
    _toolkit: Toolkit = None

    def __init__(self, ticker, quarterly=False):
        self._quarterly = quarterly
        self._ticker = ticker
        self._toolkit = Toolkit(
            tickers=[ticker], quarterly=quarterly, api_key=API_KEY)

    def _build_cache_key(self, function_name, *args, **kwargs):
        # Creates a unique key for each function call (include ticker, etc.)
        key_prefix = f"{self._ticker}_{function_name}_{CACHE_VERSION}"
        if args:
            key_prefix += "_" + "_".join(str(arg) for arg in args)
        if kwargs:
            key_prefix += "_" + "_".join(f"{k}={v}" for k, v in kwargs.items())
        return key_prefix

    def get_historical_data(self) -> pd.DataFrame:
        cache_key = self._build_cache_key("get_historical_data")
        cached_result = CACHE.get_dataframe(cache_key)
        result = None
        if cached_result is not None:
            result = cached_result
        else:
            result = self.toolkit().get_historical_data()
            CACHE.set_dataframe(cache_key=cache_key,
                                value=result, ex=CACHE_TTL_1DAY)
        return result

    def get_current_price(self) -> float:
        cache_key = self._build_cache_key("get_current_price")
        cached_result = CACHE.get(cache_key)
        result = None
        if cached_result is not None:
            result = float(cached_result)
        else:
            historical = self.get_historical_data()
            result = float(historical.iloc[-1]['Adj Close'][self._ticker])
            CACHE.set(cache_key, result, ex=CACHE_TTL_1DAY)
        return result

    def models(self):
        result = self.toolkit().models
        return result

    def toolkit(self) -> Toolkit:
        result = self._toolkit
        return result

    def estimate_dcf(self):
        import math
        fcf_growth_rates = StockUtil.get_cashflow_growth_rate(self._ticker)
        low = min(fcf_growth_rates)
        high = max(fcf_growth_rates)
        low_estimate = self.calculate_dcf_value(
            growth_rate=low,
            perpetual_growth_rate=max(
                math.sqrt(low), 0.03),  # no smaller than 3%
            periods=10,
            wacc=0.08
        )
        high_estimate = self.calculate_dcf_value(
            growth_rate=high*1.1,
            perpetual_growth_rate=max(
                math.sqrt(high), 0.05),  # no smaller than 5%
            periods=10,
            wacc=0.06
        )
        logger.info(
            f'estimate_dcf result:\nlow={low_estimate},high={high_estimate}')

        current_price = self.get_current_price()
        result = pd.DataFrame({
            'estimates': [low_estimate, high_estimate],
            'growth rate': [low, high],
            'percent of current price': [low_estimate/current_price, high_estimate/current_price]
        })
        logger.warn(f'estimate_dcf: {result}')
        return result

    def calculate_dcf_value(
            self,
            growth_rate: float = 0.11,
            perpetual_growth_rate: float = 0.03,
            wacc: float = 0.08,
            periods: int = 10,
    ) -> float:
        cache_key = self._build_cache_key(
            "calculate_dcf_value", growth_rate, perpetual_growth_rate, wacc, periods)
        cached_result = CACHE.get(cache_key)
        result = None
        if cached_result is not None:
            result = float(cached_result)
        else:
            dcf_valuation = self.models().get_intrinsic_valuation(
                growth_rate=growth_rate,
                perpetual_growth_rate=perpetual_growth_rate,
                weighted_average_cost_of_capital=wacc,
                periods=periods,
                # cash_flow_type="Operating Cash Flow",  # TODO - try this param
                rounding=2,
            )

            logger.debug(f'dcf_valuation dataframe: {dcf_valuation}')
            result = float(
                dcf_valuation.loc[(self._ticker, 'Intrinsic Value')])
            logger.warn(result)
            CACHE.set(cache_key, result, ex=CACHE_TTL_1WEEK)
        logger.debug(f'calculate_dcf_value: {result}')
        return result

    def cashflow_statement(self, trailing: int | None = None, growth=False) -> pd.DataFrame:
        cache_key = self._build_cache_key(
            "cashflow_statement", trailing, growth)
        cached_result = CACHE.get_dataframe(cache_key)

        result = None
        if cached_result is not None:
            result = cached_result
        else:
            result = self.toolkit().get_cash_flow_statement(
                overwrite=True,  # todo: might be worth playing with
                growth=growth,
                trailing=trailing
            )
            new_headers = [str(period_obj) for period_obj in result.columns]
            result.columns = new_headers
            result = result.reset_index()
            CACHE.set_dataframe(cache_key, result, ex=CACHE_TTL_1WEEK)

        logger.debug(f'cashflow_statement:\n{result}')
        return result

    def income_statement(self, trailing: int | None = None, growth=False) -> pd.DataFrame:
        cache_key = self._build_cache_key(
            "income_statement", trailing, growth)
        cached_result = CACHE.get_dataframe(cache_key)
        result = None
        if cached_result is not None:
            result = cached_result
        else:
            result = self.toolkit().get_income_statement(
                overwrite=True,  # todo: might be worth playing with
                growth=growth,
                trailing=trailing
            )

            new_headers = [str(period_obj) for period_obj in result.columns]
            result.columns = new_headers
            result = result.reset_index()
            CACHE.set_dataframe(cache_key, result, ex=CACHE_TTL_1WEEK)

        logger.debug(f'income_statement:\n{result}')
        return result

    def get_piotroski_score(self):
        cache_key = self._build_cache_key("get_piotroski_score")
        cached_result = CACHE.get_dataframe(cache_key)
        result = None
        if cached_result is not None:
            result = cached_result
        else:
            result = self.models().get_piotroski_score()
            new_headers = [str(period_obj) for period_obj in result.columns]
            result.columns = new_headers
            result = result.reset_index().drop('level_0', axis=1)
            CACHE.set_dataframe(cache_key, result, ex=CACHE_TTL_1WEEK)

        logger.debug(f'get_piotroski_score:\n{result}')
        return result
