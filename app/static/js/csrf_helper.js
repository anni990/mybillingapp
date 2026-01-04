/**
 * Enterprise-Level CSRF Token Helper for MyBillingApp
 * Provides comprehensive CSRF protection for large-scale applications
 */

class EnterpriseCSRFHelper {
    constructor() {
        this.token = null;
        this.config = {
            headerName: 'X-CSRFToken',
            formFieldName: 'csrf_token',
            autoRetry: true,
            retryDelay: 1000,
            maxRetries: 2,
            debugMode: true
        };
        this.init();
    }

    init() {
        // Get CSRF token from multiple sources with priority order
        this.token = window.MyBillingApp?.csrfToken ||
                    window.csrfToken || 
                    document.querySelector('meta[name="csrf-token"]')?.content ||
                    document.querySelector('input[name="csrf_token"]')?.value;
        
        if (!this.token) {
            console.warn('[CSRF Helper] Token not found - requests may fail');
            this.requestNewToken();
        } else if (this.config.debugMode) {
            console.log('[CSRF Helper] Enterprise CSRF protection initialized');
        }
        
        this.setupGlobalFormHandler();
        this.setupGlobalAjaxHandler();
    }

    async requestNewToken() {
        try {
            const response = await fetch('/auth/csrf-token', {
                method: 'GET',
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.token = data.csrf_token;
                this.updateTokenInDOM();
            }
        } catch (error) {
            console.error('[CSRF Helper] Failed to get new token:', error);
        }
    }

    updateTokenInDOM() {
        // Update all CSRF token references in DOM
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) metaTag.content = this.token;
        
        const inputFields = document.querySelectorAll('input[name="csrf_token"]');
        inputFields.forEach(input => input.value = this.token);
        
        if (window.MyBillingApp) {
            window.MyBillingApp.csrfToken = this.token;
        }
    }

    setupGlobalFormHandler() {
        // Automatically add CSRF tokens to all forms
        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (form.method && form.method.toLowerCase() === 'post') {
                this.addTokenToForm(form);
            }
        });
    }

    setupGlobalAjaxHandler() {
        // Override jQuery AJAX if available
        if (typeof $ !== 'undefined' && $.ajaxSetup) {
            $.ajaxSetup({
                beforeSend: (xhr, settings) => {
                    if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                        xhr.setRequestHeader(this.config.headerName, this.token);
                    }
                }
            });
        }
    }

    addTokenToForm(form) {
        if (!form.querySelector(`input[name="${this.config.formFieldName}"]`) && this.token) {
            const tokenInput = document.createElement('input');
            tokenInput.type = 'hidden';
            tokenInput.name = this.config.formFieldName;
            tokenInput.value = this.token;
            form.appendChild(tokenInput);
        }
    }

    getHeaders(existingHeaders = {}) {
        const headers = { ...existingHeaders };
        
        if (this.token && !headers[this.config.headerName] && !headers['X-CSRF-Token']) {
            headers[this.config.headerName] = this.token;
        }
        
        return headers;
    }

    addTokenToFormData(formData) {
        if (formData instanceof FormData && !formData.has(this.config.formFieldName) && this.token) {
            formData.append(this.config.formFieldName, this.token);
        }
        return formData;
    }

    // Enhanced fetch with automatic retry on CSRF errors
    async fetch(url, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        let attempt = 0;
        
        const makeRequest = async () => {
            // Add CSRF token for state-changing requests
            if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
                options.headers = this.getHeaders(options.headers);
                
                if (options.body instanceof FormData) {
                    options.body = this.addTokenToFormData(options.body);
                }
            }
            
            const response = await window.fetch(url, options);
            
            // Handle CSRF errors with automatic retry
            if (response.status === 400 && this.config.autoRetry && attempt < this.config.maxRetries) {
                try {
                    const errorData = await response.clone().json();
                    if (errorData.csrf_error) {
                        console.warn(`[CSRF Helper] CSRF error detected, retrying... (${attempt + 1}/${this.config.maxRetries})`);
                        await new Promise(resolve => setTimeout(resolve, this.config.retryDelay));
                        await this.requestNewToken();
                        attempt++;
                        return makeRequest();
                    }
                } catch (e) {
                    // If response is not JSON, don't retry
                }
            }
            
            return response;
        };
        
        return makeRequest();
    }
}

// Initialize enterprise CSRF helper globally
document.addEventListener('DOMContentLoaded', () => {
    window.enterpriseCSRF = new EnterpriseCSRFHelper();
});

// Fallback for cases where DOMContentLoaded has already fired
if (document.readyState !== 'loading') {
    window.enterpriseCSRF = new EnterpriseCSRFHelper();
}