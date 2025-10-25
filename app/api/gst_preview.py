"""
GST Preview API endpoint for real-time calculations.
Provides frontend with accurate GST calculations without storing data.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from decimal import Decimal, InvalidOperation
import traceback

from app.utils.gst import calc_line, generate_gst_summary, calculate_bill_totals, validate_gst_rate
from ..shopkeeper.utils import shopkeeper_required

# Create blueprint for preview endpoints
preview_bp = Blueprint('preview', __name__, url_prefix='/api/preview')


@preview_bp.route('/gst', methods=['POST'])
def preview_gst():
    """
    Preview GST calculations for bill items without saving to database.
    
    Expected JSON payload:
    {
        "items": [
            {
                "unit_price": "118.00",
                "qty": 2,
                "gst_rate": "18.00",
                "discount_percent": "10.00",
                "mode": "INCLUSIVE",
                "product_name": "Mobile Phone",
                "hsn_code": "8517"
            },
            ...
        ],
        "bill_mode": "EXCLUSIVE"  // Default mode for items without specific mode
    }
    
    Returns:
    {
        "success": true,
        "lines": [
            {
                "unit_price_base": "100.00",
                "line_base_total": "200.00",
                "discount_amount": "20.00",
                "taxable_amount": "180.00",
                "cgst_rate": "9.00",
                "sgst_rate": "9.00",
                "cgst_amount": "16.20",
                "sgst_amount": "16.20",
                "total_gst": "32.40",
                "final_total": "212.40",
                "gst_rate": "18.00",
                "mode": "INCLUSIVE"
            },
            ...
        ],
        "summary": {
            "18.00": {
                "taxable_amount": "180.00",
                "cgst_amount": "16.20",
                "sgst_amount": "16.20",
                "total_gst": "32.40",
                "final_total": "212.40"
            }
        },
        "totals": {
            "total_taxable_amount": "180.00",
            "total_cgst_amount": "16.20",
            "total_sgst_amount": "16.20",
            "total_gst_amount": "32.40",
            "grand_total": "212.40"
        }
    }
    """
    try:
        data = request.get_json() or {}
        # Support both 'items' and 'line_items' for backward compatibility
        items = data.get('items', data.get('line_items', []))
        bill_mode = data.get('bill_mode', data.get('gst_mode', 'EXCLUSIVE'))
        
        if not items:
            return jsonify({
                'success': False,
                'error': 'No items provided for calculation'
            }), 400
        
        calculated_items = []
        errors = []
        
        for i, item in enumerate(items):
            try:
                # Extract and validate item data with flexible field names
                unit_price = item.get('unit_price', item.get('price', '0'))
                qty = int(item.get('qty', item.get('quantity', 1)))
                gst_rate = item.get('gst_rate', '0')
                discount_percent = item.get('discount_percent', '0')
                mode = item.get('mode', bill_mode).upper()
                
                # Validate inputs
                if qty <= 0:
                    errors.append(f"Item {i+1}: Quantity must be greater than 0")
                    continue
                
                try:
                    Decimal(str(unit_price))
                    Decimal(str(gst_rate))
                    Decimal(str(discount_percent))
                except InvalidOperation:
                    errors.append(f"Item {i+1}: Invalid numeric values")
                    continue
                
                if not validate_gst_rate(gst_rate, allow_custom=True):
                    errors.append(f"Item {i+1}: Invalid GST rate: {gst_rate}")
                    continue
                
                if mode not in ['INCLUSIVE', 'EXCLUSIVE']:
                    errors.append(f"Item {i+1}: Invalid mode. Must be INCLUSIVE or EXCLUSIVE")
                    continue
                
                # Calculate GST for this line
                calc_result = calc_line(
                    price=unit_price,
                    qty=qty,
                    gst_rate=gst_rate,
                    discount_percent=discount_percent,
                    mode=mode
                )
                
                # Add item metadata
                calc_result['item_index'] = i
                calc_result['product_name'] = item.get('product_name', '')
                calc_result['hsn_code'] = item.get('hsn_code', '')
                
                calculated_items.append(calc_result)
                
            except Exception as e:
                current_app.logger.error(f"Error calculating item {i+1}: {str(e)}")
                errors.append(f"Item {i+1}: Calculation error - {str(e)}")
        
        if errors and not calculated_items:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Generate summary and totals
        gst_summary = generate_gst_summary(calculated_items)
        bill_totals = calculate_bill_totals(calculated_items)
        
        # Convert Decimal values to strings for JSON serialization
        def decimal_to_str(obj):
            if isinstance(obj, dict):
                return {k: decimal_to_str(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [decimal_to_str(item) for item in obj]
            elif isinstance(obj, Decimal):
                return str(obj)
            return obj
        
        response_data = {
            'success': True,
            'lines': decimal_to_str(calculated_items),
            'summary': decimal_to_str(gst_summary),
            'totals': decimal_to_str(bill_totals)
        }
        
        if errors:
            response_data['warnings'] = errors
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"GST preview error: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Internal server error during GST calculation'
        }), 500


@preview_bp.route('/validate-gst-rate', methods=['POST'])
@login_required
@shopkeeper_required
def validate_gst_rate_endpoint():
    """
    Validate a single GST rate.
    
    Expected JSON payload:
    {
        "gst_rate": "18.00",
        "allow_custom": true
    }
    
    Returns:
    {
        "success": true,
        "valid": true,
        "rate": "18.00",
        "type": "standard"  // or "custom"
    }
    """
    try:
        data = request.get_json() or {}
        gst_rate = data.get('gst_rate', '0')
        allow_custom = data.get('allow_custom', False)
        
        try:
            rate_decimal = Decimal(str(gst_rate))
        except (InvalidOperation, ValueError):
            return jsonify({
                'success': True,
                'valid': False,
                'error': 'Invalid numeric value'
            })
        
        is_valid = validate_gst_rate(rate_decimal, allow_custom=allow_custom)
        
        # Determine rate type
        rate_type = 'standard'
        if is_valid and allow_custom:
            from app.utils.gst import STANDARD_GST_RATES
            if rate_decimal not in STANDARD_GST_RATES:
                rate_type = 'custom'
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'rate': str(rate_decimal),
            'type': rate_type if is_valid else None
        })
        
    except Exception as e:
        current_app.logger.error(f"GST rate validation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500