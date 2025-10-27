"""
Gemini AI service for extracting purchase bill information.
"""
import os
import json
import base64
from typing import Dict, List, Optional
import google.generativeai as genai
from flask import current_app


class GeminiService:
    """Service class for interacting with Google's Gemini AI API."""
    
    def __init__(self):
        """Initialize Gemini service with API key from environment."""
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
    
    def extract_purchase_bill_data(self, image_data: bytes, file_type: str) -> Dict:
        """
        Extract purchase bill information from image using Gemini AI.
        
        Args:
            image_data: Binary image data
            file_type: File type (jpg, jpeg, png, pdf)
            
        Returns:
            Dictionary containing extracted bill information
        """
        try:
            # Prepare the prompt for optimal extraction
            prompt = self._get_extraction_prompt()
            
            # Convert image to base64 for API
            if file_type.lower() == 'pdf':
                # For PDF, you might need to convert first page to image
                # This is a simplified approach - you may need pdf2image library
                current_app.logger.warning("PDF processing not fully implemented - treating as image")
            
            # Prepare the image for Gemini
            image_part = {
                "mime_type": f"image/{file_type.lower()}",
                "data": base64.b64encode(image_data).decode()
            }
            
            # Generate content
            response = self.model.generate_content([prompt, image_part])
            
            # Parse the response
            extracted_data = self._parse_response(response.text)
            
            return {
                'success': True,
                'data': extracted_data,
                'raw_response': response.text
            }
            
        except Exception as e:
            current_app.logger.error(f"Gemini API error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _get_extraction_prompt(self) -> str:
        """Get the optimized prompt for bill extraction."""
        return """
        You are an expert at extracting structured data from purchase bills/invoices. 
        Analyze this image and extract ALL the information in the exact JSON format below.
        
        Extract the following information and return ONLY a valid JSON object:
        
        {
            "vendor_info": {
                "name": "Company/Shop name",
                "address": "Full address",
                "gst_number": "GST number if available",
                "phone": "Phone number if available",
                "email": "Email if available"
            },
            "bill_info": {
                "invoice_number": "Invoice/Bill number",
                "date": "Date in YYYY-MM-DD format",
                "total_amount": "Total amount as number",
                "tax_amount": "Tax amount if specified",
                "discount": "Discount amount if any"
            },
            "items": [
                {
                    "name": "Product name",
                    "quantity": "Quantity as number",
                    "unit_price": "Price per unit as number",
                    "total_price": "Total price for this item as number",
                    "gst_rate": "GST rate as number (e.g., 18 for 18%)",
                    "hsn_code": "HSN code if available"
                }
            ]
        }
        
        Rules:
        1. Return ONLY the JSON object, no other text
        2. Use null for missing values
        3. Convert all prices to numbers (remove currency symbols)
        4. Convert quantities to numbers
        5. Date must be in YYYY-MM-DD format
        6. GST rate should be just the number (18, not "18%")
        7. If you can't read something clearly, use null
        8. Extract ALL items from the bill
        """
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse the Gemini response and return structured data."""
        try:
            # Clean the response - remove any markdown formatting
            clean_response = response_text.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]
            
            # Parse JSON
            data = json.loads(clean_response.strip())
            
            # Validate the structure
            self._validate_extracted_data(data)
            
            return data
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON parsing error: {str(e)}")
            current_app.logger.error(f"Raw response: {response_text}")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
    
    def _validate_extracted_data(self, data: Dict) -> None:
        """Validate the extracted data structure."""
        required_keys = ['vendor_info', 'bill_info', 'items']
        
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")
        
        # Validate items structure
        if not isinstance(data['items'], list):
            raise ValueError("Items must be a list")
        
        for item in data['items']:
            if not isinstance(item, dict):
                raise ValueError("Each item must be a dictionary")
            
            # Convert string numbers to actual numbers
            for numeric_field in ['quantity', 'unit_price', 'total_price', 'gst_rate']:
                if item.get(numeric_field) is not None:
                    try:
                        item[numeric_field] = float(item[numeric_field])
                    except (ValueError, TypeError):
                        item[numeric_field] = None
        
        # Convert bill amounts to numbers
        bill_info = data['bill_info']
        for amount_field in ['total_amount', 'tax_amount', 'discount']:
            if bill_info.get(amount_field) is not None:
                try:
                    bill_info[amount_field] = float(bill_info[amount_field])
                except (ValueError, TypeError):
                    bill_info[amount_field] = None


def get_gemini_service() -> GeminiService:
    """Factory function to get Gemini service instance."""
    return GeminiService()