"""
CA connections and marketplace routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json

from ..utils import shopkeeper_required
from app.models import (
    Shopkeeper, CharteredAccountant, ShopConnection, CAConnection, 
    EmployeeClient, CAEmployee
)
from app.extensions import db


def mask_contact_number(contact):
    """Mask contact number to show only first 2 and last 2 digits."""
    if not contact or len(contact) < 4:
        return contact
    return contact[:2] + '*' * (len(contact) - 4) + contact[-2:]


def mask_email(email):
    """Mask email to show only first 2 characters and domain."""
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return email
    return local[:2] + '*' * (len(local) - 2) + '@' + domain


def parse_json_field(json_str):
    """Parse JSON string and return list, return empty list if invalid."""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return []


def format_experience(experience):
    """Format experience years into readable string."""
    if not experience:
        return "Not specified"
    
    exp_map = {
        1: "1-2 years",
        3: "3-5 years", 
        6: "6-10 years",
        11: "11-15 years",
        16: "16-20 years",
        21: "20+ years"
    }
    
    return exp_map.get(experience, f"{experience} years")


def format_domain_expertise(expertise_list):
    """Format domain expertise list into readable strings."""
    expertise_map = {
        'taxation': 'Taxation',
        'audit': 'Audit & Assurance',
        'financial_planning': 'Financial Planning',
        'corporate_law': 'Corporate Law',
        'gst': 'GST Compliance',
        'income_tax': 'Income Tax',
        'company_formation': 'Company Formation',
        'accounting': 'Accounting Services',
        'compliance': 'Regulatory Compliance',
        'investment_advisory': 'Investment Advisory',
        'mergers_acquisitions': 'Mergers & Acquisitions',
        'forensic_accounting': 'Forensic Accounting'
    }
    
    return [expertise_map.get(exp, exp.title()) for exp in expertise_list]


def format_industries_served(industries_list):
    """Format industries served list into readable strings."""
    industries_map = {
        'retail': 'Retail & E-commerce',
        'manufacturing': 'Manufacturing',
        'healthcare': 'Healthcare',
        'real_estate': 'Real Estate',
        'hospitality': 'Hospitality',
        'education': 'Education',
        'technology': 'Technology',
        'agriculture': 'Agriculture',
        'automotive': 'Automotive',
        'textiles': 'Textiles',
        'pharmaceuticals': 'Pharmaceuticals',
        'food_beverage': 'Food & Beverage',
        'construction': 'Construction',
        'logistics': 'Logistics & Transportation',
        'financial_services': 'Financial Services',
        'startups': 'Startups & SMEs'
    }
    
    return [industries_map.get(industry, industry.title()) for industry in industries_list]


def register_routes(bp):
    """Register CA connection routes to the blueprint."""
    
    @bp.route('/ca_marketplace', methods=['GET', 'POST'])
    @login_required
    @shopkeeper_required
    def ca_marketplace():
        """CA marketplace view - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        shop_name = shopkeeper.shop_name

        # First check if shopkeeper has any approved CA connection
        approved_connection = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='approved'
        ).first()
        
        # If there's an approved connection, only get that CA's details
        if approved_connection:
            connected_ca = CharteredAccountant.query.get(approved_connection.ca_id)
            cas = [connected_ca] if connected_ca else []
        else:
            # If no approved connection, show all CAs
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
        
        # Get connection status for each CA
        connections = {c.ca_id: c for c in ShopConnection.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all()}
        
        # Get pending requests for statistics
        pending_requests = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='pending'
        ).all()
        
        # Get connected CA if exists
        connected_ca = None
        if approved_connection:
            connected_ca = CharteredAccountant.query.get(approved_connection.ca_id)
        
        # Get unique areas for filter
        unique_areas = db.session.query(CharteredAccountant.area).distinct().filter(
            CharteredAccountant.area.isnot(None)
        ).all()
        unique_areas = [area[0] for area in unique_areas if area[0]]
        
        # Enhance CA data with formatted fields
        enhanced_cas = []
        for ca in cas:
            ca_data = {
                'ca': ca,
                'domain_expertise': format_domain_expertise(parse_json_field(ca.domain_expertise)),
                'industries_served': format_industries_served(parse_json_field(ca.industries_served)),
                'experience_formatted': format_experience(ca.experience),
                'masked_contact': mask_contact_number(ca.contact_number),
                'masked_email': mask_email(ca.ca_email_id)
            }
            enhanced_cas.append(ca_data)
        
        return render_template('shopkeeper/ca_marketplace.html', 
                             shop_name=shop_name,
                             cas=enhanced_cas, 
                             connections=connections,
                             pending_requests=pending_requests,
                             connected_ca=connected_ca,
                             unique_areas=unique_areas,
                             has_approved_connection=bool(approved_connection))
    
    @bp.route('/ca_profile/<int:ca_id>')
    @login_required
    @shopkeeper_required
    def ca_profile(ca_id):
        """View CA profile - preserves original logic."""
        ca = CharteredAccountant.query.get_or_404(ca_id)
        return render_template('shopkeeper/ca_profile.html', ca=ca)
    
    @bp.route('/request_connection/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def request_connection(ca_id):
        """Request connection to a CA - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        ca = CharteredAccountant.query.get_or_404(ca_id)

        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Check if already connected
        existing_connection = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()

        if existing_connection:
            message = 'You are already connected to this CA.'
            if is_ajax:
                return jsonify({'success': False, 'message': message})
            flash(message, 'info')
            return redirect(url_for('shopkeeper.ca_marketplace'))

        # Check if request already sent
        existing_request = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()

        if existing_request:
            message = 'Connection request already sent to this CA.'
            if is_ajax:
                return jsonify({'success': False, 'message': message})
            flash(message, 'info')
            return redirect(url_for('shopkeeper.ca_marketplace'))

        # Create connection request
        shop_connection = ShopConnection(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='pending'
        )

        db.session.add(shop_connection)
        db.session.commit()

        message = 'Connection request sent successfully!'
        if is_ajax:
            return jsonify({'success': True, 'message': message})
        
        flash(message, 'success')
        return redirect(url_for('shopkeeper.ca_marketplace'))
    
    @bp.route('/my_cas')
    @login_required
    @shopkeeper_required
    def my_cas():
        """View connected CAs - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # Get connected CAs
        ca_connections = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).all()
        
        connected_cas = []
        for connection in ca_connections:
            ca = CharteredAccountant.query.get(connection.ca_id)
            if ca:
                connected_cas.append({
                    'ca': ca,
                    'connection_date': connection.connection_date
                })
        
        # Get pending requests
        pending_requests = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            status='pending'
        ).all()
        
        pending_cas = []
        for request in pending_requests:
            ca = CharteredAccountant.query.get(request.ca_id)
            if ca:
                pending_cas.append({
                    'ca': ca,
                    'request_date': request.request_date
                })
        
        return render_template(
            'shopkeeper/my_cas.html',
            connected_cas=connected_cas,
            pending_cas=pending_cas
        )
    
    @bp.route('/disconnect_ca/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def disconnect_ca(ca_id):
        """Disconnect from a CA - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        # Remove CA connection
        ca_connection = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id
        ).first()
        
        if ca_connection:
            db.session.delete(ca_connection)
        
        # Remove employee connections if any
        employee_connections = EmployeeClient.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id
        ).all()
        
        for emp_conn in employee_connections:
            employee = CAEmployee.query.get(emp_conn.employee_id)
            if employee and employee.ca_id == ca_id:
                db.session.delete(emp_conn)
        
        db.session.commit()
        flash('Successfully disconnected from CA.', 'success')
        return redirect(url_for('shopkeeper.my_cas'))
    
    @bp.route('/cancel_request/<int:ca_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def cancel_request(ca_id):
        """Cancel connection request - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        
        shop_connection = ShopConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='pending'
        ).first()
        
        if shop_connection:
            db.session.delete(shop_connection)
            db.session.commit()
            flash('Connection request cancelled.', 'success')
        else:
            flash('Request not found.', 'error')
        
        return redirect(url_for('shopkeeper.my_cas'))
    
    
    @bp.route('/ca/profile/<int:ca_id>')
    @login_required
    @shopkeeper_required
    def connected_ca_profile(ca_id):
        """View connected CA profile - preserves original logic."""
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        shop_name = shopkeeper.shop_name
        # Verify connection exists
        ca_conn = CAConnection.query.filter_by(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            ca_id=ca_id,
            status='approved'
        ).first()
        
        if not ca_conn:
            flash('No connection found with this CA.', 'danger')
            return redirect(url_for('shopkeeper.dashboard'))
        
        # Get CA details
        ca = CharteredAccountant.query.get_or_404(ca_id)
        
        # Get assigned employees
        assigned_employees = db.session.query(CAEmployee)\
            .join(EmployeeClient, CAEmployee.employee_id == EmployeeClient.employee_id)\
            .filter(EmployeeClient.shopkeeper_id == shopkeeper.shopkeeper_id)\
            .all()
        
        # Prepare enhanced CA data
        ca_data = {
            'ca': ca,
            'domain_expertise': format_domain_expertise(parse_json_field(ca.domain_expertise)),
            'industries_served': format_industries_served(parse_json_field(ca.industries_served)),
            'experience_formatted': format_experience(ca.experience),
            'masked_contact': mask_contact_number(ca.contact_number),
            'masked_email': mask_email(ca.ca_email_id)
        }
        
        return render_template('shopkeeper/connected_ca_profile.html',
            ca_data=ca_data,
            shop_name=shop_name,
            assigned_employees=assigned_employees
        )
    
    @bp.route('/search_cas')
    @login_required
    @shopkeeper_required
    def search_cas():
        """Search CAs - preserves original logic."""
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([])
        
        cas = CharteredAccountant.query.filter(
            CharteredAccountant.ca_name.ilike(f'%{query}%') |
            CharteredAccountant.specialization.ilike(f'%{query}%') |
            CharteredAccountant.city.ilike(f'%{query}%')
        ).limit(10).all()
        
        results = []
        for ca in cas:
            results.append({
                'id': ca.ca_id,
                'name': ca.ca_name,
                'specialization': ca.specialization,
                'city': ca.city,
                'rating': float(ca.rating) if ca.rating else 0,
                'experience': ca.experience_years
            })
        
        return jsonify(results)