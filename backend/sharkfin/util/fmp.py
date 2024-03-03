import requests
import os
from pandas import DataFrame
import urllib
from typing import Literal

from sharkfin.util.logger import Log

logger = Log().get_logger()


class FMP:
    BASE_URL = "https://financialmodelingprep.com/api"

    API_KEY = os.environ.get("FMP_API_KEY")
    if not API_KEY:
        raise ValueError("FMP_API_KEY env variable not set!")

    @staticmethod
    def _build_url(
        endpoint: str, symbol: str = None, symbol_in_path: bool = True, **params
    ) -> str:
        if not endpoint:
            raise ValueError("endpoint")

        if not symbol:
            raise ValueError("symbol")

        query_string = urllib.parse.urlencode(params)

        url = f"{FMP.BASE_URL}/{endpoint}/{symbol}?apikey={FMP.API_KEY}&{query_string}"
        if not symbol_in_path:
            url = f"{FMP.BASE_URL}/{endpoint}?symbol={symbol}&apikey={FMP.API_KEY}&{query_string}"
        logger.debug(f"_build_url (params={params}): {url}")
        return url

    @staticmethod
    def _get_request_url(url: str) -> dict | DataFrame:
        response = requests.get(url)
        response.raise_for_status()
        result = response.json()
        logger.debug(f"GET {url}\n{result}")
        return result

    @staticmethod
    def _get_request(
        endpoint: str, symbol: str = None, symbol_in_path: bool = True, **params
    ) -> dict | DataFrame:
        url = FMP._build_url(
            symbol=symbol, endpoint=endpoint, symbol_in_path=symbol_in_path, **params
        )
        return FMP._get_request_url(url)

    @staticmethod
    def get_company_profile(symbol):
        return FMP._get_request(endpoint=Endpoints.COMPANY_PROFILE, symbol=symbol)

    @staticmethod
    def get_dcf(symbol):
        return FMP._get_request(endpoint=Endpoints.DISCOUNTED_CASHFLOW, symbol=symbol)

    @staticmethod
    def get_analyst_estimates(symbol):
        return FMP._get_request(endpoint=Endpoints.ANALYST_ESTIMATES, symbol=symbol)

    @staticmethod
    def get_earning_call_transcript(
        symbol: str, year: int | None = None, quarter: int | None = None
    ):
        params = {}
        if year:
            params["year"] = year
            if quarter:
                params["quarter"] = quarter

        return FMP._get_request(
            Endpoints.EARNING_CALL_TRANSCRIPT, symbol=symbol, **params
        )

    @staticmethod
    def get_batch_earnings_call_transcript(symbol: str, year: int):
        if not year:
            raise ValueError("year")
        params = {"year": year}
        return FMP._get_request(
            Endpoints.BATCH_EARNING_CALL_TRANSCRIPT, symbol=symbol, **params
        )

    @staticmethod
    def get_earnings_surprise(symbol: str):
        return FMP._get_request(endpoint=Endpoints.EARNINGS_SURPRISE, symbol=symbol)

    @staticmethod
    def get_income_statement(
        symbol: str, period: Literal["quarter", "annual"] = "annual"
    ) -> dict:
        return FMP._get_request(
            endpoint=Endpoints.INCOME_STATEMENT, symbol=symbol, period=period
        )

    @staticmethod
    def get_cashflow_statement(
        symbol: str, period: Literal["quarter", "annual"] = "annual"
    ) -> dict:
        return FMP._get_request(
            endpoint=Endpoints.EARNINGS_SURPRISE, symbol=symbol, period=period
        )

    @staticmethod
    def get_price_target_summary(symbol: str):
        # Note that the price_target API uses a symbol query param instead of in the path
        # hence we turn symbol_in_path to false below:
        return FMP._get_request(
            Endpoints.PRICE_TARGET_SUMMARY, symbol=symbol, symbol_in_path=False
        )

    @staticmethod
    def get_social_sentiment(symbol: str):
        return FMP._get_request(
            Endpoints.SOCIAL_SENTIMENT, symbol=symbol, symbol_in_path=False
        )

    @staticmethod
    def get_stock_news(tickers: str):
        # Additional query params: &limit=10&tickers=AAPL,FB
        return FMP._get_request(Endpoints.STOCK_NEWS, tickers=tickers, limit=10)

    @staticmethod
    def get_historical_price_eod(symbol: str, numdays=30):
        return FMP._get_request(Endpoints.HISTORICAL_PRICE_EOD, symbol=symbol).get(
            "historical"
        )[:numdays]

    @staticmethod
    def get_technical_indicator_1day(
        symbol: str,
        type: Literal["ema", "wma", "sma", "williams", "rsi"] = "wma",
        period: int = 20,
    ) -> list:
        return FMP._get_request(
            endpoint=Endpoints.TECHNICAL_INDICATOR_1DAY,
            symbol=symbol,
            type=type,
            period=period,
        )

    def __str__(self):
        return self[0]


class Endpoints:
    COMPANY_PROFILE = "v3/profile"
    DISCOUNTED_CASHFLOW = "v3/discounted-cash-flow"
    ANALYST_ESTIMATES = "v3/analyst-estimates"
    EARNING_CALL_TRANSCRIPT = "v3/earning_call_transcript"
    BATCH_EARNING_CALL_TRANSCRIPT = "v4/batch_earning_call_transcript"
    EARNINGS_SURPRISE = "v3/earnings-surprises"
    INCOME_STATEMENT = "v3/income-statement"
    CASHFLOW_STATEMENT = "v3/cashflow-statement"
    PRICE_TARGET_SUMMARY = "v4/price-target-summary"
    HISTORICAL_PRICE_EOD = "v3/historical-price-full"
    TECHNICAL_INDICATOR_1DAY = "v3/technical_indicator/1day"
    STOCK_NEWS = "v3/stock_news"
    SOCIAL_SENTIMENT = "v4/historical/social-sentiment"

    @staticmethod
    def get_method(endpoint: str):
        """
        This is needed in order to dynamically generate the playground UI in fmp-app.py
        """
        mapping = {
            Endpoints.COMPANY_PROFILE: FMP.get_company_profile,
            Endpoints.DISCOUNTED_CASHFLOW: FMP.get_dcf,
            Endpoints.ANALYST_ESTIMATES: FMP.get_analyst_estimates,
            Endpoints.EARNING_CALL_TRANSCRIPT: FMP.get_earning_call_transcript,
            Endpoints.BATCH_EARNING_CALL_TRANSCRIPT: FMP.get_batch_earnings_call_transcript,
            Endpoints.INCOME_STATEMENT: FMP.get_income_statement,
            Endpoints.CASHFLOW_STATEMENT: FMP.get_cashflow_statement,
            Endpoints.EARNINGS_SURPRISE: FMP.get_earnings_surprise,
            Endpoints.PRICE_TARGET_SUMMARY: FMP.get_price_target_summary,
            Endpoints.HISTORICAL_PRICE_EOD: FMP.get_historical_price_eod,
            Endpoints.TECHNICAL_INDICATOR_1DAY: FMP.get_technical_indicator_1day,
            Endpoints.STOCK_NEWS: FMP.get_stock_news,
            Endpoints.SOCIAL_SENTIMENT: FMP.get_social_sentiment,
        }

        return mapping.get(endpoint)

    @classmethod
    def as_list(cls):
        """
        returns the list of class variables as a list of strings.
        """
        return [
            getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith("__") and not callable(getattr(cls, attr))
        ]
