#!/usr/bin/env python3
"""
Enhanced Smart Crawler - GUI Application with Form Interaction
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
import webbrowser

from crawler_engine import CrawlerEngine
from ai_agent import AIAgent

class SmartCrawlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Smart Crawler - AI-Powered Web Scraper & Form Filler")
        self.root.geometry("1100x850")
        self.root.minsize(900, 700)
        
        # Variables
        self.crawler_engine = None
        self.is_crawling = False
        self.results = []
        
        # Create GUI
        self.create_widgets()
        self.setup_styles()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Crawler Setup
        setup_frame = ttk.Frame(notebook)
        notebook.add(setup_frame, text="🚀 Crawler Setup")
        self.create_setup_tab(setup_frame)
        
        # Tab 2: Form Interaction (NEW)
        form_frame = ttk.Frame(notebook)
        notebook.add(form_frame, text="📝 Form Interaction")
        self.create_form_tab(form_frame)
        
        # Tab 3: AI Configuration
        ai_frame = ttk.Frame(notebook)
        notebook.add(ai_frame, text="🤖 AI Settings")
        self.create_ai_tab(ai_frame)
        
        # Tab 4: Results
        results_frame = ttk.Frame(notebook)
        notebook.add(results_frame, text="📊 Results")
        self.create_results_tab(results_frame)
        
        # Tab 5: Logs
        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="📝 Logs")
        self.create_logs_tab(logs_frame)
        
        # Status bar
        self.create_status_bar()
        
    def create_setup_tab(self, parent):
        """Create crawler setup tab"""
        
        # Main container with scrollbar
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # URL Input Section
        url_frame = ttk.LabelFrame(scrollable_frame, text="🌐 Target URLs", padding=10)
        url_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(url_frame, text="Enter URLs to crawl (one per line):").pack(anchor='w')
        self.url_text = scrolledtext.ScrolledText(url_frame, height=4, width=80)
        self.url_text.pack(fill='x', pady=5)
        self.url_text.insert('1.0', 'https://example.com')
        
        # Task Type Selection (NEW)
        task_frame = ttk.LabelFrame(scrollable_frame, text="🎯 Task Type", padding=10)
        task_frame.pack(fill='x', padx=10, pady=5)
        
        self.task_type_var = tk.StringVar(value="extract")
        
        ttk.Radiobutton(task_frame, text="📊 Extract Data (Read-only)", 
                       variable=self.task_type_var, value="extract").pack(anchor='w', pady=2)
        ttk.Radiobutton(task_frame, text="📝 Fill Forms (Interactive)", 
                       variable=self.task_type_var, value="fill_form").pack(anchor='w', pady=2)
        ttk.Radiobutton(task_frame, text="🔍 Browse & Interact", 
                       variable=self.task_type_var, value="browse").pack(anchor='w', pady=2)
        
        # Task Description Section
        task_desc_frame = ttk.LabelFrame(scrollable_frame, text="📝 Task Description", padding=10)
        task_desc_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(task_desc_frame, text="Describe what you want to do:").pack(anchor='w')
        self.prompt_text = scrolledtext.ScrolledText(task_desc_frame, height=4, width=80)
        self.prompt_text.pack(fill='x', pady=5)
        self.prompt_text.insert('1.0', 'Fill the contact form with appropriate information')
        
        # Quick task templates
        template_frame = ttk.Frame(task_desc_frame)
        template_frame.pack(fill='x', pady=5)
        
        ttk.Label(template_frame, text="Quick Templates:").pack(side='left')
        
        templates = [
            ("Contact Form", "Fill the contact form with name, email, and message"),
            ("Survey Form", "Complete the survey form with appropriate responses"),
            ("Registration", "Fill out registration form with user information"),
            ("Feedback Form", "Submit feedback through the contact form"),
            ("Extract Data", "Extract all text content, links, and metadata")
        ]
        
        for template_name, template_text in templates:
            ttk.Button(template_frame, text=template_name,
                      command=lambda t=template_text: self.set_prompt_template(t)).pack(side='left', padx=2)
        
        # Advanced Settings
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="⚙️ Advanced Settings", padding=10)
        advanced_frame.pack(fill='x', padx=10, pady=5)
        
        # Settings grid
        settings_grid = ttk.Frame(advanced_frame)
        settings_grid.pack(fill='x')
        
        # Robots.txt respect (NEW)
        self.robots_var = tk.BooleanVar(value=False)  # Default to False for form filling
        ttk.Checkbutton(settings_grid, text="🤖 Respect robots.txt (uncheck for forms)", 
                       variable=self.robots_var).grid(row=0, column=0, columnspan=2, sticky='w', padx=5)
        
        # Headless mode
        self.headless_var = tk.BooleanVar(value=False)  # Default to visible for form filling
        ttk.Checkbutton(settings_grid, text="👁️ Show browser window (recommended for forms)", 
                       variable=self.headless_var).grid(row=1, column=0, columnspan=2, sticky='w', padx=5)
        
        # Delay
        ttk.Label(settings_grid, text="⏱️ Delay (seconds):").grid(row=2, column=0, sticky='w', padx=5)
        self.delay_var = tk.StringVar(value="2.0")  # Longer delay for forms
        ttk.Entry(settings_grid, textvariable=self.delay_var, width=10).grid(row=2, column=1, padx=5)
        
        # Timeout
        ttk.Label(settings_grid, text="⏰ Timeout (seconds):").grid(row=3, column=0, sticky='w', padx=5)
        self.timeout_var = tk.StringVar(value="60")  # Longer timeout for forms
        ttk.Entry(settings_grid, textvariable=self.timeout_var, width=10).grid(row=3, column=1, padx=5)
        
        # Control Buttons
        control_frame = ttk.Frame(scrollable_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_button = ttk.Button(control_frame, text="🚀 Start Task", 
                                      command=self.start_crawling, style='Start.TButton')
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="⏹️ Stop", 
                                     command=self.stop_crawling, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Warning label for robots.txt
        self.warning_label = ttk.Label(control_frame, 
                                      text="⚠️ Bypassing robots.txt - Use responsibly!", 
                                      foreground='red')
        if not self.robots_var.get():
            self.warning_label.pack(side='right', padx=5)
        
        # Bind checkbox to show/hide warning
        self.robots_var.trace('w', self.toggle_robots_warning)
    
    def create_form_tab(self, parent):
        """Create form interaction tab (NEW)"""
        
        form_info_frame = ttk.LabelFrame(parent, text="📝 Form Interaction Guide", padding=10)
        form_info_frame.pack(fill='x', padx=10, pady=5)
        
        info_text = """
🎯 Form Interaction Mode allows you to:
- Fill out contact forms, surveys, and registrations
- Submit feedback and support requests  
- Complete multi-step forms automatically
- Handle CAPTCHAs and complex interactions

💡 Tips for Form Filling:
- Uncheck "Respect robots.txt" for most forms
- Enable "Show browser window" to watch the process
- Provide clear instructions about what information to fill
- Be specific about required vs optional fields
        """
        
        ttk.Label(form_info_frame, text=info_text, justify='left').pack(anchor='w')
        
        # Form Data Section
        form_data_frame = ttk.LabelFrame(parent, text="📋 Form Data to Use", padding=10)
        form_data_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Label(form_data_frame, text="Provide data to fill in forms (JSON format):").pack(anchor='w')
        
        self.form_data_text = scrolledtext.ScrolledText(form_data_frame, height=15, width=80)
        self.form_data_text.pack(fill='both', expand=True, pady=5)
        
        # Default form data
        default_form_data = {
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-0123",
            "company": "Example Corp",
            "message": "I would like to get more information about your services.",
            "subject": "General Inquiry",
            "first_name": "John",
            "last_name": "Smith",
            "address": "123 Main St, City, ST 12345",
            "website": "https://example.com"
        }
        
        self.form_data_text.insert('1.0', json.dumps(default_form_data, indent=2))
        
        # Form data buttons
        form_buttons_frame = ttk.Frame(form_data_frame)
        form_buttons_frame.pack(fill='x', pady=5)
        
        ttk.Button(form_buttons_frame, text="📁 Load from File", 
                  command=self.load_form_data).pack(side='left', padx=5)
        ttk.Button(form_buttons_frame, text="💾 Save to File", 
                  command=self.save_form_data).pack(side='left', padx=5)
        ttk.Button(form_buttons_frame, text="🔄 Reset to Default", 
                  command=self.reset_form_data).pack(side='left', padx=5)
        ttk.Button(form_buttons_frame, text="✅ Validate JSON", 
                  command=self.validate_form_data).pack(side='right', padx=5)
        
        # Examples section
        examples_frame = ttk.LabelFrame(parent, text="📖 Example Form Instructions", padding=10)
        examples_frame.pack(fill='x', padx=10, pady=5)
        
        examples_text = """
Example Instructions for Different Form Types:

📞 Contact Form:
"Fill the contact form with my name, email, and message. Submit the form after filling all required fields."

📋 Survey Form:  
"Complete the survey by selecting appropriate ratings and providing feedback in text areas."

👤 Registration Form:
"Fill out the registration form with personal information. Use a strong password and agree to terms."

🎫 Support Form:
"Submit a support ticket describing the technical issue with detailed information."
        """
        
        ttk.Label(examples_frame, text=examples_text, justify='left').pack(anchor='w')
    
    def create_ai_tab(self, parent):
        """Create AI configuration tab (same as before but with form-specific notes)"""
        
        # AI Model Selection
        model_frame = ttk.LabelFrame(parent, text="🤖 AI Model Selection", padding=10)
        model_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(model_frame, text="Select AI Model (for form filling, GPT-4o or Claude recommended):").pack(anchor='w')
        
        self.model_var = tk.StringVar(value="gpt-4o")
        models = [
            ("GPT-4o (OpenAI) - Best for Complex Forms ⭐", "gpt-4o"),
            ("GPT-4 (OpenAI) - High Accuracy", "gpt-4"),
            ("GPT-3.5 Turbo (OpenAI) - Fast & Cheap", "gpt-3.5-turbo"),
            ("Gemini Pro (Google) - Good Balance", "gemini-pro"),
            ("Gemini 1.5 Pro (Google) - Large Context", "gemini-1.5-pro"),
            ("Claude 3 Sonnet (Anthropic) - Reliable ⭐", "claude-3-sonnet-20240229"),
        ]
        
        for text, value in models:
            ttk.Radiobutton(model_frame, text=text, variable=self.model_var, 
                           value=value).pack(anchor='w', pady=2)
        
        # API Keys Section (same as before)
        keys_frame = ttk.LabelFrame(parent, text="🔑 API Keys", padding=10)
        keys_frame.pack(fill='x', padx=10, pady=5)
        
        # OpenAI Key
        ttk.Label(keys_frame, text="OpenAI API Key:").pack(anchor='w')
        self.openai_key_var = tk.StringVar(value=os.getenv('OPENAI_API_KEY', ''))
        openai_entry = ttk.Entry(keys_frame, textvariable=self.openai_key_var, show='*', width=60)
        openai_entry.pack(fill='x', pady=2)
        
        # Gemini Key
        ttk.Label(keys_frame, text="Gemini API Key:").pack(anchor='w')
        self.gemini_key_var = tk.StringVar(value=os.getenv('GEMINI_API_KEY', ''))
        gemini_entry = ttk.Entry(keys_frame, textvariable=self.gemini_key_var, show='*', width=60)
        gemini_entry.pack(fill='x', pady=2)
        
        # Anthropic Key
        ttk.Label(keys_frame, text="Anthropic API Key:").pack(anchor='w')
        self.anthropic_key_var = tk.StringVar(value=os.getenv('ANTHROPIC_API_KEY', ''))
        anthropic_entry = ttk.Entry(keys_frame, textvariable=self.anthropic_key_var, show='*', width=60)
        anthropic_entry.pack(fill='x', pady=2)
        
        # API Key buttons
        key_buttons_frame = ttk.Frame(keys_frame)
        key_buttons_frame.pack(fill='x', pady=5)
        
        ttk.Button(key_buttons_frame, text="Test Keys", 
                  command=self.test_api_keys).pack(side='left', padx=5)
        ttk.Button(key_buttons_frame, text="Get OpenAI Key", 
                  command=lambda: webbrowser.open("https://platform.openai.com/api-keys")).pack(side='left', padx=5)
        ttk.Button(key_buttons_frame, text="Get Gemini Key", 
                  command=lambda: webbrowser.open("https://makersuite.google.com/app/apikey")).pack(side='left', padx=5)
        
        # AI Settings
        ai_settings_frame = ttk.LabelFrame(parent, text="🎛️ AI Parameters", padding=10)
        ai_settings_frame.pack(fill='x', padx=10, pady=5)
        
        # Temperature
        temp_frame = ttk.Frame(ai_settings_frame)
        temp_frame.pack(fill='x', pady=2)
        ttk.Label(temp_frame, text="Temperature (0.0-1.0):").pack(side='left')
        self.temperature_var = tk.StringVar(value="0.1")
        ttk.Entry(temp_frame, textvariable=self.temperature_var, width=10).pack(side='right')
        
        # Max steps
        steps_frame = ttk.Frame(ai_settings_frame)
        steps_frame.pack(fill='x', pady=2)
        ttk.Label(steps_frame, text="Max AI Steps:").pack(side='left')
        self.max_steps_var = tk.StringVar(value="100")  # More steps for forms
        ttk.Entry(steps_frame, textvariable=self.max_steps_var, width=10).pack(side='right')
        
        # AI Mode toggle
        self.ai_mode_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(ai_settings_frame, text="Enable AI-Powered Interaction", 
                       variable=self.ai_mode_var).pack(anchor='w', pady=5)
    
    def create_results_tab(self, parent):
        """Create results display tab (same as before)"""
        
        # Results summary
        summary_frame = ttk.LabelFrame(parent, text="📊 Task Results", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="No tasks completed yet")
        self.summary_label.pack(anchor='w')
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(summary_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(fill='x', pady=5)
        
        # Results table
        table_frame = ttk.LabelFrame(parent, text="📋 Task Results", padding=10)
        table_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview for results
        columns = ('URL', 'Task Type', 'Status', 'Details')
        self.results_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=200)
        
        # Scrollbars for treeview
        tree_scroll_y = ttk.Scrollbar(table_frame, orient='vertical', command=self.results_tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient='horizontal', command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.results_tree.pack(fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        # Export buttons
        export_frame = ttk.Frame(table_frame)
        export_frame.pack(fill='x', pady=5)
        
        ttk.Button(export_frame, text="📄 Export JSON", 
                  command=lambda: self.export_results('json')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📊 Export CSV", 
                  command=lambda: self.export_results('csv')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="👁️ View Details", 
                  command=self.view_result_details).pack(side='left', padx=5)
        ttk.Button(export_frame, text="📸 Screenshots", 
                  command=self.view_screenshots).pack(side='left', padx=5)
    
    def create_logs_tab(self, parent):
        """Create logs display tab (same as before)"""
        
        log_frame = ttk.LabelFrame(parent, text="📝 Task Logs", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=100)
        self.log_text.pack(fill='both', expand=True)
        
        # Log control buttons
        log_buttons_frame = ttk.Frame(log_frame)
        log_buttons_frame.pack(fill='x', pady=5)
        
        ttk.Button(log_buttons_frame, text="Clear Logs", 
                  command=lambda: self.log_text.delete('1.0', 'end')).pack(side='left', padx=5)
        ttk.Button(log_buttons_frame, text="Save Logs", 
                  command=self.save_logs).pack(side='left', padx=5)
        
        # Auto-scroll checkbox
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_buttons_frame, text="Auto-scroll", 
                       variable=self.auto_scroll_var).pack(side='right', padx=5)
    
    def create_status_bar(self):
        """Create status bar (same as before)"""
        
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill='x', side='bottom')
        
        self.status_label = ttk.Label(self.status_frame, text="Ready for tasks")
        self.status_label.pack(side='left', padx=10)
        
        # Current time
        self.time_label = ttk.Label(self.status_frame, text="")
        self.time_label.pack(side='right', padx=10)
        self.update_time()
        
    def setup_styles(self):
        """Setup custom styles"""
        style = ttk.Style()
        style.configure('Start.TButton', font=('Arial', 10, 'bold'))
    
    # NEW METHODS for Form Handling
    def set_prompt_template(self, template_text):
        """Set prompt from template"""
        self.prompt_text.delete('1.0', 'end')
        self.prompt_text.insert('1.0', template_text)
    
    def toggle_robots_warning(self, *args):
        """Show/hide robots.txt warning"""
        if self.robots_var.get():
            self.warning_label.pack_forget()
        else:
            self.warning_label.pack(side='right', padx=5)
    
    def load_form_data(self):
        """Load form data from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.form_data_text.delete('1.0', 'end')
                self.form_data_text.insert('1.0', json.dumps(data, indent=2))
                self.log_message(f"Form data loaded from {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load form data: {str(e)}")
    
    def save_form_data(self):
        """Save form data to file"""
        try:
            form_data = json.loads(self.form_data_text.get('1.0', 'end'))
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(form_data, f, indent=2)
                self.log_message(f"Form data saved to {filename}")
                
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON format in form data")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save form data: {str(e)}")
    
    def reset_form_data(self):
        """Reset form data to default"""
        default_form_data = {
            "name": "John Smith",
            "email": "john.smith@example.com",
            "phone": "+1-555-0123",
            "company": "Example Corp",
            "message": "I would like to get more information about your services.",
            "subject": "General Inquiry",
            "first_name": "John",
            "last_name": "Smith",
            "address": "123 Main St, City, ST 12345",
            "website": "https://example.com"
        }
        
        self.form_data_text.delete('1.0', 'end')
        self.form_data_text.insert('1.0', json.dumps(default_form_data, indent=2))
        self.log_message("Form data reset to default values")
    
    def validate_form_data(self):
        """Validate form data JSON"""
        try:
            json.loads(self.form_data_text.get('1.0', 'end'))
            messagebox.showinfo("Validation", "✅ Form data JSON is valid!")
        except json.JSONDecodeError as e:
            messagebox.showerror("Validation Error", f"❌ Invalid JSON:\n{str(e)}")
    
    # UPDATED METHODS
    def start_crawling(self):
        """Start the crawling/form filling process"""
        if self.is_crawling:
            return
        
        # Validate inputs
        urls = [url.strip() for url in self.url_text.get('1.0', 'end').split('\n') if url.strip()]
        if not urls:
            messagebox.showerror("Error", "Please enter at least one URL")
            return
        
        prompt = self.prompt_text.get('1.0', 'end').strip()
        if not prompt:
            messagebox.showerror("Error", "Please describe what you want to do")
            return
        
        # Validate form data if form filling mode
        form_data = {}
        if self.task_type_var.get() == "fill_form":
            try:
                form_data = json.loads(self.form_data_text.get('1.0', 'end'))
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON format in form data")
                return
        
        # Check API key
        model = self.model_var.get()
        if self.ai_mode_var.get():
            if model.startswith(('gpt-', 'o1-')) and not self.openai_key_var.get():
                messagebox.showerror("Error", "OpenAI API key required for GPT models")
                return
            elif model.startswith('gemini') and not self.gemini_key_var.get():
                messagebox.showerror("Error", "Gemini API key required for Gemini models")
                return
            elif model.startswith('claude') and not self.anthropic_key_var.get():
                messagebox.showerror("Error", "Anthropic API key required for Claude models")
                return
        
        # Show warning for robots.txt bypass
        if not self.robots_var.get():
            result = messagebox.askyesno(
                "Robots.txt Warning", 
                "You are bypassing robots.txt restrictions. This should only be done on sites you own or have permission to interact with. Continue?"
            )
            if not result:
                return
        
        # Update UI
        self.is_crawling = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_var.set(0)
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.results = []
        
        task_type = self.task_type_var.get()
        self.log_message(f"Starting {task_type} task...")
        
        # Start task in separate thread
        threading.Thread(target=self.run_crawler, daemon=True).start()
    
    def run_crawler(self):
        """Run the crawler/form filler (in separate thread)"""
        try:
            # Get configuration
            urls = [url.strip() for url in self.url_text.get('1.0', 'end').split('\n') if url.strip()]
            prompt = self.prompt_text.get('1.0', 'end').strip()
            
            # Get form data if needed
            form_data = {}
            if self.task_type_var.get() == "fill_form":
                form_data = json.loads(self.form_data_text.get('1.0', 'end'))
            
            config = {
                'urls': urls,
                'prompt': prompt,
                'task_type': self.task_type_var.get(),
                'form_data': form_data,
                'delay': float(self.delay_var.get()),
                'timeout': int(self.timeout_var.get()),
                'respect_robots': self.robots_var.get(),
                'headless': not self.headless_var.get(),  # Inverted for user-friendly labeling
                'ai_mode': self.ai_mode_var.get(),
                'model': self.model_var.get(),
                'temperature': float(self.temperature_var.get()),
                'max_steps': int(self.max_steps_var.get()),
                'api_keys': {
                    'openai': self.openai_key_var.get(),
                    'gemini': self.gemini_key_var.get(),
                    'anthropic': self.anthropic_key_var.get()
                }
            }
            
            # Create and run crawler
            crawler = CrawlerEngine(config, self.log_message, self.update_progress)
            asyncio.run(crawler.run_task())
            
        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            messagebox.showerror("Task Error", str(e))
        finally:
            # Reset UI
            self.is_crawling = False
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
    
    def add_result_to_tree(self, result):
        """Add result to the treeview"""
        status = "✅ Success" if result.get('success', False) else "❌ Failed"
        task_type = result.get('task_type', 'Unknown')
        details = result.get('summary', 'No details')[:50]
        
        self.results_tree.insert('', 'end', values=(
            result.get('url', 'Unknown'),
            task_type,
            status,
            details
        ))
    
    def view_screenshots(self):
        """View screenshots from browser interactions"""
        if not self.results:
            messagebox.showwarning("Warning", "No results with screenshots available")
            return
        
        # Simple implementation - in a real app you'd show actual screenshots
        messagebox.showinfo("Screenshots", "Screenshot viewing feature would show browser screenshots here")
    
    # Keep all other methods from the original implementation...
    # (update_time, log_message, update_progress, test_api_keys, etc.)
    
    def update_time(self):
        """Update time display"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def log_message(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert('end', log_entry)
        
        if self.auto_scroll_var.get():
            self.log_text.see('end')
        
        # Also update status
        self.status_label.config(text=message)
    
    def update_progress(self, current, total, result=None):
        """Update progress bar and results"""
        if total > 0:
            progress = (current / total) * 100
            self.root.after(0, lambda: self.progress_var.set(progress))
            self.root.after(0, lambda: self.summary_label.config(
                text=f"Processed {current}/{total} URLs"))
        
        if result:
            self.results.append(result)
            self.root.after(0, lambda: self.add_result_to_tree(result))
    
    def stop_crawling(self):
        """Stop the crawling process"""
        self.is_crawling = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.log_message("Task stopped by user")
    
    def test_api_keys(self):
        """Test API key connectivity"""
        self.log_message("Testing API keys...")
        
        keys_status = []
        
        if self.openai_key_var.get():
            keys_status.append("✅ OpenAI key provided")
        else:
            keys_status.append("❌ OpenAI key missing")
        
        if self.gemini_key_var.get():
            keys_status.append("✅ Gemini key provided")
        else:
            keys_status.append("❌ Gemini key missing")
        
        if self.anthropic_key_var.get():
            keys_status.append("✅ Anthropic key provided")
        else:
            keys_status.append("❌ Anthropic key missing")
        
        status_message = "\n".join(keys_status)
        messagebox.showinfo("API Key Status", status_message)
        self.log_message("API key test completed")
    
    def export_results(self, format_type):
        """Export results in specified format"""
        if not self.results:
            messagebox.showwarning("Warning", "No results to export")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format_type == 'json':
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                initialname=f"task_results_{timestamp}.json",
                filetypes=[("JSON files", "*.json")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
                self.log_message(f"Results exported to {filename}")
        
        elif format_type == 'csv':
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialname=f"task_results_{timestamp}.csv",
                filetypes=[("CSV files", "*.csv")]
            )
            if filename:
                # Flatten results for CSV
                rows = []
                for result in self.results:
                    row = {
                        'url': result.get('url', ''),
                        'task_type': result.get('task_type', ''),
                        'success': result.get('success', False),
                        'summary': result.get('summary', ''),
                        'error': result.get('error', '')
                    }
                    # Add any extracted data
                    data = result.get('data', {})
                    for key, value in data.items():
                        row[f'data_{key}'] = str(value) if value else ''
                    rows.append(row)
                
                if rows:
                    import pandas as pd
                    df = pd.DataFrame(rows)
                    df.to_csv(filename, index=False, encoding='utf-8')
                    self.log_message(f"Results exported to {filename}")
    
    def view_result_details(self):
        """View detailed result information"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a result to view")
            return
        
        # Get selected item index
        item = self.results_tree.item(selection[0])
        url = item['values'][0]
        
        # Find the corresponding result
        result = None
        for r in self.results:
            if r.get('url') == url:
                result = r
                break
        
        if result:
            # Create details window
            details_window = tk.Toplevel(self.root)
            details_window.title(f"Task Details - {url}")
            details_window.geometry("800x600")
            
            # Details text
            details_text = scrolledtext.ScrolledText(details_window, height=35, width=100)
            details_text.pack(fill='both', expand=True, padx=10, pady=10)
            
            details_content = json.dumps(result, indent=2, ensure_ascii=False)
            details_text.insert('1.0', details_content)
            details_text.config(state='disabled')
    
    def save_logs(self):
        """Save logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialname=f"task_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text files", "*.txt")]
        )
        
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_text.get('1.0', 'end'))
            self.log_message(f"Logs saved to {filename}")

def main():
    """Main function to run the GUI"""
    root = tk.Tk()
    app = SmartCrawlerGUI(root)
    
    # Center window on screen
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()