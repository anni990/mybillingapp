"""
Dashboard routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_

from app.models import (CharteredAccountant, CAConnection, CAEmployee, EmployeeClient, 
                       Bill, Shopkeeper, GSTFilingStatus)
from app.extensions import db


def register_routes(bp):
    """Register dashboard routes to the blueprint."""
    
    @bp.route('/')
    def ca_root():
        """Root redirect - preserves original logic."""
        return redirect(url_for('ca.dashboard'))

    @bp.route('/employee')
    def ca_employee_root():
        """Employee root redirect - preserves original logic."""
        return redirect(url_for('ca.employee_dashboard'))

    @bp.route('/dashboard')
    @login_required
    def dashboard():
        """CA dashboard - preserves original logic."""
        # Only CA can access
        if current_user.role != 'CA':
            return redirect(url_for('ca.employee_dashboard'))
        
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        if not ca:
            return redirect(url_for('auth.login'))
        
        firm_name = ca.firm_name
        current_month = datetime.now().strftime('%Y-%m')
        current_year = datetime.now().year
        current_month_num = datetime.now().month
        
        # Basic metrics
        total_clients = CAConnection.query.filter_by(ca_id=ca.ca_id, status='approved').count()
        total_employees = CAEmployee.query.filter_by(ca_id=ca.ca_id).count()
        pending_approvals = CAConnection.query.filter_by(ca_id=ca.ca_id, status='pending').count()
        
        # Removed monthly revenue calculation
        
        # Recent bills (last 5)
        recent_bills = db.session.query(Bill, Shopkeeper.shop_name).join(
            Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id
        ).join(
            CAConnection, and_(
                CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id,
                CAConnection.ca_id == ca.ca_id,
                CAConnection.status == 'approved'
            )
        ).order_by(Bill.bill_date.desc()).limit(5).all()
        
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
        
        # GST Filing Status for current month
        connected_shopkeepers = db.session.query(Shopkeeper).join(
            CAConnection, and_(
                CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id,
                CAConnection.ca_id == ca.ca_id,
                CAConnection.status == 'approved'
            )
        ).all()
        
        gst_filed_count = 0
        gst_pending_count = 0
        gst_pending_clients = []
        
        for shopkeeper in connected_shopkeepers:
            gst_status = GSTFilingStatus.query.filter_by(
                shopkeeper_id=shopkeeper.shopkeeper_id,
                month=current_month
            ).first()
            
            if gst_status and gst_status.status == 'Filed':
                gst_filed_count += 1
            else:
                gst_pending_count += 1
                gst_pending_clients.append(shopkeeper)
        
        # Employee performance
        employee_performance = []
        employees = CAEmployee.query.filter_by(ca_id=ca.ca_id).all()
        
        for employee in employees:
            # Count assigned clients
            client_count = EmployeeClient.query.filter_by(employee_id=employee.employee_id).count()
            
            # Count GST filings done by this employee this month
            gst_filed = GSTFilingStatus.query.filter_by(
                employee_id=employee.employee_id,
                month=current_month,
                status='Filed'
            ).count()
            
            employee_performance.append({
                'name': employee.name,
                'client_count': client_count,
                'gst_filed': gst_filed
            })
        
        # Pending connection requests with shopkeeper details
        pending_connections_query = db.session.query(
            CAConnection, Shopkeeper
        ).join(
            Shopkeeper, CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id
        ).filter(
            CAConnection.ca_id == ca.ca_id,
            CAConnection.status == 'pending'
        ).order_by(CAConnection.created_at.desc()).all()
        
        pending_connections = []
        for connection, shopkeeper in pending_connections_query:
            pending_connections.append({
                'connection_id': connection.id,
                'shop_name': shopkeeper.shop_name,
                'domain': shopkeeper.domain,
                'contact_number': shopkeeper.contact_number,
                'gst_number': shopkeeper.gst_number,
                'created_at': connection.created_at
            })
        
        return render_template('ca/dashboard.html',
            firm_name=firm_name,
            total_clients=total_clients,
            total_employees=total_employees,
            pending_approvals=pending_approvals,

            recent_bills=bills_data,
            current_month=datetime.now().strftime('%B %Y'),
            gst_filed_count=gst_filed_count,
            gst_pending_count=gst_pending_count,
            gst_pending_clients=gst_pending_clients[:5],  # Show only first 5
            employee_performance=employee_performance,
            pending_connections=pending_connections
        )