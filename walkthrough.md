# Walkthrough - Aarsha Nidhi Banking Software

## Changes Summary: Independent Account Opening Date vs. Opening Balance Date & RD #1 Correction

### 1. Separation of Account Opening Date and Opening Balance Date
A fundamental distinction has been implemented across the entire software between:
- **A/c Opening Date (`created_at` / `open_date`)**: The contractual date when the customer registered or opened the account (used for tenure calculations, maturity date projections, passbook/certificate headers, and account masters).
- **Opening Balance Date (`op_bal_date` / `voucher_date` / `tx_date`)**: The date when opening funds were deposited / recorded into the accounting ledger (used for Journal Vouchers, Day Book, Cash Book, Bank Book, Trial Balance, Profit & Loss, and Balance Sheet date filtering).

---

### 2. UI & Backend Implementation Across Modules

#### A. Customer Management Module
1. **Tab 1 (Register Customer)**:
   - Added 3 distinct date pickers:
     - **Registration Date**: For customer KYC / master records.
     - **A/c Opening Date**: For SB, FD, RD, Gold Loan, or Personal Loan account creation.
     - **Opening Balance Date**: For the initial funding JV, Cash Book, and Bank Book entries.
2. **Tab 3 (Edit Customer)**:
   - **Section 4 (Savings Bank)**: Separate inputs for `A/c Opening Date` and `Opening Balance Date`. Updates both `sb_accounts.created_at` and linked opening JV/transactions.
   - **Section 5 (Fixed Deposits)**: Separate inputs for `A/c Opening Date` and `Opening Balance Date`. Updates `fixed_deposits.created_at` and opening JV/Bank Book/Cash Book entries.
   - **Section 6 (Recurring Deposits)**: Separate inputs for `A/c Opening Date` and `Opening Balance Date`. Updates `recurring_deposits.created_at` and opening JV/Bank Book/Cash Book entries.

#### B. Savings Bank Module (SB)
- **Tab 1 (Open SB)**: Added separate `sb_open_date` and `sb_op_bal_date`.
- **Tab 5 (Edit SB)**: Added `edit_sb_op_date` input. Synchronizes `sb_accounts.created_at` with opening date and linked transactions/JVs with opening balance date via `update_sb_account_details`.

#### C. Fixed Deposits Module (FD)
- **Tab 1 (Open FD)**: Added separate `fd_open_date` and `fd_op_bal_date`.
- **Tab 5 (Edit FD)**: Added `edit_fd_op_date` input. Invokes `update_fd_account_details(..., new_created_date=created_str, new_op_bal_date=op_bal_str, new_maturity_amount=final_fd_mat)` to synchronize all ledger entries and books.

#### D. Recurring Deposits Module (RD)
- **Tab 1 (Open RD)**: Added separate `rd_open_date` and `rd_op_bal_date`.
- **Tab 6 (Edit RD)**: Added separate `edit_created` (A/c Opening Date) and `edit_op_bal_date` (Opening Balance Date). Invokes `update_rd_account_details(..., new_created_date=edit_created_str, new_op_bal_date=edit_op_bal_str)`.

---

### 3. Database Layer (`database.py`)
- Updated functions to accept `new_op_bal_date=None` and `op_bal_date=None`:
  - `update_sb_account_details` & `create_or_link_sb_opening`
  - `update_fd_account_details` & `create_or_link_fd_opening`
  - `update_rd_account_details` & `create_or_link_rd_opening`
- Backwards compatible: defaults `new_op_bal_date` to `new_created_date` if omitted.

---

### 4. Data Migration & Correction for RD #1
- **Customer**: VANDYA OMPRAKASH (Customer #65 / `RD-01641028`)
- **A/c Opening Date (`created_at`)**: `10-03-2022` (Preserved intact)
- **Opening Balance Date**: Updated to `01-04-2023` in Opening Journal Voucher #1214 and Bank Book entry #1.
- **Balance**: ₹5,000.00 debit AST-102 (Union Bank of India), credit LIA-103 (RD Deposits Control).
- Bank Book re-sequenced and verified.

---

## Verification Results
- **Syntax and Import Checks**: `.\.venv\Scripts\python -c "import database, app, pdf_generator; print('PASSED')"` completed with 0 errors.
- **Database Consistency Verification**:
  - `recurring_deposits` (rd_id=1): `created_at = '2022-03-10'`, `collected_balance = 5000.0`, `status = 'CLOSED'`.
  - JV #1214: `voucher_date = '2023-04-01'`, `AST-102 (Dr 5000.0) / LIA-103 (Cr 5000.0)`.
  - Bank Book #1: `date = '2023-04-01'`, `debit_amount = 5000.0`.
