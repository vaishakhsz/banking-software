import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

# ============== PAGE CONFIG ==============
st.set_page_config(
    page_title="Simple Banking System",
    page_icon="🏦",
    layout="wide"
)

# ============== INITIALIZE SESSION STATE ==============
def init_session_state():
    if 'accounts' not in st.session_state:
        st.session_state.accounts = {
            'SAVINGS': {'balance': 0.0, 'transactions': []},
            'CURRENT': {'balance': 0.0, 'transactions': []},
            'FD': {'balance': 0.0, 'transactions': [], 'maturity_date': None, 'interest_rate': 7.0},
            'DAILY_COLLECTION': {'balance': 0.0, 'transactions': [], 'daily_limit': 50000.0}
        }
    if 'account_counter' not in st.session_state:
        st.session_state.account_counter = 1001

init_session_state()

# ============== HELPER FUNCTIONS ==============
def get_account_type(account_id):
    """Map account ID to account type"""
    if account_id.startswith('SAV'):
        return 'SAVINGS'
    elif account_id.startswith('CUR'):
        return 'CURRENT'
    elif account_id.startswith('FD'):
        return 'FD'
    elif account_id.startswith('DC'):
        return 'DAILY_COLLECTION'
    return None

def generate_account_id(acc_type):
    """Generate account number based on type"""
    st.session_state.account_counter += 1
    prefix = {
        'SAVINGS': 'SAV',
        'CURRENT': 'CUR',
        'FD': 'FD',
        'DAILY_COLLECTION': 'DC'
    }
    return f"{prefix[acc_type]}{st.session_state.account_counter}"

def add_transaction(acc_type, txn_type, amount, description=""):
    """Add a transaction record"""
    txn = {
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': txn_type,
        'amount': amount,
        'description': description,
        'balance_after': st.session_state.accounts[acc_type]['balance']
    }
    st.session_state.accounts[acc_type]['transactions'].append(txn)

def deposit(acc_type, amount, description=""):
    """Deposit money into an account"""
    if amount <= 0:
        return False, "Amount must be greater than zero."
    
    st.session_state.accounts[acc_type]['balance'] += amount
    add_transaction(acc_type, 'DEPOSIT', amount, description)
    return True, f"₹{amount:,.2f} deposited successfully."

def withdraw(acc_type, amount, description=""):
    """Withdraw money from an account"""
    if amount <= 0:
        return False, "Amount must be greater than zero."
    
    current_balance = st.session_state.accounts[acc_type]['balance']
    
    # Special rule for FD - cannot withdraw before maturity
    if acc_type == 'FD':
        maturity = st.session_state.accounts['FD'].get('maturity_date')
        if maturity:
            maturity_date = datetime.strptime(maturity, '%Y-%m-%d')
            if datetime.now() < maturity_date:
                return False, "❌ FD is locked until maturity date. Early withdrawal not allowed."
    
    # Special rule for Daily Collection - daily limit
    if acc_type == 'DAILY_COLLECTION':
        daily_limit = st.session_state.accounts['DAILY_COLLECTION'].get('daily_limit', 50000)
        if amount > daily_limit:
            return False, f"❌ Amount exceeds daily limit of ₹{daily_limit:,.2f}"
    
    if amount > current_balance:
        return False, f"Insufficient balance. Available: ₹{current_balance:,.2f}"
    
    st.session_state.accounts[acc_type]['balance'] -= amount
    add_transaction(acc_type, 'WITHDRAWAL', amount, description)
    return True, f"₹{amount:,.2f} withdrawn successfully."

def transfer(from_acc, to_acc, amount):
    """Transfer money between accounts"""
    if amount <= 0:
        return False, "Amount must be greater than zero."
    
    # Special check for Daily Collection limit
    if from_acc == 'DAILY_COLLECTION':
        daily_limit = st.session_state.accounts['DAILY_COLLECTION'].get('daily_limit', 50000)
        if amount > daily_limit:
            return False, f"❌ Transfer exceeds daily limit of ₹{daily_limit:,.2f}"
    
    if st.session_state.accounts[from_acc]['balance'] < amount:
        return False, f"Insufficient balance in {from_acc} account."
    
    # Perform transfer
    st.session_state.accounts[from_acc]['balance'] -= amount
    st.session_state.accounts[to_acc]['balance'] += amount
    
    # Add transactions for both accounts
    add_transaction(from_acc, 'TRANSFER_OUT', amount, f"Transfer to {to_acc}")
    add_transaction(to_acc, 'TRANSFER_IN', amount, f"Transfer from {from_acc}")
    
    return True, f"₹{amount:,.2f} transferred from {from_acc} to {to_acc}."

def create_fd(amount, tenure_months=12):
    """Create a fixed deposit"""
    if amount <= 0:
        return False, "FD amount must be greater than zero."
    
    if st.session_state.accounts['FD']['balance'] > 0:
        return False, "Only one FD account allowed at a time. Please withdraw existing FD first."
    
    interest_rate = 7.0  # 7% per annum
    maturity_date = datetime.now() + timedelta(days=tenure_months * 30)
    
    st.session_state.accounts['FD']['balance'] = amount
    st.session_state.accounts['FD']['interest_rate'] = interest_rate
    st.session_state.accounts['FD']['maturity_date'] = maturity_date.strftime('%Y-%m-%d')
    
    add_transaction('FD', 'DEPOSIT', amount, f"FD created for {tenure_months} months at {interest_rate}%")
    return True, f"✅ FD of ₹{amount:,.2f} created for {tenure_months} months at {interest_rate}% interest."

def close_fd():
    """Close FD and return with interest"""
    fd_balance = st.session_state.accounts['FD']['balance']
    if fd_balance <= 0:
        return False, "No FD to close."
    
    maturity_date_str = st.session_state.accounts['FD'].get('maturity_date')
    if maturity_date_str:
        maturity_date = datetime.strptime(maturity_date_str, '%Y-%m-%d')
        if datetime.now() < maturity_date:
            days_left = (maturity_date - datetime.now()).days
            return False, f"⚠️ FD matures on {maturity_date_str}. {days_left} days remaining."
    
    # Calculate interest (simplified)
    interest_rate = st.session_state.accounts['FD'].get('interest_rate', 7.0)
    # Simple interest calculation (assuming 1 year tenure)
    interest = fd_balance * (interest_rate / 100)
    total_amount = fd_balance + interest
    
    st.session_state.accounts['SAVINGS']['balance'] += total_amount
    add_transaction('SAVINGS', 'DEPOSIT', total_amount, f"FD maturity proceeds (Principal ₹{fd_balance:,.2f} + Interest ₹{interest:,.2f})")
    
    st.session_state.accounts['FD']['balance'] = 0.0
    st.session_state.accounts['FD']['maturity_date'] = None
    
    return True, f"✅ FD closed. ₹{total_amount:,.2f} (including ₹{interest:,.2f} interest) transferred to Savings."

# ============== UI COMPONENTS ==============
def display_account_card(acc_type, icon, color):
    """Display an account card with balance"""
    balance = st.session_state.accounts[acc_type]['balance']
    
    with st.container():
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {color}20, {color}05);
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid {color};
            margin-bottom: 10px;
        ">
            <h3 style="margin:0; color:{color};">{icon} {acc_type.replace('_', ' ').title()}</h3>
            <h2 style="margin:5px 0;">₹{balance:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)

def show_transactions(acc_type):
    """Display transaction history for an account"""
    transactions = st.session_state.accounts[acc_type]['transactions']
    if transactions:
        df = pd.DataFrame(transactions)
        df = df[['date', 'type', 'amount', 'description', 'balance_after']]
        df.columns = ['Date', 'Type', 'Amount', 'Description', 'Balance After']
        df = df.sort_values('Date', ascending=False)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet.")

# ============== MAIN APP ==============
st.title("🏦 Simple Banking System")
st.caption("No authorization required • Local standalone system")

# Sidebar - Account Balances Overview
with st.sidebar:
    st.header("📊 Account Overview")
    
    display_account_card('SAVINGS', '💰', '#2E86AB')
    display_account_card('CURRENT', '💳', '#A23B72')
    display_account_card('FD', '📈', '#F18F01')
    display_account_card('DAILY_COLLECTION', '🏪', '#1B998B')
    
    st.divider()
    total_balance = sum(st.session_state.accounts[acc]['balance'] for acc in st.session_state.accounts)
    st.metric("Total Portfolio", f"₹{total_balance:,.2f}")
    
    # FD info
    if st.session_state.accounts['FD']['balance'] > 0:
        maturity = st.session_state.accounts['FD'].get('maturity_date', 'N/A')
        rate = st.session_state.accounts['FD'].get('interest_rate', 7.0)
        st.info(f"📌 FD: {rate}% p.a. • Matures: {maturity}")

# Main tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💰 Savings", "💳 Current", "📈 Fixed Deposit", "🏪 Daily Collection", "🔄 Transfers"
])

# ---------- SAVINGS TAB ----------
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💵 Deposit")
        dep_amt = st.number_input("Amount to Deposit", min_value=0.0, step=100.0, key="sav_dep")
        if st.button("Deposit to Savings", key="sav_dep_btn"):
            if dep_amt > 0:
                success, msg = deposit('SAVINGS', dep_amt, "Over-the-counter deposit")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
    
    with col2:
        st.subheader("💸 Withdraw")
        wd_amt = st.number_input("Amount to Withdraw", min_value=0.0, step=100.0, key="sav_wd")
        if st.button("Withdraw from Savings", key="sav_wd_btn"):
            if wd_amt > 0:
                success, msg = withdraw('SAVINGS', wd_amt, "Over-the-counter withdrawal")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
    
    st.divider()
    st.subheader("📜 Transaction History")
    show_transactions('SAVINGS')

# ---------- CURRENT TAB ----------
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💵 Deposit")
        dep_amt = st.number_input("Amount to Deposit", min_value=0.0, step=100.0, key="cur_dep")
        if st.button("Deposit to Current", key="cur_dep_btn"):
            if dep_amt > 0:
                success, msg = deposit('CURRENT', dep_amt, "Over-the-counter deposit")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
    
    with col2:
        st.subheader("💸 Withdraw")
        wd_amt = st.number_input("Amount to Withdraw", min_value=0.0, step=100.0, key="cur_wd")
        if st.button("Withdraw from Current", key="cur_wd_btn"):
            if wd_amt > 0:
                success, msg = withdraw('CURRENT', wd_amt, "Over-the-counter withdrawal")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
    
    st.divider()
    st.subheader("📜 Transaction History")
    show_transactions('CURRENT')

# ---------- FIXED DEPOSIT TAB ----------
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Create FD")
        fd_amount = st.number_input("FD Amount", min_value=500.0, step=500.0, key="fd_amt")
        fd_tenure = st.selectbox("Tenure (Months)", [6, 12, 24, 36], index=1)
        
        if st.button("Create Fixed Deposit", key="fd_create"):
            success, msg = create_fd(fd_amount, fd_tenure)
            st.success(msg) if success else st.error(msg)
    
    with col2:
        st.subheader("🔓 Close FD")
        fd_balance = st.session_state.accounts['FD']['balance']
        st.metric("Current FD Balance", f"₹{fd_balance:,.2f}")
        
        if st.button("Close FD & Transfer to Savings", key="fd_close"):
            success, msg = close_fd()
            st.success(msg) if success else st.error(msg)
    
    st.divider()
    st.subheader("📜 Transaction History")
    show_transactions('FD')

# ---------- DAILY COLLECTION TAB ----------
with tab4:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏪 Deposit")
        dep_amt = st.number_input("Amount to Deposit", min_value=0.0, step=100.0, key="dc_dep")
        if st.button("Deposit to Daily Collection", key="dc_dep_btn"):
            if dep_amt > 0:
                success, msg = deposit('DAILY_COLLECTION', dep_amt, "Daily collection deposit")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
    
    with col2:
        st.subheader("💸 Withdraw")
        wd_amt = st.number_input("Amount to Withdraw", min_value=0.0, step=100.0, key="dc_wd")
        if st.button("Withdraw from Daily Collection", key="dc_wd_btn"):
            if wd_amt > 0:
                success, msg = withdraw('DAILY_COLLECTION', wd_amt, "Daily collection withdrawal")
                st.success(msg) if success else st.error(msg)
            else:
                st.warning("Enter an amount greater than zero.")
        
        # Show daily limit
        daily_limit = st.session_state.accounts['DAILY_COLLECTION'].get('daily_limit', 50000)
        st.caption(f"📌 Daily Withdrawal Limit: ₹{daily_limit:,.2f}")
    
    st.divider()
    st.subheader("📜 Transaction History")
    show_transactions('DAILY_COLLECTION')

# ---------- TRANSFER TAB ----------
with tab5:
    st.subheader("🔄 Inter-Account Transfers")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        from_acc = st.selectbox("From Account", 
                               ['SAVINGS', 'CURRENT', 'DAILY_COLLECTION'],
                               key="transfer_from")
    with col2:
        to_acc = st.selectbox("To Account", 
                             ['SAVINGS', 'CURRENT', 'DAILY_COLLECTION'],
                             key="transfer_to")
        # Prevent transferring to same account
        if from_acc == to_acc:
            st.warning("⚠️ From and To accounts must be different.")
    with col3:
        transfer_amt = st.number_input("Transfer Amount", min_value=0.0, step=100.0, key="transfer_amt")
    
    if st.button("🔄 Execute Transfer", key="transfer_btn"):
        if from_acc == to_acc:
            st.error("Cannot transfer to the same account.")
        elif transfer_amt <= 0:
            st.warning("Enter an amount greater than zero.")
        else:
            success, msg = transfer(from_acc, to_acc, transfer_amt)
            st.success(msg) if success else st.error(msg)
    
    # Show transfer summary
    st.divider()
    st.subheader("📊 Current Balances")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Savings", f"₹{st.session_state.accounts['SAVINGS']['balance']:,.2f}")
        st.metric("Current", f"₹{st.session_state.accounts['CURRENT']['balance']:,.2f}")
    with col2:
        st.metric("Daily Collection", f"₹{st.session_state.accounts['DAILY_COLLECTION']['balance']:,.2f}")
        st.metric("FD", f"₹{st.session_state.accounts['FD']['balance']:,.2f}")

# ============== FOOTER ==============
st.divider()
st.caption("🏦 Simple Banking System • Data resets when the app restarts")
