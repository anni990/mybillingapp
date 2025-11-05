"""
Bill management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import (render_template, request, flash, redirect, url_for, 
                   send_file, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from sqlalchemy import or_, desc
import datetime
import io
import os
from decimal import Decimal

from ..utils import shopkeeper_required, get_current_shopkeeper
from app.models import (Bill, BillItem, Product, Customer, CustomerLedger, 
                       Shopkeeper, CharteredAccountant, CAConnection, EmployeeClient, 
                       PurchaseBill, PurchaseBillItem)
from app.extensions import db
from app.utils.gst import calc_line, generate_gst_summary, calculate_bill_totals
from .profile import generate_next_invoice_number, is_custom_numbering_enabled
from ..services.ledger_service import CustomerLedgerService
import datetime
import io


def register_routes(bp):
    """Register bill management routes to the blueprint."""
    

    # Create Bill
    @bp.route('/create_bill', methods=['GET', 'POST'])
    @login_required
    @shopkeeper_required
    def create_bill():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name=shopkeeper.shop_name
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
                'gst_rate': float(p.gst_rate or 0),
                'hsn_code': p.hsn_code or ''
            } for p in products
        ]
        if request.method == 'POST':
            try:
                # Extract form data with new fields
                customer_name = request.form.get('customer_name')
                customer_contact = request.form.get('customer_contact')
                customer_address = request.form.get('customer_address', '')
                customer_gstin = request.form.get('customer_gstin', '')
                
                # Bill configuration
                gst_type = request.form.get('bill_gst_type', 'GST')  # Updated field name
                gst_mode = request.form.get('gst_mode', 'EXCLUSIVE').upper()  # New field
                date_with_time = request.form.get('date_with_time') == '1'  # Get date/time toggle
                payment_status = request.form.get('payment_status', 'Paid')
                paid_amount = Decimal(request.form.get('paid_amount', '0') or '0')
                
                # Product items - Updated to handle new fields
                product_ids = request.form.getlist('product_id')
                product_names = request.form.getlist('product_name')
                quantities = request.form.getlist('quantity')
                prices = request.form.getlist('price_per_unit')
                discounts = request.form.getlist('discount')  # New field
                gst_rates = request.form.getlist('gst_rate')  # New field
                hsn_codes = request.form.getlist('hsn_code')  # New field

                if not product_names or not quantities:
                    flash('Please add at least one product to create a bill.', 'error')
                    return redirect(url_for('shopkeeper.create_bill'))

                # Generate invoice number - use custom format if enabled, otherwise use timestamp
                if is_custom_numbering_enabled(shopkeeper):
                    invoice_number = generate_next_invoice_number(shopkeeper)
                else:
                    invoice_number = f"BILL{int(datetime.datetime.now().timestamp())}"
                
                # Create bill with new fields
                bill = Bill(
                    shopkeeper_id=shopkeeper.shopkeeper_id,
                    bill_number=invoice_number,
                    customer_name=customer_name,
                    customer_contact=customer_contact,
                    customer_address=customer_address,
                    customer_gstin=customer_gstin,
                    bill_date=datetime.datetime.now(),
                    gst_type=gst_type,
                    gst_mode=gst_mode,  # New field
                    payment_status=payment_status,
                    paid_amount=paid_amount,
                    total_amount=Decimal('0')  # Will be updated after calculating items
                )
                
                db.session.add(bill)
                db.session.flush()  # Get bill_id
                
                # Process bill items with GST calculations
                from app.utils.gst import calc_line
                calculated_items = []
                total_amount = Decimal('0')
                
                for i in range(len(product_names)):
                    if not product_names[i].strip():
                        continue
                        
                    # Get product data
                    product_id = product_ids[i] if i < len(product_ids) and product_ids[i] else None
                    quantity = int(quantities[i])
                    unit_price = Decimal(prices[i])
                    discount_percent = Decimal(discounts[i] if i < len(discounts) and discounts[i] else '0')
                    gst_rate = Decimal(gst_rates[i] if i < len(gst_rates) and gst_rates[i] else '0')
                    hsn_code = hsn_codes[i] if i < len(hsn_codes) else ''
                    
                    # Calculate GST using utility function
                    calc_result = calc_line(
                        price=unit_price,
                        qty=quantity,
                        gst_rate=gst_rate,
                        discount_percent=discount_percent,
                        mode=gst_mode
                    )
                    
                    # Create bill item with all calculated fields
                    bill_item = BillItem(
                        bill_id=bill.bill_id,
                        product_id=product_id,
                        custom_product_name=product_names[i] if not product_id else None,
                        custom_gst_rate=gst_rate if not product_id else None,
                        custom_hsn_code=hsn_code if not product_id else None,
                        quantity=quantity,
                        price_per_unit=unit_price,
                        discount_percent=discount_percent,
                        discount_amount=calc_result['discount_amount'],
                        taxable_amount=calc_result['taxable_amount'],
                        cgst_rate=calc_result['cgst_rate'],
                        sgst_rate=calc_result['sgst_rate'],
                        cgst_amount=calc_result['cgst_amount'],
                        sgst_amount=calc_result['sgst_amount'],
                        total_gst_amount=calc_result['total_gst'],
                        total_price=calc_result['final_total']
                    )
                    
                    db.session.add(bill_item)
                    calculated_items.append(calc_result)
                    total_amount += calc_result['final_total']
                    
                    # Update product stock if it's an existing product
                    if product_id:
                        product = Product.query.get(product_id)
                        if product and product.stock_qty >= quantity:
                            product.stock_qty = product.stock_qty - quantity
                
                # Update bill total and due amount
                bill.total_amount = total_amount
                bill.due_amount = total_amount - paid_amount
                
                # Create customer ledger entries for existing customers
                if bill.customer_id:  # Customer is linked to bill
                    try:
                        CustomerLedgerService.create_ledger_entries_for_bill(bill, shopkeeper)
                        current_app.logger.debug(f"Created ledger entries for customer {bill.customer_id} on bill {bill.bill_number}")
                    except Exception as e:
                        current_app.logger.error(f"Failed to create ledger entries: {str(e)}")
                        # Don't fail bill creation if ledger fails
                        flash('Bill created but ledger entry failed. Please check customer balance manually.', 'warning')
                
                db.session.commit()
                
                flash(f'Bill {invoice_number} created successfully!', 'success')
                return redirect(url_for('shopkeeper.view_bill', bill_id=bill.bill_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating bill: {str(e)}', 'error')
                return redirect(url_for('shopkeeper.create_bill'))
        return render_template(
            'shopkeeper/create_bill.html',
            shop_name=shop_name,
            products=products,
            products_js=products_js,
            shopkeeper=shopkeeper,
            now=datetime.datetime.now()  # Pass current datetime as 'now'
        )

    # Manage Bills
    @bp.route('/manage_bills')
    @login_required
    @shopkeeper_required
    def manage_bills():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name=shopkeeper.shop_name
        # In all relevant routes, comment out the is_verified restriction logic
        # Example for create_bill:
        #    if not shopkeeper.is_verified:
        #        flash('Please upload all required documents to use this service.', 'danger')
        #        return redirect(url_for('shopkeeper.profile'))
        search = request.args.get('search', '').strip()
        selected_statuses = request.args.getlist('status')
        
        # Sales Bills Query
        query = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
        if search:
            query = query.filter(
                (Bill.bill_number.ilike(f'%{search}%')) |
                (Bill.customer_name.ilike(f'%{search}%'))
            )
        if selected_statuses:
            query = query.filter(Bill.payment_status.in_(selected_statuses))
        bills = query.order_by(Bill.bill_date.desc()).all() if shopkeeper else []
        
        # Purchase Bills Query
        purchase_query = PurchaseBill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
        if search:
            purchase_query = purchase_query.filter(
                (PurchaseBill.vendor_name.ilike(f'%{search}%')) |
                (PurchaseBill.bill_number.ilike(f'%{search}%'))
            )
        purchase_bills = purchase_query.order_by(PurchaseBill.bill_date.desc()).all() if shopkeeper else []
        
        return render_template('shopkeeper/manage_bills.html', 
                             shop_name=shop_name,
                             bills=bills, 
                             purchase_bills=purchase_bills,
                             selected_statuses=selected_statuses)

        
    @bp.route('/bill/<int:bill_id>')
    @login_required
    @shopkeeper_required
    def view_bill(bill_id):
        bill = Bill.query.get_or_404(bill_id)
        if bill.shopkeeper.user_id != current_user.user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('shopkeeper.manage_bills'))
        
        shopkeeper = bill.shopkeeper
        
        # Access control: Check if current user can access this bill
        if current_user.role == 'CA':
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            if not ca:
                flash('Access denied: CA profile not found.', 'danger')
                return redirect(url_for('ca.bills_panel'))
            
            # Check if the bill's shopkeeper is connected to this CA
            ca_connection = CAConnection.query.filter_by(
                shopkeeper_id=bill.shopkeeper_id,
                ca_id=ca.ca_id,
                status='approved'
            ).first()
            
            if not ca_connection:
                flash('Access denied: You can only view bills from connected shopkeepers.', 'danger')
                return redirect(url_for('ca.bills_panel'))
                
        elif current_user.role == 'employee':
            employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
            if not employee:
                flash('Access denied: Employee profile not found.', 'danger')
                return redirect(url_for('ca.bills_panel'))
            
            # Check if the bill's shopkeeper is assigned to this employee
            employee_client = EmployeeClient.query.filter_by(
                shopkeeper_id=bill.shopkeeper_id,
                employee_id=employee.employee_id
            ).first()
            
            if not employee_client:
                flash('Access denied: You can only view bills from assigned shopkeepers.', 'danger')
                return redirect(url_for('ca.bills_panel'))
                
        elif current_user.role == 'shopkeeper':
            # Shopkeepers can only view their own bills
            if bill.shopkeeper.user_id != current_user.user_id:
                flash('Access denied: You can only view your own bills.', 'danger')
                return redirect(url_for('shopkeeper.manage_bills'))
        else:
            flash('Access denied: Invalid role.', 'danger')
            return redirect(url_for('auth.login'))
        
        bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
        products_dict = {str(p.product_id): p for p in products}
        
        # Check if user can edit
        is_editable = False
        if current_user.role == 'shopkeeper' and bill.shopkeeper.user_id == current_user.user_id:
            is_editable = True
        elif current_user.role == 'CA':
            ca_conn = CAConnection.query.filter_by(shopkeeper_id=bill.shopkeeper_id, ca_id=current_user.ca.ca_id, status='approved').first()
            is_editable = bool(ca_conn)
        elif current_user.role == 'employee':
            emp_client = EmployeeClient.query.filter_by(shopkeeper_id=bill.shopkeeper_id, employee_id=current_user.ca_employee.employee_id).first()
            is_editable = bool(emp_client)
        
        # Calculate GST summary using stored data or calculation engine
        bill_items_data = []
        calculated_items = []
        
        # Determine GST mode (default to EXCLUSIVE for backward compatibility)
        gst_mode = getattr(bill, 'gst_mode', 'EXCLUSIVE') or 'EXCLUSIVE'

        for item in bill_items:
            # Handle both existing products and custom products
            if item.product_id:  # Existing product
                product = products_dict.get(str(item.product_id))
                if not product:
                    continue  # Skip if product not found
                
                gst_rate = float(product.gst_rate or 0)
                hsn_code = getattr(product, 'hsn_code', '') or ''
                product_name = product.product_name
                is_custom = False
            else:  # Custom product
                gst_rate = float(item.custom_gst_rate or 0)
                hsn_code = item.custom_hsn_code or ''
                product_name = item.custom_product_name
                is_custom = True
                
                # Create a mock product object for template compatibility
                product = type('Product', (), {
                    'product_name': product_name,
                    'gst_rate': gst_rate,
                    'hsn_code': hsn_code,
                    'product_id': f'custom_{item.bill_item_id}'
                })()
            
            base_price = float(item.price_per_unit)
            quantity = int(item.quantity)
            
            # Check if we have stored discount and GST data (new bills) or need to calculate (old bills)
            if hasattr(item, 'discount_percent') and item.discount_percent is not None:
                # Use stored calculations from new bills
                discount_percent = float(item.discount_percent or 0)
                discount_amount = float(item.discount_amount or 0)
                taxable_amount = float(item.taxable_amount or 0)
                cgst_amount = float(item.cgst_amount or 0)
                sgst_amount = float(item.sgst_amount or 0)
                total_gst = float(item.total_gst_amount or 0)
                final_total = float(item.total_price)
                
                # Prepare item data using stored values
                item_data = {
                    'product': product,
                    'is_custom': is_custom,
                    'quantity': quantity,
                    'unit_price': base_price,
                    'discount_percent': discount_percent,
                    'discount_amount': discount_amount,
                    'taxable_amount': taxable_amount,
                    'gst_rate': gst_rate,
                    'cgst_rate': gst_rate / 2,
                    'sgst_rate': gst_rate / 2,
                    'cgst_amount': cgst_amount,
                    'sgst_amount': sgst_amount,
                    'total_gst': total_gst,
                    'final_total': final_total,
                    'mode': gst_mode,
                    'hsn_code': hsn_code
                }
                
                # Create gst_calc for summary generation
                gst_calc = {
                    'taxable_amount': taxable_amount,
                    'cgst_amount': cgst_amount,
                    'sgst_amount': sgst_amount,
                    'total_gst': total_gst,
                    'final_total': final_total,
                    'gst_rate': gst_rate
                }
                
                bill_items_data.append(item_data)
                calculated_items.append(gst_calc)
                
            else:
                # Calculate for old bills (backward compatibility)
                discount_percent = 0  # Old bills don't have discount data
                
                try:
                    from app.utils.gst import calc_line
                    gst_calc = calc_line(
                        price=base_price,
                        qty=quantity,
                        gst_rate=gst_rate,
                        discount_percent=discount_percent,
                        mode=gst_mode
                    )
                    
                    # Prepare item data for template with all GST details
                    item_data = {
                        'product': product,
                        'is_custom': is_custom,
                        'quantity': quantity,
                        'unit_price': base_price,
                        'unit_price_base': float(gst_calc['unit_price_base']),
                        'line_base_total': float(gst_calc['line_base_total']),
                        'discount_percent': discount_percent,
                        'discount_amount': float(gst_calc['discount_amount']),
                        'taxable_amount': float(gst_calc['taxable_amount']),
                        'gst_rate': float(gst_calc['gst_rate']),
                        'cgst_rate': float(gst_calc['cgst_rate']),
                        'sgst_rate': float(gst_calc['sgst_rate']),
                        'cgst_amount': float(gst_calc['cgst_amount']),
                        'sgst_amount': float(gst_calc['sgst_amount']),
                        'total_gst': float(gst_calc['total_gst']),
                        'final_total': float(gst_calc['final_total']),
                        'mode': gst_calc['mode'],
                        'hsn_code': hsn_code
                    }
                    
                    bill_items_data.append(item_data)
                    calculated_items.append(gst_calc)
                    
                except Exception as e:
                    current_app.logger.error(f"Error calculating GST for bill item {item.bill_item_id}: {str(e)}")
                    # Fallback to simple display
                    item_data = {
                        'product': product,
                        'is_custom': is_custom,
                        'quantity': quantity,
                        'unit_price': base_price,
                        'line_base_total': base_price * quantity,
                        'discount_percent': 0,
                        'discount_amount': 0,
                        'taxable_amount': base_price * quantity,
                        'gst_rate': gst_rate,
                        'cgst_rate': gst_rate / 2,
                        'sgst_rate': gst_rate / 2,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'total_gst': 0,
                        'final_total': float(item.total_price),
                        'mode': gst_mode,
                        'hsn_code': hsn_code
                    }
                    bill_items_data.append(item_data)
        
        # Generate GST summary and totals using new engine
        if calculated_items:
            from app.utils.gst import generate_gst_summary, calculate_bill_totals
            gst_summary = generate_gst_summary(calculated_items)
            bill_totals = calculate_bill_totals(calculated_items)
            
            # Convert summary for template (maintain backward compatibility)
            gst_summary_by_rate = {}
            for rate_str, summary_data in gst_summary.items():
                gst_summary_by_rate[rate_str] = {
                    'taxable_amount': float(summary_data['taxable_amount']),
                    'cgst_amount': float(summary_data['cgst_amount']),
                    'sgst_amount': float(summary_data['sgst_amount']),
                    'total_gst_amount': float(summary_data['total_gst']),
                    'final_total': float(summary_data['final_total'])
                }
            
            # Set totals
            overall_grand_total = float(bill_totals['grand_total'])
            total_taxable_amount = float(bill_totals['total_taxable_amount'])
            total_cgst_amount = float(bill_totals['total_cgst_amount'])
            total_sgst_amount = float(bill_totals['total_sgst_amount'])
            total_gst_amount = float(bill_totals['total_gst_amount'])
        else:
            # No items or calculation failed
            gst_summary_by_rate = {}
            overall_grand_total = float(bill.total_amount or 0)
            total_taxable_amount = 0
            total_cgst_amount = 0
            total_sgst_amount = 0
            total_gst_amount = 0

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

    @bp.route('/bill/<int:bill_id>/edit')
    @login_required
    @shopkeeper_required
    def edit_bill(bill_id):
        """Edit bill page - separate UI for editing."""
        bill = Bill.query.get_or_404(bill_id)
        if bill.shopkeeper.user_id != current_user.user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('shopkeeper.manage_bills'))
        
        bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
        shopkeeper = bill.shopkeeper
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
        products_dict = {str(p.product_id): p for p in products}
        
        # Calculate GST summary using new engine
        bill_items_data = []
        calculated_items = []
        
        # Determine GST mode (default to EXCLUSIVE for backward compatibility)
        gst_mode = getattr(bill, 'gst_mode', 'EXCLUSIVE') or 'EXCLUSIVE'

        for item in bill_items:
            # Handle both existing products and custom products
            if item.product_id:  # Existing product
                product = products_dict.get(str(item.product_id))
                if not product:
                    continue  # Skip if product not found
                
                gst_rate = float(product.gst_rate or 0)
                hsn_code = getattr(product, 'hsn_code', '') or ''
                product_name = product.product_name
                is_custom = False
            else:  # Custom product
                gst_rate = float(item.custom_gst_rate or 0)
                hsn_code = item.custom_hsn_code or ''
                product_name = item.custom_product_name
                is_custom = True
                
                # Create a mock product object for template compatibility
                product = type('Product', (), {
                    'product_name': product_name,
                    'gst_rate': gst_rate,
                    'hsn_code': hsn_code,
                    'product_id': f'custom_{item.bill_item_id}'
                })()
            
            base_price = float(item.price_per_unit)
            quantity = int(item.quantity)
            
            # Check if we have stored discount data (new bills) or use default (old bills)
            discount_percent = float(item.discount_percent or 0) if hasattr(item, 'discount_percent') and item.discount_percent is not None else 0
            
            # Check if we have stored GST data (new bills) or need to calculate (old bills)
            if hasattr(item, 'discount_percent') and item.discount_percent is not None and hasattr(item, 'taxable_amount') and item.taxable_amount is not None:
                # Use stored calculations from new bills
                discount_amount = float(item.discount_amount or 0)
                taxable_amount = float(item.taxable_amount or 0)
                cgst_amount = float(item.cgst_amount or 0)
                sgst_amount = float(item.sgst_amount or 0)
                total_gst = float(item.total_gst_amount or 0)
                final_total = float(item.total_price)
                
                # Prepare item data using stored values - handle Non-GST bills
                if getattr(bill, 'gst_type', 'GST') == 'Non-GST':
                    item_data = {
                        'product': product,
                        'is_custom': is_custom,
                        'quantity': quantity,
                        'unit_price': base_price,
                        'discount_percent': discount_percent,
                        'discount_amount': discount_amount,
                        'taxable_amount': taxable_amount,
                        'gst_rate': 0,
                        'cgst_rate': 0,
                        'sgst_rate': 0,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'total_gst': 0,
                        'final_total': final_total,
                        'mode': 'Non-GST',
                        'hsn_code': hsn_code
                    }
                else:
                    item_data = {
                        'product': product,
                        'is_custom': is_custom,
                        'quantity': quantity,
                        'unit_price': base_price,
                        'discount_percent': discount_percent,
                        'discount_amount': discount_amount,
                        'taxable_amount': taxable_amount,
                        'gst_rate': gst_rate,
                        'cgst_rate': gst_rate / 2,
                        'sgst_rate': gst_rate / 2,
                        'cgst_amount': cgst_amount,
                        'sgst_amount': sgst_amount,
                        'total_gst': total_gst,
                        'final_total': final_total,
                        'mode': gst_mode,
                        'hsn_code': hsn_code
                    }
                
                # Create gst_calc for summary generation - handle Non-GST bills
                if getattr(bill, 'gst_type', 'GST') == 'Non-GST':
                    gst_calc = {
                        'taxable_amount': taxable_amount,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'total_gst': 0,
                        'final_total': final_total,
                        'gst_rate': 0
                    }
                else:
                    gst_calc = {
                        'taxable_amount': taxable_amount,
                        'cgst_amount': cgst_amount,
                        'sgst_amount': sgst_amount,
                        'total_gst': total_gst,
                        'final_total': final_total,
                        'gst_rate': gst_rate
                    }
                
                bill_items_data.append(item_data)
                calculated_items.append(gst_calc)
                
            else:
                # Calculate for old bills - check if Non-GST bill
                try:
                    if getattr(bill, 'gst_type', 'GST') == 'Non-GST':
                        # Non-GST calculation: No GST, only quantity × price with discount
                        line_total = base_price * quantity
                        discount_amount = (line_total * discount_percent) / 100
                        final_amount = line_total - discount_amount
                        
                        # Create Non-GST calculation result
                        gst_calc = {
                            'unit_price_base': base_price,
                            'line_base_total': line_total,
                            'discount_amount': discount_amount,
                            'taxable_amount': final_amount,
                            'gst_rate': 0,
                            'cgst_rate': 0,
                            'sgst_rate': 0,
                            'cgst_amount': 0,
                            'sgst_amount': 0,
                            'total_gst': 0,
                            'final_total': final_amount,
                            'mode': 'Non-GST'
                        }
                    else:
                        # Use GST calculation engine for GST bills
                        gst_calc = calc_line(
                            price=base_price,
                            qty=quantity,
                            gst_rate=gst_rate,
                            discount_percent=discount_percent,
                            mode=gst_mode
                        )
                    
                    # Prepare item data for template with all GST details
                    item_data = {
                        'product': product,
                        'is_custom': is_custom,
                        'quantity': quantity,
                        'unit_price': base_price,
                        'unit_price_base': float(gst_calc['unit_price_base']),
                        'line_base_total': float(gst_calc['line_base_total']),
                        'discount_percent': discount_percent,
                        'discount_amount': float(gst_calc['discount_amount']),
                        'taxable_amount': float(gst_calc['taxable_amount']),
                        'gst_rate': float(gst_calc['gst_rate']),
                        'cgst_rate': float(gst_calc['cgst_rate']),
                        'sgst_rate': float(gst_calc['sgst_rate']),
                        'cgst_amount': float(gst_calc['cgst_amount']),
                        'sgst_amount': float(gst_calc['sgst_amount']),
                        'total_gst': float(gst_calc['total_gst']),
                        'final_total': float(gst_calc['final_total']),
                        'mode': gst_calc['mode'],
                        'hsn_code': hsn_code
                    }
                    
                    bill_items_data.append(item_data)
                    calculated_items.append(gst_calc)
                
                except Exception as e:
                    current_app.logger.error(f"Error calculating GST for bill item {item.bill_item_id}: {str(e)}")
                # Fallback to simple display
                item_data = {
                    'product': product,
                    'is_custom': is_custom,
                    'quantity': quantity,
                    'unit_price': base_price,
                    'line_base_total': base_price * quantity,
                    'discount_percent': 0,
                    'discount_amount': 0,
                    'taxable_amount': base_price * quantity,
                    'gst_rate': gst_rate,
                    'cgst_rate': gst_rate / 2,
                    'sgst_rate': gst_rate / 2,
                    'cgst_amount': 0,
                    'sgst_amount': 0,
                    'total_gst': 0,
                    'final_total': float(item.total_price),
                    'mode': gst_mode,
                    'hsn_code': hsn_code
                }
                bill_items_data.append(item_data)
        
        # Generate GST summary and totals using new engine
        if calculated_items:
            gst_summary = generate_gst_summary(calculated_items)
            bill_totals = calculate_bill_totals(calculated_items)
            
            # Convert summary for template (maintain backward compatibility)
            gst_summary_by_rate = {}
            for rate_str, summary_data in gst_summary.items():
                rate_float = float(rate_str)
                gst_summary_by_rate[rate_float] = {
                    'taxable_amount': float(summary_data['taxable_amount']),
                    'cgst_amount': float(summary_data['cgst_amount']),
                    'sgst_amount': float(summary_data['sgst_amount']),
                    'total_gst_amount': float(summary_data['total_gst'])
                }
            
            # Set totals
            overall_grand_total = float(bill_totals['grand_total'])
            total_taxable_amount = float(bill_totals['total_taxable_amount'])
            total_cgst_amount = float(bill_totals['total_cgst_amount'])
            total_sgst_amount = float(bill_totals['total_sgst_amount'])
            total_gst_amount = float(bill_totals['total_gst_amount'])
        else:
            # No items or calculation failed
            gst_summary_by_rate = {}
            overall_grand_total = float(bill.total_amount or 0)
            total_taxable_amount = 0
            total_cgst_amount = 0
            total_sgst_amount = 0
            total_gst_amount = 0

        return render_template('shopkeeper/edit_bill.html',
            bill=bill,
            bill_items_data=bill_items_data,
            shopkeeper=shopkeeper,
            products=products_dict,
            gst_summary_by_rate=gst_summary_by_rate,
            total_taxable_amount=total_taxable_amount,
            total_cgst_amount=total_cgst_amount,
            total_sgst_amount=total_sgst_amount,
            total_gst_amount=total_gst_amount,
            overall_grand_total=overall_grand_total)

    @bp.route('/bill/download/<int:bill_id>')
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
        
        # Calculate GST summary using new engine
        bill_items_data = []
        calculated_items = []
        
        # Determine GST mode (default to EXCLUSIVE for backward compatibility)
        gst_mode = getattr(bill, 'gst_mode', 'EXCLUSIVE') or 'EXCLUSIVE'

        for item in bill_items:
            # Handle both existing products and custom products
            if item.product_id:  # Existing product
                product = products_dict.get(str(item.product_id))
                if not product:
                    continue  # Skip if product not found
                
                gst_rate = float(product.gst_rate or 0)
                hsn_code = getattr(product, 'hsn_code', '') or ''
                product_name = product.product_name
                is_custom = False
            else:  # Custom product
                gst_rate = float(item.custom_gst_rate or 0)
                hsn_code = item.custom_hsn_code or ''
                product_name = item.custom_product_name
                is_custom = True
                
                # Create a mock product object for template compatibility
                product = type('Product', (), {
                    'product_name': product_name,
                    'gst_rate': gst_rate,
                    'hsn_code': hsn_code,
                    'product_id': f'custom_{item.bill_item_id}'
                })()
            
            base_price = float(item.price_per_unit)
            quantity = int(item.quantity)
            
            # For existing bills, assume discount = 0 unless stored elsewhere
            discount_percent = 0
            
            # Check if this is a Non-GST bill
            try:
                if getattr(bill, 'gst_type', 'GST') == 'Non-GST':
                    # Non-GST calculation: No GST, only quantity × price with discount
                    line_total = base_price * quantity
                    discount_amount = (line_total * discount_percent) / 100
                    final_amount = line_total - discount_amount
                    
                    # Create Non-GST calculation result
                    gst_calc = {
                        'unit_price_base': base_price,
                        'line_base_total': line_total,
                        'discount_amount': discount_amount,
                        'taxable_amount': final_amount,
                        'gst_rate': 0,
                        'cgst_rate': 0,
                        'sgst_rate': 0,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'total_gst': 0,
                        'final_total': final_amount,
                        'mode': 'Non-GST'
                    }
                else:
                    # Use GST calculation engine for GST bills
                    gst_calc = calc_line(
                        price=base_price,
                        qty=quantity,
                        gst_rate=gst_rate,
                        discount_percent=discount_percent,
                        mode=gst_mode
                    )
                
                # Prepare item data for template with all GST details
                item_data = {
                    'product': product,
                    'is_custom': is_custom,
                    'quantity': quantity,
                    'unit_price': base_price,
                    'unit_price_base': float(gst_calc['unit_price_base']),
                    'line_base_total': float(gst_calc['line_base_total']),
                    'discount_percent': discount_percent,
                    'discount_amount': float(gst_calc['discount_amount']),
                    'taxable_amount': float(gst_calc['taxable_amount']),
                    'gst_rate': float(gst_calc['gst_rate']),
                    'cgst_rate': float(gst_calc['cgst_rate']),
                    'sgst_rate': float(gst_calc['sgst_rate']),
                    'cgst_amount': float(gst_calc['cgst_amount']),
                    'sgst_amount': float(gst_calc['sgst_amount']),
                    'total_gst': float(gst_calc['total_gst']),
                    'final_total': float(gst_calc['final_total']),
                    'mode': gst_calc['mode'],
                    'hsn_code': hsn_code
                }
                
                bill_items_data.append(item_data)
                calculated_items.append(gst_calc)
                
            except Exception as e:
                current_app.logger.error(f"Error calculating GST for bill item {item.bill_item_id}: {str(e)}")
                # Fallback to simple display
                item_data = {
                    'product': product,
                    'is_custom': is_custom,
                    'quantity': quantity,
                    'unit_price': base_price,
                    'line_base_total': base_price * quantity,
                    'discount_percent': 0,
                    'discount_amount': 0,
                    'taxable_amount': base_price * quantity,
                    'gst_rate': gst_rate,
                    'cgst_rate': gst_rate / 2,
                    'sgst_rate': gst_rate / 2,
                    'cgst_amount': 0,
                    'sgst_amount': 0,
                    'total_gst': 0,
                    'final_total': float(item.total_price),
                    'mode': gst_mode,
                    'hsn_code': hsn_code
                }
                bill_items_data.append(item_data)
        
        # Generate GST summary and totals using new engine
        if calculated_items:
            gst_summary = generate_gst_summary(calculated_items)
            bill_totals = calculate_bill_totals(calculated_items)
            
            # Convert summary for template (maintain backward compatibility)
            gst_summary_by_rate = {}
            for rate_str, summary_data in gst_summary.items():
                rate_float = float(rate_str)
                gst_summary_by_rate[rate_float] = {
                    'taxable_amount': float(summary_data['taxable_amount']),
                    'cgst_amount': float(summary_data['cgst_amount']),
                    'sgst_amount': float(summary_data['sgst_amount']),
                    'total_gst_amount': float(summary_data['total_gst'])
                }
            
            # Set totals
            overall_grand_total = float(bill_totals['grand_total'])
            total_taxable_amount = float(bill_totals['total_taxable_amount'])
            total_cgst_amount = float(bill_totals['total_cgst_amount'])
            total_sgst_amount = float(bill_totals['total_sgst_amount'])
            total_gst_amount = float(bill_totals['total_gst_amount'])
        else:
            # No items or calculation failed
            gst_summary_by_rate = {}
            overall_grand_total = float(bill.total_amount or 0)
            total_taxable_amount = 0
            total_cgst_amount = 0
            total_sgst_amount = 0
            total_gst_amount = 0

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

    @bp.route('/bill/<int:bill_id>/edit', methods=['POST'])
    @login_required
    def update_bill(bill_id):
        """Updated method to handle comprehensive edit bill form data"""
        try:
            bill = Bill.query.get_or_404(bill_id)
            
            # Check permissions - only shopkeepers can edit bills
            if current_user.role != 'shopkeeper' or bill.shopkeeper.user_id != current_user.user_id:
                flash('Access denied. Only shopkeepers can edit bills.', 'danger')
                return redirect(url_for('shopkeeper.manage_bills'))

            # Get form data from the new comprehensive edit bill form
            customer_name = request.form.get('customer_name', '').strip()
            customer_contact = request.form.get('customer_contact', '').strip()
            customer_address = request.form.get('customer_address', '').strip()
            customer_gstin = request.form.get('customer_gstin', '').strip()
            payment_status = request.form.get('payment_status', 'Paid')
            paid_amount = float(request.form.get('paid_amount', 0) or 0)
            date_with_time = request.form.get('date_with_time') == '1'  # Get date/time toggle
            
            # Update basic bill information
            bill.customer_name = customer_name
            bill.customer_contact = customer_contact
            bill.customer_address = customer_address
            bill.customer_gstin = customer_gstin
            bill.payment_status = payment_status
            bill.paid_amount = paid_amount
            bill.date_with_time = date_with_time  # Update date/time display toggle

            # Get bill items data from dynamic form arrays
            product_ids = request.form.getlist('product_id[]')
            product_names = request.form.getlist('product_name[]')  # For custom products
            quantities = request.form.getlist('quantity[]')
            unit_prices = request.form.getlist('unit_price[]')
            discounts = request.form.getlist('discount_percent[]')  # New discount field
            gst_rates_custom = request.form.getlist('gst_rate[]')  # Custom GST rates
            hsn_codes = request.form.getlist('hsn_code[]')  # HSN codes
            
            # Get GST mode and bill type
            gst_mode = request.form.get('gst_mode', getattr(bill, 'gst_mode', 'EXCLUSIVE')).upper()
            bill_gst_type = request.form.get('bill_gst_type', getattr(bill, 'gst_type', 'GST'))
            
            # Update bill GST settings
            bill.gst_mode = gst_mode
            bill.gst_type = bill_gst_type
            
            # Validate form data
            if not product_ids or len(product_ids) != len(quantities) or len(quantities) != len(unit_prices):
                flash('Invalid item data. Please check all fields.', 'error')
                return redirect(url_for('shopkeeper.edit_bill', bill_id=bill_id))

            # First, restore stock for all existing bill items
            existing_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
            for existing_item in existing_items:
                if existing_item.product_id:  # Only for real products, not custom ones
                    product = Product.query.get(existing_item.product_id)
                    if product:
                        product.stock_qty += existing_item.quantity  # Restore stock

            # Clear existing bill items
            BillItem.query.filter_by(bill_id=bill.bill_id).delete()

            # Process new/updated items and calculate totals using GST engine
            calculated_items = []
            
            for i in range(len(product_ids)):
                try:
                    product_id = product_ids[i] if i < len(product_ids) and product_ids[i] else None
                    product_name = product_names[i] if i < len(product_names) else ''
                    quantity = int(quantities[i])
                    unit_price = float(unit_prices[i])
                    discount_percent = float(discounts[i]) if i < len(discounts) and discounts[i] else 0
                    custom_gst_rate = float(gst_rates_custom[i]) if i < len(gst_rates_custom) and gst_rates_custom[i] else 0
                    hsn_code = hsn_codes[i] if i < len(hsn_codes) else ''
                    
                    if quantity <= 0 or unit_price < 0:
                        continue
                    
                    # Check if this is an existing product or custom product
                    if product_id and product_id.strip():  # Existing product
                        product = Product.query.get(product_id)
                        if not product:
                            flash(f'Product not found for item {i+1}', 'warning')
                            continue
                            
                        # Check stock availability
                        if product.stock_qty < quantity:
                            flash(f'Insufficient stock for {product.product_name}. Available: {product.stock_qty}', 'warning')
                            # Allow the update but warn user
                        
                        # Update stock
                        product.stock_qty -= quantity
                        
                        # Use product GST rate
                        gst_rate = float(product.gst_rate or 0)
                        hsn_code = getattr(product, 'hsn_code', '') or hsn_code
                        is_custom_product = False
                        
                    else:  # Custom product
                        product = None
                        gst_rate = custom_gst_rate
                        is_custom_product = True
                        
                        # Skip if no product name for custom product
                        if not product_name.strip():
                            continue
                    
                    # Calculate using GST engine - check if Non-GST bill
                    if bill_gst_type == 'Non-GST':
                        # Non-GST calculation: No GST calculations needed
                        line_total = unit_price * quantity
                        discount_amount = (line_total * discount_percent) / 100
                        final_amount = line_total - discount_amount
                        
                        gst_calc = {
                            'unit_price_base': unit_price,
                            'line_base_total': line_total,
                            'discount_amount': discount_amount,
                            'taxable_amount': final_amount,
                            'gst_rate': 0,
                            'cgst_rate': 0,
                            'sgst_rate': 0,
                            'cgst_amount': 0,
                            'sgst_amount': 0,
                            'total_gst': 0,
                            'final_total': final_amount,
                            'mode': 'Non-GST'
                        }
                    else:
                        # GST calculation using GST engine
                        gst_calc = calc_line(
                            price=unit_price,
                            qty=quantity,
                            gst_rate=gst_rate,
                            discount_percent=discount_percent,
                            mode=gst_mode
                        )
                    
                    # Create new bill item with all calculated values
                    if is_custom_product:
                        bill_item = BillItem(
                            bill_id=bill.bill_id,
                            product_id=None,
                            custom_product_name=product_name.strip(),
                            custom_gst_rate=gst_rate,
                            custom_hsn_code=hsn_code,
                            quantity=quantity,
                            price_per_unit=unit_price,
                            discount_percent=discount_percent,
                            discount_amount=float(gst_calc['discount_amount']),
                            taxable_amount=float(gst_calc['taxable_amount']),
                            cgst_rate=float(gst_calc['cgst_rate']),
                            sgst_rate=float(gst_calc['sgst_rate']),
                            cgst_amount=float(gst_calc['cgst_amount']),
                            sgst_amount=float(gst_calc['sgst_amount']),
                            total_gst_amount=float(gst_calc['total_gst']),
                            total_price=float(gst_calc['final_total'])
                        )
                    else:
                        bill_item = BillItem(
                            bill_id=bill.bill_id,
                            product_id=product_id,
                            custom_product_name=None,
                            custom_gst_rate=None,
                            custom_hsn_code=None,
                            quantity=quantity,
                            price_per_unit=unit_price,
                            discount_percent=discount_percent,
                            discount_amount=float(gst_calc['discount_amount']),
                            taxable_amount=float(gst_calc['taxable_amount']),
                            cgst_rate=float(gst_calc['cgst_rate']),
                            sgst_rate=float(gst_calc['sgst_rate']),
                            cgst_amount=float(gst_calc['cgst_amount']),
                            sgst_amount=float(gst_calc['sgst_amount']),
                            total_gst_amount=float(gst_calc['total_gst']),
                            total_price=float(gst_calc['final_total'])
                        )
                    
                    db.session.add(bill_item)
                    calculated_items.append(gst_calc)
                        
                except (ValueError, TypeError) as e:
                    flash(f'Invalid data for item {i+1}: {str(e)}', 'error')
                    continue

            # Calculate bill totals using GST engine
            if calculated_items:
                bill_totals = calculate_bill_totals(calculated_items)
                bill.total_amount = float(bill_totals['grand_total'])
                
                # Update due amount
                bill.due_amount = bill.total_amount - bill.paid_amount
            else:
                bill.total_amount = 0
                bill.due_amount = 0
            
            # Update customer ledger entries if customer is linked
            if bill.customer_id:
                try:
                    shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
                    CustomerLedgerService.update_ledger_entries_for_bill(bill, shopkeeper)
                    current_app.logger.debug(f"Updated ledger entries for customer {bill.customer_id} on bill {bill.bill_number}")
                except Exception as e:
                    current_app.logger.error(f"Failed to update ledger entries: {str(e)}")
                    flash('Bill updated but ledger update failed. Please check customer balance manually.', 'warning')
            
            # Commit all changes
            db.session.commit()
            flash('Bill updated successfully!', 'success')
            return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating bill {bill_id}: {str(e)}")
            flash('Error updating bill. Please try again.', 'error')
            return redirect(url_for('shopkeeper.edit_bill', bill_id=bill_id))

    @bp.route('/bill/delete/<int:bill_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def delete_bill(bill_id):
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            bill = Bill.query.get_or_404(bill_id)
            
            # Check if the bill belongs to the current shopkeeper
            if bill.shopkeeper.user_id != current_user.user_id:
                return jsonify({'success': False, 'message': 'Access denied.'}), 403
            
            # Clean up customer ledger entries if customer is linked
            if bill.customer_id:
                try:
                    CustomerLedgerService.delete_ledger_entries_for_bill(bill_id, bill.customer_id)
                    current_app.logger.debug(f"Cleaned up ledger entries for deleted bill {bill.bill_number}")
                except Exception as e:
                    current_app.logger.error(f"Failed to clean up ledger entries: {str(e)}")
                    # Continue with deletion even if ledger cleanup fails
            
            # Delete the bill (BillItems will be deleted automatically due to cascade)
            db.session.delete(bill)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Bill deleted successfully.'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'Error deleting bill: {str(e)}'}), 500



    @bp.route('/generate_bill_pdf', methods=['POST'])
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
        
        gst_mode = request.form.get('gst_mode', 'EXCLUSIVE').upper()
        bill_gst_type = request.form.get('bill_gst_type', 'GST')
        date_with_time = request.form.get('date_with_time') == '1'  # Get date/time toggle
        items = request.form.getlist('product_id')
        product_names = request.form.getlist('product_name')  # Get custom product names
        quantities = request.form.getlist('quantity')
        prices = request.form.getlist('price_per_unit')
        discounts = request.form.getlist('discount')  # New discount field
        gst_rates_custom = request.form.getlist('gst_rate')  # Get custom GST rates
        hsn_codes = request.form.getlist('hsn_code')  # HSN codes
        
        # Debug: Log the form data to identify duplication source
        current_app.logger.debug(f"Form data lengths - items:{len(items)}, names:{len(product_names)}, qty:{len(quantities)}, prices:{len(prices)}")
        current_app.logger.debug(f"Items: {items}")
        current_app.logger.debug(f"Product names: {product_names}")
        current_app.logger.debug(f"Quantities: {quantities}")
        
        # Parse bill_date from form (datetime-local input)
        bill_date_str = request.form.get('bill_date')
        if bill_date_str:
            bill_date = datetime.datetime.strptime(bill_date_str, '%Y-%m-%dT%H:%M')
        else:
            bill_date = datetime.datetime.now()
        
        total_amount = 0
        # Generate invoice number - use custom format if enabled, otherwise use timestamp
        if is_custom_numbering_enabled(shopkeeper):
            bill_number = generate_next_invoice_number(shopkeeper)
        else:
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
                            gstin=customer_gstin.strip() if customer_gstin else '',
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
            gst_mode=gst_mode,  # Add GST mode field
            date_with_time=date_with_time,  # Add date/time display toggle
            total_amount=0,
            payment_status=payment_status,
            paid_amount=paid_amount,
            due_amount=due_amount
        )
        db.session.add(bill)
        db.session.flush()
        
        # Collect line items for GST calculation using new engine
        line_items = []
        calculated_items = []
        bill_items = []
        bill_items_data = []
        
        for idx, (pid, product_name, qty, price, discount, custom_gst) in enumerate(zip(items, product_names, quantities, prices, discounts, gst_rates_custom)):
            current_app.logger.debug(f"Processing item {idx}: pid={pid}, name={product_name}, qty={qty}, price={price}")
            try:
                qty = int(float(qty))
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
                    hsn_code = getattr(product, 'hsn_code', '') or ''
                    is_custom_product = False
                    product_display_name = product.product_name
                    
                else:  # Custom product (no product_id)
                    product = None
                    gst_rate = custom_gst
                    hsn_code = ''  # Can be extended to accept HSN from form
                    is_custom_product = True
                    product_display_name = product_name.strip() if product_name else ''
                    
                    # Skip if no product name for custom product
                    if not product_display_name:
                        continue
                
                # Check if this is a Non-GST bill
                if bill_gst_type == 'Non-GST':
                    # Non-GST calculation: No GST, only quantity × price with discount
                    line_total = price * qty
                    discount_amount = (line_total * discount) / 100
                    final_amount = line_total - discount_amount
                    
                    # Create Non-GST calculation result
                    gst_calc = {
                        'unit_price_base': price,
                        'line_base_total': line_total,
                        'discount_amount': discount_amount,
                        'taxable_amount': final_amount,
                        'gst_rate': 0,
                        'cgst_rate': 0,
                        'sgst_rate': 0,
                        'cgst_amount': 0,
                        'sgst_amount': 0,
                        'total_gst': 0,
                        'final_total': final_amount,
                        'mode': 'Non-GST'
                    }
                else:
                    # Use GST calculation engine for GST bills
                    # Determine GST mode (default to EXCLUSIVE for backward compatibility)
                    item_gst_mode = gst_mode.upper() if gst_mode else 'EXCLUSIVE'
                    
                    # Calculate using new GST engine
                    gst_calc = calc_line(
                        price=price,
                        qty=qty,
                        gst_rate=gst_rate,
                        discount_percent=discount,
                        mode=item_gst_mode
                    )
                
                # Update stock for existing products
                if not is_custom_product and product:
                    if product.stock_qty >= qty:
                        product.stock_qty -= qty
                    else:
                        current_app.logger.warning(f"Insufficient stock for product {product.product_name}. Available: {product.stock_qty}, Required: {qty}")
                
                # Create bill item with all calculated values
                if is_custom_product:
                    bill_item = BillItem(
                        bill_id=bill.bill_id,
                        product_id=None,
                        custom_product_name=product_display_name,
                        custom_gst_rate=gst_rate,
                        custom_hsn_code=hsn_code,
                        quantity=qty,
                        price_per_unit=price,
                        discount_percent=discount,
                        discount_amount=float(gst_calc['discount_amount']),
                        taxable_amount=float(gst_calc['taxable_amount']),
                        cgst_rate=float(gst_calc['cgst_rate']),
                        sgst_rate=float(gst_calc['sgst_rate']),
                        cgst_amount=float(gst_calc['cgst_amount']),
                        sgst_amount=float(gst_calc['sgst_amount']),
                        total_gst_amount=float(gst_calc['total_gst']),
                        total_price=float(gst_calc['final_total'])
                    )
                else:
                    bill_item = BillItem(
                        bill_id=bill.bill_id,
                        product_id=pid,
                        custom_product_name=None,
                        custom_gst_rate=None,
                        custom_hsn_code=None,
                        quantity=qty,
                        price_per_unit=price,
                        discount_percent=discount,
                        discount_amount=float(gst_calc['discount_amount']),
                        taxable_amount=float(gst_calc['taxable_amount']),
                        cgst_rate=float(gst_calc['cgst_rate']),
                        sgst_rate=float(gst_calc['sgst_rate']),
                        cgst_amount=float(gst_calc['cgst_amount']),
                        sgst_amount=float(gst_calc['sgst_amount']),
                        total_gst_amount=float(gst_calc['total_gst']),
                        total_price=float(gst_calc['final_total'])
                    )
                
                db.session.add(bill_item)
                bill_items.append(bill_item)
                
                # Prepare item data for template with all GST details
                item_data = {
                    'bill_item': bill_item,
                    'product_name': product_display_name,
                    'is_custom': is_custom_product,
                    'hsn_code': hsn_code,
                    'quantity': qty,
                    'unit_price': price,
                    'unit_price_base': float(gst_calc['unit_price_base']),
                    'line_base_total': float(gst_calc['line_base_total']),
                    'discount_percent': discount,
                    'discount_amount': float(gst_calc['discount_amount']),
                    'taxable_amount': float(gst_calc['taxable_amount']),
                    'gst_rate': float(gst_calc['gst_rate']),
                    'cgst_rate': float(gst_calc['cgst_rate']),
                    'sgst_rate': float(gst_calc['sgst_rate']),
                    'cgst_amount': float(gst_calc['cgst_amount']),
                    'sgst_amount': float(gst_calc['sgst_amount']),
                    'total_gst': float(gst_calc['total_gst']),
                    'final_total': float(gst_calc['final_total']),
                    'mode': gst_calc['mode']
                }
                
                # Add product reference for display
                if not is_custom_product and product:
                    item_data['product'] = product
                else:
                    # Create mock product for template compatibility
                    item_data['product'] = type('Product', (), {
                        'product_name': product_display_name,
                        'gst_rate': gst_rate,
                        'hsn_code': hsn_code,
                        'product_id': f'custom_{idx}'
                    })()
                
                bill_items_data.append(item_data)
                calculated_items.append(gst_calc)
                
            except Exception as e:
                current_app.logger.error(f"Error processing item {idx+1}: {str(e)}")
                flash(f"Error processing item {idx+1}: {str(e)}", 'warning')
                continue
        
        # Generate GST summary and totals using new engine
        if calculated_items:
            gst_summary = generate_gst_summary(calculated_items)
            bill_totals = calculate_bill_totals(calculated_items)
            
            # Convert summary for template (maintain backward compatibility)
            gst_summary_by_rate = {}
            for rate_str, summary_data in gst_summary.items():
                rate_float = float(rate_str)
                gst_summary_by_rate[rate_float] = {
                    'taxable_amount': float(summary_data['taxable_amount']),
                    'cgst_amount': float(summary_data['cgst_amount']),
                    'sgst_amount': float(summary_data['sgst_amount']),
                    'total_gst_amount': float(summary_data['total_gst'])
                }
            
            # Update bill totals
            overall_grand_total = float(bill_totals['grand_total'])
            total_taxable_amount = float(bill_totals['total_taxable_amount'])
            total_cgst_amount = float(bill_totals['total_cgst_amount'])
            total_sgst_amount = float(bill_totals['total_sgst_amount'])
            total_gst_amount = float(bill_totals['total_gst_amount'])
        else:
            # No items processed
            gst_summary_by_rate = {}
            overall_grand_total = 0.0
            total_taxable_amount = 0.0
            total_cgst_amount = 0.0
            total_sgst_amount = 0.0
            total_gst_amount = 0.0
        
        bill.total_amount = overall_grand_total
        
        # Update paid_amount and due_amount based on final total if needed
        try:
            if payment_status == 'Paid':
                paid_amount = overall_grand_total
                due_amount = 0
            elif payment_status == 'Unpaid':
                paid_amount = 0
                due_amount = overall_grand_total
            else:  # Partial payment
                paid_amount = float(request.form.get('paid_amount', 0))
                due_amount = overall_grand_total - paid_amount
        except (ValueError, TypeError):
            # Fallback values on error
            paid_amount = 0
            due_amount = overall_grand_total
        
        bill.paid_amount = paid_amount
        bill.due_amount = due_amount
        bill.payment_status = payment_status
        
        db.session.commit()
        
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
        
        # Create comprehensive ledger entries for all customer bills (PAID, PARTIAL, UNPAID)
        if bill.customer_id:  # Customer is linked to bill
            try:
                CustomerLedgerService.create_ledger_entries_for_bill(bill, shopkeeper)
                current_app.logger.debug(f"Created ledger entries for customer {bill.customer_id} on bill {bill.bill_number}")
            except Exception as e:
                current_app.logger.error(f"Failed to create ledger entries: {str(e)}")
                # Don't fail bill creation if ledger fails
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

    @bp.route('/bills/<filename>')
    def serve_bill_file(filename):
        return send_from_directory(os.path.join('app', 'static', 'bills'), filename)