#!/usr/bin/env python3
"""Verify backend directory structure and imports."""

import ast
import sys
from pathlib import Path

def check_imports_in_file(file_path: Path) -> bool:
    """Check if a Python file has valid syntax and imports."""
    try:
        with open(file_path, 'r') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return False

def main() -> None:
    """Main verification function."""
    backend_dir = Path(__file__).parent
    
    print("=" * 60)
    print("Video Downloader Backend Structure Verification")
    print("=" * 60)
    
    # Check required directories
    required_dirs = [
        "app",
        "app/models",
        "app/routers",
        "app/services",
        "app/tasks",
        "app/utils",
        "migrations",
        "tests",
    ]
    
    print("\n[1] Checking directory structure...")
    all_dirs_exist = True
    for dir_name in required_dirs:
        dir_path = backend_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ {dir_name}/ (MISSING)")
            all_dirs_exist = False
    
    # Check required files
    print("\n[2] Checking required files...")
    required_files = [
        "pyproject.toml",
        "Dockerfile",
        ".env.example",
        "requirements.txt",
        "app/__init__.py",
        "app/config.py",
        "app/database.py",
        "app/main.py",
        "app/models/__init__.py",
        "app/models/video.py",
        "app/models/tag.py",
        "app/models/category.py",
        "app/routers/__init__.py",
        "app/routers/downloads.py",
        "app/routers/videos.py",
        "app/routers/tags.py",
        "app/routers/categories.py",
        "app/routers/webhook.py",
        "app/routers/settings.py",
        "app/services/__init__.py",
        "app/services/downloader.py",
        "app/services/categorizer.py",
        "app/services/search.py",
        "app/services/thumbnail.py",
        "app/services/notifier.py",
        "app/tasks/__init__.py",
        "app/tasks/download_task.py",
        "app/utils/__init__.py",
        "app/utils/url_parser.py",
        "app/utils/file_utils.py",
    ]
    
    all_files_exist = True
    for file_name in required_files:
        file_path = backend_dir / file_name
        if file_path.exists() and file_path.is_file():
            print(f"  ✓ {file_name}")
        else:
            print(f"  ✗ {file_name} (MISSING)")
            all_files_exist = False
    
    # Check Python syntax
    print("\n[3] Checking Python file syntax...")
    python_files = list(backend_dir.rglob("*.py"))
    all_valid = True
    for py_file in sorted(python_files):
        # Skip __pycache__ and .venv
        if "__pycache__" in str(py_file) or ".venv" in str(py_file):
            continue
        
        if check_imports_in_file(py_file):
            print(f"  ✓ {py_file.relative_to(backend_dir)}")
        else:
            all_valid = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_dirs_exist and all_files_exist and all_valid:
        print("✓ All checks passed! Backend is ready.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Update .env with your API_KEY and preferences")
        print("3. Run: python -m uvicorn app.main:app --reload")
        sys.exit(0)
    else:
        print("✗ Some checks failed. Please review above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
