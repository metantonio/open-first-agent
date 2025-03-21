import os
import logging
import sys
import paramiko
import asyncio
import platform
from datetime import datetime
from typing import Optional

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
logger.setLevel(logging.INFO)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)

class TerminalState:
    def __init__(self):
        self.current_directory: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
        self.history: list = []
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.ssh_info: Optional[dict] = None
        self.prompt: str = "$ "
        os.makedirs(self.current_directory, exist_ok=True)

    def is_ssh_connected(self) -> bool:
        return self.ssh_client is not None and self.ssh_client.get_transport() is not None and self.ssh_client.get_transport().is_active()

    def update_prompt(self):
        if self.is_ssh_connected():
            self.prompt = f"{self.ssh_info['username']}@{self.ssh_info['hostname']}:{self.current_directory}$ "
        else:
            self.prompt = f"local:{self.current_directory}$ "

    async def connect_ssh(self, hostname: str, username: str, password: str = None, key_path: str = None, key_password: str = None) -> dict:
        """
        Connect to SSH with enhanced error handling and support for encrypted keys.
        
        Args:
            hostname (str): The remote host to connect to
            username (str): The username for authentication
            password (str, optional): Password for password authentication
            key_path (str, optional): Path to the private key file
            key_password (str, optional): Password for encrypted private key
            
        Returns:
            dict: Connection result with status and details
        """
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connection_info = {
                'status': 'failed',
                'message': '',
                'details': {}
            }
            
            if key_path:
                try:
                    # Try to load the private key
                    if key_password:
                        private_key = paramiko.RSAKey.from_private_key_file(key_path, password=key_password)
                    else:
                        try:
                            private_key = paramiko.RSAKey.from_private_key_file(key_path)
                        except paramiko.ssh_exception.PasswordRequiredException:
                            connection_info['status'] = 'error'
                            connection_info['message'] = 'Private key is encrypted. Please provide the key password.'
                            connection_info['details'] = {
                                'error_type': 'encrypted_key',
                                'requires': 'key_password'
                            }
                            return connection_info
                            
                    # Connect using the private key
                    self.ssh_client.connect(
                        hostname,
                        username=username,
                        pkey=private_key
                    )
                except Exception as key_error:
                    logger.error(f"Error loading private key: {str(key_error)}")
                    connection_info['status'] = 'error'
                    connection_info['message'] = f'Failed to load private key: {str(key_error)}'
                    connection_info['details'] = {
                        'error_type': 'key_load_failed',
                        'error': str(key_error)
                    }
                    return connection_info
            else:
                if not password:
                    connection_info['status'] = 'error'
                    connection_info['message'] = 'Either password or key file is required'
                    connection_info['details'] = {
                        'error_type': 'no_credentials'
                    }
                    return connection_info
                    
                self.ssh_client.connect(
                    hostname,
                    username=username,
                    password=password
                )
            
            self.ssh_info = {
                'hostname': hostname,
                'username': username,
                'connected_at': datetime.now().isoformat(),
                'using_key': key_path is not None
            }
            self.update_prompt()
            
            connection_info['status'] = 'success'
            connection_info['message'] = 'Successfully connected to SSH'
            connection_info['details'] = self.ssh_info
            return connection_info
            
        except paramiko.AuthenticationException:
            connection_info = {
                'status': 'error',
                'message': 'Authentication failed. Please check your credentials.',
                'details': {
                    'error_type': 'authentication_failed'
                }
            }
            logger.error("SSH authentication failed")
            return connection_info
            
        except paramiko.SSHException as ssh_error:
            connection_info = {
                'status': 'error',
                'message': f'SSH error occurred: {str(ssh_error)}',
                'details': {
                    'error_type': 'ssh_error',
                    'error': str(ssh_error)
                }
            }
            logger.error(f"SSH error: {str(ssh_error)}")
            return connection_info
            
        except Exception as e:
            connection_info = {
                'status': 'error',
                'message': f'Unexpected error: {str(e)}',
                'details': {
                    'error_type': 'unexpected_error',
                    'error': str(e)
                }
            }
            logger.error(f"Unexpected error during SSH connection: {str(e)}")
            return connection_info

    def disconnect_ssh(self) -> dict:
        """
        Disconnect from SSH with status reporting.
        
        Returns:
            dict: Disconnection result with status and details
        """
        try:
            if self.ssh_client:
                self.ssh_client.close()
                self.ssh_client = None
                self.ssh_info = None
                self.update_prompt()
                return {
                    'status': 'success',
                    'message': 'Successfully disconnected from SSH',
                    'details': {}
                }
            return {
                'status': 'info',
                'message': 'No active SSH connection to disconnect',
                'details': {}
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error during SSH disconnection: {str(e)}',
                'details': {
                    'error_type': 'disconnect_error',
                    'error': str(e)
                }
            }

class TerminalManager:
    def __init__(self):
        self.terminal = TerminalState()

    def get_background_command(self, command: str) -> str:
        """Get the appropriate background command format for the current OS."""
        os_name = platform.system().lower()
        
        if os_name == "windows":
            # Windows: use 'start /B' for background processes
            return f"start /B {command} > NUL 2>&1"
        else:
            # Unix-like systems (Linux, macOS): use nohup
            return f"nohup {command} > /dev/null 2>&1 &"

    def get_shell_info(self) -> tuple[bool, str]:
        """Get shell information based on the OS."""
        os_name = platform.system().lower()
        
        if os_name == "windows":
            return True, "cmd.exe"  # shell=True and use cmd.exe
        else:
            return True, "/bin/sh"  # shell=True and use sh

    def get_working_directory(self, command: str) -> str:
        """Determine the appropriate working directory for a command."""
        if self.terminal.current_directory is None:
            # Initialize with output directory if not set
            self.terminal.current_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
            os.makedirs(self.terminal.current_directory, exist_ok=True)
        
        return self.terminal.current_directory

    async def execute_command(self, command: str, is_background: bool = False, working_dir: str = None) -> str:
        """Execute a shell command and return the output."""
        try:
            use_shell, shell_exe = self.get_shell_info()
            
            # Handle cd command specially
            if command.strip().startswith('cd '):
                new_dir = command.strip()[3:].strip()
                if new_dir:
                    if os.path.isabs(new_dir):
                        target_dir = new_dir
                    else:
                        target_dir = os.path.abspath(os.path.join(self.terminal.current_directory, new_dir))
                    
                    if os.path.exists(target_dir) and os.path.isdir(target_dir):
                        self.terminal.current_directory = target_dir
                        return f"Changed directory to: {self.terminal.current_directory}"
                    else:
                        return f"Directory not found: {new_dir}"
            
            # Use terminal.current_directory if working_dir not specified
            cwd = working_dir if working_dir else self.terminal.current_directory
            
            if is_background:
                # Format command for background execution based on OS
                bg_command = self.get_background_command(command)
                process = await asyncio.create_subprocess_shell(
                    bg_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=use_shell,
                    executable=shell_exe,
                    cwd=cwd
                )
                return f"Command started in background in directory: {cwd}"
            else:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=use_shell,
                    executable=shell_exe,
                    cwd=cwd
                )
                stdout, stderr = await process.communicate()
                
                # Add command to terminal history
                self.terminal.history.append({
                    'command': command,
                    'output': stdout.decode() if process.returncode == 0 else stderr.decode(),
                    'success': process.returncode == 0
                })
                
                if process.returncode == 0:
                    return f"Working directory: {cwd}\nOutput:\n{stdout.decode()}"
                else:
                    return f"Error in directory {cwd}:\n{stderr.decode()}"
        except Exception as e:
            return f"Failed to execute command: {str(e)}"

    def create_terminal_content(self) -> str:
        """Create the terminal interface content."""
        return f"""```terminal
╔══════════════════════════════════════════════════════════════════════════════
║ 🖥️  Terminal Interface
║══════════════════════════════════════════════════════════════════════════════
║ Current Directory: {self.terminal.current_directory}
║
║ Available Commands:
║ - Type 'clear' to clear the terminal
║ - Type 'cd <directory>' to change directory
║ - Type 'ssh connect' to establish SSH connection
║ - Type 'ssh disconnect' to close SSH connection
║ - Type 'exit' to return to chat mode
║══════════════════════════════════════════════════════════════════════════════
"""

    def get_history_content(self, limit: int = 5) -> str:
        """Get formatted history content."""
        if not self.terminal.history:
            return ""
            
        history = "\n".join([
            "Recent Commands:",
            "══════════════",
            *[f"$ {entry['command']}\n{entry['output'] if entry['output'] else '(no output)'}" 
              for entry in self.terminal.history[-limit:]],
            "══════════════"
        ])
        return f"```terminal\n{history}\n```"

# Create a global instance of TerminalManager
terminal_manager = TerminalManager() 