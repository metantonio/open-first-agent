import os
import re
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from universal_orchestrator import orchestrator
from terminal_manager import terminal_manager
from datetime import datetime
from typing import Dict, List
import asyncio
import uuid
from pathlib import Path
from dotenv import load_dotenv
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('agent.log')
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.addHandler(logging.FileHandler('agent.log'))
logger.info("Started server")

app = FastAPI()

# Serve static files from a 'static' directory
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Verify and export critical environment variables
if not os.getenv('OPENAI_API_KEY'):
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables. Please check your .env file.")

# Ensure OPENAI_API_KEY is explicitly set in the environment
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
os.environ['OPENAI_AGENTS_DISABLE_TRACING'] = os.getenv('OPENAI_AGENTS_DISABLE_TRACING')

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket

    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

    async def send_message(self, message: dict, connection_id: str):
        if connection_id in self.active_connections:
            await self.active_connections[connection_id].send_json(message)

manager = ConnectionManager()

# Add this to server.py after the ConnectionManager class
class LogHandler(logging.Handler):
    def __init__(self, manager: ConnectionManager):
        super().__init__()
        self.manager = manager
    
    def emit(self, record):
        log_entry = self.format(record)
        asyncio.run_coroutine_threadsafe(
            self.broadcast_log(log_entry),
            asyncio.get_event_loop()
        )
    
    async def broadcast_log(self, message):
        for connection_id in manager.active_connections:
            await manager.send_message({
                "type": "server_log",
                "message": message
            }, connection_id)

# Replace the existing logging configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add the console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Add the file handler
file_handler = logging.FileHandler('agent.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Add the WebSocket log handler
ws_log_handler = LogHandler(manager)
ws_log_handler.setFormatter(formatter)
logger.addHandler(ws_log_handler)

def process_code_blocks(content: str) -> tuple[str, list[dict]]:
    """Process content to find code blocks with run tags"""
    command_blocks = []
    pattern = r"```bash\s*{(run(?::\w+)?(?:_\d+)?)}(.*?)```"
    
    def create_command_block(code: str, tag: str) -> dict:
        code = code.strip()
        code = re.sub(r'transfer_to_\w+_agent\((.*?)\)', r'\1', code)
        code = re.sub(r'^\s*{\s*"[^"]+"\s*:\s*"([^"]+)"\s*}\s*$', r'\1', code)
        is_background = ":background" in tag
        working_dir = terminal_manager.get_working_directory(code)
        return {
            'code': code,
            'is_background': is_background,
            'working_dir': working_dir,
            'action_id': "run"
        }
    
    def replacement(match):
        tag, code = match.groups()
        command_block = create_command_block(code, tag)
        command_blocks.append(command_block)
        return ""
    
    content_without_commands = re.sub(pattern, replacement, content, flags=re.DOTALL)
    return content_without_commands, command_blocks

async def update_terminal_display(connection_id: str):
    """Update the terminal display for a specific connection"""
    terminal_content = terminal_manager.create_terminal_content()
    history_content = terminal_manager.get_history_content()
    
    await manager.send_message({
        "type": "terminal_update",
        "content": terminal_content,
        "history": history_content
    }, connection_id)

@app.get("/", response_class=HTMLResponse)
async def get_ui():
    """Serve the main HTML interface"""
    
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Assistant</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/github-dark.min.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
        <link href="/static/style.css" rel="stylesheet">
    </head>
    <body>
        <div id="app">
            <div class="sidebar">
                <div class="logo">AI Assistant</div>
                <div class="menu">
                    <button @click="toggleMode" class="menu-button">
                        {{ mode === 'chat' ? 'Terminal Mode' : 'Chat Mode' }}
                    </button>
                    <button @click="clearChat" class="menu-button">Clear</button>
                    <button @click="toggleBrowserAgent" class="menu-button" 
                            :class="{ 'active': browserEnabled }">
                        {{ browserEnabled ? 'Disable Browser Agent' : 'Enable Browser Agent' }}
                    </button>
                    <button @click="toggleServerLogs" class="menu-button">
                        {{ showServerLogs ? 'Hide Server Logs' : 'Show Server Logs' }}
                    </button>
                </div>
                <div class="status">
                    <div class="status-item">
                        <span class="status-label">SSH:</span>
                        <span class="status-value" :class="{ 'connected': sshConnected }">
                            {{ sshConnected ? 'Connected' : 'Disconnected' }}
                        </span>
                    </div>
                    <div class="status-item">
                        <span class="status-label">Mode:</span>
                        <span class="status-value">{{ mode.toUpperCase() }}</span>
                    </div>
                </div>
            </div>
            
            <div class="main-content">
                <div v-if="mode === 'chat'" class="chat-container">
                    <div class="message-list" ref="messageList">
                        <div v-for="(msg, index) in messages" :key="index" class="message" :class="msg.type">
                            <div class="message-content" v-html="msg.content"></div>
                            <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
                        </div>

                        <div v-if="isLoading" class="message assistant loading-indicator">
                            <div class="message-content"></div>
                            <div class="typing-animation">
                                <div class="dot"></div>
                                <div class="dot"></div>
                                <div class="dot"></div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="input-area">
                        <textarea v-model="inputMessage" @keydown.enter.exact.prevent="sendMessage" 
                                  placeholder="Type your message here..."></textarea>
                        <button @click="sendMessage" class="send-button">Send</button>
                    </div>
                </div>

                <div v-else class="terminal-container">
                    <div class="terminal-header">
                        <div class="terminal-title">Terminal</div>
                        <div class="terminal-status">
                            <span class="status-dot" :class="{ 'active': sshConnected }"></span>
                            <span>{{ sshConnected ? sshInfo : 'Local Terminal' }}</span>
                        </div>
                    </div>
                    
                    <div class="terminal-output" ref="terminalOutput">
                        <div v-for="(line, index) in terminalLines" :key="index" class="terminal-line">
                            <span class="prompt">{{ line.prompt }}</span>
                            <span class="command">{{ line.command }}</span>
                            <div class="output" v-html="line.output"></div>
                        </div>
                        
                        <div v-if="isLoading" class="terminal-line processing">
                            <span class="prompt">{{ currentPrompt }}</span>
                            <span class="command">Processing...</span>
                        </div>
                    </div>
                    
                    <div class="terminal-input">
                        <span class="prompt">{{ currentPrompt }}</span>
                        <input v-model="terminalCommand" @keydown.enter="executeTerminalCommand" 
                            type="text" class="command-input">
                    </div>
                </div>

                <div v-if="showServerLogs" class="log-panel">
                    <div class="log-header">
                        <h3>Server Logs</h3>
                        <button @click="clearServerLogs" class="clear-button">Clear</button>
                    </div>
                    <div class="log-content">
                        <div v-for="(log, index) in serverLogs" :key="index" class="log-entry">
                            {{ log }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/vue@3.2.31/dist/vue.global.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/ansi_up@5.1.0/ansi_up.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked@4.2.12/marked.min.js"></script>
        
        <script src="/static/app.js"></script>
    </body>
    </html>
    """

@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    await manager.connect(websocket, connection_id)
    try:
        while True:
            data = await websocket.receive_json()
            await handle_client_message(data, connection_id)
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(connection_id)

async def handle_client_message(data: dict, connection_id: str):
    """Handle incoming messages from the client"""
    message_type = data.get("type")
    
    if message_type == "chat_message":
        await handle_chat_message(data["content"], connection_id)
    elif message_type == "terminal_command":
        await handle_terminal_command(data["command"], connection_id)
    elif message_type == "action":
        await handle_action(data["action"], connection_id)
    elif message_type == "toggle_browser":  # Add this new handler
        orchestrator.browser_enabled = data["enabled"]
        await manager.send_message({
            "type": "browser_status",
            "enabled": orchestrator.browser_enabled
        }, connection_id)

async def handle_chat_message(message: str, connection_id: str):
    """Handle chat messages from the user"""
    if message.startswith('!'):
        command = message[1:].strip()
        result = await terminal_manager.execute_command(command)
        await update_terminal_display(connection_id)
        await manager.send_message({
            "type": "command_output",
            "output": result
        }, connection_id)
        return
    
    # Process normal chat message
    response = await orchestrator.process_request(message)
    
    # Send the raw response to the frontend - let JavaScript handle markdown processing
    content, command_blocks = process_code_blocks(response)
    
    if command_blocks:
        await manager.send_message({
            "type": "chat_message",
            "content": content,
            "sender": "assistant"
        }, connection_id)
        
        for i, cmd_block in enumerate(command_blocks):
            await manager.send_message({
                "type": "command_block",
                "command": cmd_block['code'],
                "working_dir": os.path.basename(cmd_block['working_dir']),
                "index": i + 1
            }, connection_id)
    else:
        await manager.send_message({
            "type": "chat_message",
            "content": response,  # Send raw response
            "sender": "assistant"
        }, connection_id)

async def handle_terminal_command(command: str, connection_id: str):
    """Handle terminal commands from the user"""
    if command.lower() == "exit":
        await manager.send_message({
            "type": "mode_change",
            "mode": "chat"
        }, connection_id)
        return
    
    if command.lower() == "clear":
        terminal_manager.terminal.history = []
        await update_terminal_display(connection_id)
        return
    
    if command.lower().startswith("ssh"):
        await handle_ssh_command(command, connection_id)
        return
    
    result = await terminal_manager.execute_command(command)
    terminal_manager.terminal.update_prompt()
    
    await manager.send_message({
        "type": "terminal_output",
        "command": command,
        "output": result,
        "prompt": terminal_manager.terminal.prompt or "$ "  # Fallback to basic prompt
    }, connection_id)

async def handle_ssh_command(command: str, connection_id: str):
    """Handle SSH commands with visual feedback"""
    if command.lower() == "ssh help":
        help_text = terminal_manager.get_ssh_help()
        await manager.send_message({
            "type": "terminal_output",
            "command": command,
            "output": help_text,
            "prompt": terminal_manager.terminal.prompt
        }, connection_id)
        return
    
    if command.lower() == "ssh disconnect":
        result = terminal_manager.terminal.disconnect_ssh()
        await manager.send_message({
            "type": "ssh_status",
            "status": result['status'],
            "message": result['message'],
            "connected": False
        }, connection_id)
        return
    
    if command.lower().startswith("ssh connect"):
        params = parse_ssh_args(command)
        if 'hostname' in params and 'username' in params:
            result = await terminal_manager.terminal.connect_ssh(
                hostname=params['hostname'],
                username=params['username'],
                password=params.get('password'),
                key_path=params.get('key_path'),
                key_password=params.get('key_password')
            )
            
            if result['status'] == 'error' and result.get('details', {}).get('error_type') == 'encrypted_key':
                await manager.send_message({
                    "type": "ssh_auth",
                    "hostname": params['hostname'],
                    "username": params['username'],
                    "key_path": params.get('key_path')
                }, connection_id)
                return
            
            await manager.send_message({
                "type": "ssh_status",
                "status": result['status'],
                "message": result['message'],
                "connected": result['status'] == 'success',
                "hostname": params['hostname'],
                "username": params['username']
            }, connection_id)

def parse_ssh_args(command: str) -> dict:
    """Parse SSH command arguments"""
    args = command.split()
    params = {}
    i = 2  # Skip 'ssh connect'
    
    while i < len(args):
        if args[i] in ['-h', '--host'] and i + 1 < len(args):
            params['hostname'] = args[i + 1]
            i += 2
        elif args[i] in ['-u', '--user'] and i + 1 < len(args):
            params['username'] = args[i + 1]
            i += 2
        elif args[i] in ['-p', '--password'] and i + 1 < len(args):
            params['password'] = args[i + 1]
            i += 2
        elif args[i] in ['-k', '--key'] and i + 1 < len(args):
            params['key_path'] = args[i + 1]
            i += 2
        else:
            i += 1
    return params

async def handle_action(action: dict, connection_id: str):
    """Handle action buttons (like command execution)"""
    if action['id'] == "run":
        command = action['command']
        is_background = action.get('is_background', False)
        working_dir = action.get('working_dir')
        
        await manager.send_message({
            "type": "command_start",
            "command": command,
            "working_dir": working_dir
        }, connection_id)
        
        result = await terminal_manager.execute_command(command, is_background, working_dir)
        await update_terminal_display(connection_id)
        
        await manager.send_message({
            "type": "command_output",
            "command": command,
            "output": result
        }, connection_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)