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

    // Function to disable duplicate form inputs based on screen size
    function handleFormInputDuplicates() {
        const isMobile = window.innerWidth <= 768;
        
        // Get all product rows (desktop) and mobile cards
        const desktopRows = document.querySelectorAll('.product-row');
        const mobileCards = document.querySelectorAll('.mobile-product-card');
        
        if (isMobile) {
            // On mobile: disable desktop inputs, enable mobile inputs
            desktopRows.forEach(row => {
                const inputs = row.querySelectorAll('input[name]');
                inputs.forEach(input => {
                    input.disabled = true;
                    input.removeAttribute('name'); // Remove from form submission
                    input.setAttribute('data-original-name', input.name || input.getAttribute('data-original-name') || '');
                });
            });
            
            mobileCards.forEach(card => {
                const inputs = card.querySelectorAll('input');
                inputs.forEach(input => {
                    input.disabled = false;
                    const originalName = input.getAttribute('data-original-name');
                    if (originalName) {
                        input.setAttribute('name', originalName);
                    }
                });
            });
        } else {
            // On desktop: enable desktop inputs, disable mobile inputs
            desktopRows.forEach(row => {
                const inputs = row.querySelectorAll('input');
                inputs.forEach(input => {
                    input.disabled = false;
                    const originalName = input.getAttribute('data-original-name');
                    if (originalName) {
                        input.setAttribute('name', originalName);
                    }
                });
            });
            
            mobileCards.forEach(card => {
                const inputs = card.querySelectorAll('input[name]');
                inputs.forEach(input => {
                    input.disabled = true;
                    input.removeAttribute('name'); // Remove from form submission
                    input.setAttribute('data-original-name', input.name || input.getAttribute('data-original-name') || '');
                });
            });
        }
    }

    // Handle window resize
    window.addEventListener('resize', handleFormInputDuplicates);
    
    // Initial call
    handleFormInputDuplicates();

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
            
            // Add click handlers with duplicate prevention
            productSuggestions.querySelectorAll('.product-suggestion').forEach(item => {
                item.addEventListener('click', function(e) {
                    // Prevent double-clicks and rapid successive clicks
                    if (this.dataset.processing === 'true') {
                        return;
                    }
                    this.dataset.processing = 'true';
                    
                    const productData = JSON.parse(this.dataset.product);
                    addProductRow(productData, '', false, true); // fromSearch = true
                    productSearch.value = '';
                    productSuggestions.classList.add('hidden');
                    
                    // Reset processing flag after a short delay
                    setTimeout(() => {
                        this.dataset.processing = 'false';
                    }, 500);
                });
            });

            productSuggestions.querySelectorAll('.new-product-suggestion').forEach(item => {
                item.addEventListener('click', function(e) {
                    // Prevent double-clicks and rapid successive clicks
                    if (this.dataset.processing === 'true') {
                        return;
                    }
                    this.dataset.processing = 'true';
                    
                    const productName = this.dataset.name;
                    addProductRow(null, productName, false, true); // fromSearch = true
                    productSearch.value = '';
                    productSuggestions.classList.add('hidden');
                    
                    // Reset processing flag after a short delay
                    setTimeout(() => {
                        this.dataset.processing = 'false';
                    }, 500);
                });
            });
        } else {
            productSuggestions.classList.add('hidden');
        }
    }

    function updateTotal() {
        const rows = document.querySelectorAll('.product-row');
        if (rows.length === 0) {
            billTotal.textContent = '0.00';
            return;
        }

        // Collect all line items for GST calculation
        const lineItems = [];
        rows.forEach(row => {
            const qty = parseFloat(row.querySelector('.qty').value) || 0;
            const price = parseFloat(row.querySelector('.price').value) || 0;
            const discount = parseFloat(row.querySelector('.discount').value) || 0;
            const gstRate = parseFloat(row.querySelector('.gst-rate-input').value) || 0;
            
            if (qty > 0 && price > 0) {
                lineItems.push({
                    price: price,
                    qty: qty,
                    gst_rate: gstRate,
                    discount_percent: discount
                });
            }
        });

        if (lineItems.length === 0) {
            billTotal.textContent = '0.00';
            return;
        }

        // Get GST mode
        const gstMode = document.getElementById('gst_mode') ? document.getElementById('gst_mode').value : 'EXCLUSIVE';
        
        // Call new GST preview API
        fetch('/api/preview/gst', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                line_items: lineItems,
                gst_mode: gstMode.toUpperCase(),
                bill_gst_type: billGstType.value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update bill total
                billTotal.textContent = data.totals.grand_total.toFixed(2);
                
                // Update individual row totals with calculated values
                rows.forEach((row, index) => {
                    if (index < data.line_calculations.length) {
                        const calc = data.line_calculations[index];
                        
                        // Update row total display for desktop
                        const rowTotalDisplay = row.querySelector('.row-total');
                        if (rowTotalDisplay) {
                            rowTotalDisplay.textContent = '₹' + calc.final_total.toFixed(2);
                        }
                        
                        // Update corresponding mobile card total
                        const rowId = row.dataset.rowId;
                        const mobileCard = document.querySelector(`.mobile-product-card[data-row-id="${rowId}"]`);
                        if (mobileCard) {
                            const mobileRowTotal = mobileCard.querySelector('.row-total-mobile');
                            if (mobileRowTotal) {
                                mobileRowTotal.textContent = '₹' + calc.final_total.toFixed(2);
                            }
                        }
                    }
                });
                
                // Update GST summary display if element exists
                updateGSTSummaryDisplay(data.gst_summary, data.totals);
            } else {
                console.error('GST calculation error:', data.error);
                // Fallback to simple calculation
                fallbackCalculation(rows);
            }
        })
        .catch(error => {
            console.error('Error calling GST API:', error);
            // Fallback to simple calculation
            fallbackCalculation(rows);
        });
    }

    function fallbackCalculation(rows) {
        let total = 0;
        rows.forEach(row => {
            const qty = parseFloat(row.querySelector('.qty').value) || 0;
            const price = parseFloat(row.querySelector('.price').value) || 0;
            const discount = parseFloat(row.querySelector('.discount').value) || 0;
            const gstRate = parseFloat(row.querySelector('.gst-rate-input').value) || 0;
            
            let rowTotal = qty * price;
            if (discount > 0) {
                rowTotal = rowTotal * (1 - discount / 100);
            }
            
            // Simple GST calculation for fallback
            if (billGstType.value === 'GST') {
                const gstMode = document.getElementById('gst_mode') ? document.getElementById('gst_mode').value : 'exclusive';
                if (gstMode === 'exclusive') {
                    rowTotal += rowTotal * gstRate / 100;
                }
            }
            
            total += rowTotal;
            
            // Update row total displays
            const rowTotalDisplay = row.querySelector('.row-total');
            if (rowTotalDisplay) {
                rowTotalDisplay.textContent = '₹' + rowTotal.toFixed(2);
            }
            
            const rowId = row.dataset.rowId;
            const mobileCard = document.querySelector(`.mobile-product-card[data-row-id="${rowId}"]`);
            if (mobileCard) {
                const mobileRowTotal = mobileCard.querySelector('.row-total-mobile');
                if (mobileRowTotal) {
                    mobileRowTotal.textContent = '₹' + rowTotal.toFixed(2);
                }
            }
        });
        billTotal.textContent = total.toFixed(2);
    }

    function updateGSTSummaryDisplay(gstSummary, totals) {
        // Update GST summary display if elements exist on the page
        const summaryContainer = document.getElementById('gst-summary-display');
        if (!summaryContainer) return;
        
        let html = '<div class="bg-gray-50 p-4 rounded-lg mt-4">';
        html += '<h4 class="font-semibold mb-2">GST Summary</h4>';
        
        // Display by GST rate
        Object.entries(gstSummary).forEach(([rate, summary]) => {
            if (parseFloat(rate) > 0) {
                html += `
                    <div class="text-sm mb-1">
                        <span class="font-medium">${rate}% GST:</span>
                        Taxable: ₹${summary.taxable_amount.toFixed(2)}, 
                        CGST: ₹${summary.cgst_amount.toFixed(2)}, 
                        SGST: ₹${summary.sgst_amount.toFixed(2)}
                    </div>
                `;
            }
        });
        
        html += `
            <div class="border-t pt-2 mt-2 font-semibold">
                <div>Total Taxable: ₹${totals.total_taxable_amount.toFixed(2)}</div>
                <div>Total GST: ₹${totals.total_gst_amount.toFixed(2)}</div>
                <div>Grand Total: ₹${totals.grand_total.toFixed(2)}</div>
            </div>
        `;
        html += '</div>';
        
        summaryContainer.innerHTML = html;
    }

    function removeRow(desktopRow, mobileCard) {
        // Handle both parameter styles for backward compatibility
        if (typeof desktopRow === 'object' && desktopRow.target) {
            // Old style: event object passed
            const row = desktopRow.target.closest('.product-row');
            const rowId = row.dataset.rowId;
            const correspondingMobileCard = document.querySelector(`.mobile-product-card[data-row-id="${rowId}"]`);
            
            // Check if this is the initial blank row being removed
            if (row.classList.contains('initial-blank-row')) {
                hasInitialBlankRow = false;
            }
            
            row.remove();
            if (correspondingMobileCard) {
                correspondingMobileCard.remove();
            }
        } else {
            // New style: direct elements passed
            if (desktopRow) {
                // Check if this is the initial blank row being removed
                if (desktopRow.classList.contains('initial-blank-row')) {
                    hasInitialBlankRow = false;
                }
                desktopRow.remove();
            }
            if (mobileCard) {
                mobileCard.remove();
            }
        }
        
        updateTotal();
        
        // Check if no product rows left
        const remainingRows = productRows.querySelectorAll('.product-row');
        if (remainingRows.length === 0) {
            // Show no products messages
            if (noProductsMessage) {
                noProductsMessage.style.display = 'block';
            }
            const mobileNoProducts = document.getElementById('mobile-no-products');
            if (mobileNoProducts) {
                mobileNoProducts.style.display = 'block';
            }
            
            // Change add button styling
            addBtn.classList.add('bg-blue-500', 'hover:bg-blue-600');
            addBtn.classList.remove('bg-[#ed6a3e]', 'hover:bg-orange-700');
            addBtn.innerHTML = '<i data-feather="plus" class="mr-2 w-5 h-5"></i>Add Your First Product';
            feather.replace();
        }
    }

    function addProductRow(productData = null, productName = '', isInitialBlank = false, fromSearch = false) {
        // Prevent duplicate products (same product ID) from being added
        if (productData && productData.id) {
            const existingRows = document.querySelectorAll('.product-row');
            for (let row of existingRows) {
                const existingProductId = row.querySelector('.product-id').value;
                if (existingProductId === productData.id.toString()) {
                    console.log('Duplicate product prevented:', productData.name);
                    return; // Don't add duplicate
                }
            }
        }
        
        // Hide no products messages when adding first product
        if (noProductsMessage) {
            noProductsMessage.style.display = 'none';
        }
        
        const mobileNoProducts = document.getElementById('mobile-no-products');
        if (mobileNoProducts) {
            mobileNoProducts.style.display = 'none';
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
        row.dataset.rowId = rowCounter;
        
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

        // Create corresponding mobile card
        const mobileProducts = document.getElementById('mobile-products');
        const mobileCard = document.createElement('div');
        mobileCard.className = 'mobile-product-card bg-white rounded-lg shadow-md p-4 mb-4';
        mobileCard.dataset.rowId = rowCounter;
        
        mobileCard.innerHTML = `
            <div class="space-y-3">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <input name="product_name" type="text" value="${name}" 
                               class="product-name-mobile w-full font-medium text-gray-800 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                               placeholder="Product name" required>
                        <input name="product_id" type="hidden" value="${productId}" class="product-id-mobile">
                    </div>
                    <button type="button" class="remove-product-mobile bg-red-100 text-red-600 px-2 py-1 rounded hover:bg-red-200 transition-colors ml-3">
                        <i data-feather="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
                
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Available Stock</label>
                        <span class="available-stock-mobile text-sm ${stock ? (stock > 10 ? 'text-green-600' : stock > 0 ? 'text-yellow-600' : 'text-red-600') : 'text-gray-400'} font-medium">
                            ${stock ? stock : '--'}
                        </span>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Quantity</label>
                        <input name="quantity" type="number" min="1" value="1" 
                               class="qty-mobile w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                               ${stock ? 'max="' + stock + '"' : ''} required>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-3">
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Price per Unit</label>
                        <input name="price_per_unit" type="number" min="0" step="0.01" value="${price}" 
                               class="price-mobile w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                               placeholder="0.00" required>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-500 mb-1">Discount (%)</label>
                        <input name="discount" type="number" min="0" max="100" step="0.01" value="0" 
                               class="discount-mobile w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                               placeholder="0">
                    </div>
                </div>
                
                <div class="gst-section-mobile">
                    <label class="block text-xs font-medium text-gray-500 mb-1">GST Rate (%)</label>
                    <input name="gst_rate" type="number" min="0" max="100" step="0.01" value="${gstRate}" 
                           class="gst-rate-input-mobile w-full border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[#ed6a3e]" 
                           placeholder="0" required>
                </div>
                
                <div class="flex justify-between items-center pt-2 border-t border-gray-200">
                    <span class="text-sm font-medium text-gray-600">Total:</span>
                    <span class="row-total-mobile text-lg font-bold text-[#ed6a3e]">₹0.00</span>
                </div>
            </div>
        `;

        // Add event listeners for desktop row
        const qtyInput = row.querySelector('.qty');
        qtyInput.addEventListener('input', function() {
            // Validate against stock if available
            const availableStock = stock;
            if (availableStock && parseInt(this.value) > availableStock) {
                this.value = availableStock;
                showFlashMessage(`Maximum available quantity is ${availableStock}`, 'warning');
            }
            // Sync with mobile card
            const mobileQty = mobileCard.querySelector('.qty-mobile');
            if (mobileQty) {
                mobileQty.value = this.value;
            }
            updateTotal();
        });
        
        row.querySelector('.price').addEventListener('input', function() {
            // Sync with mobile card
            const mobilePrice = mobileCard.querySelector('.price-mobile');
            if (mobilePrice) {
                mobilePrice.value = this.value;
            }
            updateTotal();
        });
        
        row.querySelector('.discount').addEventListener('input', function() {
            // Sync with mobile card
            const mobileDiscount = mobileCard.querySelector('.discount-mobile');
            if (mobileDiscount) {
                mobileDiscount.value = this.value;
            }
            updateTotal();
        });
        
        row.querySelector('.gst-rate-input').addEventListener('input', function() {
            // Sync with mobile card
            const mobileGst = mobileCard.querySelector('.gst-rate-input-mobile');
            if (mobileGst) {
                mobileGst.value = this.value;
            }
            updateTotal();
        });
        
        row.querySelector('.remove-product').addEventListener('click', function() {
            removeRow(row, mobileCard);
        });
        
        // Product name autocomplete for desktop
        const productNameInput = row.querySelector('.product-name');
        productNameInput.addEventListener('input', function() {
            // Sync with mobile card
            const mobileProductName = mobileCard.querySelector('.product-name-mobile');
            if (mobileProductName) {
                mobileProductName.value = this.value;
            }
            
            // If user changes the name, clear the product ID (treat as custom product)
            if (productData && this.value !== productData.name) {
                row.querySelector('.product-id').value = '';
                mobileCard.querySelector('.product-id-mobile').value = '';
                // Clear stock display for custom products
                row.querySelector('.available-stock').textContent = '--';
                row.querySelector('.available-stock').className = 'available-stock text-sm text-gray-400 font-medium';
                mobileCard.querySelector('.available-stock-mobile').textContent = '--';
                mobileCard.querySelector('.available-stock-mobile').className = 'available-stock-mobile text-sm text-gray-400 font-medium';
                // Remove max constraint from quantity
                row.querySelector('.qty').removeAttribute('max');
                mobileCard.querySelector('.qty-mobile').removeAttribute('max');
            }
        });

        // Add event listeners for mobile card
        const mobileQtyInput = mobileCard.querySelector('.qty-mobile');
        mobileQtyInput.addEventListener('input', function() {
            // Validate against stock if available
            const availableStock = stock;
            if (availableStock && parseInt(this.value) > availableStock) {
                this.value = availableStock;
                showFlashMessage(`Maximum available quantity is ${availableStock}`, 'warning');
            }
            // Sync with desktop row
            const desktopQty = row.querySelector('.qty');
            if (desktopQty) {
                desktopQty.value = this.value;
            }
            updateTotal();
        });
        
        mobileCard.querySelector('.price-mobile').addEventListener('input', function() {
            // Sync with desktop row
            const desktopPrice = row.querySelector('.price');
            if (desktopPrice) {
                desktopPrice.value = this.value;
            }
            updateTotal();
        });
        
        mobileCard.querySelector('.discount-mobile').addEventListener('input', function() {
            // Sync with desktop row
            const desktopDiscount = row.querySelector('.discount');
            if (desktopDiscount) {
                desktopDiscount.value = this.value;
            }
            updateTotal();
        });
        
        mobileCard.querySelector('.gst-rate-input-mobile').addEventListener('input', function() {
            // Sync with desktop row
            const desktopGst = row.querySelector('.gst-rate-input');
            if (desktopGst) {
                desktopGst.value = this.value;
            }
            updateTotal();
        });
        
        mobileCard.querySelector('.remove-product-mobile').addEventListener('click', function() {
            removeRow(row, mobileCard);
        });
        
        // Product name autocomplete for mobile
        const mobileProductNameInput = mobileCard.querySelector('.product-name-mobile');
        mobileProductNameInput.addEventListener('input', function() {
            // Sync with desktop row
            const desktopProductName = row.querySelector('.product-name');
            if (desktopProductName) {
                desktopProductName.value = this.value;
            }
            
            // If user changes the name, clear the product ID (treat as custom product)
            if (productData && this.value !== productData.name) {
                row.querySelector('.product-id').value = '';
                mobileCard.querySelector('.product-id-mobile').value = '';
                // Clear stock display for custom products
                row.querySelector('.available-stock').textContent = '--';
                row.querySelector('.available-stock').className = 'available-stock text-sm text-gray-400 font-medium';
                mobileCard.querySelector('.available-stock-mobile').textContent = '--';
                mobileCard.querySelector('.available-stock-mobile').className = 'available-stock-mobile text-sm text-gray-400 font-medium';
                // Remove max constraint from quantity
                row.querySelector('.qty').removeAttribute('max');
                mobileCard.querySelector('.qty-mobile').removeAttribute('max');
            }
        });

        // Append to containers
        productRows.appendChild(row);
        if (mobileProducts) {
            mobileProducts.appendChild(mobileCard);
        }
        
        // Initialize feather icons for the new row
        feather.replace();
        
        updateTotal();
        
        // Handle form input duplicates for the new row
        handleFormInputDuplicates();
        
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
        
        // Toggle GST column visibility for desktop and mobile
        const gstCols = document.querySelectorAll('.gst-col');
        const gstSectionsMobile = document.querySelectorAll('.gst-section-mobile');
        if (this.value === 'GST') {
            gstCols.forEach(col => col.style.display = '');
            gstSectionsMobile.forEach(section => section.style.display = '');
        } else {
            gstCols.forEach(col => col.style.display = 'none');
            gstSectionsMobile.forEach(section => section.style.display = 'none');
        }
    });

    // Don't add initial product row automatically
    // User will add products via search or manually via button
});