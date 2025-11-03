#!/usr/bin/env python
"""
Script to fix NumPy compatibility issues with the reranker.
"""
import sys
import subprocess
import platform

def fix_numpy():
    """Install compatible version of NumPy and test reranker."""
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print("Fixing NumPy compatibility issue...\n")
    
    # First uninstall current NumPy
    print("Uninstalling current NumPy...")
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "numpy"],
        check=False
    )
    
    # Install compatible NumPy version
    print("\nInstalling NumPy 1.24.0...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "numpy==1.24.0", "--no-cache-dir"],
        check=False
    )
    
    # Verify NumPy installation
    print("\nVerifying NumPy installation...")
    try:
        import numpy as np
        print(f"NumPy version: {np.__version__}")
        print("✓ NumPy successfully installed")
    except ImportError:
        print("Failed to import NumPy")
        return False
    
    # Now test the reranker
    print("\nTesting reranker with fixed NumPy...")
    try:
        from rerankers import Reranker
        print("✓ Successfully imported Reranker")
        
        # Create the reranker
        print("Loading model...")
        reranker = Reranker('cross-encoder/ms-marco-MiniLM-L-6-v2')
        print("✓ Successfully loaded the model")
        
        # Test with Italian content
        query = "economia italiana"
        docs = ["Crescita economica in Italia", "Turismo in Croazia"]
        
        print(f"Testing reranking with query: '{query}'")
        results = reranker.rank(query=query, docs=docs)
        
        # Show results
        print("\nResults:")
        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.document.text}")
            print(f"   Score: {result.score:.4f}")
        
        print("\n✓ Reranker is working correctly!")
        return True
    except Exception as e:
        print(f"\nError testing reranker: {e}")
        return False

if __name__ == "__main__":
    success = fix_numpy()
    sys.exit(0 if success else 1)
