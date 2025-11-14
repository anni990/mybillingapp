"""
Profile and document management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, current_app, g, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from ..utils import shopkeeper_required, update_shopkeeper_verification
from app.models import Shopkeeper, CharteredAccountant, CAConnection, ShopConnection
from app.extensions import db


def generate_next_invoice_number(shopkeeper):
    """Generate the next invoice number and increment the counter."""
    # Format the number with leading zeros (e.g., 01, 02, 03)
    formatted_number = str(shopkeeper.current_invoice_number).zfill(2)
    invoice_number = f"{shopkeeper.invoice_prefix}{formatted_number}"
    
    # Increment the counter for next use
    shopkeeper.current_invoice_number += 1
    
    return invoice_number

def reset_invoice_numbering(shopkeeper, prefix=None, starting_number=None):
    """Reset invoice numbering with new prefix and/or starting number."""
    if prefix is not None:
        shopkeeper.invoice_prefix = prefix
    if starting_number is not None:
        shopkeeper.invoice_starting_number = starting_number
        shopkeeper.current_invoice_number = starting_number

def preview_next_invoice_number(shopkeeper):
    """Preview what the next invoice number will be without incrementing."""
    formatted_number = str(shopkeeper.current_invoice_number).zfill(2)
    return f"{shopkeeper.invoice_prefix}{formatted_number}"

def is_custom_numbering_enabled(shopkeeper):
    """Check if shopkeeper has enabled custom invoice numbering."""
    return (shopkeeper.invoice_prefix and 
            shopkeeper.invoice_prefix.strip() != '' and
            shopkeeper.invoice_starting_number is not None and
            shopkeeper.current_invoice_number is not None)


def register_routes(bp):
    """Register profile management routes to the blueprint."""
    

    @bp.route('/profile')
    @login_required
    @shopkeeper_required
    def profile():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        return render_template('shopkeeper/new_profile.html', 
                             shopkeeper=shopkeeper,
                             shop_name=shop_name,
                             preview_next_invoice_number=preview_next_invoice_number)

    @bp.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    @shopkeeper_required
    def profile_edit():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        if request.method == 'POST':
            try:
                # Helper function to handle empty strings
                def safe_get_form_value(field_name, convert_to=None):
                    value = request.form.get(field_name, '').strip()
                    if not value:
                        return None
                    if convert_to == int:
                        try:
                            return int(value)
                        except (ValueError, TypeError):
                            return None
                    return value
                
                # Personal Information
                shopkeeper.owner_name = safe_get_form_value('owner_name')
                shopkeeper.pan_number = safe_get_form_value('pan_number')
                shopkeeper.owner_address = safe_get_form_value('owner_address')
                
                # Business Information
                shopkeeper.shop_name = safe_get_form_value('shop_name') or shopkeeper.shop_name  # Keep existing if empty
                shopkeeper.business_type = safe_get_form_value('business_type')
                shopkeeper.established_year = safe_get_form_value('established_year', convert_to=int)
                shopkeeper.gst_number = safe_get_form_value('gst_number')
                shopkeeper.contact_number = safe_get_form_value('contact_number')
                shopkeeper.business_address = safe_get_form_value('business_address')
                
                # Location Information
                shopkeeper.city = safe_get_form_value('city')
                shopkeeper.state = safe_get_form_value('state')
                shopkeeper.pincode = safe_get_form_value('pincode')
                
                # Banking Information
                shopkeeper.bank_name = safe_get_form_value('bank_name')
                shopkeeper.account_number = safe_get_form_value('account_number')
                shopkeeper.ifsc_code = safe_get_form_value('ifsc_code')
                shopkeeper.upi_id = safe_get_form_value('upi_id')
                
                # Bill Template Settings
                template_choice = safe_get_form_value('template_choice')
                if template_choice:
                    shopkeeper.template_choice = template_choice
                
                # Backward compatibility - update legacy fields
                if shopkeeper.business_type and not shopkeeper.domain:
                    shopkeeper.domain = shopkeeper.business_type
                if shopkeeper.business_address and not shopkeeper.address:
                    shopkeeper.address = shopkeeper.business_address
                
                # Handle document uploads
                document_types = [
                    ('gst_doc', 'gst_doc_path'),
                    ('pan_doc', 'pan_doc_path'),
                    ('address_proof', 'address_proof_path'),
                    ('aadhaar_dl', 'aadhaar_dl_path'),
                    ('selfie', 'selfie_path'),
                    ('gumasta', 'gumasta_path'),
                    ('udyam', 'udyam_path'),
                    ('bank_statement', 'bank_statement_path'),
                    ('logo', 'logo_path')
                ]
                
                for form_field, db_field in document_types:
                    file = request.files.get(form_field)
                    if file and file.filename:
                        # Validate file
                        allowed_exts = {'pdf', 'jpg', 'jpeg', 'png'}
                        if form_field in ['selfie', 'logo']:
                            if form_field == 'logo':
                                allowed_exts.add('svg')
                            elif form_field == 'selfie':
                                allowed_exts = {'jpg', 'jpeg', 'png'}
                        
                        max_size = 2 * 1024 * 1024  # 2MB
                        
                        # Get file extension
                        if '.' not in file.filename:
                            flash(f'Invalid file type for {form_field.replace("_", " ").title()}. File extension required.', 'warning')
                            continue
                            
                        ext = file.filename.rsplit('.', 1)[-1].lower()
                        if ext not in allowed_exts:
                            flash(f'Invalid file type for {form_field.replace("_", " ").title()}. Allowed: {", ".join(allowed_exts).upper()}', 'warning')
                            continue
                        
                        # Check file size
                        file.seek(0, 2)
                        size = file.tell()
                        file.seek(0)
                        if size > max_size:
                            flash(f'File too large for {form_field.replace("_", " ").title()}. Maximum 2MB allowed.', 'warning')
                            continue
                        
                        # Save file
                        filename = f"shopkeeper_{shopkeeper.shopkeeper_id}_{form_field}.{ext}"
                        save_path = os.path.join('app', 'static', 'shop_upload', filename)
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        file.save(save_path)
                        
                        # Update database
                        rel_path = f"shop_upload/{filename}"
                        setattr(shopkeeper, db_field, rel_path)
                        flash(f'{form_field.replace("_", " ").title()} uploaded successfully.', 'success')
            
                # Handle invoice numbering settings
                invoice_prefix = safe_get_form_value('invoice_prefix')
                invoice_starting_number_str = safe_get_form_value('invoice_starting_number')
                
                # Update prefix (can be empty for timestamp-based numbering)
                if invoice_prefix is not None:
                    shopkeeper.invoice_prefix = invoice_prefix
                
                # Handle invoice starting number with proper validation
                if invoice_starting_number_str:
                    try:
                        starting_num = int(invoice_starting_number_str)
                        if starting_num > 0:  # Ensure positive number
                            # Only update if it's different from current
                            if starting_num != shopkeeper.invoice_starting_number:
                                shopkeeper.invoice_starting_number = starting_num
                                shopkeeper.current_invoice_number = starting_num
                                if invoice_prefix:  # Only show preview if custom numbering is enabled
                                    flash(f'Invoice numbering reset. Next invoice will be: {preview_next_invoice_number(shopkeeper)}', 'info')
                                else:
                                    flash('Invoice numbering reset to timestamp-based method.', 'info')
                        else:
                            flash('Invoice starting number must be greater than 0.', 'warning')
                    except (ValueError, TypeError):
                        flash('Invalid starting number provided. Please enter a valid number.', 'warning')
                
                # Commit all changes
                db.session.commit()
                update_shopkeeper_verification(shopkeeper)
                flash('Profile updated successfully.', 'success')
                return redirect(url_for('shopkeeper.profile'))
                
            except Exception as e:
                # Rollback on any error
                db.session.rollback()
                flash(f'An error occurred while updating your profile: {str(e)}', 'danger')
                return redirect(url_for('shopkeeper.profile_edit'))
        return render_template('shopkeeper/new_edit_profile.html', 
                             shop_name=shop_name,
                             shopkeeper=shopkeeper,
                             preview_next_invoice_number=preview_next_invoice_number)

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

    @bp.route('/upload_document/<doc_type>', methods=['POST'])
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

    @bp.route('/delete_document/<doc_type>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def delete_document(doc_type):
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            deleted = False
            
            if doc_type == 'gst' and shopkeeper.gst_doc_path:
                shopkeeper.gst_doc_path = None
                deleted = True
            elif doc_type == 'pan' and shopkeeper.pan_doc_path:
                shopkeeper.pan_doc_path = None
                deleted = True
            elif doc_type == 'address_proof' and shopkeeper.address_proof_path:
                shopkeeper.address_proof_path = None
                deleted = True
            elif doc_type == 'logo' and shopkeeper.logo_path:
                shopkeeper.logo_path = None
                deleted = True
            elif doc_type == 'aadhaar_dl' and shopkeeper.aadhaar_dl_path:
                shopkeeper.aadhaar_dl_path = None
                deleted = True
            elif doc_type == 'selfie' and shopkeeper.selfie_path:
                shopkeeper.selfie_path = None
                deleted = True
            elif doc_type == 'gumasta' and shopkeeper.gumasta_path:
                shopkeeper.gumasta_path = None
                deleted = True
            elif doc_type == 'udyam' and shopkeeper.udyam_path:
                shopkeeper.udyam_path = None
                deleted = True
            elif doc_type == 'bank_statement' and shopkeeper.bank_statement_path:
                shopkeeper.bank_statement_path = None
                deleted = True
            
            if deleted:
                db.session.commit()
                update_shopkeeper_verification(shopkeeper)
                return jsonify({
                    'success': True, 
                    'message': f'{doc_type.replace("_", " ").title()} deleted successfully.'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': f'No {doc_type.replace("_", " ")} document found to delete.'
                })
                
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False, 
                'message': f'Error deleting document: {str(e)}'
            })

    def get_shopkeeper_pending_requests():
        if hasattr(g, 'shopkeeper_pending_requests'):
            return g.shopkeeper_pending_requests
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

    @bp.app_context_processor
    def inject_shopkeeper_pending_requests():
        return {'shopkeeper_pending_requests': get_shopkeeper_pending_requests()}

    @bp.route('/handle_connection_request', methods=['POST'])
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


    @bp.route('/update-invoice-config', methods=['POST'])
    @login_required
    @shopkeeper_required
    def update_invoice_config():
        """API endpoint to update invoice configuration."""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                return jsonify({'success': False, 'message': 'Shopkeeper not found'}), 404

            # Get form data with safe handling
            invoice_prefix = request.form.get('invoice_prefix', '').strip()
            invoice_starting_number = request.form.get('invoice_starting_number', '').strip()

            # Validate starting number
            if invoice_starting_number:
                try:
                    starting_number = int(invoice_starting_number)
                    if starting_number < 1 or starting_number > 999999:
                        return jsonify({'success': False, 'message': 'Starting number must be between 1 and 999999'}), 400
                except ValueError:
                    return jsonify({'success': False, 'message': 'Invalid starting number'}), 400
            else:
                starting_number = 1

            # Validate prefix
            if invoice_prefix and len(invoice_prefix) > 10:
                return jsonify({'success': False, 'message': 'Invoice prefix must be 10 characters or less'}), 400

            # Update shopkeeper fields
            shopkeeper.invoice_prefix = invoice_prefix if invoice_prefix else None
            shopkeeper.invoice_starting_number = starting_number
            
            # Reset current counter only if starting number changed
            if shopkeeper.current_invoice_number != starting_number:
                shopkeeper.current_invoice_number = starting_number

            # Save to database
            db.session.commit()

            # Return success with preview
            preview = preview_next_invoice_number(shopkeeper) if invoice_prefix else f'BILL{str(starting_number).zfill(9)}'
            
            return jsonify({
                'success': True,
                'message': 'Invoice configuration updated successfully',
                'preview': preview
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating invoice config: {e}")
            return jsonify({'success': False, 'message': 'An error occurred while updating configuration'}), 500


    @bp.route('/update-template-config', methods=['POST'])
    @login_required
    @shopkeeper_required
    def update_template_config():
        """API endpoint to update template configuration."""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                return jsonify({'success': False, 'message': 'Shopkeeper not found'}), 404

            # Get form data
            template_choice = request.form.get('template_choice', '').strip()

            # Validate template choice
            valid_templates = ['template1', 'template2', 'template3']
            if not template_choice or template_choice not in valid_templates:
                return jsonify({'success': False, 'message': 'Invalid template selection'}), 400

            # Update shopkeeper template choice
            shopkeeper.template_choice = template_choice

            # Save to database
            db.session.commit()

            # Get template name for response
            template_names = {
                'template1': 'Basic Template',
                'template2': 'Professional Template',
                'template3': 'Modern Template'
            }

            return jsonify({
                'success': True,
                'message': f'Template updated to {template_names.get(template_choice, "Unknown")} successfully',
                'template': template_choice,
                'template_name': template_names.get(template_choice, "Unknown")
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating template config: {e}")
            return jsonify({'success': False, 'message': 'An error occurred while updating template configuration'}), 500
