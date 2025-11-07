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
        this.refreshMessages();
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
        
        if (this.config.userRole === 'CA') {
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
        } else if (this.config.userRole === 'shopkeeper') {
            console.log('Shopkeeper role - loading connected CA...');
            await this.loadShopkeeperConnectedCA();
        } else {
            console.log('Unknown role, skipping client loading');
            return;
        }
    },

    async loadShopkeeperConnectedCA() {
        // For shopkeepers, we'll load the connected CA information
        // This method can be enhanced to fetch CA details if needed
        try {
            const response = await fetch('/api/messages/connected_cas');
            if (response.ok) {
                const caData = await response.json();
                console.log('Connected CA data:', caData);
                // For shopkeepers, this is mainly for consistency
                // The actual CA selection is handled in the template
            } else {
                console.error('Failed to load connected CA');
            }
        } catch (error) {
            console.error('Error loading connected CA:', error);
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
        div.className = 'p-4 sm:p-5 hover:bg-slate-50 cursor-pointer transition-all duration-300 client-item border-l-4 border-transparent';
        div.dataset.clientId = client.user_id;
        div.dataset.clientName = client.shop_name;

        const unreadBadge = client.unread_count > 0 ? 
            `<span class="ml-auto bg-blue-500 text-white text-xs font-semibold rounded-full px-2 py-1 shadow-md">${client.unread_count}</span>` : '';

        const lastMessage = client.last_message ? 
            `<p class="text-sm text-slate-500 truncate font-medium">${client.last_message.text}</p>` :
            '<p class="text-sm text-slate-400 italic">No messages yet</p>';

        div.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center flex-1 min-w-0 space-x-3">
                    <div class="relative flex-shrink-0">
                        <div class="w-11 h-11 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-lg">
                            ${client.shop_name.charAt(0).toUpperCase()}
                        </div>
                        ${client.unread_count > 0 ? '<div class="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>' : ''}
                    </div>
                    <div class="min-w-0 flex-1">
                        <h3 class="font-semibold text-slate-800 truncate text-base">${client.shop_name}</h3>
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
        this.elements.messageInputArea.style.display = 'block';
        this.elements.messagesList.style.display = 'block';

        // Mobile navigation: Show chat panel on mobile when client is selected
        if (window.innerWidth < 768) {
            const clientsPanel = document.getElementById('clients-panel');
            const chatPanel = document.getElementById('chat-panel');
            if (clientsPanel && chatPanel) {
                clientsPanel.classList.add('hidden');
                chatPanel.classList.remove('hidden');
                chatPanel.classList.add('flex');
            }
        }

        // Load conversation
        await this.loadConversation(clientId);

        // Mark messages as read
        await this.markMessagesAsRead(clientId);
    },

    async loadConversation(clientId) {
        try {
            const url = `/api/messages/conversation/${clientId}?type=${this.config.currentMessageType}&limit=50`;
            console.log('Loading conversation from URL:', url);
            const response = await fetch(url);
            
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Response data:', data);
                
                // Handle both array response and object response with messages property
                const messages = Array.isArray(data) ? data : (data.messages || []);
                console.log('Processed messages:', messages);
                
                this.renderMessages(messages);
            } else {
                const errorText = await response.text();
                console.error('Error response:', errorText);
                this.showError('Failed to load conversation');
            }
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showError('Failed to load conversation');
        }
    },

    renderMessages(messages) {
        console.log('renderMessages called with:', messages);
        const container = this.elements.messagesList;
        container.innerHTML = '';

        // Ensure messages is an array
        if (!Array.isArray(messages)) {
            console.error('Messages is not an array:', messages);
            messages = [];
        }

        if (messages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-slate-500 py-12 px-4">
                    <div class="max-w-sm mx-auto">
                        <i data-feather="message-circle" class="w-16 h-16 mx-auto mb-4 text-slate-300"></i>
                        <h3 class="text-lg font-medium mb-2">No ${this.config.currentMessageType === 'chat' ? 'messages' : 'remarks'} yet</h3>
                        <p class="text-sm text-slate-400">Start the conversation by sending a message!</p>
                    </div>
                </div>
            `;
            feather.replace();
            return;
        }

        // Sort messages by timestamp (oldest first - normal chronological order)
        const sortedMessages = messages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Add messages in normal order (oldest to newest) with proper spacing
        sortedMessages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            container.appendChild(messageElement);
        });

        // Scroll to bottom to show latest messages (like WhatsApp)
        this.scrollToBottomInstant();
        feather.replace();
    },

    createMessageElement(message) {
        const div = document.createElement('div');
        const isOwn = message.sender_id == this.config.userId;
        const messageClass = isOwn ? 'sent' : 'received';
        
        // Clean responsive styling for message bubbles
        div.className = `message-bubble ${messageClass} ${message.message_type === 'remark' ? 'remark' : ''} mb-4 flex ${isOwn ? 'justify-end' : 'justify-start'} px-3 sm:px-4`;

        const time = new Date(message.timestamp).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });

        let billPreview = '';
        if (message.bill && message.message_type === 'remark') {
            const billDate = message.bill.bill_date ? 
                new Date(message.bill.bill_date).toLocaleDateString() : 'N/A';
            
            // Determine the correct route based on user role
            const billRoute = this.config.userRole === 'CA' ? 
                `/ca/bill/${message.bill.id}` : 
                `/shopkeeper/bill/${message.bill.id}`;
            
            billPreview = `
                <div class="bill-preview mt-3 p-3 bg-white bg-opacity-15 rounded-lg border border-white border-opacity-25">
                    <div class="flex items-center justify-between">
                        <div>
                            <a href="${billRoute}" class="text-gray-600 hover:text-gray-700 font-medium text-sm p-2">
                                📄 View Bill #${message.bill.bill_number || message.bill.id}
                            </a>
                            <p class="text-xs text-gray-600 text-opacity-90 mt-1 p-1">
                                ₹${message.bill.total_amount} • ${billDate}
                            </p>
                        </div>
                    </div>
                </div>
            `;
        }

        // Professional message bubble design with consistent app styling
        let bubbleClasses = isOwn 
            ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white shadow-lg border border-blue-400' 
            : 'bg-white text-slate-800 shadow-md border border-slate-200';
        
        const bubbleShape = isOwn 
            ? 'rounded-2xl rounded-br-sm' 
            : 'rounded-2xl rounded-bl-sm';

        // Remark styling override
        if (message.message_type === 'remark') {
            if (isOwn) {
                bubbleClasses = 'bg-gradient-to-br from-purple-500 to-purple-600 text-white shadow-lg border border-purple-400';
            } else {
                bubbleClasses = 'bg-gradient-to-br from-slate-100 to-slate-200 text-slate-800 shadow-md border border-slate-300';
            }
        }

        div.innerHTML = `
            <div class="message-content relative max-w-[80%] sm:max-w-sm md:max-w-lg lg:max-w-xl p-4 ${bubbleClasses} ${bubbleShape}">
                <div class="message-text pr-14">
                    <p class="whitespace-pre-wrap break-words text-sm sm:text-base leading-relaxed">${this.escapeHtml(message.message)}</p>
                    ${billPreview}
                </div>
                <div class="absolute bottom-2 right-2">
                    <div class="message-time text-xs ${isOwn ? 'text-white text-opacity-80' : 'text-slate-500'} flex items-center space-x-1">
                        <span>${time}</span>
                    </div>
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
                
                // Reload conversation and scroll to new message
                await this.loadConversation(this.config.selectedClientId);
                this.scrollToBottom();
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
                    this.scrollToBottom();
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

    // Smooth scroll to bottom for new messages
    scrollToBottom() {
        const container = this.elements.messagesContainer;
        if (container) {
            setTimeout(() => {
                container.scrollTo({
                    top: container.scrollHeight,
                    behavior: 'smooth'
                });
            }, 100);
        }
    },

    // Instant scroll to bottom for initial load
    scrollToBottomInstant() {
        const container = this.elements.messagesContainer;
        if (container) {
            setTimeout(() => {
                container.scrollTop = container.scrollHeight;
            },1);
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