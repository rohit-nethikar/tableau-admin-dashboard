# Tableau Admin Dashboard - Launch and Login Guide

## Prerequisites

Before launching the app, ensure you have:
- Python 3.7+ installed
- Access to Tableau Server (https://qualityanalytics.mayocliniclabs.com)
- A valid Tableau Personal Access Token (PAT) with permissions to all configured sites
- Administrator or appropriate permissions on Tableau Server

## Step 1: Install Dependencies

Open a terminal/command prompt and navigate to the project directory:

```bash
cd c:\Users\m239012\OneDrive - Mayo Clinic\GitHub_claude\tableau-admin-dashboard
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Step 2: Verify Configuration

The app is pre-configured to connect to:
- **Server URL:** https://qualityanalytics.mayocliniclabs.com
- **Configured Sites:**
  - ClientFeeSchedule-DEV
  - InteractiveDashboards
  - InteractiveDashboards-DEV
  - InteractiveDashboards-INT
  - InteractiveDashboards-TST

If you need to change these settings, edit `config.yaml` before starting the app.

## Step 3: Start the Application

Run the Flask app:

```bash
python app.py
```

You should see output indicating the server is starting. The app will listen on:
- **URL:** http://127.0.0.1:5000
- **Port:** 5000
- **Host:** 0.0.0.0 (accessible from other machines on your network)

## Step 4: Initial Setup (First Time Only)

When you first access the app, you'll need to configure your Tableau credentials:

1. **Open your browser** and go to: http://127.0.0.1:5000

2. **Click "Get Started"** on the landing page

3. **Fill in the Setup Form:**

   ### Personal Access Token Name
   - Log into your Tableau Server account
   - Go to **Account Settings → Personal Access Tokens**
   - Note the **Name** of your PAT
   - Enter it in this field
   
   ### Personal Access Token Secret
   - From the same Personal Access Tokens page, copy the **Secret**
   - Note: You can only see the secret once when the token is created
   - If you've lost it, you'll need to regenerate or create a new token
   - Enter it in this field
   
   ### Dashboard Passcode
   - Create a password for local access to this dashboard
   - This is separate from your Tableau Server password
   - Make it something secure that only you know
   
   ### Confirm Passcode
   - Re-enter your dashboard passcode to confirm

4. **Click "Save"** to complete setup

5. The app will validate your credentials with Tableau Server
   - If successful, you'll be redirected to the login page
   - If unsuccessful, you'll see an error message. See **Troubleshooting** below

## Step 5: Login to the Dashboard

After initial setup is complete:

1. **Open your browser** to: http://127.0.0.1:5000

2. **You'll see the Login Page** with a passcode field

3. **Enter your Dashboard Passcode** (the one you created in Step 4)

4. **Click "Login"**

5. **You're in!** You'll be taken to the Overview page and can access all dashboard features:
   - Workbooks
   - Data Sources
   - Permissions
   - Lineage
   - Health Scoring
   - Findings Queue
   - Refresh Reliability
   - Multi-Site Support

## Subsequent Logins

After the first setup, each time you access the app:

1. Go to: http://127.0.0.1:5000
2. Enter your dashboard passcode
3. Click "Login"
4. Access the dashboard

## Troubleshooting

### "Could not sign in to Tableau Server with those credentials"

This error means your Tableau PAT is invalid. Check:

1. **PAT Has Not Expired**
   - Log into Tableau Server
   - Go to Account Settings → Personal Access Tokens
   - Check the expiration date
   - If expired, regenerate the token

2. **PAT Name and Secret Are Correct**
   - Copy the PAT name exactly (case-sensitive)
   - Copy the PAT secret exactly from Tableau Server
   - Ensure no extra spaces were accidentally included

3. **PAT Has Proper Permissions**
   - The PAT must have permissions to access ALL configured sites:
     - ClientFeeSchedule-DEV
     - InteractiveDashboards
     - InteractiveDashboards-DEV
     - InteractiveDashboards-INT
     - InteractiveDashboards-TST
   - Check your PAT permissions in Tableau Server

4. **Tableau Server Is Accessible**
   - Verify you can reach https://qualityanalytics.mayocliniclabs.com in your browser
   - If using a VPN or proxy, ensure it's connected

### "Server is not responding"

If the app crashes or the server stops responding:

1. Stop the app (Ctrl+C in the terminal)
2. Wait 5 seconds
3. Start it again: `python app.py`

### Passcode Not Accepted

1. Verify you're entering the correct dashboard passcode (case-sensitive)
2. To reset, clear the database and restart setup:
   - Stop the app
   - Delete: `instance/cache.db`
   - Start the app again
   - Go through setup with your Tableau credentials again

## Security Notes

- The dashboard passcode is hashed and encrypted
- Tableau PAT secrets are encrypted at rest in the database
- The app listens on `0.0.0.0:5000` by default (accessible from any machine on your network)
- For production use behind a firewall or reverse proxy, use HTTPS and restrict access
- See the main README.md for additional security recommendations

## Additional Features

Once logged in, you can:

- **View Workbooks & Data Sources** with health scoring
- **Identify Findings** - orphaned content, permission risks, refresh failures
- **Track Refresh Reliability** across all extract refreshes
- **Audit Permissions** to identify security risks
- **View Lineage** to understand data dependencies
- **Multi-Site Management** - switch between configured Tableau sites
- **Custom Views & Subscriptions** - manage custom Tableau views and subscriptions

## Getting Help

For issues or questions:
- Check the main README.md for detailed feature documentation
- Review the USER_GUIDE.md for feature-specific instructions
- Check the server logs for error details

## Stopping the App

To stop the application:
1. In the terminal where the app is running, press **Ctrl+C**
2. The app will shut down gracefully
