"""
GST Calculation Engine for MyBillingApp
Handles both INCLUSIVE and EXCLUSIVE GST calculations with proper discount-before-tax logic.
"""
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import Dict, List, Union

# Set precision for Decimal calculations
getcontext().prec = 28

# Quantizer for 2 decimal places with ROUND_HALF_UP
Q2 = Decimal('0.01')

# Standard Indian GST rates
STANDARD_GST_RATES = {Decimal('0'), Decimal('5'), Decimal('12'), Decimal('18'), Decimal('28')}


def _quantize(value: Union[Decimal, str, float]) -> Decimal:
    """Quantize value to 2 decimal places with ROUND_HALF_UP."""
    return Decimal(str(value)).quantize(Q2, rounding=ROUND_HALF_UP)


def validate_gst_rate(rate: Union[Decimal, str, float], allow_custom: bool = False) -> bool:
    """
    Validate GST rate.
    
    Args:
        rate: GST rate to validate
        allow_custom: If True, allows any rate 0-100%. If False, only standard Indian GST rates.
    
    Returns:
        bool: True if rate is valid
    """
    try:
        decimal_rate = Decimal(str(rate))
        if allow_custom:
            return Decimal('0') <= decimal_rate <= Decimal('100')
        return decimal_rate in STANDARD_GST_RATES
    except (ValueError, TypeError):
        return False


def base_from_inclusive_unit_price(unit_price_incl: Union[Decimal, str, float], 
                                 gst_rate: Union[Decimal, str, float]) -> Decimal:
    """
    Calculate base unit price (excluding GST) from inclusive price.
    
    Formula: Base Price = Inclusive Price ÷ (1 + GST/100)
    
    Args:
        unit_price_incl: Unit price including GST
        gst_rate: GST rate percentage
    
    Returns:
        Decimal: Base unit price excluding GST (quantized)
    """
    price = Decimal(str(unit_price_incl))
    rate = Decimal(str(gst_rate))
    
    if rate == 0:
        return _quantize(price)
    
    divisor = Decimal('1') + (rate / Decimal('100'))
    return _quantize(price / divisor)


def calc_line(price: Union[Decimal, str, float],
              qty: int,
              gst_rate: Union[Decimal, str, float],
              discount_percent: Union[Decimal, str, float] = Decimal('0'),
              mode: str = 'EXCLUSIVE') -> Dict:
    """
    Calculate GST for a single line item.
    
    Args:
        price: Unit price (inclusive or exclusive based on mode)
        qty: Quantity
        gst_rate: GST rate percentage
        discount_percent: Discount percentage (applied before GST)
        mode: 'INCLUSIVE' or 'EXCLUSIVE'
    
    Returns:
        Dict containing all calculated values:
        - unit_price_base: Base unit price (excluding GST)
        - line_base_total: Total base amount (unit_price_base * qty)
        - discount_amount: Discount amount applied
        - taxable_amount: Amount after discount (base for GST calculation)
        - cgst_amount: CGST amount (GST/2)
        - sgst_amount: SGST amount (GST/2)
        - total_gst: Total GST amount (CGST + SGST)
        - final_total: Final line total (taxable_amount + total_gst)
        - gst_rate: GST rate used
        - mode: GST mode used
    """
    # Convert inputs to Decimal
    price = Decimal(str(price))
    qty = int(qty)
    gst_rate = Decimal(str(gst_rate))
    discount_percent = Decimal(str(discount_percent))
    
    # Step 1: Calculate base unit price and line total
    if mode.upper() == 'INCLUSIVE':
        # For inclusive: extract base price first, then calculate line total
        unit_price_base = base_from_inclusive_unit_price(price, gst_rate)
        line_base_total = _quantize(unit_price_base * qty)
    else:
        # For exclusive: price is already base price
        unit_price_base = _quantize(price)
        line_base_total = _quantize(unit_price_base * qty)
    
    # Step 2: Apply discount to base amount (discount before tax)
    discount_amount = _quantize(line_base_total * (discount_percent / Decimal('100')))
    taxable_amount = _quantize(line_base_total - discount_amount)
    
    # Step 3: Calculate GST on discounted amount
    if gst_rate == 0:
        cgst_amount = sgst_amount = total_gst = Decimal('0.00')
    else:
        # Split GST equally between CGST and SGST (intra-state model)
        half_rate = gst_rate / Decimal('2')
        cgst_amount = _quantize(taxable_amount * half_rate / Decimal('100'))
        sgst_amount = _quantize(taxable_amount * half_rate / Decimal('100'))
        total_gst = _quantize(cgst_amount + sgst_amount)
    
    # Step 4: Calculate final total
    final_total = _quantize(taxable_amount + total_gst)
    
    return {
        'unit_price_base': unit_price_base,
        'line_base_total': line_base_total,
        'discount_amount': discount_amount,
        'taxable_amount': taxable_amount,
        'cgst_rate': _quantize(gst_rate / Decimal('2')),
        'sgst_rate': _quantize(gst_rate / Decimal('2')),
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'total_gst': total_gst,
        'final_total': final_total,
        'gst_rate': _quantize(gst_rate),
        'mode': mode.upper()
    }


def generate_gst_summary(items: List[Dict]) -> Dict:
    """
    Generate rate-wise GST summary from line items.
    
    Args:
        items: List of calc_line results or dicts containing GST calculation data
    
    Returns:
        Dict: Rate-wise aggregated GST summary
        {
            "18.00": {
                "taxable_amount": Decimal,
                "cgst_amount": Decimal,
                "sgst_amount": Decimal,
                "total_gst": Decimal,
                "final_total": Decimal
            },
            ...
        }
    """
    summary = {}
    
    for item in items:
        rate = Decimal(str(item['gst_rate']))
        rate_key = str(_quantize(rate))
        
        if rate_key not in summary:
            summary[rate_key] = {
                'taxable_amount': Decimal('0'),
                'cgst_amount': Decimal('0'),
                'sgst_amount': Decimal('0'),
                'total_gst': Decimal('0'),
                'final_total': Decimal('0')
            }
        
        # Aggregate values
        summary[rate_key]['taxable_amount'] += Decimal(str(item['taxable_amount']))
        summary[rate_key]['cgst_amount'] += Decimal(str(item['cgst_amount']))
        summary[rate_key]['sgst_amount'] += Decimal(str(item['sgst_amount']))
        summary[rate_key]['total_gst'] += Decimal(str(item['total_gst']))
        summary[rate_key]['final_total'] += Decimal(str(item['final_total']))
    
    # Quantize all aggregated values
    for rate_key, values in summary.items():
        for key, value in values.items():
            values[key] = _quantize(value)
    
    return summary


def calculate_bill_totals(items: List[Dict]) -> Dict:
    """
    Calculate overall bill totals from line items.
    
    Args:
        items: List of calc_line results
    
    Returns:
        Dict containing:
        - total_taxable_amount: Sum of all taxable amounts
        - total_cgst_amount: Sum of all CGST amounts
        - total_sgst_amount: Sum of all SGST amounts
        - total_gst_amount: Sum of all GST amounts
        - grand_total: Sum of all final totals
    """
    total_taxable = Decimal('0')
    total_cgst = Decimal('0')
    total_sgst = Decimal('0')
    total_gst = Decimal('0')
    grand_total = Decimal('0')
    
    for item in items:
        total_taxable += Decimal(str(item['taxable_amount']))
        total_cgst += Decimal(str(item['cgst_amount']))
        total_sgst += Decimal(str(item['sgst_amount']))
        total_gst += Decimal(str(item['total_gst']))
        grand_total += Decimal(str(item['final_total']))
    
    return {
        'total_taxable_amount': _quantize(total_taxable),
        'total_cgst_amount': _quantize(total_cgst),
        'total_sgst_amount': _quantize(total_sgst),
        'total_gst_amount': _quantize(total_gst),
        'grand_total': _quantize(grand_total)
    }


def format_for_display(value: Decimal, currency: str = '₹') -> str:
    """
    Format Decimal value for display.
    
    Args:
        value: Decimal value to format
        currency: Currency symbol
    
    Returns:
        str: Formatted currency string
    """
    return f"{currency}{value:,.2f}"


# Example usage and test cases
if __name__ == "__main__":
    # Test Case 1: GST-Inclusive Billing (from user requirements)
    # Price per item (including GST): ₹118, Quantity: 2, GST Rate: 18%, Discount: 10%
    print("=== Test Case 1: GST-Inclusive Billing ===")
    result1 = calc_line(price=118, qty=2, gst_rate=18, discount_percent=10, mode='INCLUSIVE')
    print(f"Taxable Amount: {format_for_display(result1['taxable_amount'])}")
    print(f"Total GST: {format_for_display(result1['total_gst'])}")
    print(f"Final Total: {format_for_display(result1['final_total'])}")
    print(f"Expected: ₹212.40, Actual: {format_for_display(result1['final_total'])}")
    print()
    
    # Test Case 2: GST-Exclusive Billing (from user requirements)
    # Price per item (excluding GST): ₹100, Quantity: 2, GST Rate: 18%, Discount: 10%
    print("=== Test Case 2: GST-Exclusive Billing ===")
    result2 = calc_line(price=100, qty=2, gst_rate=18, discount_percent=10, mode='EXCLUSIVE')
    print(f"Taxable Amount: {format_for_display(result2['taxable_amount'])}")
    print(f"Total GST: {format_for_display(result2['total_gst'])}")
    print(f"Final Total: {format_for_display(result2['final_total'])}")
    print(f"Expected: ₹212.40, Actual: {format_for_display(result2['final_total'])}")
    print()
    
    # Test GST Summary
    print("=== GST Summary Test ===")
    items = [result1, result2]
    summary = generate_gst_summary(items)
    totals = calculate_bill_totals(items)
    
    print("Rate-wise Summary:")
    for rate, values in summary.items():
        print(f"  {rate}% GST: Taxable: {format_for_display(values['taxable_amount'])}, "
              f"CGST: {format_for_display(values['cgst_amount'])}, "
              f"SGST: {format_for_display(values['sgst_amount'])}")
    
    print(f"\nGrand Total: {format_for_display(totals['grand_total'])}")