from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory
from flask_login import login_required, current_user
from app.models import Product, Shopkeeper, Bill, BillItem, CharteredAccountant, CAConnection, Document, User
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
    products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
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
    return render_template('shopkeeper/create_bill.html', products=products)

# Manage Bills
@shopkeeper_bp.route('/manage_bills')
@login_required
@shopkeeper_required
def manage_bills():
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).order_by(Bill.bill_date.desc()).all() if shopkeeper else []
    return render_template('shopkeeper/manage_bills.html', bills=bills)

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
    return render_template('shopkeeper/ca_marketplace.html', cas=cas)

@shopkeeper_bp.route('/connect_ca/<int:ca_id>', methods=['POST'])
@login_required
@shopkeeper_required
def connect_ca(ca_id):
    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
    existing = CAConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=ca_id).first()
    if not existing:
        conn = CAConnection(shopkeeper_id=shopkeeper.shopkeeper_id, ca_id=ca_id, status='pending')
        db.session.add(conn)
        db.session.commit()
        flash('Connection request sent.', 'success')
    else:
        flash('Already connected or pending.', 'info')
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
    gst_type = request.form.get('gst_type')
    items = request.form.getlist('product_id')
    quantities = request.form.getlist('quantity')
    prices = request.form.getlist('price_per_unit')
    bill_date = datetime.date.today()
    total_amount = sum(float(q)*float(p) for q, p in zip(quantities, prices))
    bill_number = f"BILL{int(datetime.datetime.now().timestamp())}"
    # Save bill to DB
    bill = Bill(
        shopkeeper_id=shopkeeper.shopkeeper_id,
        bill_number=bill_number,
        customer_name=customer_name,
        customer_contact=customer_contact,
        bill_date=bill_date,
        gst_type=gst_type,
        total_amount=total_amount,
        payment_status='Paid'
    )
    db.session.add(bill)
    db.session.flush()  # get bill_id
    bill_items = []
    for pid, qty, price in zip(items, quantities, prices):
        bill_item = BillItem(
            bill_id=bill.bill_id,
            product_id=pid,
            quantity=qty,
            price_per_unit=price,
            total_price=float(qty)*float(price)
        )
        db.session.add(bill_item)
        bill_items.append(bill_item)
        # Update product stock
        product = Product.query.get(pid)
        if product:
            product.stock_qty = product.stock_qty - int(qty)
    # Save HTML as file
    bills_dir = os.path.join('app', 'static', 'bills')
    os.makedirs(bills_dir, exist_ok=True)
    filename = f"bill_{bill_date}_{bill_number}.html"
    filepath = os.path.join(bills_dir, filename)
    # Prepare data for receipt
    bill_data = {
        'bill': bill,
        'bill_items': bill_items,
        'shopkeeper': shopkeeper,
        'products': {str(p.product_id): p for p in products},
    }
    rendered = render_template('shopkeeper/bill_receipt.html', **bill_data, back_url=url_for('shopkeeper.manage_bills'))
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(rendered)
    # Save file path in DB
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
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('shopkeeper.profile'))
    return render_template('shopkeeper/profile_edit.html', shopkeeper=shopkeeper)

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
        db.session.commit()
        flash(f'{doc_type.replace("_", " ").title()} uploaded successfully.', 'success')
    else:
        flash('No file selected.', 'danger')
    return redirect(url_for('shopkeeper.profile'))
