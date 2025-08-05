"""
Enhanced crawler engine with form interaction capabilities
"""

import asyncio
import aiohttp
import json
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from playwright.async_api import async_playwright

from ai_agent import AIAgent

@dataclass
class TaskResult:
    url: str
    success: bool
    task_type: str
    data: Dict[str, Any]
    summary: str
    error: Optional[str] = None
    timestamp: float = None
    screenshots: List[str] = None

class CrawlerEngine:
    def __init__(self, config: Dict[str, Any], log_callback: Callable, progress_callback: Callable):
        self.config = config
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.visited_urls = set()
        self.session = None
        self.ai_agent = None
        self.playwright = None
        self.browser = None
        
        # Initialize AI agent if enabled
        if config.get('ai_mode', False):
            self.ai_agent = AIAgent(
                model=config.get('model', 'gpt-4o'),
                api_keys=config.get('api_keys', {}),
                temperature=config.get('temperature', 0.1),
                max_steps=config.get('max_steps', 100)
            )
    
    async def run_task(self):
        """Main task execution method"""
        self.log_callback("Initializing task engine...")
        
        task_type = self.config.get('task_type', 'extract')
        
        if task_type in ['fill_form', 'browse']:
            # Use browser for interactive tasks
            await self.run_browser_task()
        else:
            # Use HTTP client for extraction tasks
            await self.run_extraction_task()
    
    async def run_browser_task(self):
        """Run tasks requiring browser interaction"""
        self.log_callback("Starting browser for interactive task...")
        
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser
            browser_options = {
                'headless': self.config.get('headless', False),
                'slow_mo': 1000,  # Slow down actions for visibility
            }
            
            self.browser = await self.playwright.chromium.launch(**browser_options)
            context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            # Initialize AI agent if needed
            if self.ai_agent:
                await self.ai_agent.initialize()
                self.log_callback(f"AI agent initialized with model: {self.config.get('model')}")
            
            urls_to_process = self.config['urls']
            total_urls = len(urls_to_process)
            
            self.log_callback(f"Starting to process {total_urls} URLs with browser...")
            
            for i, url in enumerate(urls_to_process):
                try:
                    page = await context.new_page()
                    result = await self.process_browser_url(page, url)
                    await page.close()
                    
                    self.progress_callback(i + 1, total_urls, result.__dict__ if result else None)
                    
                    # Add delay between pages
                    if i < len(urls_to_process) - 1:
                        await asyncio.sleep(self.config.get('delay', 2.0))
                
                except Exception as e:
                    self.log_callback(f"Error processing {url}: {str(e)}")
                    error_result = TaskResult(
                        url=url,
                        success=False,
                        task_type=self.config.get('task_type', 'unknown'),
                        data={},
                        summary=f"Error: {str(e)}",
                        error=str(e),
                        timestamp=time.time()
                    )
                    self.progress_callback(i + 1, total_urls, error_result.__dict__)
            
            await context.close()
            self.log_callback("Browser task completed!")
            
        finally:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
    
    async def process_browser_url(self, page, url: str) -> Optional[TaskResult]:
        """Process a single URL with browser"""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        self.log_callback(f"Processing with browser: {url}")
        
        try:
            # Check robots.txt if enabled
            if self.config.get('respect_robots', True):
                if not await self.can_fetch_http(url):
                    self.log_callback(f"Blocked by robots.txt: {url}")
                    return TaskResult(
                        url=url,
                        success=False,
                        task_type=self.config.get('task_type', 'unknown'),
                        data={},
                        summary="Blocked by robots.txt",
                        error="Blocked by robots.txt",
                        timestamp=time.time()
                    )
            
            # Navigate to the page
            self.log_callback(f"Navigating to: {url}")
            await page.goto(url, wait_until='networkidle', timeout=self.config.get('timeout', 60) * 1000)
            
            # Take initial screenshot
            screenshot_path = f"screenshot_{int(time.time())}.png"
            await page.screenshot(path=screenshot_path)
            
            # Process based on task type
            task_type = self.config.get('task_type', 'extract')
            
            if task_type == 'fill_form':
                result = await self.fill_form_on_page(page, url)
            elif task_type == 'browse':
                result = await self.browse_and_interact(page, url)
            else:
                result = await self.extract_data_from_page(page, url)
            
            # Take final screenshot
            final_screenshot_path = f"screenshot_final_{int(time.time())}.png"
            await page.screenshot(path=final_screenshot_path)
            
            if result:
                result.screenshots = [screenshot_path, final_screenshot_path]
            
            self.log_callback(f"✅ Successfully processed: {url}")
            return result
            
        except Exception as e:
            self.log_callback(f"❌ Error processing {url}: {str(e)}")
            return TaskResult(
                url=url,
                success=False,
                task_type=self.config.get('task_type', 'unknown'),
                data={},
                summary=f"Error: {str(e)}",
                error=str(e),
                timestamp=time.time()
            )
    
    async def fill_form_on_page(self, page, url: str) -> TaskResult:
        """Fill forms on the page using AI"""
        if not self.ai_agent:
            return await self.fill_form_basic(page, url)
        
        try:
            # Get page content
            content = await page.content()
            form_data = self.config.get('form_data', {})
            prompt = self.config.get('prompt', 'Fill the form with provided data')
            
            # Use AI to fill the form
            self.log_callback("Using AI to analyze and fill the form...")
            
            # Build comprehensive prompt for form filling
            form_prompt = f"""
You are controlling a web browser to fill out a form. Here's what you need to do:

URL: {url}
Task: {prompt}

Available form data to use:
{json.dumps(form_data, indent=2)}

Instructions:
1. Analyze the webpage to identify form fields
2. Fill out the form using the provided data
3. Match form fields to the available data as best as possible
4. Handle different input types (text, email, select, checkbox, etc.)
5. Submit the form if instructed to do so
6. Provide a summary of what was accomplished

Please fill the form step by step and provide a detailed summary.
"""
            
            # Use Browser-Use agent to fill the form
            result = await self.ai_agent.interact_with_page(page, form_prompt)
            
            return TaskResult(
                url=url,
                success=True,
                task_type='fill_form',
                data=result.get('data', {}),
                summary=result.get('summary', 'Form filled using AI'),
                timestamp=time.time()
            )
            
        except Exception as e:
            self.log_callback(f"AI form filling failed, trying basic approach: {e}")
            return await self.fill_form_basic(page, url)
    
    async def fill_form_basic(self, page, url: str) -> TaskResult:
        """Basic form filling without AI"""
        self.log_callback("Using basic form filling...")
        
        try:
            form_data = self.config.get('form_data', {})
            filled_fields = []
            
            # Common field mappings
            field_mappings = {
                'name': ['name', 'full_name', 'fullname', 'your_name'],
                'first_name': ['first_name', 'firstname', 'fname'],
                'last_name': ['last_name', 'lastname', 'lname'],
                'email': ['email', 'email_address', 'mail'],
                'phone': ['phone', 'telephone', 'phone_number'],
                'message': ['message', 'comment', 'comments', 'description'],
                'subject': ['subject', 'topic'],
                'company': ['company', 'organization', 'business'],
                'website': ['website', 'url', 'site']
            }
            
            # Fill form fields
            for data_key, data_value in form_data.items():
                if not data_value:
                    continue
                
                # Get possible field names for this data
                possible_names = field_mappings.get(data_key, [data_key])
                
                for field_name in possible_names:
                    try:
                        # Try different selectors
                        selectors = [
                            f'input[name="{field_name}"]',
                            f'input[id="{field_name}"]',
                            f'textarea[name="{field_name}"]',
                            f'textarea[id="{field_name}"]',
                            f'select[name="{field_name}"]',
                            f'select[id="{field_name}"]'
                        ]
                        
                        for selector in selectors:
                            elements = await page.query_selector_all(selector)
                            if elements:
                                element = elements[0]
                                tag_name = await element.evaluate('el => el.tagName.toLowerCase()')
                                
                                if tag_name in ['input', 'textarea']:
                                    await element.fill(str(data_value))
                                    filled_fields.append(f"{field_name}: {data_value}")
                                    self.log_callback(f"Filled {field_name} with: {data_value}")
                                    break
                                elif tag_name == 'select':
                                    await element.select_option(str(data_value))
                                    filled_fields.append(f"{field_name}: {data_value}")
                                    self.log_callback(f"Selected {field_name}: {data_value}")
                                    break
                        
                        if filled_fields and filled_fields[-1].startswith(field_name):
                            break  # Successfully filled this field
                            
                    except Exception as e:
                        continue  # Try next field name
            
            # Try to submit if there's a submit button
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Send")',
                'input[value*="Submit"]',
                'input[value*="Send"]'
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    submit_btn = await page.query_selector(selector)
                    if submit_btn:
                        await submit_btn.click()
                        await page.wait_for_timeout(2000)  # Wait for submission
                        submitted = True
                        self.log_callback("Form submitted successfully")
                        break
                except Exception:
                    continue
            
            summary = f"Filled {len(filled_fields)} fields"
            if submitted:
                summary += " and submitted form"
            
            return TaskResult(
                url=url,
                success=len(filled_fields) > 0,
                task_type='fill_form',
                data={
                    'filled_fields': filled_fields,
                    'submitted': submitted,
                    'total_fields_filled': len(filled_fields)
                },
                summary=summary,
                timestamp=time.time()
            )
            
        except Exception as e:
            return TaskResult(
                url=url,
                success=False,
                task_type='fill_form',
                data={},
                summary=f"Form filling failed: {str(e)}",
                error=str(e),
                timestamp=time.time()
            )
    
    async def browse_and_interact(self, page, url: str) -> TaskResult:
        """Browse and interact with the page using AI"""
        if not self.ai_agent:
            return await self.extract_data_from_page(page, url)
        
        try:
            prompt = self.config.get('prompt', 'Browse and interact with the page')
            
            browse_prompt = f"""
You are controlling a web browser to interact with a webpage. Here's your task:

URL: {url}
Task: {prompt}

Please:
1. Analyze the webpage content and structure
2. Perform the requested interactions (clicking links, filling forms, etc.)
3. Navigate through multiple pages if needed
4. Extract any relevant information
5. Provide a comprehensive summary of your actions and findings

Work step by step and explain what you're doing.
"""
            
            result = await self.ai_agent.interact_with_page(page, browse_prompt)
            
            return TaskResult(
                url=url,
                success=True,
                task_type='browse',
                data=result.get('data', {}),
                summary=result.get('summary', 'Browsing completed using AI'),
                timestamp=time.time()
            )
            
        except Exception as e:
            self.log_callback(f"AI browsing failed: {e}")
            return await self.extract_data_from_page(page, url)
    
    async def extract_data_from_page(self, page, url: str) -> TaskResult:
        """Extract data from the page"""
        try:
            content = await page.content()
            
            if self.ai_agent:
                # Use AI for extraction
                prompt = self.config.get('prompt', 'Extract useful information from this page')
                extracted_data = await self.ai_agent.extract_data_browser(page, content, prompt)
            else:
                # Use basic extraction
                extracted_data = await self.basic_extract_from_content(content, url)
            
            return TaskResult(
                url=url,
                success=True,
                task_type='extract',
                data=extracted_data,
                summary=f"Extracted {len(extracted_data)} data points",
                timestamp=time.time()
            )
            
        except Exception as e:
            return TaskResult(
                url=url,
                success=False,
                task_type='extract',
                data={},
                summary=f"Extraction failed: {str(e)}",
                error=str(e),
                timestamp=time.time()
            )
    
    async def run_extraction_task(self):
        """Run HTTP-based extraction tasks"""
        self.log_callback("Starting HTTP-based extraction...")
        
        # Setup session
        timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
        headers = {'User-Agent': 'SmartCrawler/2.0 (+https://github.com/smartcrawler)'}
        
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            self.session = session
            
            # Initialize AI agent if needed
            if self.ai_agent:
                await self.ai_agent.initialize()
            
            urls_to_crawl = self.config['urls']
            total_urls = len(urls_to_crawl)
            
            for i, url in enumerate(urls_to_crawl):
                try:
                    result = await self.extract_from_url_http(url)
                    self.progress_callback(i + 1, total_urls, result.__dict__ if result else None)
                    
                    if i < len(urls_to_crawl) - 1:
                        await asyncio.sleep(self.config.get('delay', 1.0))
                
                except Exception as e:
                    self.log_callback(f"Error extracting from {url}: {str(e)}")
                    error_result = TaskResult(
                        url=url,
                        success=False,
                        task_type='extract',
                        data={},
                        summary=f"Error: {str(e)}",
                        error=str(e),
                        timestamp=time.time()
                    )
                    self.progress_callback(i + 1, total_urls, error_result.__dict__)
            
            self.log_callback("HTTP extraction completed!")
    
    async def extract_from_url_http(self, url: str) -> Optional[TaskResult]:
        """Extract data from URL using HTTP"""
        if url in self.visited_urls:
            return None
        
        self.visited_urls.add(url)
        self.log_callback(f"Extracting from: {url}")
        
        try:
            # Check robots.txt if enabled
            if self.config.get('respect_robots', True):
                if not await self.can_fetch_http(url):
                    self.log_callback(f"Blocked by robots.txt: {url}")
                    return TaskResult(
                        url=url,
                        success=False,
                        task_type='extract',
                        data={},
                        summary="Blocked by robots.txt",
                        error="Blocked by robots.txt",
                        timestamp=time.time()
                    )
            
            # Fetch the page
            async with self.session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    
                    # Extract data
                    if self.ai_agent:
                        extracted_data = await self.ai_agent.extract_data(url, content, self.config['prompt'])
                    else:
                        extracted_data = await self.basic_extract_from_content(content, url)
                    
                    return TaskResult(
                        url=url,
                        success=True,
                        task_type='extract',
                        data=extracted_data,
                        summary=f"Extracted {len(extracted_data)} data points",
                        timestamp=time.time()
                    )
                
                else:
                    error_msg = f"HTTP {response.status}"
                    return TaskResult(
                        url=url,
                        success=False,
                        task_type='extract',
                        data={},
                        summary=f"Failed: {error_msg}",
                        error=error_msg,
                        timestamp=time.time()
                    )
        
        except Exception as e:
            return TaskResult(
                url=url,
                success=False,
                task_type='extract',
                data={},
                summary=f"Error: {str(e)}",
                error=str(e),
                timestamp=time.time()
            )
    
    async def basic_extract_from_content(self, content: str, url: str) -> Dict[str, Any]:
        """Basic extraction from HTML content"""
        soup = BeautifulSoup(content, 'html.parser')
        
        data = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            data['title'] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data['description'] = meta_desc.get('content', '')
        
        # Forms found
        forms = soup.find_all('form')
        if forms:
            form_info = []
            for form in forms:
                inputs = form.find_all(['input', 'textarea', 'select'])
                input_info = []
                for inp in inputs:
                    input_info.append({
                        'name': inp.get('name', ''),
                        'type': inp.get('type', 'text'),
                        'id': inp.get('id', ''),
                        'required': inp.has_attr('required')
                    })
                form_info.append({
                    'action': form.get('action', ''),
                    'method': form.get('method', 'get'),
                    'inputs': input_info
                })
            data['forms'] = form_info
        
        # Headings
        headings = []
        for h in soup.find_all(['h1', 'h2', 'h3']):
            headings.append(h.get_text(strip=True))
        if headings:
            data['headings'] = headings
        
        # Paragraphs
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text and len(text) > 20:
                paragraphs.append(text)
        if paragraphs:
            data['content'] = paragraphs[:5]
        
        # Links
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if text and href:
                full_url = urljoin(url, href)
                links.append({'text': text, 'url': full_url})
        if links:
            data['links'] = links[:10]
        
        return data
    
    async def can_fetch_http(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    # Simple robots.txt check
                    if 'Disallow: /' in robots_content and 'User-agent: *' in robots_content:
                        return False
            
            return True
        except:
            return True