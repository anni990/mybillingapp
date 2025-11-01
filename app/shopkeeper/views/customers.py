"""
Customer management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, jsonify, send_file
from flask_login import login_required, current_user
from decimal import Decimal
import datetime
from sqlalchemy import desc
import io

from ..utils import shopkeeper_required
from app.models import Customer, CustomerLedger, Shopkeeper, Bill
from app.extensions import db


def register_routes(bp):
    """Register customer management routes to the blueprint."""
    

    @bp.route('/customer_management')
    @login_required
    @shopkeeper_required
    def customer_management():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('shopkeeper.dashboard'))
        
        # Get all customers for this shopkeeper
        customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id, is_active=True).all()
        
        # Calculate customer statistics
        active_customers_count = len([c for c in customers if c.total_balance > 0])
        
        # Calculate total sales from all credit amounts in customer ledger
        total_sales_query = db.session.query(db.func.sum(CustomerLedger.credit_amount)).filter_by(shopkeeper_id=shopkeeper.user_id).scalar()
        total_sales = float(total_sales_query or 0)
        
        # Calculate total remaining balance (sum of all customer balances)
        total_remaining_balance = sum(float(c.total_balance) for c in customers if c.total_balance > 0)
        
        # Get unique locations
        unique_locations = list(set([c.address for c in customers if c.address]))
        
        # Add additional customer data
        for customer in customers:
            # Get customer's bill count and last order date
            customer_bills = Bill.query.filter_by(customer_id=customer.customer_id).all()
            customer.total_orders = len(customer_bills)
            customer.last_order_date = max([b.bill_date for b in customer_bills]) if customer_bills else None
            customer.total_spent = sum(float(b.total_amount) for b in customer_bills)
        
        return render_template('shopkeeper/customer_management.html', 
                            shop_name=shop_name,
                            customers=customers,
                            active_customers_count=active_customers_count,
                            total_sales=total_sales,
                            total_remaining_balance=total_remaining_balance,
                            unique_locations=unique_locations)

    @bp.route('/add_customer', methods=['POST'])
    @login_required
    @shopkeeper_required
    def add_customer():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            return jsonify({'success': False, 'message': 'Shopkeeper profile not found'})
        
        try:
            # Check if customer with same phone already exists for this shopkeeper
            existing_customer = Customer.query.filter_by(
                shopkeeper_id=shopkeeper.user_id, 
                phone=request.form.get('phone')
            ).first()
            
            if existing_customer:
                return jsonify({'success': False, 'message': 'Customer with this phone number already exists'})
            
            customer = Customer(
                shopkeeper_id=shopkeeper.user_id,
                name=request.form.get('name'),
                phone=request.form.get('phone'),
                email=request.form.get('email') or None,
                address=request.form.get('address') or None
            )
            
            db.session.add(customer)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Customer added successfully'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    @bp.route('/get_customer/<int:customer_id>')
    @login_required
    @shopkeeper_required
    def get_customer(customer_id):
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        return jsonify({
            'success': True,
            'customer': {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'address': customer.address
            }
        })

    @bp.route('/update_customer/<int:customer_id>', methods=['PUT'])
    @login_required
    @shopkeeper_required
    def update_customer(customer_id):
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        try:
            # Check if phone number is being changed and if it conflicts with another customer
            new_phone = request.form.get('phone')
            if new_phone != customer.phone:
                existing_customer = Customer.query.filter_by(
                    shopkeeper_id=shopkeeper.user_id, 
                    phone=new_phone
                ).filter(Customer.customer_id != customer_id).first()
                
                if existing_customer:
                    return jsonify({'success': False, 'message': 'Another customer with this phone number already exists'})
            
            customer.name = request.form.get('name')
            customer.phone = new_phone
            customer.email = request.form.get('email') or None
            customer.address = request.form.get('address') or None
            customer.updated_date = datetime.datetime.now()
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Customer updated successfully'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    @bp.route('/delete_customer/<int:customer_id>', methods=['DELETE'])
    @login_required
    @shopkeeper_required
    def delete_customer(customer_id):
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        try:
            # Check if customer has any pending dues
            if customer.total_balance > 0:
                return jsonify({'success': False, 'message': 'Cannot delete customer with pending dues. Please clear all dues first.'})
            
            # Soft delete - set is_active to False instead of actually deleting
            customer.is_active = False
            customer.updated_date = datetime.datetime.now()
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Customer deleted successfully'})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    @bp.route('/get_customer_details/<int:customer_id>')
    @login_required
    @shopkeeper_required
    def get_customer_details(customer_id):
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        # Get customer's order history
        bills = Bill.query.filter_by(customer_id=customer_id).order_by(desc(Bill.bill_date)).all()
        
        orders = []
        for bill in bills:
            orders.append({
                'bill_id': bill.bill_id,
                'date': bill.bill_date.strftime('%d %b %Y'),
                'total': f"{bill.total_amount:,.0f}",
                'items_count': len(bill.bill_items)
            })
        
        return jsonify({
            'success': True,
            'customer': {
                'customer_id': customer.customer_id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'address': customer.address,
                'total_balance': float(customer.total_balance)
            },
            'orders': orders
        })

    @bp.route('/customer_ledger/<int:customer_id>')
    @login_required
    @shopkeeper_required
    def customer_ledger(customer_id):
        print(f"🔍 Customer ledger route called for customer ID: {customer_id}")
        
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            print(f"❌ Customer not found: ID {customer_id}")
            flash('Customer not found.', 'error')
            return redirect(url_for('shopkeeper.customer_management'))
        
        print(f"✅ Customer found: {customer.name}, Balance: ₹{customer.total_balance}")
        
        # Get ledger entries
        ledger_entries = CustomerLedger.query.filter_by(customer_id=customer_id).order_by(desc(CustomerLedger.transaction_date)).all()
        
        print(f"📝 Found {len(ledger_entries)} ledger entries for customer {customer.name}")
        
        # Debug: Print recent entries
        for i, entry in enumerate(ledger_entries[:3]):
            print(f"   Entry {i+1}: {entry.transaction_date} - {entry.transaction_type} - Credit: ₹{entry.credit_amount} - Debit: ₹{entry.debit_amount}")
        
        return render_template('shopkeeper/customer_ledger.html', 
                            shop_name=shop_name,
                            customer=customer, 
                            ledger_entries=ledger_entries)

    @bp.route('/add_ledger_entry/<int:customer_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def add_ledger_entry(customer_id):
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        try:
            transaction_type = request.form.get('transaction_type')
            debit_amount = Decimal(request.form.get('debit_amount', '0'))
            credit_amount = Decimal(request.form.get('credit_amount', '0'))
            particulars = request.form.get('particulars')
            invoice_no = request.form.get('invoice_no')
            notes = request.form.get('notes')
            
            # Calculate new balance
            current_balance = customer.total_balance or Decimal('0')
            new_balance = current_balance + debit_amount - credit_amount
            
            # Create ledger entry
            ledger_entry = CustomerLedger(
                customer_id=customer_id,
                shopkeeper_id=shopkeeper.user_id,
                invoice_no=invoice_no,
                particulars=particulars,
                debit_amount=debit_amount,
                credit_amount=credit_amount,
                balance_amount=new_balance,
                transaction_type=transaction_type,
                notes=notes
            )
            
            # Update customer balance
            customer.total_balance = new_balance
            customer.updated_date = datetime.datetime.now()
            
            db.session.add(ledger_entry)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Ledger entry added successfully', 'new_balance': float(new_balance)})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    @bp.route('/complete_payment/<int:customer_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def complete_payment(customer_id):
        print(f"🔍 Complete payment route called for customer ID: {customer_id}")
        
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
        
        if not customer:
            print(f"❌ Customer not found: ID {customer_id}, Shopkeeper ID {shopkeeper.user_id if shopkeeper else 'None'}")
            return jsonify({'success': False, 'message': 'Customer not found'})
        
        print(f"✅ Customer found: {customer.name}, Balance: ₹{customer.total_balance}")
        
        try:
            current_balance = customer.total_balance or Decimal('0')
            print(f"💰 Current balance: ₹{current_balance}")
            
            # Check if customer has any outstanding balance
            if current_balance <= 0:
                print("❌ No outstanding balance to clear")
                return jsonify({'success': False, 'message': 'No outstanding balance to clear'})
            
            print("📝 Creating ledger entry...")
            
            # Create ledger entry for complete payment
            ledger_entry = CustomerLedger(
                customer_id=customer_id,
                shopkeeper_id=shopkeeper.user_id,
                transaction_date=datetime.datetime.now(),  # Explicitly set current timestamp
                invoice_no=f"PAY{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                particulars="Complete Balance Payment - Cash Received",
                debit_amount=Decimal('0'),
                credit_amount=current_balance,
                balance_amount=Decimal('0'),
                transaction_type='PAYMENT',
                notes="Full outstanding balance paid in cash"
            )
            
            # Clear customer balance
            customer.total_balance = Decimal('0')
            customer.updated_date = datetime.datetime.now()
            
            db.session.add(ledger_entry)
            db.session.commit()
            
            print(f"✅ Complete payment processed successfully! Ledger entry ID: {ledger_entry.ledger_id}")
            
            return jsonify({
                'success': True, 
                'message': f'Complete payment of ₹{current_balance:.2f} recorded successfully',
                'amount_cleared': float(current_balance)
            })
        
        except Exception as e:
            print(f"❌ Error during complete payment: {e}")
            db.session.rollback()
            return jsonify({'success': False, 'message': str(e)})

    @bp.route('/get_customers_list')
    @login_required
    @shopkeeper_required
    def get_customers_list():
        """Get list of customers for bill creation dropdown"""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            return jsonify({'success': False, 'message': 'Shopkeeper profile not found'})
        
        customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id, is_active=True).all()
        
        customers_list = []
        for customer in customers:
            customers_list.append({
                'customer_id': customer.customer_id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email,
                'address': customer.address,
                'balance': float(customer.total_balance)
            })
        
        return jsonify({'success': True, 'customers': customers_list})

    @bp.route('/export_customers')
    @login_required
    @shopkeeper_required
    def export_customers():
        """Export customers to CSV"""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('shopkeeper.customer_management'))
        
        customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id, is_active=True).all()
        
        # Create CSV content
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'Phone', 'Email', 'Address', 'Balance', 'Created Date'])
        
        # Write customer data
        for customer in customers:
            writer.writerow([
                customer.name,
                customer.phone,
                customer.email or '',
                customer.address or '',
                f"{customer.total_balance:.2f}",
                customer.created_date.strftime('%Y-%m-%d')
            ])
        
        # Create response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'customers_{datetime.date.today().strftime("%Y%m%d")}.csv'
        )

    @bp.route('/customer_ledger_overview')
    @login_required
    @shopkeeper_required
    def customer_ledger_overview():
        """Customer ledger overview page showing all customers with ledger access"""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('shopkeeper.dashboard'))
        
        # Get all customers with their balance summary
        customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id, is_active=True).all()
        
        # Calculate summary statistics
        total_customers = len(customers)
        total_outstanding = sum(customer.total_balance for customer in customers if customer.total_balance > 0)
        total_advance = sum(abs(customer.total_balance) for customer in customers if customer.total_balance < 0)
        
        return render_template('shopkeeper/customer_ledger_overview.html', 
                            shop_name=shop_name,
                            customers=customers,
                            total_customers=total_customers,
                            total_outstanding=total_outstanding,
                            total_advance=total_advance)
