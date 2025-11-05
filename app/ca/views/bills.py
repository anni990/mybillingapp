"""
Bills management routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_
import io

from app.models import (CharteredAccountant, CAEmployee, EmployeeClient, Bill, BillItem, 
                       Shopkeeper, CAConnection, Product)
from app.extensions import db
from app.utils.gst import calc_line, generate_gst_summary, calculate_bill_totals


def register_routes(bp):
    """Register bills management routes to the blueprint."""
    
    @bp.route('/bills', methods=['GET', 'POST'])
    @login_required
    def bills_panel():
        """Bills panel - preserves original logic."""
        # Allow both CA and CA employees
        if current_user.role not in ['CA', 'employee']:
            flash('Access denied: Invalid role.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Get CA information
        ca = None
        firm_name = None
        
        if current_user.role == 'CA':
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            if ca:
                firm_name = ca.firm_name
        elif current_user.role == 'employee':
            employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
            if employee:
                ca = CharteredAccountant.query.get(employee.ca_id)
                if ca:
                    firm_name = f"{ca.firm_name} (Employee View)"
        
        if not ca:
            flash('Error: Could not find CA information.', 'danger')
            return redirect(url_for('auth.login'))
        # Filters
        shopkeeper_id = request.args.get('shopkeeper_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Base query for bills and shopkeeper names
        query = db.session.query(Bill, Shopkeeper.shop_name).join(
            Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id
        )
        
        # Modify query based on role
        if current_user.role == 'CA':
            # For CA, show bills from all connected shopkeepers
            query = query.join(
                CAConnection,
                and_(
                    CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id,
                    CAConnection.ca_id == ca.ca_id,
                    CAConnection.status == 'approved'
                )
            )
        elif current_user.role == 'employee':
            # For employee, show only bills from assigned shopkeepers
            employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
            if employee:
                query = query.join(
                    EmployeeClient,
                    and_(
                        EmployeeClient.shopkeeper_id == Shopkeeper.shopkeeper_id,
                        EmployeeClient.employee_id == employee.employee_id
                    )
                )
        if shopkeeper_id:
            query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        bills = query.order_by(Bill.bill_date.desc()).all()
        bills_data = []
        print(f"Found {len(bills)} bills")
        for bill, shopkeeper_name in bills:
            try:
                bills_data.append({
                    'bill_id': bill.bill_id,
                    'shopkeeper_name': shopkeeper_name,
                    'bill_number': bill.bill_number,
                    'bill_date': bill.bill_date,
                    'total_amount': bill.total_amount,
                    'payment_status': bill.payment_status,
                    'paid_amount':bill.paid_amount,
                    'due_amount':bill.due_amount
                })
                # print(f"Added bill {bill.bill_id} to bills_data")
            except Exception as e:
                print(f"Error processing bill: {e}")
        # Shopkeepers for filter dropdown - only approved connections
        shopkeepers = Shopkeeper.query.join(CAConnection, and_(CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id, CAConnection.ca_id == ca.ca_id, CAConnection.status == 'approved')).all()
        return render_template('ca/bills.html', bills=bills_data, shopkeepers=shopkeepers, firm_name=firm_name)
    
    @bp.route('/bill/<int:bill_id>')
    @login_required
    def view_bill(bill_id):
        bill = Bill.query.get_or_404(bill_id)
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
                return redirect(url_for('shopkeeper.sales_bills'))
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
            # ca_conn = CAConnection.query.filter_by(shopkeeper_id=bill.shopkeeper_id, ca_id=current_user.ca.ca_id, status='approved').first()
            # is_editable = bool(ca_conn)
            is_editable = False
        elif current_user.role == 'employee':
            # emp_client = EmployeeClient.query.filter_by(shopkeeper_id=bill.shopkeeper_id, employee_id=current_user.ca_employee.employee_id).first()
            # is_editable = bool(emp_client)
            is_editable = False
        
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
            back_url=url_for('ca.bills_panel'))

    @bp.route('/bill/<int:bill_id>/edit', methods=['POST'])
    @login_required
    def update_bill_ca(bill_id):
        """Update bill - Only shopkeepers can edit bills."""
        bill = Bill.query.get_or_404(bill_id)

        # Access control - Only shopkeepers can edit bills
        if current_user.role in ['CA', 'employee']:
            flash("Only Shop Owner can Edit bills.", "warning")
            return redirect(url_for('ca.view_bill', bill_id=bill_id))
        
        elif current_user.role == 'shopkeeper':
            # Check if this shopkeeper owns the bill
            if bill.shopkeeper.user_id != current_user.user_id:
                flash("Access denied: You can only edit your own bills.", "danger")
                return redirect(url_for('shopkeeper.bills'))
        else:
            flash("Access denied: Unauthorized role.", "danger")
            return redirect(url_for('auth.login'))

        # ✅ Now update the bill data
        customer_name = request.form.get('customer_name')
        customer_contact = request.form.get('customer_contact')
        item_ids = request.form.getlist('item_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')

        print("CA update called")
        print("Form data:", request.form)

        bill.customer_name = customer_name
        bill.customer_contact = customer_contact

        # Delete old items
        BillItem.query.filter_by(bill_id=bill.bill_id).delete()

        total_base = 0
        total_gst = 0

        for pid, qty, price in zip(item_ids, quantities, prices):
            qty = int(qty)
            price = float(price)
            total_price = qty * price

            bill_item = BillItem(
                bill_id=bill.bill_id,
                product_id=pid,
                quantity=qty,
                price_per_unit=price,
                total_price=total_price
            )
            db.session.add(bill_item)

            # GST calculation
            product = Product.query.get(pid)
            gst_rate = float(product.gst_rate or 0)
            total_base += total_price
            total_gst += (total_price * gst_rate / 100)

        bill.total_amount = round(total_base + total_gst, 2)
        db.session.commit()

        flash("Bill updated successfully.", "success")
        print("Logged in as:", current_user.username, "Role:", current_user.role)

        # Redirect dynamically based on role
        if current_user.role == 'employee':
            return redirect(url_for('ca.view_bill', bill_id=bill_id))
        elif current_user.role == 'CA':
            return redirect(url_for('ca.view_bill', bill_id=bill_id))
        else:  # shopkeeper
            return redirect(url_for('shopkeeper.view_bill', bill_id=bill_id))