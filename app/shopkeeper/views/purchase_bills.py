"""
Purchase Bill management routes for shopkeeper.
Handles purchase bill scanning and management with Gemini AI integration.
"""
from flask import (render_template, request, flash, redirect, url_for, 
                   send_file, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc
import datetime
import os
import uuid
from decimal import Decimal

from ..utils import shopkeeper_required, get_current_shopkeeper
from app.models import (Bill, BillItem, Product, Customer, CustomerLedger, 
                       Shopkeeper, CharteredAccountant, CAConnection, EmployeeClient, 
                       PurchaseBill, PurchaseBillItem)
from app.extensions import db
from ..services.gemini_service import get_gemini_service


def register_routes(bp):
    """Register purchase bill management routes to the blueprint."""
    

    # Purchase Bills Management Page
    @bp.route('/purchase_bills')
    @login_required
    @shopkeeper_required
    def purchase_bills():
        """Display all purchase bills for the shopkeeper."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('auth.login'))
        
        shop_name = shopkeeper.shop_name
        
        # Get filter parameters
        search_query = request.args.get('search', '')
        status_filter = request.args.get('status', 'all')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Base query for purchase bills
        query = PurchaseBill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
        
        # Apply search filter
        if search_query:
            query = query.filter(
                or_(
                    PurchaseBill.vendor_name.ilike(f'%{search_query}%'),
                    PurchaseBill.invoice_number.ilike(f'%{search_query}%'),
                    PurchaseBill.vendor_phone.ilike(f'%{search_query}%')
                )
            )
        
        # Apply status filter
        if status_filter and status_filter != 'all':
            query = query.filter(PurchaseBill.processing_status == status_filter)
        
        # Apply date filters
        if date_from:
            try:
                from_date = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(PurchaseBill.bill_date >= from_date)
            except ValueError:
                pass
                
        if date_to:
            try:
                to_date = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(PurchaseBill.bill_date <= to_date)
            except ValueError:
                pass
        
        # Order by scanned_at descending (most recent first)
        purchase_bills = query.order_by(desc(PurchaseBill.scanned_at)).all()
        
        # Calculate statistics
        total_bills = len(purchase_bills)
        completed_bills = [bill for bill in purchase_bills if bill.processing_status == 'completed']
        processing_bills = [bill for bill in purchase_bills if bill.processing_status == 'processing']
        failed_bills = [bill for bill in purchase_bills if bill.processing_status == 'failed']
        
        total_amount = sum(float(bill.total_amount or 0) for bill in completed_bills)
        
        stats = {
            'total_bills': total_bills,
            'total_amount': total_amount,
            'completed_bills': len(completed_bills),
            'processing_bills': len(processing_bills),
            'failed_bills': len(failed_bills),
            'paid_amount': 0,  # Purchase bills don't have payment status in our schema
            'unpaid_amount': 0  # Purchase bills don't have payment status in our schema
        }
        
        return render_template(
            'shopkeeper/purchase_bills.html',
            shop_name=shop_name,
            purchase_bills=purchase_bills,
            stats=stats,
            search_query=search_query,
            status_filter=status_filter,
            date_from=date_from,
            date_to=date_to,
            shopkeeper=shopkeeper
        )


    # Scan Purchase Bill Page
    @bp.route('/scan_purchase_bill')
    @login_required
    @shopkeeper_required
    def scan_purchase_bill():
        """Display the purchase bill scanning interface."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('auth.login'))
        
        shop_name = shopkeeper.shop_name
        
        # Get all products for the shopkeeper (for product suggestions)
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
        products_js = [
            {
                'id': p.product_id,
                'name': p.product_name,
                'price': float(p.price),
                'stock': p.stock_qty,
                'gst_rate': float(p.gst_rate or 0),
                'hsn_code': p.hsn_code or ''
            } for p in products
        ]
        
        return render_template(
            'shopkeeper/scan_purchase_bill.html',
            shop_name=shop_name,
            shopkeeper=shopkeeper,
            products=products,
            products_js=products_js,
            now=datetime.datetime.now()
        )


    # Process Scanned Purchase Bill (POST route for AI file upload)
    @bp.route('/scan_purchase_bill', methods=['POST'])
    @login_required
    @shopkeeper_required
    def process_scanned_purchase_bill():
        """Handle purchase bill scanning via file upload or camera with AI processing."""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                return jsonify({'success': False, 'message': 'Shopkeeper profile not found.'})
            
            # Check if file was uploaded
            if 'bill_file' not in request.files:
                return jsonify({'success': False, 'message': 'No file uploaded.'})
            
            file = request.files['bill_file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No file selected.'})
            
            # Validate file type
            allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'message': 'Invalid file type. Please upload PDF, JPG, JPEG, or PNG files.'})
            
            # Create purchase bill record
            purchase_bill = PurchaseBill(
                shopkeeper_id=shopkeeper.shopkeeper_id,
                processing_status='processing'
            )
            db.session.add(purchase_bill)
            db.session.flush()  # Get the ID
            
            # Save file
            filename = secure_filename(f"purchase_bill_{purchase_bill.purchase_bill_id}_{uuid.uuid4().hex[:8]}.{file_ext}")
            upload_dir = os.path.join(current_app.static_folder, 'purchase_bills')
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Update purchase bill with file path
            purchase_bill.file_path = f"purchase_bills/{filename}"
            db.session.commit()
            
            # Process with Gemini AI
            success = _process_bill_with_ai(purchase_bill, file_path, file_ext)
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Purchase bill scanned and processed successfully!',
                    'purchase_bill_id': purchase_bill.purchase_bill_id
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Bill uploaded but processing failed. Please check the file and try again.'
                })
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error in process_scanned_purchase_bill: {str(e)}")
            return jsonify({'success': False, 'message': f'Error processing bill: {str(e)}'})


    # Manual Purchase Bill Entry (POST route for form submission)
    @bp.route('/manual_purchase_bill', methods=['POST'])
    @login_required
    @shopkeeper_required
    def manual_purchase_bill():
        """Handle manual purchase bill entry via form submission."""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                flash('Shopkeeper profile not found.', 'error')
                return redirect(url_for('auth.login'))
            
            # Get vendor details
            vendor_name = request.form.get('vendor_name', '').strip()
            vendor_phone = request.form.get('vendor_phone', '').strip()
            vendor_address = request.form.get('vendor_address', '').strip()
            vendor_gst_number = request.form.get('vendor_gst_number', '').strip()
            vendor_email = request.form.get('vendor_email', '').strip()
            
            # Get bill details
            invoice_number = request.form.get('invoice_number', '').strip()
            bill_date = request.form.get('bill_date')
            
            # Validate required fields
            if not vendor_name:
                flash('Vendor name is required.', 'error')
                return redirect(url_for('shopkeeper.scan_purchase_bill'))
            
            # Parse bill date
            if bill_date:
                try:
                    bill_date_obj = datetime.datetime.strptime(bill_date, '%Y-%m-%d').date()
                except ValueError:
                    bill_date_obj = datetime.date.today()
            else:
                bill_date_obj = datetime.date.today()
            
            # Get product data from form
            product_names = request.form.getlist('product_name[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            gst_rates = request.form.getlist('gst_rate[]')
            hsn_codes = request.form.getlist('hsn_code[]')
            
            # Validate products
            if not product_names or len(product_names) == 0:
                flash('At least one product is required.', 'error')
                return redirect(url_for('shopkeeper.scan_purchase_bill'))
            
            # Create purchase bill
            purchase_bill = PurchaseBill(
                shopkeeper_id=shopkeeper.shopkeeper_id,
                vendor_name=vendor_name,
                vendor_phone=vendor_phone,
                vendor_address=vendor_address,
                vendor_gst_number=vendor_gst_number,
                vendor_email=vendor_email,
                invoice_number=invoice_number,
                bill_date=bill_date_obj,
                processing_status='completed'  # Manual entry is immediately completed
            )
            
            db.session.add(purchase_bill)
            db.session.flush()  # Get the ID
            
            total_amount = Decimal('0')
            tax_amount = Decimal('0')
            
            # Process each product
            for i in range(len(product_names)):
                if not product_names[i].strip():
                    continue
                    
                product_name = product_names[i].strip()
                quantity = int(quantities[i]) if quantities[i] else 0
                unit_price = Decimal(prices[i]) if prices[i] else Decimal('0')
                gst_rate = Decimal(gst_rates[i]) if gst_rates[i] else Decimal('0')
                hsn_code = hsn_codes[i].strip() if i < len(hsn_codes) else ''
                
                if quantity <= 0 or unit_price <= 0:
                    continue
                
                # Calculate line totals
                subtotal = quantity * unit_price
                gst_amount = (subtotal * gst_rate) / Decimal('100')
                line_total = subtotal + gst_amount
                
                # Create purchase bill item
                purchase_item = PurchaseBillItem(
                    purchase_bill_id=purchase_bill.purchase_bill_id,
                    item_name=product_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=line_total,
                    gst_rate=gst_rate,
                    hsn_code=hsn_code
                )
                
                db.session.add(purchase_item)
                total_amount += line_total
                tax_amount += gst_amount
                
                # Update or create product stock
                existing_product = Product.query.filter_by(
                    shopkeeper_id=shopkeeper.shopkeeper_id,
                    product_name=product_name
                ).first()
                
                if existing_product:
                    # Update existing product stock and details
                    existing_product.stock_qty = (existing_product.stock_qty or 0) + quantity
                    existing_product.price = unit_price  # Update price to latest purchase price
                    existing_product.gst_rate = gst_rate
                    if hsn_code:
                        existing_product.hsn_code = hsn_code
                        
                    # Mark as matched
                    purchase_item.matched_product_id = existing_product.product_id
                    purchase_item.is_new_product = False
                else:
                    # Create new product
                    new_product = Product(
                        shopkeeper_id=shopkeeper.shopkeeper_id,
                        product_name=product_name,
                        price=unit_price,
                        stock_qty=quantity,
                        gst_rate=gst_rate,
                        hsn_code=hsn_code,
                        low_stock_threshold=5  # Default threshold
                    )
                    db.session.add(new_product)
                    db.session.flush()  # Get product ID
                    
                    # Mark as new product
                    purchase_item.matched_product_id = new_product.product_id
                    purchase_item.is_new_product = True
            
            # Update purchase bill totals
            purchase_bill.total_amount = total_amount
            purchase_bill.tax_amount = tax_amount
            
            # Commit all changes
            db.session.commit()
            
            flash(f'Purchase bill created successfully! Stock updated for {len([p for p in product_names if p.strip()])} products.', 'success')
            return redirect(url_for('shopkeeper.purchase_bills'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error creating manual purchase bill: {str(e)}')
            flash('Error creating purchase bill. Please try again.', 'error')
            return redirect(url_for('shopkeeper.scan_purchase_bill'))


    # View Purchase Bill File
    @bp.route('/purchase-bill-file/<int:bill_id>')
    @login_required
    @shopkeeper_required
    def view_purchase_bill_file(bill_id):
        """Return the uploaded file for viewing in modal."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        purchase_bill = PurchaseBill.query.filter_by(
            purchase_bill_id=bill_id,
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).first_or_404()
        
        if not purchase_bill.file_path:
            return jsonify({'error': 'File not found'}), 404
            
        try:
            file_path = os.path.join(current_app.static_folder, purchase_bill.file_path)
            if os.path.exists(file_path):
                return send_file(file_path)
            else:
                return jsonify({'error': 'File not found on disk'}), 404
        except Exception as e:
            current_app.logger.error(f"Error serving purchase bill file: {str(e)}")
            return jsonify({'error': 'Error accessing file'}), 500


    # Delete Purchase Bill
    @bp.route('/delete_purchase_bill/<int:bill_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def delete_purchase_bill(bill_id):
        """Delete a purchase bill and its items"""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                return jsonify({'success': False, 'message': 'Shopkeeper not found'}), 404
            
            # Get the purchase bill
            purchase_bill = PurchaseBill.query.filter_by(
                purchase_bill_id=bill_id,
                shopkeeper_id=shopkeeper.shopkeeper_id
            ).first()
            
            if not purchase_bill:
                return jsonify({'success': False, 'message': 'Purchase bill not found'}), 404
            
            # Delete associated file if exists
            if purchase_bill.file_path:
                try:
                    file_path = os.path.join(current_app.static_folder, purchase_bill.file_path)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    current_app.logger.error(f"Error deleting file: {str(e)}")
            
            # Delete purchase bill items first (cascade should handle this, but being explicit)
            PurchaseBillItem.query.filter_by(purchase_bill_id=bill_id).delete()
            
            # Delete the purchase bill
            db.session.delete(purchase_bill)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Purchase bill deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting purchase bill: {str(e)}")
            return jsonify({'success': False, 'message': 'Error deleting purchase bill'}), 500


    # View Purchase Bill Details
    @bp.route('/purchase_bill/<int:purchase_bill_id>')
    @login_required
    @shopkeeper_required
    def view_purchase_bill(purchase_bill_id):
        """View details of a specific purchase bill."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'error')
            return redirect(url_for('auth.login'))
        
        purchase_bill = PurchaseBill.query.filter_by(
            purchase_bill_id=purchase_bill_id,
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).first()
        
        if not purchase_bill:
            flash('Purchase bill not found.', 'error')
            return redirect(url_for('shopkeeper.purchase_bills'))
        
        # Get all items for this purchase bill
        purchase_items = PurchaseBillItem.query.filter_by(
            purchase_bill_id=purchase_bill_id
        ).all()
        
        return render_template(
            'shopkeeper/view_purchase_bill.html',
            shop_name=shopkeeper.shop_name,
            purchase_bill=purchase_bill,
            purchase_items=purchase_items,
            shopkeeper=shopkeeper
        )


def _process_bill_with_ai(purchase_bill, file_path, file_ext):
    """Process the uploaded bill with Gemini AI."""
    try:
        # Read file data
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Process with Gemini
        gemini_service = get_gemini_service()
        result = gemini_service.extract_purchase_bill_data(file_data, file_ext)
        
        if not result['success']:
            purchase_bill.processing_status = 'failed'
            purchase_bill.error_message = result.get('error', 'Unknown error')
            db.session.commit()
            return False
        
        # Store raw response for debugging
        purchase_bill.raw_llm_response = result.get('raw_response', '')
        
        # Extract data
        data = result['data']
        
        # Update purchase bill with vendor and bill info
        vendor_info = data.get('vendor_info', {})
        bill_info = data.get('bill_info', {})
        
        purchase_bill.vendor_name = vendor_info.get('name')
        purchase_bill.vendor_address = vendor_info.get('address')
        purchase_bill.vendor_gst_number = vendor_info.get('gst_number')
        purchase_bill.vendor_phone = vendor_info.get('phone')
        purchase_bill.vendor_email = vendor_info.get('email')
        
        purchase_bill.invoice_number = bill_info.get('invoice_number')
        if bill_info.get('date'):
            try:
                purchase_bill.bill_date = datetime.datetime.strptime(bill_info['date'], '%Y-%m-%d').date()
            except:
                pass
        purchase_bill.total_amount = bill_info.get('total_amount')
        purchase_bill.tax_amount = bill_info.get('tax_amount')
        purchase_bill.discount_amount = bill_info.get('discount')
        
        # Process items
        items = data.get('items', [])
        products_added = 0
        products_updated = 0
        
        for item_data in items:
            if not item_data.get('name'):
                continue
                
            # Create purchase bill item
            bill_item = PurchaseBillItem(
                purchase_bill_id=purchase_bill.purchase_bill_id,
                item_name=item_data.get('name'),
                quantity=item_data.get('quantity'),
                unit_price=item_data.get('unit_price'),
                total_price=item_data.get('total_price'),
                gst_rate=item_data.get('gst_rate'),
                hsn_code=item_data.get('hsn_code')
            )
            
            # Try to match with existing product using name, price, and HSN code
            item_name = item_data.get('name')
            item_price = item_data.get('unit_price')
            item_hsn = item_data.get('hsn_code')
            
            # Look for exact match on name first
            potential_products = Product.query.filter_by(
                shopkeeper_id=purchase_bill.shopkeeper_id,
                product_name=item_name
            ).all()
            
            exact_match = None
            
            # Check for exact match on name, price, and HSN code
            for product in potential_products:
                product_price = float(product.price) if product.price else 0
                product_hsn = product.hsn_code or ''
                
                price_match = (item_price is None or 
                             abs(product_price - float(item_price)) < 0.01 if item_price else True)
                hsn_match = (item_hsn is None or 
                           product_hsn == (item_hsn or ''))
                
                if price_match and hsn_match:
                    exact_match = product
                    break
            
            if exact_match:
                # Found exact match - only update quantity
                if item_data.get('quantity'):
                    exact_match.stock_qty = (exact_match.stock_qty or 0) + int(item_data['quantity'])
                
                bill_item.matched_product_id = exact_match.product_id
                bill_item.is_new_product = False
                products_updated += 1
                
            else:
                # Create new product
                new_product = Product(
                    shopkeeper_id=purchase_bill.shopkeeper_id,
                    product_name=item_data.get('name'),
                    price=item_data.get('unit_price') or 0,
                    stock_qty=int(item_data.get('quantity', 0)),
                    gst_rate=item_data.get('gst_rate'),
                    hsn_code=item_data.get('hsn_code'),
                    low_stock_threshold=5  # Default threshold
                )
                db.session.add(new_product)
                db.session.flush()  # Get product ID
                
                bill_item.matched_product_id = new_product.product_id
                bill_item.is_new_product = True
                products_added += 1
            
            db.session.add(bill_item)
        
        purchase_bill.processing_status = 'completed'
        db.session.commit()
        
        current_app.logger.info(f"Purchase bill processed: {products_added} new products, {products_updated} updated")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error processing bill with AI: {str(e)}")
        purchase_bill.processing_status = 'failed'
        purchase_bill.error_message = str(e)
        db.session.rollback()
        return False