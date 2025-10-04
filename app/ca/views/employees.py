"""
Employee management routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_
from werkzeug.security import generate_password_hash

from app.models import (CharteredAccountant, CAEmployee, EmployeeClient, Shopkeeper, 
                       CAConnection, User, GSTFilingStatus)
from app.extensions import db
from app.forms import EmployeeRegistrationForm, EmployeeEditForm


def register_routes(bp):
    """Register employee management routes to the blueprint."""
    
    @bp.route('/employees')
    @login_required
    def employees():
        """Employee list - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name
        employees = CAEmployee.query.filter_by(ca_id=ca.ca_id).all()
        employees_data = []
        for emp in employees:
            user = User.query.get(emp.user_id)
            # Get assigned shops count
            assigned_shops_count = EmployeeClient.query.filter_by(employee_id=emp.employee_id).count()
            
            employees_data.append({
                'employee_id': emp.employee_id,
                'name': emp.name,
                'email': emp.email,
                'plain_password': user.plain_password if user else '',
                'assigned_shops_count': assigned_shops_count
            })
        return render_template('ca/employees.html', employees=employees_data,firm_name=firm_name)

    @bp.route('/employees/add', methods=['GET', 'POST'])
    @login_required
    def add_employee():
        """Add employee - preserves original logic."""
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
            # Assign to selected shops (multi)
            for shopkeeper_id in form.shop_id.data:
                emp_client = EmployeeClient(employee_id=ca_employee.employee_id, shopkeeper_id=shopkeeper_id)
                db.session.add(emp_client)
            db.session.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('ca.employees'))
        return render_template('ca/employee_add.html', form=form, firm_name=firm_name)

    @bp.route('/employees/<int:employee_id>/remove')
    @login_required
    def remove_employee(employee_id):
        """Remove employee - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if not ca:
            return redirect(url_for('auth.login'))
        
        # Get employee and associated user
        employee = CAEmployee.query.get_or_404(employee_id)
        
        # Verify employee belongs to this CA
        if employee.ca_id != ca.ca_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('ca.employees'))
        
        try:
            # Get associated user
            user = User.query.get(employee.user_id)
            
            # Delete employee clients first (due to foreign key constraints)
            EmployeeClient.query.filter_by(employee_id=employee_id).delete()
            
            # Delete employee record
            db.session.delete(employee)
            
            # Delete user account if exists
            if user:
                db.session.delete(user)
            
            db.session.commit()
            flash('Employee removed successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error removing employee. Please try again.', 'danger')
        
        return redirect(url_for('ca.employees'))

    @bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_employee(employee_id):
        """Edit employee - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        employee = CAEmployee.query.get_or_404(employee_id)
        user = User.query.get(employee.user_id)
        # Get all shopkeepers for this CA
        shopkeepers = Shopkeeper.query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved')).all()
        shop_choices = [(shop.shopkeeper_id, shop.shop_name) for shop in shopkeepers]
        # Get current shop assignments (multi)
        current_clients = EmployeeClient.query.filter_by(employee_id=employee.employee_id).all()
        current_shop_ids = [ec.shopkeeper_id for ec in current_clients]
        form = EmployeeEditForm(obj=employee)
        form.shop_id.choices = shop_choices
        if request.method == 'GET':
            form.shop_id.data = current_shop_ids
            form.name.data = employee.name
            form.email.data = employee.email
        if form.validate_on_submit():
            # Update user
            user.username = form.name.data
            user.email = form.email.data
            if form.password.data:
                user.password_hash = generate_password_hash(form.password.data)
                user.plain_password = form.password.data
            # Update CAEmployee
            employee.name = form.name.data
            employee.email = form.email.data
            # Update shop assignments (multi)
            new_shop_ids = set(form.shop_id.data)
            old_shop_ids = set(current_shop_ids)
            # Remove unselected
            for ec in current_clients:
                if ec.shopkeeper_id not in new_shop_ids:
                    db.session.delete(ec)
            # Add new assignments
            for shopkeeper_id in new_shop_ids - old_shop_ids:
                db.session.add(EmployeeClient(employee_id=employee.employee_id, shopkeeper_id=shopkeeper_id))
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('ca.employees'))
        return render_template('ca/employee_edit.html', form=form)

    @bp.route('/employees/<int:employee_id>/assign', methods=['GET', 'POST'])
    @login_required
    def assign_clients(employee_id):
        """Assign clients to employee - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        if request.method == 'POST':
            # Placeholder: Assign/unassign clients logic
            flash('Clients assigned (placeholder)', 'success')
            return redirect(url_for('ca.employees'))
        return render_template('ca/employee_assign.html', employee_id=employee_id)
    
    @bp.route('/employee/<int:employee_id>')
    @login_required
    def employee_profile(employee_id):
        """Employee profile - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
            
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if not ca:
            return redirect(url_for('auth.login'))
        
        # Get employee details
        employee = CAEmployee.query.filter_by(employee_id=employee_id, ca_id=ca.ca_id).first_or_404()
        
        # Get assigned shops with their details
        assigned_shops_query = db.session.query(
            Shopkeeper, GSTFilingStatus.status.label('gst_status')
        ).join(
            EmployeeClient, Shopkeeper.shopkeeper_id == EmployeeClient.shopkeeper_id
        ).outerjoin(
            GSTFilingStatus, and_(
                GSTFilingStatus.shopkeeper_id == Shopkeeper.shopkeeper_id,
                GSTFilingStatus.month == datetime.now().strftime('%Y-%m')
            )
        ).filter(
            EmployeeClient.employee_id == employee_id
        ).all()
        
        assigned_shops = []
        for shop, gst_status in assigned_shops_query:
            assigned_shops.append({
                'shopkeeper_id': shop.shopkeeper_id,
                'shop_name': shop.shop_name,
                'domain': shop.domain,
                'contact_number': shop.contact_number,
                'gst_status': gst_status or 'Not Filed'
            })
        
        # Get GST filing count for current month
        gst_filed_count = GSTFilingStatus.query.filter_by(
            employee_id=employee_id,
            month=datetime.now().strftime('%Y-%m'),
            status='Filed'
        ).count()
        
        return render_template('ca/employee_profile.html',
            firm_name=ca.firm_name,
            employee=employee,
            assigned_shops=assigned_shops,
            gst_filed_count=gst_filed_count
        )