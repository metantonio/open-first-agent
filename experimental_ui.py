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
import markdown
from bs4 import BeautifulSoup
import webbrowser
import paramiko

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
                                QHBoxLayout, QPushButton, QTextEdit, QLabel,
                                QProgressBar, QTextBrowser, QDockWidget, QComboBox)
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QUrl
    from PyQt6.QtGui import QTextCursor, QDesktopServices, QSyntaxHighlighter, QTextCharFormat, QColor
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

TERMINAL_WELCOME_MESSAGE = """
🖥️ Terminal Mode Activated 🖥️

Common Commands:
- ls, cd, pwd: File system navigation
- cat, less: View file contents
- mkdir, rm, cp, mv: File operations
- grep: Search in files
- ps, top: Process management
- clear: Clear screen
- exit: Return to chat mode

SSH Commands:
- ssh help: Show SSH commands
- ssh user@hostname: Connect to remote host
- scp source destination: Copy files securely
- ssh-keygen: Generate SSH key pair
- ssh-copy-id user@hostname: Copy SSH key to server

Type 'help' for more commands or 'exit' to return to chat mode.
"""

# Add CSS styles for markdown rendering
MARKDOWN_CSS = """
<style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; }
    h1 { color: #2c3e50; border-bottom: 2px solid #eee; }
    h2 { color: #2c3e50; border-bottom: 1px solid #eee; }
    h3, h4, h5, h6 { color: #2c3e50; }
    code { 
        background-color: #1E1E1E; 
        color: #D4D4D4; 
        padding: 2px 4px; 
        border-radius: 4px; 
        font-family: 'Courier New', monospace;
    }
    pre { 
        background-color: #1E1E1E; 
        color: #D4D4D4;
        padding: 1em; 
        border-radius: 4px; 
        overflow-x: auto;
        font-family: 'Courier New', monospace;
    }
    pre code {
        background-color: transparent;
        padding: 0;
        border-radius: 0;
    }
    blockquote { border-left: 4px solid #eee; margin-left: 0; padding-left: 1em; color: #666; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f8f9fa; }
    a { color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    img { max-width: 100%; height: auto; }
    ul, ol { padding-left: 2em; }
    li { margin: 0.5em 0; }
</style>
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

    async def debug_ssh_connection(self, hostname, username, key_path):
        """
        Debug SSH connection with detailed logging and error handling
        """
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        try:
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load private key
            private_key = paramiko.RSAKey.from_private_key_file(key_path)

            # Set connection timeout and logging
            logger.info(f"Attempting to connect to {hostname} as {username}")
            
            try:
                # Use asyncio to set a timeout
                with asyncio.timeout(10):  # 10-second timeout
                    client.connect(
                        hostname, 
                        username=username, 
                        pkey=private_key,
                        timeout=10
                    )
                
                logger.info("SSH Connection successful")
                
                # Try running a simple command
                stdin, stdout, stderr = client.exec_command('whoami')
                result = stdout.read().decode().strip()
                logger.info(f"Remote user: {result}")

            except asyncio.TimeoutError:
                logger.error("Connection timed out")
                return {"status": "error", "message": "Connection timed out"}
            except paramiko.AuthenticationException:
                logger.error("Authentication failed")
                return {"status": "error", "message": "Authentication failed"}
            except paramiko.SSHException as ssh_exception:
                logger.error(f"SSH Exception: {ssh_exception}")
                return {"status": "error", "message": str(ssh_exception)}
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {"status": "error", "message": str(e)}
            
            finally:
                client.close()

        except Exception as setup_error:
            logger.error(f"Setup error: {setup_error}")
            return {"status": "error", "message": str(setup_error)}

    async def process_message(self, message, mode):
        """Process a message asynchronously"""
        try:
            if mode == "terminal":
                if message.lower() == "exit":
                    return "exit_terminal"
                elif message.lower() == "clear":
                    return "clear_screen"
                else:
                    try:
                        # Execute the command asynchronously
                        result = await terminal_manager.execute_command(message)
                        if result is None or result.strip() == "":
                            result = "Command executed successfully"
                        terminal_manager.terminal.update_prompt()
                        return f"{result}\n{terminal_manager.terminal.prompt}"
                    except Exception as e:
                        return f"Error executing command: {str(e)}\n{terminal_manager.terminal.prompt}"
            else:
                if message.startswith('ssh'):
                    # Remove 'connect' from the command if present
                    if 'connect' in message:
                        message = message.replace('connect', '').strip()
                    
                    # Check if command line arguments are provided
                    if len(message.split()) > 2:
                        try:
                            # Parse command line arguments
                            params = parse_ssh_args(message)
                            
                            # If we have both hostname and username
                            if 'hostname' in params and 'username' in params:
                                # Call the debug function instead of connect_ssh
                                result = await self.debug_ssh_connection(
                                    hostname=params['hostname'],
                                    username=params['username'],
                                    key_path=params['key_path']
                                )
                                await cl.Message(content=result['message']).send()
                                return
                            else:
                                # Missing required parameters, fall back to interactive mode
                                await handle_ssh_connection()
                                return
                        except ValueError as e:
                            await cl.Message(content=f"❌ Error parsing arguments: {str(e)}").send()
                            return
                        except Exception as e:
                            await cl.Message(content=f"❌ Error during SSH connection: {str(e)}").send()
                            return
                elif message.startswith('!'):
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

def parse_ssh_args(command: str) -> dict:
    """Parse SSH command line arguments into a dictionary."""
    args = command.split()
    params = {}
    i = 2  # Skip 'ssh connect'
    
    while i < len(args):
        if args[i] in ['-h', '--host']:
            if i + 1 < len(args):
                params['hostname'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing hostname value after -h/--host")
        elif args[i] in ['-u', '--user']:
            if i + 1 < len(args):
                params['username'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing username value after -u/--user")
        elif args[i] in ['-k', '--key']:
            if i + 1 < len(args):
                params['key_path'] = args[i + 1]
                i += 2
            else:
                raise ValueError("Missing key path value after -k/--key")
        else:
            raise ValueError(f"Unknown argument: {args[i]}")  # Raise an error for unknown arguments
    
    return params

async def handle_ssh_connection():
    """Handle SSH connection with proper user input handling"""
    try:
        # Ask for connection details
        hostname = input("Enter hostname (e.g., example.com): ")
        if not hostname:
            print("Connection cancelled - no hostname provided")
            return
            
        username = input("Enter username: ")
        if not username:
            print("Connection cancelled - no username provided")
            return
            
        auth_method = input("Choose authentication method (password/key): ")
        if not auth_method or auth_method.lower() not in ['password', 'key']:
            print("Invalid authentication method. Please use 'password' or 'key'")
            return
            
        if auth_method.lower() == 'password':
            password = input("Enter password: ")
            if not password:
                print("Connection cancelled - no password provided")
                return
                
            # Connect with password
            result = await terminal_manager.terminal.connect_ssh(
                hostname=hostname,
                username=username,
                password=password
            )
        else:
            key_path = input("Enter path to private key file: ")
            if not key_path:
                print("Connection cancelled - no key path provided")
                return
                
            # Try connecting without key password first
            result = await terminal_manager.terminal.connect_ssh(
                hostname=hostname,
                username=username,
                key_path=key_path
            )
            
            # If key is encrypted, ask for password
            if result.get('details', {}).get('error_type') == 'encrypted_key':
                key_password = input("Key is encrypted. Please enter key password: ")
                if not key_password:
                    print("Connection cancelled - no key password provided")
                    return
                    
                # Try again with key password
                result = await terminal_manager.terminal.connect_ssh(
                    hostname=hostname,
                    username=username,
                    key_path=key_path,
                    key_password=key_password
                )
        
        # Handle connection result
        if result['status'] == 'success':
            print(f"✅ {result['message']}")
            return True
        else:
            print(f"❌ Connection failed: {result['message']}")
            if 'error' in result.get('details', {}):
                print(f"Error details: {result['details']['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error during SSH connection: {str(e)}")
        return False

if USE_QT:
    class TerminalDockWidget(QDockWidget):
        """Dockable terminal widget"""
        def __init__(self, parent=None):
            super().__init__("Terminal", parent)
            self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
            
            # Create terminal widget
            self.terminal_widget = QWidget()
            self.setWidget(self.terminal_widget)
            
            # Create layout
            layout = QVBoxLayout(self.terminal_widget)
            
            # Create terminal output area with monospace font and dark theme
            self.terminal_output = QTextBrowser()
            self.terminal_output.setFont(QApplication.font("Courier"))
            self.terminal_output.setStyleSheet("""
                QTextBrowser {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border: none;
                    font-family: 'Courier New', monospace;
                }
            """)
            self.terminal_output.setReadOnly(True)
            layout.addWidget(self.terminal_output)
            
            # Create terminal input area with matching style
            self.terminal_input = QTextEdit()
            self.terminal_input.setMaximumHeight(50)
            self.terminal_input.setFont(QApplication.font("Courier"))
            self.terminal_input.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #FFFFFF;
                    border: none;
                    border-top: 1px solid #333333;
                    font-family: 'Courier New', monospace;
                }
            """)
            layout.addWidget(self.terminal_input)
            
            # Create send button with matching style
            self.send_button = QPushButton("Send")
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    color: #FFFFFF;
                    border: none;
                    padding: 5px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
            """)
            layout.addWidget(self.send_button)

        def append_output(self, text):
            """Append text to terminal output with proper formatting"""
            cursor = self.terminal_output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.terminal_output.setTextCursor(cursor)
            self.terminal_output.insertPlainText(text + '\n')
            self.terminal_output.ensureCursorVisible()

    class CodeViewerDockWidget(QDockWidget):
        """Dockable code viewer widget with syntax highlighting"""
        def __init__(self, parent=None):
            super().__init__("Code Viewer", parent)
            self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
            
            # Create main widget
            self.main_widget = QWidget()
            self.setWidget(self.main_widget)
            layout = QVBoxLayout(self.main_widget)
            
            # Create toolbar
            toolbar = QHBoxLayout()
            
            # Add language selector
            self.language_selector = QComboBox()
            self.language_selector.addItems(["python", "javascript", "bash", "shell", "sas"])
            self.language_selector.currentTextChanged.connect(self.update_highlighting)
            toolbar.addWidget(QLabel("Language:"))
            toolbar.addWidget(self.language_selector)
            
            # Add copy button
            self.copy_button = QPushButton("Copy Code")
            self.copy_button.clicked.connect(self.copy_code)
            toolbar.addWidget(self.copy_button)
            
            layout.addLayout(toolbar)
            
            # Create code editor
            self.code_editor = QTextEdit()
            self.code_editor.setFont(QApplication.font("Courier"))
            self.code_editor.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: none;
                    font-family: 'Courier New', monospace;
                }
            """)
            self.code_editor.setReadOnly(True)
            layout.addWidget(self.code_editor)

        def set_code(self, code, language=None):
            """Set the code content and optionally specify the language"""
            self.code_editor.setPlainText(code)
            if language:
                index = self.language_selector.findText(language.lower())
                if index >= 0:
                    self.language_selector.setCurrentIndex(index)
            self.update_highlighting()

        def copy_code(self):
            """Copy code to clipboard"""
            QApplication.clipboard().setText(self.code_editor.toPlainText())

        def update_highlighting(self):
            """Update syntax highlighting based on selected language"""
            # Basic syntax highlighting could be implemented here
            pass

    class QtUI(QMainWindow):
        """PyQt6 UI implementation for macOS"""
        def __init__(self):
            super().__init__()
            self.setWindowTitle("AI Assistant")
            self.setGeometry(100, 100, 1200, 600)  # Made window wider
            
            # Initialize variables
            self.mode = "chat"
            self.command_queue = Queue()
            self.output_queue = Queue()
            self.markdown_mode = True  # Start with markdown mode active
            self.is_processing = False
            
            # Create central widget and layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Create terminal dock widget
            self.terminal_dock = TerminalDockWidget(self)
            self.terminal_dock.hide()
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.terminal_dock)
            
            # Create code viewer dock widget
            self.code_viewer = CodeViewerDockWidget(self)
            self.code_viewer.hide()
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.code_viewer)
            
            # Create UI elements
            self.create_output_area(layout)
            self.create_input_area(layout)
            self.create_loading_indicator(layout)
            self.create_buttons(layout)
            
            # Connect signals
            self.terminal_dock.terminal_input.installEventFilter(self)
            self.terminal_dock.send_button.clicked.connect(self.send_terminal_command)
            
            # Start async processor
            self.async_processor = AsyncProcessor(self.command_queue, self.output_queue)
            self.async_processor.output_ready.connect(self.handle_output)
            self.async_processor.error_occurred.connect(self.handle_error)
            self.async_processor.start()
            
            # Show welcome message
            self.show_welcome_message()

            # Connect text browser signals
            self.output_text.anchorClicked.connect(self.handle_link_click)
            self.output_text.setOpenLinks(False)

        def create_output_area(self, layout):
            self.output_text = QTextBrowser()
            self.output_text.setOpenExternalLinks(True)
            self.output_text.setReadOnly(True)
            self.output_text.setFont(QApplication.font("Courier"))
            self.output_text.setAcceptRichText(True)
            layout.addWidget(self.output_text)

        def create_input_area(self, layout):
            self.input_text = QTextEdit()
            self.input_text.setMaximumHeight(70)
            self.input_text.setFont(QApplication.font("Courier"))
            # Install event filter for handling key press events
            self.input_text.installEventFilter(self)
            layout.addWidget(self.input_text)

        def create_loading_indicator(self, layout):
            loading_layout = QHBoxLayout()
            
            self.loading_bar = QProgressBar()
            self.loading_bar.setTextVisible(False)
            self.loading_bar.setMaximumHeight(2)  # Make it thin
            self.loading_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                }
            """)
            self.loading_bar.hide()
            
            loading_layout.addWidget(self.loading_bar)
            layout.addLayout(loading_layout)

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

            self.markdown_button = QPushButton("Toggle Markdown")
            self.markdown_button.clicked.connect(self.toggle_markdown)
            button_layout.addWidget(self.markdown_button)
            
            layout.addLayout(button_layout)

        def eventFilter(self, obj, event):
            if obj is self.input_text and event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_message()
                    return True
                elif event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    # Allow Shift+Enter for new line
                    return False
            elif obj is self.terminal_dock.terminal_input and event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_terminal_command()
                    return True
            return super().eventFilter(obj, event)

        def keyPressEvent(self, event):
            # Handle global key events
            super().keyPressEvent(event)

        def append_output(self, text):
            if self.markdown_mode and not self.mode == "terminal":
                # Check for code blocks before converting to HTML
                code_blocks = re.findall(r'```(\w+)?\n(.*?)\n```', text, re.DOTALL)
                
                # Convert markdown to HTML with custom CSS
                html_content = markdown.markdown(text, extensions=['fenced_code', 'tables'])
                styled_html = f"{MARKDOWN_CSS}\n{html_content}"
                self.output_text.setHtml(styled_html)
                
                # If code blocks were found, show them in the code viewer
                if code_blocks:
                    language, code = code_blocks[0]  # Show the first code block
                    self.code_viewer.show()
                    self.code_viewer.set_code(code.strip(), language)
            else:
                # Convert URLs to clickable links
                text_with_links = self.convert_urls_to_links(text)
                self.output_text.append(text_with_links)

        def convert_urls_to_links(self, text):
            """Convert URLs in text to HTML links"""
            url_pattern = r'(https?://\S+)'
            return re.sub(url_pattern, r'<a href="\1">\1</a>', text)

        def clear_output(self):
            self.output_text.clear()
            if self.mode == "terminal":
                self.show_terminal_prompt()

        def show_welcome_message(self):
            # Convert welcome message to HTML since markdown mode is active by default
            html_content = markdown.markdown(WELCOME_MESSAGE, extensions=['fenced_code', 'tables'])
            styled_html = f"{MARKDOWN_CSS}\n{html_content}"
            self.output_text.setHtml(styled_html)

        def show_terminal_prompt(self):
            prompt = terminal_manager.terminal.prompt
            self.append_output(prompt)

        def toggle_terminal_mode(self):
            if self.mode == "chat":
                self.mode = "terminal"
                self.terminal_dock.show()
                self.terminal_dock.terminal_output.append(TERMINAL_WELCOME_MESSAGE)
                self.terminal_dock.terminal_output.append(terminal_manager.terminal.prompt)
            else:
                self.mode = "chat"
                self.terminal_dock.hide()
                self.append_output("\nSwitched to chat mode")

        def toggle_markdown(self):
            self.markdown_mode = not self.markdown_mode
            current_text = self.output_text.toPlainText()
            self.output_text.clear()
            
            if self.markdown_mode:
                # Convert markdown to HTML with custom CSS
                html_content = markdown.markdown(current_text, extensions=['fenced_code', 'tables'])
                styled_html = f"{MARKDOWN_CSS}\n{html_content}"
                self.output_text.setHtml(styled_html)
            else:
                # Show plain text
                self.output_text.setPlainText(current_text)

        def show_loading(self, show=True):
            if show:
                self.loading_bar.setRange(0, 0)  # Indeterminate mode
                self.loading_bar.show()
                self.is_processing = True
            else:
                self.loading_bar.hide()
                self.is_processing = False

        def send_message(self):
            message = self.input_text.toPlainText().strip()
            if not message:
                return
            
            self.input_text.clear()
            if self.mode == "terminal":
                self.append_output(message)
            else:
                self.append_output(f"You: {message}")
            
            self.show_loading(True)
            self.command_queue.put((message, self.mode))

        def handle_output(self, output):
            self.show_loading(False)
            if output == "exit_terminal":
                self.mode = "chat"
                self.terminal_dock.hide()
                self.append_output("Exited terminal mode. Back to chat mode.")
            elif output == "clear_screen":
                if self.mode == "terminal":
                    self.terminal_dock.terminal_output.clear()
                    self.terminal_dock.terminal_output.append(terminal_manager.terminal.prompt)
                else:
                    self.clear_output()
            else:
                if self.mode == "terminal":
                    self.terminal_dock.terminal_output.append(output)
                else:
                    self.append_output(output)

        def handle_error(self, error):
            self.show_loading(False)
            self.append_output(error)

        def handle_link_click(self, url):
            """Handle clicking on links in the output text"""
            QDesktopServices.openUrl(url)

        def send_terminal_command(self):
            """Send command from terminal input"""
            command = self.terminal_dock.terminal_input.toPlainText().strip()
            if not command:
                return
            
            self.terminal_dock.terminal_input.clear()
            self.terminal_dock.terminal_output.append(f"> {command}")
            
            self.show_loading(True)
            self.command_queue.put((command, "terminal"))

else:
    class TkUI(tk.Frame):
        """Tkinter UI implementation for non-macOS platforms"""
        def __init__(self, root):
            super().__init__(root)
            self.root = root
            self.root.title("AI Assistant")
            self.root.geometry("800x600")
            
            # Initialize variables
            self.mode = "chat"
            self.command_queue = Queue()
            self.output_queue = Queue()
            self.markdown_mode = False
            self.is_processing = False
            
            # Pack the main frame
            self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create output text area
            self.create_output_area()
            
            # Create loading indicator
            self.create_loading_indicator()
            
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

            # Configure tag for URLs
            self.output_text.tag_configure("url", foreground="blue", underline=1)
            self.output_text.tag_bind("url", "<Button-1>", self.handle_url_click)
            self.output_text.tag_bind("url", "<Enter>", lambda e: self.output_text.config(cursor="hand2"))
            self.output_text.tag_bind("url", "<Leave>", lambda e: self.output_text.config(cursor=""))

        def create_output_area(self):
            self.output_text = scrolledtext.ScrolledText(
                self,
                wrap=tk.WORD,
                height=20,
                font=("Courier", 10)
            )
            self.output_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.output_text.config(state=tk.DISABLED)

        def create_loading_indicator(self):
            self.loading_frame = ttk.Frame(self)
            self.loading_frame.pack(fill=tk.X, pady=(0, 5))
            
            self.loading_bar = ttk.Progressbar(
                self.loading_frame,
                mode='indeterminate',
                length=200
            )
            self.loading_bar.pack(fill=tk.X)
            self.loading_bar.pack_forget()  # Hide initially

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

            self.markdown_button = ttk.Button(
                button_frame,
                text="Toggle Markdown",
                command=self.toggle_markdown
            )
            self.markdown_button.pack(side=tk.LEFT, padx=5)

        def append_output(self, text, tag=None):
            self.output_text.config(state=tk.NORMAL)
            if self.markdown_mode and not self.mode == "terminal":
                # Convert markdown to styled text
                html_content = markdown.markdown(text, extensions=['fenced_code', 'tables'])
                soup = BeautifulSoup(html_content, 'html.parser')
                styled_text = self.style_markdown_text(soup.get_text())
                self.output_text.insert(tk.END, styled_text + "\n", tag)
            else:
                # Process text for URLs
                last_end = 0
                for match in re.finditer(r'(https?://\S+)', text):
                    start, end = match.span()
                    # Insert text before the URL
                    if start > last_end:
                        self.output_text.insert(tk.END, text[last_end:start])
                    # Insert URL with special tag
                    url = text[start:end]
                    self.output_text.insert(tk.END, url, ("url", url))
                    last_end = end
                # Insert remaining text
                if last_end < len(text):
                    self.output_text.insert(tk.END, text[last_end:])
                self.output_text.insert(tk.END, "\n")
            
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
                self.append_output(TERMINAL_WELCOME_MESSAGE)
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

        def show_loading(self, show=True):
            if show and not self.is_processing:
                self.loading_bar.pack(fill=tk.X)
                self.loading_bar.start(10)  # Speed of animation
                self.is_processing = True
            elif not show and self.is_processing:
                self.loading_bar.stop()
                self.loading_bar.pack_forget()
                self.is_processing = False

        def send_message(self):
            message = self.input_text.get(1.0, tk.END).strip()
            if not message:
                return
                
            self.input_text.delete(1.0, tk.END)
            if self.mode == "terminal":
                self.append_output(message)
            else:
                self.append_output(f"You: {message}")
            
            self.show_loading(True)
            self.command_queue.put((message, self.mode))

        def process_output_queue(self):
            while not self.output_queue.empty():
                output = self.output_queue.get()
                self.show_loading(False)
                self.append_output(output)
            
            self.root.after(100, self.process_output_queue)

        def toggle_markdown(self):
            self.markdown_mode = not self.markdown_mode
            current_text = self.output_text.get(1.0, tk.END)
            self.output_text.config(state=tk.NORMAL)
            self.output_text.delete(1.0, tk.END)
            
            if self.markdown_mode:
                # Convert markdown to HTML
                html_content = markdown.markdown(current_text, extensions=['fenced_code', 'tables'])
                # Clean up the HTML and apply basic styling
                soup = BeautifulSoup(html_content, 'html.parser')
                styled_text = self.style_markdown_text(soup.get_text())
                self.output_text.insert(tk.END, styled_text)
            else:
                self.output_text.insert(tk.END, current_text)
            
            self.output_text.config(state=tk.DISABLED)

        def style_markdown_text(self, text):
            """Apply basic styling to markdown text for Tkinter"""
            lines = text.split('\n')
            styled_lines = []
            for line in lines:
                if line.startswith('# '):
                    styled_lines.append(f"\n{line[2:].upper()}\n{'='*len(line)}\n")
                elif line.startswith('## '):
                    styled_lines.append(f"\n{line[3:].title()}\n{'-'*len(line)}\n")
                elif line.startswith('* '):
                    styled_lines.append(f"  • {line[2:]}")
                else:
                    styled_lines.append(line)
            return '\n'.join(styled_lines)

        def handle_url_click(self, event):
            """Handle clicking on URLs in the output text"""
            # Get the URL from the tag
            tags = self.output_text.tag_names("current")
            for tag in tags:
                if isinstance(tag, tuple) and tag[0] == "url":
                    url = tag[1]
                    webbrowser.open(url)
                    break

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