from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Retrieve the API key using os.getenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def get_llm() -> ChatGoogleGenerativeAI:
    if not GOOGLE_API_KEY:
        raise EnvironmentError(
            "GOOGLE_API_KEY is not set. Export it first: "
            "export GOOGLE_API_KEY=your_key_here"
        )
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0.1,
        api_key=GOOGLE_API_KEY,
    )
ai_Model = get_llm()


def get_tavily():
    if not TAVILY_API_KEY:
        raise EnvironmentError(
            "TAVILY_API_KEY is not set. ")
            
    return TavilyClient(api_key=TAVILY_API_KEY)
tavily_client= get_tavily()
    

