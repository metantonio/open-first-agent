import os
import asyncio
import logging
import platform
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, function_tool, ModelSettings
from .config import get_model_config
import shutil
import fnmatch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
model = get_model_config()

# Detect operating system
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def normalize_path_for_os(path: str) -> str:
    """Normalize path for current operating system."""
    if IS_WINDOWS:
        # Convert forward slashes to backslashes for Windows
        return str(Path(path.replace('/', '\\')))
    else:
        # Convert backslashes to forward slashes for Unix-like systems
        return str(Path(path.replace('\\', '/')))

def join_paths_for_os(*paths: str) -> str:
    """Join paths in a way appropriate for the current OS."""
    # Use Path to handle the joining in an OS-appropriate way
    return str(Path(*paths))

def get_absolute_path(path: str, directory: Optional[str] = None) -> str:
    """Get absolute path, considering OS and optional directory context."""
    if directory:
        # If directory context is provided, join with the path
        full_path = join_paths_for_os(directory, path)
    else:
        full_path = path
        
    # Convert to absolute path
    return str(Path(full_path).absolute())

@function_tool
async def create_file(filename: str, content: str = '', directory: Optional[str] = None) -> Dict[str, Any]:
    """Create a new file with optional content.
    
    Args:
        filename (str): Path to the file to create
        content (str, optional): Content to write to the file. Defaults to empty string.
        directory (str, optional): Directory context for the file. Defaults to None.
    """
    try:
        # Normalize paths for current OS
        filename = normalize_path_for_os(filename)
        if directory:
            directory = normalize_path_for_os(directory)
            
        # Get absolute path
        filepath = get_absolute_path(filename, directory)
            
        # Ensure parent directory exists
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
            
        # Write the file using Path for better OS compatibility
        Path(filepath).write_text(content)
            
        return {
            'success': True,
            'message': f"Successfully created file {filename}",
            'path': filepath
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Failed to create file {filename}: {str(e)}"
        }

@function_tool
async def copy_file(source: str, destination: str, directory: Optional[str] = None) -> Dict[str, Any]:
    """Copy a file from source to destination."""
    try:
        # Normalize paths for current OS
        source = normalize_path_for_os(source)
        destination = normalize_path_for_os(destination)
        if directory:
            directory = normalize_path_for_os(directory)
            
        # Get absolute paths
        source_path = get_absolute_path(source, directory)
        dest_path = get_absolute_path(destination, directory)
        
        # Ensure source exists
        if not Path(source_path).exists():
            return {
                'success': False,
                'error': f"Source file {source} does not exist"
            }
            
        # Create destination directory if needed
        dest_dir = os.path.dirname(dest_path)
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
            
        # Perform the copy using Path
        if Path(source_path).is_dir():
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
async def delete_file(target: str, directory: Optional[str] = None) -> Dict[str, Any]:
    """Delete a file or directory."""
    try:
        # Normalize paths for current OS
        target = normalize_path_for_os(target)
        if directory:
            directory = normalize_path_for_os(directory)
            
        # Get absolute path
        target_path = get_absolute_path(target, directory)
        
        # Use Path for operations
        path_obj = Path(target_path)
        if path_obj.is_dir():
            shutil.rmtree(target_path)
        else:
            path_obj.unlink()
        
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
        # Normalize path for current OS
        path = normalize_path_for_os(path)
        
        # Get absolute path
        target_path = get_absolute_path(path)
        path_obj = Path(target_path)
        
        if not path_obj.exists():
            return {
                'success': False,
                'error': f"Directory {path} does not exist"
            }
            
        if not path_obj.is_dir():
            return {
                'success': False,
                'error': f"{path} is not a directory"
            }
            
        # Use Path for listing contents
        contents = list(path_obj.iterdir())
        
        files = []
        directories = []
        
        for item in contents:
            try:
                if item.is_dir():
                    directories.append(f"{item.name}/")
                else:
                    files.append(item.name)  # Removed trailing slash for files
            except OSError:
                continue
        
        output = []
        if files:
            output.append("Files:")
            for f in sorted(files):
                output.append(f"- {f}")  # Files without trailing slash
        if directories:
            if files:
                output.append("")
            output.append("Directories:")
            for d in sorted(directories):
                output.append(f"- {d}")  # Directories with trailing slash
                
        return {
            'success': True,
            'output': "\n".join(output),
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
        # Convert to absolute path if relative
        target_path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(target_path):
            return {
                'success': False,
                'error': f"Directory {path} does not exist"
            }
            
        if not os.path.isdir(target_path):
            return {
                'success': False,
                'error': f"{path} is not a directory"
            }
            
        matches = []
        for root, dirnames, filenames in os.walk(target_path):
            for filename in fnmatch.filter(filenames, pattern):
                # Get relative path from target directory
                rel_path = os.path.relpath(os.path.join(root, filename), target_path)
                matches.append(rel_path)
                
        output = ["Matching files:"]
        for match in sorted(matches):
            output.append(f"- {match}")
            
        return {
            'success': True,
            'output': "\n".join(output),
            'matches': sorted(matches)
        }
    except PermissionError:
        return {
            'success': False,
            'error': f"Permission denied when searching directory {path}"
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
    - Create new files with specified content
    - Handle file paths correctly
    - Return success/failure status
    
    You MUST:
    1. Extract the file path and content from the request
    2. Call the create_file function with the exact parameters:
       - path: The file path to create
       - content: The content to write (empty string if not specified)
       - directory: The directory context (if provided)
    3. Return the tool's response directly
    
    Example commands and responses:
    Request: "Create file test.txt with content 'Hello World' in /path/to/dir"
    Action: create_file(path="test.txt", content="Hello World", directory="/path/to/dir")
    
    Request: "Make a new empty file called empty.txt"
    Action: create_file(path="empty.txt", content="", directory=None)
    
    Important:
    - Create parent directories if they don't exist
    - Handle both absolute and relative paths
    - Return clear error messages if operation fails
    - Do not modify content unless explicitly told to
    
    Path handling:
    - If path starts with /, treat as absolute
    - If path doesn't start with /, treat as relative to directory (if provided)
    - Use the exact path provided in the request
    
    Content handling:
    - Use exact content provided
    - Empty string for empty files
    - Preserve all whitespace and formatting""",
    model=model,
    tools=[create_file]
)

file_copier = Agent(
    name="File Copier",
    instructions="""You are responsible for ONLY copying files.
    Your single responsibility is to:
    - Copy files from source to destination
    - When given a directory context, resolve paths relative to that directory
    - Create destination parent directories if needed
    - Handle copy errors with clear messages
    
    You MUST:
    1. Extract source and destination paths from the request
    2. If a directory is specified, pass it as the directory parameter
    3. Call the copy_file tool with the exact parameters:
       - source: The source file path (relative or absolute)
       - destination: The destination file path (relative or absolute)
       - directory: The directory context (if provided)
    4. Return the tool's response directly
    
    Example commands and responses:
    Request: "Copy source.txt to dest.txt in directory /path/to/dir"
    Action: copy_file(source="source.txt", destination="dest.txt", directory="/path/to/dir")
    
    Request: "Copy /abs/path/source.txt to /abs/path/dest.txt"
    Action: copy_file(source="/abs/path/source.txt", destination="/abs/path/dest.txt")
    
    Important:
    - Do not modify paths unless explicitly told to
    - Create parent directories automatically
    - Return clear error messages if operation fails
    
    Path handling:
    - If directory context is provided, resolve relative paths against it
    - If path starts with /, treat as absolute
    - If path doesn't start with /, treat as relative""",
    model=model,
    tools=[copy_file]
)

file_deleter = Agent(
    name="File Deleter",
    instructions="""You are responsible for ONLY deleting files.
    Your single responsibility is to:
    - Delete specified files or directories
    - Handle file paths correctly
    - Return success/failure status
    
    You MUST:
    1. Extract the file path from the request
    2. Call delete_file with the exact parameters:
       - target: The file path to delete (extract from phrases like "at path", "file at", "delete file")
       - directory: The directory context (if provided)
    3. Return the tool's response directly
    
    Example commands and responses:
    Request: "Delete file test.txt in /path/to/dir"
    Action: delete_file(target="test.txt", directory="/path/to/dir")
    
    Request: "Delete the file at /absolute/path/to/file.txt"
    Action: delete_file(target="/absolute/path/to/file.txt")
    
    Request: "Please delete the file at path/to/file.txt"
    Action: delete_file(target="path/to/file.txt")
    
    Important:
    - Handle both absolute and relative paths
    - Return clear error messages if operation fails
    - Do not modify the path provided in the request
    - Execute the delete operation directly, don't just plan it
    
    Path handling:
    - If path starts with /, treat as absolute
    - If path doesn't start with /, treat as relative to directory (if provided)
    - Extract path from phrases like "at path", "file at", "delete file"
    - Use the exact path provided in the request""",
    model=model,
    tools=[delete_file]
)

directory_lister = Agent(
    name="Directory Lister",
    instructions="""You are responsible for ONLY listing directory contents.
    Your single responsibility is to:
    - List all files and directories in the specified path
    - Format output as a clear text list
    - Sort contents alphabetically
    - Distinguish files from directories with trailing '/'
    
    You MUST:
    1. Extract the directory path from the request
    2. Call the list_contents function with the exact path parameter
    3. Return the tool's response directly
    
    Example commands and responses:
    Request: "Show me a list of all files and folders in the directory /path/to/dir"
    Action: list_contents(path="/path/to/dir")
    
    Request: "List contents of directory /path/to/dir"
    Action: list_contents(path="/path/to/dir")
    
    Important:
    - Do not modify paths unless explicitly told to
    - Handle both absolute and relative paths
    - Return clear error messages if operation fails
    
    Path handling:
    - If path starts with /, treat as absolute
    - If path doesn't start with /, treat as relative
    - Use the exact path provided in the request""",
    model=model,
    tools=[list_contents]
)

file_finder = Agent(
    name="File Finder",
    instructions="""You are responsible for ONLY finding files.
    Your single responsibility is to:
    - Find files matching the given pattern
    - Search recursively in the specified directory
    - Return matches as a list
    - Handle search errors
    
    You MUST:
    1. Extract the search pattern and directory from the request
    2. Call the find_files function with the exact parameters:
       - pattern: The exact pattern to match
       - path: The directory to search in
    3. Return the tool's response directly
    
    Example commands and responses:
    Request: "Find files matching pattern test*.txt in /path/to/dir"
    Action: find_files(pattern="test*.txt", path="/path/to/dir")
    
    Request: "Please find all files that match the pattern *.py in /path/to/dir"
    Action: find_files(pattern="*.py", path="/path/to/dir")
    
    Important:
    - Do not modify patterns unless explicitly told to
    - Handle both absolute and relative paths
    - Return clear error messages if operation fails
    
    Path handling:
    - If path starts with /, treat as absolute
    - If path doesn't start with /, treat as relative
    - Use the exact path provided in the request
    
    Pattern handling:
    - Use the exact pattern provided
    - Do not modify wildcards or patterns
    - Common patterns: *.txt, test*.py, *.*, etc.""",
    model=model,
    tools=[find_files]
)

# Command Execution Agents
command_executor = Agent(
    name="Command Executor",
    instructions="""You are responsible for ONLY executing commands.
    Your single responsibility is to:
    - Execute the given shell command
    - Return command output or error message
    - Handle non-existent commands with clear error messages
    - Include 'command not found' in error messages for invalid commands
    
    Example commands:
    - "Execute command: ls -l"
    - "Execute command: nonexistentcmd" -> Should return "command not found"
    """,
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
    instructions="""You are the main orchestrator for local terminal operations. Your responsibilities include:
    1. Task Analysis:
       - Parse the user request to identify operation type
       - Break down complex requests into individual steps
       - Execute operations directly using available tools
       - Maintain operation sequence and dependencies
    
    2. Direct Tool Usage:
       - For file creation:
         Use create_file(filename="test.txt", content="Hello", directory="/path")
       
       - For file copying:
         Use copy_file(source="source.txt", destination="dest.txt", directory="/path")
         
       - For file deletion:
         Use delete_file(target="test.txt", directory="/path")
         
       - For directory listing:
         Use list_contents(path="/path")
         
       - For file finding:
         Use find_files(pattern="*.txt", path="/path")
         
       - For command execution:
         Use execute_command(command="ls -l", working_dir="/path")
    
    3. Directory Context:
       - Extract directory from "in directory" or "in path" phrases
       - Use "." if no directory specified
       - Create directories if needed using create_file
       - Pass directory context to all operations
       - For multi-step operations, use the same directory context throughout
    
    4. Multi-step Operations:
       - For operations requiring multiple steps:
         1. Extract directory context first and use it for all steps
         2. Create any required directories first
         3. Execute each operation in sequence
         4. Verify each step's success before proceeding
         5. If any step fails, stop and return error
         6. After all steps complete, verify final state
    
    5. Response Handling:
       - Return tool responses directly
       - Include error messages if operation fails
       - For multi-step operations, show final directory state

    Examples:
    1. Single file creation:
       Request: "Create file test.txt with content 'Hello' in /tmp"
       Action: create_file(filename="test.txt", content="Hello", directory="/tmp")
    
    2. File copy with context:
       Request: "Copy source.txt to dest.txt in directory /tmp"
       Action: copy_file(source="source.txt", destination="dest.txt", directory="/tmp")
    
    3. Complex workflow:
       Request: "In directory /tmp, create file1.txt with 'Test' and copy it to file2.txt"
       Actions:
       1. result = create_file(filename="file1.txt", content="Test", directory="/tmp")
          if not result['success']: return result
       2. result = copy_file(source="file1.txt", destination="file2.txt", directory="/tmp")
          if not result['success']: return result
       3. return list_contents(path="/tmp")

    Important:
    - Execute tools directly, don't just plan actions
    - Use exact paths and content as provided
    - Include directory context in every operation
    - For multi-step operations:
      * Extract all parameters first
      * Use consistent directory context
      * Execute operations in sequence
      * Verify each step's success
      * Show final directory state""",
    model=model,
    tools=[create_file, copy_file, delete_file, list_contents, find_files, execute_command]
)

# 4. Main workflow function

def run_workflow(request: str) -> str:
    """Run the terminal workflow with the orchestrator as the main controller."""
    logger.info(f"Starting terminal workflow for request: {request}")
    
    try:
        # Create a new event loop for the orchestrator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the orchestrator with the request
            response = Runner.run_sync(
                terminal_orchestrator,
                request,
                context={
                    "extract_path": extract_path,
                    "extract_content": extract_content,
                    "extract_directory": extract_directory,
                    "extract_pattern": extract_pattern,
                    "extract_command": extract_command,
                    "extract_source_path": extract_source_path,
                    "extract_dest_path": extract_dest_path
                }
            )
        finally:
            loop.close()
        
        if not response:
            return "No response received from orchestrator"
            
        # Get the final output from the response
        final_output = response.final_output
        
        # If the response is a string, check if it's a command structure
        if isinstance(final_output, str):
            # If it looks like a command structure, execute it
            if "<command>" in final_output and "</command>" in final_output:
                # Parse the command structure and execute it
                if "<transfer_to_file_creator>" in final_output:
                    import json
                    try:
                        # Extract the JSON between the tags
                        start = final_output.find("<transfer_to_file_creator>") + len("<transfer_to_file_creator>")
                        end = final_output.find("</transfer_to_file_creator>")
                        json_str = final_output[start:end].strip()
                        params = json.loads(json_str)
                        
                        # Execute create_file with the extracted parameters
                        result = asyncio.run(create_file(**params))
                        return str(result)
                    except Exception as e:
                        return f"Error executing file creation: {str(e)}"
                        
                # Add similar handlers for other command types
                return "Unhandled command type"
            else:
                return final_output.strip()
                
        # Handle dictionary responses
        elif isinstance(final_output, dict):
            if not final_output.get('success', True):
                error_msg = final_output.get('error', 'Unknown error occurred')
                return f"Error: {error_msg}"
                
            if 'output' in final_output:
                return final_output['output']
            elif 'message' in final_output:
                return final_output['message']
            elif 'matches' in final_output:
                return "\n".join([
                    "Matching files:",
                    *[f"- {match}" for match in sorted(final_output['matches'])]
                ])
            elif 'files' in final_output or 'directories' in final_output:
                output = []
                if final_output.get('files'):
                    output.append("Files:")
                    output.extend(f"- {f}" for f in sorted(final_output['files']))
                if final_output.get('directories'):
                    if output:
                        output.append("")
                    output.append("Directories:")
                    output.extend(f"- {d}" for d in sorted(final_output['directories']))
                return "\n".join(output) if output else "No files or directories found"
            else:
                return str(final_output)
        else:
            return str(final_output)
            
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