from flask import Blueprint, render_template, redirect, url_for, request, flash, g, send_file
from flask_login import login_required, current_user
from app.models import (db, User, Shopkeeper, CharteredAccountant, CAEmployee, EmployeeClient, 
                       Bill, BillItem, Product, CAConnection, ShopConnection, GSTFilingStatus)
import io
from sqlalchemy import func, and_, or_
from app.forms import EmployeeRegistrationForm, EmployeeEditForm, CAProfileForm
from werkzeug.security import generate_password_hash
import io
import pandas as pd
from flask import send_file
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from sqlalchemy.orm import joinedload

def get_ca_pending_requests():
    if hasattr(g, 'ca_pending_requests'):
        return g.ca_pending_requests
    from flask_login import current_user
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and getattr(current_user, 'role', None) == 'CA':
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if ca:
            pending = ShopConnection.query.filter_by(ca_id=ca.ca_id, status='pending').all()
            requests = []
            for conn in pending:
                shop = Shopkeeper.query.get(conn.shopkeeper_id)
                requests.append({
                    'conn_id': conn.id,
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'domain': shop.domain,
                    'contact_number': shop.contact_number
                })
            g.ca_pending_requests = requests
            return requests
    g.ca_pending_requests = []
    return []

ca_bp = Blueprint('ca', __name__, url_prefix='/ca')

@ca_bp.app_context_processor
def inject_ca_pending_requests():
    return {'ca_pending_requests': get_ca_pending_requests()}

@ca_bp.route('/')
def ca_root():
    return redirect(url_for('ca.dashboard'))

@ca_bp.route('/employee')
def ca_employee_root():
    return redirect(url_for('ca.employee_dashboard'))

@ca_bp.route('/dashboard')
@login_required
def dashboard():
    # Only CA can access
    if current_user.role != 'CA':
        return redirect(url_for('ca.employee_dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    # Summary cards
    total_clients = CAConnection.query.filter_by(ca_id=ca.ca_id, status='approved').count()
    new_connections = CAConnection.query.filter_by(ca_id=ca.ca_id, status='approved').filter(CAConnection.id > 0).count() # Placeholder logic
    pending_approvals = CAConnection.query.filter_by(ca_id=ca.ca_id, status='pending').count()
    # Recent bills (last 5)
    recent_bills = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
    recent_bills = recent_bills.join(CAConnection, and_(CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id, CAConnection.ca_id == ca.ca_id, CAConnection.status == 'approved'))
    recent_bills = recent_bills.order_by(Bill.bill_date.desc()).limit(5).all()
    bills_data = []
    for bill, shopkeeper_name in recent_bills:
        bills_data.append({
            'bill_id': bill.bill_id,
            'shopkeeper_name': shopkeeper_name,
            'bill_number': bill.bill_number,
            'bill_date': bill.bill_date,
            'total_amount': bill.total_amount,
            'payment_status': bill.payment_status
        })
    return render_template('ca/dashboard.html',
        total_clients=total_clients,
        new_connections=new_connections,
        pending_approvals=pending_approvals,
        recent_bills=bills_data,
        firm_name=firm_name)

@ca_bp.route('/clients')
@login_required
def clients():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    connections = CAConnection.query.filter_by(ca_id=ca.ca_id).all()
    clients = []
    for conn in connections:
        shop = Shopkeeper.query.get(conn.shopkeeper_id)
        clients.append({
            'shopkeeper_id': shop.shopkeeper_id,
            'shop_name': shop.shop_name,
            'domain': shop.domain,
            'contact_number': shop.contact_number,
            'status': conn.status
        })
    return render_template('ca/clients.html', clients=clients, firm_name=firm_name)

@ca_bp.route('/bills', methods=['GET', 'POST'])
@login_required
def bills_panel():
    # Allow both CA and CA employees
    if current_user.role not in ['CA', 'employee']:
        flash('Access denied: Invalid role.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Get CA information
    ca = None
    firm_name = None
    
    if current_user.role == 'CA':
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if ca:
            firm_name = ca.firm_name
    elif current_user.role == 'employee':
        employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
        if employee:
            ca = CharteredAccountant.query.get(employee.ca_id)
            if ca:
                firm_name = f"{ca.firm_name} (Employee View)"
    
    if not ca:
        flash('Error: Could not find CA information.', 'danger')
        return redirect(url_for('auth.login'))
    # Filters
    shopkeeper_id = request.args.get('shopkeeper_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query for bills and shopkeeper names
    query = db.session.query(Bill, Shopkeeper.shop_name).join(
        Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id
    )
    
    # Modify query based on role
    if current_user.role == 'CA':
        # For CA, show bills from all connected shopkeepers
        query = query.join(
            CAConnection,
            and_(
                CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id,
                CAConnection.ca_id == ca.ca_id,
                CAConnection.status == 'approved'
            )
        )
    elif current_user.role == 'employee':
        # For employee, show only bills from assigned shopkeepers
        employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
        if employee:
            query = query.join(
                EmployeeClient,
                and_(
                    EmployeeClient.shopkeeper_id == Shopkeeper.shopkeeper_id,
                    EmployeeClient.employee_id == employee.employee_id
                )
            )
    if shopkeeper_id:
        query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
    if start_date:
        query = query.filter(Bill.bill_date >= start_date)
    if end_date:
        query = query.filter(Bill.bill_date <= end_date)
    bills = query.order_by(Bill.bill_date.desc()).all()
    bills_data = []
    print(f"Found {len(bills)} bills")
    for bill, shopkeeper_name in bills:
        try:
            bills_data.append({
                'bill_id': bill.bill_id,
                'shopkeeper_name': shopkeeper_name,
                'bill_number': bill.bill_number,
                'bill_date': bill.bill_date,
                'total_amount': bill.total_amount,
                'payment_status': bill.payment_status
            })
            print(f"Added bill {bill.bill_id} to bills_data")
        except Exception as e:
            print(f"Error processing bill: {e}")
    # Shopkeepers for filter dropdown
    shopkeepers = Shopkeeper.query.join(CAConnection, and_(CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id, CAConnection.ca_id == ca.ca_id)).all()
    return render_template('ca/bills.html', bills=bills_data, shopkeepers=shopkeepers, firm_name=firm_name)

@ca_bp.route('/employees')
@login_required
def employees():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    employees = CAEmployee.query.filter_by(ca_id=ca.ca_id).all()
    employees_data = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        # Assigned clients
        client_ids = [ec.shopkeeper_id for ec in emp.employee_clients]
        clients = Shopkeeper.query.filter(Shopkeeper.shopkeeper_id.in_(client_ids)).all() if client_ids else []
        employees_data.append({
            'employee_id': emp.employee_id,
            'name': emp.name,
            'email': emp.email,
            'plain_password': user.plain_password if user else '',
            'clients': [{'shop_name': c.shop_name} for c in clients]
        })
    return render_template('ca/employees.html', employees=employees_data,firm_name=firm_name)

@ca_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    # Get all shopkeepers for this CA
    shopkeepers = Shopkeeper.query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved')).all()
    shop_choices = [(shop.shopkeeper_id, shop.shop_name) for shop in shopkeepers]
    form = EmployeeRegistrationForm()
    form.shop_id.choices = shop_choices
    if form.validate_on_submit():
        # Create user
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.name.data, email=form.email.data, password_hash=hashed_password, role='employee', plain_password=form.password.data)
        db.session.add(user)
        db.session.flush()  # Get user_id
        # Create CAEmployee
        ca_employee = CAEmployee(ca_id=ca.ca_id, user_id=user.user_id, name=form.name.data, email=form.email.data)
        db.session.add(ca_employee)
        db.session.flush()  # Get employee_id
        # Assign to shop
        emp_client = EmployeeClient(employee_id=ca_employee.employee_id, shopkeeper_id=form.shop_id.data)
        db.session.add(emp_client)
        db.session.commit()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('ca.employees'))
    return render_template('ca/employee_add.html', form=form, firm_name=firm_name)

@ca_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    employee = CAEmployee.query.get_or_404(employee_id)
    user = User.query.get(employee.user_id)
    # Get all shopkeepers for this CA
    shopkeepers = Shopkeeper.query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved')).all()
    shop_choices = [(shop.shopkeeper_id, shop.shop_name) for shop in shopkeepers]
    # Get current shop assignment
    current_client = EmployeeClient.query.filter_by(employee_id=employee.employee_id).first()
    form = EmployeeEditForm(obj=employee)
    form.shop_id.choices = shop_choices
    if request.method == 'GET' and current_client:
        form.shop_id.data = current_client.shopkeeper_id
        form.name.data = employee.name
        form.email.data = employee.email
    if form.validate_on_submit():
        # Update user
        user.username = form.name.data
        user.email = form.email.data
        if form.password.data:
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(form.password.data)
            user.plain_password = form.password.data
        # Update CAEmployee
        employee.name = form.name.data
        employee.email = form.email.data
        # Update shop assignment
        if current_client and current_client.shopkeeper_id != form.shop_id.data:
            current_client.shopkeeper_id = form.shop_id.data
        elif not current_client:
            new_client = EmployeeClient(employee_id=employee.employee_id, shopkeeper_id=form.shop_id.data)
            db.session.add(new_client)
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('ca.employees'))
    return render_template('ca/employee_edit.html', form=form)

@ca_bp.route('/employees/<int:employee_id>/remove')
@login_required
def remove_employee(employee_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    # Placeholder: Remove employee logic
    flash('Employee removed (placeholder)', 'success')
    return redirect(url_for('ca.employees'))

@ca_bp.route('/employees/<int:employee_id>/assign', methods=['GET', 'POST'])
@login_required
def assign_clients(employee_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    if request.method == 'POST':
        # Placeholder: Assign/unassign clients logic
        flash('Clients assigned (placeholder)', 'success')
        return redirect(url_for('ca.employees'))
    return render_template('ca/employee_assign.html', employee_id=employee_id)

@ca_bp.route('/clients/<int:shopkeeper_id>')
@login_required
def client_profile(shopkeeper_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    shop = Shopkeeper.query.get(shopkeeper_id)
    if not shop:
        flash('Client not found', 'danger')
        return redirect(url_for('ca.clients'))
    documents = shop.documents  # List of Document objects
    return render_template('ca/client_profile.html', client=shop, documents=documents)

@ca_bp.route('/export/all')
@login_required
def export_all_bills():
    # Placeholder: implement Excel/Tally export logic
    flash('Export feature coming soon!', 'info')
    return redirect(url_for('ca.dashboard'))

@ca_bp.route('/bills/export_bulk', methods=['POST'])
@login_required
def export_bulk_bills():
    # Placeholder: implement bulk export logic
    flash('Bulk export feature coming soon!', 'info')
    return redirect(url_for('ca.bills_panel'))

@ca_bp.route('/reports', methods=['GET', 'POST'])
@login_required
def reports():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    shopkeepers = Shopkeeper.query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved')).all()
    preview_bills = []
    shopkeeper_id = None
    start_date = None
    end_date = None
    if request.method == 'POST' and request.form.get('preview') == '1':
        shopkeeper_id = request.form.get('shopkeeper_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        query = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
        query = query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved'))
        if shopkeeper_id:
            query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        bills = query.order_by(Bill.bill_date.desc()).limit(5).all()
        for bill, shop_name in bills:
            preview_bills.append({
                'Date': bill.bill_date.strftime('%d-%m-%Y'),
                'Voucher Type': 'Sales',
                'Party Name': shop_name,
                'Bill No': bill.bill_number,
                'GST Type': bill.gst_type,
                'Total Amount': bill.total_amount,
                'Payment Status': bill.payment_status,
            })
    return render_template('ca/reports.html', shopkeepers=shopkeepers, firm_name=firm_name, preview_bills=preview_bills, selected_shopkeeper_id=shopkeeper_id, selected_start_date=start_date, selected_end_date=end_date)

@ca_bp.route('/export_bills', methods=['POST'])
@login_required
def export_bills():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    # Get filters
    shopkeeper_id = request.form.get('shopkeeper_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    # Query bills
    query = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
    query = query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved'))
    if shopkeeper_id:
        query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
    if start_date:
        query = query.filter(Bill.bill_date >= start_date)
    if end_date:
        query = query.filter(Bill.bill_date <= end_date)
    bills = query.order_by(Bill.bill_date.desc()).all()
    # Prepare data for Tally-compatible Excel
    data = []
    for bill, shop_name in bills:
        data.append({
            'Date': bill.bill_date.strftime('%d-%m-%Y'),
            'Voucher Type': 'Sales',
            'Party Name': shop_name,
            'Bill No': bill.bill_number,
            'GST Type': bill.gst_type,
            'Total Amount': bill.total_amount,
            'Payment Status': bill.payment_status,
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Bills')
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='bills_tally.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@ca_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def ca_profile():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    edit_mode = request.args.get('edit', '0') == '1'
    form = CAProfileForm(obj=ca)
    if form.validate_on_submit():
        ca.firm_name = form.firm_name.data
        ca.area = form.area.data
        ca.contact_number = form.contact_number.data
        ca.gst_number = form.gst_number.data
        ca.pan_number = form.pan_number.data
        ca.address = form.address.data
        ca.gstin = form.gstin.data
        # Handle file uploads
        upload_folder = os.path.join('app', 'static', 'ca_upload')
        os.makedirs(upload_folder, exist_ok=True)
        def save_file(field, old_path=None):
            file = getattr(form, field).data
            if file:
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                return f'ca_upload/{filename}'
            return old_path
        ca.aadhaar_file = save_file('aadhaar_file', ca.aadhaar_file)
        ca.pan_file = save_file('pan_file', ca.pan_file)
        ca.icai_certificate_file = save_file('icai_certificate_file', ca.icai_certificate_file)
        ca.cop_certificate_file = save_file('cop_certificate_file', ca.cop_certificate_file)
        ca.business_reg_file = save_file('business_reg_file', ca.business_reg_file)
        ca.bank_details_file = save_file('bank_details_file', ca.bank_details_file)
        ca.photo_file = save_file('photo_file', ca.photo_file)
        ca.signature_file = save_file('signature_file', ca.signature_file)
        ca.office_address_proof_file = save_file('office_address_proof_file', ca.office_address_proof_file)
        ca.self_declaration_file = save_file('self_declaration_file', ca.self_declaration_file)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('ca.ca_profile'))
    return render_template('ca/ca_profile.html', form=form, ca=ca, edit_mode=edit_mode, firm_name=firm_name)

@ca_bp.route('/employee_dashboard')
@login_required
def employee_dashboard():
    # Only for employees
    from flask_login import current_user
    if current_user.role != 'employee':
        return redirect(url_for('ca.dashboard'))
    ca_employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
    # Get all clients assigned to this employee
    emp_clients = EmployeeClient.query.filter_by(employee_id=ca_employee.employee_id).all()
    client_ids = [ec.shopkeeper_id for ec in emp_clients]
    clients = Shopkeeper.query.filter(Shopkeeper.shopkeeper_id.in_(client_ids)).all() if client_ids else []
    # For each client, get GST status for current month
    current_month = datetime.now().strftime('%Y-%m')
    gst_status_map = {}
    for client in clients:
        status_obj = GSTFilingStatus.query.filter_by(shopkeeper_id=client.shopkeeper_id, month=current_month).first()
        gst_status_map[client.shopkeeper_id] = status_obj.status if status_obj else 'Not Filed'
    return render_template('ca/employee_dashboard.html', clients=clients, gst_status_map=gst_status_map, current_month=current_month)

@ca_bp.route('/employee_client_dashboard/<int:shopkeeper_id>', methods=['GET', 'POST'])
@login_required
def employee_client_dashboard(shopkeeper_id):
    from flask_login import current_user
    if current_user.role != 'employee':
        return redirect(url_for('ca.dashboard'))
    ca_employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
    # Use class-bound attribute for joinedload
    shopkeeper = Shopkeeper.query.options(joinedload(Shopkeeper.bills)).get_or_404(shopkeeper_id)
    # Only allow if this employee is assigned to this client
    emp_client = EmployeeClient.query.filter_by(employee_id=ca_employee.employee_id, shopkeeper_id=shopkeeper_id).first()
    if not emp_client:
        flash('You are not assigned to this client.', 'danger')
        return redirect(url_for('ca.employee_dashboard'))
    # Month selector
    months = []
    now = datetime.now()
    for i in range(0, 12):
        m = (now.month - i - 1) % 12 + 1
        y = now.year - ((now.month - i - 1) // 12)
        months.append(f"{y}-{m:02d}")
    selected_month = request.args.get('month') or now.strftime('%Y-%m')
    # GST status for selected month
    gst_status_obj = GSTFilingStatus.query.filter_by(shopkeeper_id=shopkeeper_id, month=selected_month).first()
    gst_status = gst_status_obj.status if gst_status_obj else 'Not Filed'
    # Mark as Filed
    if request.method == 'POST' and request.form.get('action') == 'mark_filed':
        if not gst_status_obj:
            gst_status_obj = GSTFilingStatus(shopkeeper_id=shopkeeper_id, employee_id=ca_employee.employee_id, month=selected_month, status='Filed', filed_at=datetime.now())
            db.session.add(gst_status_obj)
        else:
            gst_status_obj.status = 'Filed'
            gst_status_obj.filed_at = datetime.now()
        db.session.commit()
        flash('GST status marked as Filed.', 'success')
        return redirect(url_for('ca.employee_client_dashboard', shopkeeper_id=shopkeeper_id, month=selected_month))
    # Bills for selected month
    bills = [bill for bill in shopkeeper.bills if bill.bill_date.strftime('%Y-%m') == selected_month]
    # Export bills to Excel
    if request.method == 'POST' and request.form.get('action') == 'export_excel':
        import pandas as pd
        from flask import send_file
        data = []
        for bill in bills:
            data.append({'Bill No.': bill.bill_number, 'Amount': float(bill.total_amount)})
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Bills')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f'bills_{selected_month}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # Export bills to PDF (placeholder, implement as needed)
    if request.method == 'POST' and request.form.get('action') == 'export_pdf':
        flash('PDF export not implemented yet.', 'info')
        return redirect(url_for('ca.employee_client_dashboard', shopkeeper_id=shopkeeper_id, month=selected_month))
    return render_template('ca/employee_client_dashboard.html', shopkeeper=shopkeeper, bills=bills, months=months, selected_month=selected_month, gst_status=gst_status)

@ca_bp.route('/connection_requests', methods=['GET', 'POST'])
@login_required
def connection_requests():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    if request.method == 'POST':
        conn_id = request.form.get('conn_id')
        action = request.form.get('action')
        conn = CAConnection.query.get(conn_id)
        if conn and conn.ca_id == ca.ca_id and conn.status == 'pending':
            if action == 'accept':
                conn.status = 'approved'
                db.session.commit()
                flash('Connection approved.', 'success')
            elif action == 'reject':
                conn.status = 'rejected'
                db.session.commit()
                flash('Connection rejected.', 'info')
        return redirect(url_for('ca.connection_requests'))
    # GET: show pending requests
    pending = CAConnection.query.filter_by(ca_id=ca.ca_id, status='pending').all()
    requests = []
    for conn in pending:
        shop = Shopkeeper.query.get(conn.shopkeeper_id)
        requests.append({
            'conn_id': conn.id,
            'shopkeeper_id': shop.shopkeeper_id,
            'shop_name': shop.shop_name,
            'domain': shop.domain,
            'contact_number': shop.contact_number
        })
    return render_template('ca/connection_requests.html', requests=requests)

@ca_bp.route('/shopkeeper_marketplace', methods=['GET', 'POST'])
@login_required
def shopkeeper_marketplace():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    shopkeepers = []
    if request.method == 'POST':
        area = request.form.get('area')
        domain = request.form.get('domain')
        query = Shopkeeper.query
        if area:
            query = query.filter(Shopkeeper.address.ilike(f'%{area}%'))
        if domain:
            query = query.filter(Shopkeeper.domain.ilike(f'%{domain}%'))
        shopkeepers = query.all()
    else:
        shopkeepers = Shopkeeper.query.all()
    # Get connection status for each shopkeeper
    connections = {c.shopkeeper_id: c for c in CAConnection.query.filter_by(ca_id=ca.ca_id).all()}
    return render_template('ca/shopkeeper_marketplace.html', shopkeepers=shopkeepers, connections=connections)

@ca_bp.route('/connect_shopkeeper/<int:shopkeeper_id>', methods=['POST'])
@login_required
def connect_shopkeeper(shopkeeper_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    existing = CAConnection.query.filter_by(shopkeeper_id=shopkeeper_id, ca_id=ca.ca_id).first()
    if not existing:
        conn = CAConnection(shopkeeper_id=shopkeeper_id, ca_id=ca.ca_id, status='pending')
        db.session.add(conn)
        db.session.commit()
        flash('Connection request sent.', 'success')
    else:
        if existing.status == 'pending':
            flash('Request already sent and pending approval.', 'info')
        elif existing.status == 'approved':
            flash('You are already connected with this shopkeeper.', 'info')
        elif existing.status == 'rejected':
            # Allow resending if rejected
            existing.status = 'pending'
            db.session.commit()
            flash('Connection request resent.', 'success')
    return redirect(url_for('ca.shopkeeper_marketplace'))

@ca_bp.route('/handle_shop_connection_request', methods=['POST'])
@login_required
def handle_shop_connection_request():
    pass

@ca_bp.route('/bill/<int:bill_id>')
@login_required
def view_bill(bill_id):
    print(f"Accessing bill {bill_id} by user {current_user.user_id} with role {current_user.role}")
    
    # Allow access only for CA and employees
    if current_user.role not in ['CA', 'employee']:
        flash('Access denied: Invalid role.', 'danger')
        return redirect(url_for('auth.login'))

    bill = Bill.query.get_or_404(bill_id)
    print(f"Found bill {bill.bill_id} for shopkeeper {bill.shopkeeper_id}")

    # Initialize access check
    is_editable = False

    if current_user.role == 'CA':
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if ca:
            ca_conn = CAConnection.query.filter_by(
                shopkeeper_id=bill.shopkeeper_id,
                ca_id=ca.ca_id,
                status='approved'
            ).first()
            is_editable = bool(ca_conn)
            print(f"CA {ca.ca_id} connection status with shopkeeper {bill.shopkeeper_id}: {is_editable}")

    elif current_user.role == 'employee':
        employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
        if employee:
            emp_client = EmployeeClient.query.filter_by(
                shopkeeper_id=bill.shopkeeper_id,
                employee_id=employee.employee_id
            ).first()
            is_editable = bool(emp_client)
            print(f"Employee-Client access status: {is_editable}")

    if not is_editable:
        flash('Access denied: You are not authorized to view this bill.', 'danger')
        return redirect(url_for('ca.bills_panel'))

    # Determine correct back_url based on role
    if current_user.role == 'CA':
        back_url = url_for('ca.bills_panel')
    elif current_user.role == 'employee':
        back_url = url_for('ca.employee_dashboard')
    else:
        back_url = url_for('auth.login')

    print(f"Rendering bill view for role {current_user.role}, back_url = {back_url}")

    # Download PDF flag
    is_download = request.args.get('download') == 'true'

    # Get bill items and related data
    bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
    shopkeeper = bill.shopkeeper
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    products_dict = {str(p.product_id): p for p in products}

    # GST Summary calculations
    bill_items_data = []
    gst_summary_by_rate = {}
    total_taxable_amount = 0
    total_cgst_amount = 0
    total_sgst_amount = 0
    total_gst_amount = 0
    overall_grand_total = 0

    for item in bill_items:
        product = products_dict.get(str(item.product_id))
        if not product:
            continue
        base_price = float(item.price_per_unit)
        quantity = int(item.quantity)
        total_price = base_price * quantity

        discount = 0
        discount_amount = (discount / 100) * total_price
        discounted_price = total_price - discount_amount

        gst_rate = float(product.gst_rate or 0)
        sgst_rate = cgst_rate = gst_rate / 2
        sgst_amount = (sgst_rate / 100) * discounted_price
        cgst_amount = (cgst_rate / 100) * discounted_price
        final_price = discounted_price + sgst_amount + cgst_amount

        item_data = {
            'product': product,
            'hsn_code': product.hsn_code if hasattr(product, 'hsn_code') else '',
            'quantity': quantity,
            'base_price': base_price,
            'discount': discount,
            'discount_amount': discount_amount,
            'discounted_price': discounted_price,
            'sgst_rate': sgst_rate,
            'sgst_amount': sgst_amount,
            'cgst_rate': cgst_rate,
            'cgst_amount': cgst_amount,
            'final_price': final_price
        }
        bill_items_data.append(item_data)

        gst_summary_by_rate.setdefault(gst_rate, {
            'taxable_amount': 0,
            'cgst_amount': 0,
            'sgst_amount': 0,
            'total_gst_amount': 0
        })

        gst_summary_by_rate[gst_rate]['taxable_amount'] += discounted_price
        gst_summary_by_rate[gst_rate]['cgst_amount'] += cgst_amount
        gst_summary_by_rate[gst_rate]['sgst_amount'] += sgst_amount
        gst_summary_by_rate[gst_rate]['total_gst_amount'] += (cgst_amount + sgst_amount)

        total_taxable_amount += discounted_price
        total_cgst_amount += cgst_amount
        total_sgst_amount += sgst_amount
        total_gst_amount += (cgst_amount + sgst_amount)
        overall_grand_total += final_price

    template_data = {
        'bill': bill,
        'bill_items_data': bill_items_data,
        'shopkeeper': shopkeeper,
        'products': products_dict,
        'gst_summary_by_rate': gst_summary_by_rate,
        'total_taxable_amount': total_taxable_amount,
        'total_cgst_amount': total_cgst_amount,
        'total_sgst_amount': total_sgst_amount,
        'total_gst_amount': total_gst_amount,
        'overall_grand_total': overall_grand_total,
        'is_editable': is_editable,
        'back_url': back_url  # ✅ Correct dynamic back URL passed to template
    }

    if is_download:
        from weasyprint import HTML
        html = render_template('shopkeeper/bill_receipt.html', **template_data, is_editable=False)
        pdf = HTML(string=html).write_pdf()
        return send_file(
            io.BytesIO(pdf),
            download_name=f'bill_{bill.bill_number}.pdf',
            mimetype='application/pdf'
        )

    return render_template('shopkeeper/bill_receipt.html', **template_data)

@ca_bp.route('/bill/<int:bill_id>/edit', methods=['POST'])
@login_required
def update_bill_ca(bill_id):
    bill = Bill.query.get_or_404(bill_id)

    # Access control
    if current_user.role == 'CA':
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        allowed = CAConnection.query.filter_by(shopkeeper_id=bill.shopkeeper_id, ca_id=ca.ca_id, status='approved').first()
        if not allowed:
            flash("Access denied: CA not connected to this client.", "danger")
            return redirect(url_for('ca.bills_panel'))

    elif current_user.role == 'employee':
        employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
        allowed = EmployeeClient.query.filter_by(shopkeeper_id=bill.shopkeeper_id, employee_id=employee.employee_id).first()
        if not allowed:
            flash("Access denied: Employee not assigned to this client.", "danger")
            return redirect(url_for('ca.bills_panel'))

    else:
        flash("Access denied: Unauthorized role.", "danger")
        return redirect(url_for('auth.login'))

    # ✅ Now update the bill data
    customer_name = request.form.get('customer_name')
    customer_contact = request.form.get('customer_contact')
    item_ids = request.form.getlist('item_id[]')
    quantities = request.form.getlist('quantity[]')
    prices = request.form.getlist('price[]')

    print("CA update called")
    print("Form data:", request.form)

    bill.customer_name = customer_name
    bill.customer_contact = customer_contact

    # Delete old items
    BillItem.query.filter_by(bill_id=bill.bill_id).delete()

    total_base = 0
    total_gst = 0

    for pid, qty, price in zip(item_ids, quantities, prices):
        qty = int(qty)
        price = float(price)
        total_price = qty * price

        bill_item = BillItem(
            bill_id=bill.bill_id,
            product_id=pid,
            quantity=qty,
            price_per_unit=price,
            total_price=total_price
        )
        db.session.add(bill_item)

        # GST calculation
        product = Product.query.get(pid)
        gst_rate = float(product.gst_rate or 0)
        total_base += total_price
        total_gst += (total_price * gst_rate / 100)

    bill.total_amount = round(total_base + total_gst, 2)
    db.session.commit()

    flash("Bill updated successfully.", "success")
    print("Logged in as:", current_user.username, "Role:", current_user.role)

    # Redirect dynamically based on role
    if current_user.role == 'employee':
        return redirect(url_for('ca.employee_dashboard'))
    elif current_user.role == 'CA':
        return redirect(url_for('ca.view_bill', bill_id=bill_id))
    else:  # shopkeeper
        return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))
