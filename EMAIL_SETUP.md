# Email Notification Setup Guide

This guide will help you set up Gmail email notifications for HOT marketplace items.

## Prerequisites

- A Gmail account
- Access to your Google Account settings

## Step-by-Step Setup

### 1. Enable 2-Factor Authentication (Required)

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", click on **2-Step Verification**
4. Follow the prompts to set up 2-factor authentication if not already enabled

### 2. Generate Gmail App Password

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", click on **App passwords**
   - If you don't see this option, make sure 2-Step Verification is enabled first
4. Click **Select app** and choose **Mail**
5. Click **Select device** and choose **Other (custom name)**
6. Enter a name like "Facebook Marketplace Scraper"
7. Click **Generate**
8. **IMPORTANT**: Copy the 16-character password that appears (it looks like: `abcd efgh ijkl mnop`)
   - This is your App Password - save it securely!

### 3. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your actual values:
   ```bash
   # Your Gmail address that will send the notifications
   GMAIL_SENDER=your.actual.email@gmail.com
   
   # The 16-character App Password you just generated
   GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
   
   # Email addresses that should receive notifications (comma-separated)
   EMAIL_RECIPIENTS=recipient1@gmail.com,recipient2@yahoo.com
   ```

### 4. Test the Email Configuration

Run the test script to verify your setup:

```bash
python test_email.py
```

If successful, you should receive a test email at your configured recipient addresses.

## Email Notification Features

### When Emails Are Sent

- **Only for HOT items**: Emails are sent when items are found that are both "suggested" by Facebook AND have the "Just listed" pill
- **Real-time alerts**: Emails are sent immediately when HOT items are discovered
- **Rich HTML format**: Beautiful, mobile-friendly email design with images and direct links

### Email Content

Each notification email includes:
- 🔥 **HOT ITEMS ALERT** header with count and timestamp
- **Item details**: Title, image, and direct link to Facebook
- **Visual styling**: Red borders and badges to highlight hot items
- **One-click access**: Direct "VIEW ON FACEBOOK" buttons
- **Mobile-friendly**: Responsive design that works on all devices

### Sample Email Preview

```
🔥 HOT ITEMS ALERT! 🔥
Found 2 hot items in Toronto for "vintage camera"
December 15, 2024 at 3:42 PM

🔥 HOT ITEM
Canon AE-1 Vintage Film Camera - Excellent Condition
[Image of camera]
[VIEW ON FACEBOOK →]

🔥 HOT ITEM  
Rare Polaroid SX-70 - Working Condition
[Image of polaroid]
[VIEW ON FACEBOOK →]
```

## Security Notes

- **Never share your App Password**: Treat it like a regular password
- **Use environment variables**: Don't hardcode credentials in your code
- **Secure your .env file**: Add `.env` to your `.gitignore` to avoid committing secrets

## Troubleshooting

### Common Issues

**"Authentication failed" error:**
- Double-check your Gmail address and App Password
- Make sure 2-Step Verification is enabled
- Verify the App Password was copied correctly (no extra spaces)

**"No module named 'dotenv'" error:**
- Install the required dependency: `pip install python-dotenv`

**Not receiving emails:**
- Check your spam/junk folder
- Verify recipient email addresses are correct
- Run the test script to isolate the issue

**"Less secure app access" message:**
- This is outdated - use App Passwords instead of "less secure apps"
- App Passwords are the modern, secure way to authenticate

### Getting Help

If you encounter issues:
1. Run `python test_email.py` to test your configuration
2. Check the console logs for specific error messages
3. Verify all environment variables are set correctly
4. Ensure your Gmail account has 2-factor authentication enabled

## Advanced Configuration

### Multiple Recipients

You can send notifications to multiple email addresses:

```bash
EMAIL_RECIPIENTS=admin@company.com,manager@company.com,alerts@team.com
```

### Custom Email Settings

The email configuration uses these Gmail SMTP settings:
- **SMTP Server**: smtp.gmail.com
- **Port**: 587 (TLS/STARTTLS)
- **Security**: TLS encryption

## Privacy & Data Usage

- **No data storage**: Email credentials are only used for sending notifications
- **Secure transmission**: All email communication uses TLS encryption  
- **Local processing**: All data processing happens on your local machine
- **No tracking**: No analytics or tracking in sent emails