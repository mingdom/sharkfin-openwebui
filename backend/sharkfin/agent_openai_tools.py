from langchain_community.utilities.google_serper import GoogleSerperAPIWrapper
from langchain_core.tools import tool, Tool
from sharkfin.util.stockdata import StockData
from sharkfin.util.logger import Log
import os
from sharkfin.util.fmp import FMP

from sharkfin.util.transcript import search_earnings_transcripts, get_earnings_transcript_summary

logger = Log().get_logger()


def get_agent_tools():
    tools = [
        get_company_profile,
        # get_stock_intrinsic_value_dcf, # TODO - disabled for now
        get_discounted_cashflow_fmp,
        get_earnings_transcript_summary,
        # search_earnings_transcripts, # TODO - disabled for now, need more testing
        cashflow_statement,
        income_statement,
        technical_analysis_dailychart,
        historical_price_volume_eod,
        analyst_earning_surprise,
        analyst_estimates,
        analyst_price_targets,
        # social_sentiment, # not that useful
    ]

    if os.environ.get("SERPER_API_KEY"):
        search = GoogleSerperAPIWrapper()
        tools.append(
            Tool(
                name="Search",
                func=search.run,
                description="useful for when you need to ask with search if other tools cannot provide answer",
            )
        )

    return tools


"""
Agent tools below:
"""


@tool
def social_sentiment(symbol: str):
    """
    Gets the social sentiment of a given stock

    Returns:
    - A list of social sentiment data for the stock, one entry per day. Most recent first
    """
    sentiment_per_day = FMP.get_social_sentiment(symbol)

    return f"""
        The daily social sentiment for {symbol} is below:
        ---
        {sentiment_per_day}
        ---
        Summarize the above by:
        1. Compute the average `stocktwitsSentiment` of the last week
        2. How many posts is this based on? Sum `stocktwitsPosts` of the last week
        3. Summarize the data to provide an overall sentiment rating of either: Bearish or Bullish
    """


@tool
def historical_price_volume_eod(symbol: str):
    """
    Gets the historical EOD daily price and volume data for a stock
    """
    return FMP.get_historical_price_eod(symbol=symbol)


@tool
def analyst_estimates(symbol: str):
    """
    Get the analyst estimates or expectations for a given company stock ticker symbol in upcoming quarters

    Parameters:
    - symbol: The stock ticker

    Returns:
    - JSON data for the analyst earning estimates to be summarized or used in an answer
    """
    data = FMP.get_analyst_estimates(symbol)
    return f"""
        Here is the JSON representation of the analyst expectations for {symbol}:
        ---
            {data}
        ---
        Summarize the data above. Make sure to specify the date for each estimate.
    """


@tool
def analyst_price_targets(symbol: str):
    """
    Get the analyst price target summary for a stock.
    Can be used in conjunction to DCF/Intrinsic value to help evaluate stock price.

    Parameters:
    - symbol: The stock ticker

    Returns:
    - Analyst price target summary
    """
    price_targets = FMP.get_price_target_summary(symbol=symbol)[:10]
    return f"""
    Summary of analyst price targets below:
        {price_targets}
    """


@tool
def analyst_earning_surprise(symbol: str):
    """
    Compare actual earnings result against analyst expectations, for the EPS metric.

    Parameters:
    - symbol: The stock ticker

    Returns:
    - Analysis of the analyst earning surprise - actual vs. expectations
    """

    data = FMP.get_earnings_surprise(symbol)
    return f"""
        Here is the JSON representation of the analyst earning surprise for {symbol}:
        ---
            {data}
        ---
        Summarize the data above. Make sure to specify the date when using the data to answer questions
    """


@tool
def cashflow_statement(symbol: str, quarterly: bool) -> str:
    """
    Get cashflow statements for a given stock

    Parameters:
    - ticker: The stock ticker.
    - quarterly (bool): Flag indicating whether to retrieve quarterly data vs annual. Default is True.

    Returns:
    - str: A string containing the cash flow statement in a csv.
    - examples of metrics includes:
        - net income
        - cashflow from investing
        - net change in cash
        - free cash flow
        - operating cash flow
        - capital expenditure
        - and many other metrics typically found on the cashflow statement
    """
    period = "annual"
    if quarterly:
        period = "quarter"

    cashflow = FMP.get_cashflow_statement(symbol=symbol, period=period)[:12]
    return f"Here's the cashflow JSON: {cashflow}.\nUse this to answer questions about cashflow such as Free Cash Flow (FCF) or OCF"


@tool
def income_statement(symbol: str, quarterly: bool) -> str:
    """
    Get income statement for a given stock

    Parameters:
    - ticker: The stock ticker
    - quarterly (bool): Get the quarterly statements instead of annual

    Returns:
    - str: A string containing the income statement in csv.
    - metrics includes:
        - revenue
        - cost of goods sold (cogs)
        - gross profit ratio
        - gross profit
        - ebitda
        - ebitda ratio
        - operating income
        - net income
        - eps
        - eps diluted
        - and many other metrics typically found on the income statement
    """
    period = "annual"
    if quarterly:
        period = "quarter"

    income = FMP.get_income_statement(symbol=symbol, period=period)[:12]
    return f"""
        Here's the income statement as JSON: {income}.\nUse this to answer questions about the company's income such as revenue and eps
    """


@tool
def get_company_profile(symbol: str):
    """
    Get stock data for a given ticker.

    Parameters:
    - ticker: Stock ticker symbol.

    Returns:
    - str: A string containing company profile for the given ticker.
    """
    company_profile = FMP.get_company_profile(symbol)

    return f"""
        JSON containing the company profile information:\n{company_profile}
    """


# @tool
# TODO: this is deprecated for now
def get_stock_intrinsic_value_dcf(
    symbol: str,
    growth_rate: float,
    perpetual_growth_rate: float,
    wacc: float,
    periods: int,
):
    """
    Calculate the intrinsic value of a stock based on the Discounted Cash Flow (DCF) method.

    Parameters:
        symbol: The ticker symbol of the stock.

    Returns:
        The intrinsic value of a company based on discounted cashflow analysis.
    """
    stock_data = StockData(symbol)
    dcf = stock_data.calculate_dcf_value(
        growth_rate=growth_rate,
        perpetual_growth_rate=perpetual_growth_rate,
        wacc=wacc,
        periods=periods,
    )
    return f"""
        Here is the intrinsic value for the stock based on DCF compared with the current price:
        {dcf}
        Note:
         - If the intrinsic value is lower than the current price, that implies the current price is overvalued.
         - If the intrinsic value is higher, then that means the current stock is undervalued.
        Finally, give the user a percentage for how much the stock will go up and down according to the intrinsic value.
        """


@tool
def get_discounted_cashflow_fmp(symbol: str) -> str:
    """
    Calculate the intrinsic value of a stock based on the Discounted Cash Flow (DCF) method.

    Parameters:
        ticker: Stock ticker symbol

    Returns:
        str: Gives the user a DCF estimate of the stock's intrinsic value alongside its current price.
    Note that the growth rate and WACC rates are estimated based on FMP API's AI
    """
    dcf_value = FMP.get_dcf(symbol=symbol)
    return f"""
        Discounted cashflow value for {symbol}: {dcf_value}. [Show the DCF value as well as the current price]'
        Note: this is not financial advice nor an endorsement of the company. More research is needed!
    """


@tool
def technical_analysis_dailychart(symbol: str) -> str:
    """
    Perform technical analysis based on moving averages and RSI

    Parameters:
        ticker: The stock ticker

    Returns: The technical evaluation based on chart data of moving averages (EMA & WMA) and RSI.
    """

    # Trim results to the last 14 days to save tokens
    ema_20d = FMP.get_technical_indicator_1day(symbol=symbol, type="ema", period=20)[
        :14
    ]
    wma_50d = FMP.get_technical_indicator_1day(symbol=symbol, type="wma", period=50)[
        :14
    ]
    rsi_14d = FMP.get_technical_indicator_1day(symbol=symbol, type="rsi", period=14)[
        :14
    ]
    historical_price_volume = FMP.get_historical_price_eod(symbol=symbol)[:14]

    # TODO: Add daily movement chart and volume data into the analysis
    # https://financialmodelingprep.com/api/v3/historical-chart/1day/AAPL?apikey=44eb8a19dccc54b6ee00e6dda35927e0
    result = {
        "20d-EMA": ema_20d,
        "20d-WMA": wma_50d,
        # "WMA 200d": wma_200d,
        "14d-RSI": rsi_14d,
        "Historical Price & Volume data (last 14 days)": historical_price_volume,
    }

    return f"""
        The chart data used for technical analysis for {symbol} is below\n:
        ---
            {result}
        ---
        Based on the above data:
        1. Perform technical analysis:
            - If stock closed higher than open, that's positive, especially on high volume.
            - If stock closed lower than open, that's negative, especially on high volume.
            - Is the volume increasing or decreasing? Increasing volume means stronger signal (either positive or negative)
            - RSI will show if a stock is overbought (>60) or oversold (<30)
            - If stock is trading above 20 day EMA and 50 day WMA levels, that's positive. Otherwise negative
        2. Support: Provide one or more support levels below current price
        3. Resistance: Provide one or more resistance levels above current price
        4. Please rate the stock based on technical strength from 1-5, where 1 is "Strong Sell", 5 is "Strong Buy"
    """
