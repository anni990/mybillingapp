from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt, login_manager
from app.models import User,Shopkeeper,CharteredAccountant 
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session
from .utils import redirect_to_dashboard
from authlib.integrations.flask_client import OAuth
import os

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.shopkeeper.services.watermark_service import WatermarkService

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('shopkeeper', 'Shopkeeper'), ('CA', 'Chartered Accountant')], validators=[DataRequired()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class GoogleRoleForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    role = SelectField('Role', choices=[('shopkeeper', 'Shopkeeper'), ('CA', 'Chartered Accountant')], validators=[DataRequired()])
    submit = SubmitField('Complete Registration')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different username.')

# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with app context"""
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/')
def auth_root():
    # The before_request handler already redirects authenticated users
    # No need to check again here
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # The before_request handler already redirects authenticated users
    # No need to check again here
    
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_pw,
            role=form.role.data
        )
        db.session.add(user)
        db.session.flush()  # Get user_id before commit
        # If registering as shopkeeper, create Shopkeeper profile
        if form.role.data == 'shopkeeper':
            # from app.models import Shopkeeper
            shopkeeper = Shopkeeper(
                user_id=user.user_id,
                shop_name=form.username.data + "'s Shop",  # Placeholder, can be edited later
                domain='',
                address='',
                gst_number='',
                contact_number='',
                subscription_plan='free'  # Default to free plan
            )
            # Initialize watermark settings based on subscription plan
            WatermarkService.initialize_watermark_for_new_shopkeeper(shopkeeper)
            db.session.add(shopkeeper)
        elif form.role.data == 'CA':
            # Add logic for creating a CharteredAccountant profile
            ca = CharteredAccountant(
                user_id=user.user_id,
                firm_name=form.username.data + "'s Firm", # Placeholder
                area="Not specified", # Placeholder
                contact_number="Not specified" # Placeholder
            )
            db.session.add(ca)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # The before_request handler already redirects authenticated users
    # No need to check again here
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            # Check if remember me checkbox was checked
            remember = bool(request.form.get('remember'))
            login_user(user, remember=remember)
            
            # Make session permanent if remember me is checked
            if remember:
                session.permanent = True
                # Optionally refresh session lifetime
                if hasattr(current_app.config, 'PERMANENT_SESSION_LIFETIME'):
                    session.permanent_session_lifetime = current_app.config['PERMANENT_SESSION_LIFETIME']
            
            flash('Logged in successfully.', 'success')
            # Redirect based on role using the utility function
            return redirect_to_dashboard()
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@auth_bp.route('/google')
def google_login():
    """Initiate Google OAuth login"""
    # Ensure redirect URI uses the same host as the request
    redirect_uri = url_for('auth.google_callback', _external=True)
    current_app.logger.info(f"Google OAuth redirect URI: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        if not token:
            flash('Google authentication was cancelled or failed. Please try again.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Get user info from Google
        userinfo = token.get('userinfo')
        if not userinfo:
            # Try alternative method to get user info
            try:
                resp = oauth.google.get('userinfo', token=token)
                userinfo = resp.json()
            except Exception:
                flash('Failed to get user information from Google. Please try again.', 'danger')
                return redirect(url_for('auth.login'))
        
        email = userinfo.get('email')
        google_id = userinfo.get('sub')
        name = userinfo.get('name')
        avatar = userinfo.get('picture')
        
        if not email or not google_id:
            flash('Invalid user information from Google. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # User exists - link Google account if not already linked
            if not existing_user.google_id:
                existing_user.google_id = google_id
                existing_user.oauth_provider = 'google'
                existing_user.avatar_url = avatar
                db.session.commit()
                flash(f'Your Google account has been linked successfully!', 'success')
            else:
                flash('Welcome back!', 'success')
            
            login_user(existing_user)
            return redirect_to_dashboard()
        
        else:
            # New user - store info in session for role selection
            session['google_user_info'] = {
                'email': email,
                'google_id': google_id,
                'name': name,
                'avatar': avatar
            }
            return redirect(url_for('auth.google_setup'))
    
    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        
        # Handle specific OAuth errors
        error_msg = str(e).lower()
        if 'access_blocked' in error_msg or 'blocked' in error_msg:
            flash('Google OAuth access is currently blocked. Please contact the administrator or try regular login.', 'warning')
        elif 'redirect_uri_mismatch' in error_msg:
            flash('OAuth configuration error. Please contact the administrator.', 'danger')
        elif 'invalid_client' in error_msg:
            flash('OAuth client configuration error. Please contact the administrator.', 'danger')
        else:
            flash('Google authentication failed. Please try again or use regular login.', 'danger')
        
        return redirect(url_for('auth.login'))

@auth_bp.route('/google/setup', methods=['GET', 'POST'])
def google_setup():
    """Complete Google OAuth registration with role selection"""
    # Check if user info exists in session
    google_user_info = session.get('google_user_info')
    if not google_user_info:
        flash('Session expired. Please try logging in with Google again.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = GoogleRoleForm()
    
    # Pre-fill username with Google name
    if not form.username.data:
        form.username.data = google_user_info.get('name', '').replace(' ', '').lower()
    
    if form.validate_on_submit():
        try:
            # Create new user
            user = User(
                username=form.username.data,
                email=google_user_info['email'],
                password_hash='',  # Empty for OAuth users
                role=form.role.data,
                google_id=google_user_info['google_id'],
                oauth_provider='google',
                avatar_url=google_user_info['avatar']
            )
            db.session.add(user)
            db.session.flush()  # Get user_id
            
            # Create role-specific profile
            if form.role.data == 'shopkeeper':
                shopkeeper = Shopkeeper(
                    user_id=user.user_id,
                    shop_name=form.username.data + "'s Shop",
                    domain='',
                    address='',
                    gst_number='',
                    contact_number='',
                    subscription_plan='free'
                )
                # Initialize watermark settings based on subscription plan
                WatermarkService.initialize_watermark_for_new_shopkeeper(shopkeeper)
                db.session.add(shopkeeper)
            
            elif form.role.data == 'CA':
                ca = CharteredAccountant(
                    user_id=user.user_id,
                    firm_name=form.username.data + "'s Firm",
                    area="Not specified",
                    contact_number="Not specified"
                )
                db.session.add(ca)
            
            db.session.commit()
            
            # Clear session and log in user
            session.pop('google_user_info', None)
            login_user(user)
            
            flash('Account created successfully with Google! Welcome to MyBillingApp.', 'success')
            return redirect_to_dashboard()
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating Google user: {str(e)}")
            flash('Error creating account. Please try again.', 'danger')
    
    return render_template('auth/google_setup.html', 
                         form=form, 
                         google_user_info=google_user_info)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear all session data including remember cookies
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
