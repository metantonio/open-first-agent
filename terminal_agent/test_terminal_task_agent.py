import pytest
import os
import shutil
import platform
import asyncio
import time
from pathlib import Path

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from .terminal_task_agent import (
    run_workflow,
    terminal_orchestrator
)

# Detect operating system
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

@pytest.fixture(autouse=True)
def setup_teardown():
    """Global setup and teardown for all tests."""
    # Setup - ensure we're in a clean state
    test_root = Path('test_terminal_agent')
    if test_root.exists():
        shutil.rmtree(test_root)
    test_root.mkdir(exist_ok=True)
    
    yield
    
    # Teardown - clean up after all tests
    if test_root.exists():
        shutil.rmtree(test_root)

@pytest.fixture
def test_dir():
    """Create and clean up a test directory for each test."""
    test_dir = Path('test_terminal_agent/current_test')
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)

def ensure_dir(path):
    """Ensure directory exists."""
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def normalize_path(path):
    """Normalize path for the current OS."""
    return str(Path(path).absolute())

def wait_for_file(file_path, timeout=5):
    """Wait for a file to exist with timeout."""
    start_time = time.time()
    while not os.path.exists(file_path):
        if time.time() - start_time > timeout:
            return False
        time.sleep(0.1)
    return True

@pytest.mark.order(1)
def test_create_file(test_dir):
    """Test file creation."""
    file_path = normalize_path(test_dir / "test2.txt")
    ensure_dir(Path(file_path))
    
    result = run_workflow(f"Create a new text file at {file_path} and write 'Test Content' into it")
    print(f"Create file result: {result}")  # Debug output
    
    assert wait_for_file(file_path), f"File {file_path} was not created"
    with open(file_path) as f:
        content = f.read()
        assert "Test Content" in content, f"Expected 'Test Content' but got: {content}"

@pytest.mark.order(2)
def test_copy_file(test_dir):
    """Test file copying."""
    # Create source file
    source = test_dir / "source.txt"
    source.write_text("test content")
    assert source.exists(), f"Source file {source} was not created"
    
    # Define destination path
    dest = test_dir / "dest2.txt"
    
    # Try to copy the file using the actual directory context
    result = run_workflow(f"Copy the file source.txt to dest2.txt in directory {test_dir}")
    print(f"Copy file result: {result}")  # Debug output
    
    assert dest.exists(), f"Destination file {dest} was not created"
    assert dest.read_text() == "test content", f"Content mismatch in {dest}"

@pytest.mark.order(3)
def test_list_contents(test_dir):
    """Test listing directory contents."""
    dir_path = normalize_path(test_dir)
    
    # Create test files and directories
    test_files = ["file1.txt", "file2.txt"]
    for file in test_files:
        path = test_dir / file
        path.write_text(f"content of {file}")
        assert path.exists(), f"Failed to create {path}"
    
    test_dir_path = test_dir / "dir1"
    test_dir_path.mkdir(exist_ok=True)
    assert test_dir_path.exists(), f"Failed to create directory {test_dir_path}"
    
    # List contents
    result = run_workflow(f"Show me a list of all files and folders in the directory {dir_path}")
    print(f"List contents result: {result}")  # Debug output
    
    result_lower = result.lower()
    for file in test_files:
        assert file.lower() in result_lower, f"File {file} not found in result: {result}"
    assert any(d in result_lower for d in ["dir1", "dir1/", "dir1\\"]), f"Directory 'dir1' not found in result: {result}"

@pytest.mark.order(4)
def test_find_files(test_dir):
    """Test finding files."""
    dir_path = normalize_path(test_dir)
    
    # Create test files
    (test_dir / "test1.txt").touch()
    (test_dir / "test2.txt").touch()
    (test_dir / "other.txt").touch()
    
    result = run_workflow(f"Please find all files that match the pattern test*.txt in {dir_path}")
    result_lower = result.lower()
    assert "test1.txt" in result_lower
    assert "test2.txt" in result_lower
    assert "other.txt" not in result_lower

@pytest.mark.order(5)
def test_delete_file(test_dir):
    """Test file deletion."""
    file_path = normalize_path(test_dir / "to_delete.txt")
    ensure_dir(Path(file_path))
    Path(file_path).write_text("delete me")
    
    result = run_workflow(f"Please delete the file at {file_path}")
    assert any(msg in result.lower() for msg in ["success", "deleted", "removed"])
    assert not os.path.exists(file_path)

@pytest.mark.order(6)
def test_execute_command():
    """Test command execution."""
    test_message = "Hello from test"
    
    # Use appropriate echo command for the OS
    if IS_WINDOWS:
        command = f'echo {test_message}'
    else:
        command = f'echo "{test_message}"'
    
    result = run_workflow(f"Please execute this command: {command}")
    assert test_message.lower() in result.lower()

@pytest.mark.order(7)
def test_complex_workflow(test_dir):
    """Test a complex workflow with multiple operations."""
    # Create test directory
    complex_dir = normalize_path(test_dir / "complex_test")
    Path(complex_dir).mkdir(parents=True, exist_ok=True)
    assert os.path.exists(complex_dir), f"Failed to create directory {complex_dir}"
    
    # Create first file
    file1_path = normalize_path(Path(complex_dir) / "file1.txt")
    result1 = run_workflow(f"Create a new text file at {file1_path} with the content 'Test Content'")
    print(f"Create file result: {result1}")  # Debug output
    
    assert wait_for_file(file1_path), f"File {file1_path} was not created"
    assert Path(file1_path).read_text() == "Test Content", f"Content mismatch in {file1_path}"
    
    # Copy the file
    file2_path = normalize_path(Path(complex_dir) / "file2.txt")
    result2 = run_workflow(f"Copy {file1_path} to create {file2_path}")
    print(f"Copy file result: {result2}")  # Debug output
    
    assert wait_for_file(file2_path), f"File {file2_path} was not created"
    assert Path(file2_path).read_text() == "Test Content", f"Content mismatch in {file2_path}"
    
    # List contents
    result3 = run_workflow(f"List all files in the directory {complex_dir}")
    print(f"List contents result: {result3}")  # Debug output
    
    result3_lower = result3.lower()
    assert "file1.txt" in result3_lower, f"file1.txt not found in result: {result3}"
    assert "file2.txt" in result3_lower, f"file2.txt not found in result: {result3}"

@pytest.mark.order(8)
def test_error_handling():
    """Test error handling for invalid operations."""
    # Use an invalid path appropriate for the OS
    invalid_path = "/nonexistent/file.txt" if not IS_WINDOWS else "C:\\nonexistent\\file.txt"
    
    result = run_workflow(f"Please delete the file at {invalid_path}")
    assert any(msg in result.lower() for msg in ["not exist", "error", "cannot", "failed"])
    
    # Use a command that doesn't exist on any OS
    result = run_workflow("Please execute this command: nonexistentcommand123")
    assert any(msg in result.lower() for msg in ["not found", "error", "cannot", "failed"])

if __name__ == "__main__":
    # Install pytest-order if not already installed
    os.system("pip install pytest-order")
    pytest.main(["-v", "--order-scope=module", __file__]) 