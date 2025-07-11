from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.models import db, User, Shopkeeper, CharteredAccountant, CAEmployee, EmployeeClient, Bill, CAConnection
from sqlalchemy import func, and_, or_

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
        recent_bills=bills_data)

@ca_bp.route('/clients')
@login_required
def clients():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
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
    return render_template('ca/clients.html', clients=clients)

@ca_bp.route('/bills', methods=['GET', 'POST'])
@login_required
def bills_panel():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
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
    return render_template('ca/bills.html', bills=bills_data, shopkeepers=shopkeepers)

@ca_bp.route('/employees')
@login_required
def employees():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
    employees = CAEmployee.query.filter_by(ca_id=ca.ca_id).all()
    employees_data = []
    for emp in employees:
        # Assigned clients
        client_ids = [ec.shopkeeper_id for ec in emp.employee_clients]
        clients = Shopkeeper.query.filter(Shopkeeper.shopkeeper_id.in_(client_ids)).all() if client_ids else []
        employees_data.append({
            'employee_id': emp.employee_id,
            'name': emp.name,
            'email': emp.email,
            'clients': [{'shop_name': c.shop_name} for c in clients]
        })
    return render_template('ca/employees.html', employees=employees_data)

@ca_bp.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    if request.method == 'POST':
        # Placeholder: Add employee logic
        flash('Employee added (placeholder)', 'success')
        return redirect(url_for('ca.employees'))
    return render_template('ca/employee_add.html')

@ca_bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    if current_user.role != 'CA':
        return redirect(url_for('ca.dashboard'))
    if request.method == 'POST':
        # Placeholder: Edit employee logic
        flash('Employee updated (placeholder)', 'success')
        return redirect(url_for('ca.employees'))
    return render_template('ca/employee_edit.html', employee_id=employee_id)

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
    return render_template('ca/client_profile.html', client=shop)

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

@ca_bp.route('/employee_dashboard')
@login_required
def employee_dashboard():
    return render_template('ca/employee_dashboard.html')
