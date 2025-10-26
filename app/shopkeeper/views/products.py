"""
Product management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
import os
import uuid
from datetime import datetime
from flask import render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from werkzeug.utils import secure_filename

from ..utils import shopkeeper_required, get_current_shopkeeper
from app.models import Product, Shopkeeper, PurchaseBill, PurchaseBillItem
from app.extensions import db
from ..services.gemini_service import get_gemini_service


def register_routes(bp):
    """Register product management routes to the blueprint."""
 

    # Products & Stock (already implemented above)
    @bp.route('/products', methods=['GET'])
    @login_required
    @shopkeeper_required
    def products_stock():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
        return render_template('shopkeeper/products_stock.html', products=products)

    @bp.route('/products/add', methods=['POST'])
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

    @bp.route('/products/edit/<int:product_id>', methods=['POST'])
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

    @bp.route('/products/delete/<int:product_id>', methods=['POST'])
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

    @bp.route('/scan-purchase-bill', methods=['POST'])
    @login_required
    @shopkeeper_required
    def scan_purchase_bill():
        """Handle purchase bill scanning via file upload or camera."""
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
            current_app.logger.error(f"Error in scan_purchase_bill: {str(e)}")
            return jsonify({'success': False, 'message': f'Error processing bill: {str(e)}'})

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
                from flask import send_file
                return send_file(file_path)
            else:
                return jsonify({'error': 'File not found on disk'}), 404
        except Exception as e:
            current_app.logger.error(f"Error serving purchase bill file: {str(e)}")
            return jsonify({'error': 'Error accessing file'}), 500
        
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
            
            # Delete associated bill items first
            PurchaseBillItem.query.filter_by(purchase_bill_id=bill_id).delete()
            
            # Delete the bill file if it exists
            if purchase_bill.file_path and os.path.exists(purchase_bill.file_path):
                try:
                    os.remove(purchase_bill.file_path)
                except Exception as e:
                    current_app.logger.warning(f"Could not delete file {purchase_bill.file_path}: {str(e)}")
            
            # Delete the purchase bill
            db.session.delete(purchase_bill)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Purchase bill deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting purchase bill: {str(e)}")
            return jsonify({'success': False, 'message': 'Failed to delete purchase bill'}), 500


def _process_bill_with_ai(purchase_bill, file_path, file_ext):
    """Process the uploaded bill with Gemini AI."""
    try:
        # Import here to avoid circular imports
        
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
                purchase_bill.bill_date = datetime.strptime(bill_info['date'], '%Y-%m-%d').date()
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

    
