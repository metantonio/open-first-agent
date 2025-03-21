import pytest
import os
import shutil
import asyncio
from pathlib import Path

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

from .terminal_task_agent import (
    run_workflow,
    terminal_orchestrator,
    create_file,
    copy_file,
    delete_file,
    list_contents,
    find_files,
    execute_command
)

@pytest.fixture
def test_dir():
    """Create and clean up a test directory."""
    test_dir = Path('test_terminal_agent')
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(exist_ok=True)
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)

def ensure_dir(path):
    """Ensure directory exists."""
    path = Path(path)
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

def test_create_file(test_dir):
    """Test file creation."""
    ensure_dir(test_dir / "test2.txt")
    
    # Test through workflow
    result = run_workflow(f"Please create a new file at {test_dir}/test2.txt with the following content: Test Content")
    assert "success" in result.lower() or "created" in result.lower()
    assert os.path.exists(f"{test_dir}/test2.txt")
    with open(f"{test_dir}/test2.txt") as f:
        assert "Test Content" in f.read()

def test_copy_file(test_dir):
    """Test file copying."""
    # Create source file
    source = test_dir / "source.txt"
    ensure_dir(source)
    source.write_text("test content")
    
    # Test through workflow
    dest = test_dir / "dest2.txt"
    ensure_dir(dest)
    result = run_workflow(f"Please copy the file from {source} to {dest}")
    assert "success" in result.lower() or "copied" in result.lower()
    assert os.path.exists(dest)
    assert dest.read_text() == "test content"

def test_list_contents(test_dir):
    """Test listing directory contents."""
    # Create test files and directories
    ensure_dir(test_dir / "file1.txt")
    (test_dir / "file1.txt").touch()
    (test_dir / "file2.txt").touch()
    (test_dir / "dir1").mkdir()
    
    # Test through workflow
    result = run_workflow(f"Please show me the contents of the directory {test_dir}")
    # Check if files are mentioned in the response
    result_lower = result.lower()
    assert any(name in result_lower for name in ["file1.txt", "file1"])
    assert any(name in result_lower for name in ["file2.txt", "file2"])
    assert any(name in result_lower for name in ["dir1", "dir1/"])

def test_find_files(test_dir):
    """Test finding files."""
    # Create test files
    ensure_dir(test_dir / "test1.txt")
    (test_dir / "test1.txt").touch()
    (test_dir / "test2.txt").touch()
    (test_dir / "other.txt").touch()
    
    # Test through workflow
    result = run_workflow(f"Please find all files that match the pattern test*.txt in {test_dir}")
    result_lower = result.lower()
    assert "test1.txt" in result_lower
    assert "test2.txt" in result_lower
    assert "other.txt" not in result_lower

def test_delete_file(test_dir):
    """Test file deletion."""
    # Create test files
    test_file = test_dir / "to_delete.txt"
    ensure_dir(test_file)
    test_file.write_text("delete me")
    
    # Test through workflow
    result = run_workflow(f"Please delete the file at {test_file}")
    assert "success" in result.lower() or "deleted" in result.lower()
    assert not test_file.exists()

def test_execute_command():
    """Test command execution."""
    # Test through workflow
    test_message = "Hello from test"
    result = run_workflow(f'Please execute this command: echo "{test_message}"')
    assert test_message in result.lower()

def test_complex_workflow(test_dir):
    """Test a complex workflow with multiple operations."""
    complex_dir = test_dir / "complex_test"
    
    # Create directory first
    if not complex_dir.exists():
        complex_dir.mkdir(parents=True)
    
    # Test file creation
    file1_path = complex_dir / "file1.txt"
    result1 = run_workflow(f"Please create a new file at {file1_path} with the content: Test Content")
    assert "success" in result1.lower() or "created" in result1.lower()
    assert file1_path.exists()
    
    # Test file copying
    file2_path = complex_dir / "file2.txt"
    result2 = run_workflow(f"Please copy {file1_path} to {file2_path}")
    assert "success" in result2.lower() or "copied" in result2.lower()
    assert file2_path.exists()
    
    # Test listing
    result3 = run_workflow(f"Please show me the contents of {complex_dir}")
    result3_lower = result3.lower()
    assert any(name in result3_lower for name in ["file1.txt", "file1"])
    assert any(name in result3_lower for name in ["file2.txt", "file2"])

def test_error_handling():
    """Test error handling for invalid operations."""
    # Test invalid file operation
    result = run_workflow("Please delete the file at /nonexistent/file.txt")
    assert any(msg in result.lower() for msg in ["not exist", "error", "cannot", "failed"])
    
    # Test invalid command
    result = run_workflow("Please execute this command: nonexistentcommand")
    assert any(msg in result.lower() for msg in ["not found", "error", "cannot", "failed"])

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 