#!/usr/bin/env python3
"""
Customer Ledger Management Service
Handles all customer ledger operations for bill creation and updates
"""

from decimal import Decimal
from datetime import datetime
from app.models import CustomerLedger, Customer
from app.extensions import db
from flask import current_app


class CustomerLedgerService:
    """Service class to manage customer ledger operations"""
    
    @staticmethod
    def create_ledger_entries_for_bill(bill, shopkeeper):
        """
        Create comprehensive ledger entries for a bill
        Handles all payment statuses: PAID, PARTIAL, UNPAID
        """
        if not bill.customer_id:
            return  # No customer linked, skip ledger entries
        
        customer = Customer.query.get(bill.customer_id)
        if not customer:
            current_app.logger.warning(f"Bill has customer_id={bill.customer_id} but customer not found")
            return
        
        try:
            bill_total = Decimal(str(bill.total_amount))
            paid_amount = Decimal(str(bill.paid_amount or 0))
            due_amount = Decimal(str(bill.due_amount or 0))
            
            # Get current customer balance
            current_balance = customer.total_balance or Decimal('0')
            
            current_app.logger.debug(f"Creating ledger entries for bill {bill.bill_number}: "
                                   f"total={bill_total}, paid={paid_amount}, due={due_amount}, "
                                   f"current_balance={current_balance}")
            
            # 1. ALWAYS create PURCHASE entry (debit customer for bill amount)
            purchase_entry = CustomerLedger(
                customer_id=customer.customer_id,
                shopkeeper_id=shopkeeper.user_id,
                transaction_date=bill.bill_date,
                invoice_no=bill.bill_number,
                particulars=f"Purchase - Bill #{bill.bill_number}",
                debit_amount=bill_total,
                credit_amount=Decimal('0'),
                balance_amount=current_balance + bill_total,
                transaction_type='PURCHASE',
                reference_bill_id=bill.bill_id,
                notes=f"Bill created with {len(bill.bill_items)} items"
            )
            db.session.add(purchase_entry)
            
            # Update running balance after purchase
            new_balance = current_balance + bill_total
            
            # 2. Create PAYMENT entry if any amount is paid
            if paid_amount > 0:
                payment_entry = CustomerLedger(
                    customer_id=customer.customer_id,
                    shopkeeper_id=shopkeeper.user_id,
                    transaction_date=bill.bill_date,
                    invoice_no=f"PAY-{bill.bill_number}",
                    particulars=f"Payment for Bill #{bill.bill_number}",
                    debit_amount=Decimal('0'),
                    credit_amount=paid_amount,
                    balance_amount=new_balance - paid_amount,
                    transaction_type='PAYMENT',
                    reference_bill_id=bill.bill_id,
                    notes=f"Payment received ({bill.payment_status.lower()})"
                )
                db.session.add(payment_entry)
                
                # Update final balance after payment
                new_balance = new_balance - paid_amount
            
            # 3. Update customer's total balance
            customer.total_balance = new_balance
            customer.updated_date = datetime.now()
            
            current_app.logger.debug(f"Ledger entries created successfully. "
                                   f"Customer balance: {current_balance} → {new_balance}")
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error creating ledger entries for bill {bill.bill_id}: {str(e)}")
            raise e
    
    @staticmethod
    def update_ledger_entries_for_bill(bill, shopkeeper, old_bill_data=None):
        """
        Update ledger entries when a bill is modified
        
        Args:
            bill: Updated bill object
            shopkeeper: Shopkeeper object
            old_bill_data: Dict with old bill values for comparison
        """
        if not bill.customer_id:
            return  # No customer linked, skip ledger updates
        
        customer = Customer.query.get(bill.customer_id)
        if not customer:
            current_app.logger.warning(f"Bill has customer_id={bill.customer_id} but customer not found")
            return
        
        try:
            # 1. Remove old ledger entries for this bill
            old_entries = CustomerLedger.query.filter_by(reference_bill_id=bill.bill_id).all()
            
            # Store old balance impact for reversal
            old_debit_total = sum(Decimal(str(entry.debit_amount or 0)) for entry in old_entries)
            old_credit_total = sum(Decimal(str(entry.credit_amount or 0)) for entry in old_entries)
            old_net_impact = old_debit_total - old_credit_total
            
            # Delete old entries
            for entry in old_entries:
                db.session.delete(entry)
            
            current_app.logger.debug(f"Removed {len(old_entries)} old ledger entries. "
                                   f"Old net impact: {old_net_impact}")
            
            # 2. Reverse the old balance impact
            customer.total_balance = (customer.total_balance or Decimal('0')) - old_net_impact
            
            # 3. Create new ledger entries with current bill data
            CustomerLedgerService.create_ledger_entries_for_bill(bill, shopkeeper)
            
            current_app.logger.debug(f"Updated ledger entries for bill {bill.bill_number}")
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error updating ledger entries for bill {bill.bill_id}: {str(e)}")
            raise e
    
    @staticmethod
    def delete_ledger_entries_for_bill(bill_id, customer_id):
        """
        Clean up ledger entries when a bill is deleted
        """
        try:
            # Get customer
            customer = Customer.query.get(customer_id) if customer_id else None
            if not customer:
                return
            
            # Get all entries for this bill
            entries = CustomerLedger.query.filter_by(reference_bill_id=bill_id).all()
            
            if entries:
                # Calculate net impact to reverse
                total_debit = sum(Decimal(str(entry.debit_amount or 0)) for entry in entries)
                total_credit = sum(Decimal(str(entry.credit_amount or 0)) for entry in entries)
                net_impact = total_debit - total_credit
                
                # Update entries to remove bill reference and mark as deleted
                for entry in entries:
                    entry.reference_bill_id = None
                    entry.particulars = f"{entry.particulars} (Bill Deleted)"
                    entry.notes = f"{entry.notes or ''} - Bill was deleted on {datetime.now().strftime('%Y-%m-%d')}"
                
                # Reverse the balance impact
                customer.total_balance = (customer.total_balance or Decimal('0')) - net_impact
                customer.updated_date = datetime.now()
                
                current_app.logger.debug(f"Cleaned up {len(entries)} ledger entries for deleted bill. "
                                       f"Reversed balance impact: {net_impact}")
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error cleaning up ledger entries for bill {bill_id}: {str(e)}")
            raise e
    
    @staticmethod
    def get_customer_ledger_summary(customer_id):
        """
        Get customer ledger summary with running balances
        """
        try:
            entries = CustomerLedger.query.filter_by(customer_id=customer_id)\
                                        .order_by(CustomerLedger.transaction_date.desc())\
                                        .all()
            
            summary = {
                'total_entries': len(entries),
                'total_purchases': Decimal('0'),
                'total_payments': Decimal('0'),
                'current_balance': Decimal('0'),
                'last_transaction_date': None
            }
            
            for entry in entries:
                if entry.transaction_type == 'PURCHASE':
                    summary['total_purchases'] += Decimal(str(entry.debit_amount or 0))
                elif entry.transaction_type == 'PAYMENT':
                    summary['total_payments'] += Decimal(str(entry.credit_amount or 0))
                
                if entries and not summary['last_transaction_date']:
                    summary['last_transaction_date'] = entry.transaction_date
            
            # Get current balance from customer record
            customer = Customer.query.get(customer_id)
            if customer:
                summary['current_balance'] = customer.total_balance or Decimal('0')
            
            return summary
            
        except Exception as e:
            current_app.logger.error(f"Error getting ledger summary for customer {customer_id}: {str(e)}")
            return None