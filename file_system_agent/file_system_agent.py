import os
import shutil
import glob
from pathlib import Path
from typing import List, Dict, Optional
import logging
from datetime import datetime
import json
import platform
import sys

from agents import Agent, Runner, function_tool, ModelSettings
from .config import get_model_config

model = get_model_config()
logger = logging.getLogger(__name__)

# Ensure output directory exists for logs
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# OS Detection
OS_TYPE = platform.system().lower()
IS_WINDOWS = OS_TYPE == "windows"
IS_MAC = OS_TYPE == "darwin"
IS_LINUX = OS_TYPE == "linux"

def get_os_info() -> Dict:
    """Get detailed information about the current operating system."""
    return {
        'os_type': OS_TYPE,
        'platform': platform.platform(),
        'release': platform.release(),
        'version': platform.version(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'path_separator': os.path.sep,
        'line_separator': os.linesep,
        'environment': {
            'home': os.path.expanduser('~'),
            'temp': os.getenv('TEMP') if IS_WINDOWS else '/tmp',
            'system_root': os.getenv('SystemRoot') if IS_WINDOWS else '/',
        }
    }

def normalize_path(path: str) -> str:
    """Normalize path based on the current operating system."""
    # Expand user directory (~ or %USERPROFILE%)
    path = os.path.expanduser(path)
    
    # Convert forward slashes to backslashes on Windows
    if IS_WINDOWS:
        path = path.replace('/', '\\')
    else:
        path = path.replace('\\', '/')
    
    # Normalize the path (resolve .. and . components)
    return os.path.normpath(path)

@function_tool
def get_system_info() -> Dict:
    """Get information about the current operating system and file system."""
    try:
        os_info = get_os_info()
        fs_info = {
            'directory_separator': os.path.sep,
            'line_separator': os.linesep,
            'file_system_encoding': sys.getfilesystemencoding(),
            'default_encoding': sys.getdefaultencoding(),
            'max_path_length': 260 if IS_WINDOWS else 4096,  # Typical values
            'case_sensitive': not IS_WINDOWS,  # Windows is case-insensitive
            'hidden_files_pattern': r'^\.' if not IS_WINDOWS else r'^\.|\$',
            'executable_extensions': ['.exe', '.bat', '.cmd'] if IS_WINDOWS else ['.sh', ''],
        }
        
        return {
            'success': True,
            'message': 'System information retrieved successfully',
            'os_info': os_info,
            'fs_info': fs_info
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error getting system information: {str(e)}'
        }

# 1. Create Tools

@function_tool
def read_file_content(file_path: str, start_line: int = 1, end_line: int = None) -> Dict:
    """Read content from a file with optional line range."""
    try:
        file_path = normalize_path(file_path)
        if not os.path.exists(file_path):
            return {
                'success': False,
                'message': f'File not found: {file_path}',
                'content': None
            }

        # Handle encoding based on OS
        encoding = 'utf-8'
        if IS_WINDOWS:
            # Try to detect encoding on Windows
            import chardet
            with open(file_path, 'rb') as f:
                raw = f.read()
                result = chardet.detect(raw)
                encoding = result['encoding'] or 'utf-8'

        with open(file_path, 'r', encoding=encoding) as f:
            if end_line:
                lines = []
                for i, line in enumerate(f, 1):
                    if i < start_line:
                        continue
                    if i > end_line:
                        break
                    # Normalize line endings
                    lines.append(line.rstrip('\r\n') + os.linesep)
                content = ''.join(lines)
            else:
                content = f.read()

        return {
            'success': True,
            'message': 'File read successfully',
            'content': content,
            'file_path': file_path,
            'encoding': encoding
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error reading file: {str(e)}',
            'content': None
        }

@function_tool
def write_file_content(file_path: str, content: str, mode: str = 'w') -> Dict:
    """Write or append content to a file."""
    try:
        file_path = normalize_path(file_path)
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Handle line endings based on OS
        if IS_WINDOWS:
            content = content.replace('\n', '\r\n')
        else:
            content = content.replace('\r\n', '\n')
        
        # Set appropriate permissions based on OS
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        if not IS_WINDOWS:
            # Set Unix permissions (read/write for owner, read for others)
            os.chmod(file_path, 0o644)
        
        return {
            'success': True,
            'message': f'Content {"written to" if mode == "w" else "appended to"} file successfully',
            'file_path': file_path,
            'os_type': OS_TYPE
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error writing to file: {str(e)}'
        }

@function_tool
def list_directory(directory: str = '.', pattern: str = '*', show_hidden: bool = False) -> Dict:
    """List contents of a directory with optional glob pattern."""
    try:
        directory = normalize_path(directory)
        if not os.path.exists(directory):
            return {
                'success': False,
                'message': f'Directory not found: {directory}',
                'contents': None
            }

        # Handle hidden files based on OS
        hidden_pattern = r'^\.' if not IS_WINDOWS else r'^\.|\$'
        items = glob.glob(os.path.join(directory, pattern))
        
        files = []
        dirs = []
        for item in items:
            # Skip hidden files unless explicitly requested
            if not show_hidden and (
                (not IS_WINDOWS and os.path.basename(item).startswith('.')) or
                (IS_WINDOWS and any(p.startswith('.') or p.endswith('$') for p in Path(item).parts))
            ):
                continue

            if os.path.isfile(item):
                file_info = {
                    'name': os.path.basename(item),
                    'path': item,
                    'size': os.path.getsize(item),
                    'modified': datetime.fromtimestamp(os.path.getmtime(item)).isoformat(),
                    'is_hidden': (
                        (not IS_WINDOWS and os.path.basename(item).startswith('.')) or
                        (IS_WINDOWS and bool(os.stat(item).st_file_attributes & 0x2))
                    ),
                    'is_executable': (
                        not IS_WINDOWS and os.access(item, os.X_OK) or
                        IS_WINDOWS and any(item.lower().endswith(ext) for ext in ['.exe', '.bat', '.cmd'])
                    )
                }
                files.append(file_info)
            elif os.path.isdir(item):
                dir_info = {
                    'name': os.path.basename(item),
                    'path': item,
                    'modified': datetime.fromtimestamp(os.path.getmtime(item)).isoformat(),
                    'is_hidden': (
                        (not IS_WINDOWS and os.path.basename(item).startswith('.')) or
                        (IS_WINDOWS and bool(os.stat(item).st_file_attributes & 0x2))
                    )
                }
                dirs.append(dir_info)

        return {
            'success': True,
            'message': 'Directory listed successfully',
            'directory': directory,
            'files': files,
            'directories': dirs,
            'os_type': OS_TYPE
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error listing directory: {str(e)}',
            'contents': None
        }

@function_tool
def move_file(source: str, destination: str) -> Dict:
    """Move a file or directory from source to destination."""
    try:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        if not os.path.exists(source):
            return {
                'success': False,
                'message': f'Source not found: {source}'
            }

        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        
        # Move the file or directory
        shutil.move(source, destination)
        
        return {
            'success': True,
            'message': f'Successfully moved {source} to {destination}',
            'source': source,
            'destination': destination
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error moving file: {str(e)}'
        }

@function_tool
def copy_file(source: str, destination: str) -> Dict:
    """Copy a file or directory from source to destination."""
    try:
        source = os.path.expanduser(source)
        destination = os.path.expanduser(destination)
        
        if not os.path.exists(source):
            return {
                'success': False,
                'message': f'Source not found: {source}'
            }

        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
        
        # Copy the file or directory
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        
        return {
            'success': True,
            'message': f'Successfully copied {source} to {destination}',
            'source': source,
            'destination': destination
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error copying file: {str(e)}'
        }

@function_tool
def delete_file(file_path: str) -> Dict:
    """Delete a file or directory."""
    try:
        file_path = os.path.expanduser(file_path)
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'message': f'Path not found: {file_path}'
            }

        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
        
        return {
            'success': True,
            'message': f'Successfully deleted {file_path}',
            'deleted_path': file_path
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error deleting file: {str(e)}'
        }

@function_tool
def search_files(directory: str = '.', pattern: str = '*', content_pattern: str = None) -> Dict:
    """Search for files by name pattern and optionally by content."""
    try:
        directory = os.path.expanduser(directory)
        if not os.path.exists(directory):
            return {
                'success': False,
                'message': f'Directory not found: {directory}',
                'matches': None
            }

        matches = []
        # Walk through directory
        for root, _, files in os.walk(directory):
            for filename in files:
                if glob.fnmatch.fnmatch(filename, pattern):
                    file_path = os.path.join(root, filename)
                    
                    # If content pattern is specified, check file content
                    if content_pattern:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content_pattern in content:
                                    matches.append({
                                        'path': file_path,
                                        'size': os.path.getsize(file_path),
                                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                                    })
                        except:
                            # Skip files that can't be read as text
                            continue
                    else:
                        matches.append({
                            'path': file_path,
                            'size': os.path.getsize(file_path),
                            'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        })

        return {
            'success': True,
            'message': f'Found {len(matches)} matching files',
            'matches': matches
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'Error searching files: {str(e)}',
            'matches': None
        }

# 2. Create Specialized Agents

file_reader_agent = Agent(
    name="File Reader Agent",
    instructions=f"""You are a file reading specialist. Your responsibilities include:
    
    1. Read file contents:
       - Handle different file types
       - Support line range reading
       - Report file content accurately
       - Handle encoding properly
       - Handle OS-specific line endings ({repr(os.linesep)})
    
    2. Operating System Awareness:
       Current OS: {OS_TYPE.upper()}
       - Path separator: {repr(os.path.sep)}
       - Line separator: {repr(os.linesep)}
       - File system encoding: {sys.getfilesystemencoding()}
    
    3. Command Execution Format:
       For each command:
       1. Show the command to be executed:
          ```bash {{run}}
          cat file_path  # or appropriate OS-specific command
          ```
          
       2. Show the terminal output:
          ```terminal
          <actual file content>
          ```
          
       3. Provide analysis of the content
    
    Focus on accurate file reading and content presentation.""",
    model=model,
    tools=[read_file_content, get_system_info]
)

file_writer_agent = Agent(
    name="File Writer Agent",
    instructions=f"""You are a file writing specialist. Your responsibilities include:
    
    1. Write file contents:
       - Create new files
       - Append to existing files
       - Handle different file types
       - Ensure proper permissions
       - Handle OS-specific line endings ({repr(os.linesep)})
    
    2. Operating System Awareness:
       Current OS: {OS_TYPE.upper()}
       - Path separator: {repr(os.path.sep)}
       - Line separator: {repr(os.linesep)}
       - File system encoding: {sys.getfilesystemencoding()}
    
    3. Command Execution Format:
       For each operation:
       1. Show the write operation:
          ```file-write
          Writing to: file_path
          Content: <content to write>
          ```
          
       2. Show the result:
          ```terminal
          <operation result>
          ```
          
       3. Verify the write operation
    
    Focus on safe and accurate file writing.""",
    model=model,
    tools=[write_file_content, get_system_info]
)

file_manager_agent = Agent(
    name="File Manager Agent",
    instructions=f"""You are a file management specialist. Your responsibilities include:
    
    1. Manage files and directories:
       - List directory contents
       - Move files and directories
       - Copy files and directories
       - Delete files and directories
       - Search for files
       - Handle OS-specific paths and separators
    
    2. Operating System Awareness:
       Current OS: {OS_TYPE.upper()}
       - Path separator: {repr(os.path.sep)}
       - Line separator: {repr(os.linesep)}
       - File system encoding: {sys.getfilesystemencoding()}
       - Case sensitivity: {not IS_WINDOWS}
    
    3. Command Execution Format:
       For each operation:
       1. Show the command to be executed:
          ```bash {{run}}
          ls/dir/mv/cp/rm command  # Use appropriate OS-specific command
          ```
          
       2. Show the terminal output:
          ```terminal
          <actual terminal output>
          ```
          
       3. Provide operation status
    
    Focus on safe and efficient file management.""",
    model=model,
    tools=[list_directory, move_file, copy_file, delete_file, search_files, get_system_info]
)

# 3. Create Main File System Agent

file_system_agent = Agent(
    name="File System Agent",
    instructions=f"""You are the main orchestrator for file system operations. Your responsibilities include:

    1. Operating System Awareness:
       Current OS: {OS_TYPE.upper()}
       - Path separator: {repr(os.path.sep)}
       - Line separator: {repr(os.linesep)}
       - File system encoding: {sys.getfilesystemencoding()}
       - Case sensitivity: {not IS_WINDOWS}
       - Max path length: {260 if IS_WINDOWS else 4096}
    
    2. Coordinate Between Specialized Agents:
       - Use file_reader_agent for reading operations
       - Use file_writer_agent for writing operations
       - Use file_manager_agent for management tasks
    
    3. Command Execution Format:
       For each operation:
       1. Show the command to be executed:
          ```bash {{run}}
          file system command  # Use appropriate OS-specific command
          ```
          
       2. Show the terminal output:
          ```terminal
          <actual terminal output>
          ```
          
       3. Provide operation status
    
    4. Handle Complex Operations:
       - Combine multiple file operations
       - Ensure operation safety
       - Maintain data integrity
       - Handle errors gracefully
       - Consider OS-specific limitations
    
    5. Provide Clear Feedback:
       - Show operation progress
       - Report success/failure
       - Display relevant file info
       - Suggest next steps
       - Include OS-specific details
    
    Focus on providing a reliable and safe file system interface.""",
    model=model,
    tools=[
        read_file_content,
        write_file_content,
        list_directory,
        move_file,
        copy_file,
        delete_file,
        search_files,
        get_system_info
    ],
    handoffs=[
        file_reader_agent,
        file_writer_agent,
        file_manager_agent
    ]
)

# 4. Main workflow function

def run_workflow(request: str) -> str:
    """Run the file system workflow."""
    logger.info(f"Starting file system workflow for request: {request}")
    
    response = Runner.run_sync(
        file_system_agent,
        f"""Process this file system request: {request}
        
        1. Analyze the request:
           - Determine required operations
           - Check file paths
           - Verify permissions
        
        2. Execute operations:
           - Show each command
           - Display results
           - Handle any errors
        
        3. Provide feedback:
           - Summarize actions taken
           - Show operation results
           - Suggest next steps
        
        IMPORTANT:
        - Show all commands and their outputs
        - Format commands with {{run}} tags
        - Never use numbered action IDs
        - Always use "run" as the action name
        - Handle errors gracefully
        """
    )
    
    return response.final_output

# Only run the test if this file is run directly
if __name__ == "__main__":
    test_request = "List the contents of the current directory"
    print(f"Running test with request: {test_request}")
    print(run_workflow(test_request)) 