"""
Bills management routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user
from sqlalchemy import and_
import io

from app.models import (CharteredAccountant, CAEmployee, EmployeeClient, Bill, BillItem, 
                       Shopkeeper, CAConnection, Product)
from app.extensions import db


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
                print(f"Added bill {bill.bill_id} to bills_data")
            except Exception as e:
                print(f"Error processing bill: {e}")
        # Shopkeepers for filter dropdown
        shopkeepers = Shopkeeper.query.join(CAConnection, and_(CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id, CAConnection.ca_id == ca.ca_id)).all()
        return render_template('ca/bills.html', bills=bills_data, shopkeepers=shopkeepers, firm_name=firm_name)
    
    @bp.route('/bill/<int:bill_id>')
    @login_required
    def view_bill(bill_id):
        """View bill - preserves original logic."""
        print(f"Accessing bill {bill_id} by user {current_user.user_id} with role {current_user.role}")
        
        # Allow access only for CA and employees
        if current_user.role not in ['CA', 'employee']:
            flash('Access denied: Invalid role.', 'danger')
            return redirect(url_for('auth.login'))

        bill = Bill.query.get_or_404(bill_id)
        print(f"Found bill {bill.bill_id} for shopkeeper {bill.shopkeeper_id}")

        # Initialize access check
        is_editable = False

        if current_user.role == 'CA':
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            if ca:
                ca_conn = CAConnection.query.filter_by(
                    shopkeeper_id=bill.shopkeeper_id,
                    ca_id=ca.ca_id,
                    status='approved'
                ).first()
                is_editable = bool(ca_conn)
                print(f"CA {ca.ca_id} connection status with shopkeeper {bill.shopkeeper_id}: {is_editable}")

        elif current_user.role == 'employee':
            employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
            if employee:
                emp_client = EmployeeClient.query.filter_by(
                    shopkeeper_id=bill.shopkeeper_id,
                    employee_id=employee.employee_id
                ).first()
                is_editable = bool(emp_client)
                print(f"Employee-Client access status: {is_editable}")

        if not is_editable:
            flash('Access denied: You are not authorized to view this bill.', 'danger')
            return redirect(url_for('ca.bills_panel'))

        # Determine correct back_url based on role
        if current_user.role == 'CA':
            back_url = url_for('ca.bills_panel')
        elif current_user.role == 'employee':
            back_url = url_for('ca.employee_dashboard')
        else:
            back_url = url_for('auth.login')

        print(f"Rendering bill view for role {current_user.role}, back_url = {back_url}")

        # Download PDF flag
        is_download = request.args.get('download') == 'true'

        # Get bill items and related data
        bill_items = BillItem.query.filter_by(bill_id=bill.bill_id).all()
        shopkeeper = bill.shopkeeper
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()
        products_dict = {str(p.product_id): p for p in products}

        # GST Summary calculations
        bill_items_data = []
        gst_summary_by_rate = {}
        total_taxable_amount = 0
        total_cgst_amount = 0
        total_sgst_amount = 0
        total_gst_amount = 0
        overall_grand_total = 0

        for item in bill_items:
            product = products_dict.get(str(item.product_id))
            if not product:
                continue
            base_price = float(item.price_per_unit)
            quantity = int(item.quantity)
            total_price = base_price * quantity

            discount = 0
            discount_amount = (discount / 100) * total_price
            discounted_price = total_price - discount_amount

            gst_rate = float(product.gst_rate or 0)
            sgst_rate = cgst_rate = gst_rate / 2
            sgst_amount = (sgst_rate / 100) * discounted_price
            cgst_amount = (cgst_rate / 100) * discounted_price
            final_price = discounted_price + sgst_amount + cgst_amount

            item_data = {
                'product': product,
                'hsn_code': product.hsn_code if hasattr(product, 'hsn_code') else '',
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

            gst_summary_by_rate.setdefault(gst_rate, {
                'taxable_amount': 0,
                'cgst_amount': 0,
                'sgst_amount': 0,
                'total_gst_amount': 0
            })

            gst_summary_by_rate[gst_rate]['taxable_amount'] += discounted_price
            gst_summary_by_rate[gst_rate]['cgst_amount'] += cgst_amount
            gst_summary_by_rate[gst_rate]['sgst_amount'] += sgst_amount
            gst_summary_by_rate[gst_rate]['total_gst_amount'] += (cgst_amount + sgst_amount)

            total_taxable_amount += discounted_price
            total_cgst_amount += cgst_amount
            total_sgst_amount += sgst_amount
            total_gst_amount += (cgst_amount + sgst_amount)
            overall_grand_total += final_price

        template_data = {
            'bill': bill,
            'bill_items_data': bill_items_data,
            'shopkeeper': shopkeeper,
            'products': products_dict,
            'gst_summary_by_rate': gst_summary_by_rate,
            'total_taxable_amount': total_taxable_amount,
            'total_cgst_amount': total_cgst_amount,
            'total_sgst_amount': total_sgst_amount,
            'total_gst_amount': total_gst_amount,
            'overall_grand_total': overall_grand_total,
            'is_editable': is_editable,
            'back_url': back_url  # ✅ Correct dynamic back URL passed to template
        }

        if is_download:
            from weasyprint import HTML
            template_data['is_editable'] = False
            html = render_template('shopkeeper/bill_receipt.html', **template_data)
            pdf = HTML(string=html).write_pdf()
            return send_file(
                io.BytesIO(pdf),
                download_name=f'bill_{bill.bill_number}.pdf',
                mimetype='application/pdf'
            )

        return render_template('shopkeeper/bill_receipt.html', **template_data)

    @bp.route('/bill/<int:bill_id>/edit', methods=['POST'])
    @login_required
    def update_bill_ca(bill_id):
        """Update bill - preserves original logic."""
        bill = Bill.query.get_or_404(bill_id)

        # Access control
        if current_user.role == 'CA':
            ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
            allowed = CAConnection.query.filter_by(shopkeeper_id=bill.shopkeeper_id, ca_id=ca.ca_id, status='approved').first()
            if not allowed:
                flash("Access denied: CA not connected to this client.", "danger")
                return redirect(url_for('ca.bills_panel'))

        elif current_user.role == 'employee':
            employee = CAEmployee.query.filter_by(user_id=current_user.user_id).first()
            allowed = EmployeeClient.query.filter_by(shopkeeper_id=bill.shopkeeper_id, employee_id=employee.employee_id).first()
            if not allowed:
                flash("Access denied: Employee not assigned to this client.", "danger")
                return redirect(url_for('ca.bills_panel'))

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