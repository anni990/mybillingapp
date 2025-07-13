from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import db, User, Shopkeeper, CharteredAccountant, CAEmployee, EmployeeClient, Bill, CAConnection
from sqlalchemy import func, and_, or_
from app.forms import EmployeeRegistrationForm, EmployeeEditForm, CAProfileForm
from werkzeug.security import generate_password_hash
import io
import pandas as pd
from flask import send_file

ca_bp = Blueprint('ca', __name__, url_prefix='/ca')

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
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    firm_name = ca.firm_name
    # Filters
    shopkeeper_id = request.args.get('shopkeeper_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
    query = query.join(CAConnection, and_(CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id, CAConnection.ca_id == ca.ca_id, CAConnection.status == 'approved'))
    if shopkeeper_id:
        query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
    if start_date:
        query = query.filter(Bill.bill_date >= start_date)
    if end_date:
        query = query.filter(Bill.bill_date <= end_date)
    bills = query.order_by(Bill.bill_date.desc()).all()
    bills_data = []
    for bill, shopkeeper_name in bills:
        bills_data.append({
            'bill_id': bill.bill_id,
            'shopkeeper_name': shopkeeper_name,
            'bill_number': bill.bill_number,
            'bill_date': bill.bill_date,
            'total_amount': bill.total_amount,
            'payment_status': bill.payment_status
        })
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
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('ca.ca_profile'))
    return render_template('ca/ca_profile.html', form=form, ca=ca, edit_mode=edit_mode,firm_name=firm_name)

@ca_bp.route('/employee_dashboard')
@login_required
def employee_dashboard():
    # Only for employees
    from flask_login import current_user
    if current_user.role != 'employee':
        return redirect(url_for('ca.dashboard'))
    # Get employee record
    ca_employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
    shop = None
    products = []
    bills = []
    if ca_employee:
        emp_client = EmployeeClient.query.filter_by(employee_id=ca_employee.employee_id).first()
        if emp_client:
            shop = Shopkeeper.query.get(emp_client.shopkeeper_id)
            if shop:
                products = shop.products
                bills = shop.bills[:5]  # Show recent 5 bills
    return render_template('ca/employee_dashboard.html', shop=shop, products=products, bills=bills)
