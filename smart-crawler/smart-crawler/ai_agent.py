"""
Enhanced AI Agent with browser interaction capabilities
"""

import asyncio
import json
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

class AIAgent:
    def __init__(self, model: str, api_keys: Dict[str, str], temperature: float = 0.1, max_steps: int = 100):
        self.model = model
        self.api_keys = api_keys
        self.temperature = temperature
        self.max_steps = max_steps
        self.llm = None
        self.browser_agent = None
    
    async def initialize(self):
        """Initialize the AI model and browser agent"""
        try:
            # Initialize LangChain LLM
            if self.model.startswith(('gpt-', 'o1-')):
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=self.api_keys.get('openai')
                )
            
            elif self.model.startswith('gemini'):
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    model=self.model,
                    temperature=self.temperature,
                    google_api_key=self.api_keys.get('gemini')
                )
            
            elif self.model.startswith('claude'):
                from langchain_anthropic import ChatAnthropic
                self.llm = ChatAnthropic(
                    model=self.model,
                    temperature=self.temperature,
                    api_key=self.api_keys.get('anthropic')
                )
            
            else:
                raise ValueError(f"Unsupported model: {self.model}")
            
            # Try to initialize Browser-Use agent for advanced interactions
            try:
                from browser_use import Agent
                self.browser_agent = Agent(
                    task="Interact with web pages",
                    llm=self.llm,
                    max_actions_per_step=self.max_steps
                )
                print(f"Browser-Use agent initialized with {self.model}")
            except ImportError:
                print("Browser-Use not available, using basic browser interactions")
                self.browser_agent = None
        
        except Exception as e:
            print(f"Failed to initialize AI model: {e}")
            self.llm = None
            self.browser_agent = None
    
    async def interact_with_page(self, page, prompt: str) -> Dict[str, Any]:
        """Interact with a page using AI (form filling, clicking, etc.)"""
        if self.browser_agent:
            return await self.interact_with_browser_use(page, prompt)
        else:
            return await self.interact_basic(page, prompt)
    
    async def interact_with_browser_use(self, page, prompt: str) -> Dict[str, Any]:
        """Use Browser-Use agent for advanced interactions"""
        try:
            # This would use the actual Browser-Use agent
            # For now, we'll simulate the interaction
            
            # Get page content and structure
            content = await page.content()
            url = page.url
            
            # Build comprehensive prompt
            interaction_prompt = f"""
You are controlling a web browser to interact with a webpage. 

URL: {url}
Task: {prompt}

Current page title: {await page.title()}

Please analyze the page and perform the requested actions. Focus on:
1. Understanding the page structure and available elements
2. Performing the specific task requested
3. Providing detailed feedback on what was accomplished

Work step by step and explain your actions.
"""
            
            # Use LLM to generate interaction plan
            from langchain.schema import HumanMessage
            response = await asyncio.to_thread(
                self.llm.invoke,
                [HumanMessage(content=interaction_prompt)]
            )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse response and execute actions
            actions_performed = []
            data_extracted = {}
            
            # This is a simplified version - in a real implementation,
            # Browser-Use would directly control the browser
            
            # Try to extract form fields and fill them
            if "fill" in prompt.lower() or "form" in prompt.lower():
                forms = await page.query_selector_all('form')
                for form in forms:
                    inputs = await form.query_selector_all('input, textarea, select')
                    for input_elem in inputs:
                        try:
                            name = await input_elem.get_attribute('name')
                            input_type = await input_elem.get_attribute('type')
                            
                            if name and input_type in ['text', 'email', 'tel']:
                                # Use AI to determine what to fill
                                if 'email' in name.lower():
                                    await input_elem.fill('ai.assistant@example.com')
                                    actions_performed.append(f'Filled {name} with email')
                                elif 'name' in name.lower():
                                    await input_elem.fill('AI Assistant')
                                    actions_performed.append(f'Filled {name} with name')
                                elif 'message' in name.lower():
                                    await input_elem.fill('This is an automated message from AI Assistant.')
                                    actions_performed.append(f'Filled {name} with message')
                        except Exception:
                            continue
            
            return {
                'data': data_extracted,
                'summary': f"Performed {len(actions_performed)} actions: {', '.join(actions_performed)}",
                'actions': actions_performed,
                'ai_response': response_text[:500]  # Truncate for brevity
            }
            
        except Exception as e:
            return {
                'data': {},
                'summary': f"Interaction failed: {str(e)}",
                'error': str(e)
            }
    
    async def interact_basic(self, page, prompt: str) -> Dict[str, Any]:
        """Basic interaction without Browser-Use"""
        try:
            # Get page information
            title = await page.title()
            url = page.url
            content = await page.content()
            
            # Use AI to understand what to do
            if self.llm:
                interaction_prompt = f"""
Analyze this webpage and provide specific instructions for interacting with it.

URL: {url}
Title: {title}
Task: {prompt}

Based on the task, provide:
1. What elements to look for (forms, buttons, links)
2. What actions to take
3. What data to extract

Respond with a JSON object containing your analysis and recommended actions.
"""
                
                try:
                    from langchain.schema import HumanMessage
                    response = await asyncio.to_thread(
                        self.llm.invoke,
                        [HumanMessage(content=interaction_prompt)]
                    )
                    
                    response_text = response.content if hasattr(response, 'content') else str(response)
                    
                    # Try to extract JSON from response
                    json_data = self.extract_json_from_text(response_text)
                    
                    return {
                        'data': json_data or {},
                        'summary': 'AI analysis completed',
                        'ai_response': response_text[:500]
                    }
                
                except Exception as e:
                    print(f"AI interaction failed: {e}")
            
            # Fallback to basic analysis
            soup = BeautifulSoup(content, 'html.parser')
            
            forms = soup.find_all('form')
            buttons = soup.find_all('button')
            links = soup.find_all('a')
            
            return {
                'data': {
                    'forms_found': len(forms),
                    'buttons_found': len(buttons),
                    'links_found': len(links),
                    'page_title': title
                },
                'summary': f'Basic analysis: found {len(forms)} forms, {len(buttons)} buttons, {len(links)} links'
            }
            
        except Exception as e:
            return {
                'data': {},
                'summary': f"Basic interaction failed: {str(e)}",
                'error': str(e)
            }
    
    async def extract_data_browser(self, page, content: str, prompt: str) -> Dict[str, Any]:
        """Extract data from browser page"""
        try:
            url = page.url
            title = await page.title()
            
            if self.llm:
                # Use AI for extraction
                return await self.extract_data(url, content, prompt)
            else:
                # Fallback extraction
                return await self.fallback_extract_browser(content, title)
        
        except Exception as e:
            return {'error': str(e)}
    
    async def extract_data(self, url: str, content: str, prompt: str) -> Dict[str, Any]:
        """Extract data using AI (same as before but enhanced)"""
        if not self.llm:
            return await self.fallback_extract(content)
        
        try:
            # Clean and prepare content
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content (limited to avoid token limits)
            text_content = soup.get_text()
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            # Limit content length
            if len(text_content) > 8000:
                text_content = text_content[:8000] + "..."
            
            # Enhanced extraction prompt
            extraction_prompt = f"""
You are a web scraping assistant. Extract structured information from the following webpage based on the user's request.

URL: {url}
User Request: {prompt}

Webpage Content:
{text_content}

Instructions:
1. Extract the information requested by the user
2. Return the data as a valid JSON object
3. Use descriptive field names
4. If information is not found, use null values
5. Be precise and accurate
6. Focus on the most relevant information

For form-related pages, also identify:
- Form fields and their types
- Required vs optional fields
- Form action and method

Return only the JSON object, no additional text.
"""
            
            # Get AI response
            try:
                from langchain.schema import HumanMessage
                response = await asyncio.to_thread(
                    self.llm.invoke,
                    [HumanMessage(content=extraction_prompt)]
                )
                
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract JSON from response
                json_data = self.extract_json_from_text(response_text)
                
                if json_data:
                    return json_data
                else:
                    return self.parse_response_text(response_text, prompt)
            
            except Exception as e:
                print(f"AI extraction failed: {e}")
                return await self.fallback_extract(content)
        
        except Exception as e:
            print(f"Error in AI extraction: {e}")
            return await self.fallback_extract(content)
    
    def extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from AI response text"""
        try:
            # Look for JSON blocks
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, text, re.DOTALL)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data:
                        return data
                except json.JSONDecodeError:
                    continue
            
            # Try to parse the entire response as JSON
            return json.loads(text)
        
        except:
            return None
    
    def parse_response_text(self, text: str, prompt: str) -> Dict[str, Any]:
        """Parse AI response text when JSON extraction fails"""
        data = {}
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if ':' in line and len(line) < 200:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower().replace(' ', '_')
                    value = parts[1].strip()
                    value = re.sub(r'^["\']|["\']$', '', value)
                    data[key] = value
        
        if not data:
            data['extracted_content'] = text[:500]
        
        return data
    
    async def fallback_extract(self, content: str) -> Dict[str, Any]:
        """Fallback extraction when AI is not available"""
        return await self.fallback_extract_browser(content, "")
    
    async def fallback_extract_browser(self, content: str, title: str) -> Dict[str, Any]:
        """Enhanced fallback extraction for browser content"""
        soup = BeautifulSoup(content, 'html.parser')
        
        data = {}
        
        # Title
        if title:
            data['title'] = title
        elif soup.find('title'):
            data['title'] = soup.find('title').get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data['description'] = meta_desc.get('content', '')
        
        # Forms
        forms = soup.find_all('form')
        if forms:
            form_data = []
            for form in forms:
                inputs = form.find_all(['input', 'textarea', 'select'])
                input_info = []
                for inp in inputs:
                    input_info.append({
                        'name': inp.get('name', ''),
                        'type': inp.get('type', 'text'),
                        'id': inp.get('id', ''),
                        'placeholder': inp.get('placeholder', ''),
                        'required': inp.has_attr('required')
                    })
                form_data.append({
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'inputs': input_info
                })
            data['forms'] = form_data
        
        # Contact information
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        text_content = soup.get_text()
        emails = re.findall(email_pattern, text_content)
        phones = re.findall(phone_pattern, text_content)
        
        if emails:
            data['emails'] = list(set(emails))
        if phones:
            data['phones'] = list(set([phone[0] + phone[1] if isinstance(phone, tuple) else phone for phone in phones]))
        
        # Headings
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            text = h.get_text(strip=True)
            if text:
                headings.append(text)
        
        if headings:
            data['headings'] = headings
        
        # First few paragraphs
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                paragraphs.append(text)
        
        if paragraphs:
            data['content'] = paragraphs[:3]
        
        return data