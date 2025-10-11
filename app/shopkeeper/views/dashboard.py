"""
Dashboard routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
import datetime
from dateutil.relativedelta import relativedelta

from ..utils import shopkeeper_required, get_current_shopkeeper
from app.models import Bill, Product, CAConnection, CharteredAccountant, CAEmployee, EmployeeClient, Shopkeeper
from app.extensions import db


def register_routes(bp):
    """Register dashboard routes to the blueprint."""
    
    @bp.route('/')
    def shopkeeper_root():
        return redirect(url_for('shopkeeper.dashboard'))
    
    @bp.route('/dashboard')
    @login_required
    @shopkeeper_required
    def dashboard():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        if not shopkeeper:
            return render_template('shopkeeper/dashboard.html',
                total_amount=0, paid=0, unpaid=0, partial=0,
                monthly_total=0, monthly_bills_count=0, monthly_growth=0,
                low_stock=[], recent_bills=[], connected_ca=None, connected_employees=[],
                monthly_sales_labels=[], monthly_sales_data=[]
            )
        
        shopkeeper_id = shopkeeper.shopkeeper_id

        # Today's Sales summary
        today = datetime.date.today()
        bills_today = Bill.query.filter_by(shopkeeper_id=shopkeeper_id, bill_date=today).all()
        total_amount = sum(float(b.total_amount) for b in bills_today)
        paid = sum(1 for b in bills_today if b.payment_status == 'Paid')
        unpaid = sum(1 for b in bills_today if b.payment_status == 'Unpaid')
        partial = sum(1 for b in bills_today if b.payment_status == 'Partial')
        
        # Monthly Sales Summary
        first_day_of_current_month = today.replace(day=1)
        bills_this_month = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)\
            .filter(Bill.bill_date >= first_day_of_current_month, Bill.bill_date <= today).all()
        monthly_total = sum(float(b.total_amount) for b in bills_this_month)
        monthly_bills_count = len(bills_this_month)

        # Calculate growth percentage from last month
        last_month_start = first_day_of_current_month - relativedelta(months=1)
        last_month_end = first_day_of_current_month - datetime.timedelta(days=1)
        bills_last_month = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)\
            .filter(Bill.bill_date >= last_month_start, Bill.bill_date <= last_month_end).all()
        last_month_total = sum(float(b.total_amount) for b in bills_last_month)
        
        monthly_growth = 0
        if last_month_total > 0:
            monthly_growth = ((monthly_total - last_month_total) / last_month_total) * 100
        
        # Get monthly sales data for chart (last 6 months)
        monthly_sales_data = []
        monthly_sales_labels = []
        
        for i in range(5, -1, -1):
            month_to_fetch = today - relativedelta(months=i)
            start_of_month = month_to_fetch.replace(day=1)
            end_of_month = (start_of_month + relativedelta(months=1)) - datetime.timedelta(days=1)
            
            monthly_bills = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)\
                .filter(Bill.bill_date >= start_of_month, Bill.bill_date <= end_of_month).all()
            
            sales_for_month = sum(float(b.total_amount) for b in monthly_bills)
            
            monthly_sales_data.append(sales_for_month)
            monthly_sales_labels.append(month_to_fetch.strftime('%b %Y'))
        
        # Low stock
        low_stock = Product.query.filter_by(shopkeeper_id=shopkeeper_id)\
            .filter(Product.stock_qty <= Product.low_stock_threshold).all()
        
        # CA connection and employees
        ca_conn = CAConnection.query.filter_by(shopkeeper_id=shopkeeper_id, status='approved').first()
        connected_ca = None
        connected_employees = []
        
        if ca_conn:
            connected_ca = CharteredAccountant.query.get(ca_conn.ca_id)
            if connected_ca:
                connected_employees = db.session.query(CAEmployee)\
                    .join(EmployeeClient, CAEmployee.employee_id == EmployeeClient.employee_id)\
                    .filter(EmployeeClient.shopkeeper_id == shopkeeper_id)\
                    .all()
        
        # Recent bills
        recent_bills = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)\
            .order_by(Bill.bill_date.desc()).limit(5).all()
        
        # Check if this is first time login (no bills created yet and walkthrough not completed)
        show_walkthrough = (len(recent_bills) == 0 and 
                          not current_user.walkthrough_completed and 
                          current_user.role == 'shopkeeper')
        
        return render_template('shopkeeper/dashboard.html',
            total_amount=total_amount,
            paid=paid,
            unpaid=unpaid,
            partial=partial,
            monthly_total=monthly_total,
            monthly_bills_count=monthly_bills_count,
            monthly_growth=round(monthly_growth, 1),
            low_stock=low_stock,
            recent_bills=recent_bills,
            connected_ca=connected_ca,
            connected_employees=connected_employees,
            monthly_sales_labels=monthly_sales_labels,
            monthly_sales_data=monthly_sales_data,
            show_walkthrough=show_walkthrough
        )