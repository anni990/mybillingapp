"""
Employee dashboard routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy.orm import joinedload
import io
import pandas as pd

from app.models import (CAEmployee, EmployeeClient, Shopkeeper, GSTFilingStatus)
from app.extensions import db


def register_routes(bp):
    """Register employee dashboard routes to the blueprint."""
    
    @bp.route('/employee_dashboard')
    @login_required
    def employee_dashboard():
        """Employee dashboard - preserves original logic."""
        # Only for employees
        if current_user.role != 'employee':
            return redirect(url_for('ca.dashboard'))
        ca_employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
        # Get all clients assigned to this employee
        emp_clients = EmployeeClient.query.filter_by(employee_id=ca_employee.employee_id).all()
        client_ids = [ec.shopkeeper_id for ec in emp_clients]
        clients = Shopkeeper.query.filter(Shopkeeper.shopkeeper_id.in_(client_ids)).all() if client_ids else []
        # Filter by shop name if requested
        shop_filter = request.args.get('shop_filter', type=int)
        if shop_filter:
            clients = [c for c in clients if c.shopkeeper_id == shop_filter]
        # For each client, get GST status for current month
        current_month = datetime.now().strftime('%Y-%m')
        gst_status_map = {}
        for client in clients:
            status_obj = GSTFilingStatus.query.filter_by(shopkeeper_id=client.shopkeeper_id, month=current_month).first()
            gst_status_map[client.shopkeeper_id] = status_obj.status if status_obj else 'Not Filed'
        return render_template('ca/employee_dashboard.html', clients=clients, gst_status_map=gst_status_map, current_month=current_month, shop_filter=shop_filter)

    @bp.route('/employee_client_dashboard/<int:shopkeeper_id>', methods=['GET', 'POST'])
    @login_required
    def employee_client_dashboard(shopkeeper_id):
        """Employee client dashboard - preserves original logic."""
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