import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import random
import queue
import threading

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
}

def load_questions_from_txt(file_path):
    """Load question-answer pairs from text file"""
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

class ModernFlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ Modern Flashcard Learning System")
        self.root.geometry("900x700")
        self.root.configure(bg=COLORS['background'])
        
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
        
        # Configure frame styles
        style.configure('Card.TFrame',
                       background=COLORS['card_bg'],
                       relief='flat',
                       borderwidth=1)

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
                                   font=('Helvetica', 10),
                                   bg=COLORS['card_bg'],
                                   fg=COLORS['text_secondary'],
                                   selectcolor=COLORS['primary'])
        shuffle_cb.pack(side='left', padx=10)
        
        self.queue_var = tk.BooleanVar(value=False)
        queue_cb = tk.Checkbutton(options_frame, text="🔄 Use Retry Queue",
                                 variable=self.queue_var,
                                 font=('Helvetica', 10),
                                 bg=COLORS['card_bg'],
                                 fg=COLORS['text_secondary'],
                                 selectcolor=COLORS['success'])
        queue_cb.pack(side='left', padx=10)
        
        # Start button
        ttk.Button(options_frame, text="▶️ Start Learning", 
                  command=self.start_session,
                  style='Primary.TButton').pack(side='right')

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
        
        ttk.Button(button_frame, text="👁️ Show Answer", 
                  command=self.show_answer,
                  style='Primary.TButton').pack(side='left', padx=(0, 10))
        
        ttk.Button(button_frame, text="➡️ Next Question", 
                  command=self.next_question,
                  style='Primary.TButton').pack(side='left', padx=10)
        
        ttk.Button(button_frame, text="❌ I Forgot This", 
                  command=lambda: self.rate_question(True),
                  style='Warning.TButton').pack(side='right')
        
        ttk.Button(button_frame, text="✅ I Know This", 
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
                                      font=('Helvetica', 11),
                                      bg=COLORS['card_bg'],
                                      fg=COLORS['text_primary'])
        self.progress_label.pack(side='left')
        
        self.forgotten_label = tk.Label(stats_container, text="Retry Queue: 0",
                                       font=('Helvetica', 11),
                                       bg=COLORS['card_bg'],
                                       fg=COLORS['warning'])
        self.forgotten_label.pack(side='left', padx=(30, 0))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(stats_container, length=200, mode='determinate')
        self.progress_bar.pack(side='right')

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