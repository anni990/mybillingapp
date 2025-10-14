#!/usr/bin/env python3
"""
Migration script to add invoice numbering fields to existing shopkeepers.
Run this after adding the new fields to ensure all shopkeepers have default values.
New shopkeepers will use timestamp-based numbering by default unless they set custom numbering.
"""

from app import create_app, db
from app.models import Shopkeeper

def migrate_invoice_numbering():
    app = create_app()
    
    with app.app_context():
        print("Starting invoice numbering migration...")
        
        # Create tables if they don't exist (includes new columns)
        db.create_all()
        
        # Update existing shopkeepers with default values (but leave them unset so they use timestamp)
        shopkeepers = Shopkeeper.query.all()
        updated_count = 0
        
        for shopkeeper in shopkeepers:
            # Set default values but leave prefix empty so timestamp method is used by default
            if shopkeeper.invoice_prefix is None:
                shopkeeper.invoice_prefix = ''  # Empty means use timestamp
                updated_count += 1
            if shopkeeper.invoice_starting_number is None:
                shopkeeper.invoice_starting_number = 1
                updated_count += 1
            if shopkeeper.current_invoice_number is None:
                shopkeeper.current_invoice_number = 1
                updated_count += 1
        
        try:
            db.session.commit()
            print(f"✅ Migration completed successfully!")
            print(f"📊 Updated {len(shopkeepers)} shopkeepers with default invoice numbering settings")
            print(f"🔧 Total field updates: {updated_count}")
            
            # Show summary of current settings
            print("\n📋 Current Invoice Numbering Summary:")
            for shopkeeper in shopkeepers:
                if shopkeeper.invoice_prefix and shopkeeper.invoice_prefix.strip():
                    from app.shopkeeper.views.profile import preview_next_invoice_number
                    next_num = preview_next_invoice_number(shopkeeper)
                    print(f"   • {shopkeeper.shop_name}: Custom numbering - {next_num}")
                else:
                    print(f"   • {shopkeeper.shop_name}: Default timestamp-based numbering")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {str(e)}")

if __name__ == '__main__':
    migrate_invoice_numbering()