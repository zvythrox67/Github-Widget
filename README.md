# GitHub Streak Widget

A  desktop widget that shows your live GitHub commit streak, a scrolling contribution calendar, and your most recent repo/commit. Minimize it and it collapses into
a small always-on-top flame icon you can drag anywhere on screen; click the
icon to bring the full widget back.

## What it does

- Signs in with your **real GitHub account** via OAuth Device Flow
- Shows your current commit streak and total commits (last 90 days)
- Shows a  calendar of daily commit activity, color-coded just like
  GitHub's  temperature graph
- Shows your most recently  repo where u recently pushed/did your commits to and when you did it.
- Auto-refreshes every 5 minutes
- Minimizes to a small draggable flame icon instead of closing
- 

## Setup

1. Go to [github.com/settings/developers](https://github.com/settings/developers) and Fill in any name, homepage URL, and callback URL.
2. Click **Register application**
3. Open your new app's settings page
4. **Enable Device Flow**, if you dont do this, you'll get a "Failed to start login" error
5. Copy the **Client ID** shown at the top of the page 
6. Open the `main.py` file and paste your Client ID in:

```python
Client_ID = "YOUR_CLIENT_ID_HERE"
```

7. Install requests 

```bash
pip install requests
```

8. Run the file
9. First time you run, it will load a screen that says **Sign in with GitHub**. Click it
10. A code will pop up and your browser will open automatically to GitHub
11. Enter the code, and approve access.

**Your Widget is now Working!**


