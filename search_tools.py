import json
import os
import requests
from langchain.tools import BaseTool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchTools(BaseTool):
    name = "Search the internet"
    description = "Use this tool to search the internet for information. This tool returns 8-9 results from Google search engine."

    @staticmethod
    def _run(query: str):
        """Use this tool to search the internet for information."""
        logger.info("Searching the internet...")
        top_result_to_return = 10  # Increased to 10 to ensure we get at least 8-9 results
        url = "https://google.serper.dev/search"
        payload = json.dumps(
            {"q": query, "num": top_result_to_return, "tbm": "nws"})
        headers = {
            'X-API-KEY': os.environ.get('SERPER_API_KEY'),
            'content-type': 'application/json'
        }
        if not headers['X-API-KEY']:
            error_message = "SERPER_API_KEY is not set in the environment variables."
            logger.error(error_message)
            return {"error": error_message}
        
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"HTTP Request failed: {e}")
            return {"error": "Failed to fetch news due to network issues."}

        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from Serper API.")
            return {"error": "Invalid JSON response from Serper API."}

        if 'organic' not in data:
            error_message = "No 'organic' key in Serper API response. Possible invalid API key or no results found."
            logger.error(error_message)
            return {"error": error_message}
        else:
            results = data['organic']
            news_list = []
            logger.info(f"Results fetched: {len(results[:top_result_to_return])}")
            for result in results[:top_result_to_return]:
                try:
                    title = result.get('title', 'No Title')
                    url_link = result.get('link', 'No URL')
                    summary = result.get('snippet', 'No Summary')
                    news_item = {
                        "title": title,
                        "url": url_link,
                        "summary": summary
                    }
                    news_list.append(news_item)
                except KeyError as e:
                    logger.warning(f"Missing key {e} in result. Skipping.")
                    continue
            return news_list[:9]  # Return at most 9 results

    def _arun(self, query: str):
        """Optional: Implement asynchronous run if needed."""
        raise NotImplementedError("This tool does not support async.")