from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory, g, current_app
from flask_login import login_required, current_user
from app.models import Product, Shopkeeper, Bill, BillItem, CharteredAccountant, CAConnection, ShopConnection, Document, User, Customer, CustomerLedger
from app.extensions import db
from sqlalchemy import func, desc, or_
import datetime
import io
import os
from decimal import Decimal

shopkeeper_bp = Blueprint('shopkeeper', __name__, url_prefix='/shopkeeper')

@shopkeeper_bp.route('/')
def shopkeeper_root():
    return redirect(url_for('shopkeeper.dashboard'))

def shopkeeper_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'shopkeeper':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Dashboard Home
@shopkeeper_bp.route('/dashboard')
@login_required
@shopkeeper_required
def dashboard():
    from dateutil.relativedelta import relativedelta
    from app.models import CAEmployee, EmployeeClient

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
        monthly_sales_data=monthly_sales_data
    )

@shopkeeper_bp.route('/ca/profile/<int:ca_id>')
@login_required
@shopkeeper_required
def connected_ca_profile(ca_id):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    
    # Verify connection exists
    ca_conn = CAConnection.query.filter_by(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        ca_id=ca_id,
        status='approved'
    ).first()
    
    if not ca_conn:
        flash('No connection found with this CA.', 'danger')
        return redirect(url_for('shopkeeper.dashboard'))
    
    # Get CA details
    ca = CharteredAccountant.query.get_or_404(ca_id)
    
    # Get assigned employees
    from app.models import CAEmployee, EmployeeClient
    assigned_employees = db.session.query(CAEmployee)\
        .join(EmployeeClient, CAEmployee.employee_id == EmployeeClient.employee_id)\
        .filter(EmployeeClient.shopkeeper_id == shopkeeper.shopkeeper_id)\
        .all()
    
    return render_template('shopkeeper/connected_ca_profile.html',
        ca=ca,
        assigned_employees=assigned_employees
    )

# Create Bill
@shopkeeper_bp.route('/create_bill', methods=['GET', 'POST'])
@login_required
@shopkeeper_required
def create_bill():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # In all relevant routes, comment out the is_verified restriction logic
    # Example for create_bill:
    #    if not shopkeeper.is_verified:
    #        flash('Please upload all required documents to use this service.', 'danger')
    #        return redirect(url_for('shopkeeper.profile'))
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
    products_js = [
        {
            'id': p.product_id,
            'name': p.product_name,
            'price': float(p.price),
            'stock': p.stock_qty,
            'gst_rate': float(p.gst_rate or 0)
        } for p in products
    ]
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_contact = request.form.get('customer_contact')
        customer_address = request.form.get('customer_address')
        customer_gstin=request.form.get('customer_gstin')
        gst_type = request.form.get('gst_type')
        bill_date = datetime.date.today()
        items = request.form.getlist('product_id')
        quantities = request.form.getlist('quantity')
        prices = request.form.getlist('price_per_unit')
        total_amount = sum(float(q)*float(p) for q, p in zip(quantities, prices))
        bill = Bill(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            bill_number=f"BILL{int(datetime.datetime.now().timestamp())}",
            customer_name=customer_name,
            customer_contact=customer_contact,
            customer_address=customer_address,
            customer_gstin=customer_gstin,
            bill_date=bill_date,
            gst_type=gst_type,
            total_amount=total_amount,
            payment_status='Paid',
            paid_amount=total_amount,  # Set payment amounts for paid bills
            due_amount=0
        )
        db.session.add(bill)
        db.session.flush()  # get bill_id
        for pid, qty, price in zip(items, quantities, prices):
            bill_item = BillItem(
                bill_id=bill.bill_id,
                product_id=pid,
                quantity=qty,
                price_per_unit=price,
                total_price=float(qty)*float(price)
            )
            db.session.add(bill_item)
            # Update product stock
            product = Product.query.get(pid)
            if product:
                product.stock_qty = product.stock_qty - int(qty)
        db.session.commit()
        flash('Bill created successfully.', 'success')
        return redirect(url_for('shopkeeper.manage_bills'))
    return render_template(
        'shopkeeper/create_bill.html',
        products=products,
        products_js=products_js,
        shopkeeper=shopkeeper,
        now=datetime.datetime.now()  # Pass current datetime as 'now'
    )

# Manage Bills
@shopkeeper_bp.route('/manage_bills')
@login_required
@shopkeeper_required
def manage_bills():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # In all relevant routes, comment out the is_verified restriction logic
    # Example for create_bill:
    #    if not shopkeeper.is_verified:
    #        flash('Please upload all required documents to use this service.', 'danger')
    #        return redirect(url_for('shopkeeper.profile'))
    search = request.args.get('search', '').strip()
    selected_statuses = request.args.getlist('status')
    query = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
    if search:
        query = query.filter(
            (Bill.bill_number.ilike(f'%{search}%')) |
            (Bill.customer_name.ilike(f'%{search}%'))
        )
    if selected_statuses:
        query = query.filter(Bill.payment_status.in_(selected_statuses))
    bills = query.order_by(Bill.bill_date.desc()).all() if shopkeeper else []
    return render_template('shopkeeper/manage_bills.html', bills=bills, selected_statuses=selected_statuses)

@shopkeeper_bp.route('/bill/<int:bill_id>')
@login_required
@shopkeeper_required
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if bill.shopkeeper.user_id != current_user.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('shopkeeper.manage_bills'))
    
    bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
    shopkeeper = bill.shopkeeper
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    products_dict = {str(p.product_id): p for p in products}
    
    # Check if user can edit (you can customize this based on roles)
    is_editable = False
    if current_user.role == 'shopkeeper' and bill.shopkeeper.user_id == current_user.user_id:
        is_editable = True
    elif current_user.role == 'CA':
        ca_conn = CAConnection.query.filter_by(shopkeeper_id=bill.shopkeeper_id, ca_id=current_user.ca.ca_id, status='approved').first()
        is_editable = bool(ca_conn)
    elif current_user.role == 'employee':
        emp_client = EmployeeClient.query.filter_by(shopkeeper_id=bill.shopkeeper_id, employee_id=current_user.ca_employee.employee_id).first()
        is_editable = bool(emp_client)
    
    # Calculate GST summary for each item
    bill_items_data = []
    gst_summary_by_rate = {}
    total_taxable_amount = 0
    total_cgst_amount = 0
    total_sgst_amount = 0
    total_gst_amount = 0
    overall_grand_total = 0

    for item in bill_items:
        # Handle both existing products and custom products
        if item.product_id:  # Existing product
            product = products_dict.get(str(item.product_id))
            if not product:
                continue  # Skip if product not found
            
            gst_rate = float(product.gst_rate or 0)
            hsn_code = product.hsn_code if hasattr(product, 'hsn_code') else ''
            product_name = product.product_name
            is_custom = False
        else:  # Custom product
            # Create a mock product object for custom products
            product = type('Product', (), {
                'product_name': item.custom_product_name,
                'gst_rate': float(item.custom_gst_rate or 0),
                'hsn_code': item.custom_hsn_code or '',
                'product_id': f'custom_{item.bill_item_id}'
            })()
            
            gst_rate = float(item.custom_gst_rate or 0)
            hsn_code = item.custom_hsn_code or ''
            product_name = item.custom_product_name
            is_custom = True
        
        base_price = float(item.price_per_unit)
        quantity = int(item.quantity)
        total_price = base_price * quantity
        
        # Assuming discount percentage is stored or calculated
        discount = 0  # You can modify this based on your discount logic
        discount_amount = (discount / 100) * total_price
        discounted_price = total_price - discount_amount
        
        # GST calculations
        sgst_rate = cgst_rate = gst_rate / 2
        sgst_amount = (sgst_rate / 100) * discounted_price
        cgst_amount = (cgst_rate / 100) * discounted_price
        final_price = discounted_price + sgst_amount + cgst_amount

        item_data = {
            'product': product,
            'is_custom': is_custom,
            'hsn_code': hsn_code,
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

        # Update GST summary
        if gst_rate not in gst_summary_by_rate:
            gst_summary_by_rate[gst_rate] = {
                'taxable_amount': 0,
                'cgst_amount': 0,
                'sgst_amount': 0,
                'total_gst_amount': 0
            }
        
        gst_summary_by_rate[gst_rate]['taxable_amount'] += discounted_price
        gst_summary_by_rate[gst_rate]['cgst_amount'] += cgst_amount
        gst_summary_by_rate[gst_rate]['sgst_amount'] += sgst_amount
        gst_summary_by_rate[gst_rate]['total_gst_amount'] += (cgst_amount + sgst_amount)
        
        total_taxable_amount += discounted_price
        total_cgst_amount += cgst_amount
        total_sgst_amount += sgst_amount
        total_gst_amount += (cgst_amount + sgst_amount)
        overall_grand_total += final_price

    is_editable = True  # You can set conditions for editability here

    return render_template('shopkeeper/bill_receipt.html',
        bill=bill,
        bill_items_data=bill_items_data,
        shopkeeper=shopkeeper,
        products=products_dict,
        gst_summary_by_rate=gst_summary_by_rate,
        total_taxable_amount=total_taxable_amount,
        total_cgst_amount=total_cgst_amount,
        total_sgst_amount=total_sgst_amount,
        total_gst_amount=total_gst_amount,
        overall_grand_total=overall_grand_total,
        is_editable=is_editable,
        back_url=url_for('shopkeeper.manage_bills'))

@shopkeeper_bp.route('/bill/download/<int:bill_id>')
@login_required
def download_bill_pdf(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    
    # Check permissions
    if current_user.role == 'shopkeeper' and bill.shopkeeper.user_id != current_user.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('shopkeeper.manage_bills'))
    
    # Get bill data
    bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
    shopkeeper = bill.shopkeeper
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    products_dict = {str(p.product_id): p for p in products}
    
    # Calculate GST summary
    bill_items_data = []
    gst_summary_by_rate = {}
    total_taxable_amount = 0
    total_cgst_amount = 0
    total_sgst_amount = 0
    total_gst_amount = 0
    overall_grand_total = 0

    for item in bill_items:
        # Handle both existing products and custom products
        if item.product_id:  # Existing product
            product = products_dict.get(str(item.product_id))
            if not product:
                continue  # Skip if product not found
            
            gst_rate = float(product.gst_rate or 0)
            hsn_code = product.hsn_code if hasattr(product, 'hsn_code') else ''
            is_custom = False
        else:  # Custom product
            # Create a mock product object for custom products
            product = type('Product', (), {
                'product_name': item.custom_product_name,
                'gst_rate': float(item.custom_gst_rate or 0),
                'hsn_code': item.custom_hsn_code or '',
                'product_id': f'custom_{item.bill_item_id}'
            })()
            
            gst_rate = float(item.custom_gst_rate or 0)
            hsn_code = item.custom_hsn_code or ''
            is_custom = True
        
        base_price = float(item.price_per_unit)
        quantity = int(item.quantity)
        total_price = base_price * quantity
        
        discount = 0
        discount_amount = (discount / 100) * total_price
        discounted_price = total_price - discount_amount
        
        sgst_rate = cgst_rate = gst_rate / 2
        sgst_amount = (sgst_rate / 100) * discounted_price
        cgst_amount = (cgst_rate / 100) * discounted_price
        final_price = discounted_price + sgst_amount + cgst_amount

        item_data = {
            'product': product,
            'is_custom': is_custom,
            'hsn_code': hsn_code,
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

        if gst_rate not in gst_summary_by_rate:
            gst_summary_by_rate[gst_rate] = {
                'taxable_amount': 0,
                'cgst_amount': 0,
                'sgst_amount': 0,
                'total_gst_amount': 0
            }
        
        gst_summary_by_rate[gst_rate]['taxable_amount'] += discounted_price
        gst_summary_by_rate[gst_rate]['cgst_amount'] += cgst_amount
        gst_summary_by_rate[gst_rate]['sgst_amount'] += sgst_amount
        gst_summary_by_rate[gst_rate]['total_gst_amount'] += (cgst_amount + sgst_amount)
        
        total_taxable_amount += discounted_price
        total_cgst_amount += cgst_amount
        total_sgst_amount += sgst_amount
        total_gst_amount += (cgst_amount + sgst_amount)
        overall_grand_total += final_price

    # Render template to HTML
    html = render_template('shopkeeper/bill_receipt.html',
        bill=bill,
        bill_items_data=bill_items_data,
        shopkeeper=shopkeeper,
        products=products_dict,
        gst_summary_by_rate=gst_summary_by_rate,
        total_taxable_amount=total_taxable_amount,
        total_cgst_amount=total_cgst_amount,
        total_sgst_amount=total_sgst_amount,
        total_gst_amount=total_gst_amount,
        overall_grand_total=overall_grand_total,
        is_editable=False # No edit button in PDF
    )

    # Generate PDF using WeasyPrint
    from weasyprint import HTML
    pdf = HTML(string=html).write_pdf()

    return send_file(
        io.BytesIO(pdf),
        download_name=f'bill_{bill.bill_number}.pdf',
        mimetype='application/pdf'
    )

@shopkeeper_bp.route('/bill/<int:bill_id>/edit', methods=['POST'])
@login_required
def update_bill(bill_id):
    print("Update bill route called")
    print("Form data:", request.form)
    
    try:
        bill = Bill.query.get_or_404(bill_id)
        
        # Check permissions
        if current_user.role == 'shopkeeper' and bill.shopkeeper.user_id != current_user.user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('shopkeeper.manage_bills'))

        # Get form data
        customer_name = request.form.get('customer_name')
        customer_contact = request.form.get('customer_contact')
        payment_status = request.form.get('payment_status', bill.payment_status)
        
        print(f"Customer details - Name: {customer_name}, Contact: {customer_contact}")

        # Update basic bill information
        if customer_name:
            bill.customer_name = customer_name
        if customer_contact:
            bill.customer_contact = customer_contact
        bill.payment_status = payment_status

        # Get bill items data from form
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        
        print(f"Bill items - IDs: {item_ids}, Quantities: {quantities}, Prices: {prices}")

        # Update bill items
        total_bill_amount = 0
        
        for index, (item_id, qty, price) in enumerate(zip(item_ids, quantities, prices)):
            try:
                # Convert form data to appropriate types
                item_id = str(item_id)  # Convert to string to match product_id
                qty = int(qty)
                price = float(price)
                
                # Get the bill item
                bill_item = BillItem.query.filter_by(
                    bill_id=bill.bill_id,
                    product_id=item_id
                ).first()
                
                if bill_item:
                    print(f"Processing item {item_id} - Old qty: {bill_item.quantity}, New qty: {qty}")
                    print(f"Old price: {bill_item.price_per_unit}, New price: {price}")
                    
                    # Update product stock
                    product = Product.query.get(item_id)
                    if product:
                        # Adjust stock
                        old_qty = bill_item.quantity
                        stock_adjustment = old_qty - qty
                        product.stock_qty += stock_adjustment
                        print(f"Stock adjustment for product {product.product_name}: {stock_adjustment}")
                        
                        # Calculate item total with GST
                        gst_rate = float(product.gst_rate or 0)
                        base_amount = qty * price
                        gst_amount = (gst_rate / 100) * base_amount
                        item_total = base_amount + gst_amount
                        
                        # Update bill item
                        bill_item.quantity = qty
                        bill_item.price_per_unit = price
                        bill_item.total_price = item_total
                        
                        print(f"Updated totals - Base: {base_amount}, GST: {gst_amount}, Total: {item_total}")
                        
                        total_bill_amount += item_total
                    else:
                        print(f"Product not found for ID: {item_id}")
                else:
                    print(f"Bill item not found for ID: {item_id}")
            
            except ValueError as ve:
                print(f"Value error processing item {item_id}: {str(ve)}")
                flash(f"Invalid value for item {index + 1}", 'error')
                continue
            except Exception as e:
                print(f"Error processing item {item_id}: {str(e)}")
                continue

        # Update bill total
        bill.total_amount = total_bill_amount
        print(f"Final bill amount: {total_bill_amount}")
        
        # Commit all changes
        db.session.commit()
        flash('Bill updated successfully!', 'success')
        return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))
        
    except Exception as e:
        print(f"Error updating bill: {str(e)}")
        db.session.rollback()
        flash('Error updating bill. Please try again.', 'danger')
        return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))
    
    db.session.commit()
    flash('Bill updated successfully.', 'success')
    return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))

@shopkeeper_bp.route('/bill/delete/<int:bill_id>', methods=['POST'])
@login_required
@shopkeeper_required
def delete_bill(bill_id):
    try:
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        bill = Bill.query.get_or_404(bill_id)
        
        # Check if the bill belongs to the current shopkeeper
        if bill.shopkeeper.user_id != current_user.user_id:
            return jsonify({'success': False, 'message': 'Access denied.'}), 403
        
        # Handle related CustomerLedger entries - set reference_bill_id to NULL
        # This preserves the financial history while removing the bill reference
        from app.models import CustomerLedger
        related_ledger_entries = CustomerLedger.query.filter_by(reference_bill_id=bill_id).all()
        for entry in related_ledger_entries:
            entry.reference_bill_id = None
            entry.particulars = f"{entry.particulars} (Bill #{bill.bill_number} - Deleted)"
        
        # Delete the bill (BillItems will be deleted automatically due to cascade)
        db.session.delete(bill)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Bill deleted successfully.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting bill: {str(e)}'}), 500



# Sales Reports
@shopkeeper_bp.route('/sales_reports')
@login_required
@shopkeeper_required
def sales_reports():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # In all relevant routes, comment out the is_verified restriction logic
    # Example for create_bill:
    #    if not shopkeeper.is_verified:
    #        flash('Please upload all required documents to use this service.', 'danger')
    #        return redirect(url_for('shopkeeper.profile'))
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
        d = bill.bill_date.strftime('%Y-%m-%d')
        if d in chart_data:
            chart_data[d] += float(bill.total_amount)
    chart_labels = list(chart_data.keys())
    chart_values = list(chart_data.values())
    return render_template('shopkeeper/sales_reports.html', bills=bills, chart_labels=chart_labels, chart_values=chart_values, start=start, end=end)

# CA Marketplace
@shopkeeper_bp.route('/ca_marketplace', methods=['GET', 'POST'])
@login_required
@shopkeeper_required
def ca_marketplace():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    
    # First check if shopkeeper has any approved CA connection
    approved_connection = ShopConnection.query.filter_by(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        status='approved'
    ).first()
    
    # If there's an approved connection, only get that CA's details
    if approved_connection:
        connected_ca = CharteredAccountant.query.get(approved_connection.ca_id)
        cas = [connected_ca] if connected_ca else []
    else:
        # If no approved connection, show all CAs
        cas = []
        if request.method == 'POST':
            area = request.form.get('area')
            domain = request.form.get('domain')
            query = CharteredAccountant.query
            if area:
                query = query.filter(CharteredAccountant.area.ilike(f'%{area}%'))
            cas = query.all()
        else:
            cas = CharteredAccountant.query.all()
    
    # Get connection status for each CA
    connections = {c.ca_id: c for c in ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()}
    
    return render_template('shopkeeper/ca_marketplace.html', 
                         cas=cas, 
                         connections=connections,
                         has_approved_connection=bool(approved_connection))

@shopkeeper_bp.route('/connect_ca/<int:ca_id>', methods=['POST'])
@login_required
@shopkeeper_required
def connect_ca(ca_id):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    existing = ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=ca_id).first()
    if not existing:
        conn = ShopConnection(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=ca_id, status='pending')
        db.session.add(conn)
        db.session.commit()
        flash('Connection request sent.', 'success')
    else:
        if existing.status == 'pending':
            flash('Request already sent and pending approval.', 'info')
        elif existing.status == 'approved':
            flash('You are already connected with this CA.', 'info')
        elif existing.status == 'rejected':
            existing.status = 'pending'
            db.session.commit()
            flash('Connection request resent.', 'success')
    return redirect(url_for('shopkeeper.ca_marketplace'))


# Products & Stock (already implemented above)
@shopkeeper_bp.route('/products', methods=['GET'])
@login_required
@shopkeeper_required
def products_stock():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
    return render_template('shopkeeper/products_stock.html', products=products)

@shopkeeper_bp.route('/products/add', methods=['POST'])
@login_required
@shopkeeper_required
def add_product():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    if not shopkeeper:
        flash('Shopkeeper profile not found.', 'danger')
        return redirect(url_for('shopkeeper.products_stock'))
    name = request.form.get('product_name')
    barcode = request.form.get('barcode')
    price = request.form.get('price')
    gst_rate = request.form.get('gst_rate')
    hsn_code = request.form.get('hsn_code')
    stock_qty = request.form.get('stock_qty')
    low_stock_threshold = request.form.get('low_stock_threshold')
    if not name or not price:
        flash('Product name and price are required.', 'danger')
        return redirect(url_for('shopkeeper.products_stock'))
    product = Product(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        product_name=name,
        barcode=barcode,
        price=price,
        gst_rate=gst_rate,
        hsn_code=hsn_code,
        stock_qty=stock_qty or 0,
        low_stock_threshold=low_stock_threshold or 0
    )
    db.session.add(product)
    db.session.commit()
    flash('Product added successfully.', 'success')
    return redirect(url_for('shopkeeper.products_stock'))

@shopkeeper_bp.route('/products/edit/<int:product_id>', methods=['POST'])
@login_required
@shopkeeper_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.shopkeeper.user_id != current_user.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('shopkeeper.products_stock'))
    
    # Update all product fields
    product.product_name = request.form.get('product_name')
    product.barcode = request.form.get('barcode')
    product.price = request.form.get('price')
    product.gst_rate = request.form.get('gst_rate')
    product.hsn_code = request.form.get('hsn_code')
    product.stock_qty = request.form.get('stock_qty')
    product.low_stock_threshold = request.form.get('low_stock_threshold')
    
    db.session.commit()
    flash('Product updated successfully.', 'success')
    return redirect(url_for('shopkeeper.products_stock'))

@shopkeeper_bp.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
@shopkeeper_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    if product.shopkeeper.user_id != current_user.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('shopkeeper.products_stock'))
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully.', 'success')
    return redirect(url_for('shopkeeper.products_stock'))

@shopkeeper_bp.route('/generate_bill_pdf', methods=['POST'])
@login_required
@shopkeeper_required
def generate_bill_pdf():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
    
    # Customer information
    customer_type = request.form.get('customer_type', 'new')
    existing_customer_id = request.form.get('existing_customer_id')
    customer_name = request.form.get('customer_name')
    customer_contact = request.form.get('customer_contact')
    customer_address = request.form.get('customer_address')
    customer_gstin = request.form.get('customer_gstin')
    save_as_customer = request.form.get('save_as_customer') == '1'  # Get save customer toggle
    
    # Payment information
    payment_status_form = request.form.get('payment_status', 'Paid')
    paid_amount_form = request.form.get('paid_amount', '0')
    
    gst_mode = request.form.get('gst_mode', 'exclusive')
    bill_gst_type = request.form.get('bill_gst_type', 'GST')
    bill_gst_rate = float(request.form.get('bill_gst_rate', 0))
    items = request.form.getlist('product_id')
    product_names = request.form.getlist('product_name')  # Get custom product names
    quantities = request.form.getlist('quantity')
    prices = request.form.getlist('price_per_unit')
    discounts = request.form.getlist('discount')
    gst_rates_custom = request.form.getlist('gst_rate')  # Get custom GST rates
    
    # Parse bill_date from form (datetime-local input)
    bill_date_str = request.form.get('bill_date')
    if bill_date_str:
        bill_date = datetime.datetime.strptime(bill_date_str, '%Y-%m-%dT%H:%M')
    else:
        bill_date = datetime.datetime.now()
    
    total_amount = 0
    bill_number = f"BILL{int(datetime.datetime.now().timestamp())}"
    
    # Determine payment status and amounts
    # For existing customers use the form selection. For new customers that are being saved
    # (save_as_customer == True) also respect the form selection (Paid/Partial/Unpaid).
    if (customer_type == 'existing' and existing_customer_id) or (customer_type == 'new' and save_as_customer):
        payment_status = payment_status_form
        if payment_status == 'Paid':
            paid_amount = 0  # Will be calculated after total_amount
            due_amount = 0
        elif payment_status == 'Unpaid':
            paid_amount = 0
            due_amount = 0  # Will be calculated after total_amount
        else:  # Partial
            try:
                paid_amount = float(paid_amount_form)
            except (ValueError, TypeError):
                paid_amount = 0
            due_amount = 0  # Will be calculated after total_amount
    else:
        # For guest customers (not saved), default to Paid
        payment_status = 'Paid'
        paid_amount = 0  # Will be calculated after total_amount
        due_amount = 0
    
    # Ensure created_customer_id exists on all paths
    created_customer_id = None  # Track if we created/found a customer

    # Handle customer creation BEFORE bill creation when toggle is enabled
    if customer_type == 'new' and save_as_customer and customer_name and customer_name.strip():
        try:
            # Check for duplicate customer by phone number for this shopkeeper
            existing_customer = None
            if customer_contact and customer_contact.strip():
                existing_customer = Customer.query.filter_by(
                    shopkeeper_id=shopkeeper.user_id,
                    phone=customer_contact.strip()
                ).first()
            
            if existing_customer:
                # Use existing customer
                created_customer_id = existing_customer.customer_id
                current_app.logger.debug(f"Reusing existing customer: {existing_customer.name} (id={created_customer_id})")
            else:
                # Create new customer
                try:
                    new_customer = Customer(
                        shopkeeper_id=shopkeeper.user_id,  # Use shopkeeper.user_id per project convention
                        name=customer_name.strip(),
                        phone=customer_contact.strip() if customer_contact else '',
                        email='',  # Email not captured in current form
                        address=customer_address.strip() if customer_address else '',
                        is_active=True,
                        total_balance=0.00
                    )
                    db.session.add(new_customer)
                    db.session.flush()  # Get customer_id
                    created_customer_id = new_customer.customer_id
                    # Persist customer immediately so it appears in customer management
                    db.session.commit()
                    current_app.logger.debug(f"Created new customer: {new_customer.name} with ID {created_customer_id}")
                except Exception:
                    current_app.logger.exception("Error creating new customer")
                    # Rollback to clear session state and avoid interfering with bill creation
                    db.session.rollback()
                    created_customer_id = None
                
        except Exception:
            # If customer lookup fails, log it and continue with bill creation
            current_app.logger.exception("Error checking existing customer")
            created_customer_id = None

    # Create bill object
    bill = Bill(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        customer_id=created_customer_id if created_customer_id else (int(existing_customer_id) if existing_customer_id and customer_type == 'existing' else None),
        bill_number=bill_number,
        customer_name=customer_name,
        customer_contact=customer_contact,
        customer_address=customer_address,
        customer_gstin=customer_gstin,
        bill_date=bill_date,
        gst_type=bill_gst_type,
        total_amount=0,
        payment_status=payment_status,
        paid_amount=paid_amount,
        due_amount=due_amount
    )
    db.session.add(bill)
    db.session.flush()
    
    bill_items = []
    bill_items_data = []
    gst_summary_by_rate = {}
    overall_grand_total = 0.0
    
    # Handle customer creation BEFORE bill creation when toggle is enabled
    if customer_type == 'new' and save_as_customer and customer_name and customer_name.strip():
        try:
            # Check for duplicate customer by phone number for this shopkeeper
            existing_customer = None
            if customer_contact and customer_contact.strip():
                existing_customer = Customer.query.filter_by(
                    shopkeeper_id=shopkeeper.user_id,
                    phone=customer_contact.strip()
                ).first()
            
            if existing_customer:
                # Use existing customer
                created_customer_id = existing_customer.customer_id
                print(f"Reusing existing customer: {existing_customer.name}")
            else:
                # Create new customer
                new_customer = Customer(
                    shopkeeper_id=shopkeeper.user_id,  # Use shopkeeper.user_id per project convention
                    name=customer_name.strip(),
                    phone=customer_contact.strip() if customer_contact else '',
                    email='',  # Email not captured in current form
                    address=customer_address.strip() if customer_address else '',
                    is_active=True,
                    total_balance=0.00
                )
                db.session.add(new_customer)
                db.session.flush()  # Get customer_id
                created_customer_id = new_customer.customer_id
                print(f"Created new customer: {new_customer.name} with ID {created_customer_id}")
                
        except Exception as e:
            # If customer creation fails, continue with bill creation (don't let it fail)
            print(f"Error creating customer: {e}")
            created_customer_id = None
    
    for idx, (pid, product_name, qty, price, discount, custom_gst) in enumerate(zip(items, product_names, quantities, prices, discounts, gst_rates_custom)):
        qty = float(qty)
        price = float(price)
        discount = float(discount) if discount else 0
        custom_gst = float(custom_gst) if custom_gst else 0
        
        # Check if this is an existing product or a custom product
        if pid and pid.strip():  # Existing product
            product = Product.query.get(pid)
            if not product:
                continue
                
            # Get GST rate from product
            gst_rate = float(product.gst_rate or 0)
            hsn_code = product.hsn_code or ''
            is_custom_product = False
            
        else:  # Custom product (no product_id)
            product = None
            gst_rate = custom_gst
            hsn_code = ''  # Can be extended to accept HSN from form
            is_custom_product = True
            
            # Skip if no product name for custom product
            if not product_name or not product_name.strip():
                continue
        
        # Calculate base price
        total_base_price = price * qty
        
        # Calculate discount
        discount_amount = total_base_price * (discount / 100.0)
        
        # Calculate discounted price (taxable value)
        discounted_price = total_base_price - discount_amount
        
        # Calculate CGST and SGST (50/50 split)
        cgst_rate_percentage = gst_rate / 2.0
        sgst_rate_percentage = gst_rate / 2.0
        
        cgst_amount = discounted_price * (cgst_rate_percentage / 100.0)
        sgst_amount = discounted_price * (sgst_rate_percentage / 100.0)
        total_gst_item_amount = cgst_amount + sgst_amount
        
        # Final price for item
        final_price_item = discounted_price + total_gst_item_amount
        
        # Create bill item
        if is_custom_product:
            # Create bill item for custom product
            bill_item = BillItem(
                bill_id=bill.bill_id,
                product_id=None,  # No product_id for custom products
                custom_product_name=product_name.strip(),
                custom_gst_rate=gst_rate,
                custom_hsn_code=hsn_code,
                quantity=qty,
                price_per_unit=price,
                total_price=final_price_item
            )
        else:
            # Create bill item for existing product
            bill_item = BillItem(
                bill_id=bill.bill_id,
                product_id=pid,
                custom_product_name=None,
                custom_gst_rate=None,
                custom_hsn_code=None,
                quantity=qty,
                price_per_unit=price,
                total_price=final_price_item
            )
        db.session.add(bill_item)
        bill_items.append(bill_item)
        
        # Store calculated data for template
        if is_custom_product:
            # Create a mock product object for custom products
            mock_product = type('Product', (), {
                'product_name': product_name.strip(),
                'gst_rate': gst_rate,
                'hsn_code': hsn_code,
                'product_id': f'custom_{idx}'  # Unique identifier for template
            })()
            
            item_data = {
                'product': mock_product,
                'is_custom': True,
                'quantity': qty,
                'base_price': price,
                'total_base_price': total_base_price,
                'discount': discount,
                'discount_amount': discount_amount,
                'discounted_price': discounted_price,
                'gst_rate': gst_rate,
                'cgst_rate': cgst_rate_percentage,
                'sgst_rate': sgst_rate_percentage,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'total_gst_amount': total_gst_item_amount,
                'final_price': final_price_item,
                'hsn_code': hsn_code
            }
        else:
            item_data = {
                'product': product,
                'is_custom': False,
                'quantity': qty,
                'base_price': price,
                'total_base_price': total_base_price,
                'discount': discount,
                'discount_amount': discount_amount,
                'discounted_price': discounted_price,
                'gst_rate': gst_rate,
                'cgst_rate': cgst_rate_percentage,
                'sgst_rate': sgst_rate_percentage,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'total_gst_amount': total_gst_item_amount,
                'final_price': final_price_item,
                'hsn_code': hsn_code
            }
        bill_items_data.append(item_data)
        
        # Aggregate by GST rate
        gst_rate_key = str(int(gst_rate)) if gst_rate > 0 else '0'
        if gst_rate_key not in gst_summary_by_rate:
            gst_summary_by_rate[gst_rate_key] = {
                'taxable_amount': 0.0,
                'cgst_amount': 0.0,
                'sgst_amount': 0.0,
                'total_gst_amount': 0.0
            }
        
        gst_summary_by_rate[gst_rate_key]['taxable_amount'] += discounted_price
        gst_summary_by_rate[gst_rate_key]['cgst_amount'] += cgst_amount
        gst_summary_by_rate[gst_rate_key]['sgst_amount'] += sgst_amount
        gst_summary_by_rate[gst_rate_key]['total_gst_amount'] += total_gst_item_amount
        
        overall_grand_total += final_price_item
        
        # Update product stock only for existing products (not custom products)
        if product and not is_custom_product:
            product.stock_qty = product.stock_qty - int(qty)
    
    bill.total_amount = overall_grand_total
    try:
    # Update paid_amount and due_amount based on final total if needed
        if payment_status == 'Paid':
            paid_amount = overall_grand_total
            due_amount = 0
        elif payment_status == 'Unpaid':
            paid_amount = 0
            due_amount = overall_grand_total
        else:
                # For partial payments, use the calculated amounts
                paid_amount = float(request.form.get('calculated_paid_amount', 0))
                due_amount = float(request.form.get('calculated_unpaid_amount', 0))
    except Exception:
        # Fallback values
        paid_amount = 0
        due_amount = 0
    
    bill.paid_amount = paid_amount
    bill.due_amount = due_amount
    db.session.commit()
    
    # Calculate grand total summary
    total_taxable_amount = sum(summary['taxable_amount'] for summary in gst_summary_by_rate.values())
    total_cgst_amount = sum(summary['cgst_amount'] for summary in gst_summary_by_rate.values())
    total_sgst_amount = sum(summary['sgst_amount'] for summary in gst_summary_by_rate.values())
    total_gst_amount = sum(summary['total_gst_amount'] for summary in gst_summary_by_rate.values())
    
    # Prepare data for receipt
    bill_data = {
        'bill': bill,
        'bill_items': bill_items,
        'bill_items_data': bill_items_data,
        'shopkeeper': shopkeeper,
        'products': {str(p.product_id): p for p in products},
        'gst_summary_by_rate': gst_summary_by_rate,
        'overall_grand_total': overall_grand_total,
        'total_taxable_amount': total_taxable_amount,
        'total_cgst_amount': total_cgst_amount,
        'total_sgst_amount': total_sgst_amount,
        'total_gst_amount': total_gst_amount,
        'gst_mode': gst_mode,
        'bill_gst_type': bill_gst_type,
        'bill_gst_rate': bill_gst_rate,
        'amount_paid': paid_amount,
        'amount_unpaid': due_amount,
        'payment_status': payment_status
    }
    
    # rendered = render_template('shopkeeper/bill_receipt.html', **bill_data, back_url=url_for('shopkeeper.manage_bills'))
    # bills_dir = os.path.join('app', 'static', 'bills')
    # os.makedirs(bills_dir, exist_ok=True)
    # # Use current system date/time for filename
    # filename_date = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    # filename = f"bill_{filename_date}_{bill_number}.html"
    # filepath = os.path.join(bills_dir, filename)
    # with open(filepath, 'w', encoding='utf-8') as f:
    #     f.write(rendered)
    # bill.pdf_file_path = f'static/bills/{filename}'
    
    # Create ledger entry for customers with unpaid/partial amounts (existing OR newly created)
    # Add logging to help debug missing ledger entries
    if bill.customer_id and (payment_status == 'Unpaid' or payment_status == 'Partial'):
        try:
            current_app.logger.debug(f"Preparing ledger entries: bill_id={bill.bill_id}, customer_id={bill.customer_id}, payment_status={payment_status}, paid_amount={paid_amount}, overall_total={overall_grand_total}")
            customer = Customer.query.get(bill.customer_id)
            if customer:
                # Calculate debit and credit amounts
                debit_amount = Decimal(str(overall_grand_total))  # Total bill amount (purchase)
                credit_amount = Decimal(str(paid_amount))  # Amount paid

                # Calculate new balance
                current_balance = customer.total_balance or Decimal('0')
                new_balance = current_balance + debit_amount - credit_amount

                # Create purchase ledger entry
                purchase_entry = CustomerLedger(
                    customer_id=customer.customer_id,
                    shopkeeper_id=shopkeeper.user_id,
                    invoice_no=bill_number,
                    particulars=f"Bill Purchase - {bill_number}",
                    debit_amount=debit_amount,
                    credit_amount=0,
                    balance_amount=current_balance + debit_amount,
                    transaction_type='PURCHASE',
                    reference_bill_id=bill.bill_id,
                    notes=f"Products purchased via bill {bill_number}"
                )
                db.session.add(purchase_entry)

                # If there's a payment, create payment entry
                if credit_amount > 0:
                    payment_entry = CustomerLedger(
                        customer_id=customer.customer_id,
                        shopkeeper_id=shopkeeper.user_id,
                        invoice_no=f"PAY-{bill_number}",
                        particulars=f"Payment for Bill {bill_number}",
                        debit_amount=0,
                        credit_amount=credit_amount,
                        balance_amount=new_balance,
                        transaction_type='PAYMENT',
                        reference_bill_id=bill.bill_id,
                        notes=f"Partial payment for bill {bill_number}"
                    )
                    db.session.add(payment_entry)

                # Update customer balance
                customer.total_balance = new_balance
                customer.updated_date = datetime.datetime.now()
                current_app.logger.debug(f"Ledger entries created for customer_id={customer.customer_id}, new_balance={new_balance}")
            else:
                current_app.logger.warning(f"Bill has customer_id={bill.customer_id} but no customer found in DB.")

        except Exception:
            current_app.logger.exception("Error creating ledger entry")
            # Don't fail the bill creation if ledger entry fails
            pass
    
    # Add appropriate flash messages based on customer creation outcome
    if customer_type == 'new' and save_as_customer and customer_name and customer_name.strip():
        if created_customer_id:
            existing_customer = Customer.query.filter_by(
                shopkeeper_id=shopkeeper.user_id,
                phone=customer_contact.strip() if customer_contact else ''
            ).first() if customer_contact else None
            
            if existing_customer and existing_customer.customer_id == created_customer_id and customer_contact:
                flash(f'Bill created successfully! Existing customer "{existing_customer.name}" was used.', 'success')
            else:
                flash('Bill created successfully! Customer saved to your customer list.', 'success')
        else:
            flash('Bill created successfully! (Customer could not be saved due to an error.)', 'warning')
    elif customer_type == 'new' and not save_as_customer:
        flash('Bill created successfully!', 'success')
    elif customer_type == 'existing':
        flash('Bill created successfully!', 'success')
    
    db.session.commit()
    return render_template('shopkeeper/bill_receipt.html', **bill_data, back_url=url_for('shopkeeper.manage_bills'))

@shopkeeper_bp.route('/bills/<filename>')
def serve_bill_file(filename):
    return send_from_directory(os.path.join('app', 'static', 'bills'), filename)

@shopkeeper_bp.route('/profile')
@login_required
@shopkeeper_required
def profile():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    return render_template('shopkeeper/profile.html', shopkeeper=shopkeeper)

@shopkeeper_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@shopkeeper_required
def profile_edit():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    if request.method == 'POST':
        shopkeeper.shop_name = request.form.get('shop_name')
        shopkeeper.domain = request.form.get('domain')
        shopkeeper.address = request.form.get('address')
        shopkeeper.gst_number = request.form.get('gst_number')
        shopkeeper.contact_number = request.form.get('contact_number')
        shopkeeper.city = request.form.get('city')
        shopkeeper.state = request.form.get('state')
        shopkeeper.pincode = request.form.get('pincode')
        shopkeeper.bank_name = request.form.get('bank_name')
        shopkeeper.account_number = request.form.get('account_number')
        shopkeeper.ifsc_code = request.form.get('ifsc_code')
        shopkeeper.template_choice = request.form.get('template_choice')
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('shopkeeper.profile'))
    return render_template('shopkeeper/profile_edit.html', shopkeeper=shopkeeper)

def update_shopkeeper_verification(shopkeeper):
    required_fields = [
        shopkeeper.aadhaar_dl_path,
        shopkeeper.pan_doc_path,
        shopkeeper.address_proof_path,
        shopkeeper.selfie_path,
        shopkeeper.gumasta_path,
        shopkeeper.bank_statement_path,
    ]
    shopkeeper.is_verified = all(required_fields)
    db.session.commit()

@shopkeeper_bp.route('/upload_document/<doc_type>', methods=['POST'])
@login_required
@shopkeeper_required
def upload_document(doc_type):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    file = request.files.get('document')
    allowed_exts = {'pdf', 'jpg', 'jpeg', 'png'}
    max_size = 2 * 1024 * 1024  # 2MB
    if file:
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed_exts:
            flash('Invalid file type. Only PDF, JPG, PNG allowed.', 'danger')
            return redirect(url_for('shopkeeper.profile'))
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > max_size:
            flash('File too large. Max 2MB allowed.', 'danger')
            return redirect(url_for('shopkeeper.profile'))
        filename = f"shopkeeper_{shopkeeper.shopkeeper_id}_{doc_type}.{ext}"
        save_path = os.path.join('app', 'static', 'uploads', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)
        rel_path = f"uploads/{filename}"
        if doc_type == 'gst':
            shopkeeper.gst_doc_path = rel_path
        elif doc_type == 'pan':
            shopkeeper.pan_doc_path = rel_path
        elif doc_type == 'address_proof':
            shopkeeper.address_proof_path = rel_path
        elif doc_type == 'logo':
            shopkeeper.logo_path = rel_path
        elif doc_type == 'aadhaar_dl':
            shopkeeper.aadhaar_dl_path = rel_path
        elif doc_type == 'selfie':
            shopkeeper.selfie_path = rel_path
        elif doc_type == 'gumasta':
            shopkeeper.gumasta_path = rel_path
        elif doc_type == 'udyam':
            shopkeeper.udyam_path = rel_path
        elif doc_type == 'bank_statement':
            shopkeeper.bank_statement_path = rel_path
        db.session.commit()
        update_shopkeeper_verification(shopkeeper)
        flash(f'{doc_type.replace("_", " ").title()} uploaded successfully.', 'success')
    else:
        flash('No file selected.', 'danger')
    return redirect(url_for('shopkeeper.profile'))

@shopkeeper_bp.route('/delete_document/<doc_type>', methods=['POST'])
@login_required
@shopkeeper_required
def delete_document(doc_type):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    if doc_type == 'gst' and shopkeeper.gst_doc_path:
        shopkeeper.gst_doc_path = None
    elif doc_type == 'pan' and shopkeeper.pan_doc_path:
        shopkeeper.pan_doc_path = None
    elif doc_type == 'address_proof' and shopkeeper.address_proof_path:
        shopkeeper.address_proof_path = None
    elif doc_type == 'logo' and shopkeeper.logo_path:
        shopkeeper.logo_path = None
    elif doc_type == 'aadhaar_dl' and shopkeeper.aadhaar_dl_path:
        shopkeeper.aadhaar_dl_path = None
    elif doc_type == 'selfie' and shopkeeper.selfie_path:
        shopkeeper.selfie_path = None
    elif doc_type == 'gumasta' and shopkeeper.gumasta_path:
        shopkeeper.gumasta_path = None
    elif doc_type == 'udyam' and shopkeeper.udyam_path:
        shopkeeper.udyam_path = None
    elif doc_type == 'bank_statement' and shopkeeper.bank_statement_path:
        shopkeeper.bank_statement_path = None
    db.session.commit()
    update_shopkeeper_verification(shopkeeper)
    flash(f'{doc_type.replace("_", " ").title()} deleted successfully.', 'success')
    return redirect(url_for('shopkeeper.profile'))

def get_shopkeeper_pending_requests():
    if hasattr(g, 'shopkeeper_pending_requests'):
        return g.shopkeeper_pending_requests
    from flask_login import current_user
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated and getattr(current_user, 'role', None) == 'shopkeeper':
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if shopkeeper:
            pending = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id, status='pending').all()
            requests = []
            for conn in pending:
                ca = CharteredAccountant.query.get(conn.ca_id)
                requests.append({
                    'conn_id': conn.id,
                    'ca_id': ca.ca_id,
                    'ca_firm_name': ca.firm_name,
                    'ca_area': ca.area,
                    'ca_contact_number': ca.contact_number
                })
            g.shopkeeper_pending_requests = requests
            return requests
    g.shopkeeper_pending_requests = []
    return []

@shopkeeper_bp.app_context_processor
def inject_shopkeeper_pending_requests():
    return {'shopkeeper_pending_requests': get_shopkeeper_pending_requests()}

@shopkeeper_bp.route('/handle_connection_request', methods=['POST'])
@login_required
@shopkeeper_required
def handle_connection_request():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    conn_id = request.form.get('conn_id')
    action = request.form.get('action')
    conn = CAConnection.query.get(conn_id)
    if conn and conn.shopkeeper_id == shopkeeper.shopkeeper_id and conn.status == 'pending':
        # Find or create the corresponding ShopConnection
        shop_conn = ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=conn.ca_id).first()
        if not shop_conn:
            shop_conn = ShopConnection(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=conn.ca_id, status='pending')
            db.session.add(shop_conn)
        if action == 'accept':
            conn.status = 'approved'
            shop_conn.status = 'approved'
            db.session.commit()
            flash('Connection approved.', 'success')
        elif action == 'reject':
            conn.status = 'rejected'
            shop_conn.status = 'rejected'
            db.session.commit()
            flash('Connection rejected.', 'info')
    return redirect(request.referrer or url_for('shopkeeper.dashboard'))

@shopkeeper_bp.route('/update_payment/<int:bill_id>', methods=['POST'])
@login_required
@shopkeeper_required
def update_payment(bill_id):
    # Bill payment updates are now disabled - use customer ledger instead
    return jsonify({
        'success': False, 
        'message': 'Bill payment updates are disabled. Please use Customer Ledger to manage payments.'
    })

@shopkeeper_bp.route('/customer_management')
@login_required
@shopkeeper_required
def customer_management():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    if not shopkeeper:
        flash('Shopkeeper profile not found.', 'error')
        return redirect(url_for('shopkeeper.dashboard'))
    
    # Get all customers for this shopkeeper
    customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id, is_active=True).all()
    
    # Calculate customer statistics
    active_customers_count = len([c for c in customers if c.total_balance > 0])
    total_sales = sum(float(c.total_balance) for c in customers if c.total_balance > 0)
    avg_order_value = total_sales / len(customers) if customers else 0
    
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
                         customers=customers,
                         active_customers_count=active_customers_count,
                         total_sales=total_sales,
                         avg_order_value=avg_order_value,
                         unique_locations=unique_locations)

@shopkeeper_bp.route('/add_customer', methods=['POST'])
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

@shopkeeper_bp.route('/get_customer/<int:customer_id>')
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

@shopkeeper_bp.route('/update_customer/<int:customer_id>', methods=['PUT'])
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

@shopkeeper_bp.route('/delete_customer/<int:customer_id>', methods=['DELETE'])
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

@shopkeeper_bp.route('/get_customer_details/<int:customer_id>')
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

@shopkeeper_bp.route('/customer_ledger/<int:customer_id>')
@login_required
@shopkeeper_required
def customer_ledger(customer_id):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    customer = Customer.query.filter_by(customer_id=customer_id, shopkeeper_id=shopkeeper.user_id).first()
    
    if not customer:
        flash('Customer not found.', 'error')
        return redirect(url_for('shopkeeper.customer_management'))
    
    # Get ledger entries
    ledger_entries = CustomerLedger.query.filter_by(customer_id=customer_id).order_by(desc(CustomerLedger.transaction_date)).all()
    
    return render_template('shopkeeper/customer_ledger.html', 
                         customer=customer, 
                         ledger_entries=ledger_entries)

@shopkeeper_bp.route('/add_ledger_entry/<int:customer_id>', methods=['POST'])
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

@shopkeeper_bp.route('/get_customers_list')
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

@shopkeeper_bp.route('/export_customers')
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

@shopkeeper_bp.route('/customer_ledger_overview')
@login_required
@shopkeeper_required
def customer_ledger_overview():
    """Customer ledger overview page showing all customers with ledger access"""
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
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
                         customers=customers,
                         total_customers=total_customers,
                         total_outstanding=total_outstanding,
                         total_advance=total_advance)
