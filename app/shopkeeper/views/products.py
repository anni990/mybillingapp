"""
Product management routes for shopkeeper.
Extracted from original routes.py - maintaining all original logic.
"""
from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from decimal import Decimal

from ..utils import shopkeeper_required, get_current_shopkeeper
from app.models import Product, Shopkeeper
from app.extensions import db


def register_routes(bp):
    """Register product management routes to the blueprint."""
 

    # Products & Stock (already implemented above)
    @bp.route('/products', methods=['GET'])
    @login_required
    @shopkeeper_required
    def products_stock():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id).all() if shopkeeper else []
        return render_template('shopkeeper/products_stock.html', products=products)

    @bp.route('/products/add', methods=['POST'])
    @login_required
    @shopkeeper_required
    def add_product():
        shopkeeper = Shopkeeper.query.filter_by(user_id=current_user.user_id).first()
        if not shopkeeper:
            flash('Shopkeeper profile not found.', 'danger')
            return redirect(url_for('shopkeeper.products_stock'))
        name = request.form.get('product_name')
        barcode = request.form.get('barcode')
        price = request.form.get('price')
        gst_rate = request.form.get('gst_rate')
        hsn_code = request.form.get('hsn_code')
        stock_qty = request.form.get('stock_qty')
        low_stock_threshold = request.form.get('low_stock_threshold')
        if not name or not price:
            flash('Product name and price are required.', 'danger')
            return redirect(url_for('shopkeeper.products_stock'))
        product = Product(
            shopkeeper_id=shopkeeper.shopkeeper_id,
            product_name=name,
            barcode=barcode,
            price=price,
            gst_rate=gst_rate,
            hsn_code=hsn_code,
            stock_qty=stock_qty or 0,
            low_stock_threshold=low_stock_threshold or 0
        )
        db.session.add(product)
        db.session.commit()
        flash('Product added successfully.', 'success')
        return redirect(url_for('shopkeeper.products_stock'))

    @bp.route('/products/edit/<int:product_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def edit_product(product_id):
        product = Product.query.get_or_404(product_id)
        if product.shopkeeper.user_id != current_user.user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('shopkeeper.products_stock'))
        
        # Update all product fields
        product.product_name = request.form.get('product_name')
        product.barcode = request.form.get('barcode')
        product.price = request.form.get('price')
        product.gst_rate = request.form.get('gst_rate')
        product.hsn_code = request.form.get('hsn_code')
        product.stock_qty = request.form.get('stock_qty')
        product.low_stock_threshold = request.form.get('low_stock_threshold')
        
        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('shopkeeper.products_stock'))

    @bp.route('/products/delete/<int:product_id>', methods=['POST'])
    @login_required
    @shopkeeper_required
    def delete_product(product_id):
        product = Product.query.get_or_404(product_id)
        if product.shopkeeper.user_id != current_user.user_id:
            flash('Access denied.', 'danger')
            return redirect(url_for('shopkeeper.products_stock'))
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully.', 'success')
        return redirect(url_for('shopkeeper.products_stock'))
