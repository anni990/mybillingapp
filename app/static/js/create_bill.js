// create_bill.js (cleaned version with editable GST)

document.addEventListener('DOMContentLoaded', function () {
    const addBtn = document.getElementById('add-product-btn');
    const productRows = document.getElementById('product-rows');
    const billGstType = document.getElementById('bill_gst_type');

    // Remove row
    function removeRow(e) {
        e.target.closest('.product-row').remove();
        calculateTotalWithGST();
    }

    // Create product dropdown
    function createProductDropdown(selectedId) {
        let html = `<select name="product_id" class="product-select border rounded px-2 py-1 w-40" required>`;
        html += `<option value="">Select Product</option>`;
        PRODUCTS.forEach(p => {
            html += `<option value="${p.id}" ${selectedId == p.id ? 'selected' : ''}>${p.name}</option>`;
        });
        html += `</select>`;
        return html;
    }

    // When product changes → autofill fields
    function onProductChange(e) {
        const row = e.target.closest('.product-row');
        const productId = e.target.value;
        const product = PRODUCTS.find(p => p.id == productId);

        if (product) {
            row.querySelector('.price').value = product.price;
            row.querySelector('.discount').value = product.discount || 0;
            row.querySelector('.gst-rate-input').value = product.gst_rate || 0;
            row.querySelector('.stock').textContent = `Stock: ${product.stock}`;
        } else {
            row.querySelector('.price').value = '';
            row.querySelector('.discount').value = '';
            row.querySelector('.gst-rate-input').value = '';
            row.querySelector('.stock').textContent = '';
        }

        calculateTotalWithGST();
    }

    // Add a new product row
    function addProductRow() {
        const row = document.createElement('div');
        row.className = 'product-row flex space-x-2 mb-2 items-center';
        row.innerHTML = `
            ${createProductDropdown('')}
            <input name="quantity" type="number" min="1" value="1" 
                class="qty border rounded px-2 py-1 w-16" required>
            <input name="price_per_unit" type="number" min="0" step="0.01" value="0.00" 
                class="price border rounded px-2 py-1 w-24" required>
            <input name="discount" type="number" min="0" max="100" step="0.01" value="0" 
                class="discount border rounded px-2 py-1 w-20" placeholder="0">
            <input name="gst_rate" type="number" min="0" max="28" step="0.01" value="0" 
                class="gst-rate-input border rounded px-2 py-1 w-20 text-center" required>
            <span class="stock text-xs text-gray-500"></span>
            <button type="button" 
                class="remove-product bg-red-100 text-red-600 px-2 rounded hover:bg-red-200">&times;</button>
        `;

        // Attach listeners
        row.querySelector('.product-select').addEventListener('change', onProductChange);
        row.querySelector('.qty').addEventListener('input', calculateTotalWithGST);
        row.querySelector('.price').addEventListener('input', calculateTotalWithGST);
        row.querySelector('.discount').addEventListener('input', calculateTotalWithGST);
        row.querySelector('.gst-rate-input').addEventListener('input', calculateTotalWithGST);
        row.querySelector('.remove-product').addEventListener('click', removeRow);

        productRows.appendChild(row);
        calculateTotalWithGST();
    }

    addBtn.addEventListener('click', addProductRow);

    // Add initial row
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

        const qty = parseFloat(row.querySelector('[name="quantity"]').value) || 0;
        const price = parseFloat(row.querySelector('[name="price_per_unit"]').value) || 0;
        const discount = parseFloat(row.querySelector('[name="discount"]').value) || 0;
        const gstRate = billGstType === 'GST' 
            ? (parseFloat(row.querySelector('[name="gst_rate"]').value) || 0) 
            : 0;

        let basePrice = price * qty;
        let discountAmount = basePrice * (discount / 100);
        let discountedPrice = basePrice - discountAmount;
        let gstAmount = 0;
        let finalPrice = 0;

        if (billGstType === 'GST') {
            if (gstMode === 'inclusive' && gstRate > 0) {
                // GST-Inclusive
                const divisor = 1 + (gstRate / 100);
                const actualBasePrice = basePrice / divisor;

                discountAmount = actualBasePrice * (discount / 100);
                discountedPrice = actualBasePrice - discountAmount;

                gstAmount = discountedPrice * (gstRate / 100);
                finalPrice = discountedPrice + gstAmount;
            } else {
                // GST-Exclusive
                discountAmount = basePrice * (discount / 100);
                discountedPrice = basePrice - discountAmount;

                gstAmount = discountedPrice * (gstRate / 100);
                finalPrice = discountedPrice + gstAmount;
            }
        } else {
            // Non-GST
            finalPrice = discountedPrice;
        }

        grandTotal += finalPrice;
    });

    // Round to 2 decimals
    grandTotal = Math.round(grandTotal * 100) / 100;
    document.getElementById('bill-total').textContent = grandTotal.toFixed(2);

    // Update payment fields if available
    if (typeof updatePaymentFields === 'function') {
        updatePaymentFields();
    }
}

// Setup recalculation listeners
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('gst_mode')?.addEventListener('change', calculateTotalWithGST);
    document.getElementById('bill_gst_type')?.addEventListener('change', calculateTotalWithGST);

    // Recalculate when adding product
    document.getElementById('add-product-btn').addEventListener('click', function() {
        setTimeout(calculateTotalWithGST, 100);
    });
});
