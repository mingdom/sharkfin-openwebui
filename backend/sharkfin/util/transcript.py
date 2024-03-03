from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List
import datetime
from sharkfin.util.fmp import FMP
from sharkfin.util.logger import Log

logger = Log().get_logger()


def get_batch_earnings_transcript_multiyear(symbol: str, years: List[str]):
    transcripts = []
    for year in years:
        try:
            transcript = FMP.get_batch_earnings_call_transcript(
                symbol=symbol, year=year)
            if len(transcript) > 0:
                transcripts.extend(transcript)
        except Exception as e:
            logger.error(
                f"Failed to get transcript data for year {year} and ticker {symbol}: {e}")
    return transcripts


def _search_earnings_transcripts(query: str, symbol: str, years: List[str]):
    transcripts = get_batch_earnings_transcript_multiyear(symbol, years)

    # Split into chunks with `chunk_size` tokens each, and `chunk_overlap` tokens overlap between successive chunks,
    # we might want to experiment with different parameters.
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=150, chunk_overlap=22)

    all_documents = []
    for transcript in transcripts:
        # Split each earnings call transcript into document chunks and store it in texts
        documents = text_splitter.create_documents([transcript['content']])
        for document in documents:  # The split chunks are called documents
            # Add ticker symbol and date of earnings call to the metadata of each document
            # to easily identify its source in future
            document.metadata = {
                "title": f"{transcript['symbol']} Earnings Call: {transcript['date']}"}
        # Add all the documents into document list of all news articles
        all_documents.extend(documents)

    if len(all_documents) == 0:
        return []

    db = Chroma.from_documents(all_documents, OpenAIEmbeddings())

    # k=4 means the similarity_search function will return the 4 most similar items
    # from the database based on their vector representations
    similar_docs = db.similarity_search(query, k=4)
    return similar_docs


@tool
def get_earnings_transcript_summary(symbol: str, year: int | None = None, quarter: int | None = None):
    """
    Get the latest earnings call transcript for a company or a particular quarter's earning transcript.

    Parameters:
        symbol: The ticker symbol for the company
        year: the fiscal year for the transcript. Optional.
        quarter: the quarter for the transcript. Optional.

    Returns:
        str: The summarized earnings call transcript text for the latest (default) quarter or the specified quarter
    """
    transcript = FMP.get_earning_call_transcript(
        symbol=symbol, year=year, quarter=quarter)

    return f'''
        Here's the earnings data for ${symbol}:\n{transcript}.
        The date of the earning call was [TODO: Fill date]

        Next steps: write the following sections based on the data above
            1. Key Metrics: Note down all key metrics such as revenue and revenue growth, EPS and EPS growth.
            2. Guidance: Note down the management guidance for the upcoming quarter or year
            3. Sentiment: Provide an overall sentiment for the earnings and outlook.
            4. Summary: Finally, summarize the earnings call transcript
    '''

@tool
def get_analyst_surprise_against_earnings(symbol):
    """
    Get data on actual earnings vs. analyst expectations for EPS for a given company.

    Parameters:
        symbol: The ticker symbol for the company

    Returns:
        str: How the earnings compare against analyst expectations
    """
    analyst_surprise = FMP.get_earnings_surprise(symbol=symbol)
    return f'''
        Here's how {symbol}'s actual earnings compare against analyst expectations: analyst_surprise
    '''


@tool
def search_earnings_transcripts(query: str, symbol: str, years: List[str] = [datetime.datetime.now().year]):
    """
    Search a company's earnings transcripts for a particular query over multiple years.

    Parameters:
        query: Question related to company earnings
        symbol: The ticker symbol for the company
        years: a list of years

    Returns:
        str: Relevant information regarding the search query
    """
    if not symbol or not query:
        return ""

    similar_docs = _search_earnings_transcripts(query, symbol, years)
    logger.debug(f'search_earnings_transcripts documents:\n{similar_docs}')

    if len(similar_docs) == 0:
        return ""

    return f'''
        Below are the search results found in the earnings transcripts:
        ---
        {similar_docs}
        ---
        for each item in the list above, do the following:
            1. Select complete sentences from "page_content" field and put it in blockquote with markdown. The part in blockquote should be verbatim.
            2. For each blockquote from #1, give context for which earnings call it came from, and source of the quote
            3. Repeat

        After completing the above. Feel free to summarize the search result at the end.
    '''
