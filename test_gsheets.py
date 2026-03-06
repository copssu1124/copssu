import gspread
from oauth2client.service_account import ServiceAccountCredentials

def test_connection():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    print("1. Authenticating with google_key.json...")
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scopes)
        client = gspread.authorize(creds)
        print("✅ Authentication successful!")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1swMVdcbV3keWCEF-7XctrKxxR7YkhlgNFBy8BLlOnDA/edit"
    print(f"2. Opening spreadsheet {SPREADSHEET_URL}...")
    try:
        sheet = client.open_by_url(SPREADSHEET_URL)
        print(f"✅ Spreadsheet '{sheet.title}' opened successfully!")
    except Exception as e:
        print(f"❌ Failed to open spreadsheet. Did you share it with the service account? Error: {e}")
        return

    print("3. Testing write permission by creating a test worksheet...")
    try:
        try:
            worksheet = sheet.worksheet("Test_Connection")
            print("Worksheet already exists.")
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Test_Connection", rows="10", cols="10")
            print("✅ Test worksheet created successfully!")
        
        worksheet.update_acell('A1', 'Connection Successful!')
        print("✅ Wrote to cell A1 successfully!")
    except Exception as e:
        print(f"❌ Write permission error: {e}")

if __name__ == "__main__":
    test_connection()
