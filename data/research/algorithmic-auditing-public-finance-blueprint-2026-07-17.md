---
title: Algorithmic Auditing of Public Finance — Operational Blueprint
source: operator paste (Gemini/deep research style)
ingested: 2026-07-17
status: archive-raw
---

# Algorithmic Auditing of Public Finance: An Operational Blueprint for Indiana Local Government Financial Oversight

> Raw archive of operator-provided research. Distilled SOT lives in Ravenstack ops + `data/audit_strategy.yaml` + `data/content_truth_rules.yaml`.

Algorithmic Auditing of Public Finance: An Operational Blueprint for Indiana Local Government Financial Oversight
Executive Summary
This report establishes an operational blueprint for the "ReClaw / county auditor" pipeline, a platform built to automate the auditing of public financial ledgers across Indiana's 92 counties. The current system struggles with high noise levels, generating 60 to 90 unwatchable anomalies per county. These alerts are primarily driven by false-positive vendor identification on aggregate ledger lines (such as "Governmental Activities") and misapplied statistical models.   

The primary recommendation to resolve these issues is a shift from unsupervised statistical anomaly detection to a structured, multi-pass deterministic framework. This approach combines data from the Indiana State Board of Accounts (SBOA) with Certified Employee Compensation Reports (Form 100R).   

                                  [ Raw Financial Ledger Ingest ]
                                                 |
                                                 v
                                    [ Programmatic Filters ]
                                 (Discard aggregate category codes
                                  and rollup-vendor associations)
                                                 |
                                                 v
                                  [ Deterministic Anomaly Engine ]
                              (Compute cohort-matched salary z-scores,
                               YoY fund spikes, & SBOA text patterns)
                                                 |
                                                 v
                                      [ Human Review Card ]
                                  (60-second manual validation
                                   of primary citation provenance)
                                                 |
                                                 v
                                     [ High-Retention Video ]
                                  (Auto-generate scripted narration
                                   citing verified SBOA audit IDs)
By filtering out aggregate accounts (such as "Other Services and Charges" or "WATER") and implementing cross-source validation against county commissioner claims dockets, the pipeline can isolate verifiable public finance anomalies. These findings can then be paired with clear, peer-county comparisons to produce engaging and legally defensible public interest narratives.   

Technical Analysis of Indiana County Public Finance Data Sources
Programmatic auditing of local finances in Indiana requires a clear understanding of the state's accounting systems and public data portals. The pipeline relies on a mix of state-administered data warehouses, regulatory audit repositories, local administrative records, and federal databases.   

Ingestion Source Inventory and Constraints
To prevent false positives, the ingestion engine must map the specific fields, limits, and collection methods of each targeted platform.   

1. Indiana Gateway for Government Units (gateway.ifionline.org)
Indiana Gateway serves as the central repository for local government financial reporting. It is administered by six state agencies, including the Department of Local Government Finance (DLGF) and the State Board of Accounts (SBOA).   

Annual Financial Report (AFR): This report provides annual receipts, disbursements, and fund balances on a cash basis. For cities and counties, the Detailed Disbursements dataset contains the following fields: year, county_code, unit_name, fund_name, disburse_name, and amount.   

Data Boundary: This dataset contains no vendor payee names, payment dates, invoice IDs, or purchase order numbers. The disburse_name field refers to standard accounting categories (e.g., "Other Services and Charges" or "Office Supplies"), not private companies.   

Township Exception: Unlike cities and counties, townships are required to upload vendor-level disbursements under the Disbursements by Vendor (Townships Only) application. This report includes payee names and annual totals, but does not provide transaction dates or invoice numbers.   

Employee Compensation (Form 100R): Legally mandated by IC 5-11-13-1, this certified report lists the names, business addresses, departments, job titles, and total calendar-year compensation of all public employees.   

Data Boundary: Form 100R records represent aggregate annual compensation, which can make it difficult to distinguish regular wages from overtime, retroactive pay, or multi-role adjustments. The dataset is uploaded in CSV format and includes fields such as Year, Last, First, Middle, Dept, and compensation.   

2. Indiana State Board of Accounts (audit.sboa.in.gov / in.gov/sboa)
The SBOA audits all public offices and entities receiving public funds. Its public database can be systematically queried via the SBOA Audit Report Filings App.   

Audit Frequency: Under IC 5-11-1-25, audits are conducted annually for entities with over $750,000 in federal expenditures or outstanding bond debt. Other entities are audited every two to four years based on SBOA's risk-assessment models.   

Confidentiality Boundary: SBOA Directive 2014-1 mandates that draft audit reports, exit conference findings, and related discussions remain strictly confidential. Information cannot be shared publicly until the final report is officially filed and published on the SBOA website.   

3. Local County Administrative Records (Claims Dockets and AP Warrant Lists)
Under IC 36-2-6-3, counties must present claims dockets to the Board of County Commissioners for approval prior to disbursement.   

Data Quality: Unlike Gateway's aggregate entries, local claims dockets contain transaction-level fields: vendor_name, payment_date, check_number, invoice_amount, and department.   

Access Constraints: These dockets are rarely centralized at the state level. They must be collected by scraping individual county commissioner meeting minutes or auditor portals. Document formats vary from clean PDFs to scanned, non-searchable image dockets.   

4. Auxiliary Databases
ProPublica Nonprofit Explorer API: Provides tax returns (Form 990) and audit filings for non-profit entities. This is useful for analyzing county-funded volunteer fire departments or local development corporations.   

DLGF Budget Orders and Beacon/GIS Systems: Provides property tax rates, levies, net assessed values, and parcel ownership details. These records are useful for contextualizing spending shifts against the county's tax base.   

Ingestion Source Priority Matrix
Source Name    Primary Fields    Red-Flags Unlocked    Scrape/API Method    Ingestion Priority
SBOA Report Database

[cite: 21, 36]

report_number, unit_name, file_date, report_type (B, I, S series)

Cash shortages, credit card abuse, nepotism, undocumented spending

Traversing the SBOA Audit Report Filings App using HTTP search parameters.

Level 1 (High reliability, verified findings)

Gateway Form 100R

[cite: 5, 6]

year, last_name, first_name, department, job_title, compensation

[cite: 6, 19]

High salary outliers, multi-line compensation

Post requests to public search endpoints.

Level 1 (Consistent statewide coverage)

County Claims Dockets

[cite: 7, 8]

vendor_name, check_date, check_number, amount, department

[cite: 25, 26]

Split purchases, sequential invoices, round-dollar payments

Scrape county auditor portals for meeting minutes and PDF dockets.

Level 2 (Detailed transaction data, lower coverage)

Gateway AFR

[cite: 2, 18]

year, unit_name, fund_name, disburse_name, amount

[cite: 2, 3]

Obscure fund spikes, cash-to-budget imbalances

Bulk download of pipe-delimited text files (`    
`).

ProPublica Nonprofit API

[cite: 14, 30]

ein, organization_name, revenue, expenses, officer_comp

[cite: 14, 30]

Financial health of county contractors

REST API queries using organization name or EIN.

Level 3 (Contextual validation only)

  
Publishable Red-Flag Taxonomy and Quality Gates
The pipeline requires a strict validation taxonomy to ensure the accuracy of generated scripts and preserve the fair-report privilege.   

Core Flag Taxonomy
1. Named Public Salary Shocks
Definition: Annual compensation on Form 100R that stands out as a statistical outlier compared to peer counties, or represents an extreme multiple of the county's median wage.   

Minimum Evidence: The target salary C 
i
​
  must exceed a z-score of 3.0 within its job-title cohort across all 92 counties, or exceed the county's household median wage W 
m
​
  by a factor of 4:

C 
i
​
 >μ 
cohort
​
 +3σ 
cohort
​
 ∨C 
i
​
 >4×W 
m
​
 
False-Positive Traps:

Combining different employees with the same name (e.g., "William Miller") in larger counties.

Misinterpreting retroactive pay or combined compensation for dual-role positions (such as a Sheriff acting as a Jail Commander).   

On-Screen Evidence: Highlighted cells on SBOA Form 100R, alongside a bar chart comparing the salary to peer-county averages.   

Kill Rules: Discard if the title is "Judge" or "Prosecutor" (whose salary tiers are set by state statute and reimbursed by the State of Indiana), or if the position is a contracted medical role.

2. Dual-Line Compensation (Double-Dipping)
Definition: The occurrence of identical employee names across multiple compensation rows within the same county unit on Form 100R, suggesting multiple salaries are being paid to one individual.   

Minimum Evidence: Exact match on first_name and last_name within a single county_code across distinct department entries, where the sum of compensation C 
total
​
 ≥$100,000 and the secondary salary C 
secondary
​
 ≥$20,000.   

False-Positive Traps: Common names within populated counties (e.g., Marion, Lake). High school coaches or seasonal election staff who hold multiple minor roles.   

On-Screen Evidence: Side-by-side rows from the SBOA Gateway Employee Lookup interface, highlighted and linked.   

Kill Rules: Discard if the secondary job title contains terms like "Seasonal," "Part-Time," "Poll Worker," "Temporary," "Board Member," or "Advisory".   

3. Structured Split-Purchases (Bid-Threshold Avoidance)
Definition: Dividing a single purchase into multiple transactions to stay below the public bidding threshold of $150,000, or the small-purchase quote threshold of $50,000, within a short timeframe.

Minimum Evidence: A sequence of n payments p to vendor v within a 30-day window t, where each payment falls within a narrow percentage band below the statutory threshold T:

0.90≤ 
T
p 
i
​
 
​
 <1.0
False-Positive Traps: Routine progress payments for documented construction projects or recurring utility bills.   

On-Screen Evidence: Rows from a local claims docket displaying successive checks issued to the same vendor on adjacent days.   

Kill Rules: Discard if the source is aggregate Gateway disbursement data, as it lacks vendor details and transaction timestamps. This analysis must only run on scraped local claims dockets.   

4. Round-Dollar / Identical Sequential Payments
Definition: A sequence of disbursements to a private vendor that are exact multiples of $1,000, or contain identical decimal values, suggesting a lack of itemized invoicing.   

Minimum Evidence: Three or more consecutive payments p 
i
​
  to a vendor where:

p 
i
​
 (mod1000)=0for p 
i
​
 ≥$5,000
False-Positive Traps: Fixed-rate lease agreements, monthly retainer fees, or standardized software licensing agreements.   

On-Screen Evidence: Zoomed-in view of a county claims registry showing repeating, identical round-dollar payouts.   

Kill Rules: Discard if the payee is a financial institution, utility provider, or intergovernmental fund transfer.   

5. SBOA Prior Audit Findings and Special Investigations
Definition: Written citations in Supplemental Compliance Reports or Special Investigations detailing misappropriation, unsupported spending, or internal control failures.   

Minimum Evidence: Presence of a high-severity regulatory phrase matched against an SBOA finding database.   

False-Positive Traps: Misinterpreting minor compliance errors (e.g., submitting an annual report three days late) as a major financial deficit.   

On-Screen Evidence: Sourced PDF pages from WebReports showing the "Audit Results and Comments" section, with key sentences highlighted.   

Kill Rules: None. This is the most reliable narrative category, provided the citation references the official SBOA report ID and page.   

6. Fund-Specific YoY Expenditure Spikes
Definition: Sudden spending increases in obscure local county funds, such as "Jail Commissary," "Probation User Fees," or "Cumulative Capital".   

Minimum Evidence: A YoY change in fund-level disbursements D that exceeds 3σ of the historical fund trend:

ΔD 
y,y−1
​
 >1.5×D 
y−1
​
 where D 
y−1
​
 ≥$50,000
False-Positive Traps: Spikes driven by major capital projects funded by state or federal grants.   

On-Screen Evidence: Line graphs showing stable baseline spending followed by a sharp vertical spike.   

Kill Rules: Discard if the spike is offset by an equivalent increase in federal grant revenues or documented bond proceeds within the same fiscal year.   

7. Federal vs. Local Spending Mismatches
Definition: Using restricted local funds to cover matching requirements for federal grants without authorization, or spending federal funds outside approved program guidelines.   

Minimum Evidence: SBOA audit findings confirming unauthorized local fund usage for federal match requirements.   

False-Positive Traps: Legitimate, pre-approved inter-fund transfers that have been authorized by the county council.   

On-Screen Evidence: A split-screen comparison of the federal grant guidelines against the actual local disbursement voucher.   

Kill Rules: Discard if the SBOA report indicates the transfer was legally resolved or corrected during the exit conference.   

8. Transparency and Reporting Failures
Definition: A county's failure to file mandatory financial disclosures (AFR or Form 100R) on Gateway within the legally required timeline.   

Minimum Evidence:

Current Date>Statutory Deadline+30 dayswith submission_status=Pending
False-Positive Traps: Minor administrative extensions granted by the state but not updated in the public tracking portal.   

On-Screen Evidence: A red highlight on the Gateway Submission Log interface showing a missing annual report.   

Kill Rules: Discard if the county has filed the necessary reports but they are temporarily locked for corrections.   

Hard System Kill List
The following automated red-line rules must be enforced during the pre-processing stage to eliminate statistical noise:

Target Pattern    Technical Filter Rule    Mathematical Condition    Why It Must Be Discarded
Category-Only Aggregate Sums    
Discard if disburse_name matches standard account headers.

disburse_name ∈ {"Other Services and Charges", "Other Capital Outlays", "Supplies"}.

These represent broad accounting categories, not payments to individual vendors.

Rollup Entities    
Discard if the entity name represents internal ledger balancing.

disburse_name or ent_name ∈ {"Governmental Activities", "Transfers Out", "Internal Service Funds"}.

These are internal fund transfers, not external cash transactions.

Pure Benford's Law Outliers    Block anomalies based solely on Benford's Law first-digit distribution.    χ 
Benford
2
​
 >threshold (without named ledger references).    Benford's Law is a diagnostic tool, not direct evidence of public fund mismanagement.
Low-Dollar Seasonal Compensation    
Discard if the total annual compensation is below $15,000.

compensation < $15,000 on Form 100R.

This prevents flagging minor pay adjustments for seasonal or part-time staff.

Payroll Aggregate Outliers    
Discard anomalies that fire on aggregate payroll lines.

disburse_name ∈ {"Salaries and Wages", "Employee Benefits"}.

These totals scale naturally with cost-of-living adjustments and contracts.

  
Data Extraction, Vendor Normalization, and Provenance Processing
Maintaining a high publication volume across multiple counties requires structured data ingestion pipelines. Ingestion engines must standardize disparate sources, convert unstructured PDFs into structured records, and maintain clear provenance for compliance.   

Unstructured SBOA PDF Extraction
To convert SBOA PDF findings into structured data, the parser must target specific section layouts within the documents.   

                     [ Ingest SBOA Supplemental PDF ] 
                                    |
                                    v
          [ Segment PDF by Heading: "Audit Results and Comments" ]
                                    |
                                    v
          [ Isolate Text blocks containing Statutory Citations ]
                                    |
                                    v
            [ Extract Entity, Amount, Violation, and Page Metadata ]
                                    |
                                    v
                    [ Validate and Structure into Schema ]
The parsing utility uses a regular expression engine to isolate the "Results and Comments" sections. It uses a two-pass parser to extract entities, financial values, and citations:   

Python
import re

def parse_sboa_narrative(pdf_text: str, report_id: str) -> list:
    # Isolate SBOA "Results and Comments" section
    section_match = re.search(
        r"(AUDIT RESULTS AND COMMENTS|SPECIAL INVESTIGATION RESULTS AND COMMENTS)(.*?)(EXIT CONFERENCE)", 
        pdf_text, 
        re.DOTALL | re.IGNORECASE
    )
    if not section_match:
        return []
    
    findings_block = section_match.group(2)
    extracted_findings = []
    
    # Locate instances of financial values and nearby statutory citations
    citation_pattern = r"(IC\s+\d+-\d+-\d+-\d+(?:\(.\))?)"
    amount_pattern = r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
    
    paragraphs = findings_block.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        amounts = re.findall(amount_pattern, paragraph)
        citations = re.findall(citation_pattern, paragraph)
        
        if amounts and citations:
            findings_data = {
                "report_id": report_id,
                "paragraph_index": index,
                "statutory_citation": citations[0],
                "financial_values": [float(amt.replace(",", "")) for amt in amounts],
                "context_snippet": paragraph[:250].strip()
            }
            extracted_findings.append(findings_data)
            
    return extracted_findings
Cross-Source Entity Resolution and Vendor Normalization
To resolve inconsistent vendor naming across county claims dockets, the ingestion engine uses a string-matching utility. This utility handles typical variations in vendor entries:   

Python
import re

def normalize_vendor(name: str) -> str:
    if not name:
        return "UNKNOWN_ENTITY"
    
    # Standardize casing and strip whitespace
    name = name.upper().strip()
    
    # Remove common corporate suffixes
    name = re.sub(r'\b(INC\b\.?|LLC\b\.?|CORP\b\.?|CO\b\.?|LTD\b\.?|L\.P\.?|INCORPORATED|LIMITED LIABILITY COMPANY)', '', name)
    
    # Standardize spaces and punctuation
    name = re.sub(r'[^A-Z0-9\s&]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Hardcoded entity resolution dictionary
    resolution_map = {
        "AMAZON CAPITAL SERVICES": "AMAZON",
        "DUKE ENERGY INDIANA": "DUKE ENERGY",
        "CDW GOVERNMENT": "CDW-G",
        "BOYCE SYSTEMS": "A_E_BOYCE",
    }
    
    return resolution_map.get(name, name)
By standardizing these names, the system can run a cross-source validation step:

County AP Claim Total (Scraped)⟺Gateway Grant/Contract Disclosures⟺ProPublica Nonprofit Explorer (Form 990) [cite: 7, 18, 30]
Video-Optimized Red-Flag JSON Schema
This structured data model represents a validated anomaly profile. It is designed to provide all necessary details for automated script generation and human compliance review:

JSON
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RedFlagRecord",
  "type": "object",
  "required": [
    "flag_id",
    "county",
    "fips_code",
    "fiscal_year",
    "flag_type",
    "severity_score",
    "primary_actor",
    "anomaly_amount",
    "provenance"
  ],
  "properties": {
    "flag_id": {
      "type": "string",
      "pattern": "^RF-[0-9]{4}-[0-9]{2}-[0-9]{5}$"
    },
    "county": {
      "type": "string"
    },
    "fips_code": {
      "type": "string",
      "pattern": "^18[0-9]{3}$"
    },
    "fiscal_year": {
      "type": "integer"
    },
    "flag_type": {
      "type": "string",
      "enum": [
        "SALARY_SHOCK",
        "DOUBLE_COMPENSATION",
        "SPLIT_PURCHASE",
        "ROUND_DOLLAR",
        "SBOA_FINDING",
        "FUND_SPIKE",
        "FEDERAL_MISMATCH",
        "TRANSPARENCY_GAP"
      ]
    },
    "severity_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 10.0
    },
    "primary_actor": {
      "type": "object",
      "required": ["entity_name", "entity_type"],
      "properties": {
        "entity_name": { "type": "string" },
        "entity_type": { "type": "string", "enum": ["INDIVIDUAL", "VENDOR", "FUND", "DEPARTMENT"] },
        "job_title": { "type": "string" }
      }
    },
    "comparison_metrics": {
      "type": "object",
      "properties": {
        "peer_mean": { "type": "number" },
        "county_median_wage": { "type": "number" },
        "percentage_deviation": { "type": "number" }
      }
    },
    "anomaly_amount": {
      "type": "number"
    },
    "provenance": {
      "type": "object",
      "required": ["source_platform", "report_identifier", "page_number", "url"],
      "properties": {
        "source_platform": { "type": "string", "enum": ["GATEWAY_AFR", "GATEWAY_100R", "SBOA_REPORTS", "COUNTY_AP_DOCKET"] },
[<35;95;44M[<35;96;45M        "report_identifier": { "type": "string" },
        "row_index_or_paragraph": { "type": "string" },
[<35;97;46M        "page_number": { "type": "integer" },
[<35;98;46M        "url": { "type": "string", "format": "uri" },
[<35;99;47M        "extracted_text_quote": { "type": "string" },
        "governing_statute": { "type": "string" }
      }
[<35;100;47M    }
  }
[<35;100;48M}
Short-Form Narrative Engineering and Legal Boundaries
To generate viral, faceless short-form videos (30–60 seconds), content must be optimized for viewer retention while operating within strict legal guidelines.

Short-Form Video Structure
[00-03s: Hook]       -> Bold, high-contrast text on-screen. Immediate visual focal point.
[03-15s: Proof]      -> Rapid zoom onto the official SBOA report PDF or Form 100R ledger line.
[15-30s: ELI5]       -> Simple comparison using visual charts (e.g., target salary vs. peer median).
[<35;100;48M[30-45s: Fair-Query] -> Objective, open-ended question based directly on the cited findings.
[<35;99;48M[45-60s: CTA]        -> Prompt for local engagement: "Download the report from Gateway."
Visual and Text Guidelines
On-Screen Text Density: Use a maximum of 5–7 words per screen. Text must be center-aligned in bold, sans-serif fonts (e.g., Impact or Montserrat Bold) with a high-contrast background stroke or block.

Numeric Formatting: Format financial values to avoid visual clutter. Round values above $1,000 to one decimal place (e.g., $210.8K instead of $210,811.13).

Visual Pacing: Transitions should occur every 1.5 to 2.2 seconds. Alternate between direct document highlights, dynamic bar charts, and zoom-ins on specific ledger lines. Use color-coded highlights to direct focus:   

Yellow
​
 →Target Salaries∣ 
Red
​
 →Direct Financial Deficits
Geo-Targeting Strategy
Social media distribution algorithms prioritize content using local engagement signals. Video packages must incorporate county-specific identifiers in titles, descriptions, and hashtags:

Titles: Focus on geographic specificity: "{County} County Taxpayers, Look At This..."

Metadata: Include relevant hashtags (e.g., #Indiana, #{County}County, #LocalGovernment, #Taxpayers).

Pinpointed Distribution: Post and share videos in active local community groups (e.g., Facebook community pages, local subreddits) using simple, non-spammy descriptions: "Found this in the official SBOA audit for our county."

Legal Defensibility and Fair-Report Guidelines
To maintain legal protections under the fair-report privilege and avoid defamation claims, the automation pipeline must follow strict scripting protocols:

No Criminal Accusations: Never use terms like "embezzled," "stole," "corrupt," "criminals," "fraud," or "theft" when discussing individuals. Use SBOA-aligned terminology, such as: "unsupported disbursements," "compliance failures," or "unidentified adjustments".   

Fair-Report Attribution: Frame all statements around public records, citing the official source within the narrative: "According to State Board of Accounts report B54685..." or "Public records on Indiana Gateway show..."   

Open-Ended Questioning: Frame conclusions as public inquiries: "Why did the county pay this compensation?" or "What was the business purpose of these matching grant expenses?"

[cite: 9]

Hook Rewrite Matrix
Original Anomaly Pattern    Weak/Deficient Hook    Strong/Publishable Hook    Why It Succeeds
Salary Outlier (Form 100R)

[cite: 5]

"Gibson County pays their sheriff way too much money."    
"Gibson County paid one sheriff $210K—that is double what peer counties pay. Why?"

Uses the specific county name, states an exact figure, provides peer contrast, and frames the point as an inquiry.
SBOA Finding (Late Fees)

[cite: 49]

"This county was too disorganized to pay their credit cards on time."    
"State auditors found Hampton County spent $15K in taxpayer money just on credit card late fees. Who approved this?"

Cites the auditing agency, states the exact cost to taxpayers, and asks a direct question.
SBOA Finding (Rodeo Loss)

[cite: 43]

"Lawrenceburg spent utility funds on a rodeo and lost money."    
"Lawrenceburg municipal utilities spent $390K on a professional rodeo. Rate-payers covered the loss. Is this utility-approved?"

Names the specific utility unit, cites the exact financial impact, and highlights the issue for local ratepayers.
ECA Credit Card Misuse

[cite: 50]

"A school superintendent used credit cards for personal stuff."    
"A compliance audit shows a school superintendent spent over $12K on travel credit cards. Why did school accounts pay this?"

Grounds the hook in an official compliance report and questions the underlying business purpose.
  
Video Script Templates
Salary-Specific Templates (Require Form 100R data)
Template 1: The Peer-County Outlier
Title: Who approved this salary in {county} County?

Spoken Script: "Public records show the {county} County {title} was paid ${amount} in {year}. But look at this: in neighboring {peer_county} County, the same job pays just ${peer_mean}. Why is {county} paying {pct}% more? Click below to review the official SBOA salary filings."   
[O
Caption: Indiana Gateway records show a major salary gap between {county} and {peer_county}. Is this a proper use of local property taxes? #Indiana #{county}County #Taxpayers

Template 2: Double-Compensation Flag
Title: One employee, multiple salaries in {county} County?

Spoken Script: "According to {county} County's official Form 100R filing, {name} is listed under two different departments: {dept_1} and {dept_2}. The combined payout? ${amount} in a single year. How are these dual duties tracked? The official public records are linked below."   

Caption: Form 100R records show double-line compensation for {name} in {county} County. Let us review the public data. #Indiana #{county}County #Accounting

Template 3: The Median-Wage Gap
Title: Is the {county} {title} salary too high?

Spoken Script: "The median household income in {county} County is ${median_wage}. Yet, public records show the county's {title} received ${amount} in compensation in {year}. That is {multiplier} times the average local wage. Why is local compensation scaling at this rate? Read the filings on Indiana Gateway."   

Caption: Salary comparison for {county} County. Public official compensation is {multiplier}x the local median wage. #Indiana #{county}County

Template 4: The Sudden Salary Jump
Title: A sudden salary increase in {county} County.

Spoken Script: "Official records show the {county} {title} position was paid ${amount_prev} in {year_prev}. But in {year}, that salary rose to ${amount}—a {pct}% increase in a single year. What drove this sudden adjustment? See the Gateway ledger records below."   

Caption: A year-over-year compensation adjustment for the {county} {title}. Public records are accessible on Indiana Gateway. #Indiana #{county}County

Template 5: Combined Administrative Overhead
Title: Administrative costs spike in {county} County.

Spoken Script: "Form 100R filings show the {county} {department} department paid its top three administrators a combined ${amount} in {year}. This represents {pct}% of the department's total payroll. Is this allocation of administrative costs sustainable for the county? Check the source files below."   

Caption: Administrative overhead payroll totals for {county} County's {department} department. #Indiana #{county}County

Template 6: Part-Time Aggregate Anomaly
Title: Tracking part-time compensation in {county} County.

Spoken Script: "{county} County's {year} employee report shows {count} part-time employees in the {department} department received a combined ${amount}. How does this compare to full-time staffing costs? Look through the Form 100R records on Gateway."   

Caption: Part-time payroll expenditures in the {county} County {department} department. #Indiana #{county}County

SBOA Finding Templates (Require "S" or "I" series PDF data)
Template 7: The Cash Shortage Citations
Title: A cash shortage in {county} County?

Spoken Script: "State Board of Accounts report {report_id} lists a ${amount} cash shortage in {county} County's {department}. According to the audit, the reconciled bank balance was less than the office ledgers. Page {page} details the discrepancy. Why were these accounts unreconciled?"   

Caption: SBOA compliance audit reveals a cash balance discrepancy in the {county} {department} accounts. #Indiana #{county}County

Template 8: Unsupported Disbursements
Title: Where are the receipts in {county}?

Spoken Script: "State auditors reviewed the {county} {department} and flagged ${amount} in unsupported disbursements. Page {page} of report {report_id} shows these public funds lacked vendor invoices or receipts. Why were these paid without documentation?"   

Caption: State auditors cite a lack of documentation for {county} County disbursements. Official audit: {report_id}. #Indiana #{county}County

Template 9: Late Fees Charged to Taxpayers
Title: Taxpayers cover late fees in {county}.

Spoken Script: "An official SBOA audit shows {county} County spent ${amount} on credit card late fees and interest. Report {report_id} on page {page} notes that officials did not pay invoice claims on time. Why should public funds cover these penalties?"   

Caption: Audit citation details late fees and interest penalties charged to {county} County accounts. #Indiana #{county}County

Template 10: Nepotism Policy Non-Compliance
Title: A nepotism policy alert in {county} County.

Spoken Script: "State auditors cited {county} County for failing to file annual nepotism certifications. Report {report_id} on page {page} shows the county did not comply with IC 36-1-20.2. Why are these oversight requirements being missed? Read the report on the SBOA portal."   

Caption: State Board of Accounts cites {county} County for nepotism compliance failures under Indiana Code. #Indiana #{county}County

Template 11: The Secret Credit Card Charges
Title: Credit card oversight failures in {county}.

Spoken Script: "SBOA report {report_id} details credit card usage in {county} County's {department}. Investigators noted that several purchases had no itemized receipts or prior approvals. Why were these card limits used without documentation?"   

Caption: Oversight issues with public credit cards cited in {county} County. SBOA report details are online. #Indiana #{county}County

Template 12: The Unresolved Prior Findings
Title: Unresolved audit issues in {county} County.

Spoken Script: "SBOA's latest report for {county} County shows {count} repeat findings from previous audits. These issues with {finding_type} have remained unresolved for over {years} years. Why hasn't the county resolved these compliance concerns?"   

Caption: Repeated audit findings cited in the {county} County compliance report. Details on page {page}. #Indiana #{county}County

Template 13: Over-Budget Spending
Title: Over-budget spending in {county} County.

Spoken Script: "State auditors flagged that {county} County's {fund_name} fund spent ${amount} over its authorized budget limit. Page {page} of SBOA report {report_id} notes this exceeded statutory appropriations. Who authorized these expenditures?"   

Caption: Auditors cite over-budget spending in the {county} {fund_name} fund. #Indiana #{county}County

Local Docket Templates (Require scraped county claims data)
Template 14: The Split-Purchase Detection
Title: Split purchases in {county} County?

Spoken Script: "Look at this timing: local claims show {county} County paid ${amount} to {vendor} across three separate checks in one week. That total falls just under the public bidding threshold. Was this split to avoid competitive bidding? Review the claims below."   

Caption: County claims show sequential check patterns for {vendor} in {county} County. #Indiana #{county}County

Template 15: The Round-Dollar Run
Title: Why these round-dollar payments in {county}?

Spoken Script: "{county} County's claims docket shows a series of payments to {vendor} for exactly ${amount}. No cents, no itemized variation. Is this based on flat retainers or rounded estimates? Look through the county's disbursement records."   

Caption: Repeating round-dollar transactions identified in {county} County claims. #Indiana #{county}County

Template 16: The Weekend Invoices
Title: Weekend transactions in {county} County.

Spoken Script: "A review of {county} County's claims docket shows ${amount} in vendor checks issued on dates that fall on weekends. How are weekend services and invoices tracked and verified? See the transaction log on the county site."   

Caption: Weekend invoice processing dates identified in {county} County claims dockets. #Indiana #{county}County

Template 17: Sudden Vendor Dominance
Title: A new dominant vendor in {county} County?

Spoken Script: "In {year_prev}, {vendor} received ${amount_prev} from {county} County. But this year, their total rose to ${amount}—representing {pct}% of the county's total vendor spending. What drove this sudden increase? Check the claims records."

Caption: Vendor spending concentration trends in {county} County. #Indiana #{county}County

Template 18: Unmapped Ledger Transfers
Title: Unmapped transfers in {county} County.

Spoken Script: "Local claims show {county} County transferred ${amount} from {fund_1} into {fund_2} on {payment_date}. There is no matching authorization in the commissioner meeting minutes. How was this transfer approved?"   

Caption: Inter-fund transfer patterns identified in {county} County. #Indiana #{county}County

Macro and General Finance Templates (Require Gateway budget/AFR data)
Template 19: The Obscure Fund YoY Spike
Title: A spending spike in {county} County's {fund_name}.

Spoken Script: "Gateway budget reports show {county} County's {fund_name} fund rose from ${amount_prev} to ${amount}. That is a {pct}% increase in this account. What is driving this sudden change in {county}? Review the line-item budgets below."   

Caption: Year-over-year spending spikes in {county} County's {fund_name} fund. Budget records are public. #Indiana #{county}County

Template 20: Federal Funding Surpluses
Title: Federal grant spending in {county} County.

Spoken Script: "Official records show {county} County spent ${amount} in federal grant funding on {fund_name} in {year}. But the matching local contributions only totaled ${amount_local}. Why this mismatch? Review the grant schedule on Gateway."   

Caption: Federal award funding allocations and matching patterns in {county} County. #Indiana #{county}County

Template 21: The Missing Annual Reports
Title: Missing transparency reports in {county}?

Spoken Script: "By law, Indiana counties must submit their Annual Financial Reports on Gateway by March 1st. But as of today, {county} County's filing status is listed as missing. Why the delay? Check the SBOA submission log below."   

Caption: Oversight alert: {county} County's Annual Financial Report is listed as missing on Gateway. #Indiana #{county}County

Template 22: High Per-Capita Debt
Title: High per-capita debt in {county} County.

Spoken Script: "Gateway debt reports show {county} County has a total public debt of ${amount}. That amounts to ${debt_per_capita} for every local resident. How does this compare to nearby counties? Review the debt analysis below."   

Caption: Public debt per capita comparisons for {county} County. Data sourced from DLGF debt filings. #Indiana #{county}County

Template 23: The Capital Asset Decline
Title: Declining capital assets in {county} County.

Spoken Script: "{county} County's official asset records show a ${amount} decline in the valuation of county-owned properties. SBOA reports highlight a lack of maintenance records on page {page}. Why are assets losing value? Read the audit."   

Caption: Valuation adjustments and maintenance records for {county} County capital assets. #Indiana #{county}County

Template 24: High Administrative Costs
Title: Administrative payroll spike in {county} County.

Spoken Script: "{county} County spent ${amount} on county commissioner salaries and administrative budgets in {year}. That is a {pct}% increase in overhead while local infrastructure spending fell. What is the business case? Read the budget details below."   

Caption: Administrative payroll patterns in {county} County. #Indiana #{county}County

Template 25: Unpaid Pension Liabilities
Title: Pension liabilities in {county} County.

Spoken Script: "{county} County's pension reporting reveals a ${amount} funding gap for county employee retirement plans. SBOA audits cite a failure to make timely required contributions. How will the county cover this shortfall?"   

Caption: Pension liability trends and contribution metrics in {county} County. #Indiana #{county}County

Production System Architecture and Quality Assurance Gates
To scale programmatic auditing across all 92 Indiana counties without sacrificing accuracy, the system requires automated quality gates and a structured review process.

Stage-Gate Exit Criteria
The production pipeline utilizes a five-stage architecture. Each stage must satisfy specific criteria before advancing:

Stage 1: Ingest Validation

Process: Retrieve files from Indiana Gateway, SBOA, and local county scrapers.   

Exit Criteria: Successful schema validation of the retrieved files. Check for null values on essential fields (e.g., compensation values in Form 100R, report numbers in SBOA files).   

Stage 2: Statistical Filtration

Process: Apply the Hard System Kill List rules to filter out false positives.

Exit Criteria: Remove all category aggregates, rollup entities, and statistical noise on aggregate payroll lines.   

Stage 3: Outlier Computation

Process: Calculate employee salary z-scores, fund YoY variations, and scan SBOA text.   

Exit Criteria: Generate anomaly records that meet the defined taxonomy thresholds.

Stage 4: Automated Narrative Scoring

Process: Calculate the severity and engagement score for each flagged record.

Exit Criteria: Select the top-ranked anomaly to construct a media-optimized script and generate a corresponding human review card.

Stage 5: Human Gatekeeper Approval

Process: Present the anomaly details to a human operator via a structured review card.

Exit Criteria: The operator manually verifies the primary citation and approves the record for production.

Anomaly Cold-Open Scoring Model
When multiple anomalies are flagged within a single county, the system ranks them using a weighted scoring model to select the most engaging and verifiable story:

Severity Score (S)=w 
1
​
 ⋅A 
norm
​
 +w 
2
​
 ⋅R 
type
​
 +w 
3
​
 ⋅D 
contrast
​
 −w 
4
​
 ⋅C 
complexity
​
 
Where:

A 
norm
​
 =min(1.0, 
$500,000
Anomaly Amount
​
 ) (Normalized financial magnitude)   

R 
type
​
  is the source reliability score:

SBOA Special Investigation (I series) = 1.0

[cite: 9, 31]

SBOA Supplemental Compliance (S series) = 0.8

[cite: 37, 38]

Gateway Form 100R Salary Outlier = 0.7

[cite: 5, 6]

Scraped Local Claims Docket = 0.5 (Requires manual verification)   

D 
contrast
​
  is the contextual contrast factor (e.g., the ratio of the target salary to the county median).   

C 
complexity
​
  is an asset complexity penalty (deducts points for complicated accounting items like depreciation schedules or pension actuarial changes).   

w 
1
​
 ,w 
2
​
 ,w 
3
​
 ,w 
4
​
  are model weights: w 
1
​
 =0.35, w 
2
​
 =0.30, w 
3
​
 =0.25, w 
4
​
 =0.10.

Human Review Card Interface Design
The human review card must present all necessary context within a single screen, allowing an operator to evaluate and approve an anomaly in under 60 seconds:

================================================================================
AUDIT PIPELINE REVIEW CARD                                    ID: RF-2025-47-00122
================================================================================
[COUNTY]: DEARBORN COUNTY, IN         [FISCAL YEAR]: 2024
[FLAG TYPE]: SBOA_FINDING (Category: Special Event Deficit)

--------------------------------------------------------------------------------
PRIMARY TRANSACTION DETAILS
--------------------------------------------------------------------------------
* Entity: Municipal Utilities / City of Lawrenceburg
* Anomaly Value: $390,236.00 (Rodeo Event Loss funded by Rate-Payers)
* Detail: $148,394.00 spent on temporary fabric building; virtual reality 
  headsets purchased; contract with famous rodeo celebrity.

--------------------------------------------------------------------------------
[I[<35;63;44MVERIFIED EVIDENCE PROVENANCE (SBOA WebReports)
--------------------------------------------------------------------------------
* Source: Indiana SBOA Supplemental Compliance Report
* Report ID: B54685
* Page Number: Page 14 (Results and Comments Section)
* Direct Quote: "A review of the financial transactions associated with the 
  events indicated that the rodeo operated at a loss. As a result, the loss was 
[<35;65;44M[<35;66;44M  covered by the rate-payers through funds generated in normal operations."
[<35;67;44M* Verification Link: https://www.in.gov/sboa/WebReports/B54685.pdf

[<35;68;44M--------------------------------------------------------------------------------
[<35;69;44MAUTOMATED SCRIPT TEXT GENERATION
--------------------------------------------------------------------------------
[<35;72;44M"An official state audit shows Dearborn County's Municipal Utilities spent 
[<35;75;44Mover $390K on a professional rodeo. The event operated at a loss, and rate-payers
[<35;76;44Mcovered the difference. Page 14 of SBOA report B54685 details the costs, 
[<35;77;44M[<35;78;44Mincluding a virtual reality headset and a fabric building. Why did utility accounts 
[<35;79;44Mcover a rodeo loss?"
[<35;80;44M
[<35;81;44M--------------------------------------------------------------------------------
[<35;82;44MDECISION ACTIONS (Operator Input Required)
[<35;83;44M--------------------------------------------------------------------------------
[<35;84;44M[1] APPROVE AND QUEUE FOR PRODUCTION
[2] REJECT AND DISCARD RECORD
[3] REQUEST MANUAL AUDIT INVESTIGATION
[<35;86;44M================================================================================
Script Packaging and Channel Cadence
The system uses specific criteria to determine the publication format for each verified anomaly:
[<35;87;44M
Short-Form Content (30–60 Seconds): Standard format. Used for single, highly focused findings with clear visual evidence (e.g., a high salary outlier, credit card late fees, or a missing annual report).   

Long-Form Content (8–12 Minutes): Produced only when an audit yields 3 or more independent findings for a single county (e.g., a SBOA special investigation detailing multiple unauthorized expenditures, cash shortages, and credit card abuse simultaneously).   
[<35;88;44M
Weekly Operational Schedule:

Monday to Tuesday: Programmatic ingestion of updated Gateway databases and SBOA reports.   

Wednesday: Run outlier calculations, filter out false positives, and populate the human review queue.

[<0;88;44MThursday: Human review and script verification.

Friday: Render video assets and queue them for weekend publication.

Competitive and Formatting Landscape
Analyzing the current landscape of public-sector accountability content reveals key visual and narrative formats that can be adapted for the Indiana market.

Marketplace Analysis
[<0;88;44mOn social media, government accountability content generally falls into three main categories:

Local Agency Watchdogs (e.g., Florida DOGE, Municipal Audit Channels): Inspired by state-level efficiency initiatives, these channels highlight waste, overhead expenses, and local spending increases. They rely heavily on showing official documents on-screen and comparing local figures to peer benchmarks.   

First-Person Public Audits (e.g., Citizen Watchdog, Public Ledger Activists): These creators focus on physical audits of public offices and local compliance meetings. While they generate high engagement, they require boots-on-the-ground reporting and carry higher legal risks.   

Faceless Accountability Channels: These channels use text-on-screen, automated narrators, and highlighted public records to explain municipal budgets and audits. This approach is highly scalable and keeps the focus directly on verified public data.   

Indiana's county-level market remains largely open. Local coverage of SBOA findings is typically limited to traditional print media, leaving a significant gap for engaging, short-form video content based on public records.   

Story Formats for Productization
These five production formats are designed to adapt common public-records findings into engaging video narratives:

1. The Executive Salary Comparison
Data Required: Gateway Form 100R, peer county means, county-wide median wage.   

Format: 30–60 second vertical video.   

Narrative Flow: State a county official's salary, highlight that it exceeds peer averages, compare it to the local median household income, and ask an open-ended question about the variation.   

2. SBOA Audit Highlights
Data Required: SBOA Supplemental Compliance ("S" series) PDF.   

Format: 30–60 second vertical video.

Narrative Flow: Open with a specific audit citation (e.g., credit card late fees or unsupported travel expenses), show the official PDF page on-screen, and question the lack of oversight.   

3. Special Investigation Profiles
Data Required: SBOA Special Investigation ("I" series) PDF, local news reports.   

Format: 1-minute vertical video or 8–12 minute horizontal video.   

Narrative Flow: Detail a major compliance investigation (e.g., unauthorized checks or personal use of public vehicles), show the SBOA "Summary of Charges" affidavit, and list the verified findings.   

4. Obscure Fund Spikes
Data Required: Gateway Detailed Disbursements, historical fund trends.   

Format: 45-second vertical video.

Narrative Flow: Highlight a sharp spending increase in a restricted local fund (e.g., Jail Commissary), rule out standard matching grants, and ask for clarification on the spending increase.   

5. Local Transparency Alerts
Data Required: Gateway Submission Log.   

Format: 30-second vertical video.

Narrative Flow: Note that a county has missed its legal filing deadline for financial reports, display the missing status on-screen, and emphasize the importance of timely public disclosures.   

Technical Appendices
Appendix A: Production Ingestion Priority and Field Limits
Public Platform    Document / Dataset Type    Fields Ingested    Known Field Exclusions    Unlocks Specific Flags    Scrape / API Strategy    Priority
Indiana Gateway

[cite: 1, 15]

Annual Financial Report (AFR)
Algorithmic Auditing of Public Finance: An Operational Blueprint for Indiana Local Government Financial Oversight
Executive Summary
This report establishes an operational blueprint for the "ReClaw / county auditor" pipeline, a platform built to automate the auditing of public financial ledgers across Indiana's 92 counties. The current system struggles with high noise levels, generating 60 to 90 unwatchable anomalies per county. These alerts are primarily driven by false-positive vendor identification on aggregate ledger lines (such as "Governmental Activities") and misapplied statistical models.   

The primary recommendation to resolve these issues is a shift from unsupervised statistical anomaly detection to a structured, multi-pass deterministic framework. This approach combines data from the Indiana State Board of Accounts (SBOA) with Certified Employee Compensation Reports (Form 100R).   

                                  [ Raw Financial Ledger Ingest ]
                                                 |
                                                 v
                                    [ Programmatic Filters ]
                                 (Discard aggregate category codes
                                  and rollup-vendor associations)
                                                 |
                                                 v
                                  [ Deterministic Anomaly Engine ]
                              (Compute cohort-matched salary z-scores,
                               YoY fund spikes, & SBOA text patterns)
                                                 |
                                                 v
                                      [ Human Review Card ]
                                  (60-second manual validation
                                   of primary citation provenance)
                                                 |
                                                 v
                                     [ High-Retention Video ]
                                  (Auto-generate scripted narration
                                   citing verified SBOA audit IDs)
By filtering out aggregate accounts (such as "Other Services and Charges" or "WATER") and implementing cross-source validation against county commissioner claims dockets, the pipeline can isolate verifiable public finance anomalies. These findings can then be paired with clear, peer-county comparisons to produce engaging and legally defensible public interest narratives.   

Technical Analysis of Indiana County Public Finance Data Sources
Programmatic auditing of local finances in Indiana requires a clear understanding of the state's accounting systems and public data portals. The pipeline relies on a mix of state-administered data warehouses, regulatory audit repositories, local administrative records, and federal databases.   

Ingestion Source Inventory and Constraints
To prevent false positives, the ingestion engine must map the specific fields, limits, and collection methods of each targeted platform.   

1. Indiana Gateway for Government Units (gateway.ifionline.org)
Indiana Gateway serves as the central repository for local government financial reporting. It is administered by six state agencies, including the Department of Local Government Finance (DLGF) and the State Board of Accounts (SBOA).   

Annual Financial Report (AFR): This report provides annual receipts, disbursements, and fund balances on a cash basis. For cities and counties, the Detailed Disbursements dataset contains the following fields: year, county_code, unit_name, fund_name, disburse_name, and amount.   

Data Boundary: This dataset contains no vendor payee names, payment dates, invoice IDs, or purchase order numbers. The disburse_name field refers to standard accounting categories (e.g., "Other Services and Charges" or "Office Supplies"), not private companies.   

Township Exception: Unlike cities and counties, townships are required to upload vendor-level disbursements under the Disbursements by Vendor (Townships Only) application. This report includes payee names and annual totals, but does not provide transaction dates or invoice numbers.   

Employee Compensation (Form 100R): Legally mandated by IC 5-11-13-1, this certified report lists the names, business addresses, departments, job titles, and total calendar-year compensation of all public employees.   

Data Boundary: Form 100R records represent aggregate annual compensation, which can make it difficult to distinguish regular wages from overtime, retroactive pay, or multi-role adjustments. The dataset is uploaded in CSV format and includes fields such as Year, Last, First, Middle, Dept, and compensation.   

2. Indiana State Board of Accounts (audit.sboa.in.gov / in.gov/sboa)
The SBOA audits all public offices and entities receiving public funds. Its public database can be systematically queried via the SBOA Audit Report Filings App.   

Audit Frequency: Under IC 5-11-1-25, audits are conducted annually for entities with over $750,000 in federal expenditures or outstanding bond debt. Other entities are audited every two to four years based on SBOA's risk-assessment models.   

Confidentiality Boundary: SBOA Directive 2014-1 mandates that draft audit reports, exit conference findings, and related discussions remain strictly confidential. Information cannot be shared publicly until the final report is officially filed and published on the SBOA website.   

3. Local County Administrative Records (Claims Dockets and AP Warrant Lists)
Under IC 36-2-6-3, counties must present claims dockets to the Board of County Commissioners for approval prior to disbursement.   

Data Quality: Unlike Gateway's aggregate entries, local claims dockets contain transaction-level fields: vendor_name, payment_date, check_number, invoice_amount, and department.   

Access Constraints: These dockets are rarely centralized at the state level. They must be collected by scraping individual county commissioner meeting minutes or auditor portals. Document formats vary from clean PDFs to scanned, non-searchable image dockets.   

4. Auxiliary Databases
ProPublica Nonprofit Explorer API: Provides tax returns (Form 990) and audit filings for non-profit entities. This is useful for analyzing county-funded volunteer fire departments or local development corporations.   

DLGF Budget Orders and Beacon/GIS Systems: Provides property tax rates, levies, net assessed values, and parcel ownership details. These records are useful for contextualizing spending shifts against the county's tax base.   

Ingestion Source Priority Matrix
Source Name    Primary Fields    Red-Flags Unlocked    Scrape/API Method    Ingestion Priority
SBOA Report Database

[cite: 21, 36]

report_number, unit_name, file_date, report_type (B, I, S series)

Cash shortages, credit card abuse, nepotism, undocumented spending

Traversing the SBOA Audit Report Filings App using HTTP search parameters.

Level 1 (High reliability, verified findings)

Gateway Form 100R

[cite: 5, 6]

year, last_name, first_name, department, job_title, compensation

[cite: 6, 19]

High salary outliers, multi-line compensation

[<35;91;43MPost requests to public search endpoints.
[<35;91;42M
[<35;92;42MLevel 1 (Consistent statewide coverage)
[<35;94;41M
[<35;95;41MCounty Claims Dockets
[<35;96;40M
[<35;97;39M[cite: 7, 8]
[<35;99;38M
[<35;100;38Mvendor_name, check_date, check_number, amount, department
[<35;105;35M[<35;107;34M
[cite: 25, 26]
[<35;109;32M[<35;110;32M[<35;111;32M
[<35;111;31MSplit purchases, sequential invoices, round-dollar payments
[<35;112;31M
Scrape county auditor portals for meeting minutes and PDF dockets.
[<35;112;30M
Level 2 (Detailed transaction data, lower coverage)

Gateway AFR

[cite: 2, 18]

year, unit_name, fund_name, disburse_name, amount

[cite: 2, 3]

Obscure fund spikes, cash-to-budget imbalances

Bulk download of pipe-delimited text files (`    
`).
[<35;111;30M
ProPublica Nonprofit API

[cite: 14, 30]

[<35;110;30Mein, organization_name, revenue, expenses, officer_comp

[<35;109;30M[cite: 14, 30]
[<35;108;31M
Financial health of county contractors
[<35;107;31M[<35;106;32M
REST API queries using organization name or EIN.
[<35;105;32M
Level 3 (Contextual validation only)

  
Publishable Red-Flag Taxonomy and Quality Gates
The pipeline requires a strict validation taxonomy to ensure the accuracy of generated scripts and preserve the fair-report privilege.   
[<35;104;32M
Core Flag Taxonomy
1. Named Public Salary Shocks
Definition: Annual compensation on Form 100R that stands out as a statistical outlier compared to peer counties, or represents an extreme multiple of the county's median wage.   

Minimum Evidence: The target salary C 
i
​
  must exceed a z-score of 3.0 within its job-title cohort across all 92 counties, or exceed the county's household median wage W 
m
​
  by a factor of 4:

C 
i
​
 >μ 
cohort
​
 +3σ 
cohort
​
 ∨C 
i
​
 >4×W 
m
​
 
False-Positive Traps:

Combining different employees with the same name (e.g., "William Miller") in larger counties.

Misinterpreting retroactive pay or combined compensation for dual-role positions (such as a Sheriff acting as a Jail Commander).   

On-Screen Evidence: Highlighted cells on SBOA Form 100R, alongside a bar chart comparing the salary to peer-county averages.   

Kill Rules: Discard if the title is "Judge" or "Prosecutor" (whose salary tiers are set by state statute and reimbursed by the State of Indiana), or if the position is a contracted medical role.

2. Dual-Line Compensation (Double-Dipping)
Definition: The occurrence of identical employee names across multiple compensation rows within the same county unit on Form 100R, suggesting multiple salaries are being paid to one individual.   

Minimum Evidence: Exact match on first_name and last_name within a single county_code across distinct department entries, where the sum of compensation C 
total
​
 ≥$100,000 and the secondary salary C 
secondary
​
 ≥$20,000.   
[<35;98;32M
[<35;95;32M[<35;91;32MFalse-Positive Traps: Common names within populated counties (e.g., Marion, Lake). High school coaches or seasonal election staff who hold multiple minor roles.   
[<35;67;32M[<35;62;31M
[<35;60;31MOn-Screen Evidence: Side-by-side rows from the SBOA Gateway Employee Lookup interface, highlighted and linked.   
[<35;59;31M
[<35;55;31MKill Rules: Discard if the secondary job title contains terms like "Seasonal," "Part-Time," "Poll Worker," "Temporary," "Board Member," or "Advisory".   
[<35;48;32M[<35;46;32M[<35;43;32M
[<35;41;33M3. Structured Split-Purchases (Bid-Threshold Avoidance)
[<35;38;33MDefinition: Dividing a single purchase into multiple transactions to stay below the public bidding threshold of $150,000, or the small-purchase quote threshold of $50,000, within a short timeframe.
[<35;34;34M[<35;33;34M[<35;32;34M[<35;31;34M
[<35;29;34MMinimum Evidence: A sequence of n payments p to vendor v within a 30-day window t, where each payment falls within a narrow percentage band below the statutory threshold T:

0.90≤ 
T
p 
i
​
 
​
 <1.0
[<35;31;35M[<35;32;36M[<35;33;36M[<35;34;37MFalse-Positive Traps: Routine progress payments for documented construction projects or recurring utility bills.   
[<35;37;38M[<35;38;38M
On-Screen Evidence: Rows from a local claims docket displaying successive checks issued to the same vendor on adjacent days.   
[<35;39;38M
Kill Rules: Discard if the source is aggregate Gateway disbursement data, as it lacks vendor details and transaction timestamps. This analysis must only run on scraped local claims dockets.   

[<35;40;38M4. Round-Dollar / Identical Sequential Payments
Definition: A sequence of disbursements to a private vendor that are exact multiples of $1,000, or contain identical decimal values, suggesting a lack of itemized invoicing.   
[<35;41;38M
[<35;42;38MMinimum Evidence: Three or more consecutive payments p 
i
​
[<35;43;38M  to a vendor where:

p 
i
[<35;44;38M​
[<35;45;38M (mod1000)=0for p 
[<35;46;38M[<35;46;37Mi
[<35;47;37M​
 ≥$5,000
[<35;48;37M[<35;49;37MFalse-Positive Traps: Fixed-rate lease agreements, monthly retainer fees, or standardized software licensing agreements.   

On-Screen Evidence: Zoomed-in view of a county claims registry showing repeating, identical round-dollar payouts.   
[<35;50;37M
[<35;51;37MKill Rules: Discard if the payee is a financial institution, utility provider, or intergovernmental fund transfer.   

5. SBOA Prior Audit Findings and Special Investigations
Definition: Written citations in Supplemental Compliance Reports or Special Investigations detailing misappropriation, unsupported spending, or internal control failures.   
[<35;52;37M
Minimum Evidence: Presence of a high-severity regulatory phrase matched against an SBOA finding database.   

False-Positive Traps: Misinterpreting minor compliance errors (e.g., submitting an annual report three days late) as a major financial deficit.   
[<35;53;37M
[<35;53;36MOn-Screen Evidence: Sourced PDF pages from WebReports showing the "Audit Results and Comments" section, with key sentences highlighted.   
[<35;54;36M
Kill Rules: None. This is the most reliable narrative category, provided the citation references the official SBOA report ID and page.   
[<35;56;36M[<35;57;36M
6. Fund-Specific YoY Expenditure Spikes
Definition: Sudden spending increases in obscure local county funds, such as "Jail Commissary," "Probation User Fees," or "Cumulative Capital".   
[<35;58;36M[<35;59;36M
[<35;60;36MMinimum Evidence: A YoY change in fund-level disbursements D that exceeds 3σ of the historical fund trend:
[<35;61;36M
ΔD 
[<35;62;36My,y−1
[<35;63;36M​
 >1.5×D 
[<35;64;36My−1
​
 where D 
y−1
​
 ≥$50,000
False-Positive Traps: Spikes driven by major capital projects funded by state or federal grants.   

On-Screen Evidence: Line graphs showing stable baseline spending followed by a sharp vertical spike.   

Kill Rules: Discard if the spike is offset by an equivalent increase in federal grant revenues or documented bond proceeds within the same fiscal year.   

7. Federal vs. Local Spending Mismatches
Definition: Using restricted local funds to cover matching requirements for federal grants without authorization, or spending federal funds outside approved program guidelines.   

Minimum Evidence: SBOA audit findings confirming unauthorized local fund usage for federal match requirements.   

False-Positive Traps: Legitimate, pre-approved inter-fund transfers that have been authorized by the county council.   

On-Screen Evidence: A split-screen comparison of the federal grant guidelines against the actual local disbursement voucher.   

[<35;67;36MKill Rules: Discard if the SBOA report indicates the transfer was legally resolved or corrected during the exit conference.   
[<35;70;36M
[<35;71;36M8. Transparency and Reporting Failures
Definition: A county's failure to file mandatory financial disclosures (AFR or Form 100R) on Gateway within the legally required timeline.   
[<35;74;36M
Minimum Evidence:

[<35;75;36MCurrent Date>Statutory Deadline+30 dayswith submission_status=Pending
False-Positive Traps: Minor administrative extensions granted by the state but not updated in the public tracking portal.   

On-Screen Evidence: A red highlight on the Gateway Submission Log interface showing a missing annual report.   

Kill Rules: Discard if the county has filed the necessary reports but they are temporarily locked for corrections.   

Hard System Kill List
The following automated red-line rules must be enforced during the pre-processing stage to eliminate statistical noise:

Target Pattern    Technical Filter Rule    Mathematical Condition    Why It Must Be Discarded
Category-Only Aggregate Sums    
Discard if disburse_name matches standard account headers.

disburse_name ∈ {"Other Services and Charges", "Other Capital Outlays", "Supplies"}.

These represent broad accounting categories, not payments to individual vendors.

Rollup Entities    
Discard if the entity name represents internal ledger balancing.

disburse_name or ent_name ∈ {"Governmental Activities", "Transfers Out", "Internal Service Funds"}.

These are internal fund transfers, not external cash transactions.

Pure Benford's Law Outliers    Block anomalies based solely on Benford's Law first-digit distribution.    χ 
Benford
2
​
 >threshold (without named ledger references).    Benford's Law is a diagnostic tool, not direct evidence of public fund mismanagement.
Low-Dollar Seasonal Compensation    
Discard if the total annual compensation is below $15,000.

compensation < $15,000 on Form 100R.

This prevents flagging minor pay adjustments for seasonal or part-time staff.

Payroll Aggregate Outliers    
Discard anomalies that fire on aggregate payroll lines.

disburse_name ∈ {"Salaries and Wages", "Employee Benefits"}.

These totals scale naturally with cost-of-living adjustments and contracts.

  
Data Extraction, Vendor Normalization, and Provenance Processing
Maintaining a high publication volume across multiple counties requires structured data ingestion pipelines. Ingestion engines must standardize disparate sources, convert unstructured PDFs into structured records, and maintain clear provenance for compliance.   

Unstructured SBOA PDF Extraction
To convert SBOA PDF findings into structured data, the parser must target specific section layouts within the documents.   

                     [ Ingest SBOA Supplemental PDF ] 
                                    |
                                    v
          [ Segment PDF by Heading: "Audit Results and Comments" ]
                                    |
                                    v
          [ Isolate Text blocks containing Statutory Citations ]
                                    |
                                    v
            [ Extract Entity, Amount, Violation, and Page Metadata ]
                                    |
                                    v
                    [ Validate and Structure into Schema ]
The parsing utility uses a regular expression engine to isolate the "Results and Comments" sections. It uses a two-pass parser to extract entities, financial values, and citations:   

Python
import re

def parse_sboa_narrative(pdf_text: str, report_id: str) -> list:
    # Isolate SBOA "Results and Comments" section
    section_match = re.search(
        r"(AUDIT RESULTS AND COMMENTS|SPECIAL INVESTIGATION RESULTS AND COMMENTS)(.*?)(EXIT CONFERENCE)", 
        pdf_text, 
        re.DOTALL | re.IGNORECASE
    )
    if not section_match:
        return []
    
    findings_block = section_match.group(2)
    extracted_findings = []
    
    # Locate instances of financial values and nearby statutory citations
    citation_pattern = r"(IC\s+\d+-\d+-\d+-\d+(?:\(.\))?)"
    amount_pattern = r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"
    
    paragraphs = findings_block.split("\n\n")
    for index, paragraph in enumerate(paragraphs):
        amounts = re.findall(amount_pattern, paragraph)
        citations = re.findall(citation_pattern, paragraph)
        
        if amounts and citations:
            findings_data = {
                "report_id": report_id,
                "paragraph_index": index,
                "statutory_citation": citations[0],
                "financial_values": [float(amt.replace(",", "")) for amt in amounts],
                "context_snippet": paragraph[:250].strip()
            }
            extracted_findings.append(findings_data)
            
    return extracted_findings
Cross-Source Entity Resolution and Vendor Normalization
To resolve inconsistent vendor naming across county claims dockets, the ingestion engine uses a string-matching utility. This utility handles typical variations in vendor entries:   

Python
import re

def normalize_vendor(name: str) -> str:
    if not name:
        return "UNKNOWN_ENTITY"
    
    # Standardize casing and strip whitespace
    name = name.upper().strip()
    
    # Remove common corporate suffixes
    name = re.sub(r'\b(INC\b\.?|LLC\b\.?|CORP\b\.?|CO\b\.?|LTD\b\.?|L\.P\.?|INCORPORATED|LIMITED LIABILITY COMPANY)', '', name)
    
    # Standardize spaces and punctuation
    name = re.sub(r'[^A-Z0-9\s&]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Hardcoded entity resolution dictionary
    resolution_map = {
        "AMAZON CAPITAL SERVICES": "AMAZON",
        "DUKE ENERGY INDIANA": "DUKE ENERGY",
        "CDW GOVERNMENT": "CDW-G",
        "BOYCE SYSTEMS": "A_E_BOYCE",
    }
    
    return resolution_map.get(name, name)
By standardizing these names, the system can run a cross-source validation step:

County AP Claim Total (Scraped)⟺Gateway Grant/Contract Disclosures⟺ProPublica Nonprofit Explorer (Form 990) [cite: 7, 18, 30]
Video-Optimized Red-Flag JSON Schema
This structured data model represents a validated anomaly profile. It is designed to provide all necessary details for automated script generation and human compliance review:

JSON
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RedFlagRecord",
  "type": "object",
  "required": [
    "flag_id",
    "county",
    "fips_code",
    "fiscal_year",
    "flag_type",
    "severity_score",
    "primary_actor",
    "anomaly_amount",
    "provenance"
  ],
  "properties": {
    "flag_id": {
      "type": "string",
      "pattern": "^RF-[0-9]{4}-[0-9]{2}-[0-9]{5}$"
    },
    "county": {
      "type": "string"
    },
    "fips_code": {
      "type": "string",
      "pattern": "^18[0-9]{3}$"
    },
    "fiscal_year": {
      "type": "integer"
    },
    "flag_type": {
      "type": "string",
      "enum": [
        "SALARY_SHOCK",
        "DOUBLE_COMPENSATION",
        "SPLIT_PURCHASE",
        "ROUND_DOLLAR",
        "SBOA_FINDING",
        "FUND_SPIKE",
        "FEDERAL_MISMATCH",
        "TRANSPARENCY_GAP"
      ]
    },
    "severity_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 10.0
    },
    "primary_actor": {
      "type": "object",
      "required": ["entity_name", "entity_type"],
      "properties": {
        "entity_name": { "type": "string" },
        "entity_type": { "type": "string", "enum": ["INDIVIDUAL", "VENDOR", "FUND", "DEPARTMENT"] },
        "job_title": { "type": "string" }
      }
    },
    "comparison_metrics": {
      "type": "object",
      "properties": {
        "peer_mean": { "type": "number" },
        "county_median_wage": { "type": "number" },
        "percentage_deviation": { "type": "number" }
      }
    },
    "anomaly_amount": {
      "type": "number"
    },
    "provenance": {
      "type": "object",
      "required": ["source_platform", "report_identifier", "page_number", "url"],
      "properties": {
        "source_platform": { "type": "string", "enum": ["GATEWAY_AFR", "GATEWAY_100R", "SBOA_REPORTS", "COUNTY_AP_DOCKET"] },
        "report_identifier": { "type": "string" },
        "row_index_or_paragraph": { "type": "string" },
        "page_number": { "type": "integer" },
        "url": { "type": "string", "format": "uri" },
        "extracted_text_quote": { "type": "string" },
        "governing_statute": { "type": "string" }
      }

