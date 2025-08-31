#!/usr/bin/env python3
"""
PayMCP Environment Setup Script

This script helps set up the testing environment for PayMCP by:
- Checking system requirements
- Validating provider credentials  
- Setting up environment variables
- Installing dependencies
- Running basic validation tests

Usage:
    python scripts/setup_test_env.py [--interactive] [--provider PROVIDER]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Dict, List, Optional

class PayMCPSetup:
    """PayMCP environment setup assistant."""
    
    def __init__(self, interactive: bool = False):
        self.interactive = interactive
        self.project_root = Path(__file__).parent.parent
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with colored output."""
        colors = {
            "INFO": "\033[94m",    # Blue
            "SUCCESS": "\033[92m", # Green
            "ERROR": "\033[91m",   # Red
            "WARNING": "\033[93m", # Yellow
            "RESET": "\033[0m"     # Reset
        }
        
        color = colors.get(level, colors["RESET"])
        reset = colors["RESET"]
        print(f"{color}{message}{reset}")
    
    def check_python_version(self) -> bool:
        """Check Python version compatibility."""
        self.log("🐍 Checking Python version...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            self.log(f"❌ Python 3.10+ required, found {version.major}.{version.minor}", "ERROR")
            return False
        
        self.log(f"✅ Python {version.major}.{version.minor}.{version.micro}", "SUCCESS")
        return True
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed."""
        self.log("📦 Checking dependencies...")
        
        required_packages = ["requests", "pydantic"]
        test_packages = ["pytest", "pytest-cov", "pytest-mock"]
        
        missing = []
        
        for package in required_packages + test_packages:
            try:
                __import__(package.replace("-", "_"))
                self.log(f"  ✅ {package}")
            except ImportError:
                missing.append(package)
                self.log(f"  ❌ {package} (missing)", "WARNING")
        
        if missing:
            self.log(f"Missing packages: {', '.join(missing)}", "WARNING")
            if self.interactive:
                install = input("Install missing packages? (y/n): ").lower().strip()
                if install == 'y':
                    return self.install_dependencies()
            return False
        
        return True
    
    def install_dependencies(self) -> bool:
        """Install project dependencies."""
        self.log("📥 Installing dependencies...")
        
        try:
            # Install main package in development mode
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", "."
            ], cwd=self.project_root, check=True, capture_output=True)
            
            # Install test dependencies
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-e", ".[test,dev]"
            ], cwd=self.project_root, check=True, capture_output=True)
            
            self.log("✅ Dependencies installed successfully", "SUCCESS")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Failed to install dependencies: {e}", "ERROR")
            return False
    
    def setup_paypal_credentials(self) -> None:
        """Interactive PayPal credential setup."""
        self.log("\n🔐 PayPal Credentials Setup")
        self.log("Get your credentials from: https://developer.paypal.com")
        
        client_id = os.getenv("PAYPAL_CLIENT_ID")
        client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        
        if client_id and client_secret:
            self.log("✅ PayPal credentials already set", "SUCCESS")
            self.log(f"  Client ID: {client_id[:10]}...{client_id[-4:]}")
            return
        
        if self.interactive:
            print("\nEnter your PayPal sandbox credentials:")
            client_id = input("PayPal Client ID: ").strip()
            client_secret = input("PayPal Client Secret: ").strip()
            
            if client_id and client_secret:
                self.log("Add these to your environment:", "INFO")
                print(f'export PAYPAL_CLIENT_ID="{client_id}"')
                print(f'export PAYPAL_CLIENT_SECRET="{client_secret}"')
                print('export PAYPAL_RETURN_URL="https://yourapp.com/success"')
                print('export PAYPAL_CANCEL_URL="https://yourapp.com/cancel"')
        else:
            self.log("❌ PayPal credentials not found", "WARNING")
            self.log("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET environment variables")
    
    def setup_stripe_credentials(self) -> None:
        """Interactive Stripe credential setup."""
        self.log("\n💳 Stripe Credentials Setup") 
        self.log("Get your credentials from: https://stripe.com/docs/keys")
        
        api_key = os.getenv("STRIPE_API_KEY")
        
        if api_key:
            self.log("✅ Stripe credentials already set", "SUCCESS")
            self.log(f"  API Key: {api_key[:10]}...{api_key[-4:]}")
            return
        
        if self.interactive:
            print("\nEnter your Stripe test credentials:")
            api_key = input("Stripe Secret Key (sk_test_...): ").strip()
            
            if api_key:
                self.log("Add this to your environment:", "INFO")
                print(f'export STRIPE_API_KEY="{api_key}"')
                print('export STRIPE_SUCCESS_URL="https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}"')
                print('export STRIPE_CANCEL_URL="https://yourapp.com/cancel"')
        else:
            self.log("❌ Stripe credentials not found", "WARNING")
            self.log("Set STRIPE_API_KEY environment variable")
    
    def setup_walleot_credentials(self) -> None:
        """Interactive Walleot credential setup."""
        self.log("\n🔵 Walleot Credentials Setup")
        self.log("Get your credentials from: https://walleot.com/developers")
        
        api_key = os.getenv("WALLEOT_API_KEY")
        
        if api_key:
            self.log("✅ Walleot credentials already set", "SUCCESS")
            self.log(f"  API Key: {api_key[:10]}...{api_key[-4:]}")
            return
        
        if self.interactive:
            print("\nEnter your Walleot credentials:")
            api_key = input("Walleot API Key: ").strip()
            
            if api_key:
                self.log("Add this to your environment:", "INFO")
                print(f'export WALLEOT_API_KEY="{api_key}"')
        else:
            self.log("❌ Walleot credentials not found", "WARNING")
            self.log("Set WALLEOT_API_KEY environment variable")
    
    def validate_setup(self) -> bool:
        """Validate that setup is working."""
        self.log("\n🧪 Validating setup...")
        
        try:
            # Test imports
            from paymcp import PayMCP
            from paymcp.providers.paypal import PayPalProvider
            from paymcp.providers.stripe import StripeProvider
            from paymcp.providers.walleot import WalleotProvider
            
            self.log("✅ All modules imported successfully", "SUCCESS")
            
            # Test PayPal if credentials available
            if os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET"):
                from paymcp.providers.paypal import PayPalConfig
                config = PayPalConfig.from_env()
                provider = PayPalProvider(config=config)
                self.log("✅ PayPal provider initialized", "SUCCESS")
            
            # Test Stripe if credentials available
            if os.getenv("STRIPE_API_KEY"):
                provider = StripeProvider(api_key=os.getenv("STRIPE_API_KEY"))
                self.log("✅ Stripe provider initialized", "SUCCESS")
            
            # Test Walleot if credentials available
            if os.getenv("WALLEOT_API_KEY"):
                provider = WalleotProvider(api_key=os.getenv("WALLEOT_API_KEY"))
                self.log("✅ Walleot provider initialized", "SUCCESS")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Setup validation failed: {e}", "ERROR")
            return False
    
    def create_env_file(self) -> None:
        """Create sample .env file."""
        self.log("📝 Creating sample .env file...")
        
        env_content = '''# PayMCP Environment Configuration
# Copy this file to .env and fill in your credentials

# PayPal Configuration
PAYPAL_CLIENT_ID=your_paypal_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_paypal_sandbox_client_secret
PAYPAL_RETURN_URL=https://yourapp.com/payment/success
PAYPAL_CANCEL_URL=https://yourapp.com/payment/cancel
PAYPAL_BRAND_NAME=Your App Name

# Stripe Configuration
STRIPE_API_KEY=sk_test_your_stripe_secret_key
STRIPE_SUCCESS_URL=https://yourapp.com/success?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://yourapp.com/cancel

# Walleot Configuration
WALLEOT_API_KEY=your_walleot_api_key

# Optional: Load with python-dotenv
# pip install python-dotenv
# from dotenv import load_dotenv
# load_dotenv()
'''
        
        env_file = self.project_root / ".env.example"
        with open(env_file, "w") as f:
            f.write(env_content)
        
        self.log(f"✅ Created {env_file}", "SUCCESS")
        self.log("Edit .env.example with your credentials and rename to .env")
    
    def print_next_steps(self) -> None:
        """Print next steps for the user."""
        self.log("\n🎯 NEXT STEPS:", "SUCCESS")
        
        steps = [
            "1. Set up provider credentials (see .env.example)",
            "2. Run basic tests: python scripts/test_all_providers.py --unit-only",
            "3. Run integration tests: python scripts/test_all_providers.py --integration", 
            "4. Run comprehensive tests: python scripts/test_all_providers.py --verbose",
            "5. Check the SETUP_AND_TESTING_GUIDE.md for detailed instructions"
        ]
        
        for step in steps:
            self.log(f"  {step}")
        
        self.log("\n📚 Documentation:")
        self.log("  • Setup Guide: SETUP_AND_TESTING_GUIDE.md")
        self.log("  • PayPal Provider: src/paymcp/providers/paypal/README.md")
        self.log("  • Main README: README.md")
    
    def run_setup(self, provider: Optional[str] = None) -> bool:
        """Run the complete setup process."""
        self.log("🚀 PayMCP Environment Setup Starting...\n")
        
        # Check system requirements
        if not self.check_python_version():
            return False
        
        # Check and install dependencies
        if not self.check_dependencies():
            self.log("Please install dependencies and run again", "ERROR")
            return False
        
        # Setup provider credentials
        if not provider or provider == "paypal":
            self.setup_paypal_credentials()
        
        if not provider or provider == "stripe":
            self.setup_stripe_credentials()
        
        if not provider or provider == "walleot":
            self.setup_walleot_credentials()
        
        # Create sample environment file
        self.create_env_file()
        
        # Validate setup
        if self.validate_setup():
            self.log("\n🎉 Setup completed successfully!", "SUCCESS")
            self.print_next_steps()
            return True
        else:
            self.log("\n⚠️  Setup completed with issues", "WARNING")
            self.print_next_steps()
            return False


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description="PayMCP environment setup")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Interactive credential setup")
    parser.add_argument("--provider", choices=["paypal", "stripe", "walleot"],
                       help="Setup specific provider only")
    
    args = parser.parse_args()
    
    setup = PayMCPSetup(interactive=args.interactive)
    success = setup.run_setup(provider=args.provider)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()