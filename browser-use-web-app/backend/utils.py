import re
from fastapi import UploadFile
import PyPDF2

def setup_logging():
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger()

def validate_api_key(key: str, provider: str) -> bool:
    if provider == "openai":
        return bool(re.match(r"^sk-[A-Za-z0-9]{48}$", key))
    return True

async def process_file(file: UploadFile) -> str:
    data = await file.read()
    if file.content_type == "application/pdf":
        reader = PyPDF2.PdfReader(data)
        return "\n".join(page.extract_text() for page in reader.pages)
    return data.decode(errors="ignore")

def get_llm_instance(provider: str, api_key: str, model: str):
    if provider == "openai":
        from browser_use.llm import ChatOpenAI
        return ChatOpenAI(model=model, openai_api_key=api_key)
    if provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        class GeminiLLM:
            def __init__(self, m): self.m = genai.GenerativeModel(m)
            async def ainvoke(self, msgs):
                prompt = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
                return (await self.m.generate_content_async(prompt)).text
        return GeminiLLM(model)
    raise ValueError("Unsupported provider")
