"""
CA Bill Scan Service - Handle bill scanning for CA clients.
Uses Gemini AI for bill data extraction.
"""
import base64
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import logging

import google.generativeai as genai
from flask import current_app

from app.models import Bill, BillItem, Shopkeeper, CAConnection, Product
from app.extensions import db


class CABillScanService:
    """Service class for CA bill scanning operations."""
    
    @staticmethod
    def configure_gemini():
        """Configure Gemini AI with API key."""
        api_key = current_app.config.get('GEMINI_API_KEY')
        if not api_key:
            return False
        try:
            genai.configure(api_key=api_key)
            return True
        except Exception:
            return False
    
    @staticmethod
    def extract_bill_data(image_data: bytes, file_type: str) -> Dict:
        """Extract bill data from image using Gemini AI."""
        try:
            # Check if Gemini is configured
            if not CABillScanService.configure_gemini():
                return {
                    'success': False, 
                    'message_type': 'warning',
                    'error': 'This feature is coming soon!'
                }
            
            # Convert image to base64
            if file_type.lower() in ['jpg', 'jpeg', 'png']:
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                mime_type = f"image/{file_type.lower()}"
            else:
                return {'success': False, 'error': 'Unsupported file type'}
            
            # Create model
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Structured prompt for bill extraction
            prompt = """
            Extract the following information from this sales bill/invoice image and return ONLY a valid JSON object:
            
            {
                "vendor_info": {
                    "vendor_name": "string",
                    "vendor_address": "string",
                    "vendor_contact": "string",
                    "vendor_gst": "string"
                },
                "bill_info": {
                    "bill_number": "string",
                    "bill_date": "YYYY-MM-DD",
                    "total_amount": "number"
                },
                "customer_info": {
                    "customer_name": "string",
                    "customer_contact": "string",
                    "customer_gst": "string"
                },
                "items": [
                    {
                        "product_name": "string",
                        "hsn_code": "string",
                        "quantity": "number",
                        "unit_price": "number",
                        "gst_rate": "number",
                        "total_amount": "number"
                    }
                ]
            }
            
            If any field is not available, use null. Ensure all numeric values are valid numbers.
            """
            
            # Generate content
            image_part = {
                'mime_type': mime_type,
                'data': image_base64
            }
            
            response = model.generate_content([prompt, image_part])
            
            if response.text:
                # Clean the response text
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                # Parse JSON
                extracted_data = json.loads(response_text.strip())
                
                # Validate and normalize data
                normalized_data = CABillScanService._normalize_extracted_data(extracted_data)
                
                return {
                    'success': True,
                    'data': normalized_data
                }
            else:
                return {'success': False, 'error': 'No response from AI'}
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return {'success': False, 'error': f'Invalid JSON response: {e}'}
        except Exception as e:
            logging.error(f"Bill extraction error: {e}")
            return {'success': False, 'error': f'Extraction failed: {e}'}
    
    @staticmethod
    def _normalize_extracted_data(data: Dict) -> Dict:
        """Normalize and validate extracted data."""
        try:
            # Convert numeric strings to proper types
            if 'bill_info' in data and data['bill_info']:
                bill_info = data['bill_info']
                for field in ['total_amount']:
                    if field in bill_info and bill_info[field] is not None:
                        try:
                            bill_info[field] = float(str(bill_info[field]).replace(',', ''))
                        except (ValueError, AttributeError):
                            bill_info[field] = 0.0
            
            # Normalize items
            if 'items' in data and data['items']:
                for item in data['items']:
                    for field in ['quantity', 'unit_price', 'gst_rate', 'total_amount']:
                        if field in item and item[field] is not None:
                            try:
                                item[field] = float(str(item[field]).replace(',', ''))
                            except (ValueError, AttributeError):
                                item[field] = 0.0
            
            return data
            
        except Exception as e:
            logging.error(f"Data normalization error: {e}")
            return data
    
    @staticmethod
    def save_scanned_bill(ca_id: int, shopkeeper_id: int, extracted_data: Dict, 
                         scanned_by_ca: bool = True) -> Tuple[Bill, bool]:
        """Save scanned bill data to database."""
        try:
            # Verify CA has access to this shopkeeper
            if not CABillScanService._verify_ca_access(ca_id, shopkeeper_id):
                return None, False
            
            bill_info = extracted_data.get('bill_info', {})
            customer_info = extracted_data.get('customer_info', {})
            
            # Helper function to safely convert to Decimal
            def safe_decimal(value, default=0):
                if value is None or value == '':
                    return Decimal(str(default))
                try:
                    # Remove commas and convert to string first
                    clean_value = str(value).replace(',', '').strip()
                    if clean_value == '' or clean_value.lower() in ['null', 'none']:
                        return Decimal(str(default))
                    return Decimal(clean_value)
                except (ValueError, TypeError, AttributeError):
                    return Decimal(str(default))
            
            # Helper function to safely convert to int
            def safe_int(value, default=1):
                if value is None or value == '':
                    return default
                try:
                    clean_value = str(value).replace(',', '').strip()
                    if clean_value == '' or clean_value.lower() in ['null', 'none']:
                        return default
                    return int(float(clean_value))  # Convert via float first to handle decimals
                except (ValueError, TypeError, AttributeError):
                    return default
            
            # Parse and validate bill date
            bill_date = datetime.now()
            if bill_info.get('bill_date'):
                try:
                    bill_date = datetime.strptime(bill_info['bill_date'], '%Y-%m-%d')
                except (ValueError, TypeError):
                    # Try other common date formats
                    try:
                        bill_date = datetime.strptime(bill_info['bill_date'], '%d/%m/%Y')
                    except (ValueError, TypeError):
                        try:
                            bill_date = datetime.strptime(bill_info['bill_date'], '%d-%m-%Y')
                        except (ValueError, TypeError):
                            bill_date = datetime.now()
            
            # Calculate payment status
            total_amt = safe_decimal(bill_info.get('total_amount', 0))
            paid_amt = safe_decimal(bill_info.get('total_amount', 0))
            # due_amt = safe_decimal(bill_info.get('due_amount', 0))
            due_amt = safe_decimal(0)
            
            # If due amount is not provided, calculate it
            if due_amt == 0 and total_amt > 0:
                due_amt = total_amt - paid_amt
                if due_amt < 0:
                    due_amt = Decimal('0')
            
            payment_status = 'paid' if due_amt == 0 else ('partial' if paid_amt > 0 else 'unpaid')
            
            # Create bill
            bill = Bill(
                shopkeeper_id=shopkeeper_id,
                bill_number=bill_info.get('bill_number', f"SCAN-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
                customer_name=customer_info.get('customer_name', 'Walk-in Customer') or 'Walk-in Customer',
                customer_contact=customer_info.get('customer_contact') or None,
                customer_gstin=customer_info.get('customer_gst') or None,
                bill_date=bill_date,
                gst_type='GST',  # Required field - always GST for scanned bills
                gst_mode='EXCLUSIVE',  # Default GST mode
                total_amount=total_amt,
                paid_amount=paid_amt,
                due_amount=due_amt,
                payment_status=payment_status
            )
            
            db.session.add(bill)
            db.session.flush()  # Get bill ID
            
            # Create bill items
            items = extracted_data.get('items', [])
            for item_data in items:
                if not item_data:  # Skip empty items
                    continue
                    
                product_name = item_data.get('product_name', 'Unknown Product') or 'Unknown Product'
                hsn_code = item_data.get('hsn_code') or None
                quantity = safe_int(item_data.get('quantity', 1))
                unit_price = safe_decimal(item_data.get('unit_price', 0))
                gst_rate = safe_decimal(item_data.get('gst_rate', 0))
                item_total = safe_decimal(item_data.get('total_amount', 0))
                
                # If item total is not provided, calculate it
                if item_total == 0 and unit_price > 0 and quantity > 0:
                    item_total = unit_price * Decimal(str(quantity))
                
                # Calculate GST breakdown (CGST = SGST = GST Rate / 2)
                cgst_rate = gst_rate / Decimal('2') if gst_rate > 0 else Decimal('0')
                sgst_rate = cgst_rate
                
                # Calculate taxable amount (assuming exclusive GST)
                if gst_rate > 0:
                    taxable_amount = item_total / (Decimal('1') + (gst_rate / Decimal('100')))
                    total_gst_amount = item_total - taxable_amount
                    cgst_amount = total_gst_amount / Decimal('2')
                    sgst_amount = cgst_amount
                else:
                    taxable_amount = item_total
                    total_gst_amount = Decimal('0')
                    cgst_amount = Decimal('0')
                    sgst_amount = Decimal('0')
                
                bill_item = BillItem(
                    bill_id=bill.bill_id,
                    custom_product_name=product_name,  # Use custom product since we don't have product_id
                    custom_gst_rate=gst_rate,
                    custom_hsn_code=hsn_code,
                    quantity=quantity,
                    price_per_unit=unit_price,
                    total_price=item_total,
                    discount_percent=Decimal('0'),  # No discount for scanned bills
                    discount_amount=Decimal('0'),
                    taxable_amount=taxable_amount,
                    cgst_rate=cgst_rate,
                    sgst_rate=sgst_rate,
                    cgst_amount=cgst_amount,
                    sgst_amount=sgst_amount,
                    total_gst_amount=total_gst_amount
                )
                db.session.add(bill_item)
            
            db.session.commit()
            return bill, True
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving scanned bill: {e}")
            import traceback
            traceback.print_exc()
            return None, False
    
    @staticmethod
    def _verify_ca_access(ca_id: int, shopkeeper_id: int) -> bool:
        """Verify CA has access to the shopkeeper."""
        connection = CAConnection.query.filter_by(
            ca_id=ca_id,
            shopkeeper_id=shopkeeper_id,
            status='approved'
        ).first()
        return connection is not None
    
    @staticmethod
    def get_ca_client_options(ca_id: int) -> List[Dict]:
        """Get client options for dropdown selection."""
        connections = CAConnection.query.filter_by(
            ca_id=ca_id,
            status='approved'
        ).all()
        
        clients = []
        for conn in connections:
            shop = Shopkeeper.query.get(conn.shopkeeper_id)
            if shop:
                clients.append({
                    'shopkeeper_id': shop.shopkeeper_id,
                    'shop_name': shop.shop_name,
                    'owner_name': shop.owner_name or 'N/A'
                })
        
        return clients
