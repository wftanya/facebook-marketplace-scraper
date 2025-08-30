#!/usr/bin/env python3
"""
Test script for email notifications
Run this to test your email configuration before using the scraper
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the parent directory to Python path to import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import send_hot_item_email
    print("✅ Successfully imported email function")
except ImportError as e:
    print(f"❌ Failed to import email function: {e}")
    sys.exit(1)

def test_email_config():
    """Test email configuration and send a test email"""
    
    # Check environment variables
    sender = os.getenv('GMAIL_SENDER', '')
    password = os.getenv('GMAIL_APP_PASSWORD', '')
    recipients = os.getenv('EMAIL_RECIPIENTS', '')
    
    print("\n🔍 Checking email configuration...")
    
    if not sender:
        print("❌ GMAIL_SENDER not set in .env file")
        return False
    else:
        print(f"✅ GMAIL_SENDER: {sender}")
    
    if not password:
        print("❌ GMAIL_APP_PASSWORD not set in .env file")
        return False
    else:
        print(f"✅ GMAIL_APP_PASSWORD: {'*' * len(password)} (hidden)")
    
    if not recipients:
        print("❌ EMAIL_RECIPIENTS not set in .env file")
        return False
    else:
        print(f"✅ EMAIL_RECIPIENTS: {recipients}")
    
    return True

def send_test_email():
    """Send a test HOT item notification"""
    
    # Create sample HOT items for testing
    test_hot_items = [
        {
            'title': 'Test HOT Item #1 - Vintage Computer',
            'image': 'https://via.placeholder.com/300x200/ff4444/ffffff?text=Test+Item+1',
            'link': 'https://www.facebook.com/marketplace/item/test123',
            'item_type': 'hot',
            'has_just_listed_pill': True
        },
        {
            'title': 'Test HOT Item #2 - Rare Collectible',
            'image': 'https://via.placeholder.com/300x200/ff4444/ffffff?text=Test+Item+2',
            'link': 'https://www.facebook.com/marketplace/item/test456',
            'item_type': 'hot',
            'has_just_listed_pill': True
        }
    ]
    
    print("\n📧 Sending test email notification...")
    
    try:
        success = send_hot_item_email(
            hot_items=test_hot_items,
            query="Test Query",
            city="TestCity"
        )
        
        if success:
            print("✅ Test email sent successfully!")
            print("📬 Check your inbox for the HOT items notification")
            return True
        else:
            print("❌ Failed to send test email")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 DingBot™ Email Notification Test")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("\n❌ No .env file found!")
        print("📋 Please copy .env.example to .env and fill in your credentials")
        print("\nSteps:")
        print("1. cp .env.example .env")
        print("2. Edit .env with your Gmail credentials")
        print("3. Run this test again")
        return False
    
    # Test configuration
    if not test_email_config():
        print("\n❌ Email configuration incomplete")
        print("📋 Please check your .env file and fill in all required fields")
        return False
    
    # Send test email
    if not send_test_email():
        print("\n❌ Email test failed")
        print("🔧 Please check your Gmail App Password and try again")
        return False
    
    print("\n🎉 All tests passed!")
    print("🔥 Your HOT item email notifications are ready to go!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
