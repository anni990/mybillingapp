document.addEventListener('DOMContentLoaded', function () {
    console.log('Manage Bills: Initializing page functionality...');
    feather.replace();
    
    // Tab toggle functionality
    const salesTab = document.getElementById('sales-bills-tab');
    const purchaseTab = document.getElementById('purchase-bills-tab');
    const salesSection = document.getElementById('sales-bills-section');
    const purchaseSection = document.getElementById('purchase-bills-section');
    
    console.log('Toggle elements:', { salesTab, purchaseTab, salesSection, purchaseSection });
    
    if (salesTab && purchaseTab && salesSection && purchaseSection) {
        salesTab.addEventListener('click', function() {
            console.log('Sales tab clicked');
            salesTab.classList.add('active');
            purchaseTab.classList.remove('active');
            salesSection.classList.remove('hidden');
            purchaseSection.classList.add('hidden');
        });
        
        purchaseTab.addEventListener('click', function() {
            console.log('Purchase tab clicked');
            purchaseTab.classList.add('active');
            salesTab.classList.remove('active');
            purchaseSection.classList.remove('hidden');
            salesSection.classList.add('hidden');
        });
        console.log('Tab toggle functionality initialized');
    } else {
        console.error('Missing toggle elements');
    }

    // Search and Filter functionality
    const searchInput = document.getElementById('bill-search');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const statusFilter = document.getElementById('payment-status-filter');
    const clearFiltersBtn = document.getElementById('clear-filters');

    console.log('Filter elements:', { searchInput, startDateInput, endDateInput, statusFilter, clearFiltersBtn });

    function filterBills() {
        console.log('Filtering bills...');
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const startDate = startDateInput ? startDateInput.value : '';
        const endDate = endDateInput ? endDateInput.value : '';
        const statusValue = statusFilter ? statusFilter.value : '';

        console.log('Filter criteria:', { searchTerm, startDate, endDate, statusValue });

        // Filter sales bills
        const billRows = document.querySelectorAll('.bill-row, .bill-card');
        console.log('Found bill rows:', billRows.length);
        
        billRows.forEach(row => {
            const billNumber = row.dataset.billNumber || '';
            const customer = row.dataset.customer || '';
            const date = row.dataset.date || '';
            const status = row.dataset.status || '';

            let showRow = true;

            // Search filter
            if (searchTerm && !billNumber.includes(searchTerm) && !customer.includes(searchTerm)) {
                showRow = false;
            }

            // Date range filter
            if (startDate && date < startDate) showRow = false;
            if (endDate && date > endDate) showRow = false;

            // Status filter
            if (statusValue && status !== statusValue) showRow = false;

            row.style.display = showRow ? '' : 'none';
        });

        // Filter purchase bills
        const purchaseBillRows = document.querySelectorAll('.purchase-bill-row, .purchase-bill-card');
        console.log('Found purchase bill rows:', purchaseBillRows.length);
        
        purchaseBillRows.forEach(row => {
            const vendor = row.dataset.vendor || '';
            const invoice = row.dataset.invoice || '';
            const date = row.dataset.date || '';

            let showRow = true;

            // Search filter
            if (searchTerm && !vendor.includes(searchTerm) && !invoice.includes(searchTerm)) {
                showRow = false;
            }

            // Date range filter
            if (startDate && date < startDate) showRow = false;
            if (endDate && date > endDate) showRow = false;

            row.style.display = showRow ? '' : 'none';
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterBills);
        console.log('Search input listener added');
    }
    if (startDateInput) {
        startDateInput.addEventListener('change', filterBills);
        console.log('Start date listener added');
    }
    if (endDateInput) {
        endDateInput.addEventListener('change', filterBills);
        console.log('End date listener added');
    }
    if (statusFilter) {
        statusFilter.addEventListener('change', filterBills);
        console.log('Status filter listener added');
    }

    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function () {
            console.log('Clear filters clicked');
            if (searchInput) searchInput.value = '';
            if (startDateInput) startDateInput.value = '';
            if (endDateInput) endDateInput.value = '';
            if (statusFilter) statusFilter.value = '';
            filterBills();
        });
        console.log('Clear filters listener added');
    }

    // Payment Modal Logic
    const modal = document.getElementById('update-payment-modal');
    const closeModal = () => {
        if (modal) modal.classList.add('hidden');
    };

    document.querySelectorAll('.update-payment-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            if (!modal) return;
            modal.classList.remove('hidden');
            
            // Populate modal with data
            const elements = {
                'modal-customer': btn.dataset.customer,
                'modal-bill-number': btn.dataset.billNumber,
                'modal-customer-phone': btn.dataset.customerPhone,
                'modal-bill-date': btn.dataset.billDate,
                'modal-bill-amount': btn.dataset.amount,
                'modal-bill-paid': btn.dataset.paid,
                'modal-bill-unpaid': btn.dataset.unpaid
            };
            
            Object.entries(elements).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            });
            
            const paymentInput = document.getElementById('modal-new-payment');
            if (paymentInput) paymentInput.value = '';
            
            const form = document.getElementById('update-payment-form');
            if (form) {
                form.dataset.billId = btn.dataset.billId;
                form.dataset.paid = btn.dataset.paid;
                form.dataset.unpaid = btn.dataset.unpaid;
                form.dataset.amount = btn.dataset.amount;
            }
        });
    });

    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalCancel = document.getElementById('modal-cancel');
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (modalCancel) modalCancel.addEventListener('click', closeModal);

    // Payment form submission
    const paymentForm = document.getElementById('update-payment-form');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function (e) {
            e.preventDefault();
            const billId = this.dataset.billId;
            const newPaymentInput = document.getElementById('modal-new-payment');
            const newPayment = parseFloat(newPaymentInput?.value) || 0;
            const paid = parseFloat(this.dataset.paid) || 0;
            const amount = parseFloat(this.dataset.amount) || 0;
            
            let newStatus = 'Partial';
            let finalPaid = paid + newPayment;
            let finalUnpaid = amount - finalPaid;
            
            if (finalPaid >= amount) {
                newStatus = 'Paid';
                finalPaid = amount;
                finalUnpaid = 0;
            }
            
            fetch(`/shopkeeper/update_payment/${billId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_payment: newPayment, new_status: newStatus })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showFlashPopup({
                        customer: document.getElementById('modal-customer')?.textContent || '',
                        billNumber: document.getElementById('modal-bill-number')?.textContent || '',
                        customerPhone: document.getElementById('modal-customer-phone')?.textContent || '',
                        billDate: document.getElementById('modal-bill-date')?.textContent || '',
                        amount: document.getElementById('modal-bill-amount')?.textContent || '',
                        paid: `₹${finalPaid.toFixed(2)}`,
                        unpaid: `₹${finalUnpaid.toFixed(2)}`,
                        status: newStatus
                    });
                    closeModal();
                } else {
                    showNotification('Error updating payment', 'error');
                }
            })
            .catch(error => {
                console.error('Payment update error:', error);
                showNotification('Error updating payment', 'error');
            });
        });
    }

    // Complete Payment Button
    const completePaymentBtn = document.getElementById('complete-payment-btn');
    if (completePaymentBtn) {
        completePaymentBtn.addEventListener('click', function () {
            const form = document.getElementById('update-payment-form');
            if (!form) return;
            
            const billId = form.dataset.billId;
            const amount = parseFloat(form.dataset.amount) || 0;
            
            fetch(`/shopkeeper/update_payment/${billId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ new_payment: amount, new_status: 'Paid' })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showFlashPopup({
                        customer: document.getElementById('modal-customer')?.textContent || '',
                        billNumber: document.getElementById('modal-bill-number')?.textContent || '',
                        customerPhone: document.getElementById('modal-customer-phone')?.textContent || '',
                        billDate: document.getElementById('modal-bill-date')?.textContent || '',
                        amount: document.getElementById('modal-bill-amount')?.textContent || '',
                        paid: `₹${amount.toFixed(2)}`,
                        unpaid: `₹0.00`,
                        status: 'Paid'
                    });
                    closeModal();
                } else {
                    showNotification('Error updating payment', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error updating payment', 'error');
            });
        });
    }

    // Flash Popup Logic
    function showFlashPopup(billData) {
        const popup = document.getElementById('flash-popup');
        if (!popup) return;

        const elements = {
            'flash-customer': billData.customer,
            'flash-bill-number': billData.billNumber,
            'flash-customer-phone': billData.customerPhone,
            'flash-bill-date': billData.billDate,
            'flash-bill-amount': billData.amount,
            'flash-bill-paid': billData.paid,
            'flash-bill-unpaid': billData.unpaid,
            'flash-bill-status': billData.status
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
        
        popup.classList.remove('hidden');
        popup.classList.add('popup-visible');
        
        // Auto-hide after 5 seconds
        if (popup._timeout) clearTimeout(popup._timeout);
        popup._timeout = setTimeout(() => {
            hideFlashPopup();
        }, 5000);
    }

    function hideFlashPopup() {
        const popup = document.getElementById('flash-popup');
        if (popup) {
            popup.classList.remove('popup-visible');
            popup.classList.add('hidden');
            if (popup._timeout) clearTimeout(popup._timeout);
        }
    }

    const flashOkBtn = document.getElementById('flash-ok-btn');
    if (flashOkBtn) flashOkBtn.addEventListener('click', hideFlashPopup);

    // Delete Modal Logic
    const deleteModal = document.getElementById('delete-confirmation-modal');
    const deleteCancelBtn = document.getElementById('delete-cancel-btn');
    const deleteConfirmBtn = document.getElementById('delete-confirm-btn');
    let billToDelete = null;

    // Make deleteBill function global
    window.deleteBill = function(billId) {
        console.log('Delete bill called for ID:', billId);
        billToDelete = billId;
        if (deleteModal) {
            deleteModal.classList.remove('hidden');
        } else {
            showNotification('Modal not found. Please refresh the page and try again.', 'error');
        }
    };

    function closeDeleteModal() {
        if (deleteModal) deleteModal.classList.add('hidden');
        billToDelete = null;
    }

    if (deleteCancelBtn) deleteCancelBtn.addEventListener('click', closeDeleteModal);

    if (deleteConfirmBtn) {
        deleteConfirmBtn.addEventListener('click', function() {
            if (!billToDelete) {
                showNotification('No bill selected for deletion.', 'error');
                return;
            }
            
            fetch(`/shopkeeper/bill/delete/${billToDelete}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return response.json();
            })
            .then(data => {
                closeDeleteModal();
                if (data.success) {
                    showNotification(data.message || 'Bill deleted successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(data.message || 'Error deleting bill. Please try again.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                closeDeleteModal();
                showNotification('Error deleting bill: ' + error.message, 'error');
            });
        });
    }

    // Close modal when clicking outside
    if (deleteModal) {
        deleteModal.addEventListener('click', function(e) {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }

    // File Viewer Functionality
    let currentZoom = 1;
    const fileModal = document.getElementById('file-viewer-modal');
    const closeBtn = document.getElementById('close-file-viewer');
    const zoomInBtn = document.getElementById('zoom-in-btn');
    const zoomOutBtn = document.getElementById('zoom-out-btn');
    const zoomLevel = document.getElementById('zoom-level');
    const image = document.getElementById('file-image');

    window.viewPurchaseBillFile = function(billId) {
        console.log('View purchase bill file called for ID:', billId);
        const loading = document.getElementById('file-loading');
        
        if (fileModal) fileModal.classList.remove('hidden');
        if (loading) loading.classList.remove('hidden');
        if (image) image.classList.add('hidden');
        
        fetch(`/shopkeeper/purchase-bill-file/${billId}`)
            .then(response => {
                if (!response.ok) throw new Error('File not found');
                return response.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                if (image) {
                    image.src = url;
                    image.onload = () => {
                        if (loading) loading.classList.add('hidden');
                        image.classList.remove('hidden');
                    };
                }
            })
            .catch(error => {
                console.error('Error loading file:', error);
                if (loading) loading.innerHTML = '<p class="text-red-600">Error loading file</p>';
            });
    };

    function closeFileViewer() {
        if (fileModal) fileModal.classList.add('hidden');
        currentZoom = 1;
        if (image) image.style.transform = 'scale(1)';
        if (zoomLevel) zoomLevel.textContent = '100%';
    }

    function updateZoom() {
        if (image) image.style.transform = `scale(${currentZoom})`;
        if (zoomLevel) zoomLevel.textContent = `${Math.round(currentZoom * 100)}%`;
    }

    if (closeBtn) closeBtn.addEventListener('click', closeFileViewer);
    
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', () => {
            if (currentZoom < 3) {
                currentZoom += 0.25;
                updateZoom();
            }
        });
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', () => {
            if (currentZoom > 0.5) {
                currentZoom -= 0.25;
                updateZoom();
            }
        });
    }

    // Close modal when clicking outside
    if (fileModal) {
        fileModal.addEventListener('click', (e) => {
            if (e.target === fileModal) closeFileViewer();
        });
    }

    // Delete purchase bill functionality
    window.deletePurchaseBill = function(billId) {
        console.log('Delete purchase bill called for ID:', billId);
        if (confirm('Are you sure you want to delete this purchase bill? This action cannot be undone.')) {
            fetch(`/shopkeeper/delete_purchase_bill/${billId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification('Purchase bill deleted successfully!', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(data.message || 'Error deleting purchase bill.', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error deleting purchase bill.', 'error');
            });
        }
    };

    // Notification System
    function showNotification(message, type = 'info') {
        // Check if showFlashMessage function exists (from base template)
        if (typeof showFlashMessage === 'function') {
            showFlashMessage(message, type);
            return;
        }
        
        // Fallback notification system
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 translate-x-full max-w-sm`;
        
        if (type === 'success') {
            notification.className += ' bg-green-500 text-white';
            notification.innerHTML = `
                <div class="flex items-center">
                    <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    ${message}
                </div>
            `;
        } else {
            notification.className += ' bg-red-500 text-white';
            notification.innerHTML = `
                <div class="flex items-center">
                    <svg class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    ${message}
                </div>
            `;
        }

        document.body.appendChild(notification);

        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);

        // Auto remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
    
    console.log('Manage Bills: All functionality initialized successfully');
});