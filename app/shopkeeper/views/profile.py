"""
Profile and document management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, current_app, g, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import logging
import json
from datetime import datetime, timedelta

from ..utils import shopkeeper_required, update_shopkeeper_verification
from app.models import Shopkeeper, CharteredAccountant, CAConnection, ShopConnection
from app.extensions import db
from ..services.watermark_service import WatermarkService
from ..services.payment_service import PaymentService
from ..services.watermark_service import WatermarkService

# Configure logging
logger = logging.getLogger(__name__)


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
                             preview_next_invoice_number=preview_next_invoice_number,
                             watermark_info=WatermarkService.get_watermark_display_info(shopkeeper),
                             watermark_types=WatermarkService.get_watermark_types())

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
                
                # Handle watermark settings
                watermark_enabled = request.form.get('watermark_enabled') == 'true'
                watermark_type = safe_get_form_value('watermark_type') or 'diagonal'
                
                # Validate watermark settings with business rules
                validation = WatermarkService.validate_watermark_update(shopkeeper, watermark_enabled, watermark_type)
                if validation['valid']:
                    shopkeeper.watermark_enabled = watermark_enabled
                    shopkeeper.watermark_type = watermark_type
                    flash('Watermark settings updated successfully.', 'success')
                else:
                    flash(validation['message'], 'warning')
                
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
                             preview_next_invoice_number=preview_next_invoice_number,
                             watermark_info=WatermarkService.get_watermark_display_info(shopkeeper),
                             watermark_types=WatermarkService.get_watermark_types())

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
        """Update invoice configuration with CSRF support."""
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
        """Update template configuration with CSRF support."""
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

    
    @bp.route('/subscription')
    @login_required
    @shopkeeper_required
    def subscription():
        """Subscription management page."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        from ..services import SubscriptionService
        usage_stats = SubscriptionService.get_usage_stats(shopkeeper)
        
        # Get payment history for the subscription page
        payment_history = PaymentService.get_shopkeeper_payment_history(shopkeeper, limit=5)
        
        return render_template('shopkeeper/subscription.html',
                             shopkeeper=shopkeeper,
                             shop_name=shopkeeper.shop_name,
                             usage_stats=usage_stats,
                             payment_history=payment_history,
                             plan_features=SubscriptionService.PLAN_FEATURES)
    
    @bp.route('/initiate-payment', methods=['POST'])
    @login_required
    @shopkeeper_required
    def initiate_payment():
        """Initiate Razorpay payment for subscription upgrade."""
        try:
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                return jsonify({'success': False, 'error': 'Shopkeeper not found'}), 404
            
            plan_type = request.json.get('plan_type')
            if not plan_type or plan_type not in ['lite', 'gold']:
                return jsonify({'success': False, 'error': 'Invalid plan type'}), 400
            
            # Prevent downgrade payments (business logic)
            current_plan_hierarchy = {'free': 0, 'lite': 1, 'gold': 2}
            if current_plan_hierarchy.get(shopkeeper.subscription_plan, 0) >= current_plan_hierarchy.get(plan_type, 0):
                return jsonify({
                    'success': False, 
                    'error': f'Cannot upgrade from {shopkeeper.subscription_plan} to {plan_type}'
                }), 400
            
            # Create Razorpay order
            order_result = PaymentService.create_razorpay_order(shopkeeper, plan_type)
            
            if order_result['success']:
                logger.info(f"Payment initiated for shopkeeper {shopkeeper.shopkeeper_id}, plan: {plan_type}")
                return jsonify(order_result)
            else:
                logger.error(f"Payment initiation failed: {order_result.get('error')}")
                return jsonify(order_result), 500
                
        except Exception as e:
            logger.error(f"Error in initiate_payment: {str(e)}")
            return jsonify({'success': False, 'error': 'Payment initiation failed'}), 500
    
    @bp.route('/payment-success', methods=['POST'])
    @login_required
    @shopkeeper_required
    def payment_success():
        """Handle successful payment callback from Razorpay."""
        try:
            data = request.json
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')
            
            if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
                return jsonify({'success': False, 'error': 'Missing payment details'}), 400
            
            # Process the successful payment
            result = PaymentService.process_successful_payment(
                razorpay_order_id, razorpay_payment_id, razorpay_signature
            )
            
            if result['success']:
                logger.info(f"Payment success processed for order {razorpay_order_id}")
                return jsonify({
                    'success': True,
                    'message': f'Payment successful! Your plan has been upgraded to {result["plan_upgraded"].upper()}',
                    'redirect': url_for('shopkeeper.subscription')
                })
            else:
                logger.error(f"Payment processing failed: {result.get('error')}")
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error in payment_success: {str(e)}")
            return jsonify({'success': False, 'error': 'Payment processing failed'}), 500
    
    @bp.route('/payment-failure', methods=['POST'])
    @login_required
    @shopkeeper_required
    def payment_failure():
        """Handle failed payment callback from Razorpay."""
        try:
            data = request.json
            razorpay_order_id = data.get('razorpay_order_id')
            failure_reason = data.get('error', {}).get('description', 'Payment failed')
            
            if razorpay_order_id:
                PaymentService.handle_payment_failure(razorpay_order_id, failure_reason)
                logger.info(f"Payment failure handled for order {razorpay_order_id}")
            
            return jsonify({
                'success': False,
                'error': 'Payment was cancelled or failed. Please try again.',
                'redirect': url_for('shopkeeper.subscription')
            })
            
        except Exception as e:
            logger.error(f"Error in payment_failure: {str(e)}")
            return jsonify({'success': False, 'error': 'Error handling payment failure'}), 500
    
    
    @bp.route('/update-subscription', methods=['POST'])
    @login_required
    @shopkeeper_required
    def update_subscription():
        """Update shopkeeper subscription plan - now redirects paid plans to payment."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        new_plan = request.form.get('plan')
        
        if not new_plan or new_plan not in ['free', 'lite', 'gold']:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid plan selected'}), 400
            flash('Invalid plan selected.', 'error')
            return redirect(url_for('shopkeeper.subscription'))
        
        # For paid plans (lite/gold), redirect to payment process
        if new_plan in ['lite', 'gold']:
            if request.is_json:
                return jsonify({
                    'success': False, 
                    'message': 'Payment required for this plan',
                    'require_payment': True,
                    'plan_type': new_plan
                })
            flash(f'Payment required to upgrade to {new_plan.upper()} plan.', 'info')
            return redirect(url_for('shopkeeper.subscription'))
        
        # Only allow free plan changes without payment
        from ..services import SubscriptionService
        success = SubscriptionService.update_plan(shopkeeper, new_plan)
        
        if success:
            if request.is_json:
                return jsonify({'success': True, 'message': f'Plan updated to {new_plan.upper()} successfully'})
            flash(f'Plan updated to {new_plan.upper()} successfully!', 'success')
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Failed to update plan'}), 500
            flash('Failed to update plan. Please try again.', 'error')
        
        return redirect(url_for('shopkeeper.subscription'))

    @bp.route('/update-watermark-settings', methods=['POST'])
    @login_required
    @shopkeeper_required
    def update_watermark_settings():
        """Update watermark settings from profile page."""
        try:
            # Debug: Log request information
            # logger.info(f"Watermark update request - Headers: {dict(request.headers)}")
            # logger.info(f"Content-Type: {request.content_type}, Is JSON: {request.is_json}")
            
            shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
            if not shopkeeper:
                logger.error(f"Shopkeeper not found for user {current_user.user_id}")
                return jsonify({
                    'success': False,
                    'message': 'Shopkeeper not found'
                }), 404
            
            # Handle both JSON and form data
            if request.is_json:
                data = request.get_json()
                if not data:
                    logger.error("No JSON data provided in request")
                    return jsonify({
                        'success': False,
                        'message': 'No data provided'
                    }), 400
                
                watermark_enabled = data.get('watermark_enabled')
                watermark_type = data.get('watermark_type', shopkeeper.watermark_type or 'diagonal')
                
                # Debug: Log received data
                # logger.info(f"JSON data received: {data}")
            else:
                watermark_enabled = request.form.get('watermark_enabled')
                watermark_type = request.form.get('watermark_type', shopkeeper.watermark_type or 'diagonal')
                
                # Debug: Log form data
                logger.info(f"Form data received: watermark_enabled={watermark_enabled}, watermark_type={watermark_type}")
            
            # Convert string 'true'/'false' to boolean if needed
            if isinstance(watermark_enabled, str):
                watermark_enabled = watermark_enabled.lower() == 'true'
            elif watermark_enabled is None:
                watermark_enabled = shopkeeper.watermark_enabled  # Keep current setting
            
            logger.info(f"Watermark update request - User: {current_user.user_id}, Plan: {shopkeeper.subscription_plan}, Enabled: {watermark_enabled}, Type: {watermark_type}")
            
            # Special handling for free users - they can change style but not disable watermark
            if shopkeeper.subscription_plan == 'free':
                if not watermark_enabled:
                    logger.warning(f"Free user {shopkeeper.shopkeeper_id} tried to disable watermark")
                    return jsonify({
                        'success': False,
                        'message': 'Free users cannot disable watermark. Upgrade to Lite or Gold plan to remove watermarks.',
                        'upgrade_required': True
                    }), 400
                
                # Free users can change watermark type, so force enabled = True
                watermark_enabled = True
            
            # Validate watermark type
            valid_types = ['diagonal', 'bottom', 'centered']
            if watermark_type not in valid_types:
                logger.error(f"Invalid watermark type provided: {watermark_type}")
                return jsonify({
                    'success': False,
                    'message': f'Invalid watermark type. Available types: {", ".join(valid_types)}'
                }), 400
            
            # Update shopkeeper settings
            old_enabled = shopkeeper.watermark_enabled
            old_type = shopkeeper.watermark_type
            
            shopkeeper.watermark_enabled = watermark_enabled
            shopkeeper.watermark_type = watermark_type
            db.session.commit()
            
            # Determine success message
            if old_type != watermark_type and old_enabled == watermark_enabled:
                message = f'Watermark style updated to {watermark_type.title()}'
            elif old_enabled != watermark_enabled and old_type == watermark_type:
                message = f'Watermark {"enabled" if watermark_enabled else "disabled"}'
            else:
                message = f'Watermark updated: {watermark_type.title()} style, {"enabled" if watermark_enabled else "disabled"}'
            
            logger.info(f"Watermark settings updated successfully for shopkeeper {shopkeeper.shopkeeper_id}")
            
            return jsonify({
                'success': True,
                'message': message,
                'watermark_enabled': watermark_enabled,
                'watermark_type': watermark_type,
                'subscription_plan': shopkeeper.subscription_plan
            })
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating watermark settings: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'An error occurred while updating watermark settings. Please try again.'
            }), 500



    @bp.route('/payment-webhook', methods=['POST'])
    def payment_webhook():
        """
        Production-level Razorpay webhook handler.
        Handles payment status updates with proper security and idempotency.
        """
        try:
            # Get raw payload and signature
            payload = request.get_data(as_text=True)
            signature = request.headers.get('X-Razorpay-Signature', '')
            
            # Validate webhook signature
            if not PaymentService.validate_webhook_signature(payload, signature):
                logger.warning("Invalid webhook signature received")
                return jsonify({'error': 'Invalid signature'}), 401
            
            # Parse webhook data
            import json
            webhook_data = json.loads(payload)
            event_type = webhook_data.get('event')
            
            # Use IST for webhook ID timestamp
            from ..services.payment_service import PaymentService
            ist_timestamp = int(PaymentService._get_ist_now().timestamp())
            webhook_id = webhook_data.get('event_id', f"webhook_{ist_timestamp}")
            
            logger.info(f"Received webhook event: {event_type}, ID: {webhook_id}")
            
            # Handle different event types
            if event_type == 'payment.captured':
                return handle_payment_captured_webhook(webhook_data, webhook_id)
            elif event_type == 'payment.failed':
                return handle_payment_failed_webhook(webhook_data, webhook_id)
            elif event_type == 'order.paid':
                return handle_order_paid_webhook(webhook_data, webhook_id)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return jsonify({'status': 'ignored'}), 200
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return jsonify({'error': 'Invalid JSON'}), 400
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return jsonify({'error': 'Webhook processing failed'}), 500
    
    def handle_payment_captured_webhook(webhook_data, webhook_id):
        """Handle payment.captured webhook event."""
        try:
            payment_entity = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            payment_id = payment_entity.get('id')
            
            if not order_id:
                return jsonify({'error': 'Missing order_id'}), 400
            
            # Find payment record
            from app.models import SubscriptionPayment
            payment_record = SubscriptionPayment.query.filter_by(
                razorpay_order_id=order_id
            ).first()
            
            if not payment_record:
                logger.warning(f"Payment record not found for order {order_id}")
                return jsonify({'error': 'Payment record not found'}), 404
            
            # Check for duplicate processing (idempotency)
            from app.models import PaymentAuditLog
            existing_log = PaymentAuditLog.query.filter_by(
                payment_id=payment_record.payment_id,
                webhook_event_id=webhook_id
            ).first()
            
            if existing_log:
                logger.info(f"Webhook {webhook_id} already processed")
                return jsonify({'status': 'already_processed'}), 200
            
            # Update payment status if not already captured
            if payment_record.status != 'captured':
                old_status = payment_record.status
                payment_record.status = 'captured'
                payment_record.webhook_verified = True
                payment_record.razorpay_payment_id = payment_id
                payment_record.updated_at = PaymentService._get_ist_naive_now()
                
                # Update shopkeeper subscription
                shopkeeper = payment_record.shopkeeper
                if shopkeeper:
                    from ..services import SubscriptionService
                    SubscriptionService.update_plan_with_payment_validation(shopkeeper, payment_record.plan_type)
                    shopkeeper.subscription_expires_at = PaymentService._get_ist_naive_now() + timedelta(days=30)
                    shopkeeper.last_payment_id = payment_record.payment_id
                
                db.session.commit()
                
                # Create audit log
                PaymentService._create_audit_log(
                    payment_record.payment_id,
                    old_status=old_status,
                    new_status='captured',
                    change_reason='Payment captured via webhook',
                    webhook_event_id=webhook_id
                )
                
                logger.info(f"Payment {payment_id} captured via webhook")
            
            return jsonify({'status': 'success'}), 200
            
        except Exception as e:
            logger.error(f"Error in payment captured webhook: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Processing failed'}), 500
    
    def handle_payment_failed_webhook(webhook_data, webhook_id):
        """Handle payment.failed webhook event."""
        try:
            payment_entity = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id')
            error_description = payment_entity.get('error_description', 'Payment failed')
            
            if not order_id:
                return jsonify({'error': 'Missing order_id'}), 400
            
            # Process the failure
            result = PaymentService.handle_payment_failure(order_id, error_description)
            
            if result['success']:
                # Create audit log with webhook info
                from app.models import SubscriptionPayment
                payment_record = SubscriptionPayment.query.filter_by(
                    razorpay_order_id=order_id
                ).first()
                
                if payment_record:
                    PaymentService._create_audit_log(
                        payment_record.payment_id,
                        old_status='created',
                        new_status='failed',
                        change_reason=f'Payment failed via webhook: {error_description}',
                        webhook_event_id=webhook_id
                    )
                
                logger.info(f"Payment failure processed for order {order_id}")
                return jsonify({'status': 'success'}), 200
            else:
                return jsonify({'error': 'Failed to process payment failure'}), 500
                
        except Exception as e:
            logger.error(f"Error in payment failed webhook: {str(e)}")
            return jsonify({'error': 'Processing failed'}), 500
    
    def handle_order_paid_webhook(webhook_data, webhook_id):
        """Handle order.paid webhook event (backup verification)."""
        try:
            order_entity = webhook_data.get('payload', {}).get('order', {}).get('entity', {})
            order_id = order_entity.get('id')
            
            if not order_id:
                return jsonify({'error': 'Missing order_id'}), 400
            
            # This is a backup check - the payment.captured event is the primary handler
            from app.models import SubscriptionPayment
            payment_record = SubscriptionPayment.query.filter_by(
                razorpay_order_id=order_id
            ).first()
            
            if payment_record and payment_record.status == 'created':
                logger.info(f"Order {order_id} paid but payment not captured yet - waiting for payment.captured event")
            
            return jsonify({'status': 'acknowledged'}), 200
            
        except Exception as e:
            logger.error(f"Error in order paid webhook: {str(e)}")
            return jsonify({'error': 'Processing failed'}), 500
