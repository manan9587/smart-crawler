import logging
import re
import io
from typing import Any, Dict
from fastapi import UploadFile

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("agent.log")
        ]
    )
    return logging.getLogger("agent_manager")

def validate_api_key(api_key: str, provider: str) -> bool:
    """Validate API key format based on provider"""
    if not api_key or not api_key.strip():
        return False
    
    if provider == "openai":
        # OpenAI API keys start with 'sk-' and are typically 51 characters long
        return bool(re.match(r"^sk-[A-Za-z0-9]{48}$", api_key.strip()))
    
    elif provider == "gemini":
        # Google Gemini API keys are typically 39 characters
        return len(api_key.strip()) >= 20  # More lenient check
    
    elif provider == "anthropic":
        # Anthropic API keys start with 'sk-ant-'
        return bool(re.match(r"^sk-ant-[A-Za-z0-9\-_]{95,}$", api_key.strip()))
    
    # For other providers, just check it's not empty
    return len(api_key.strip()) > 0

async def process_file(file: UploadFile) -> str:
    """Process uploaded file and return content as string"""
    try:
        content = await file.read()
        
        if file.content_type == "application/pdf":
            # Handle PDF files
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_content = ""
                for page in pdf_reader.pages:
                    text_content += page.extract_text() + "\n"
                return text_content
            except ImportError:
                return "PDF processing not available - PyPDF2 not installed"
            except Exception as e:
                return f"Error processing PDF: {str(e)}"
        
        elif file.content_type in ["text/plain", "text/csv", "application/json"]:
            # Handle text files
            return content.decode('utf-8', errors='ignore')
        
        elif file.content_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            # Handle Excel files using openpyxl instead of pandas
            try:
                import openpyxl
                from io import BytesIO
                
                workbook = openpyxl.load_workbook(BytesIO(content))
                sheet = workbook.active
                
                # Convert to text representation
                text_content = ""
                for row in sheet.iter_rows(values_only=True):
                    text_content += "\t".join(str(cell) if cell is not None else "" for cell in row) + "\n"
                
                return text_content
            except ImportError:
                return "Excel processing not available - openpyxl not installed"
            except Exception as e:
                return f"Error processing Excel file: {str(e)}"
        
        else:
            # Try to decode as text for unknown types
            try:
                return content.decode('utf-8', errors='ignore')
            except:
                return f"Unable to process file type: {file.content_type}"
                
    except Exception as e:
        logging.error(f"Error processing file {file.filename}: {e}")
        return f"Error processing file: {str(e)}"

def get_llm_instance(provider: str, api_key: str, model: str):
    """Get LLM instance based on provider"""
    try:
        if provider == "openai":
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
                
                class OpenAIWrapper:
                    def __init__(self, client, model):
                        self.client = client
                        self.model = model
                    
                    async def ainvoke(self, messages):
                        response = await self.client.chat.completions.create(
                            model=self.model,
                            messages=messages,
                            max_tokens=1000
                        )
                        return response.choices[0].message.content
                
                return OpenAIWrapper(client, model)
                
            except ImportError:
                raise Exception("OpenAI library not installed. Run: pip install openai")
        
        elif provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                
                class GeminiWrapper:
                    def __init__(self, model_name):
                        self.model = genai.GenerativeModel(model_name)
                    
                    async def ainvoke(self, messages):
                        # Convert messages to text prompt
                        prompt = "\n".join([f"{msg.get('role', 'user')}: {msg.get('content', '')}" for msg in messages])
                        response = await self.model.generate_content_async(prompt)
                        return response.text
                
                return GeminiWrapper(model)
                
            except ImportError:
                raise Exception("Google Generative AI library not installed. Run: pip install google-generativeai")
        
        elif provider == "anthropic":
            try:
                import anthropic
                client = anthropic.AsyncAnthropic(api_key=api_key)
                
                class AnthropicWrapper:
                    def __init__(self, client, model):
                        self.client = client
                        self.model = model
                    
                    async def ainvoke(self, messages):
                        response = await self.client.messages.create(
                            model=self.model,
                            max_tokens=1000,
                            messages=messages
                        )
                        return response.content[0].text
                
                return AnthropicWrapper(client, model)
                
            except ImportError:
                raise Exception("Anthropic library not installed. Run: pip install anthropic")
        
        else:
            raise Exception(f"Unsupported LLM provider: {provider}")
            
    except Exception as e:
        logging.error(f"Error creating LLM instance: {e}")
        raise

def parse_url_from_context(context: Dict[str, Any]) -> str:
    """Extract URL from context"""
    url = context.get("url", "")
    if not url:
        return "about:blank"
    
    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    return url

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    return safe_filename[:255]  # Limit length

def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"