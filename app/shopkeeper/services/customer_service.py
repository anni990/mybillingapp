"""
Customer and ledger management service.
Extracted from original routes.py - maintains all business logic.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from app.models import Customer, CustomerLedger, Bill
from app.extensions import db


class CustomerService:
    """Service class for customer and ledger management."""
    
    @staticmethod
    def create_customer(shopkeeper_user_id: int, customer_data: Dict) -> Tuple[Customer, bool]:
        """Create a new customer."""
        try:
            customer = Customer(
                shopkeeper_id=shopkeeper_user_id,  # Uses user_id for customers
                name=customer_data['name'],
                contact_number=customer_data.get('contact_number'),
                email=customer_data.get('email'),
                address=customer_data.get('address'),
                city=customer_data.get('city'),
                state=customer_data.get('state'),
                pincode=customer_data.get('pincode'),
                gst_number=customer_data.get('gst_number'),
                total_balance=Decimal('0.00')
            )
            
            db.session.add(customer)
            db.session.commit()
            return customer, True
            
        except Exception:
            db.session.rollback()
            return None, False
    
    @staticmethod
    def update_customer(customer_id: int, customer_data: Dict) -> bool:
        """Update customer information."""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return False
            
            customer.name = customer_data.get('name', customer.name)
            customer.contact_number = customer_data.get('contact_number', customer.contact_number)
            customer.email = customer_data.get('email', customer.email)
            customer.address = customer_data.get('address', customer.address)
            customer.city = customer_data.get('city', customer.city)
            customer.state = customer_data.get('state', customer.state)
            customer.pincode = customer_data.get('pincode', customer.pincode)
            customer.gst_number = customer_data.get('gst_number', customer.gst_number)
            
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def delete_customer(customer_id: int) -> bool:
        """Delete customer and related records."""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return False
            
            # Check if customer has any bills
            bills = Bill.query.filter_by(customer_id=customer_id).count()
            if bills > 0:
                return False  # Cannot delete customer with bills
            
            # Delete ledger entries
            CustomerLedger.query.filter_by(customer_id=customer_id).delete()
            
            # Delete customer
            db.session.delete(customer)
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def add_ledger_entry(customer_id: int, transaction_type: str, 
                        debit_amount: Decimal = None, credit_amount: Decimal = None,
                        description: str = '', bill_id: int = None) -> bool:
        """Add entry to customer ledger."""
        try:
            customer = Customer.query.get(customer_id)
            if not customer:
                return False
            
            # Ensure proper decimal values
            debit_amount = debit_amount or Decimal('0.00')
            credit_amount = credit_amount or Decimal('0.00')
            
            # Calculate new balance
            current_balance = customer.total_balance or Decimal('0.00')
            new_balance = current_balance + debit_amount - credit_amount
            
            # Create ledger entry with SQL Server compatibility
            with db.session.no_autoflush:
                ledger_entry = CustomerLedger(
                    customer_id=customer_id,
                    transaction_type=transaction_type,
                    debit_amount=debit_amount,
                    credit_amount=credit_amount,
                    balance_amount=new_balance,
                    description=description,
                    transaction_date=date.today(),
                    bill_id=bill_id
                )
                
                # Update customer balance
                customer.total_balance = new_balance
                
                db.session.add(ledger_entry)
                db.session.add(customer)
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_customer_ledger(customer_id: int, page: int = 1, per_page: int = 20) -> Dict:
        """Get customer ledger with pagination."""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        # Get ledger entries with pagination
        ledger_query = CustomerLedger.query.filter_by(customer_id=customer_id)\
                                          .order_by(CustomerLedger.transaction_date.desc(),
                                                   CustomerLedger.ledger_id.desc())
        
        ledger_pagination = ledger_query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return {
            'customer': customer,
            'ledger_entries': ledger_pagination.items,
            'pagination': ledger_pagination,
            'total_balance': customer.total_balance or Decimal('0.00')
        }
    
    @staticmethod
    def get_customer_summary(customer_id: int) -> Dict:
        """Get customer summary with totals."""
        customer = Customer.query.get(customer_id)
        if not customer:
            return None
        
        # Get ledger totals
        ledger_entries = CustomerLedger.query.filter_by(customer_id=customer_id).all()
        
        total_purchases = sum(
            entry.debit_amount for entry in ledger_entries 
            if entry.transaction_type == 'PURCHASE'
        )
        total_payments = sum(
            entry.credit_amount for entry in ledger_entries 
            if entry.transaction_type == 'PAYMENT'
        )
        
        # Get bill count
        bill_count = Bill.query.filter_by(customer_id=customer_id).count()
        
        return {
            'customer': customer,
            'total_purchases': total_purchases,
            'total_payments': total_payments,
            'outstanding_balance': customer.total_balance or Decimal('0.00'),
            'total_transactions': len(ledger_entries),
            'total_bills': bill_count
        }
    
    @staticmethod
    def process_payment(customer_id: int, payment_amount: Decimal, 
                       description: str = 'Payment received') -> bool:
        """Process customer payment."""
        return CustomerService.add_ledger_entry(
            customer_id=customer_id,
            transaction_type='PAYMENT',
            credit_amount=payment_amount,
            description=description
        )
    
    @staticmethod
    def adjust_balance(customer_id: int, adjustment_amount: Decimal, 
                      description: str = 'Balance adjustment') -> bool:
        """Adjust customer balance (positive for debit, negative for credit)."""
        if adjustment_amount > 0:
            return CustomerService.add_ledger_entry(
                customer_id=customer_id,
                transaction_type='ADJUSTMENT',
                debit_amount=adjustment_amount,
                description=description
            )
        else:
            return CustomerService.add_ledger_entry(
                customer_id=customer_id,
                transaction_type='ADJUSTMENT',
                credit_amount=abs(adjustment_amount),
                description=description
            )
    
    @staticmethod
    def get_customers_with_balance(shopkeeper_user_id: int, 
                                  balance_type: str = 'all') -> List[Customer]:
        """Get customers filtered by balance type."""
        query = Customer.query.filter_by(shopkeeper_id=shopkeeper_user_id)
        
        if balance_type == 'positive':
            query = query.filter(Customer.total_balance > 0)
        elif balance_type == 'negative':
            query = query.filter(Customer.total_balance < 0)
        elif balance_type == 'zero':
            query = query.filter(Customer.total_balance == 0)
        
        return query.order_by(Customer.name).all()
    
    @staticmethod
    def export_customer_data(customer_id: int) -> Dict:
        """Export customer data for reports."""
        customer_summary = CustomerService.get_customer_summary(customer_id)
        if not customer_summary:
            return None
        
        # Get all ledger entries
        ledger_entries = CustomerLedger.query.filter_by(customer_id=customer_id)\
                                            .order_by(CustomerLedger.transaction_date.desc()).all()
        
        # Convert to exportable format
        ledger_data = []
        for entry in ledger_entries:
            ledger_data.append({
                'date': entry.transaction_date.strftime('%Y-%m-%d'),
                'type': entry.transaction_type,
                'description': entry.description or '',
                'debit': float(entry.debit_amount) if entry.debit_amount else 0,
                'credit': float(entry.credit_amount) if entry.credit_amount else 0,
                'balance': float(entry.balance_amount),
                'bill_id': entry.bill_id
            })
        
        return {
            'customer_info': {
                'name': customer_summary['customer'].name,
                'contact': customer_summary['customer'].contact_number,
                'email': customer_summary['customer'].email,
                'address': customer_summary['customer'].address,
                'gst_number': customer_summary['customer'].gst_number
            },
            'summary': {
                'total_purchases': float(customer_summary['total_purchases']),
                'total_payments': float(customer_summary['total_payments']),
                'outstanding_balance': float(customer_summary['outstanding_balance']),
                'total_transactions': customer_summary['total_transactions'],
                'total_bills': customer_summary['total_bills']
            },
            'ledger_entries': ledger_data
        }