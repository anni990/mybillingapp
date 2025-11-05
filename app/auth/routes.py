from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, bcrypt, login_manager
from app.models import User,Shopkeeper,CharteredAccountant 
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session
from .utils import redirect_to_dashboard

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

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

# Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

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
                contact_number=''
            )
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

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear all session data including remember cookies
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
