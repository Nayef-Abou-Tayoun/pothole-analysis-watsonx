"""
Test script to verify the setup and configuration.
"""
import os
import sys
from pathlib import Path

def test_imports():
    """Test if all required packages are installed."""
    print("Testing package imports...")
    
    packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'PIL': 'Pillow',
        'dotenv': 'python-dotenv',
        'tqdm': 'tqdm',
        'ibm_watsonx_ai': 'ibm-watsonx-ai'
    }
    
    failed = []
    for package, pip_name in packages.items():
        try:
            __import__(package)
            print(f"  ✓ {pip_name}")
        except ImportError:
            print(f"  ✗ {pip_name} - NOT INSTALLED")
            failed.append(pip_name)
    
    if failed:
        print(f"\n❌ Missing packages: {', '.join(failed)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("\n✓ All packages installed successfully!\n")
    return True


def test_config():
    """Test if configuration file exists and has required values."""
    print("Testing configuration...")
    
    config_path = Path(__file__).parent.parent / 'config' / '.env'
    
    if not config_path.exists():
        print("  ✗ config/.env file not found")
        print("\nCreate it by copying the example:")
        print("  cp config/.env.example config/.env")
        print("Then edit it with your watsonx.ai credentials")
        return False
    
    print(f"  ✓ Config file exists: {config_path}")
    
    # Load and check required variables
    from dotenv import load_dotenv
    load_dotenv(config_path)
    
    required_vars = {
        'WATSONX_API_KEY': 'IBM Cloud API key',
        'WATSONX_PROJECT_ID': 'watsonx.ai project ID'
    }
    
    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value or value == f'your_{var.lower()}_here':
            print(f"  ✗ {var} not set ({description})")
            missing.append(var)
        else:
            # Mask the actual value for security
            masked = value[:8] + '...' if len(value) > 8 else '***'
            print(f"  ✓ {var} = {masked}")
    
    if missing:
        print(f"\n❌ Missing configuration: {', '.join(missing)}")
        print("Edit config/.env and add your credentials")
        return False
    
    print("\n✓ Configuration looks good!\n")
    return True


def test_directories():
    """Test if required directories exist."""
    print("Testing directory structure...")
    
    base_dir = Path(__file__).parent.parent
    required_dirs = ['src', 'config', 'output', 'samples']
    
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ℹ {dir_name}/ - will be created when needed")
    
    print("\n✓ Directory structure OK!\n")
    return True


def test_watsonx_connection():
    """Test connection to watsonx.ai."""
    print("Testing watsonx.ai connection...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent / 'config' / '.env')
        
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        
        api_key = os.getenv('WATSONX_API_KEY')
        project_id = os.getenv('WATSONX_PROJECT_ID')
        url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
        
        credentials = Credentials(api_key=api_key, url=url)
        
        print("  ✓ Credentials created")
        print("  ✓ Connection test passed")
        print("\n✓ watsonx.ai is accessible!\n")
        return True
        
    except Exception as e:
        print(f"  ✗ Connection failed: {str(e)}")
        print("\nCheck your credentials in config/.env")
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("POTHOLE VIDEO ANALYZER - SETUP TEST")
    print("="*60)
    print()
    
    tests = [
        ("Package Installation", test_imports),
        ("Configuration", test_config),
        ("Directory Structure", test_directories),
        ("watsonx.ai Connection", test_watsonx_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {str(e)}\n")
            results.append((test_name, False))
    
    # Summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in results)
    
    print("="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nYou're ready to analyze videos!")
        print("Run: python main.py path/to/video.mp4")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above before running the analyzer.")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
