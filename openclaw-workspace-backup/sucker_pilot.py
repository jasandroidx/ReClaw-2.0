import requests
import pandas as pd
import os

# The Gateway Download Page
URL = "https://gateway.ifionline.org/public/download.aspx"

# These are the form fields identified in the recon for "Annual Financial Reports" -> "Disbursements by Fund"
# We target 2023 for a recent, completed year.
payload = {
    "ctl00$ContentPlaceHolder1$RadComboBox1": "Annual Financial Reports",
    "ctl00$ContentPlaceHolder1$RadComboBox2": "Disbursements by Fund",
    "ctl00$ContentPlaceHolder1$DropDownListUnitType": "All",
    "ctl00$ContentPlaceHolder1$DropDownListYear": "2023",
    "ctl00$ContentPlaceHolder1$button_download1": "Download"
}

def download_gateway_data():
    print("Initiating bulk download from Gateway...")
    session = requests.Session()
    
    # First get the page to grab the ViewState (required for ASP.NET forms)
    response = session.get(URL)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    viewstate = soup.find("input", {"id": "__VIEWSTATE"})['value']
    viewstate_gen = soup.find("input", {"id": "__VIEWSTATEGENERATOR"})['value']
    event_validation = soup.find("input", {"id": "__EVENTVALIDATION"})['value']
    
    # Add the required ASP.NET hidden fields to our payload
    payload["__VIEWSTATE"] = viewstate
    payload["__VIEWSTATEGENERATOR"] = viewstate_gen
    payload["__EVENTVALIDATION"] = event_validation
    
    # Perform the POST request
    print("Sending POST request for 2023 Disbursements...")
    res = session.post(URL, data=payload)
    
    if res.status_code == 200:
        with open("gateway_disbursements_2023.txt", "wb") as f:
            f.write(res.content)
        print("File downloaded successfully: gateway_disbursements_2023.txt")
        return True
    else:
        print(f"Download failed with status: {res.status_code}")
        return False

def analyze_pike_county():
    print("\nAnalyzing data for Pike County...")
    # The file is pipe-delimited (|)
    try:
        df = pd.read_csv("gateway_disbursements_2023.txt", sep='|', on_bad_lines='skip', low_memory=False)
        
        # Search for 'Pike' in the unit name/column. 
        # We need to find the correct column name first.
        print("Columns found:", df.columns.tolist())
        
        # Try to find the unit column (likely contains 'Unit' or 'Name')
        unit_col = next((col for col in df.columns if 'Unit' in col or 'Name' in col), None)
        if not unit_col:
            print("Could not find unit column.")
            return
        
        pike_data = df[df[unit_col].str.contains("Pike", case=False, na=False)]
        
        if pike_data.empty:
            print("No data found for Pike County in this file.")
            return
            
        print(f"Found {len(pike_data)} records for Pike County.")
        
        # Look for the largest expenditures
        amount_col = next((col for col in df.columns if 'Amount' in col or 'Total' in col), None)
        if amount_col:
            top_spends = pike_data.sort_values(by=amount_col, ascending=False).head(10)
            print("\n--- Top 10 Expenditures for Pike County (2023) ---")
            print(top_spends[[unit_col, amount_col] + [col for col in df.columns if 'Category' in col or 'Fund' in col][:2]])
        else:
            print("Could not find amount column.")
            
    except Exception as e:
        print(f"Analysis error: {e}")

if __name__ == "__main__":
    if download_gateway_data():
        analyze_pike_county()
