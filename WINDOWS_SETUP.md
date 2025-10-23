# Windows Setup Guide for MCP BigQuery + Streamlit

This guide will help you set up and run the MCP BigQuery server with the Streamlit AI analyst app on Windows.

## Prerequisites

- Python 3.10 or higher
- Google Cloud Project with BigQuery enabled
- OpenAI API key
- Git (optional)

## Step 1: Install Dependencies

Open PowerShell or Command Prompt and navigate to the project directory:

```powershell
cd C:\Users\YourUsername\Documents\mcp-bigquery-server

# Install the project and dependencies
pip install -e .
```

## Step 2: Set Up Google Cloud Credentials

### Option A: Service Account Key (Recommended for Development)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to "IAM & Admin" → "Service Accounts"
3. Create a new service account or select an existing one
4. Click "Keys" → "Add Key" → "Create new key" → "JSON"
5. Download the JSON key file
6. Save it in a secure location (e.g., `C:\keys\bigquery-key.json`)

### Option B: Application Default Credentials

```powershell
# Install Google Cloud SDK from:
# https://cloud.google.com/sdk/docs/install

# After installation, authenticate:
gcloud auth application-default login
```

## Step 3: Configure Environment Variables

### Option A: Using PowerShell (Temporary - for current session)

```powershell
# Required
$env:PROJECT_ID = "your-bigquery-project-id"
$env:OPENAI_API_KEY = "sk-your-openai-api-key"

# Optional - if using service account key
$env:KEY_FILE = "C:\keys\bigquery-key.json"

# Optional - defaults are usually fine
$env:LOCATION = "US"
$env:MCP_BIGQUERY_BASE_URL = "http://localhost:8005"
```

### Option B: Using .env File (Recommended - Persistent)

Create a file named `.env` in the project root (`C:\Users\YourUsername\Documents\mcp-bigquery-server\.env`):

```env
# Required
PROJECT_ID=your-bigquery-project-id
OPENAI_API_KEY=sk-your-openai-api-key

# Optional - if using service account key
KEY_FILE=C:\keys\bigquery-key.json

# Optional - defaults
LOCATION=US
MCP_BIGQUERY_BASE_URL=http://localhost:8005
```

**Important:** Add `.env` to your `.gitignore` to avoid committing secrets!

## Step 4: Verify Setup

Run the diagnostic tool to check if everything is configured correctly:

```powershell
python check_mcp_server.py
```

You should see output like:
```
✓ PASS  Environment Variables
✓ PASS  BigQuery Credentials
✗ FAIL  MCP Server Running  (This is expected - we haven't started it yet)
```

## Step 5: Start the MCP Server

Open a PowerShell window and run:

```powershell
# Make sure you're in the project directory
cd C:\Users\YourUsername\Documents\mcp-bigquery-server

# Start the server
mcp-bigquery --transport http --host 0.0.0.0 --port 8005
```

You should see:
```
Starting server in HTTP mode on 0.0.0.0:8005...
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8005
```

**Keep this window open!** The server needs to keep running.

## Step 6: Verify Server is Running

Open a **new** PowerShell window and run:

```powershell
python check_mcp_server.py
```

Now you should see:
```
✓ PASS  Environment Variables
✓ PASS  BigQuery Credentials
✓ PASS  MCP Server Running
✓ PASS  Server Endpoints
✓ PASS  MCPTools Client
```

## Step 7: Start the Streamlit App

In the **second** PowerShell window (not the one running the server), run:

```powershell
streamlit run streamlit_app/app.py
```

The Streamlit app should open automatically in your browser at `http://localhost:8501`

If it doesn't open automatically, manually navigate to: http://localhost:8501

## Step 8: Use the App

1. **Check the sidebar:**
   - You should see your available BigQuery datasets
   - Select a dataset to explore
   - Select tables to include schema context

2. **Ask questions:**
   - Type natural language questions like:
     - "Show me the first 10 rows from my table"
     - "What are the most common values in column X?"
     - "Analyze the data from the last 7 days"

3. **Review results:**
   - The app will show SQL queries, results, and analysis
   - Download results as CSV if needed

## Troubleshooting

### "No datasets available or the MCP server is unreachable"

**Cause:** The Streamlit app cannot connect to the MCP server.

**Solutions:**

1. **Check if the server is running:**
   ```powershell
   # In a new PowerShell window
   curl http://localhost:8005/health
   ```

   You should get a JSON response. If you get an error, the server is not running.

2. **Check the server window:**
   - Look at the PowerShell window where you started the server
   - Check for error messages
   - Make sure `PROJECT_ID` is set

3. **Restart the server:**
   - Press Ctrl+C in the server window
   - Run `mcp-bigquery --transport http --host 0.0.0.0 --port 8005` again

4. **Check firewall:**
   - Windows Firewall might be blocking the connection
   - Try allowing Python through the firewall

### "Configuration error: PROJECT_ID environment variable is required"

**Cause:** The `PROJECT_ID` environment variable is not set.

**Solution:**

```powershell
# Set it for current session
$env:PROJECT_ID = "your-bigquery-project-id"

# Or add it to .env file
```

Then restart the server.

### "Key file not found or inaccessible"

**Cause:** The path to your service account key file is wrong.

**Solution:**

1. Check the path in your environment variable or .env file:
   ```powershell
   echo $env:KEY_FILE
   ```

2. Make sure the file exists:
   ```powershell
   Test-Path "C:\keys\bigquery-key.json"
   ```

3. Use the absolute path with forward slashes or double backslashes:
   ```
   C:/keys/bigquery-key.json
   or
   C:\\keys\\bigquery-key.json
   ```

### Port Already in Use

**Cause:** Another application is using port 8005 or 8501.

**Solution:**

Use different ports:

```powershell
# For MCP server
mcp-bigquery --transport http --host 0.0.0.0 --port 8006

# Update .env file
MCP_BIGQUERY_BASE_URL=http://localhost:8006

# For Streamlit
streamlit run streamlit_app/app.py --server.port 8502
```

### "Failed to load datasets: 403 Forbidden"

**Cause:** Your service account or user account doesn't have permission to access BigQuery.

**Solution:**

1. Go to [Google Cloud Console IAM](https://console.cloud.google.com/iam-admin/iam)
2. Find your service account or user
3. Add the "BigQuery Data Viewer" role at minimum
4. Recommended roles:
   - BigQuery Data Viewer
   - BigQuery Job User

### Test Script Encoding Error

**Cause:** Windows uses a different default encoding than UTF-8.

**Solution:**

The test script has been updated to use UTF-8 encoding. If you still see errors, run:

```powershell
# Set console to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

# Then run the test
python test_integration.py
```

## Running in Production

For production deployment on Windows:

1. **Use Windows Service:**
   - Use NSSM (Non-Sucking Service Manager) to run the server as a Windows service
   - Download from: https://nssm.cc/

2. **Use IIS as reverse proxy:**
   - Install URL Rewrite and Application Request Routing
   - Configure reverse proxy to the Python server

3. **Use Docker:**
   - Create a Dockerfile for the application
   - Use Docker Desktop for Windows
   - Run containers with proper environment variables

## Quick Reference

### Start Everything

```powershell
# Terminal 1: MCP Server
mcp-bigquery --transport http --host 0.0.0.0 --port 8005

# Terminal 2: Streamlit App
streamlit run streamlit_app/app.py
```

### Check Status

```powershell
# Check MCP server
curl http://localhost:8005/health

# Check Streamlit
curl http://localhost:8501
```

### Stop Everything

```powershell
# In each terminal window, press:
Ctrl + C
```

## Additional Resources

- [Google Cloud BigQuery Docs](https://cloud.google.com/bigquery/docs)
- [Streamlit Documentation](https://docs.streamlit.io)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Python Virtual Environments on Windows](https://docs.python.org/3/library/venv.html)

## Need Help?

1. Run the diagnostic tool:
   ```powershell
   python check_mcp_server.py
   ```

2. Check the server logs in the PowerShell window

3. Check the Streamlit logs (shown in terminal or browser console)

4. Review the integration report:
   ```powershell
   cat INTEGRATION_REPORT.md
   ```

5. Run integration tests:
   ```powershell
   python test_integration.py
   ```
