import pytest
import os
import shutil
import platform
import asyncio
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
    
    yield
    
    # Teardown - clean up after all tests
    if test_root.exists():
        shutil.rmtree(test_root)

@pytest.fixture
def test_dir():
    """Create and clean up a test directory for each test."""
    test_dir = Path('test_terminal_agent/current_test')
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

@pytest.mark.order(1)
def test_create_file(test_dir):
    """Test file creation."""
    file_path = normalize_path(test_dir / "test2.txt")
    ensure_dir(Path(file_path))
    
    result = run_workflow(f"Please create a new file at {file_path} with the following content: Test Content")
    assert any(msg in result.lower() for msg in ["success", "created", "file has been"])
    assert os.path.exists(file_path)
    with open(file_path) as f:
        assert "Test Content" in f.read()

@pytest.mark.order(2)
def test_copy_file(test_dir):
    """Test file copying."""
    source = normalize_path(test_dir / "source.txt")
    ensure_dir(Path(source))
    Path(source).write_text("test content")
    
    dest = normalize_path(test_dir / "dest2.txt")
    ensure_dir(Path(dest))
    
    result = run_workflow(f"Please copy the file from {source} to {dest}")
    assert any(msg in result.lower() for msg in ["success", "copied", "completed"])
    assert os.path.exists(dest)
    assert Path(dest).read_text() == "test content"

@pytest.mark.order(3)
def test_list_contents(test_dir):
    """Test listing directory contents."""
    dir_path = normalize_path(test_dir)
    
    # Create test files and directories
    (test_dir / "file1.txt").touch()
    (test_dir / "file2.txt").touch()
    (test_dir / "dir1").mkdir()
    
    result = run_workflow(f"Please list all files and directories in {dir_path}")
    result_lower = result.lower()
    
    # Check for files in a platform-independent way
    assert any(name in result_lower for name in ["file1.txt", "file1"])
    assert any(name in result_lower for name in ["file2.txt", "file2"])
    assert any(name in result_lower for name in ["dir1", "dir1/", "dir1\\"])

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
    complex_dir = normalize_path(test_dir / "complex_test")
    
    # Create directory first
    Path(complex_dir).mkdir(parents=True, exist_ok=True)
    
    # Test file creation
    file1_path = normalize_path(Path(complex_dir) / "file1.txt")
    result1 = run_workflow(f"Please create a new file at {file1_path} with the content: Test Content")
    assert any(msg in result1.lower() for msg in ["success", "created", "file has been"])
    assert os.path.exists(file1_path)
    
    # Test file copying
    file2_path = normalize_path(Path(complex_dir) / "file2.txt")
    result2 = run_workflow(f"Please copy {file1_path} to {file2_path}")
    assert any(msg in result2.lower() for msg in ["success", "copied", "completed"])
    assert os.path.exists(file2_path)
    
    # Test listing
    result3 = run_workflow(f"Please list all files in {complex_dir}")
    result3_lower = result3.lower()
    assert any(name in result3_lower for name in ["file1.txt", "file1"])
    assert any(name in result3_lower for name in ["file2.txt", "file2"])

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