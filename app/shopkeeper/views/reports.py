"""
Sales reports routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request
from flask_login import login_required, current_user
import datetime

from ..utils import shopkeeper_required
from app.models import Bill, Shopkeeper
from app.extensions import db


def register_routes(bp):
    """Register sales reports routes to the blueprint."""
    
    @bp.route('/sales_reports')
    @login_required
    @shopkeeper_required
    def sales_reports():
        """Sales reports with date filtering - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        # Original verification check commented out
        # if not shopkeeper.is_verified:
        #     flash('Please upload all required documents to use this service.', 'danger')
        #     return redirect(url_for('shopkeeper.profile'))
        
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=6)
        
        start = request.args.get('start')
        end = request.args.get('end')
        
        if not start:
            start = default_start.strftime('%Y-%m-%d')
        if not end:
            end = today.strftime('%Y-%m-%d')
        
        # Convert to date objects
        start_date = datetime.datetime.strptime(start, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end, '%Y-%m-%d').date()
        
        # Query bills in range
        query = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
        query = query.filter(Bill.bill_date >= start_date, Bill.bill_date <= end_date)
        bills = query.order_by(Bill.bill_date.desc()).all()
        
        # Build date list for the selected range
        num_days = (end_date - start_date).days + 1
        date_list = [(start_date + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_days)]
        chart_data = {d: 0 for d in date_list}
        
        for bill in bills:
            bill_date_str = bill.bill_date.strftime('%Y-%m-%d')
            if bill_date_str in chart_data:
                chart_data[bill_date_str] += float(bill.total_amount)
        
        chart_labels = list(chart_data.keys())
        chart_values = list(chart_data.values())
        
        return render_template('shopkeeper/sales_reports.html', 
                             shop_name=shop_name,
                             bills=bills, 
                             chart_labels=chart_labels, 
                             chart_values=chart_values, 
                             start=start, 
                             end=end)