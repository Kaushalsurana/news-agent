# test_search_tools.py
import os
from dotenv import load_dotenv
from search_tools import SearchTools

def test_search_internet():
    # Load environment variables from .env file
    load_dotenv()

    query = "latest startup funding"
    results = SearchTools.search_internet(query)
    print(results)

    # Check if an error was returned
    if isinstance(results, dict) and "error" in results:
        raise Exception(results["error"])

    assert isinstance(results, list), "Expected a list of dictionaries"

    for item in results:
        assert isinstance(item, dict), "Each result should be a dictionary"
        assert "title" in item, "Missing 'title' key in result"
        assert "url" in item, "Missing 'url' key in result"
        assert "summary" in item, "Missing 'summary' key in result"
    print("All tests passed!")

if __name__ == "__main__":
    test_search_internet()
