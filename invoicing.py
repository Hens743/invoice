import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --- Database Initialization ---
DB_PATH = 'invoices.db'

def initialize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Invoices table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoiceNumber TEXT NOT NULL UNIQUE,
            invoiceDate TEXT NOT NULL,
            clientName TEXT NOT NULL,
            clientEmail TEXT,
            totalAmount REAL NOT NULL,
            isRecurring INTEGER DEFAULT 0,
            recurrenceFrequency TEXT,
            nextInvoiceDate TEXT,
            endDate TEXT
        )
    ''')

    # Create LineItems table (linked to Invoices)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS LineItems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoiceId INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unitPrice REAL NOT NULL,
            FOREIGN KEY (invoiceId) REFERENCES Invoices(id) ON DELETE CASCADE
        )
    ''')

    # Create Estimates table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimateNumber TEXT NOT NULL UNIQUE,
            estimateDate TEXT NOT NULL,
            clientName TEXT NOT NULL,
            clientEmail TEXT,
            totalAmount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft'
        )
    ''')

    # Create EstimateLineItems table (linked to Estimates)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS EstimateLineItems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimateId INTEGER NOT NULL,
            description TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unitPrice REAL NOT NULL,
            FOREIGN KEY (estimateId) REFERENCES Estimates(id) ON DELETE CASCADE
        )
    ''')

    # Create Counters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Counters (
            name TEXT PRIMARY KEY,
            currentNumber INTEGER NOT NULL
        )
    ''')

    # Initialize counters if they don't exist
    cursor.execute("INSERT OR IGNORE INTO Counters (name, currentNumber) VALUES (?, ?)", ['invoiceNumber', 1000])
    cursor.execute("INSERT OR IGNORE INTO Counters (name, currentNumber) VALUES (?, ?)", ['estimateNumber', 2000])

    conn.commit()
    conn.close()

# --- Database Operations (Adapted for Streamlit) ---

def get_next_number(type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE Counters SET currentNumber = currentNumber + 1 WHERE name = ?", (type,))
    conn.commit()
    cursor.execute("SELECT currentNumber FROM Counters WHERE name = ?", (type,))
    number = cursor.fetchone()[0]
    conn.close()
    return number

def add_invoice(invoice_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Invoices (invoiceNumber, invoiceDate, clientName, clientEmail, totalAmount, isRecurring, recurrenceFrequency, nextInvoiceDate, endDate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (invoice_data['invoiceNumber'], invoice_data['invoiceDate'], invoice_data['clientName'], invoice_data['clientEmail'], invoice_data['totalAmount'], 1 if invoice_data['isRecurring'] else 0, invoice_data['recurrenceFrequency'], invoice_data['nextInvoiceDate'], invoice_data['endDate'])
    )
    invoice_id = cursor.lastrowid
    for item in invoice_data['lineItems']:
        cursor.execute(
            'INSERT INTO LineItems (invoiceId, description, quantity, unitPrice) VALUES (?, ?, ?, ?)',
            (invoice_id, item['description'], item['quantity'], item['unitPrice'])
        )
    conn.commit()
    conn.close()
    return True

def get_invoices():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Invoices ORDER BY invoiceNumber DESC')
    invoices_raw = cursor.fetchall()
    
    invoices = []
    for inv_raw in invoices_raw:
        invoice_dict = {
            'id': inv_raw[0],
            'invoiceNumber': inv_raw[1],
            'invoiceDate': inv_raw[2],
            'clientName': inv_raw[3],
            'clientEmail': inv_raw[4],
            'totalAmount': inv_raw[5],
            'isRecurring': bool(inv_raw[6]),
            'recurrenceFrequency': inv_raw[7],
            'nextInvoiceDate': inv_raw[8],
            'endDate': inv_raw[9]
        }
        cursor.execute('SELECT * FROM LineItems WHERE invoiceId = ?', (invoice_dict['id'],))
        line_items_raw = cursor.fetchall()
        invoice_dict['lineItems'] = [
            {'id': li[0], 'invoiceId': li[1], 'description': li[2], 'quantity': li[3], 'unitPrice': li[4]}
            for li in line_items_raw
        ]
        invoices.append(invoice_dict)
    conn.close()
    return invoices

def update_invoice(invoice_id, updated_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE Invoices SET invoiceDate = ?, clientName = ?, clientEmail = ?, totalAmount = ?, isRecurring = ?, recurrenceFrequency = ?, nextInvoiceDate = ?, endDate = ? WHERE id = ?',
        (updated_data['invoiceDate'], updated_data['clientName'], updated_data['clientEmail'], updated_data['totalAmount'], 1 if updated_data['isRecurring'] else 0, updated_data['recurrenceFrequency'], updated_data['nextInvoiceDate'], updated_data['endDate'], invoice_id)
    )
    cursor.execute('DELETE FROM LineItems WHERE invoiceId = ?', (invoice_id,))
    for item in updated_data['lineItems']:
        cursor.execute(
            'INSERT INTO LineItems (invoiceId, description, quantity, unitPrice) VALUES (?, ?, ?, ?)',
            (invoice_id, item['description'], item['quantity'], item['unitPrice'])
        )
    conn.commit()
    conn.close()
    return True

def delete_invoice(invoice_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Invoices WHERE id = ?', (invoice_id,))
    conn.commit()
    conn.close()
    return True

def add_estimate(estimate_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO Estimates (estimateNumber, estimateDate, clientName, clientEmail, totalAmount, status) VALUES (?, ?, ?, ?, ?, ?)',
        (estimate_data['estimateNumber'], estimate_data['estimateDate'], estimate_data['clientName'], estimate_data['clientEmail'], estimate_data['totalAmount'], estimate_data['status'])
    )
    estimate_id = cursor.lastrowid
    for item in estimate_data['lineItems']:
        cursor.execute(
            'INSERT INTO EstimateLineItems (estimateId, description, quantity, unitPrice) VALUES (?, ?, ?, ?)',
            (estimate_id, item['description'], item['quantity'], item['unitPrice'])
        )
    conn.commit()
    conn.close()
    return True

def get_estimates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM Estimates ORDER BY estimateNumber DESC')
    estimates_raw = cursor.fetchall()
    
    estimates = []
    for est_raw in estimates_raw:
        estimate_dict = {
            'id': est_raw[0],
            'estimateNumber': est_raw[1],
            'estimateDate': est_raw[2],
            'clientName': est_raw[3],
            'clientEmail': est_raw[4],
            'totalAmount': est_raw[5],
            'status': est_raw[6]
        }
        cursor.execute('SELECT * FROM EstimateLineItems WHERE estimateId = ?', (estimate_dict['id'],))
        line_items_raw = cursor.fetchall()
        estimate_dict['lineItems'] = [
            {'id': li[0], 'estimateId': li[1], 'description': li[2], 'quantity': li[3], 'unitPrice': li[4]}
            for li in line_items_raw
        ]
        estimates.append(estimate_dict)
    conn.close()
    return estimates

def update_estimate(estimate_id, updated_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE Estimates SET estimateDate = ?, clientName = ?, clientEmail = ?, totalAmount = ?, status = ? WHERE id = ?',
        (updated_data['estimateDate'], updated_data['clientName'], updated_data['clientEmail'], updated_data['totalAmount'], updated_data['status'], estimate_id)
    )
    cursor.execute('DELETE FROM EstimateLineItems WHERE estimateId = ?', (estimate_id,))
    for item in updated_data['lineItems']:
        cursor.execute(
            'INSERT INTO EstimateLineItems (estimateId, description, quantity, unitPrice) VALUES (?, ?, ?, ?)',
            (estimate_id, item['description'], item['quantity'], item['unitPrice'])
        )
    conn.commit()
    conn.close()
    return True

def delete_estimate(estimate_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM Estimates WHERE id = ?', (estimate_id,))
    conn.commit()
    conn.close()
    return True

# --- Translation Data ---
translations = {
    'en': {
        'appName': "Small Business Invoicing",
        'loading': "Loading application...",
        'yourInvoices': "Your Invoices",
        'addNewInvoice': "+ Add New Invoice",
        'noInvoicesYet': "No invoices yet. Click \"Add New Invoice\" to get started!",
        'invoiceNumber': "Invoice #",
        'client': "Client",
        'date': "Date",
        'total': "Total",
        'edit': "Edit",
        'save': "Save",
        'delete': "Delete",
        'confirmDeletion': "Confirm Deletion",
        'areYouSureDelete': "Are you sure you want to delete {} #{} for {}?",
        'cancel': "Cancel",
        'description': "Description",
        'quantity': "Quantity",
        'unitPrice': "Unit Price",
        'amount': "Amount",
        'actions': "Actions",
        'remove': "Remove",
        'addLineItem': "Add Line Item",
        'totalAmount': "Total Amount",
        'addInvoiceTitle': "Add New Invoice",
        'clientName': "Client Name",
        'clientEmail': "Client Email",
        'createInvoice': "Create Invoice",
        'databaseNotReady': "Database not ready. Please try again.",
        'invoiceAddedSuccess': "Invoice added successfully!",
        'failedToAddInvoice': "Failed to add invoice:",
        'invoiceUpdatedSuccess': "Invoice updated successfully!",
        'failedToUpdateInvoice': "Failed to update invoice:",
        'invoiceDeletedSuccess': "Invoice deleted successfully!",
        'failedToDeleteInvoice': "Failed to delete invoice:",
        'selectInvoice': "Select an invoice from the list or add a new one to view details.",
        'invoiceDate': "Invoice Date",
        'language': "Language",
        'currency': "Currency",
        'estimates': "Estimates",
        'yourEstimates': "Your Estimates",
        'addNewEstimate': "+ Add New Estimate",
        'noEstimatesYet': "No estimates yet. Click \"Add New Estimate\" to get started!",
        'estimateNumber': "Estimate #",
        'addEstimateTitle': "Add New Estimate",
        'createEstimate': "Create Estimate",
        'estimateAddedSuccess': "Estimate added successfully!",
        'failedToAddEstimate': "Failed to add estimate:",
        'estimateUpdatedSuccess': "Estimate updated successfully!",
        'failedToUpdateEstimate': "Failed to update estimate:",
        'estimateDeletedSuccess': "Estimate deleted successfully!",
        'failedToDeleteEstimate': "Failed to delete estimate:",
        'selectEstimate': "Select an estimate from the list or add a new one to view details.",
        'status': "Status",
        'convertEstimate': "Convert to Invoice",
        'recurringInvoice': "Make Recurring",
        'recurrenceFrequency': "Recurrence Frequency",
        'nextInvoiceDate': "Next Invoice Date",
        'endDate': "End Date (Optional)",
        'monthly': "Monthly",
        'quarterly': "Quarterly",
        'annually': "Annually",
        'generateNextInvoice': "Generate Next Invoice",
        'invoiceGeneratedSuccess': "Next invoice generated successfully!",
        'failedToGenerateInvoice': "Failed to generate next invoice:",
        'draft': "Draft",
        'sent': "Sent",
        'accepted': "Accepted",
        'rejected': "Rejected",
        'invoice': "Invoice",
        'estimate': "Estimate",
        'generatePdf': "Generate PDF (Print)", # Changed to indicate print functionality
        'generatingPdf': "Preparing for print...",
        'pdfGeneratedSuccess': "Print preview ready!",
        'failedToGeneratePdf': "Failed to prepare print preview:",
        'failedToLoadInvoices': "Failed to load invoices:",
        'failedToLoadEstimates': "Failed to load estimates:",
    }
}

def get_translation(lang, key, *args):
    # Since only 'en' is supported, we can simplify this.
    # The 'lang' parameter will effectively always be 'en' from session state.
    text = translations['en'].get(key, key)
    return text.format(*args)

# --- Currency Data and Formatter ---
currencies = {
    'USD': {'symbol': '$', 'locale': 'en-US'},
    'EUR': {'symbol': '€', 'locale': 'de-DE'},
    'NOK': {'symbol': 'kr', 'locale': 'nb-NO'},
}

def format_currency(amount, currency_code):
    currency_info = currencies.get(currency_code, currencies['USD'])
    try:
        # Using f-string for locale-aware formatting, requires Python 3.6+
        # For older Python, you'd use string.format or manual concatenation
        if currency_code == 'NOK': # Norwegian Krone often uses 'kr' after amount
             return f"{float(amount):,.2f} {currency_info['symbol']}"
        return f"{currency_info['symbol']}{float(amount):,.2f}"
    except Exception as e:
        st.error(f"Error formatting currency: {e}")
        return f"{currency_info['symbol']}{float(amount):.2f}"

# --- Streamlit App Components ---

def show_message(message, type='success'):
    if type == 'success':
        st.success(message)
    else:
        st.error(message)

def calculate_total(line_items):
    total = 0.0
    for item in line_items:
        try:
            qty = float(item.get('quantity', 0))
            price = float(item.get('unitPrice', 0))
            total += qty * price
        except ValueError:
            continue # Handle cases where quantity or unitPrice might be invalid
    return total

def invoice_detail_view(invoice, on_update, on_delete, on_generate_next_invoice, lang, currency):
    st.subheader(get_translation(lang, 'invoiceNumber') + invoice['invoiceNumber'])

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button(get_translation(lang, 'edit'), key=f"edit_invoice_{invoice['id']}"):
            st.session_state.editing_invoice_id = invoice['id']
            st.session_state.edited_invoice_data = invoice.copy()
            st.session_state.edited_invoice_data['lineItems'] = [item.copy() for item in invoice['lineItems']]
            st.session_state.show_add_invoice_modal = True # Re-use modal for editing
            st.rerun()
    with col2:
        if st.button(get_translation(lang, 'delete'), key=f"delete_invoice_{invoice['id']}"):
            st.session_state.show_delete_confirm = True
            st.session_state.item_to_delete = {'id': invoice['id'], 'type': 'invoice', 'number': invoice['invoiceNumber'], 'clientName': invoice['clientName']}
            st.rerun()
    with col3:
        if st.button(get_translation(lang, 'generatePdf'), key=f"print_invoice_{invoice['id']}"):
            st.session_state.show_print_preview = True
            st.session_state.print_item = {'type': 'invoice', 'data': invoice}
            st.rerun()

    st.markdown("---")

    # Display for printing
    st.markdown(f"### {get_translation(lang, 'invoiceNumber')}{invoice['invoiceNumber']}")
    st.write(f"**{get_translation(lang, 'invoiceDate')}:** {invoice['invoiceDate']}")
    st.write(f"**{get_translation(lang, 'clientName')}:** {invoice['clientName']}")
    st.write(f"**{get_translation(lang, 'clientEmail')}:** {invoice['clientEmail']}")

    st.markdown("#### " + get_translation(lang, 'lineItems'))
    line_item_data = []
    for i, item in enumerate(invoice['lineItems']):
        line_item_data.append({
            '#': i + 1,
            get_translation(lang, 'description'): item['description'],
            get_translation(lang, 'quantity'): item['quantity'],
            get_translation(lang, 'unitPrice'): format_currency(item['unitPrice'], currency),
            get_translation(lang, 'amount'): format_currency(float(item['quantity']) * float(item['unitPrice']), currency)
        })
    st.table(pd.DataFrame(line_item_data))
    st.markdown(f"**{get_translation(lang, 'totalAmount')}:** {format_currency(calculate_total(invoice['lineItems']), currency)}")

    st.markdown("---")
    
    # Recurring invoice details
    if invoice['isRecurring']:
        st.markdown(f"**{get_translation(lang, 'recurringInvoice')}**")
        st.write(f"**{get_translation(lang, 'recurrenceFrequency')}:** {get_translation(lang, invoice['recurrenceFrequency'].lower())}")
        st.write(f"**{get_translation(lang, 'nextInvoiceDate')}:** {invoice['nextInvoiceDate']}")
        if invoice['endDate']:
            st.write(f"**{get_translation(lang, 'endDate')}:** {invoice['endDate']}")
        
        today = datetime.now().date()
        next_invoice_date_dt = datetime.strptime(invoice['nextInvoiceDate'], '%Y-%m-%d').date()

        if next_invoice_date_dt <= today:
            if st.button(get_translation(lang, 'generateNextInvoice'), key=f"gen_next_invoice_{invoice['id']}"):
                on_generate_next_invoice(invoice)

def estimate_detail_view(estimate, on_update, on_delete, on_convert, lang, currency):
    st.subheader(get_translation(lang, 'estimateNumber') + estimate['estimateNumber'])

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button(get_translation(lang, 'edit'), key=f"edit_estimate_{estimate['id']}"):
            st.session_state.editing_estimate_id = estimate['id']
            st.session_state.edited_estimate_data = estimate.copy()
            st.session_state.edited_estimate_data['lineItems'] = [item.copy() for item in estimate['lineItems']]
            st.session_state.show_add_estimate_modal = True # Re-use modal for editing
            st.rerun()
    with col2:
        if st.button(get_translation(lang, 'delete'), key=f"delete_estimate_{estimate['id']}"):
            st.session_state.show_delete_confirm = True
            st.session_state.item_to_delete = {'id': estimate['id'], 'type': 'estimate', 'number': estimate['estimateNumber'], 'clientName': estimate['clientName']}
            st.rerun()
    with col3:
        if st.button(get_translation(lang, 'generatePdf'), key=f"print_estimate_{estimate['id']}"):
            st.session_state.show_print_preview = True
            st.session_state.print_item = {'type': 'estimate', 'data': estimate}
            st.rerun()

    st.markdown("---")

    st.write(f"**{get_translation(lang, 'date')}:** {estimate['estimateDate']}")
    st.write(f"**{get_translation(lang, 'clientName')}:** {estimate['clientName']}")
    st.write(f"**{get_translation(lang, 'clientEmail')}:** {estimate['clientEmail']}")
    st.write(f"**{get_translation(lang, 'status')}:** {get_translation(lang, estimate['status'])}")

    st.markdown("#### " + get_translation(lang, 'lineItems'))
    line_item_data = []
    for i, item in enumerate(estimate['lineItems']):
        line_item_data.append({
            '#': i + 1,
            get_translation(lang, 'description'): item['description'],
            get_translation(lang, 'quantity'): item['quantity'],
            get_translation(lang, 'unitPrice'): format_currency(item['unitPrice'], currency),
            get_translation(lang, 'amount'): format_currency(float(item['quantity']) * float(item['unitPrice']), currency)
        })
    st.table(pd.DataFrame(line_item_data))
    st.markdown(f"**{get_translation(lang, 'totalAmount')}:** {format_currency(calculate_total(estimate['lineItems']), currency)}")

    st.markdown("---")

    if estimate['status'] != 'accepted':
        if st.button(get_translation(lang, 'convertEstimate'), key=f"convert_estimate_{estimate['id']}"):
            on_convert(estimate)

def add_edit_invoice_form(on_add_invoice, on_update_invoice, lang, currency):
    is_editing = 'editing_invoice_id' in st.session_state and st.session_state.editing_invoice_id is not None
    
    st.header(get_translation(lang, 'addInvoiceTitle') if not is_editing else f"{get_translation(lang, 'edit')} {get_translation(lang, 'invoice')}")

    # Ensure initial_data is always a dictionary
    initial_data_from_session = st.session_state.get('edited_invoice_data')
    if initial_data_from_session is None:
        initial_data = {
            'invoiceDate': datetime.now().strftime('%Y-%m-%d'),
            'clientName': '',
            'clientEmail': '',
            'lineItems': [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}],
            'isRecurring': False,
            'recurrenceFrequency': 'monthly',
            'nextInvoiceDate': datetime.now().strftime('%Y-%m-%d'),
            'endDate': ''
        }
    else:
        initial_data = initial_data_from_session

    # Initialize form_line_items in session state if not present or if switching invoices in edit mode
    if 'form_line_items' not in st.session_state or \
       (is_editing and st.session_state.editing_invoice_id != st.session_state.get('last_edited_invoice_id_for_form')):
        st.session_state.form_line_items = initial_data.get('lineItems', [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}])
        st.session_state.last_edited_invoice_id_for_form = st.session_state.editing_invoice_id

    # Safely determine initial date values for st.date_input
    invoice_date_val = datetime.now().date()
    if initial_data.get('invoiceDate'):
        try:
            invoice_date_val = datetime.strptime(initial_data['invoiceDate'], '%Y-%m-%d').date()
        except ValueError:
            pass

    next_invoice_date_val = datetime.now().date()
    if initial_data.get('nextInvoiceDate'):
        try:
            next_invoice_date_val = datetime.strptime(initial_data['nextInvoiceDate'], '%Y-%m-%d').date()
        except ValueError:
            pass

    end_date_val = None
    if initial_data.get('endDate'):
        try:
            end_date_val = datetime.strptime(initial_data['endDate'], '%Y-%m-%d').date()
        except ValueError:
            pass

    # --- Main Form for Invoice Details ---
    with st.form(key='invoice_form'):
        client_name = st.text_input(get_translation(lang, 'clientName'), value=initial_data['clientName'])
        client_email = st.text_input(get_translation(lang, 'clientEmail'), value=initial_data['clientEmail'])
        invoice_date = st.date_input(get_translation(lang, 'invoiceDate'), value=invoice_date_val)

        is_recurring = st.checkbox(get_translation(lang, 'recurringInvoice'), value=initial_data['isRecurring'])
        recurrence_frequency = initial_data['recurrenceFrequency']
        next_invoice_date = None
        end_date = None

        if is_recurring:
            recurrence_frequency = st.selectbox(get_translation(lang, 'recurrenceFrequency'), ['monthly', 'quarterly', 'annually'], index=['monthly', 'quarterly', 'annually'].index(initial_data['recurrenceFrequency']))
            next_invoice_date = st.date_input(get_translation(lang, 'nextInvoiceDate'), value=next_invoice_date_val)
            end_date = st.date_input(get_translation(lang, 'endDate'), value=end_date_val)

        submitted = st.form_submit_button(get_translation(lang, 'createInvoice') if not is_editing else get_translation(lang, 'save'))
        if submitted:
            invoice_data = {
                'invoiceDate': invoice_date.strftime('%Y-%m-%d'),
                'clientName': client_name,
                'clientEmail': client_email,
                'lineItems': st.session_state.form_line_items, # Get the latest from session state
                'totalAmount': calculate_total(st.session_state.form_line_items),
                'isRecurring': is_recurring,
                'recurrenceFrequency': recurrence_frequency,
                'nextInvoiceDate': next_invoice_date.strftime('%Y-%m-%d') if next_invoice_date else None,
                'endDate': end_date.strftime('%Y-%m-%d') if end_date else None,
            }
            if is_editing:
                on_update_invoice(st.session_state.editing_invoice_id, invoice_data)
            else:
                on_add_invoice(invoice_data)
            
            # Clear form state and close modal
            st.session_state.show_add_invoice_modal = False
            st.session_state.editing_invoice_id = None
            st.session_state.edited_invoice_data = None
            st.session_state.form_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}] # Reset form line items
            st.session_state.last_edited_invoice_id_for_form = None # Clear this flag
            st.rerun()

    # --- Line Item Management (OUTSIDE the form) ---
    st.markdown("---")
    st.subheader(get_translation(lang, 'lineItems'))
    
    # Display and allow editing of existing line items
    for i, item in enumerate(st.session_state.form_line_items):
        st.markdown(f"**{get_translation(lang, 'lineItems')} {i+1}**")
        col_desc, col_qty, col_price, col_amt, col_remove = st.columns([3, 1, 1, 1, 0.5])
        with col_desc:
            st.session_state.form_line_items[i]['description'] = st.text_input(get_translation(lang, 'description'), value=item['description'], key=f"desc_{i}_{is_editing}_outside")
        with col_qty:
            st.session_state.form_line_items[i]['quantity'] = st.number_input(get_translation(lang, 'quantity'), min_value=0.0, value=float(item['quantity']), key=f"qty_{i}_{is_editing}_outside")
        with col_price:
            st.session_state.form_line_items[i]['unitPrice'] = st.number_input(get_translation(lang, 'unitPrice'), min_value=0.0, value=float(item['unitPrice']), format="%.2f", key=f"price_{i}_{is_editing}_outside")
        with col_amt:
            st.text_input(get_translation(lang, 'amount'), value=format_currency(float(item['quantity']) * float(item['unitPrice']), currency), disabled=True, key=f"amt_{i}_{is_editing}_outside")
        with col_remove:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            if st.button(get_translation(lang, 'remove'), key=f"remove_{i}_{is_editing}_outside"):
                st.session_state.form_line_items.pop(i)
                st.rerun() # Rerun to update the list

    if st.button(get_translation(lang, 'addLineItem'), key=f"add_line_item_{is_editing}_outside"):
        st.session_state.form_line_items.append({'description': '', 'quantity': 1.0, 'unitPrice': 0.0})
        st.rerun() # Rerun to show new line item

    st.markdown(f"**{get_translation(lang, 'totalAmount')}:** {format_currency(calculate_total(st.session_state.form_line_items), currency)}")
    st.markdown("---")

    if st.button(get_translation(lang, 'cancel'), key=f"cancel_invoice_form_{is_editing}"):
        st.session_state.show_add_invoice_modal = False
        st.session_state.editing_invoice_id = None
        st.session_state.edited_invoice_data = None
        st.session_state.form_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}] # Reset form line items
        st.session_state.last_edited_invoice_id_for_form = None # Clear this flag
        st.rerun()


def add_edit_estimate_form(on_add_estimate, on_update_estimate, lang, currency):
    is_editing = 'editing_estimate_id' in st.session_state and st.session_state.editing_estimate_id is not None
    
    st.header(get_translation(lang, 'addEstimateTitle') if not is_editing else f"{get_translation(lang, 'edit')} {get_translation(lang, 'estimate')}")

    # Ensure initial_data is always a dictionary
    initial_data_from_session = st.session_state.get('edited_estimate_data')
    if initial_data_from_session is None:
        initial_data = {
            'estimateDate': datetime.now().strftime('%Y-%m-%d'),
            'clientName': '',
            'clientEmail': '',
            'lineItems': [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}],
            'status': 'draft'
        }
    else:
        initial_data = initial_data_from_session

    # Initialize form_estimate_line_items in session state if not present or if switching estimates in edit mode
    if 'form_estimate_line_items' not in st.session_state or \
       (is_editing and st.session_state.editing_estimate_id != st.session_state.get('last_edited_estimate_id_for_form')):
        st.session_state.form_estimate_line_items = initial_data.get('lineItems', [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}])
        st.session_state.last_edited_estimate_id_for_form = st.session_state.editing_estimate_id

    # Safely determine initial date value for st.date_input
    estimate_date_val = datetime.now().date()
    if initial_data.get('estimateDate'):
        try:
            estimate_date_val = datetime.strptime(initial_data['estimateDate'], '%Y-%m-%d').date()
        except ValueError:
            pass

    # --- Main Form for Estimate Details ---
    with st.form(key='estimate_form'):
        client_name = st.text_input(get_translation(lang, 'clientName'), value=initial_data['clientName'])
        client_email = st.text_input(get_translation(lang, 'clientEmail'), value=initial_data['clientEmail'])
        estimate_date = st.date_input(get_translation(lang, 'date'), value=estimate_date_val)
        status = st.selectbox(get_translation(lang, 'status'), ['draft', 'sent', 'accepted', 'rejected'], index=['draft', 'sent', 'accepted', 'rejected'].index(initial_data['status']))

        submitted = st.form_submit_button(get_translation(lang, 'createEstimate') if not is_editing else get_translation(lang, 'save'))
        if submitted:
            estimate_data = {
                'estimateDate': estimate_date.strftime('%Y-%m-%d'),
                'clientName': client_name,
                'clientEmail': client_email,
                'lineItems': st.session_state.form_estimate_line_items, # Get the latest from session state
                'totalAmount': calculate_total(st.session_state.form_estimate_line_items),
                'status': status
            }
            if is_editing:
                on_update_estimate(st.session_state.editing_estimate_id, estimate_data)
            else:
                on_add_estimate(estimate_data)
            
            st.session_state.show_add_estimate_modal = False
            st.session_state.editing_estimate_id = None
            st.session_state.edited_estimate_data = None
            st.session_state.form_estimate_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}]
            st.session_state.last_edited_estimate_id_for_form = None
            st.rerun()

    # --- Line Item Management (OUTSIDE the form) ---
    st.markdown("---")
    st.subheader(get_translation(lang, 'lineItems'))

    new_line_items = []
    for i, item in enumerate(st.session_state.form_estimate_line_items):
        st.markdown(f"**{get_translation(lang, 'lineItems')} {i+1}**")
        col_desc, col_qty, col_price, col_amt, col_remove = st.columns([3, 1, 1, 1, 0.5])
        with col_desc:
            st.session_state.form_estimate_line_items[i]['description'] = st.text_input(get_translation(lang, 'description'), value=item['description'], key=f"est_desc_{i}_{is_editing}_outside")
        with col_qty:
            st.session_state.form_estimate_line_items[i]['quantity'] = st.number_input(get_translation(lang, 'quantity'), min_value=0.0, value=float(item['quantity']), key=f"est_qty_{i}_{is_editing}_outside")
        with col_price:
            st.session_state.form_estimate_line_items[i]['unitPrice'] = st.number_input(get_translation(lang, 'unitPrice'), min_value=0.0, value=float(item['unitPrice']), format="%.2f", key=f"est_price_{i}_{is_editing}_outside")
        with col_amt:
            st.text_input(get_translation(lang, 'amount'), value=format_currency(float(item['quantity']) * float(item['unitPrice']), currency), disabled=True, key=f"est_amt_{i}_{is_editing}_outside")
        with col_remove:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            if st.button(get_translation(lang, 'remove'), key=f"est_remove_{i}_{is_editing}_outside"):
                st.session_state.form_estimate_line_items.pop(i)
                st.rerun()
            new_line_items.append(item)
    st.session_state.form_estimate_line_items = new_line_items

    if st.button(get_translation(lang, 'addLineItem'), key=f"est_add_line_item_{is_editing}_outside"):
        st.session_state.form_estimate_line_items.append({'description': '', 'quantity': 1.0, 'unitPrice': 0.0})
        st.rerun()

    st.markdown(f"**{get_translation(lang, 'totalAmount')}:** {format_currency(calculate_total(st.session_state.form_estimate_line_items), currency)}")
    st.markdown("---")

    if st.button(get_translation(lang, 'cancel'), key=f"cancel_estimate_form_{is_editing}"):
        st.session_state.show_add_estimate_modal = False
        st.session_state.editing_estimate_id = None
        st.session_state.edited_estimate_data = None
        st.session_state.form_estimate_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}]
        st.session_state.last_edited_estimate_id_for_form = None
        st.rerun()

def main():
    initialize_database()

    # Initialize session state variables
    if 'current_view' not in st.session_state:
        st.session_state.current_view = 'invoices'
    # Default language to 'en' and remove language selection UI
    st.session_state.language = 'en' 
    if 'currency' not in st.session_state:
        st.session_state.currency = 'USD'
    if 'show_add_invoice_modal' not in st.session_state:
        st.session_state.show_add_invoice_modal = False
    if 'show_add_estimate_modal' not in st.session_state:
        st.session_state.show_add_estimate_modal = False
    if 'show_delete_confirm' not in st.session_state:
        st.session_state.show_delete_confirm = False
    if 'item_to_delete' not in st.session_state:
        st.session_state.item_to_delete = None
    if 'selected_invoice' not in st.session_state:
        st.session_state.selected_invoice = None
    if 'selected_estimate' not in st.session_state:
        st.session_state.selected_estimate = None
    if 'editing_invoice_id' not in st.session_state:
        st.session_state.editing_invoice_id = None
    if 'edited_invoice_data' not in st.session_state:
        st.session_state.edited_invoice_data = None
    if 'editing_estimate_id' not in st.session_state:
        st.session_state.editing_estimate_id = None
    if 'edited_estimate_data' not in st.session_state:
        st.session_state.edited_estimate_data = None
    if 'show_print_preview' not in st.session_state:
        st.session_state.show_print_preview = False
    if 'print_item' not in st.session_state:
        st.session_state.print_item = None

    st.set_page_config(layout="wide")

    st.title(get_translation(st.session_state.language, 'appName'))

    # Removed language selection column, keeping only currency
    col_currency = st.columns(1)[0] # Use a single column for currency
    with col_currency:
        selected_currency = st.selectbox(get_translation(st.session_state.language, 'currency'), ['USD', 'EUR', 'NOK'])
        if selected_currency != st.session_state.currency:
            st.session_state.currency = selected_currency
            st.rerun()

    st.markdown("---")

    # Message display
    if 'message' in st.session_state and st.session_state.message:
        if st.session_state.message_type == 'success':
            st.success(st.session_state.message)
        else:
            st.error(st.session_state.message)
        # Clear message after display
        st.session_state.message = ''
        st.session_state.message_type = ''

    # Dashboard navigation
    col_invoices, col_estimates = st.columns(2)
    with col_invoices:
        if st.button(get_translation(st.session_state.language, 'yourInvoices'), use_container_width=True):
            st.session_state.current_view = 'invoices'
            st.session_state.selected_invoice = None # Clear selection on view change
            st.session_state.show_add_invoice_modal = False
            st.session_state.editing_invoice_id = None
            st.session_state.edited_invoice_data = None
            st.session_state.form_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}] # Reset form line items
            st.session_state.last_edited_invoice_id_for_form = None
            st.rerun()
    with col_estimates:
        if st.button(get_translation(st.session_state.language, 'estimates'), use_container_width=True):
            st.session_state.current_view = 'estimates'
            st.session_state.selected_estimate = None # Clear selection on view change
            st.session_state.show_add_estimate_modal = False
            st.session_state.editing_estimate_id = None
            st.session_state.edited_estimate_data = None
            st.session_state.form_estimate_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}]
            st.session_state.last_edited_estimate_id_for_form = None
            st.rerun()

    st.markdown("---")

    # Main content area
    if st.session_state.current_view == 'invoices':
        invoices = get_invoices()
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.subheader(get_translation(st.session_state.language, 'yourInvoices'))
            if st.button(get_translation(st.session_state.language, 'addNewInvoice'), use_container_width=True, key="add_new_invoice_btn"):
                st.session_state.show_add_invoice_modal = True
                st.session_state.editing_invoice_id = None # Ensure not in edit mode when adding
                st.session_state.edited_invoice_data = None
                st.session_state.form_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}] # Reset form line items
                st.session_state.last_edited_invoice_id_for_form = None
                st.rerun()

            if not invoices:
                st.info(get_translation(st.session_state.language, 'noInvoicesYet'))
            else:
                for inv in invoices:
                    is_selected = st.session_state.selected_invoice and st.session_state.selected_invoice['id'] == inv['id']
                    if st.button(f"{get_translation(st.session_state.language, 'invoiceNumber')}{inv['invoiceNumber']} - {inv['clientName']} ({format_currency(inv['totalAmount'], st.session_state.currency)})", key=f"select_invoice_{inv['id']}", use_container_width=True):
                        st.session_state.selected_invoice = inv
                        st.session_state.show_print_preview = False # Hide print preview when selecting new invoice
                        st.rerun()
                    if is_selected:
                        st.markdown("---") # Separator for selected item

        with col_detail:
            if st.session_state.selected_invoice:
                invoice_detail_view(
                    st.session_state.selected_invoice,
                    on_update=lambda inv_id, data: (update_invoice(inv_id, data), setattr(st.session_state, 'message', get_translation(st.session_state.language, 'invoiceUpdatedSuccess')), setattr(st.session_state, 'message_type', 'success'), st.rerun()),
                    on_delete=lambda item: (setattr(st.session_state, 'show_delete_confirm', True), setattr(st.session_state, 'item_to_delete', item), st.rerun()),
                    on_generate_next_invoice=lambda original_inv: generate_next_invoice(original_inv, st.session_state.language, st.session_state.currency),
                    lang=st.session_state.language,  # Added missing argument
                    currency=st.session_state.currency # Added missing argument
                )
            else:
                st.info(get_translation(st.session_state.language, 'selectInvoice'))

    elif st.session_state.current_view == 'estimates':
        estimates = get_estimates()
        col_list, col_detail = st.columns([1, 2])

        with col_list:
            st.subheader(get_translation(st.session_state.language, 'yourEstimates'))
            if st.button(get_translation(st.session_state.language, 'addNewEstimate'), use_container_width=True, key="add_new_estimate_btn"):
                st.session_state.show_add_estimate_modal = True
                st.session_state.editing_estimate_id = None
                st.session_state.edited_estimate_data = None
                st.session_state.form_estimate_line_items = [{'description': '', 'quantity': 1.0, 'unitPrice': 0.0}]
                st.session_state.last_edited_estimate_id_for_form = None
                st.rerun()

            if not estimates:
                st.info(get_translation(st.session_state.language, 'noEstimatesYet'))
            else:
                for est in estimates:
                    is_selected = st.session_state.selected_estimate and st.session_state.selected_estimate['id'] == est['id']
                    if st.button(f"{get_translation(st.session_state.language, 'estimateNumber')}{est['estimateNumber']} - {est['clientName']} ({format_currency(est['totalAmount'], st.session_state.currency)})", key=f"select_estimate_{est['id']}", use_container_width=True):
                        st.session_state.selected_estimate = est
                        st.session_state.show_print_preview = False # Hide print preview when selecting new estimate
                        st.rerun()
                    if is_selected:
                        st.markdown("---") # Separator for selected item

        with col_detail:
            if st.session_state.selected_estimate:
                estimate_detail_view(
                    st.session_state.selected_estimate,
                    on_update=lambda est_id, data: (update_estimate(est_id, data), setattr(st.session_state, 'message', get_translation(st.session_state.language, 'estimateUpdatedSuccess')), setattr(st.session_state, 'message_type', 'success'), st.rerun()),
                    on_delete=lambda item: (setattr(st.session_state, 'show_delete_confirm', True), setattr(st.session_state, 'item_to_delete', item), st.rerun()),
                    on_convert=lambda estimate: convert_estimate_to_invoice(estimate, st.session_state.language, st.session_state.currency),
                    lang=st.session_state.language, # Added missing argument
                    currency=st.session_state.currency # Added missing argument
                )
            else:
                st.info(get_translation(st.session_state.language, 'selectEstimate'))

    # Modals (implemented as conditional rendering in Streamlit)
    if st.session_state.show_add_invoice_modal:
        st.sidebar.markdown("## " + (get_translation(st.session_state.language, 'addInvoiceTitle') if st.session_state.editing_invoice_id is None else f"{get_translation(st.session_state.language, 'edit')} {get_translation(st.session_state.language, 'invoice')}"))
        add_edit_invoice_form(
            on_add_invoice=lambda data: (add_invoice_wrapper(data, st.session_state.language), st.rerun()),
            on_update_invoice=lambda inv_id, data: (update_invoice_wrapper(inv_id, data, st.session_state.language), st.rerun()),
            lang=st.session_state.language,
            currency=st.session_state.currency
        )
    
    if st.session_state.show_add_estimate_modal:
        st.sidebar.markdown("## " + (get_translation(st.session_state.language, 'addEstimateTitle') if st.session_state.editing_estimate_id is None else f"{get_translation(st.session_state.language, 'edit')} {get_translation(st.session_state.language, 'estimate')}"))
        add_edit_estimate_form(
            on_add_estimate=lambda data: (add_estimate_wrapper(data, st.session_state.language), st.rerun()),
            on_update_estimate=lambda est_id, data: (update_estimate_wrapper(est_id, data, st.session_state.language), st.rerun()),
            lang=st.session_state.language,
            currency=st.session_state.currency
        )

    if st.session_state.show_delete_confirm:
        item = st.session_state.item_to_delete
        st.warning(get_translation(st.session_state.language, 'areYouSureDelete', get_translation(st.session_state.language, item['type']), item['number'], item['clientName']))
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button(get_translation(st.session_state.language, 'delete'), key="confirm_delete_btn"):
                if item['type'] == 'invoice':
                    delete_invoice(item['id'])
                    st.session_state.selected_invoice = None # Deselect deleted item
                    st.session_state.message = get_translation(st.session_state.language, 'invoiceDeletedSuccess')
                    st.session_state.message_type = 'success'
                else:
                    delete_estimate(item['id'])
                    st.session_state.selected_estimate = None # Deselect deleted item
                    st.session_state.message = get_translation(st.session_state.language, 'estimateDeletedSuccess')
                    st.session_state.message_type = 'success'
                st.session_state.show_delete_confirm = False
                st.session_state.item_to_delete = None
                st.rerun()
        with col_cancel:
            if st.button(get_translation(st.session_state.language, 'cancel'), key="cancel_delete_btn"):
                st.session_state.show_delete_confirm = False
                st.session_state.item_to_delete = None
                st.rerun()

    if st.session_state.show_print_preview:
        item_to_print = st.session_state.print_item['data']
        item_type = st.session_state.print_item['type']
        
        st.sidebar.markdown(f"## {get_translation(st.session_state.language, 'generatePdf')}")
        st.sidebar.info(get_translation(st.session_state.language, 'pdfGeneratedSuccess'))
        st.sidebar.button(get_translation(st.session_state.language, 'cancel'), key="cancel_print_preview", on_click=lambda: setattr(st.session_state, 'show_print_preview', False))

        st.markdown("---")
        st.markdown("<style>@media print { body { visibility: hidden; } .printable-area { visibility: visible; position: absolute; top: 0; left: 0; width: 100%; } }</style>", unsafe_allow_html=True)
        
        st.markdown('<div class="printable-area">', unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align: center;'>{get_translation(st.session_state.language, item_type).upper()} #{item_to_print[f'{item_type}Number']}</h1>", unsafe_allow_html=True)
        
        st.write(f"**{get_translation(st.session_state.language, 'date')}:** {item_to_print[f'{item_type}Date']}")
        st.write(f"**{get_translation(lang, 'clientName')}:** {item_to_print['clientName']}")
        st.write(f"**{get_translation(lang, 'clientEmail')}:** {item_to_print['clientEmail']}")
        
        if item_type == 'estimate':
            st.write(f"**{get_translation(lang, 'status')}:** {get_translation(lang, item_to_print['status'])}")

        st.markdown("### " + get_translation(lang, 'lineItems'))
        printable_line_item_data = []
        for i, item in enumerate(item_to_print['lineItems']):
            printable_line_item_data.append({
                '#': i + 1,
                get_translation(lang, 'description'): item['description'],
                get_translation(lang, 'quantity'): item['quantity'],
                get_translation(lang, 'unitPrice'): format_currency(item['unitPrice'], st.session_state.currency),
                get_translation(lang, 'amount'): format_currency(float(item['quantity']) * float(item['unitPrice']), st.session_state.currency)
            })
        st.table(pd.DataFrame(printable_line_item_data))
        st.markdown(f"**{get_translation(lang, 'totalAmount')}:** {format_currency(calculate_total(item_to_print['lineItems']), st.session_state.currency)}")
        st.markdown('</div>', unsafe_allow_html=True)
        st.info("Use your browser's print function (Ctrl+P or Cmd+P) to save this as a PDF.")


# --- Wrapper functions for database operations with Streamlit messaging ---
def add_invoice_wrapper(invoice_data, lang):
    try:
        next_invoice_number = get_next_number('invoiceNumber')
        invoice_data['invoiceNumber'] = str(next_invoice_number)
        add_invoice(invoice_data)
        st.session_state.message = get_translation(lang, 'invoiceAddedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_invoice = None # Clear selection to refresh list
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToAddInvoice')} {e}"
        st.session_state.message_type = 'error'

def update_invoice_wrapper(invoice_id, updated_data, lang):
    try:
        update_invoice(invoice_id, updated_data)
        st.session_state.message = get_translation(lang, 'invoiceUpdatedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_invoice = None # Clear selection to refresh list
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToUpdateInvoice')} {e}"
        st.session_state.message_type = 'error'

def generate_next_invoice(original_invoice, lang, currency):
    try:
        today = datetime.now().date()
        next_date_str = original_invoice['nextInvoiceDate']
        if not next_date_str:
            st.session_state.message = "Next invoice date is not set for recurring invoice."
            st.session_state.message_type = 'error'
            return

        next_date = datetime.strptime(next_date_str, '%Y-%m-%d').date()

        if original_invoice['recurrenceFrequency'] == 'monthly':
            next_date = (next_date + timedelta(days=31)).replace(day=min(next_date.day, (next_date + timedelta(days=31)).day)) # Adjust for month end
        elif original_invoice['recurrenceFrequency'] == 'quarterly':
            next_date = (next_date + timedelta(days=92)).replace(day=min(next_date.day, (next_date + timedelta(days=92)).day)) # Approx 3 months
        elif original_invoice['recurrenceFrequency'] == 'annually':
            next_date = (next_date + timedelta(days=366)).replace(day=min(next_date.day, (next_date + timedelta(days=366)).day)) # Approx 1 year
        
        if original_invoice['endDate'] and datetime.strptime(original_invoice['endDate'], '%Y-%m-%d').date() < next_date:
            st.session_state.message = "Cannot generate next invoice: End date has passed."
            st.session_state.message_type = 'error'
            return

        new_invoice_number = get_next_number('invoiceNumber')
        
        new_invoice_data = original_invoice.copy()
        new_invoice_data['invoiceNumber'] = str(new_invoice_number)
        new_invoice_data['invoiceDate'] = next_date.strftime('%Y-%m-%d')
        new_invoice_data['id'] = None # Ensure new ID for new record
        
        add_invoice(new_invoice_data)
        
        # Update original invoice's nextInvoiceDate
        original_invoice['nextInvoiceDate'] = next_date.strftime('%Y-%m-%d')
        update_invoice(original_invoice['id'], original_invoice)

        st.session_state.message = get_translation(lang, 'invoiceGeneratedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_invoice = None # Refresh list and details
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToGenerateInvoice')} {e}"
        st.session_state.message_type = 'error'
    st.rerun()


def add_estimate_wrapper(estimate_data, lang):
    try:
        next_estimate_number = get_next_number('estimateNumber')
        estimate_data['estimateNumber'] = str(next_estimate_number)
        add_estimate(estimate_data)
        st.session_state.message = get_translation(lang, 'estimateAddedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_estimate = None # Clear selection to refresh list
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToAddEstimate')} {e}"
        st.session_state.message_type = 'error'

def update_estimate_wrapper(estimate_id, updated_data, lang):
    try:
        update_estimate(estimate_id, updated_data)
        st.session_state.message = get_translation(lang, 'estimateUpdatedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_estimate = None # Clear selection to refresh list
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToUpdateEstimate')} {e}"
        st.session_state.message_type = 'error'

def convert_estimate_to_invoice(estimate, lang, currency):
    try:
        next_invoice_number = get_next_number('invoiceNumber')
        
        new_invoice_data = {
            'invoiceNumber': str(next_invoice_number),
            'invoiceDate': datetime.now().strftime('%Y-%m-%d'),
            'clientName': estimate['clientName'],
            'clientEmail': estimate['clientEmail'],
            'lineItems': estimate['lineItems'],
            'totalAmount': estimate['totalAmount'],
            'isRecurring': False,
            'recurrenceFrequency': None,
            'nextInvoiceDate': None,
            'endDate': None,
        }
        add_invoice(new_invoice_data)

        # Update estimate status to 'accepted'
        estimate['status'] = 'accepted'
        update_estimate(estimate['id'], estimate)

        st.session_state.message = get_translation(lang, 'estimateConvertedSuccess')
        st.session_state.message_type = 'success'
        st.session_state.selected_estimate = None # Deselect converted estimate
        st.session_state.current_view = 'invoices' # Switch to invoices view
    except Exception as e:
        st.session_state.message = f"{get_translation(lang, 'failedToConvertEstimate')} {e}"
        st.session_state.message_type = 'error'
    st.rerun()


if __name__ == "__main__":
    main()
