from flask import Blueprint, render_template

home_bp = Blueprint('home', __name__, url_prefix='/')

@home_bp.route('/')
def index():
    return render_template('home/index.html')

@home_bp.route('/features')
def features():
    return render_template('home/features.html')

@home_bp.route('/pricing')
def pricing():
    return render_template('home/pricing.html')

@home_bp.route('/about')
def about():
    return render_template('home/about.html')