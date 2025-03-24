import sys
import platform
import logging
import re
import asyncio
import os
from datetime import datetime
import json
import threading
from queue import Queue
import tracemalloc
from dotenv import load_dotenv
from pathlib import Path
from universal_orchestrator import orchestrator
from terminal_manager import terminal_manager
import traceback
import nest_asyncio

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Verify and export critical environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

# Ensure OPENAI_API_KEY is explicitly set in the environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

# Enable tracemalloc
tracemalloc.start()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent.log')
    ]
)
logger = logging.getLogger(__name__)

# Determine which UI framework to use
IS_MACOS = platform.system() == "Darwin"
USE_QT = IS_MACOS  # Use Qt on macOS

# Import UI frameworks and define base classes
if USE_QT:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                                QHBoxLayout, QPushButton, QTextEdit, QLabel)
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    BaseThread = QThread
else:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    BaseThread = threading.Thread

WELCOME_MESSAGE = """👋 Welcome to the AI Assistant!

I can help you with various tasks:

1. 🌐 Web Search and News
2. 🏗️ Terraform Infrastructure
3. 💻 Development Environment Setup
4. ☁️ AWS CLI Configuration
5. 📂 File System Operations
6. 🖥️ Terminal Interface

Type your request or toggle terminal mode to use terminal commands.
Use ! prefix to execute terminal commands in chat mode.
"""

class AsyncProcessor(BaseThread):
    """Handle async processing for both UI frameworks"""
    if USE_QT:
        output_ready = pyqtSignal(str)
        error_occurred = pyqtSignal(str)

    def __init__(self, command_queue, output_queue):
        super().__init__()
        self.command_queue = command_queue
        self.output_queue = output_queue
        self.loop = None
        self.daemon = True
        self._running = True

    async def process_message(self, message, mode):
        """Process a message asynchronously"""
        try:
            if mode == "terminal":
                if message.lower() == "exit":
                    return "exit_terminal"
                elif message.lower() == "clear":
                    return "clear_screen"
                else:
                    result = await terminal_manager.execute_command(message)
                    terminal_manager.terminal.update_prompt()
                    return f"{result}\n{terminal_manager.terminal.prompt}"
            else:
                if message.startswith('!'):
                    command = message[1:].strip()
                    result = await terminal_manager.execute_command(command)
                    return f"📝 Output:\n{result}"
                
                try:
                    # Use the current event loop
                    response = await orchestrator.process_request(message)
                    return response
                except Exception as e:
                    logger.error(f"Error in orchestrator: {str(e)}")
                    logger.error(traceback.format_exc())
                    return f"❌ Error processing request: {str(e)}"

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            if "429" in str(e):
                error_msg += "\nRate limit reached. Please try again in a few minutes."
            return error_msg

    async def process_commands(self):
        while self._running:
            try:
                if not self.command_queue.empty():
                    command, mode = self.command_queue.get()
                    result = await self.process_message(command, mode)
                    if USE_QT:
                        self.output_ready.emit(result)
                    else:
                        self.output_queue.put(result)
                await asyncio.sleep(0.1)
            except Exception as e:
                error_msg = f"❌ Internal error: {str(e)}"
                logger.error(f"Error in process_commands: {str(e)}")
                logger.error(traceback.format_exc())
                if USE_QT:
                    self.error_occurred.emit(error_msg)
                else:
                    self.output_queue.put(error_msg)

    def stop(self):
        """Stop the async processor"""
        self._running = False
        if self.loop and self.loop.is_running():
            try:
                self.loop.stop()
            except Exception as e:
                logger.error(f"Error stopping loop: {str(e)}")

    def run(self):
        """Thread entry point"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Create and run the main task
            main_task = self.loop.create_task(self.process_commands())
            self.loop.run_until_complete(main_task)
            
        except Exception as e:
            logger.error(f"Error in run: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            if self.loop and self.loop.is_running():
                try:
                    pending = asyncio.all_tasks(self.loop)
                    self.loop.run_until_complete(asyncio.gather(*pending))
                    self.loop.close()
                except Exception as e:
                    logger.error(f"Error cleaning up loop: {str(e)}")

if USE_QT:
    class QtUI(QMainWindow):
        """PyQt6 UI implementation for macOS"""
        def __init__(self):
            super().__init__()
            self.setWindowTitle("AI Assistant")
            self.setGeometry(100, 100, 800, 600)
            
            # Initialize variables
            self.mode = "chat"
            self.command_queue = Queue()
            self.output_queue = Queue()
            
            # Create central widget and layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Create UI elements
            self.create_output_area(layout)
            self.create_input_area(layout)
            self.create_buttons(layout)
            
            # Start async processor
            self.async_processor = AsyncProcessor(self.command_queue, self.output_queue)
            self.async_processor.output_ready.connect(self.handle_output)
            self.async_processor.error_occurred.connect(self.handle_error)
            self.async_processor.start()
            
            # Show welcome message
            self.show_welcome_message()

        def create_output_area(self, layout):
            self.output_text = QTextEdit()
            self.output_text.setReadOnly(True)
            self.output_text.setFont(QApplication.font("Courier"))
            layout.addWidget(self.output_text)

        def create_input_area(self, layout):
            self.input_text = QTextEdit()
            self.input_text.setMaximumHeight(70)
            self.input_text.setFont(QApplication.font("Courier"))
            # Install event filter for handling key press events
            self.input_text.installEventFilter(self)
            layout.addWidget(self.input_text)

        def create_buttons(self, layout):
            button_layout = QHBoxLayout()
            
            self.send_button = QPushButton("Send")
            self.send_button.clicked.connect(self.send_message)
            button_layout.addWidget(self.send_button)
            
            self.terminal_button = QPushButton("Toggle Terminal Mode")
            self.terminal_button.clicked.connect(self.toggle_terminal_mode)
            button_layout.addWidget(self.terminal_button)
            
            self.clear_button = QPushButton("Clear")
            self.clear_button.clicked.connect(self.clear_output)
            button_layout.addWidget(self.clear_button)
            
            layout.addLayout(button_layout)

        def eventFilter(self, obj, event):
            if obj is self.input_text and event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_message()
                    return True
                elif event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Allow Shift+Enter for new line
                    return False
            return super().eventFilter(obj, event)

        def keyPressEvent(self, event):
            # Handle global key events
            super().keyPressEvent(event)

        def append_output(self, text):
            self.output_text.append(text)

        def clear_output(self):
            self.output_text.clear()
            if self.mode == "terminal":
                self.show_terminal_prompt()

        def show_welcome_message(self):
            self.append_output(WELCOME_MESSAGE)

        def show_terminal_prompt(self):
            prompt = terminal_manager.terminal.prompt
            self.append_output(prompt)

        def toggle_terminal_mode(self):
            if self.mode == "chat":
                self.mode = "terminal"
                self.append_output("\nSwitched to terminal mode")
                self.show_terminal_prompt()
            else:
                self.mode = "chat"
                self.append_output("\nSwitched to chat mode")

        def send_message(self):
            message = self.input_text.toPlainText().strip()
            if not message:
                return
            
            self.input_text.clear()
            if self.mode == "terminal":
                self.append_output(message)
            else:
                self.append_output(f"You: {message}")
            
            self.command_queue.put((message, self.mode))

        def handle_output(self, output):
            if output == "exit_terminal":
                self.mode = "chat"
                self.append_output("Exited terminal mode. Back to chat mode.")
            elif output == "clear_screen":
                self.clear_output()
            else:
                self.append_output(output)

        def handle_error(self, error):
            self.append_output(error)

else:
    class TkUI(tk.Frame):
        """Tkinter UI implementation for non-macOS platforms"""
        def __init__(self, root):
            super().__init__(root)
            self.root = root
            self.root.title("AI Assistant")
            self.root.geometry("800x600")
            
            # Initialize variables
            self.mode = "chat"  # chat or terminal
            self.command_queue = Queue()
            self.output_queue = Queue()
            
            # Pack the main frame
            self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create output text area
            self.create_output_area()
            
            # Create input area
            self.create_input_area()
            
            # Create buttons
            self.create_buttons()
            
            # Start async processor
            self.async_processor = AsyncProcessor(self.command_queue, self.output_queue)
            self.async_processor.start()
            
            # Start output processing
            self.root.after(100, self.process_output_queue)
            
            # Show welcome message
            self.show_welcome_message()

        def create_output_area(self):
            self.output_text = scrolledtext.ScrolledText(
                self,
                wrap=tk.WORD,
                height=20,
                font=("Courier", 10)
            )
            self.output_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.output_text.config(state=tk.DISABLED)

        def create_input_area(self):
            self.input_text = scrolledtext.ScrolledText(
                self,
                wrap=tk.WORD,
                height=3,
                font=("Courier", 10)
            )
            self.input_text.pack(fill=tk.X, pady=(0, 10))
            
            # Bind Enter and Shift+Enter keys
            self.input_text.bind("<Return>", self.handle_return)
            self.input_text.bind("<Shift-Return>", self.handle_shift_return)

        def create_buttons(self):
            button_frame = ttk.Frame(self)
            button_frame.pack(fill=tk.X)
            
            self.send_button = ttk.Button(
                button_frame,
                text="Send",
                command=self.send_message
            )
            self.send_button.pack(side=tk.LEFT, padx=5)
            
            self.terminal_button = ttk.Button(
                button_frame,
                text="Toggle Terminal Mode",
                command=self.toggle_terminal_mode
            )
            self.terminal_button.pack(side=tk.LEFT, padx=5)
            
            self.clear_button = ttk.Button(
                button_frame,
                text="Clear",
                command=self.clear_output
            )
            self.clear_button.pack(side=tk.LEFT, padx=5)

        def append_output(self, text, tag=None):
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, text + "\n", tag)
            self.output_text.see(tk.END)
            self.output_text.config(state=tk.DISABLED)

        def clear_output(self):
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete(1.0, tk.END)
            self.output_text.config(state=tk.DISABLED)
            if self.mode == "terminal":
                self.show_terminal_prompt()

        def show_welcome_message(self):
            self.append_output(WELCOME_MESSAGE)

        def show_terminal_prompt(self):
            prompt = terminal_manager.terminal.prompt
            self.append_output(prompt, "prompt")

        def toggle_terminal_mode(self):
            if self.mode == "chat":
                self.mode = "terminal"
                self.append_output("\nSwitched to terminal mode")
                self.show_terminal_prompt()
            else:
                self.mode = "chat"
                self.append_output("\nSwitched to chat mode")

        def handle_return(self, event):
            """Handle Enter key press"""
            self.send_message()
            return "break"  # Prevent default behavior

        def handle_shift_return(self, event):
            """Handle Shift+Enter key press"""
            return None  # Allow default behavior (new line)

        def send_message(self):
            message = self.input_text.get(1.0, tk.END).strip()
            if not message:
                return
                
            self.input_text.delete(1.0, tk.END)
            if self.mode == "terminal":
                self.append_output(message)
            else:
                self.append_output(f"You: {message}")
            
            self.command_queue.put((message, self.mode))

        def process_output_queue(self):
            while not self.output_queue.empty():
                output = self.output_queue.get()
                self.append_output(output)
            
            self.root.after(100, self.process_output_queue)

def cleanup():
    """Cleanup function to be called before exit"""
    tracemalloc.stop()

def main():
    try:
        if USE_QT:
            app = QApplication(sys.argv)
            app.setStyle('Fusion')  # Use Fusion style for better macOS compatibility
            window = QtUI()
            window.show()
            app.aboutToQuit.connect(cleanup)  # Connect cleanup to quit signal
            sys.exit(app.exec())
        else:
            root = tk.Tk()
            app = TkUI(root)
            root.protocol("WM_DELETE_WINDOW", lambda: [cleanup(), root.destroy()])  # Add cleanup to window close
            root.mainloop()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main() 