# 🔥 HOT Items Notification Tracking System

## Overview

The DingBot™ Facebook Scraper now includes a sophisticated notification tracking system that prevents duplicate notifications for HOT items. This ensures you only get alerted about truly NEW hot items, not ones you've already been notified about.

## How It Works

### 1. **Persistent Tracking Database**
- Creates a JSON file: `hot_items_notifications.json`
- Stores item IDs with timestamps of when notifications were sent
- Automatically cleans up old entries (older than 7 days)

### 2. **Item ID-Based Tracking**
- Uses Facebook Marketplace item IDs extracted from URLs
- More reliable than URL comparison (which varies with search parameters)
- Tracks format: `/marketplace/item/{ITEM_ID}`

### 3. **Dual Notification Channels**
- **Email Notifications**: Sent through backend API using Gmail SMTP
- **GUI Ding Notifications**: Played through Streamlit GUI
- Both channels share the same tracking database

### 4. **Smart HOT Item Classification**
The system classifies items with this priority:
1. 🔥 **HOT**: Items appearing in BOTH recent AND suggested searches (common items)
2. 🔥 **HOT**: Suggested items with Facebook's "Just listed" pill
3. ✨ **NEW**: Recent items with "Just listed" pill  
4. 💡 **SUGGESTED**: Suggested items without "Just listed" pill
5. **No badge**: Recent items without "Just listed" pill

### 5. **Automatic Cleanup**
- Old notification records (>7 days) are automatically removed
- Prevents the tracking file from growing indefinitely
- Ensures you can be re-notified if the same item becomes hot again after a week

## Files Modified

### Backend (`app.py`)
- `load_notified_items()`: Loads and cleans notification history
- `add_notified_items()`: Adds new notifications with timestamps
- `extract_item_id()`: Extracts unique item IDs from Facebook URLs
- Integration in main crawl endpoint to check and update notifications

### Frontend (`gui.py`)
- `load_notified_items()`: GUI version of notification loading
- `add_notified_items_gui()`: GUI version for updating notifications
- `extract_item_id()`: Same item ID extraction as backend
- Updated ding notification logic to use persistent tracking

### Configuration Files
- `.env.example`: Template for email configuration
- `EMAIL_SETUP.md`: Complete setup guide for Gmail notifications
- `test_email.py`: Test script to verify email configuration

## Usage Examples

### Email Notifications
Only sent for NEW hot items that haven't been notified about before:
```
🔥 2 HOT Marketplace Items Found!
Found 2 hot items in Hamilton for "Horror VHS"
August 29, 2025 at 02:30 PM

🔥 HOT ITEM: Rare Horror VHS Collection - Friday the 13th Complete Series
[Image and Facebook link included]

🔥 HOT ITEM: Vintage Nightmare on Elm Street VHS Box Set  
[Image and Facebook link included]
```

### GUI Ding Notifications
```
🔥 DING! Found 2 new HOT items!
[Audio notification plays]
```

## Benefits

1. **No Duplicate Alerts**: Never get the same notification twice
2. **Cross-Channel Sync**: Email and ding notifications share the same tracking
3. **Persistent**: Works across app restarts and crashes
4. **Self-Cleaning**: Automatically removes old entries
5. **Reliable**: Uses Facebook's actual item IDs, not fragile URL matching

## Notification Tracking File Structure

```json
{
  "123456789": 1724936400.123,
  "987654321": 1724936405.456,
  "555444333": 1724936410.789
}
```

Where:
- Keys are Facebook Marketplace item IDs
- Values are Unix timestamps of when notification was sent

## Testing

Run the test script to verify your email setup:
```bash
python test_email.py
```

This will send a test email with sample HOT items to verify everything is working correctly.
