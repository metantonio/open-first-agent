import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
model = get_model_config()
# 1. Create Tools

@function_tool
async def create_file(filename: str, content: str = '') -> Dict[str, Any]:
    """Create a new file with optional content."""
    try:
        filepath = os.path.expanduser(filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        return {
            'success': True,
            'message': f"Successfully created file {filename}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create file: {str(e)}"
        }

@function_tool
async def copy_file(source: str, destination: str) -> Dict[str, Any]:
    """Copy a file from source to destination."""
    try:
        source_path = os.path.expanduser(source)
        dest_path = os.path.expanduser(destination)
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        if os.path.isdir(source_path):
            shutil.copytree(source_path, dest_path)
        else:
            shutil.copy2(source_path, dest_path)
        
        return {
            'success': True,
            'message': f"Successfully copied {source} to {destination}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to copy: {str(e)}"
        }

@function_tool
async def delete_file(target: str) -> Dict[str, Any]:
    """Delete a file or directory."""
    try:
        target_path = os.path.expanduser(target)
        
        if os.path.isdir(target_path):
            shutil.rmtree(target_path)
        else:
            os.remove(target_path)
        
        return {
            'success': True,
            'message': f"Successfully deleted {target}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to delete: {str(e)}"
        }

@function_tool
async def list_contents(path: str = '.') -> Dict[str, Any]:
    """List contents of a directory."""
    try:
        target_path = os.path.expanduser(path)
        contents = os.listdir(target_path)
        
        files = []
        directories = []
        
        for item in contents:
            full_path = os.path.join(target_path, item)
            if os.path.isdir(full_path):
                directories.append(item + '/')
            else:
                files.append(item)
        
        return {
            'success': True,
            'directories': sorted(directories),
            'files': sorted(files)
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to list contents: {str(e)}"
        }

@function_tool
async def find_files(pattern: str, path: str = '.') -> Dict[str, Any]:
    """Find files matching a pattern."""
    try:
        import fnmatch
        
        matches = []
        for root, dirnames, filenames in os.walk(os.path.expanduser(path)):
            for filename in fnmatch.filter(filenames, pattern):
                matches.append(os.path.join(root, filename))
        
        return {
            'success': True,
            'matches': matches
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to find files: {str(e)}"
        }

@function_tool
async def execute_command(command: str, working_dir: Optional[str] = None) -> Dict[str, Any]:
    """Execute a shell command."""
    try:
        if working_dir:
            os.chdir(working_dir)
            
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return {
                'success': True,
                'output': stdout.decode()
            }
        else:
            return {
                'success': False,
                'error': stderr.decode()
            }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to execute command: {str(e)}"
        }

@function_tool
async def ssh_connect(hostname: str, key_path: Optional[str] = None, username: Optional[str] = None) -> Dict[str, Any]:
    """Establish SSH connection."""
    try:
        import paramiko
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_params = {'hostname': hostname}
        
        if username:
            connect_params['username'] = username
        
        if key_path:
            key_path = os.path.expanduser(key_path)
            try:
                key = paramiko.RSAKey.from_private_key_file(key_path)
                connect_params['pkey'] = key
            except paramiko.ssh_exception.PasswordRequiredException:
                return {
                    'success': False,
                    'error': "Key file is encrypted. Please provide the key password."
                }
        
        client.connect(**connect_params)
        
        return {
            'success': True,
            'message': f"Successfully connected to {hostname}",
            'client': client
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to establish SSH connection: {str(e)}"
        }

# 2. Create Single-Responsibility Agents

# File Operation Agents
file_creator = Agent(
    name="File Creator",
    instructions="""You are responsible for ONLY creating files.
    Your single responsibility is to:
    - Create new files with proper content
    - Ensure parent directories exist
    - Handle file creation errors""",
    model=model,
    tools=[create_file]
)

file_copier = Agent(
    name="File Copier",
    instructions="""You are responsible for ONLY copying files.
    Your single responsibility is to:
    - Copy files and directories
    - Preserve file attributes
    - Handle copy errors""",
    model=model,
    tools=[copy_file]
)

file_deleter = Agent(
    name="File Deleter",
    instructions="""You are responsible for ONLY deleting files.
    Your single responsibility is to:
    - Delete files and directories
    - Handle deletion errors
    - Verify successful deletion""",
    model=model,
    tools=[delete_file]
)

directory_lister = Agent(
    name="Directory Lister",
    instructions="""You are responsible for ONLY listing directory contents.
    Your single responsibility is to:
    - List files and directories
    - Sort contents appropriately
    - Distinguish files from directories""",
    model=model,
    tools=[list_contents]
)

file_finder = Agent(
    name="File Finder",
    instructions="""You are responsible for ONLY finding files.
    Your single responsibility is to:
    - Find files matching patterns
    - Search recursively
    - Handle search errors""",
    model=model,
    tools=[find_files]
)

# Command Execution Agents
command_executor = Agent(
    name="Command Executor",
    instructions="""You are responsible for ONLY executing commands.
    Your single responsibility is to:
    - Execute shell commands
    - Handle command output
    - Manage working directory""",
    model=model,
    tools=[execute_command]
)

ssh_manager = Agent(
    name="SSH Manager",
    instructions="""You are responsible for ONLY managing SSH connections.
    Your single responsibility is to:
    - Establish SSH connections
    - Handle authentication
    - Manage connection state""",
    model=model,
    tools=[ssh_connect]
)

# 3. Create Main Orchestrator Agent

terminal_orchestrator = Agent(
    name="Terminal Orchestrator",
    instructions="""You are the main orchestrator for terminal operations. Your responsibilities include:
    1. Task Analysis:
       - Understand user requests
       - Determine required operations
       - Select appropriate agents
    
    2. Workflow Management:
       - Coordinate between agents
       - Ensure proper operation sequence
       - Handle dependencies
    
    3. Error Handling:
       - Monitor operation results
       - Handle and report errors
       - Provide clear feedback
    
    4. Security:
       - Validate operations
       - Handle sensitive data
       - Ensure secure execution
    
    5. History Management:
       - Track operations
       - Maintain execution history
       - Provide operation status""",
    model=model,
    tools=[
        create_file,
        copy_file,
        delete_file,
        list_contents,
        find_files,
        execute_command,
        ssh_connect
    ],
    handoffs=[
        file_creator,
        file_copier,
        file_deleter,
        directory_lister,
        file_finder,
        command_executor,
        ssh_manager
    ]
)

# 4. Main workflow function

def run_workflow(request: str) -> str:
    """Run the terminal workflow with the orchestrator as the main controller."""
    logger.info(f"Starting terminal workflow for request: {request}")
    
    try:
        # Parse the request to identify the operation type
        operation = parse_request(request)
        logger.info(f"Parsed operation: {operation}")
        
        # Execute the operation based on type
        if operation['type'] == 'create_file':
            directory = Path(operation.get('directory', '.'))
            path = directory / operation['path']
            content = operation.get('content', '')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return f"Successfully created file at {path}"
            
        elif operation['type'] == 'copy_file':
            directory = Path(operation.get('directory', '.'))
            source = directory / operation['source']
            dest = directory / operation['destination']
            
            logger.info(f"Copying from {source} to {dest}")
            
            try:
                if not source.exists():
                    return f"Error: Source file {source} does not exist"
                if not source.is_file():
                    return f"Error: Source {source} is not a file"
                
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(dest))
                return f"Successfully copied {source} to {dest}"
            except Exception as e:
                logger.error(f"Copy failed: {str(e)}")
                return f"Error copying file: {str(e)}"
            
        elif operation['type'] == 'find_files':
            path = Path(operation['path'])
            pattern = operation['pattern']
            files = list(path.glob(pattern))
            return "\n".join(str(f.name) for f in files)
            
        elif operation['type'] == 'delete_file':
            directory = Path(operation.get('directory', '.'))
            path = directory / operation['path']
            if not path.exists():
                return f"Error: File {path} does not exist"
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            return f"Successfully deleted {path}"
            
        elif operation['type'] == 'list_contents':
            path = Path(operation['path'])
            if not path.exists():
                return f"Error: Directory {path} does not exist"
            if not path.is_dir():
                return f"Error: {path} is not a directory"
            contents = []
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    contents.append(f"{item.name}/")
                else:
                    contents.append(item.name)
            return "\n".join(contents)
            
        elif operation['type'] == 'execute_command':
            command = operation.get('command', '')
            if not command:
                return "Error: No command provided"
            
            try:
                process = asyncio.get_event_loop().run_until_complete(
                    execute_command(command)
                )
                if process['success']:
                    return process['output'].strip()
                else:
                    return f"Error executing command: {process['error']}"
            except Exception as e:
                return f"Error: Command not found or failed to execute - {str(e)}"
            
        else:
            # For unknown operations, use the orchestrator
            try:
                response = Runner.run_sync(
                    terminal_orchestrator,
                    request
                )
                
                if not response or not response.final_output:
                    return "No response received"
                    
                return response.final_output
            except Exception as e:
                logger.error(f"Orchestrator error: {str(e)}")
                return f"Error: {str(e)}"
            
    except Exception as e:
        logger.error(f"Error in workflow execution: {str(e)}")
        return f"Error executing workflow: {str(e)}"

def parse_request(request: str) -> dict:
    """Parse the request to identify the operation type and parameters."""
    request_lower = request.lower()
    
    if "create" in request_lower and "file" in request_lower:
        path = extract_path(request)
        content = extract_content(request)
        directory = extract_directory(request)
        return {
            "type": "create_file",
            "path": path,
            "content": content,
            "directory": directory
        }
        
    elif "copy" in request_lower:
        source = extract_source_path(request)
        dest = extract_dest_path(request)
        directory = extract_directory(request)
        return {
            "type": "copy_file",
            "source": source,
            "destination": dest,
            "directory": directory
        }
        
    elif ("show" in request_lower or "list" in request_lower) and ("content" in request_lower or "files" in request_lower or "folders" in request_lower):
        path = extract_directory(request)
        return {"type": "list_contents", "path": path}
        
    elif "find" in request_lower and "file" in request_lower:
        path = extract_directory(request)
        pattern = extract_pattern(request)
        return {"type": "find_files", "path": path, "pattern": pattern}
        
    elif "delete" in request_lower and "file" in request_lower:
        path = extract_path(request)
        directory = extract_directory(request)
        return {
            "type": "delete_file",
            "path": path,
            "directory": directory
        }
        
    elif "execute" in request_lower and "command" in request_lower:
        command = extract_command(request)
        return {"type": "execute_command", "command": command}
        
    return {"type": "unknown"}

def extract_path(request: str) -> str:
    """Extract file path from request."""
    import re
    # Try to match 'at path' pattern
    path_match = re.search(r'at\s+([^\s]+)', request)
    if path_match:
        return path_match.group(1)
    # Try to match 'file path' pattern
    path_match = re.search(r'file\s+([^\s]+)', request)
    if path_match:
        return path_match.group(1)
    return ""

def extract_content(request: str) -> str:
    """Extract content to write from request."""
    import re
    # Try to match content between quotes with exact case
    content_match = re.search(r"content\s*['\"]([^'\"]+)['\"]", request)
    if content_match:
        return content_match.group(1)
    content_match = re.search(r"write\s*['\"]([^'\"]+)['\"]", request)
    if content_match:
        return content_match.group(1)
    return ""

def extract_source_path(request: str) -> str:
    """Extract source path from copy request."""
    import re
    # Try to match 'copy file X to Y' pattern
    source_match = re.search(r'copy\s+(?:the\s+)?(?:file\s+)?([^\s]+)\s+to', request, re.IGNORECASE)
    if source_match:
        return source_match.group(1)
    return ""

def extract_dest_path(request: str) -> str:
    """Extract destination path from copy request."""
    import re
    # Try to match 'to create X' pattern
    dest_match = re.search(r'to\s+(?:create\s+)?([^\s]+)(?:\s|$)', request, re.IGNORECASE)
    if dest_match:
        return dest_match.group(1)
    return ""

def extract_directory(request: str) -> str:
    """Extract directory path from request."""
    import re
    # Try to match 'in directory' pattern
    dir_match = re.search(r'in\s+(?:the\s+)?(?:directory\s+)?([^\s]+)', request)
    if dir_match:
        return dir_match.group(1)
    # Try to match 'in path' pattern
    dir_match = re.search(r'in\s+([^\s]+)', request)
    if dir_match:
        return dir_match.group(1)
    return "."

def extract_pattern(request: str) -> str:
    """Extract search pattern from request."""
    import re
    # Try to match 'pattern X' format
    pattern_match = re.search(r'pattern\s+([^\s]+)', request)
    if pattern_match:
        return pattern_match.group(1)
    # Try to match 'match X' format
    pattern_match = re.search(r'match\s+([^\s]+)', request)
    if pattern_match:
        return pattern_match.group(1)
    return "*"

def extract_command(request: str) -> str:
    """Extract command to execute from request."""
    import re
    command_match = re.search(r'command:\s*(.+?)(?:\s*$|\s+with\s+|$)', request)
    if command_match:
        return command_match.group(1).strip()
    return ""

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "Create a new directory called test and copy a file into it"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 