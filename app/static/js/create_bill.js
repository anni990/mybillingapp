// create_bill.js - Enhanced version with product search functionality and stock display

document.addEventListener('DOMContentLoaded', function () {
    const addBtn = document.getElementById('add-product-btn');
    const productRows = document.getElementById('product-rows');
    const billTotal = document.getElementById('bill-total');
    const billGstType = document.getElementById('bill_gst_type');
    const productSearch = document.getElementById('product-search');
    const productSuggestions = document.getElementById('product-suggestions');
    const noProductsMessage = document.getElementById('no-products-message');

    let rowCounter = 0;
    let hasInitialBlankRow = false;
    let firstProductAdded = false;

    // Product search functionality
    let searchTimeout;
    productSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.toLowerCase().trim();
        
        if (query.length < 1) {
            productSuggestions.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(() => {
            showProductSuggestions(query);
        }, 300);
    });

    // Hide suggestions when clicking outside
    document.addEventListener('click', function(e) {
        if (!productSearch.contains(e.target) && !productSuggestions.contains(e.target)) {
            productSuggestions.classList.add('hidden');
        }
    });

    function showProductSuggestions(query) {
        const matchedProducts = PRODUCTS.filter(product => 
            product.name.toLowerCase().includes(query)
        );

        let html = '';
        
        // Show matched products
        matchedProducts.forEach(product => {
            html += `
                <div class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 product-suggestion" 
                     data-product='${JSON.stringify(product)}'>
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-medium text-gray-800">${product.name}</p>
                            <p class="text-sm text-gray-500">₹${product.price} | Stock: ${product.stock} | GST: ${product.gst_rate}%</p>
                        </div>
                        <div class="text-sm text-[#ed6a3e] font-medium">
                            <i data-feather="plus" class="w-4 h-4 inline"></i>
                        </div>
                    </div>
                </div>
            `;
        });

        // Add option for new product if no exact match
        const exactMatch = matchedProducts.find(p => p.name.toLowerCase() === query);
        if (!exactMatch && query.length > 0) {
            html += `
                <div class="px-4 py-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 new-product-suggestion bg-blue-50" 
                     data-name="${query}">
                    <div class="flex justify-between items-center">
                        <div>
                            <p class="font-medium text-blue-800">+ Add new product: "${query}"</p>
                            <p class="text-sm text-blue-600">Click to add as custom product</p>
                        </div>
                        <div class="text-sm text-blue-600 font-medium">
                            <i data-feather="plus-circle" class="w-4 h-4 inline"></i>
                        </div>
                    </div>
                </div>
            `;
        }

        if (html) {
            productSuggestions.innerHTML = html;
            productSuggestions.classList.remove('hidden');
            
            // Reinitialize feather icons for the suggestions
            feather.replace();
            
            // Add click handlers
            productSuggestions.querySelectorAll('.product-suggestion').forEach(item => {
                item.addEventListener('click', function() {
                    const productData = JSON.parse(this.dataset.product);
                    addProductRow(productData, '', false, true); // fromSearch = true
                    productSearch.value = '';
                    productSuggestions.classList.add('hidden');
                });
            });

            productSuggestions.querySelectorAll('.new-product-suggestion').forEach(item => {
                item.addEventListener('click', function() {
                    const productName = this.dataset.name;
                    addProductRow(null, productName, false, true); // fromSearch = true
                    productSearch.value = '';
                    productSuggestions.classList.add('hidden');
                });
            });
        } else {
            productSuggestions.classList.add('hidden');
        }
    }

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
            
            // Update row total display
            const rowTotalDisplay = row.querySelector('.row-total');
            if (rowTotalDisplay) {
                rowTotalDisplay.textContent = '₹' + rowTotal.toFixed(2);
            }
        });
        billTotal.textContent = total.toFixed(2);
    }

    function removeRow(e) {
        const row = e.target.closest('.product-row');
        
        // Check if this is the initial blank row being removed
        if (row.classList.contains('initial-blank-row')) {
            hasInitialBlankRow = false;
        }
        
        row.remove();
        updateTotal();
        
        // Check if no product rows left
        const remainingRows = productRows.querySelectorAll('.product-row');
        if (remainingRows.length === 0) {
            // Show no products message
            if (noProductsMessage) {
                noProductsMessage.style.display = 'block';
            }
            
            // Change add button styling
            addBtn.classList.add('bg-blue-500', 'hover:bg-blue-600');
            addBtn.classList.remove('bg-[#ed6a3e]', 'hover:bg-orange-700');
            addBtn.innerHTML = '<i data-feather="plus" class="mr-2 w-5 h-5"></i>Add Your First Product';
            feather.replace();
        }
    }

    function addProductRow(productData = null, productName = '', isInitialBlank = false, fromSearch = false) {
        // Hide no products message when adding first product
        if (noProductsMessage) {
            noProductsMessage.style.display = 'none';
        }
        
        // If this is the first product being added and we have an initial blank row, remove it
        if (!isInitialBlank && !firstProductAdded && hasInitialBlankRow) {
            const blankRow = document.querySelector('.initial-blank-row');
            if (blankRow) {
                blankRow.remove();
                hasInitialBlankRow = false;
            }
            firstProductAdded = true;
        }
        
        rowCounter++;
        const row = document.createElement('div');
        row.className = 'product-row px-4 py-3';
        
        // Add initial blank row class if this is the initial blank row
        if (isInitialBlank) {
            row.classList.add('initial-blank-row');
            hasInitialBlankRow = true;
        }
        
        const product = productData || {};
        const name = productData ? product.name : productName;
        const price = productData ? product.price : '';
        const gstRate = productData ? product.gst_rate : '';
        const stock = productData ? product.stock : '';
        const productId = productData ? product.id : '';

        row.innerHTML = `
            <div class="grid grid-cols-12 gap-3 items-center">
                <div class="col-span-2">
                    <input name="product_name" type="text" value="${name}" 
                           class="product-name w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           placeholder="Product name" required>
                    <input name="product_id" type="hidden" value="${productId}" class="product-id">
                </div>
                <div class="col-span-2 text-center">
                    <span class="available-stock text-sm ${stock ? (stock > 10 ? 'text-green-600' : stock > 0 ? 'text-yellow-600' : 'text-red-600') : 'text-gray-400'} font-medium">
                        ${stock ? stock : '--'}
                    </span>
                </div>
                <div class="col-span-1">
                    <input name="quantity" type="number" min="1" value="1" 
                           class="qty w-full border border-gray-300 rounded px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           ${stock ? 'max="' + stock + '"' : ''} required>
                </div>
                <div class="col-span-2">
                    <input name="price_per_unit" type="number" min="0" step="0.01" value="${price}" 
                           class="price w-full border border-gray-300 rounded px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           placeholder="0.00" required>
                </div>
                <div class="col-span-1">
                    <input name="discount" type="number" min="0" max="100" step="0.01" value="0" 
                           class="discount w-full border border-gray-300 rounded px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           placeholder="0">
                </div>
                <div class="col-span-2 gst-col">
                    <input name="gst_rate" type="number" min="0" max="100" step="0.01" value="${gstRate}" 
                           class="gst-rate-input w-full border border-gray-300 rounded px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           placeholder="0" required>
                </div>
                <div class="col-span-1 text-center">
                    <span class="row-total text-sm font-medium text-gray-700">₹0.00</span>
                </div>
                <div class="col-span-1 text-center">
                    <button type="button" class="remove-product bg-red-100 text-red-600 px-2 py-1 rounded hover:bg-red-200 transition-colors text-sm">
                        <i data-feather="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
        `;

        // Add event listeners
        const qtyInput = row.querySelector('.qty');
        qtyInput.addEventListener('input', function() {
            // Validate against stock if available
            const availableStock = stock;
            if (availableStock && parseInt(this.value) > availableStock) {
                this.value = availableStock;
                showFlashMessage(`Maximum available quantity is ${availableStock}`, 'warning');
            }
            updateTotal();
        });
        
        row.querySelector('.price').addEventListener('input', updateTotal);
        row.querySelector('.discount').addEventListener('input', updateTotal);
        row.querySelector('.gst-rate-input').addEventListener('input', updateTotal);
        row.querySelector('.remove-product').addEventListener('click', removeRow);
        
        // Product name autocomplete
        const productNameInput = row.querySelector('.product-name');
        productNameInput.addEventListener('input', function() {
            // If user changes the name, clear the product ID (treat as custom product)
            if (productData && this.value !== productData.name) {
                row.querySelector('.product-id').value = '';
                // Clear stock display for custom products
                row.querySelector('.available-stock').textContent = '--';
                row.querySelector('.available-stock').className = 'available-stock text-sm text-gray-400 font-medium';
                // Remove max constraint from quantity
                row.querySelector('.qty').removeAttribute('max');
            }
        });

        productRows.appendChild(row);
        
        // Initialize feather icons for the new row
        feather.replace();
        
        updateTotal();
        
        // Reset the add button styling if it was changed
        if (addBtn.classList.contains('bg-blue-500')) {
            addBtn.classList.remove('bg-blue-500', 'hover:bg-blue-600');
            addBtn.classList.add('bg-[#ed6a3e]', 'hover:bg-orange-700');
            addBtn.innerHTML = '<i data-feather="plus" class="mr-2 w-4 h-4"></i>Add Another Product';
            feather.replace();
        }
    }

    // Event listeners
    addBtn.addEventListener('click', () => addProductRow());
    
    // Initial setup
    billGstType.addEventListener('change', function() {
        updateTotal(); // Recalculate when GST type changes
        
        // Toggle GST column visibility
        const gstCols = document.querySelectorAll('.gst-col');
        if (this.value === 'GST') {
            gstCols.forEach(col => col.style.display = '');
        } else {
            gstCols.forEach(col => col.style.display = 'none');
        }
    });

    // Don't add initial product row automatically
    // User will add products via search or manually via button
});