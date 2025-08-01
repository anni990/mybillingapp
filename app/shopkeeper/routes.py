from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory, g
from flask_login import login_required, current_user
from app.models import Product, Shopkeeper, Bill, BillItem, CharteredAccountant, CAConnection, ShopConnection, Document, User
from app.extensions import db
from sqlalchemy import func
import datetime
import io
import os

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
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # Sales summary
    today = datetime.date.today()
    bills_today = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).filter(Bill.bill_date == today).all() if shopkeeper else []
    total_amount = sum(b.total_amount for b in bills_today)
    paid = sum(1 for b in bills_today if b.payment_status == 'Paid')
    unpaid = sum(1 for b in bills_today if b.payment_status == 'Unpaid')
    partial = sum(1 for b in bills_today if b.payment_status == 'Partial')
    # Low stock
    low_stock = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).filter(Product.stock_qty <= Product.low_stock_threshold).all() if shopkeeper else []
    # Recent bills
    recent_bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).order_by(Bill.bill_date.desc()).limit(5).all() if shopkeeper else []
    # CA connection
    ca_conn = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id, status='approved').first() if shopkeeper else None
    ca = CharteredAccountant.query.get(ca_conn.ca_id) if ca_conn else None
    return render_template('shopkeeper/dashboard.html',
        total_amount=total_amount,
        paid=paid,
        unpaid=unpaid,
        partial=partial,
        low_stock=low_stock,
        recent_bills=recent_bills,
        ca=ca
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
            bill_date=bill_date,
            gst_type=gst_type,
            total_amount=total_amount,
            payment_status='Paid'
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
    return render_template('shopkeeper/create_bill.html', products=products, products_js=products_js, shopkeeper=shopkeeper)

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
    items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
    shopkeeper = bill.shopkeeper
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
    products_dict = {str(p.product_id): p for p in products}
    if bill.pdf_file_path:
        # Try to read the HTML file and render it
        try:
            with open(os.path.join('app', bill.pdf_file_path), 'r', encoding='utf-8') as f:
                bill_html = f.read()
            # Render as safe HTML
            from flask import Markup
            return bill_html
        except Exception:
            pass
    # Fallback: render the template
    return render_template('shopkeeper/bill_receipt.html', bill=bill, bill_items=items, shopkeeper=shopkeeper, products=products_dict, back_url=url_for('shopkeeper.manage_bills'))

@shopkeeper_bp.route('/bill/delete/<int:bill_id>', methods=['POST'])
@login_required
@shopkeeper_required
def delete_bill(bill_id):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    # In all relevant routes, comment out the is_verified restriction logic
    # Example for create_bill:
    #    if not shopkeeper.is_verified:
    #        flash('Please upload all required documents to use this service.', 'danger')
    #        return redirect(url_for('shopkeeper.profile'))
    bill = Bill.query.get_or_404(bill_id)
    if bill.shopkeeper.user_id != current_user.user_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('shopkeeper.manage_bills'))
    db.session.delete(bill)
    db.session.commit()
    flash('Bill deleted.', 'success')
    return redirect(url_for('shopkeeper.manage_bills'))

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
    # Get connection status for each CA (shopkeeper-initiated)
    connections = {c.ca_id: c for c in ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()}
    return render_template('shopkeeper/ca_marketplace.html', cas=cas, connections=connections)

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

# # Documents
# @shopkeeper_bp.route('/documents', methods=['GET', 'POST'])
# @login_required
# @shopkeeper_required
# def documents():
#     shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
#     if request.method == 'POST':
#         file = request.files.get('file')
#         name = request.form.get('name')
#         if file and name:
#             path = f'static/uploads/{file.filename}'
#             file.save(path)
#             doc = Document(shopkeeper_id=shopkeeper.shopkeeper_id, document_name=name, file_path=path)
#             db.session.add(doc)
#             db.session.commit()
#             flash('Document uploaded.', 'success')
#         else:
#             flash('File and name required.', 'danger')
#     docs = Document.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
#     return render_template('shopkeeper/documents.html', docs=docs)

# @shopkeeper_bp.route('/documents/delete/<int:doc_id>', methods=['POST'])
# @login_required
# @shopkeeper_required
# def delete_document(doc_id):
#     doc = Document.query.get_or_404(doc_id)
#     if doc.shopkeeper.user_id != current_user.user_id:
#         flash('Access denied.', 'danger')
#         return redirect(url_for('shopkeeper.documents'))
#     db.session.delete(doc)
#     db.session.commit()
#     flash('Document deleted.', 'success')
#     return redirect(url_for('shopkeeper.documents'))

# @shopkeeper_bp.route('/documents/download/<int:doc_id>')
# @login_required
# @shopkeeper_required
# def download_document(doc_id):
#     doc = Document.query.get_or_404(doc_id)
#     if doc.shopkeeper.user_id != current_user.user_id:
#         flash('Access denied.', 'danger')
#         return redirect(url_for('shopkeeper.documents'))
#     return send_file(doc.file_path, as_attachment=True)

# Settings
@shopkeeper_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@shopkeeper_required
def settings():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    user = User.query.get(current_user.user_id)
    if request.method == 'POST':
        shop_name = request.form.get('shop_name')
        domain = request.form.get('domain')
        address = request.form.get('address')
        gst_number = request.form.get('gst_number')
        contact_number = request.form.get('contact_number')
        if shopkeeper:
            shopkeeper.shop_name = shop_name
            shopkeeper.domain = domain
            shopkeeper.address = address
            shopkeeper.gst_number = gst_number
            shopkeeper.contact_number = contact_number
            db.session.commit()
            flash('Profile updated.', 'success')
        # Password change
        current_pw = request.form.get('current_password')
        new_pw = request.form.get('new_password')
        confirm_pw = request.form.get('confirm_new_password')
        if current_pw and new_pw and new_pw == confirm_pw:
            from werkzeug.security import check_password_hash, generate_password_hash
            if check_password_hash(user.password_hash, current_pw):
                user.password_hash = generate_password_hash(new_pw)
                db.session.commit()
                flash('Password changed.', 'success')
            else:
                flash('Current password incorrect.', 'danger')
    return render_template('shopkeeper/settings.html', shopkeeper=shopkeeper)

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
    product.product_name = request.form.get('product_name')
    product.barcode = request.form.get('barcode')
    product.price = request.form.get('price')
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
    customer_name = request.form.get('customer_name')
    customer_contact = request.form.get('customer_contact')
    gst_mode = request.form.get('gst_mode', 'exclusive')
    bill_gst_type = request.form.get('bill_gst_type', 'GST')
    bill_gst_rate = float(request.form.get('bill_gst_rate', 0))
    items = request.form.getlist('product_id')
    quantities = request.form.getlist('quantity')
    prices = request.form.getlist('price_per_unit')
    discounts = request.form.getlist('discount')
    bill_date = datetime.date.today()
    total_amount = 0
    bill_number = f"BILL{int(datetime.datetime.now().timestamp())}"
    payment_status = request.form.get('bill_status', 'Paid').capitalize()
    try:
        amount_paid = float(request.form.get('calculated_paid_amount', 0))
    except Exception:
        amount_paid = 0
    try:
        amount_unpaid = float(request.form.get('calculated_unpaid_amount', 0))
    except Exception:
        amount_unpaid = 0
    
    bill = Bill(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        bill_number=bill_number,
        customer_name=customer_name,
        customer_contact=customer_contact,
        bill_date=bill_date,
        gst_type=bill_gst_type,
        total_amount=0,
        payment_status=payment_status,
        amount_paid=amount_paid,
        amount_unpaid=amount_unpaid
    )
    db.session.add(bill)
    db.session.flush()
    
    bill_items = []
    bill_items_data = []
    gst_summary_by_rate = {}
    overall_grand_total = 0.0
    
    for idx, (pid, qty, price, discount) in enumerate(zip(items, quantities, prices, discounts)):
        qty = float(qty)
        price = float(price)
        discount = float(discount) if discount else 0
        product = Product.query.get(pid)
        
        if not product:
            continue
            
        # Get GST rate from product
        gst_rate = float(product.gst_rate or 0)
        hsn_code = product.hsn_code or ''
        
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
        bill_item = BillItem(
            bill_id=bill.bill_id,
            product_id=pid,
            quantity=qty,
            price_per_unit=price,
            total_price=final_price_item
        )
        db.session.add(bill_item)
        bill_items.append(bill_item)
        
        # Store calculated data for template
        item_data = {
            'product': product,
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
        
        # Update product stock
        if product:
            product.stock_qty = product.stock_qty - int(qty)
    
    bill.total_amount = overall_grand_total
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
        'amount_paid': amount_paid,
        'amount_unpaid': amount_unpaid,
        'payment_status': payment_status
    }
    
    rendered = render_template('shopkeeper/bill_receipt.html', **bill_data, back_url=url_for('shopkeeper.manage_bills'))
    bills_dir = os.path.join('app', 'static', 'bills')
    os.makedirs(bills_dir, exist_ok=True)
    filename = f"bill_{bill_date}_{bill_number}.html"
    filepath = os.path.join(bills_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rendered)
    bill.pdf_file_path = f'static/bills/{filename}'
    db.session.commit()
    return render_template('shopkeeper/bill_receipt.html', **bill_data, bill_file=filename, back_url=url_for('shopkeeper.manage_bills'))

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
