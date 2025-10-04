"""
Reporting and analytics service.
Extracted from original routes.py - maintains all business logic.
"""
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, extract

from app.models import Bill, BillItem, Product, Customer, CustomerLedger
from app.extensions import db


class ReportService:
    """Service class for reports and analytics."""
    
    @staticmethod
    def get_sales_summary(shopkeeper_id: int, start_date: date = None, 
                         end_date: date = None) -> Dict:
        """Get comprehensive sales summary."""
        query = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)
        
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        
        bills = query.all()
        
        # Calculate totals
        total_bills = len(bills)
        total_sales = sum(bill.total_amount for bill in bills) or Decimal('0')
        total_gst = sum(bill.gst_amount for bill in bills) or Decimal('0')
        total_discount = sum(bill.discount_amount for bill in bills) or Decimal('0')
        total_collected = sum(bill.paid_amount for bill in bills) or Decimal('0')
        total_pending = sum(bill.due_amount for bill in bills) or Decimal('0')
        
        # Payment status breakdown
        paid_bills = len([b for b in bills if b.payment_status == 'paid'])
        partial_bills = len([b for b in bills if b.payment_status == 'partial'])
        unpaid_bills = len([b for b in bills if b.payment_status == 'unpaid'])
        
        return {
            'total_bills': total_bills,
            'total_sales': total_sales,
            'total_gst': total_gst,
            'total_discount': total_discount,
            'total_collected': total_collected,
            'total_pending': total_pending,
            'paid_bills': paid_bills,
            'partial_bills': partial_bills,
            'unpaid_bills': unpaid_bills,
            'average_bill_value': total_sales / total_bills if total_bills > 0 else Decimal('0')
        }
    
    @staticmethod
    def get_monthly_sales_chart(shopkeeper_id: int, year: int = None) -> Dict:
        """Get monthly sales data for charts."""
        if year is None:
            year = datetime.now().year
        
        # Query monthly totals
        monthly_data = db.session.query(
            extract('month', Bill.bill_date).label('month'),
            func.count(Bill.bill_id).label('bill_count'),
            func.sum(Bill.total_amount).label('total_sales'),
            func.sum(Bill.paid_amount).label('total_collected')
        ).filter(
            and_(
                Bill.shopkeeper_id == shopkeeper_id,
                extract('year', Bill.bill_date) == year
            )
        ).group_by(extract('month', Bill.bill_date)).all()
        
        # Initialize all 12 months
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        chart_data = {
            'labels': months,
            'sales': [0] * 12,
            'collections': [0] * 12,
            'bill_counts': [0] * 12
        }
        
        # Fill actual data
        for row in monthly_data:
            month_index = int(row.month) - 1
            chart_data['sales'][month_index] = float(row.total_sales or 0)
            chart_data['collections'][month_index] = float(row.total_collected or 0)
            chart_data['bill_counts'][month_index] = int(row.bill_count or 0)
        
        return chart_data
    
    @staticmethod
    def get_daily_sales_chart(shopkeeper_id: int, days: int = 30) -> Dict:
        """Get daily sales data for the last N days."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        # Query daily totals
        daily_data = db.session.query(
            Bill.bill_date,
            func.count(Bill.bill_id).label('bill_count'),
            func.sum(Bill.total_amount).label('total_sales')
        ).filter(
            and_(
                Bill.shopkeeper_id == shopkeeper_id,
                Bill.bill_date >= start_date,
                Bill.bill_date <= end_date
            )
        ).group_by(Bill.bill_date).all()
        
        # Create date range
        date_range = [(start_date + timedelta(days=x)) for x in range(days)]
        
        # Initialize data
        chart_data = {
            'labels': [d.strftime('%m-%d') for d in date_range],
            'sales': [0] * days,
            'bill_counts': [0] * days
        }
        
        # Fill actual data
        daily_dict = {row.bill_date: row for row in daily_data}
        for i, current_date in enumerate(date_range):
            if current_date in daily_dict:
                row = daily_dict[current_date]
                chart_data['sales'][i] = float(row.total_sales or 0)
                chart_data['bill_counts'][i] = int(row.bill_count or 0)
        
        return chart_data
    
    @staticmethod
    def get_product_performance(shopkeeper_id: int, start_date: date = None, 
                              end_date: date = None, limit: int = 10) -> List[Dict]:
        """Get top performing products."""
        query = db.session.query(
            BillItem.product_name,
            func.sum(BillItem.quantity).label('total_quantity'),
            func.sum(BillItem.total_amount).label('total_sales'),
            func.count(BillItem.bill_item_id).label('times_sold')
        ).join(Bill).filter(Bill.shopkeeper_id == shopkeeper_id)
        
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        
        results = query.group_by(BillItem.product_name)\
                      .order_by(func.sum(BillItem.total_amount).desc())\
                      .limit(limit).all()
        
        products = []
        for row in results:
            products.append({
                'product_name': row.product_name,
                'total_quantity': int(row.total_quantity),
                'total_sales': float(row.total_sales),
                'times_sold': int(row.times_sold),
                'avg_sale_value': float(row.total_sales) / int(row.times_sold)
            })
        
        return products
    
    @staticmethod
    def get_customer_analysis(shopkeeper_user_id: int) -> Dict:
        """Get customer analysis with top customers."""
        # Get customers with purchases
        customer_data = db.session.query(
            Customer.customer_id,
            Customer.name,
            Customer.total_balance,
            func.count(Bill.bill_id).label('total_bills'),
            func.sum(Bill.total_amount).label('total_purchases'),
            func.sum(Bill.paid_amount).label('total_paid')
        ).outerjoin(Bill, Customer.customer_id == Bill.customer_id)\
         .filter(Customer.shopkeeper_id == shopkeeper_user_id)\
         .group_by(Customer.customer_id, Customer.name, Customer.total_balance)\
         .all()
        
        # Process data
        total_customers = len(customer_data)
        customers_with_balance = len([c for c in customer_data if c.total_balance and c.total_balance > 0])
        total_outstanding = sum(c.total_balance for c in customer_data if c.total_balance) or Decimal('0')
        
        # Top customers by purchase value
        top_customers = sorted(
            [c for c in customer_data if c.total_purchases],
            key=lambda x: x.total_purchases or 0,
            reverse=True
        )[:10]
        
        return {
            'total_customers': total_customers,
            'customers_with_balance': customers_with_balance,
            'total_outstanding': total_outstanding,
            'top_customers': [
                {
                    'name': c.name,
                    'total_purchases': float(c.total_purchases or 0),
                    'total_bills': int(c.total_bills or 0),
                    'outstanding_balance': float(c.total_balance or 0)
                } for c in top_customers
            ]
        }
    
    @staticmethod
    def get_gst_report(shopkeeper_id: int, month: int, year: int) -> Dict:
        """Get GST report for a specific month."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # Get bills for the month
        bills = Bill.query.filter(
            and_(
                Bill.shopkeeper_id == shopkeeper_id,
                Bill.bill_date >= start_date,
                Bill.bill_date <= end_date
            )
        ).all()
        
        # Group by GST rates
        gst_summary = {}
        total_taxable = Decimal('0')
        total_gst = Decimal('0')
        
        for bill in bills:
            bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
            
            for item in bill_items:
                gst_rate = item.gst_rate or Decimal('0')
                taxable_value = item.subtotal - (item.discount_amount or Decimal('0'))
                gst_amount = item.gst_amount or Decimal('0')
                
                if gst_rate not in gst_summary:
                    gst_summary[gst_rate] = {
                        'taxable_value': Decimal('0'),
                        'gst_amount': Decimal('0')
                    }
                
                gst_summary[gst_rate]['taxable_value'] += taxable_value
                gst_summary[gst_rate]['gst_amount'] += gst_amount
                
                total_taxable += taxable_value
                total_gst += gst_amount
        
        return {
            'month': month,
            'year': year,
            'period': f"{start_date.strftime('%B %Y')}",
            'gst_breakdown': {
                str(rate): {
                    'taxable_value': float(data['taxable_value']),
                    'gst_amount': float(data['gst_amount'])
                } for rate, data in gst_summary.items()
            },
            'total_taxable_value': float(total_taxable),
            'total_gst_amount': float(total_gst),
            'total_invoice_value': float(total_taxable + total_gst)
        }
    
    @staticmethod
    def get_payment_analysis(shopkeeper_id: int, days: int = 30) -> Dict:
        """Get payment collection analysis."""
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        bills = Bill.query.filter(
            and_(
                Bill.shopkeeper_id == shopkeeper_id,
                Bill.bill_date >= start_date
            )
        ).all()
        
        # Payment method breakdown
        payment_methods = {}
        for bill in bills:
            method = bill.payment_method or 'cash'
            if method not in payment_methods:
                payment_methods[method] = {
                    'count': 0,
                    'amount': Decimal('0')
                }
            payment_methods[method]['count'] += 1
            payment_methods[method]['amount'] += bill.paid_amount or Decimal('0')
        
        # Overdue analysis
        overdue_bills = [b for b in bills if b.due_amount and b.due_amount > 0]
        
        return {
            'payment_methods': {
                method: {
                    'count': data['count'],
                    'amount': float(data['amount'])
                } for method, data in payment_methods.items()
            },
            'overdue_analysis': {
                'overdue_bills': len(overdue_bills),
                'overdue_amount': float(sum(b.due_amount for b in overdue_bills)),
                'collection_rate': (
                    float(sum(b.paid_amount for b in bills)) / 
                    float(sum(b.total_amount for b in bills))
                ) * 100 if bills else 0
            }
        }
    
    @staticmethod
    def export_sales_data(shopkeeper_id: int, start_date: date, 
                         end_date: date) -> List[Dict]:
        """Export sales data for external use."""
        bills = Bill.query.filter(
            and_(
                Bill.shopkeeper_id == shopkeeper_id,
                Bill.bill_date >= start_date,
                Bill.bill_date <= end_date
            )
        ).order_by(Bill.bill_date.desc()).all()
        
        export_data = []
        for bill in bills:
            export_data.append({
                'bill_id': bill.bill_id,
                'date': bill.bill_date.strftime('%Y-%m-%d'),
                'customer_name': bill.customer_name or 'Walk-in',
                'subtotal': float(bill.subtotal_amount),
                'gst_amount': float(bill.gst_amount),
                'discount': float(bill.discount_amount or 0),
                'total_amount': float(bill.total_amount),
                'paid_amount': float(bill.paid_amount),
                'due_amount': float(bill.due_amount),
                'payment_status': bill.payment_status,
                'payment_method': bill.payment_method or 'cash'
            })
        
        return export_data