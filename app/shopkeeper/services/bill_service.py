"""
Bill generation service - Complex GST calculation logic.
Extracted from original routes.py - maintains all business logic.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.models import Bill, BillItem, Product, Customer, CustomerLedger
from app.extensions import db


class BillService:
    """Service class for bill-related business logic."""
    
    @staticmethod
    def calculate_gst_amount(price: Decimal, gst_rate: Decimal) -> Decimal:
        """Calculate GST amount with proper decimal precision."""
        return (price * gst_rate / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    @staticmethod
    def calculate_item_totals(price: Decimal, quantity: int, gst_rate: Decimal, 
                            discount_percent: Decimal = Decimal('0')) -> Dict[str, Decimal]:
        """Calculate all amounts for a bill item."""
        # Basic calculations
        subtotal = price * Decimal(str(quantity))
        discount_amount = (subtotal * discount_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        discounted_subtotal = subtotal - discount_amount
        
        # GST calculations
        gst_amount = BillService.calculate_gst_amount(discounted_subtotal, gst_rate)
        total_with_gst = discounted_subtotal + gst_amount
        
        return {
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'discounted_subtotal': discounted_subtotal,
            'gst_amount': gst_amount,
            'total_with_gst': total_with_gst
        }
    
    @staticmethod
    def calculate_bill_totals(bill_items: List[Dict]) -> Dict[str, Decimal]:
        """Calculate total amounts for entire bill."""
        subtotal = Decimal('0')
        total_discount = Decimal('0')
        total_gst = Decimal('0')
        final_total = Decimal('0')
        
        for item in bill_items:
            item_totals = BillService.calculate_item_totals(
                Decimal(str(item['price'])),
                int(item['quantity']),
                Decimal(str(item.get('gst_rate', 0))),
                Decimal(str(item.get('discount_percent', 0)))
            )
            
            subtotal += item_totals['subtotal']
            total_discount += item_totals['discount_amount']
            total_gst += item_totals['gst_amount']
            final_total += item_totals['total_with_gst']
        
        return {
            'subtotal': subtotal,
            'total_discount': total_discount,
            'total_gst': total_gst,
            'final_total': final_total
        }
    
    @staticmethod
    def create_bill(shopkeeper_id: int, bill_data: Dict, bill_items: List[Dict]) -> Tuple[Bill, bool]:
        """
        Create a new bill with items and handle inventory/customer ledger.
        Returns (Bill object, success_flag)
        """
        try:
            # Calculate bill totals
            totals = BillService.calculate_bill_totals(bill_items)
            
            # Create bill
            bill = Bill(
                shopkeeper_id=shopkeeper_id,
                customer_name=bill_data['customer_name'],
                customer_contact=bill_data.get('customer_contact'),
                customer_address=bill_data.get('customer_address'),
                bill_date=datetime.strptime(bill_data['bill_date'], '%Y-%m-%d').date(),
                subtotal_amount=totals['subtotal'],
                gst_amount=totals['total_gst'],
                discount_amount=totals['total_discount'],
                total_amount=totals['final_total'],
                paid_amount=Decimal(str(bill_data.get('paid_amount', 0))),
                due_amount=totals['final_total'] - Decimal(str(bill_data.get('paid_amount', 0))),
                payment_method=bill_data.get('payment_method', 'cash'),
                payment_status='paid' if totals['final_total'] <= Decimal(str(bill_data.get('paid_amount', 0))) else 'partial',
                notes=bill_data.get('notes', '')
            )
            
            db.session.add(bill)
            db.session.flush()  # Get bill ID
            
            # Create bill items and update inventory
            for item_data in bill_items:
                item_totals = BillService.calculate_item_totals(
                    Decimal(str(item_data['price'])),
                    int(item_data['quantity']),
                    Decimal(str(item_data.get('gst_rate', 0))),
                    Decimal(str(item_data.get('discount_percent', 0)))
                )
                
                bill_item = BillItem(
                    bill_id=bill.bill_id,
                    product_name=item_data['product_name'],
                    hsn_code=item_data.get('hsn_code', ''),
                    quantity=int(item_data['quantity']),
                    unit_price=Decimal(str(item_data['price'])),
                    gst_rate=Decimal(str(item_data.get('gst_rate', 0))),
                    discount_percent=Decimal(str(item_data.get('discount_percent', 0))),
                    subtotal=item_totals['subtotal'],
                    discount_amount=item_totals['discount_amount'],
                    gst_amount=item_totals['gst_amount'],
                    total_amount=item_totals['total_with_gst']
                )
                
                db.session.add(bill_item)
                
                # Update product inventory if it's an existing product
                if 'product_id' in item_data and item_data['product_id']:
                    product = Product.query.get(item_data['product_id'])
                    if product and product.stock_quantity >= int(item_data['quantity']):
                        product.stock_quantity -= int(item_data['quantity'])
                        db.session.add(product)
            
            # Handle customer ledger if customer exists
            if bill_data.get('customer_id'):
                BillService.update_customer_ledger(
                    int(bill_data['customer_id']),
                    bill,
                    totals['final_total'],
                    Decimal(str(bill_data.get('paid_amount', 0)))
                )
            
            db.session.commit()
            return bill, True
            
        except Exception as e:
            db.session.rollback()
            return None, False
    
    @staticmethod
    def update_customer_ledger(customer_id: int, bill: Bill, total_amount: Decimal, paid_amount: Decimal):
        """Update customer ledger with bill transaction."""
        customer = Customer.query.get(customer_id)
        if not customer:
            return
        
        # Create purchase entry (debit)
        purchase_entry = CustomerLedger(
            customer_id=customer_id,
            transaction_type='PURCHASE',
            debit_amount=total_amount,
            credit_amount=Decimal('0'),
            description=f'Bill #{bill.bill_id}',
            transaction_date=bill.bill_date,
            bill_id=bill.bill_id
        )
        
        # Update running balance
        current_balance = customer.total_balance or Decimal('0')
        new_balance = current_balance + total_amount
        purchase_entry.balance_amount = new_balance
        
        db.session.add(purchase_entry)
        
        # If payment made, create payment entry (credit)
        if paid_amount > 0:
            payment_entry = CustomerLedger(
                customer_id=customer_id,
                transaction_type='PAYMENT',
                debit_amount=Decimal('0'),
                credit_amount=paid_amount,
                description=f'Payment for Bill #{bill.bill_id}',
                transaction_date=bill.bill_date,
                bill_id=bill.bill_id
            )
            
            new_balance -= paid_amount
            payment_entry.balance_amount = new_balance
            db.session.add(payment_entry)
        
        # Update customer's total balance
        customer.total_balance = new_balance
        db.session.add(customer)
    
    @staticmethod
    def update_bill_payment(bill_id: int, payment_amount: Decimal, payment_method: str = 'cash') -> bool:
        """Update bill payment status."""
        try:
            bill = Bill.query.get(bill_id)
            if not bill:
                return False
            
            # Update payment amounts
            bill.paid_amount += payment_amount
            bill.due_amount = bill.total_amount - bill.paid_amount
            
            # Update payment status
            if bill.due_amount <= Decimal('0'):
                bill.payment_status = 'paid'
                bill.due_amount = Decimal('0')
            else:
                bill.payment_status = 'partial'
            
            bill.payment_method = payment_method
            
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_bill_summary(shopkeeper_id: int, date_from: Optional[datetime] = None, 
                        date_to: Optional[datetime] = None) -> Dict:
        """Get bill summary with totals and counts."""
        query = Bill.query.filter_by(shopkeeper_id=shopkeeper_id)
        
        if date_from:
            query = query.filter(Bill.bill_date >= date_from.date())
        if date_to:
            query = query.filter(Bill.bill_date <= date_to.date())
        
        bills = query.all()
        
        total_bills = len(bills)
        total_amount = sum(bill.total_amount for bill in bills)
        total_paid = sum(bill.paid_amount for bill in bills)
        total_due = sum(bill.due_amount for bill in bills)
        
        return {
            'total_bills': total_bills,
            'total_amount': total_amount,
            'total_paid': total_paid,
            'total_due': total_due,
            'paid_bills': len([b for b in bills if b.payment_status == 'paid']),
            'partial_bills': len([b for b in bills if b.payment_status == 'partial']),
            'unpaid_bills': len([b for b in bills if b.payment_status == 'unpaid'])
        }