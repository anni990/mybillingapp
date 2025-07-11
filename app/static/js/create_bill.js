// create_bill.js

document.addEventListener('DOMContentLoaded', function () {
    const addBtn = document.getElementById('add-product-btn');
    const productRows = document.getElementById('product-rows');
    const billTotal = document.getElementById('bill-total');

    function updateTotal() {
        let total = 0;
        document.querySelectorAll('.product-row').forEach(row => {
            const qty = parseFloat(row.querySelector('.qty').value) || 0;
            const price = parseFloat(row.querySelector('.price').value) || 0;
            total += qty * price;
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
        } else {
            row.querySelector('.price').value = '';
            row.querySelector('.stock').textContent = '';
        }
        updateTotal();
    }

    addBtn.addEventListener('click', function () {
        const row = document.createElement('div');
        row.className = 'product-row flex space-x-2 mb-2 items-center';
        row.innerHTML = `
            ${createProductDropdown('')}
            <input name="quantity" type="number" min="1" value="1" class="qty border rounded px-2 py-1 w-16" required>
            <input name="price_per_unit" type="number" min="0" step="0.01" value="0.00" class="price border rounded px-2 py-1 w-24" required>
            <span class="stock text-xs text-gray-500"></span>
            <button type="button" class="remove-product bg-red-100 text-red-600 px-2 rounded hover:bg-red-200">&times;</button>
        `;
        row.querySelector('.product-select').addEventListener('change', onProductChange);
        row.querySelector('.qty').addEventListener('input', updateTotal);
        row.querySelector('.price').addEventListener('input', updateTotal);
        row.querySelector('.remove-product').addEventListener('click', removeRow);
        productRows.appendChild(row);
        updateTotal();
    });

    // Initial row
    addBtn.click();
}); 