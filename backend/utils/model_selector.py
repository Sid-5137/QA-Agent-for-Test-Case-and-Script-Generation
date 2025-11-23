import os
import socket
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

load_dotenv()

class ModelSelector:
    def __init__(self):
        self.have_groq = bool(os.getenv("GROQ_API_KEY"))
        self.have_openai = bool(os.getenv("OPENAI_API_KEY"))
        self.online = self._check_network()

    def _check_network(self):
        try:
            socket.gethostbyname("example.com")
            return True
        except:
            return False

    def choose(self, task: str = ""):
        if self.have_groq:
            task_lower = task.lower()
            if any(k in task_lower for k in ["reason", "selenium", "complex", "analysis"]):
                return ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0,
                    groq_api_key=os.getenv("GROQ_API_KEY")
                )
            if "test" in task_lower:
                return ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0,
                    groq_api_key=os.getenv("GROQ_API_KEY")
                )
            return ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0,
                groq_api_key=os.getenv("GROQ_API_KEY")
            )

        if self.have_openai:
            task_lower = task.lower()
            if any(k in task_lower for k in ["reason", "selenium", "complex"]):
                return ChatOpenAI(
                    model="gpt-4.1",
                    temperature=0,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            if "test" in task_lower:
                return ChatOpenAI(
                    model="o3-mini",
                    temperature=0,
                    api_key=os.getenv("OPENAI_API_KEY")
                )
            return ChatOpenAI(
                model="gpt-4.1-mini",
                temperature=0,
                api_key=os.getenv("OPENAI_API_KEY")
            )

        raise RuntimeError("No valid LLM found: Set GROQ_API_KEY or OPENAI_API_KEY.")
