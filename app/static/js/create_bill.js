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
            const gstRate = parseFloat(row.querySelector('.gst-rate-input').value) || 0;
            let rowTotal = qty * price;
            if (discount > 0) {
                rowTotal = rowTotal * (1 - discount / 100);
            }
            // GST calculation
            if (billGstType.value === 'GST') {
                const gstMode = document.getElementById('gst_mode') ? document.getElementById('gst_mode').value : 'exclusive';
                if (gstMode === 'exclusive') {
                    rowTotal += rowTotal * gstRate / 100;
                } // If inclusive, GST is already included in price
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
            row.querySelector('.gst-rate-input').value = product.gst_rate;
        } else {
            row.querySelector('.price').value = '';
            row.querySelector('.stock').textContent = '';
            row.querySelector('.gst-rate-input').value = '';
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
            <input name="gst_rate" type="number" min="0" max="100" step="0.01" value="0" class="gst-rate-input border rounded px-2 py-1 w-20 text-center" required>
            <span class="stock text-xs text-gray-500"></span>
            <button type="button" class="remove-product bg-red-100 text-red-600 px-2 rounded hover:bg-red-200">&times;</button>
        `;
        row.querySelector('.product-select').addEventListener('change', onProductChange);
        row.querySelector('.qty').addEventListener('input', updateTotal);
        row.querySelector('.price').addEventListener('input', updateTotal);
        row.querySelector('.discount').addEventListener('input', updateTotal);
        row.querySelector('.gst-rate-input').addEventListener('input', updateTotal);
        row.querySelector('.remove-product').addEventListener('click', removeRow);
        productRows.appendChild(row);
        updateTotal();
    }
    addBtn.addEventListener('click', addProductRow);
    // Initial row
    addProductRow();
});