/**
 * Messages Application
 * Handles CA-Shopkeeper messaging with WhatsApp-style interface
 */

const MessagesApp = {
    config: {
        userRole: null,
        userId: null,
        selectedClientId: null,
        currentMessageType: 'chat', // 'chat' or 'remark'
        pollInterval: null,
        pollFrequency: 60000, // 60 seconds (reduced from 5 seconds)
        enablePolling: false // Disabled by default to reduce server load
    },

    elements: {},

    init(config) {
        console.log('MessagesApp initializing with config:', config);
        this.config = { ...this.config, ...config };
        this.cacheElements();
        this.bindEvents();
        console.log('About to load clients, userRole:', this.config.userRole);
        this.loadClients();
        // Only start polling if explicitly enabled
        if (this.config.enablePolling) {
            this.startPolling();
        }
    },

    cacheElements() {
        this.elements = {
            // Client list
            clientsList: document.getElementById('clients-list'),
            clientsLoading: document.getElementById('clients-loading'),
            clientSearch: document.getElementById('client-search'),

            // Chat area
            chatHeader: document.getElementById('chat-header'),
            chatToggle: document.getElementById('chat-toggle'),
            messagesContainer: document.getElementById('messages-container'),
            messagesList: document.getElementById('messages-list'),
            welcomeState: document.getElementById('welcome-state'),
            messageInputArea: document.getElementById('message-input-area'),

            // Chat controls
            selectedClientAvatar: document.getElementById('selected-client-avatar'),
            selectedClientName: document.getElementById('selected-client-name'),
            chatTab: document.getElementById('chat-tab'),
            remarksTab: document.getElementById('remarks-tab'),
            messageInput: document.getElementById('message-input'),
            sendBtn: document.getElementById('send-btn'),
            charCount: document.getElementById('char-count'),

            // Remark modal
            remarkModal: document.getElementById('remark-modal'),
            closeRemarkModal: document.getElementById('close-remark-modal'),
            remarkBillInfo: document.getElementById('remark-bill-info'),
            remarkText: document.getElementById('remark-text'),
            remarkCharCount: document.getElementById('remark-char-count'),
            cancelRemark: document.getElementById('cancel-remark'),
            submitRemark: document.getElementById('submit-remark'),

            // Sidebar badge
            unreadBadge: document.getElementById('msg-unread-badge')
        };
        
        console.log('Elements cached:', {
            clientsList: !!this.elements.clientsList,
            clientsLoading: !!this.elements.clientsLoading,
            clientSearch: !!this.elements.clientSearch
        });
    },

    bindEvents() {
        // Client search
        this.elements.clientSearch?.addEventListener('input', (e) => {
            this.filterClients(e.target.value);
        });

        // Manual refresh button
        document.getElementById('refresh-messages')?.addEventListener('click', () => {
            this.refreshMessages();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // R key for refresh (when not typing in input fields)
            if (e.key === 'r' || e.key === 'R') {
                if (!['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                    e.preventDefault();
                    this.refreshMessages();
                }
            }
        });

        // Tab switching
        this.elements.chatTab?.addEventListener('click', () => {
            this.switchTab('chat');
        });

        this.elements.remarksTab?.addEventListener('click', () => {
            this.switchTab('remark');
        });

        // Message input
        this.elements.messageInput?.addEventListener('input', (e) => {
            this.updateCharCount(e.target.value.length, this.elements.charCount);
            this.toggleSendButton();
            this.autoResizeTextarea(e.target);
        });

        this.elements.messageInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Send button
        this.elements.sendBtn?.addEventListener('click', () => {
            this.sendMessage();
        });

        // Remark modal
        this.elements.closeRemarkModal?.addEventListener('click', () => {
            this.closeRemarkModal();
        });

        this.elements.cancelRemark?.addEventListener('click', () => {
            this.closeRemarkModal();
        });

        this.elements.submitRemark?.addEventListener('click', () => {
            this.submitRemark();
        });

        this.elements.remarkText?.addEventListener('input', (e) => {
            this.updateCharCount(e.target.value.length, this.elements.remarkCharCount);
        });
    },

    async loadClients() {
        console.log('loadClients called, userRole:', this.config.userRole);
        if (this.config.userRole !== 'CA') {
            console.log('Not CA role, skipping client loading');
            return;
        }

        console.log('Making API call to load clients...');
        try {
            const response = await fetch('/api/messages/clients');
            console.log('API response received:', response.status, response.statusText);
            if (response.ok) {
                const clients = await response.json();
                console.log('Clients data received:', clients);
                this.renderClients(clients);
                this.updateUnreadBadge(clients);
            } else {
                const errorText = await response.text();
                console.error('Failed to load clients:', response.status, errorText);
                this.showError('Failed to load clients');
            }
        } catch (error) {
            console.error('Error loading clients:', error);
            this.showError('Failed to load clients');
        }

        if (this.elements.clientsLoading) {
            this.elements.clientsLoading.style.display = 'none';
        }
    },

    renderClients(clients) {
        console.log('renderClients called with clients:', clients);
        const container = this.elements.clientsList;
        container.innerHTML = '';

        if (clients.length === 0) {
            console.log('No clients to display');
            container.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    <p>No connected clients found</p>
                </div>
            `;
            return;
        }

        console.log('Rendering', clients.length, 'clients');
        clients.forEach(client => {
            const clientElement = this.createClientElement(client);
            container.appendChild(clientElement);
        });
    },

    createClientElement(client) {
        const div = document.createElement('div');
        div.className = 'p-4 hover:bg-gray-50 cursor-pointer transition-colors duration-200 client-item';
        div.dataset.clientId = client.user_id;
        div.dataset.clientName = client.shop_name;

        const unreadBadge = client.unread_count > 0 ? 
            `<span class="ml-auto bg-orange-500 text-white text-xs rounded-full px-2 py-1">${client.unread_count}</span>` : '';

        const lastMessage = client.last_message ? 
            `<p class="text-sm text-gray-500 truncate">${client.last_message.text}</p>` :
            '<p class="text-sm text-gray-500 italic">No messages yet</p>';

        div.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center flex-1 min-w-0">
                    <div class="w-10 h-10 bg-orange-500 rounded-full flex items-center justify-center text-white font-semibold mr-3">
                        ${client.shop_name.charAt(0).toUpperCase()}
                    </div>
                    <div class="min-w-0 flex-1">
                        <h3 class="font-medium text-gray-900 truncate">${client.shop_name}</h3>
                        ${lastMessage}
                    </div>
                </div>
                ${unreadBadge}
            </div>
        `;

        div.addEventListener('click', () => {
            this.selectClient(client.user_id, client.shop_name);
        });

        return div;
    },

    filterClients(searchTerm) {
        const clientItems = document.querySelectorAll('.client-item');
        const term = searchTerm.toLowerCase();

        clientItems.forEach(item => {
            const clientName = item.dataset.clientName.toLowerCase();
            if (clientName.includes(term)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    },

    async selectClient(clientId, clientName) {
        // Update UI state
        this.config.selectedClientId = clientId;
        
        // Update selected state
        document.querySelectorAll('.client-item').forEach(item => {
            item.classList.remove('bg-orange-50', 'border-l-4', 'border-orange-500');
        });
        
        const selectedItem = document.querySelector(`[data-client-id="${clientId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('bg-orange-50', 'border-l-4', 'border-orange-500');
        }

        // Update chat header
        this.elements.selectedClientName.textContent = clientName;
        this.elements.selectedClientAvatar.textContent = clientName.charAt(0).toUpperCase();

        // Show chat interface
        this.elements.welcomeState.style.display = 'none';
        this.elements.chatHeader.style.display = 'block';
        this.elements.chatToggle.style.display = 'block';
        this.elements.messageInputArea.style.display = 'block';
        this.elements.messagesList.style.display = 'block';

        // Load conversation
        await this.loadConversation(clientId);

        // Mark messages as read
        await this.markMessagesAsRead(clientId);
    },

    async loadConversation(clientId) {
        try {
            const url = `/api/messages/conversation/${clientId}?type=${this.config.currentMessageType}&limit=50`;
            const response = await fetch(url);
            
            if (response.ok) {
                const messages = await response.json();
                this.renderMessages(messages);
            } else {
                this.showError('Failed to load conversation');
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Failed to load conversation');
        }
    },

    renderMessages(messages) {
        const container = this.elements.messagesList;
        container.innerHTML = '';

        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <i data-feather="message-circle" class="w-12 h-12 mx-auto mb-4 text-gray-300"></i>
                    <p>No ${this.config.currentMessageType === 'chat' ? 'messages' : 'remarks'} yet</p>
                    <p class="text-sm">Start the conversation!</p>
                </div>
            `;
            feather.replace();
            return;
        }

        messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            container.appendChild(messageElement);
        });

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
        feather.replace();
    },

    createMessageElement(message) {
        const div = document.createElement('div');
        const isOwn = message.sender_id == this.config.userId;
        const messageClass = isOwn ? 'sent' : 'received';
        
        // Add responsive styling for message bubbles
        div.className = `message-bubble ${messageClass} ${message.message_type === 'remark' ? 'remark' : ''} mb-4 flex ${isOwn ? 'justify-end' : 'justify-start'}`;

        const time = new Date(message.timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });

        let billPreview = '';
        if (message.bill && message.message_type === 'remark') {
            const billDate = message.bill.bill_date ? 
                new Date(message.bill.bill_date).toLocaleDateString() : 'N/A';
            
            billPreview = `
                <div class="bill-preview mt-2 p-3 bg-gray-50 rounded-lg border">
                    <div class="flex items-center justify-between">
                        <div>
                            <a href="/ca/bills?bill_id=${message.bill.id}" class="text-orange-600 hover:text-orange-700 font-medium">
                                📄 View Bill #${message.bill.bill_number || message.bill.id}
                            </a>
                            <p class="text-sm text-gray-600 mt-1">
                                ₹${message.bill.total_amount} • ${billDate}
                            </p>
                        </div>
                    </div>
                </div>
            `;
        }

        div.innerHTML = `
            <div class="message-content max-w-xs lg:max-w-md xl:max-w-lg p-3 rounded-lg ${isOwn ? 'bg-orange-500 text-white rounded-br-none' : 'bg-gray-100 text-gray-900 rounded-bl-none'}">
                <p class="whitespace-pre-wrap break-words">${this.escapeHtml(message.message)}</p>
                ${billPreview}
                <div class="message-time text-xs mt-2 opacity-70">
                    ${time}
                    ${message.message_type === 'remark' ? ' • Remark' : ''}
                </div>
            </div>
        `;

        return div;
    },

    switchTab(messageType) {
        this.config.currentMessageType = messageType;

        // Update tab appearance
        this.elements.chatTab.classList.toggle('bg-white', messageType === 'chat');
        this.elements.chatTab.classList.toggle('shadow-sm', messageType === 'chat');
        this.elements.remarksTab.classList.toggle('bg-white', messageType === 'remark');
        this.elements.remarksTab.classList.toggle('shadow-sm', messageType === 'remark');

        // Reload conversation with new filter
        if (this.config.selectedClientId) {
            this.loadConversation(this.config.selectedClientId);
        }
    },

    async sendMessage() {
        const message = this.elements.messageInput.value.trim();
        if (!message || !this.config.selectedClientId) return;

        try {
            const response = await fetch('/api/messages/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    receiver_id: this.config.selectedClientId,
                    message: message,
                    message_type: this.config.currentMessageType
                })
            });

            if (response.ok) {
                this.elements.messageInput.value = '';
                this.updateCharCount(0, this.elements.charCount);
                this.toggleSendButton();
                this.autoResizeTextarea(this.elements.messageInput);
                
                // Reload conversation
                await this.loadConversation(this.config.selectedClientId);
            } else {
                const error = await response.json();
                this.showError(error.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message');
        }
    },

    async markMessagesAsRead(partnerId) {
        try {
            await fetch('/api/messages/mark_read', {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    partner_id: partnerId
                })
            });

            // Reload clients to update unread counts
            this.loadClients();
        } catch (error) {
            console.error('Error marking messages as read:', error);
        }
    },

    openRemarkModal(billId, billNumber, totalAmount, billDate) {
        // Show bill info
        this.elements.remarkBillInfo.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <h4 class="font-medium">Bill #${billNumber || billId}</h4>
                    <p class="text-sm text-gray-600">₹${totalAmount} • ${billDate}</p>
                </div>
            </div>
        `;

        // Reset modal
        this.elements.remarkText.value = '';
        this.updateCharCount(0, this.elements.remarkCharCount);
        this.elements.submitRemark.dataset.billId = billId;

        // Show modal
        this.elements.remarkModal.style.display = 'flex';
    },

    closeRemarkModal() {
        this.elements.remarkModal.style.display = 'none';
        this.elements.remarkText.value = '';
    },

    async submitRemark() {
        const remarkText = this.elements.remarkText.value.trim();
        const billId = this.elements.submitRemark.dataset.billId;

        if (!remarkText || !billId) return;

        try {
            const response = await fetch(`/api/messages/send`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    receiver_id: this.config.selectedClientId,
                    message: remarkText,
                    message_type: 'remark',
                    bill_id: parseInt(billId)
                })
            });

            if (response.ok) {
                this.closeRemarkModal();
                
                // Switch to remarks tab and reload
                this.switchTab('remark');
                if (this.config.selectedClientId) {
                    await this.loadConversation(this.config.selectedClientId);
                }
            } else {
                const error = await response.json();
                this.showError(error.error || 'Failed to add remark');
            }
        } catch (error) {
            console.error('Error submitting remark:', error);
            this.showError('Failed to add remark');
        }
    },

    updateCharCount(count, element) {
        if (element) {
            element.textContent = `${count}/2000`;
            element.classList.toggle('text-red-500', count > 1900);
        }
    },

    toggleSendButton() {
        const hasText = this.elements.messageInput.value.trim().length > 0;
        this.elements.sendBtn.disabled = !hasText || !this.config.selectedClientId;
    },

    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    },

    updateUnreadBadge(clients) {
        const totalUnread = clients.reduce((sum, client) => sum + client.unread_count, 0);
        if (this.elements.unreadBadge) {
            if (totalUnread > 0) {
                this.elements.unreadBadge.textContent = totalUnread;
                this.elements.unreadBadge.classList.remove('hidden');
            } else {
                this.elements.unreadBadge.classList.add('hidden');
            }
        }
    },

    startPolling() {
        this.stopPolling(); // Clear any existing interval
        
        this.config.pollInterval = setInterval(() => {
            if (document.visibilityState === 'visible') {
                this.loadClients();
                
                if (this.config.selectedClientId) {
                    this.loadConversation(this.config.selectedClientId);
                }
            }
        }, this.config.pollFrequency);
    },

    stopPolling() {
        if (this.config.pollInterval) {
            clearInterval(this.config.pollInterval);
            this.config.pollInterval = null;
        }
    },

    // Manual refresh method to replace automatic polling
    refreshMessages() {
        console.log('Manual refresh triggered');
        
        // Show loading state on refresh button
        const refreshBtn = document.getElementById('refresh-messages');
        if (refreshBtn) {
            const originalHTML = refreshBtn.innerHTML;
            refreshBtn.innerHTML = `
                <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
            `;
            refreshBtn.disabled = true;
            
            // Restore button after 2 seconds
            setTimeout(() => {
                refreshBtn.innerHTML = originalHTML;
                refreshBtn.disabled = false;
            }, 2000);
        }
        
        this.loadClients();
        
        if (this.config.selectedClientId) {
            this.loadConversation(this.config.selectedClientId);
        }
    },

    showError(message) {
        // You can implement a toast notification system here
        console.error(message);
        alert(message); // Simple fallback
    },

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
};

// Global function to open remark modal (called from bill pages)
window.openRemarkModal = function(billId, billNumber, totalAmount, billDate) {
    if (typeof MessagesApp !== 'undefined') {
        MessagesApp.openRemarkModal(billId, billNumber, totalAmount, billDate);
    }
};

// Stop polling when page is hidden
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') {
        MessagesApp.stopPolling();
    } else if (MessagesApp.config.enablePolling) {
        MessagesApp.startPolling();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    MessagesApp.stopPolling();
});