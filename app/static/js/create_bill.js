// create_bill.js

document.addEventListener('DOMContentLoaded', function () {
    const addBtn = document.getElementById('add-product-btn');
    const productRows = document.getElementById('product-rows');
    const billTotal = document.getElementById('bill-total');
    const billGstType = document.getElementById('bill_gst_type');

    function updateTotal() {
        let total = 0;
        document.querySelectorAll('.product-row').forEach(row => {
            const qty = parseFloat(row.querySelector('.qty').value) || 0;
            const price = parseFloat(row.querySelector('.price').value) || 0;
            const discount = parseFloat(row.querySelector('.discount').value) || 0;
            let rowTotal = qty * price;
            if (discount > 0) {
                rowTotal = rowTotal * (1 - discount / 100);
            }
            total += rowTotal;
        });
        billTotal.textContent = total.toFixed(2);
    }

    function removeRow(e) {
        e.target.closest('.product-row').remove();
        updateTotal();
    }

    function createProductDropdown(selectedId) {
        let html = `<select name="product_id" class="product-select border rounded px-2 py-1 w-40" required>`;
        html += `<option value="">Select Product</option>`;
        PRODUCTS.forEach(p => {
            html += `<option value="${p.id}" ${selectedId == p.id ? 'selected' : ''}>${p.name}</option>`;
        });
        html += `</select>`;
        return html;
    }

    function onProductChange(e) {
        const row = e.target.closest('.product-row');
        const productId = e.target.value;
        const product = PRODUCTS.find(p => p.id == productId);
        if (product) {
            row.querySelector('.price').value = product.price;
            row.querySelector('.stock').textContent = `Stock: ${product.stock}`;
            row.querySelector('.gst-rate').textContent = `${product.gst_rate}%`;
        } else {
            row.querySelector('.price').value = '';
            row.querySelector('.stock').textContent = '';
            row.querySelector('.gst-rate').textContent = '';
        }
        updateTotal();
    }

    function updateGSTSectionVisibility() {
        if (billGstType.value === 'GST') {
            // gstSectionContainer.style.display = ''; // This line is removed
        } else {
            // gstSectionContainer.style.display = 'none'; // This line is removed
        }
    }

    billGstType.addEventListener('change', updateGSTSectionVisibility);
    updateGSTSectionVisibility(); // Initial call on page load

    function addProductRow() {
        const row = document.createElement('div');
        row.className = 'product-row flex space-x-2 mb-2 items-center';
        row.innerHTML = `
            ${createProductDropdown('')}
            <input name="quantity" type="number" min="1" value="1" class="qty border rounded px-2 py-1 w-16" required>
            <input name="price_per_unit" type="number" min="0" step="0.01" value="0.00" class="price border rounded px-2 py-1 w-24" required>
            <input name="discount" type="number" min="0" max="100" step="0.01" value="0" class="discount border rounded px-2 py-1 w-20" placeholder="0">
            <span class="gst-rate w-20 text-center"></span>
            <span class="stock text-xs text-gray-500"></span>
            <button type="button" class="remove-product bg-red-100 text-red-600 px-2 rounded hover:bg-red-200">&times;</button>
        `;
        row.querySelector('.product-select').addEventListener('change', onProductChange);
        row.querySelector('.qty').addEventListener('input', updateTotal);
        row.querySelector('.price').addEventListener('input', updateTotal);
        row.querySelector('.discount').addEventListener('input', updateTotal);
        row.querySelector('.remove-product').addEventListener('click', removeRow);
        productRows.appendChild(row);
        updateTotal();
    }
    addBtn.addEventListener('click', addProductRow);
    // Initial row
    addProductRow();
});

// Function to calculate total with GST
function calculateTotalWithGST() {
    const rows = document.querySelectorAll('.product-row');
    const gstMode = document.getElementById('gst_mode').value;
    const billGstType = document.getElementById('bill_gst_type').value;
    let grandTotal = 0;
    
    rows.forEach(row => {
        const productSelect = row.querySelector('[name="product_id"]');
        if (!productSelect || !productSelect.value) return;
        
        const productId = productSelect.value;
        const product = PRODUCTS.find(p => p.id == productId);
        if (!product) return;
        
        const qty = parseFloat(row.querySelector('[name="quantity"]').value) || 0;
        const price = parseFloat(row.querySelector('[name="price_per_unit"]').value) || 0;
        const discount = parseFloat(row.querySelector('[name="discount"]').value) || 0;
        
        // Get GST rate - for Non-GST bills, treat as if GST is 0%
        let gstRate = billGstType === 'GST' ? (parseFloat(product.gst_rate) || 0) : 0;
        
        // Set GST rate display
        const gstRateElem = row.querySelector('.gst-rate');
        if (gstRateElem) {
            gstRateElem.textContent = gstRate + '%';
        }
        
        let basePrice = price * qty;
        let discountAmount = basePrice * (discount / 100);
        let discountedPrice = basePrice - discountAmount;
        let gstAmount = 0;
        let finalPrice = 0;
        
        if (billGstType === 'GST') {
            if (gstMode === 'inclusive' && gstRate > 0) {
                // CASE 1: GST-Inclusive Billing
                // Base price without GST
                const divisor = 1 + (gstRate / 100);
                const actualBasePrice = basePrice / divisor;
                
                // Apply discount to base price
                discountAmount = actualBasePrice * (discount / 100);
                discountedPrice = actualBasePrice - discountAmount;
                
                // Calculate GST on discounted price
                gstAmount = discountedPrice * (gstRate / 100);
                
                // Final price
                finalPrice = discountedPrice + gstAmount;
            } else {
                // CASE 2: GST-Exclusive Billing
                // Calculate discount on base price
                discountAmount = basePrice * (discount / 100);
                discountedPrice = basePrice - discountAmount;
                
                // Calculate GST on discounted price
                gstAmount = discountedPrice * (gstRate / 100);
                
                // Final price
                finalPrice = discountedPrice + gstAmount;
            }
        } else {
            // Non-GST billing - just use the discounted price
            finalPrice = discountedPrice;
        }
        
        // Add to grand total
        grandTotal += finalPrice;
    });
    
    // Round to 2 decimal places and update display
    grandTotal = Math.round(grandTotal * 100) / 100;
    document.getElementById('bill-total').textContent = grandTotal.toFixed(2);
    
    // Update payment fields
    if (typeof updatePaymentFields === 'function') {
        updatePaymentFields();
    }
}

// Add event listeners to all product-related inputs
function setupGSTCalculationListeners() {
    const productContainer = document.getElementById('product-rows');
    
    // Use event delegation for all product inputs
    productContainer.addEventListener('input', function(e) {
        if (e.target.matches('[name="quantity"], [name="price_per_unit"], [name="discount"]')) {
            calculateTotalWithGST();
        }
    });
    
    // Listen for product selection changes
    productContainer.addEventListener('change', function(e) {
        if (e.target.matches('[name="product_id"]')) {
            calculateTotalWithGST();
        }
    });
    
    // Recalculate when GST mode changes
    document.getElementById('gst_mode')?.addEventListener('change', calculateTotalWithGST);
    document.getElementById('bill_gst_type')?.addEventListener('change', calculateTotalWithGST);
    
    // Call initially
    calculateTotalWithGST();
}

// Call this after adding the first product row
document.addEventListener('DOMContentLoaded', function() {
    // Setup after a short delay to ensure product rows are created
    setTimeout(setupGSTCalculationListeners, 500);
    
    // Add listener to "Add Product" button
    document.getElementById('add-product-btn').addEventListener('click', function() {
        // Wait for row to be added
        setTimeout(calculateTotalWithGST, 100);
    });
});