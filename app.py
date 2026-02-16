import tkinter as tk
from tkinter import messagebox, simpledialog
import fitz  # PyMuPDF
import os
import re
from PIL import Image, ImageTk
from io import BytesIO

class TerraformQuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Terraform Exam Simulator")
        self.root.geometry("1100x850")
        self.root.configure(bg="#f5f7fa")

        self.questions_dir = "./output2"
        self.logo_path = "./logo.png"
        self.questions_data = []
        self.current_q_index = 0
        self.score_right = 0
        self.score_wrong = 0
        self.answered = False
        self.selected_answers = []
        self.image_references = []
        
        self.setup_ui()
        self.start_session()

    def setup_ui(self):
        # Top bar with logo in corner (FIXED - doesn't scroll)
        top_bar = tk.Frame(self.root, bg="#ffffff", height=70)
        top_bar.pack(fill="x", pady=(0, 10))
        top_bar.pack_propagate(False)

        try:
            logo_original = tk.PhotoImage(file=self.logo_path)
            self.logo_small = logo_original.subsample(4, 4)
            tk.Label(top_bar, image=self.logo_small, bg="#ffffff").pack(side="left", padx=20, pady=10)
        except Exception as e:
            print(f"Logo not found: {e}")

        tk.Label(top_bar, text="Terraform Certification Quiz", 
                font=("Segoe UI", 20, "bold"), bg="#ffffff", fg="#2c3e50").pack(side="left", padx=10)

        # SCROLLABLE MAIN CONTAINER
        container = tk.Frame(self.root, bg="#f5f7fa")
        container.pack(fill="both", expand=True, padx=40, pady=10)

        # Create Canvas and Scrollbar
        self.canvas = tk.Canvas(container, bg="#f5f7fa", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        
        # Scrollable frame inside canvas
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        # Question card (inside scrollable frame)
        question_outer = tk.Frame(self.scrollable_frame, bg="#e0e6ed", relief="flat")
        question_outer.pack(fill="x", pady=(0, 25))
        
        question_inner = tk.Frame(question_outer, bg="#ffffff")
        question_inner.pack(fill="x", padx=2, pady=2)

        self.question_label = tk.Label(question_inner, text="Loading questions...", 
                                      wraplength=950, font=("Segoe UI", 13), bg="#ffffff", 
                                      fg="#2c3e50", padx=30, pady=25, justify="left")
        self.question_label.pack(fill="x")

        # Options container (inside scrollable frame)
        self.options_frame = tk.Frame(self.scrollable_frame, bg="#f5f7fa")
        self.options_frame.pack(fill="both", expand=True)
        self.option_buttons = []

        # Next button (inside scrollable frame)
        self.next_button = tk.Button(self.scrollable_frame, text="Next Question →", 
                                    command=self.load_next_question,
                                    font=("Segoe UI", 13, "bold"), bg="#4caf50", fg="#000000",
                                    padx=40, pady=15, cursor="hand2", relief="flat",
                                    activebackground="#45a049", activeforeground="#000000")

        # Bottom status bar (FIXED - doesn't scroll)
        status_bar = tk.Frame(self.root, bg="#ffffff", height=70)
        status_bar.pack(fill="x", side="bottom")
        status_bar.pack_propagate(False)

        score_frame = tk.Frame(status_bar, bg="#ffffff")
        score_frame.pack(pady=20)

        self.score_label = tk.Label(score_frame, text="✓ Correct: 0    ✗ Wrong: 0", 
                                   font=("Segoe UI", 13, "bold"), bg="#ffffff", fg="#5c6bc0")
        self.score_label.pack()

    def extract_pdf_data(self, file_path):
        try:
            doc = fitz.open(file_path)
            full_text = ""
            images = []
            
            for page in doc:
                full_text += page.get_text()
                
                # Extract images from the page
                image_list = page.get_images(full=True)
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        images.append(image_bytes)
                    except:
                        pass
            
            doc.close()

            # Extract correct answer(s) - can be multiple
            answer_match = re.search(r"CORRECT ANSWER\(S\):\s*-?\s*([A-Z,\s]+)", full_text, re.IGNORECASE)
            if not answer_match:
                answer_match = re.search(r"Suggested Answer:\s*([A-Z,\s]+)", full_text, re.IGNORECASE)
            
            if answer_match:
                correct_answers_str = answer_match.group(1).upper()
                correct_answers = [letter.strip() for letter in re.findall(r'[A-Z]', correct_answers_str)]
            else:
                correct_answers = ["A"]

            # Extract question text
            question_match = re.search(r"QUESTION:(.*?)(?=\n[A-Z]\.|\nA\.)", full_text, re.DOTALL)
            question_text = question_match.group(1).strip() if question_match else "Question not found"

            # Extract all available options dynamically
            options = {}
            
            option_markers = re.findall(r'\n([A-Z])\.\s', full_text)
            unique_markers = []
            for marker in option_markers:
                if marker not in unique_markers and marker in 'ABCDEFGH':
                    unique_markers.append(marker)
            
            for i, letter in enumerate(unique_markers):
                if i + 1 < len(unique_markers):
                    next_letter = unique_markers[i + 1]
                    pattern = rf'\n{letter}\.\s+(.*?)(?=\n{next_letter}\.)'
                else:
                    pattern = rf'\n{letter}\.\s+(.*?)(?=\nShow Suggested Answer|\nANSWERS:|\nCORRECT ANSWER|\nCommunity vote|$)'
                
                match = re.search(pattern, full_text, re.DOTALL)
                if match:
                    option_text = match.group(1).strip()
                    option_text = re.sub(r'Most Voted', '', option_text)
                    option_text = re.sub(r'\n+', ' ', option_text)
                    option_text = option_text.strip()
                    if option_text and len(option_text) > 0:
                        options[letter] = option_text

            if not options:
                for letter in ['A', 'B', 'C', 'D']:
                    pattern = rf'{letter}\.\s+(.*?)(?=\n[A-D]\.|\nShow|\nANSWERS|$)'
                    match = re.search(pattern, full_text, re.DOTALL)
                    if match:
                        options[letter] = match.group(1).strip()[:200]

            return {
                "question": question_text,
                "options": options,
                "correct": correct_answers,
                "images": images
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def start_session(self):
        range_input = simpledialog.askstring(
            "Question Range", 
            "Enter question range (e.g., 1-90 or 50-356):",
            parent=self.root
        )
        
        if not range_input:
            self.root.destroy()
            return
        
        try:
            start_num, end_num = map(int, range_input.split('-'))
            if start_num < 1 or end_num > 358 or start_num > end_num:
                raise ValueError("Invalid range")
            
            for i in range(start_num, end_num + 1):
                pdf_path = os.path.join(self.questions_dir, f"terraform_q{i}.pdf")
                if os.path.exists(pdf_path):
                    data = self.extract_pdf_data(pdf_path)
                    if data and data['options']:
                        self.questions_data.append(data)
            
            if not self.questions_data:
                messagebox.showerror("Error", "No questions found in the specified range!")
                self.root.destroy()
                return
            
            self.load_question()
            
        except ValueError:
            messagebox.showerror("Error", "Invalid format! Use format like: 1-90")
            self.root.destroy()

    def load_question(self):
        if self.current_q_index >= len(self.questions_data):
            return
        
        self.answered = False
        self.selected_answers = []
        self.next_button.pack_forget()
        
        # Scroll to top
        self.canvas.yview_moveto(0)
        
        # Clear previous options
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.option_buttons = []
        
        # Get current question
        data = self.questions_data[self.current_q_index]
        correct_count = len(data['correct'])
        
        # Update question label with multi-answer hint
        question_text = f"Question {self.current_q_index + 1} of {len(self.questions_data)}\n\n{data['question']}"
        if correct_count > 1:
            question_text += f"\n\n⚠️ Select {correct_count} answers"
        
        self.question_label.config(text=question_text)
        
        # Display images if they exist (code snippets, diagrams, etc.)
        self.image_references = []
        
        if data.get('images') and len(data['images']) > 0:
            for img_bytes in data['images']:
                try:
                    # Convert bytes to PIL Image
                    pil_image = Image.open(BytesIO(img_bytes))
                    
                    # Resize image if too large (max width 900px)
                    max_width = 900
                    if pil_image.width > max_width:
                        ratio = max_width / pil_image.width
                        new_height = int(pil_image.height * ratio)
                        pil_image = pil_image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(pil_image)
                    self.image_references.append(photo)
                    
                    # Create frame for image with background
                    img_container = tk.Frame(self.options_frame, bg="#2c3e50", relief="solid", borderwidth=2)
                    img_container.pack(fill="x", pady=15, padx=10)
                    
                    # Create label to display image
                    img_label = tk.Label(img_container, image=photo, bg="#ffffff", padx=10, pady=10)
                    img_label.pack()
                    
                except Exception as e:
                    print(f"Error displaying image: {e}")
        
        # Create option buttons for available options only
        available_options = sorted(data['options'].keys())
        
        for letter in available_options:
            option_text = data['options'][letter]
            
            option_container = tk.Frame(self.options_frame, bg="#f5f7fa")
            option_container.pack(fill="x", pady=6)
            
            btn_frame = tk.Frame(option_container, bg="#ffffff", relief="solid", borderwidth=1)
            btn_frame.pack(fill="x")
            
            btn = tk.Label(
                btn_frame, 
                text=f"{letter}. {option_text}",
                wraplength=900,
                anchor="w",
                justify="left",
                font=("Segoe UI", 12),
                bg="#ffffff",
                fg="#2c3e50",
                padx=25,
                pady=18,
                cursor="hand2"
            )
            btn.pack(fill="x")
            btn.bind("<Button-1>", lambda e, l=letter, f=btn_frame: self.toggle_answer(l, f))
            self.option_buttons.append((letter, btn, btn_frame))
            
            def on_enter(e, b=btn):
                if not self.answered:
                    b.config(bg="#f0f3f7")
            
            def on_leave(e, b=btn, l=letter):
                if not self.answered and l not in self.selected_answers:
                    b.config(bg="#ffffff")
            
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def toggle_answer(self, letter, btn_frame):
        if self.answered:
            return
        
        data = self.questions_data[self.current_q_index]
        required_count = len(data['correct'])
        
        if letter in self.selected_answers:
            self.selected_answers.remove(letter)
            for l, btn, frame in self.option_buttons:
                if l == letter:
                    btn.config(bg="#ffffff")
                    frame.config(bg="#ffffff", borderwidth=1)
        else:
            self.selected_answers.append(letter)
            for l, btn, frame in self.option_buttons:
                if l == letter:
                    btn.config(bg="#bbdefb")
                    frame.config(bg="#bbdefb", borderwidth=2)
        
        if len(self.selected_answers) == required_count:
            self.check_answer()

    def check_answer(self):
        if self.answered:
            return
        
        self.answered = True
        correct_answers = self.questions_data[self.current_q_index]['correct']
        
        is_correct = set(self.selected_answers) == set(correct_answers)
        
        for letter, btn, btn_frame in self.option_buttons:
            btn.unbind("<Enter>")
            btn.unbind("<Leave>")
            btn.unbind("<Button-1>")
            btn.config(cursor="arrow")
            
            if letter in correct_answers:
                btn.config(bg="#4caf50", fg="white", font=("Segoe UI", 12, "bold"))
                btn_frame.config(bg="#4caf50", borderwidth=3)
            elif letter in self.selected_answers:
                btn.config(bg="#ffc107", fg="#000000", font=("Segoe UI", 12, "bold"))
                btn_frame.config(bg="#ffc107", borderwidth=3)
        
        if is_correct:
            self.score_right += 1
        else:
            self.score_wrong += 1
        
        self.score_label.config(text=f"✓ Correct: {self.score_right}    ✗ Wrong: {self.score_wrong}")
        
        self.next_button.pack(pady=25)

    def load_next_question(self):
        self.current_q_index += 1
        
        if self.current_q_index < len(self.questions_data):
            self.load_question()
        else:
            percentage = (self.score_right / len(self.questions_data)) * 100
            messagebox.showinfo(
                "🎉 Quiz Complete!",
                f"Congratulations! You've finished all questions!\n\n"
                f"📊 Final Score:\n"
                f"✓ Correct: {self.score_right}\n"
                f"✗ Wrong: {self.score_wrong}\n"
                f"📈 Percentage: {percentage:.1f}%",
                parent=self.root
            )
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TerraformQuizApp(root)
    root.mainloop()