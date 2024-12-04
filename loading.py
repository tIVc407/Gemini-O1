import random
import time
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk  # Added import for Progressbar
from threading import Thread
from typing import Tuple  # Added import for Tuple

class LoadingScreenGenerator:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.verbs = [
            "Raising", "Calibrating", "Reticulating", "Downloading", "Configuring",
            "Optimizing", "Synchronizing", "Initializing", "Defragmenting", "Updating"
        ]
        
        self.objects = [
            "Dongles", "Splines", "Quantum Bits", "Memory Beans", "Data Hamsters",
            "Digital Sprockets", "Flux Capacitors", "Random Numbers", "Code Monkeys",
            "Processing Units", "Neural Pathways", "Binary Trees", "Stack Overflow",
            "Cache Cookies", "Buffer Zones", "Logic Gates", "Pixel Dust"
        ]
        
        self.adjectives = [
            "Virtual", "Digital", "Quantum", "Cyber", "Neural",
            "Binary", "Automated", "Encrypted", "Cloud-Based", "AI-Powered",
            "Blockchain", "Organic", "Free-Range", "Artisanal"
        ]
        
        self.percentages = [
            "{}%", "{}.{}%", "{}% of {}%", "Phase {} of {}"
        ]

        # Extend the lists with more words...
        # (Include the extended lists here)

    def generate_message(self) -> Tuple[str, int]:
        """Generate a random loading message with completion percentage."""
        verb = random.choice(self.verbs)
        obj = random.choice(self.objects)
        adj = random.choice(self.adjectives)
        percent = random.choice(self.percentages).format(random.randint(0, 99), random.randint(0, 9), random.randint(0, 99), random.randint(0, 99))
        message = f"{verb} {adj} {obj}"
        delay = random.uniform(0.1, 0.5)
        
        return f"{message}... {percent}", delay

    def run_loading_sequence(self, num_steps: int = 40):
        """Run a sequence of loading messages in the GUI."""
        self.text_widget.insert(tk.END, "Commencing Ultimate Loading Experience... Brace yourself!\n")
        self.text_widget.yview(tk.END)  # Scroll to the bottom

        for i in range(num_steps):
            message, delay = self.generate_message()
            self.text_widget.insert(tk.END, message + '\n')
            self.text_widget.yview(tk.END)  # Scroll to the bottom
            self.progress['value'] = (i + 1) * (100 / num_steps)  # Update progress bar
            time.sleep(delay)
        
        self.text_widget.insert(tk.END, "\nAll systems go! The universe is at your command!\n")
        self.text_widget.yview(tk.END)  # Scroll to the bottom

def start_loading():
    loader = LoadingScreenGenerator(text_widget)
    loader.run_loading_sequence()

# Set up the GUI
root = tk.Tk()
root.title("Loading Screen Simulator")

# Create a text widget with a scrollbar
text_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20, state='normal')
text_widget.pack(pady=10)

# Add a progress bar
progress = ttk.Progressbar(root, orient='horizontal', length=400, mode='determinate')
progress.pack(pady=10)
# Assign progress bar to loader
LoadingScreenGenerator.progress = progress

# Add a Start button
start_button = tk.Button(root, text="Start Loading", command=lambda: Thread(target=start_loading).start())
start_button.pack(pady=10)

# Start the main event loop
root.mainloop()
