# Walkthrough - Aarsha Nidhi Banking Software

The Aarsha Nidhi Banking Software is a robust, double-entry banking system built using Streamlit, SQLite, Plotly, and ReportLab. It has been successfully implemented using a clean, modular architecture.

## Implementation Details

The codebase is organized as follows:
- [`database.py`](file:///C:/Users/vaish/.gemini/antigravity/scratch/aarsha-nidhi-banking/database.py): Handles the SQLite connection, schema initialization, auto-migration of missing columns, default accounts injection (32 default accounting heads), balance lookup functions, voucher generators, and automated double-entry journal voucher (JV) posting.
- [`pdf_generator.py`](file:///C:/Users/vaish/.gemini/antigravity/scratch/aarsha-nidhi-banking/pdf_generator.py): Implements clean, professional ReportLab PDF layout generation for ledger print books, cash/bank/journal vouchers, and FD/RD certificates.
- [`app.py`](file:///C:/Users/vaish/.gemini/antigravity/scratch/aarsha-nidhi-banking/app.py): The complete monolithic entry point containing all Streamlit views (Dashboard, Customer, KYC, SB, FD, RD, Chart of Accounts, Cash Book, Bank Book, JVs, Admin Record Editor, Statements, Reports, and Interest calculation), routing logic, sidebar configurations, custom linear-gradient styling, and backup/restore controls.
- [`requirements.txt`](file:///C:/Users/vaish/.gemini/antigravity/scratch/aarsha-nidhi-banking/requirements.txt): Lists all necessary third-party Python modules.

## Completed Missing Functionality

### 1. Interactive Plotly Charts in Reports
Added the complete set of interactive graphs:
- **Customer Registration Trend**: Line chart tracking customer registration dates.
- **Account Distribution**: Pie chart illustrating the proportions of SB, FD, and RD accounts.
- **SB Account Balances**: Bar chart displaying account numbers and current balances.
- **FD Maturity Distribution**: Bar chart presenting Fixed Deposit IDs and estimated maturity values.
- **RD Installment Progress**: Stacked bar chart comparing paid installments vs remaining ones.

### 2. Savings Bank (SB) Interest Calculation
Implemented the periodic SB interest calculation module:
- Computes interest as: `Balance * (Interest Rate / 100) * (Period in Days / 365)`
- Defaults to a rate of 3.5% p.a. as per database configurations.
- Shows a preview table of all accounts, names, current balances, and calculated interest.
- Posts a consolidated automated Journal Voucher (debiting Interest Paid `EXP-101`, crediting SB Deposits Control `LIA-101`).
- Sequentially credits each active SB account balance and inserts interest credit transaction logs.

### 3. Strict Non-Negative Balance Enforcement & Detailed Capital Accounts
Implemented comprehensive asset safety and compliance rules:
- **Cash Book Checks**: Blocks payment/withdrawal transactions if they exceed the available physical Cash in Hand (`AST-101`). Checks corresponding bank account balances during cash receipts to prevent bank ledger deficits.
- **Bank Book Checks**: Blocks bank deposits (from cash) and bank-to-bank transfers if the funding source has insufficient funds. Blocks bank withdrawals exceeding the selected bank's current ledger balance.
- **Manual Journal Vouchers Validation**: Evaluates manual JV postings. Blocks JVs where the credited account is an asset (Cash/Bank) and the transaction amount exceeds the current asset balance.
- **Detailed Share Capital Accounts**: Groups and displays Equity entries in the Balance Sheet individually based on the transaction particulars/narration (e.g. tracking individual capital contributions), while consolidating Union Bank and SBI balances as single overall Asset rows.

## Verification Results

### Automated Verification
Compiling code using the virtual environment interpreter compiled successfully with exit code 0:
```powershell
.venv\Scripts\python.exe -m py_compile database.py pdf_generator.py views_core.py views_accounting.py app.py
```

Database schema verified successfully:
```powershell
.venv\Scripts\python.exe -c "import database; print('Default accounts count:', database.run_query('SELECT COUNT(*) FROM chart_of_accounts')[0][0])"
# Output: Default accounts count: 32
```

## Running the Application

To run the banking software, open a PowerShell terminal in the project directory and execute:
```powershell
.venv\Scripts\streamlit run app.py
```
> [!TIP]
> Use the default admin credentials to login:
> - **Username**: `admin`
> - **Password**: `admin123`
