"""
Reports and exports routes for CA.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, redirect, url_for, request, flash, send_file
from flask_login import login_required, current_user
import io
import pandas as pd
import os
from werkzeug.utils import secure_filename

from app.models import (CharteredAccountant, CAConnection, Shopkeeper, Bill)
from app.extensions import db
from app.forms import CAProfileForm


def register_routes(bp):
    """Register reports and exports routes to the blueprint."""
    
    @bp.route('/reports', methods=['GET', 'POST'])
    @login_required
    def reports():
        """Reports - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name
        shopkeepers = Shopkeeper.query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved')).all()
        preview_bills = []
        shopkeeper_id = None
        start_date = None
        end_date = None
        if request.method == 'POST' and request.form.get('preview') == '1':
            shopkeeper_id = request.form.get('shopkeeper_id')
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            query = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
            query = query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved'))
            if shopkeeper_id:
                query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
            if start_date:
                query = query.filter(Bill.bill_date >= start_date)
            if end_date:
                query = query.filter(Bill.bill_date <= end_date)
            bills = query.order_by(Bill.bill_date.desc()).limit(5).all()
            for bill, shop_name in bills:
                preview_bills.append({
                    'Date': bill.bill_date.strftime('%d-%m-%Y'),
                    'Voucher Type': 'Sales',
                    'Party Name': shop_name,
                    'Bill No': bill.bill_number,
                    'GST Type': bill.gst_type,
                    'Total Amount': bill.total_amount,
                    'Payment Status': bill.payment_status,
                })
        return render_template('ca/reports.html', shopkeepers=shopkeepers, firm_name=firm_name, preview_bills=preview_bills, selected_shopkeeper_id=shopkeeper_id, selected_start_date=start_date, selected_end_date=end_date)

    @bp.route('/export_bills', methods=['POST'])
    @login_required
    def export_bills():
        """Export bills - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        # Get filters
        shopkeeper_id = request.form.get('shopkeeper_id')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        # Query bills
        query = db.session.query(Bill, Shopkeeper.shop_name).join(Shopkeeper, Bill.shopkeeper_id == Shopkeeper.shopkeeper_id)
        query = query.join(CAConnection, (CAConnection.shopkeeper_id == Shopkeeper.shopkeeper_id) & (CAConnection.ca_id == ca.ca_id) & (CAConnection.status == 'approved'))
        if shopkeeper_id:
            query = query.filter(Bill.shopkeeper_id == shopkeeper_id)
        if start_date:
            query = query.filter(Bill.bill_date >= start_date)
        if end_date:
            query = query.filter(Bill.bill_date <= end_date)
        bills = query.order_by(Bill.bill_date.desc()).all()
        # Prepare data for Tally-compatible Excel
        data = []
        for bill, shop_name in bills:
            data.append({
                'Date': bill.bill_date.strftime('%d-%m-%Y'),
                'Voucher Type': 'Sales',
                'Party Name': shop_name,
                'Bill No': bill.bill_number,
                'GST Type': bill.gst_type,
                'Total Amount': bill.total_amount,
                'Payment Status': bill.payment_status,
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Bills')
        output.seek(0)
        return send_file(output, as_attachment=True, download_name='bills_tally.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    @bp.route('/export/all')
    @login_required
    def export_all_bills():
        """Export all bills - preserves original logic."""
        # Placeholder: implement Excel/Tally export logic
        flash('Export feature coming soon!', 'info')
        return redirect(url_for('ca.dashboard'))

    @bp.route('/bills/export_bulk', methods=['POST'])
    @login_required
    def export_bulk_bills():
        """Export bulk bills - preserves original logic."""
        # Placeholder: implement bulk export logic
        flash('Bulk export feature coming soon!', 'info')
        return redirect(url_for('ca.bills_panel'))
    
    @bp.route('/profile', methods=['GET', 'POST'])
    @login_required
    def ca_profile():
        """CA profile management - preserves original logic."""
        if current_user.role != 'CA':
            return redirect(url_for('ca.dashboard'))
        ca = CharteredAccountant.query.filter_by(user_id=current_user.user_id).first()
        firm_name = ca.firm_name
        edit_mode = request.args.get('edit', '0') == '1'
        
        form = CAProfileForm()
        
        # Initialize form fields with existing data for GET requests
        if request.method == 'GET':
            # Populate form with existing CA data
            form.firm_name.data = ca.firm_name
            form.area.data = ca.area
            form.contact_number.data = ca.contact_number
            form.gst_number.data = ca.gst_number
            form.pan_number.data = ca.pan_number
            form.address.data = ca.address
            form.about_me.data = ca.about_me
            form.city.data = ca.city
            form.state.data = ca.state
            form.pincode.data = ca.pincode
            form.ca_name.data = ca.ca_name
            form.ca_email_id.data = ca.ca_email_id
            # form.gstin.data = ca.gstin
            
            # Initialize form fields with existing JSON data
            import json
            if ca.domain_expertise:
                try:
                    form.domain_expertise.data = json.loads(ca.domain_expertise)
                except (json.JSONDecodeError, TypeError):
                    form.domain_expertise.data = []
            else:
                form.domain_expertise.data = []
            
            if ca.industries_served:
                try:
                    form.industries_served.data = json.loads(ca.industries_served)
                except (json.JSONDecodeError, TypeError):
                    form.industries_served.data = []
            else:
                form.industries_served.data = []
            
            if ca.experience:
                form.experience.data = str(ca.experience)
            else:
                form.experience.data = ''
            
        if form.validate_on_submit():
            import json
            
            # Debug: Print form data
            print("DEBUG - Form Domain Expertise Data:", form.domain_expertise.data)
            print("DEBUG - Form Industries Served Data:", form.industries_served.data)
            print("DEBUG - Form Experience Data:", form.experience.data)
            
            ca.firm_name = form.firm_name.data
            ca.area = form.area.data
            ca.contact_number = form.contact_number.data
            ca.gst_number = form.gst_number.data
            ca.pan_number = form.pan_number.data
            ca.address = form.address.data
            # ca.gstin = form.gstin.data
            ca.about_me = form.about_me.data  # Save About Me
            ca.city = form.city.data
            ca.state = form.state.data
            ca.pincode = form.pincode.data
            
            # Save new professional profile fields
            ca.ca_name = form.ca_name.data
            ca.ca_email_id = form.ca_email_id.data
            
            # Handle domain expertise (convert list to JSON string)
            if form.domain_expertise.data:
                ca.domain_expertise = json.dumps(form.domain_expertise.data)
                print("DEBUG - Saving Domain Expertise:", ca.domain_expertise)
            else:
                ca.domain_expertise = None
                print("DEBUG - Domain Expertise is None")
                
            # Handle experience (convert to integer)
            if form.experience.data and form.experience.data != '':
                try:
                    ca.experience = int(form.experience.data)
                    print("DEBUG - Saving Experience:", ca.experience)
                except ValueError:
                    ca.experience = None
                    print("DEBUG - Experience ValueError")
            else:
                ca.experience = None
                print("DEBUG - Experience is None")
                
            # Handle industries served (convert list to JSON string)
            if form.industries_served.data:
                ca.industries_served = json.dumps(form.industries_served.data)
                print("DEBUG - Saving Industries Served:", ca.industries_served)
            else:
                ca.industries_served = None
                print("DEBUG - Industries Served is None")
            
            # Handle file uploads
            upload_folder = os.path.join('app', 'static', 'ca_upload')
            os.makedirs(upload_folder, exist_ok=True)
            def save_file(field, old_path=None):
                file = getattr(form, field).data
                # Only save if file is a FileStorage object (has filename attribute)
                if hasattr(file, 'filename') and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(upload_folder, filename)
                    file.save(file_path)
                    return f'ca_upload/{filename}'
                return old_path
            ca.aadhaar_file = save_file('aadhaar_file', ca.aadhaar_file)
            ca.pan_file = save_file('pan_file', ca.pan_file)
            ca.icai_certificate_file = save_file('icai_certificate_file', ca.icai_certificate_file)
            ca.cop_certificate_file = save_file('cop_certificate_file', ca.cop_certificate_file)
            ca.business_reg_file = save_file('business_reg_file', ca.business_reg_file)
            ca.bank_details_file = save_file('bank_details_file', ca.bank_details_file)
            ca.photo_file = save_file('photo_file', ca.photo_file)
            ca.signature_file = save_file('signature_file', ca.signature_file)
            ca.office_address_proof_file = save_file('office_address_proof_file', ca.office_address_proof_file)
            ca.self_declaration_file = save_file('self_declaration_file', ca.self_declaration_file)
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('ca.ca_profile'))
        return render_template('ca/ca_profile.html', form=form, ca=ca, edit_mode=edit_mode, firm_name=firm_name)