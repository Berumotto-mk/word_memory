import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import random
import queue
import threading
import requests
from bs4 import BeautifulSoup
import re
import json

# Custom colors and styles
COLORS = {
    'primary': '#2563eb',      # Blue
    'primary_light': '#3b82f6',
    'secondary': '#64748b',    # Gray
    'success': '#059669',      # Green
    'warning': '#d97706',      # Orange
    'background': '#f8fafc',   # Light gray
    'card_bg': '#ffffff',      # White
    'text_primary': '#1e293b', # Dark gray
    'text_secondary': '#64748b',
    'border': '#e2e8f0',       # Light border
    'accent': '#8b5cf6',       # Purple
    'ori_white': '#ffffff'     # Original white
}



'''
TODO
1.添加封面，可以选择背单词或者一般的 question-answer,进入两个系统
2. 添加把 queue 储存在一个文件中的功能
3. 添加一个按钮可以查看 queue 中的单词
4. 接入 AI 给单词造句，或者生成问题的答案
5. 增加 last words

Bug ：查询时。例如 in defiance of 时，只会爬 in 的词典---- fixed
'''





# Load from .txt file
def load_questions_from_txt(file_path):
    """Load question-answer pairs from text file"""
    '''
    TODO
    这一段后面可以改进，因为 load 的方式过于简单，
    比如有的问题和答案可能是多行的
    '''


    all_parts = []
    current_part = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line and current_part:
                all_parts.append(current_part)
                current_part = []
                continue
            if ' ' in line:
                idx = line.rfind(' ')
                question = line[:idx].strip()
                answer = line[idx+1:].strip()
                current_part.append((question, answer))
    if current_part:
        all_parts.append(current_part)
    return all_parts

class DictionarySearcher:
    """Dictionary web scraper for fetching word information"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search_youdao(self, word):
        """Search Youdao Dictionary for word information"""
        try:
            # Clean the word - extract first word if it's a phrase
            clean_word = word.strip().split()[0] if word.strip() else word
            url = f"https://dict.youdao.com/w/{clean_word}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = {
                'word': clean_word,
                'pronunciation': '',
                'definitions': [],
                'examples': []
            }
            
            # Get pronunciation
            phonetic = soup.find('span', class_='phonetic')
            if phonetic:
                result['pronunciation'] = phonetic.get_text().strip()
            
            # Get basic definitions
            trans_container = soup.find('div', class_='trans-container')
            if trans_container:
                definitions = trans_container.find_all('li')
                for def_item in definitions[:5]:  # Limit to 5 definitions
                    def_text = def_item.get_text().strip()
                    if def_text:
                        result['definitions'].append(def_text)
            
            # Get example sentences
            example_container = soup.find('div', id='bilingual')
            if example_container:
                examples = example_container.find_all('li')
                for example in examples[:3]:  # Limit to 3 examples
                    example_text = example.get_text().strip()
                    if example_text:
                        # Clean up the example text
                        cleaned_example = re.sub(r'\s+', ' ', example_text)
                        result['examples'].append(cleaned_example)
            
            return result
            
        except Exception as e:
            return {'error': f"搜索失败: {str(e)}"}
    
    def search_cambridge(self, word):
        """Search Cambridge Dictionary as backup"""
        try:
            clean_word = word.strip().split()[0] if word.strip() else word
            url = f"https://dictionary.cambridge.org/dictionary/english/{clean_word}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = {
                'word': clean_word,
                'pronunciation': '',
                'definitions': [],
                'examples': []
            }
            
            # Get pronunciation
            pron = soup.find('span', class_='ipa')
            if pron:
                result['pronunciation'] = f"/{pron.get_text().strip()}/"
            
            # Get definitions
            def_blocks = soup.find_all('div', class_='def-block')
            for block in def_blocks[:3]:
                def_elem = block.find('div', class_='def')
                if def_elem:
                    result['definitions'].append(def_elem.get_text().strip())
                
                # Get example from this definition
                example = block.find('div', class_='examp')
                if example:
                    result['examples'].append(example.get_text().strip())
            
            return result
            
        except Exception as e:
            return {'error': f"Cambridge搜索失败: {str(e)}"}

class DictionaryWindow:
    """Dictionary search results window"""
    
    def __init__(self, parent, word, searcher):
        self.searcher = searcher
        self.word = word
        
        # Create new window
        self.window = tk.Toplevel(parent)
        self.window.title(f"📖 Dictionary: {word}")
        self.window.geometry("600x500")
        self.window.configure(bg=COLORS['background'])
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_ui()
        self.search_word()
    
    def create_ui(self):
        """Create the dictionary window UI"""
        # Header
        header_frame = tk.Frame(self.window, bg=COLORS['card_bg'], padx=20, pady=15)
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        tk.Label(header_frame, 
                text=f"🔍 Searching: {self.word}",
                font=('Helvetica', 16, 'bold'),
                bg=COLORS['card_bg'],
                fg=COLORS['text_primary']).pack(anchor='w')
        
        # Loading indicator
        self.status_label = tk.Label(header_frame,
                                   text="🔄 Searching dictionary...",
                                   font=('Helvetica', 10),
                                   bg=COLORS['card_bg'],
                                   fg=COLORS['text_secondary'])
        self.status_label.pack(anchor='w', pady=(5, 0))
        
        # Results frame
        self.results_frame = tk.Frame(self.window, bg=COLORS['card_bg'])
        self.results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Scrollable text area
        self.text_area = scrolledtext.ScrolledText(
            self.results_frame,
            wrap=tk.WORD,
            font=('Helvetica', 11),
            bg='white',
            fg=COLORS['text_primary'],
            padx=15,
            pady=15
        )
        self.text_area.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Close button
        button_frame = tk.Frame(self.window, bg=COLORS['background'])
        button_frame.pack(fill='x', padx=10, pady=10)
        
        close_btn = tk.Button(button_frame,
                             text="❌ Close",
                             command=self.window.destroy,
                             bg=COLORS['secondary'],
                             fg='white',
                             font=('Helvetica', 10, 'bold'),
                             padx=20,
                             pady=8,
                             border=0)
        close_btn.pack(side='right')
    
    def search_word(self):
        """Search for word in dictionary"""
        def search_thread():
            # Try Youdao first
            result = self.searcher.search_youdao(self.word)
            
            # If Youdao fails, try Cambridge
            if 'error' in result:
                result = self.searcher.search_cambridge(self.word)
            
            # Update UI in main thread
            self.window.after(0, lambda: self.display_results(result))
        
        # Start search in background thread
        threading.Thread(target=search_thread, daemon=True).start()
    
    def display_results(self, result):
        """Display search results"""
        self.text_area.delete(1.0, tk.END)
        
        if 'error' in result:
            self.status_label.config(text="❌ Search failed", fg=COLORS['warning'])
            self.text_area.insert(tk.END, f"Error: {result['error']}\n\n")
            self.text_area.insert(tk.END, "💡 Tips:\n")
            self.text_area.insert(tk.END, "• Check your internet connection\n")
            self.text_area.insert(tk.END, "• Make sure the word is spelled correctly\n")
            self.text_area.insert(tk.END, "• Try with a single word instead of a phrase")
            return
        
        self.status_label.config(text="✅ Search completed", fg=COLORS['success'])
        
        # Display word and pronunciation
        self.text_area.insert(tk.END, f"📝 Word: {result['word']}\n", 'word')
        if result['pronunciation']:
            self.text_area.insert(tk.END, f"🔊 Pronunciation: {result['pronunciation']}\n\n", 'pronunciation')
        else:
            self.text_area.insert(tk.END, "\n")
        
        # Display definitions
        if result['definitions']:
            self.text_area.insert(tk.END, "📚 Definitions:\n", 'section_header')
            for i, definition in enumerate(result['definitions'], 1):
                self.text_area.insert(tk.END, f"{i}. {definition}\n", 'definition')
            self.text_area.insert(tk.END, "\n")
        
        # Display examples
        if result['examples']:
            self.text_area.insert(tk.END, "💡 Example Sentences:\n", 'section_header')
            for i, example in enumerate(result['examples'], 1):
                self.text_area.insert(tk.END, f"{i}. {example}\n\n", 'example')
        
        # Configure text tags for styling
        self.text_area.tag_config('word', font=('Helvetica', 20, 'bold'), foreground=COLORS['primary'])
        self.text_area.tag_config('pronunciation', font=('Helvetica', 18), foreground=COLORS['accent'])
        self.text_area.tag_config('section_header', font=('Helvetica', 18, 'bold'), foreground=COLORS['text_primary'])
        self.text_area.tag_config('definition', font=('Helvetica', 15), foreground=COLORS['text_primary'])
        self.text_area.tag_config('example', font=('Helvetica', 15), foreground=COLORS['text_secondary'])

class ModernFlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Modern Flashcard Learning System")
        self.root.configure(bg=COLORS['background'])
        self.root.geometry("1280x700")  # 设置窗口初始大小为 1000x700（可以根据你的需要调整）
        self.root.resizable(False, False)  # 禁止用户手动改变窗口大小（横向和纵向都不可调）
        
        # Initialize dictionary searcher
        self.dictionary = DictionarySearcher()
        
        # Configure ttk styles
        self.setup_styles()
        
        # Create main layout
        self.create_header()
        self.create_main_content()
        self.create_stats_panel()
        
        # State variables
        self.all_parts = []
        self.question_queue = None
        self.current_qa = None
        self.stats = {'total': 0, 'current': 0, 'forgotten': 0}
        
        # Initialize UI state
        self.update_stats()

    def setup_styles(self):
        """Configure custom ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure button styles
        style.configure('Primary.TButton',
                       background=COLORS['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(20, 10))
        style.map('Primary.TButton',
                 background=[('active', COLORS['primary_light'])])
        
        style.configure('Success.TButton',
                       background=COLORS['success'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 8))
        
        style.configure('Warning.TButton',
                       background=COLORS['warning'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 8))
        
        style.configure('Accent.TButton',
                       background=COLORS['accent'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(15, 8))
        
        # Configure frame styles
        style.configure('Card.TFrame',
                       background=COLORS['card_bg'],
                       relief='flat',
                       borderwidth=1)
        
        style.configure('.', font=('Comic Sans MS', 16))


    def create_header(self):
        """Create the header section with file loading controls"""
        header_frame = tk.Frame(self.root, bg=COLORS['card_bg'], padx=30, pady=20)
        header_frame.pack(fill='x', padx=20, pady=(20, 10))
        
        # Title
        title_label = tk.Label(header_frame, 
                              text="📚 Flashcard Learning System",
                              font=('Helvetica', 24, 'bold'),
                              bg=COLORS['card_bg'],
                              fg=COLORS['text_primary'])
        title_label.pack(anchor='w', pady=(0, 15))
        
        # File selection row
        file_frame = tk.Frame(header_frame, bg=COLORS['card_bg'])
        file_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(file_frame, text="📁 Question File:", 
                font=('Helvetica', 11, 'bold'),
                bg=COLORS['card_bg'], 
                fg=COLORS['text_secondary']).pack(side='left')
        
        self.file_path = tk.StringVar()
        file_entry = tk.Entry(file_frame, textvariable=self.file_path, 
                             font=('Helvetica', 10), width=50,
                             bg='white', fg=COLORS['text_primary'],
                             relief='solid', borderwidth=1)
        file_entry.pack(side='left', padx=(10, 5))
        
        ttk.Button(file_frame, text="Browse", 
                  command=self.browse_file,
                  style='Primary.TButton').pack(side='left', padx=5)
        
        ttk.Button(file_frame, text="Load", 
                  command=self.load_file,
                  style='Primary.TButton').pack(side='left', padx=5)
        
        # Options row
        options_frame = tk.Frame(header_frame, bg=COLORS['card_bg'])
        options_frame.pack(fill='x')
        
        # Part selection
        tk.Label(options_frame, text="📑 Part:", 
                font=('Helvetica', 11, 'bold'),
                bg=COLORS['card_bg'], 
                fg=COLORS['text_secondary']).pack(side='left')
        
        self.part_combo = ttk.Combobox(options_frame, state='disabled', width=25)
        self.part_combo.pack(side='left', padx=(5, 20))
        
        # Checkboxes with modern styling
        self.shuffle_var = tk.BooleanVar(value=False)
        shuffle_cb = tk.Checkbutton(options_frame, text="🔀 Shuffle Questions",
                                   variable=self.shuffle_var,
                                   font=('Helvetica', 18),
                                   bg=COLORS['card_bg'],
                                   fg=COLORS['text_secondary'],
                                   selectcolor=COLORS['ori_white'])
        shuffle_cb.pack(side='left', padx=10)
        
        self.queue_var = tk.BooleanVar(value=False)
        queue_cb = tk.Checkbutton(options_frame, text="🔄 Use Retry Queue",
                                 variable=self.queue_var,
                                 font=('Helvetica', 18),
                                 bg=COLORS['card_bg'],
                                 fg=COLORS['text_secondary'],
                                 selectcolor=COLORS['ori_white'])
        queue_cb.pack(side='left', padx=10)
        
        # Start button
        ttk.Button(options_frame, text="▶️ Start Learning", 
                  command=self.start_session,
                  style='Primary.TButton').pack(side='left')

    def create_main_content(self):
        """Create the main flashcard content area"""
        self.main_frame = tk.Frame(self.root, bg=COLORS['background'])
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Card container
        card_container = tk.Frame(self.main_frame, bg=COLORS['card_bg'], 
                                 relief='solid', borderwidth=1, padx=40, pady=30)
        card_container.pack(fill='both', expand=True)
        
        # Question section
        question_frame = tk.Frame(card_container, bg=COLORS['card_bg'])
        question_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(question_frame, text="❓ Question",
                font=('Helvetica', 12, 'bold'),
                bg=COLORS['card_bg'],
                fg=COLORS['text_secondary']).pack(anchor='w')
        
        self.question_label = tk.Label(question_frame, text="Click 'Start Learning' to begin",
                                      font=('Helvetica', 18, 'bold'),
                                      bg=COLORS['card_bg'],
                                      fg=COLORS['text_primary'],
                                      wraplength=700,
                                      justify='left')
        self.question_label.pack(anchor='w', pady=(5, 0))
        
        # Separator
        separator = tk.Frame(card_container, height=2, bg=COLORS['border'])
        separator.pack(fill='x', pady=20)
        
        # Answer section
        answer_frame = tk.Frame(card_container, bg=COLORS['card_bg'])
        answer_frame.pack(fill='x', pady=(0, 30))
        
        tk.Label(answer_frame, text="💡 Answer",
                font=('Helvetica', 12, 'bold'),
                bg=COLORS['card_bg'],
                fg=COLORS['text_secondary']).pack(anchor='w')
        
        self.answer_label = tk.Label(answer_frame, text="",
                                    font=('Helvetica', 16),
                                    bg=COLORS['card_bg'],
                                    fg=COLORS['primary'],
                                    wraplength=700,
                                    justify='left')
        self.answer_label.pack(anchor='w', pady=(5, 0))
        
        # Control buttons
        button_frame = tk.Frame(card_container, bg=COLORS['card_bg'])
        button_frame.pack(fill='x')
        
        # Left side buttons
        left_buttons = tk.Frame(button_frame, bg=COLORS['card_bg'])
        left_buttons.pack(side='left')
        
        ttk.Button(left_buttons, text="👁️ Show Answer", 
                  command=self.show_answer,
                  style='Primary.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(left_buttons, text="📖 Search Dictionary", 
                  command=self.search_dictionary,
                  style='Accent.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(left_buttons, text="➡️ Next Question", 
                  command=self.next_question,
                  style='Primary.TButton').pack(side='left')
        
        # Right side buttons
        right_buttons = tk.Frame(button_frame, bg=COLORS['card_bg'])
        right_buttons.pack(side='right')
        
        ttk.Button(right_buttons, text="❌ I Forgot This", 
                  command=lambda: self.rate_question(True),
                  style='Warning.TButton').pack(side='right')
        
        ttk.Button(right_buttons, text="✅ I Know This", 
                  command=lambda: self.rate_question(False),
                  style='Success.TButton').pack(side='right', padx=(0, 10))

    def create_stats_panel(self):
        """Create the statistics panel"""
        stats_frame = tk.Frame(self.root, bg=COLORS['card_bg'], padx=20, pady=15)
        stats_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        tk.Label(stats_frame, text="📊 Session Statistics",
                font=('Helvetica', 12, 'bold'),
                bg=COLORS['card_bg'],
                fg=COLORS['text_secondary']).pack(anchor='w', pady=(0, 8))
        
        # Stats container
        stats_container = tk.Frame(stats_frame, bg=COLORS['card_bg'])
        stats_container.pack(fill='x')
        
        # Progress stats
        self.progress_label = tk.Label(stats_container, text="Progress: 0/0",
                                      font=('Helvetica', 15),
                                      bg=COLORS['card_bg'],
                                      fg=COLORS['text_primary'])
        self.progress_label.pack(side='left')
        
        self.forgotten_label = tk.Label(stats_container, text="Retry Queue: 0",
                                       font=('Helvetica', 15),
                                       bg=COLORS['card_bg'],
                                       fg=COLORS['warning'])
        self.forgotten_label.pack(side='left', padx=(30, 0))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(stats_container, length=500, mode='determinate')
        self.progress_bar.pack(side='left', padx=(30, 0), fill='x', expand=True)

    def browse_file(self):
        """Browse for question file"""
        path = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Select Question-Answer File"
        )
        if path:
            self.file_path.set(path)

    def load_file(self):
        """Load questions from file"""
        path = self.file_path.get()
        if not path:
            messagebox.showerror("Error", "Please select a question file.")
            return
        
        try:
            self.all_parts = load_questions_from_txt(path)

            
            if not self.all_parts:
                messagebox.showerror("Error", "No valid question-answer pairs found in the file.")
                return
                
            parts = [f"Part {i+1} ({len(p)} questions)" for i, p in enumerate(self.all_parts)]

            whole_parts = [word for p in self.all_parts if len(p) > 0 for word in p]
            self.all_parts.append(whole_parts)

            parts.append(f"All parts combined ({len(whole_parts)} questions)")

            self.part_combo.config(values=parts, state='readonly')
            self.part_combo.current(0)
            messagebox.showinfo("Success", f"✅ Successfully loaded {len(self.all_parts)} parts!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")

    def start_session(self):
        """Start a learning session"""
        if not self.all_parts:
            messagebox.showwarning("Warning", "Please load a question file first.")
            return
            
        idx = self.part_combo.current()
        if idx < 0:
            messagebox.showwarning("Warning", "Please select a part to study.")
            return
            
        questions = list(self.all_parts[idx])
        if self.shuffle_var.get():
            random.shuffle(questions)
            
        if self.queue_var.get():
            self.question_queue = queue.Queue()
            for q in questions:
                self.question_queue.put(q)
        else:
            self.question_queue = iter(questions)
        
        # Reset stats
        self.stats = {'total': len(questions), 'current': 0, 'forgotten': 0}
        self.update_stats()
        
        self.next_question()

    def next_question(self):
        """Show the next question"""
        self.answer_label.config(text="")
        
        try:
            if isinstance(self.question_queue, queue.Queue):
                self.current_qa = self.question_queue.get_nowait()
            else:
                self.current_qa = next(self.question_queue)
                
            question, answer = self.current_qa
            self.question_label.config(text=question)
            
        except Exception:
            # Session completed
            messagebox.showinfo("Congratulations! 🎉", 
                              "🎊 You have completed this learning session!\n\n"
                              "Great job on your dedication to learning! 📚✨")
            self.question_label.config(text="Session completed! 🎉")
            self.answer_label.config(text="")

    def show_answer(self):
        """Show the answer to the current question"""
        if self.current_qa:
            self.answer_label.config(text=self.current_qa[1])

    def search_dictionary(self):
        """Open dictionary search window"""
        if not self.current_qa:
            messagebox.showwarning("Warning", "No question is currently displayed.")
            return
        
        # Extract the word to search (use the question/word)
        words = self.current_qa[0].strip().split()  # Split into list of words
        word_to_search = max(words, key=len) if words else ""  # Get longest word (or empty if no words)
        
        # Open dictionary window
        try:
            DictionaryWindow(self.root, word_to_search, self.dictionary)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open dictionary:\n{str(e)}")

    def rate_question(self, forgot):
        """Rate the current question and move to next"""
        if not self.current_qa:
            return
            
        if forgot and isinstance(self.question_queue, queue.Queue):
            self.question_queue.put(self.current_qa)
            self.stats['forgotten'] += 1
        else:
            self.stats['current'] += 1
            
        self.update_stats()
        self.next_question()

    def update_stats(self):
        """Update the statistics display"""
        progress_text = f"Progress: {self.stats['current']}/{self.stats['total']}"
        self.progress_label.config(text=progress_text)
        
        forgotten_text = f"Retry Queue: {self.stats['forgotten']}"
        self.forgotten_label.config(text=forgotten_text)
        
        if self.stats['total'] > 0:
            progress_percent = (self.stats['current'] / self.stats['total']) * 100
            self.progress_bar['value'] = progress_percent

if __name__ == '__main__':
    root = tk.Tk()
    app = ModernFlashcardApp(root)
    root.mainloop()