import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_llm():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your free key "
            "from https://console.groq.com/keys"
        )
    return ChatGroq(model=os.getenv("GROQ_MODEL", DEFAULT_MODEL), temperature=0)
