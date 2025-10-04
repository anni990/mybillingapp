"""
Profile and document management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, current_app, g
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from ..utils import shopkeeper_required, update_shopkeeper_verification
from app.models import Shopkeeper, CharteredAccountant, CAConnection, ShopConnection
from app.extensions import db


def register_routes(bp):
    """Register profile management routes to the blueprint."""
    

    @bp.route('/profile')
    @login_required
    @shopkeeper_required
    def profile():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        return render_template('shopkeeper/profile.html', shopkeeper=shopkeeper)

    @bp.route('/profile/edit', methods=['GET', 'POST'])
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
            shopkeeper.template_choice = request.form.get('template_choice')
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
