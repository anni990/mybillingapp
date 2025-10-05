/**
 * Interactive Walkthrough System for MyBillingApp
 * Provides guided tours for first-time users
 */

class WalkthroughManager {
    constructor() {
        this.currentStep = 0;
        this.steps = [];
        this.overlay = null;
        this.tooltip = null;
        this.isActive = false;
        this.onComplete = null;
        this.onSkip = null;
    }

    /**
     * Initialize walkthrough with steps configuration
     * @param {Array} steps - Array of step configurations
     * @param {Object} options - Options including callbacks
     */
    init(steps, options = {}) {
        this.steps = steps;
        this.onComplete = options.onComplete || (() => {});
        this.onSkip = options.onSkip || (() => {});
        this.currentStep = 0;
        
        this.createOverlay();
        this.createTooltip();
    }

    /**
     * Start the walkthrough
     */
    start() {
        if (this.steps.length === 0) return;
        
        this.isActive = true;
        document.body.style.overflow = 'hidden';
        this.overlay.classList.remove('hidden');
        
        // Blur sidebar during walkthrough (except for navigation step)
        this.applySidebarBlur();
        
        // Add smooth entrance animation
        this.overlay.style.opacity = '0';
        setTimeout(() => {
            this.overlay.style.transition = 'opacity 0.3s ease-in-out';
            this.overlay.style.opacity = '1';
        }, 10);
        
        this.showStep(0);
    }

    /**
     * Create the overlay element with transparent blur background
     */
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'walkthrough-overlay fixed inset-0 z-40 hidden pointer-events-none';
        // Create transparent blur effect (no white background)
        this.overlay.innerHTML = '<div class="walkthrough-mask absolute inset-0 backdrop-blur-md bg-opacity-20"></div>';
        document.body.appendChild(this.overlay);
    }

    /**
     * Create the tooltip element
     */
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'walkthrough-tooltip fixed bg-white rounded-xl md:rounded-2xl shadow-xl md:shadow-2xl p-4 md:p-6 max-w-xs md:max-w-sm w-full mx-2 md:mx-4 z-50 pointer-events-auto';
        this.tooltip.style.transform = 'translate(-50%, -50%)';
        this.tooltip.innerHTML = `
                <div class="walkthrough-content">
                <div class="flex items-start justify-between mb-3 md:mb-4">
                    <div class="flex items-center flex-1">
                        <div class="w-8 h-8 md:w-10 md:h-10 bg-gradient-to-r from-orange-400 to-orange-600 rounded-full flex items-center justify-center mr-2 md:mr-3 flex-shrink-0">
                            <i data-feather="compass" class="w-4 h-4 md:w-5 md:h-5 text-white"></i>
                        </div>
                        <div class="min-w-0">
                            <h3 class="font-bold text-gray-900 walkthrough-title text-sm md:text-base truncate"></h3>
                            <p class="text-xs md:text-sm text-gray-500 walkthrough-counter"></p>
                        </div>
                    </div>
                    <button onclick="walkthrough.skip()" class="text-gray-400 hover:text-gray-600 transition-colors p-1 flex-shrink-0">
                        <i data-feather="x" class="w-4 h-4 md:w-5 md:h-5"></i>
                    </button>
                </div>
                
                <div class="walkthrough-description text-gray-700 mb-4 md:mb-6 leading-relaxed text-sm md:text-base"></div>                <div class="flex flex-col space-y-3 md:flex-row md:items-center md:justify-between md:space-y-0">
                    <div class="flex justify-center md:justify-start space-x-1 md:space-x-2 walkthrough-dots"></div>
                    <div class="flex space-x-2">
                        <button onclick="walkthrough.skip()" class="px-3 py-2 md:px-4 md:py-2 text-gray-600 hover:text-gray-800 transition-colors font-medium text-xs md:text-sm">
                            Skip
                        </button>
                        <button onclick="walkthrough.previous()" class="walkthrough-prev px-3 py-2 md:px-4 md:py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors font-medium hidden text-xs md:text-sm">
                            Back
                        </button>
                        <button onclick="walkthrough.next()" class="walkthrough-next px-4 py-2 md:px-6 md:py-2 bg-gradient-to-r from-orange-400 to-orange-600 hover:from-orange-500 hover:to-orange-700 text-white rounded-lg transition-all duration-300 font-medium shadow-lg text-xs md:text-sm flex-1 md:flex-initial">
                            Next
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(this.tooltip);
    }

    /**
     * Show a specific step
     * @param {number} stepIndex - Index of the step to show
     */
    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) return;
        
        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];
        
        // Special handling for navigation step on mobile
        if (step.element === '#mobile-menu-btn' && window.innerWidth < 768) {
            this.handleMobileNavigation(step);
            return;
        }
        
        // Manage sidebar blur - remove blur for navigation/sidebar steps, apply for others
        this.manageSidebarBlur(step);
        
        // Update tooltip content
        this.tooltip.querySelector('.walkthrough-title').textContent = step.title;
        this.tooltip.querySelector('.walkthrough-description').textContent = step.description;
        this.tooltip.querySelector('.walkthrough-counter').textContent = `Step ${stepIndex + 1} of ${this.steps.length}`;
        
        // Update dots indicator
        this.updateDots();
        
        // Update navigation buttons
        const prevBtn = this.tooltip.querySelector('.walkthrough-prev');
        const nextBtn = this.tooltip.querySelector('.walkthrough-next');
        
        prevBtn.style.display = stepIndex > 0 ? 'block' : 'none';
        nextBtn.textContent = stepIndex === this.steps.length - 1 ? 'Finish' : 'Next';
        
        // Highlight element first
        this.highlightElement(step.element);
        
        // Add entrance animation without overriding positioning
        this.tooltip.style.opacity = '0';
        this.tooltip.style.transform = 'scale(0.9)';
        
        // Position tooltip after initial setup
        setTimeout(() => {
            this.positionTooltip(step);
        }, 10);
        
        // Animate in
        setTimeout(() => {
            this.tooltip.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
            this.tooltip.style.transform = 'scale(1)';
            this.tooltip.style.opacity = '1';
        }, 50);
        
        // Re-initialize feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }

    /**
     * Update progress dots
     */
    updateDots() {
        const dotsContainer = this.tooltip.querySelector('.walkthrough-dots');
        dotsContainer.innerHTML = '';
        
        for (let i = 0; i < this.steps.length; i++) {
            const dot = document.createElement('div');
            dot.className = `w-2 h-2 rounded-full transition-all duration-300 ${
                i === this.currentStep 
                    ? 'bg-orange-500 w-6' 
                    : i < this.currentStep 
                        ? 'bg-orange-300' 
                        : 'bg-gray-300'
            }`;
            dotsContainer.appendChild(dot);
        }
    }

    /**
     * Position tooltip relative to target element
     * @param {Object} step - Step configuration
     */
    positionTooltip(step) {
        const element = step.element ? document.querySelector(step.element) : null;
        
        // Handle center positioning for final step or when no element specified
        if (step.position === 'center' || !step.element) {
            this.tooltip.style.position = 'fixed';
            this.tooltip.style.top = '50%';
            this.tooltip.style.left = '50%';
            this.tooltip.style.transform = 'translate(-50%, -50%)';
            return;
        }
        
        if (!element) {
            // Default center position if element not found
            this.tooltip.style.position = 'fixed';
            this.tooltip.style.top = '50%';
            this.tooltip.style.left = '50%';
            this.tooltip.style.transform = 'translate(-50%, -50%)';
            return;
        }

        // Ensure tooltip is positioned fixed for proper calculation
        this.tooltip.style.position = 'fixed';
        this.tooltip.style.visibility = 'hidden';
        this.tooltip.style.display = 'block';
        
        const rect = element.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const padding = 15; // Space between element and tooltip
        const safeMargin = 10; // Minimum margin from window edges
        
        let top, left;
        let finalPosition = step.position || 'bottom';

        // Try preferred position first
        switch (finalPosition) {
            case 'top':
                top = rect.top - tooltipRect.height - padding;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                // If tooltip goes above viewport, switch to bottom
                if (top < safeMargin) {
                    finalPosition = 'bottom';
                    top = rect.bottom + padding;
                }
                break;
            case 'bottom':
                top = rect.bottom + padding;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                // If tooltip goes below viewport, switch to top
                if (top + tooltipRect.height > windowHeight - safeMargin) {
                    finalPosition = 'top';
                    top = rect.top - tooltipRect.height - padding;
                }
                break;
            case 'left':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.left - tooltipRect.width - padding;
                // If tooltip goes off left edge, switch to right
                if (left < safeMargin) {
                    finalPosition = 'right';
                    left = rect.right + padding;
                }
                break;
            case 'right':
                top = rect.top + (rect.height / 2) - (tooltipRect.height / 2);
                left = rect.right + padding;
                // If tooltip goes off right edge, switch to left
                if (left + tooltipRect.width > windowWidth - safeMargin) {
                    finalPosition = 'left';
                    left = rect.left - tooltipRect.width - padding;
                }
                break;
            case 'bottom-left':
                top = rect.bottom + padding;
                left = rect.left;
                // If tooltip goes below viewport, switch to top-left
                if (top + tooltipRect.height > windowHeight - safeMargin) {
                    top = rect.top - tooltipRect.height - padding;
                }
                break;
            default:
                finalPosition = 'bottom';
                top = rect.bottom + padding;
                left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        }

        // Final bounds checking - ensure tooltip stays within viewport
        // Horizontal bounds
        if (left < safeMargin) {
            left = safeMargin;
        } else if (left + tooltipRect.width > windowWidth - safeMargin) {
            left = windowWidth - tooltipRect.width - safeMargin;
        }

        // Vertical bounds
        if (top < safeMargin) {
            top = safeMargin;
        } else if (top + tooltipRect.height > windowHeight - safeMargin) {
            top = windowHeight - tooltipRect.height - safeMargin;
        }

        // Apply positioning
        this.tooltip.style.top = `${Math.max(safeMargin, top)}px`;
        this.tooltip.style.left = `${Math.max(safeMargin, left)}px`;
        this.tooltip.style.transform = 'none';
        this.tooltip.style.visibility = 'visible';
    }

    /**
     * Highlight target element
     * @param {string} selector - CSS selector for element to highlight
     */
    highlightElement(selector) {
        // Remove previous highlights
        this.clearHighlights();

        const element = document.querySelector(selector);
        if (element) {
            // Create spotlight effect
            this.createSpotlight(element);
            
            // Scroll element into view smoothly
            setTimeout(() => {
                element.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center',
                    inline: 'center'
                });
            }, 100);
        } else {
            // If element not found, just clear highlights
            this.clearHighlights();
        }
    }

    /**
     * Go to next step
     */
    next() {
        // Close mobile sidebar if it was opened for navigation step
        if (this.shouldCloseMobileSidebar && window.innerWidth < 768) {
            const mobileMenuBtn = document.querySelector('#mobile-menu-btn');
            
            if (mobileMenuBtn) {
                mobileMenuBtn.click(); // Close sidebar
                
                // Reapply sidebar blur after closing mobile sidebar
                setTimeout(() => {
                    this.applySidebarBlur();
                }, 300);
            }
            this.shouldCloseMobileSidebar = false;
        }
        
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        } else {
            this.complete();
        }
    }

    /**
     * Go to previous step
     */
    previous() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    /**
     * Skip walkthrough
     */
    skip() {
        this.cleanup();
        this.onSkip();
        this.markWalkthroughCompleted();
    }

    /**
     * Complete walkthrough
     */
    complete() {
        this.cleanup();
        this.onComplete();
        this.markWalkthroughCompleted();
    }

    /**
     * Handle mobile navigation step - auto open sidebar
     */
    handleMobileNavigation(step) {
        // First update tooltip content for this special step
        this.tooltip.querySelector('.walkthrough-title').textContent = step.title;
        this.tooltip.querySelector('.walkthrough-description').textContent = step.description;
        this.tooltip.querySelector('.walkthrough-counter').textContent = `Step ${this.currentStep + 1} of ${this.steps.length}`;
        
        // Update dots and navigation buttons
        this.updateDots();
        const prevButton = this.tooltip.querySelector('.walkthrough-prev');
        const nextButton = this.tooltip.querySelector('.walkthrough-next');
        prevButton.style.display = this.currentStep > 0 ? 'block' : 'none';
        nextButton.textContent = this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next';
        
        // Open mobile sidebar if it exists
        const menuButton = document.getElementById('mobile-menu-btn');
        const sidebarElement = document.getElementById('sidebar');
        
        if (menuButton && sidebarElement) {
            // Open the mobile sidebar
            menuButton.click();
            
            // Wait for sidebar to open, then highlight it
            setTimeout(() => {
                this.highlightElement('#sidebar');
                this.positionTooltip(step);
                
                // Show tooltip with animation
                this.tooltip.style.opacity = '0';
                this.tooltip.style.transform = 'scale(0.9)';
                setTimeout(() => {
                    this.tooltip.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
                    this.tooltip.style.transform = 'scale(1)';
                    this.tooltip.style.opacity = '1';
                }, 50);
            }, 300);
        } else {
            // Fallback to regular step handling
            this.highlightElement(step.element);
            this.positionTooltip(step);
        }
        this.updateDots();
        const prevBtn = this.tooltip.querySelector('.walkthrough-prev');
        const nextBtn = this.tooltip.querySelector('.walkthrough-next');
        prevBtn.style.display = this.currentStep > 0 ? 'block' : 'none';
        nextBtn.textContent = this.currentStep === this.steps.length - 1 ? 'Finish' : 'Next';
        
        // Look for mobile menu button (hamburger menu)
        const mobileMenuBtn = document.querySelector('#mobile-menu-btn');
        
        if (mobileMenuBtn && window.getComputedStyle(mobileMenuBtn).display !== 'none') {
            // Remove sidebar blur for navigation step
            this.removeSidebarBlur();
            
            // Click to open mobile sidebar
            mobileMenuBtn.click();
            
            // Wait for sidebar animation, then highlight and position tooltip
            setTimeout(() => {
                this.highlightElement(step.element);
                this.positionTooltip(step);
                
                // Store flag to close sidebar when moving to next step
                this.shouldCloseMobileSidebar = true;
            }, 300);
        } else {
            // Fallback if no mobile menu button found
            this.removeSidebarBlur();
            this.highlightElement(step.element);
            this.positionTooltip(step);
        }
    }

    /**
     * Clean up walkthrough elements
     */
    cleanup() {
        this.isActive = false;
        document.body.style.overflow = '';
        
        // Clear all highlights
        this.clearHighlights();
        
        // Remove sidebar blur when walkthrough ends
        this.removeSidebarBlur();
        
        // Fade out and remove overlay
        if (this.overlay) {
            this.overlay.style.transition = 'opacity 0.3s ease-in-out';
            this.overlay.style.opacity = '0';
            
            setTimeout(() => {
                if (this.overlay && this.overlay.parentNode) {
                    this.overlay.parentNode.removeChild(this.overlay);
                }
                if (this.tooltip && this.tooltip.parentNode) {
                    this.tooltip.parentNode.removeChild(this.tooltip);
                }
            }, 300);
        }
    }

    /**
     * Mark walkthrough as completed for the user
     */
    markWalkthroughCompleted() {
        fetch('/api/mark_walkthrough_completed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify({ completed: true })
        }).catch(error => {
            console.log('Could not mark walkthrough as completed:', error);
        });
        
        // Also store in localStorage as backup
        localStorage.setItem('walkthrough_completed', 'true');
    }

    /**
     * Create spotlight effect for highlighted element
     */
    createSpotlight(element) {
        // Store original styles for restoration
        const originalStyles = {
            position: element.style.position,
            zIndex: element.style.zIndex,
            backgroundColor: element.style.backgroundColor
        };
        
        // Store original styles as data attributes for later restoration
        element.dataset.originalPosition = originalStyles.position;
        element.dataset.originalZIndex = originalStyles.zIndex;
        element.dataset.originalBackgroundColor = originalStyles.backgroundColor;
        
        // Apply highlight styles
        element.classList.add('walkthrough-highlight');
        element.style.position = 'relative';
        element.style.zIndex = '42';
    }
    
    /**
     * Clear all highlights and spotlight effects
     */
    clearHighlights() {
        // Remove highlight classes and restore original styles
        document.querySelectorAll('.walkthrough-highlight').forEach(el => {
            el.classList.remove('walkthrough-highlight');
            
            // Restore original styles from data attributes
            if (el.dataset.originalPosition !== undefined) {
                el.style.position = el.dataset.originalPosition;
                delete el.dataset.originalPosition;
            }
            if (el.dataset.originalZIndex !== undefined) {
                el.style.zIndex = el.dataset.originalZIndex;
                delete el.dataset.originalZIndex;
            }
            if (el.dataset.originalBackgroundColor !== undefined) {
                el.style.backgroundColor = el.dataset.originalBackgroundColor;
                delete el.dataset.originalBackgroundColor;
            }
        });
        
        // Remove spotlight elements
        document.querySelectorAll('.walkthrough-spotlight').forEach(el => {
            el.remove();
        });
    }

    /**
     * Handle mobile navigation step - auto open sidebar
     */
    handleMobileNavigation(step) {
        const mobileMenuBtn = document.querySelector('[data-mobile-menu-btn]');
        const sidebar = document.querySelector('#sidebar');
        
        if (mobileMenuBtn && sidebar) {
            // Open mobile sidebar
            mobileMenuBtn.click();
            
            // Wait for sidebar animation, then highlight and position tooltip
            setTimeout(() => {
                this.highlightElement(step.element);
                this.updateTooltipContent(step);
                
                setTimeout(() => {
                    this.positionTooltip(step);
                }, 100);
                
                // Auto-close sidebar when moving to next step
                this.autoCloseSidebarOnNext = true;
            }, 300);
        } else {
            // Fallback for regular highlighting
            this.highlightElement(step.element);
            this.updateTooltipContent(step);
            setTimeout(() => {
                this.positionTooltip(step);
            }, 100);
        }
    }

    /**
     * Apply blur effect to sidebar during walkthrough
     */
    applySidebarBlur() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.style.filter = 'blur(5px)';
            sidebar.style.transition = 'filter 0.3s ease-in-out';
        }
    }
    
    /**
     * Remove blur effect from sidebar
     */
    removeSidebarBlur() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.style.filter = 'none';
        }
    }
    
    /**
     * Manage sidebar blur based on current step
     * @param {Object} step - Current step configuration
     */
    manageSidebarBlur(step) {
        // Check if current step is targeting sidebar/navigation elements
        const isSidebarStep = step.element === '#sidebar' || 
                             step.element === '#mobile-menu-btn' ||
                             (step.element && step.element.includes('sidebar'));
        
        if (isSidebarStep) {
            this.removeSidebarBlur();
        } else {
            this.applySidebarBlur();
        }
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }

    // shouldShow method removed - using direct window.showWalkthrough check for cleaner logic
}

// Initialize global walkthrough instance
window.walkthrough = new WalkthroughManager();

// Shopkeeper Dashboard Walkthrough Configuration
const isMobileDevice = window.innerWidth < 768;

const shopkeeperWalkthroughSteps = [
    {
        title: isMobileDevice ? "Welcome! 🎉" : "Welcome to MyBillingApp!",
        description: isMobileDevice ? 
            "Quick tour to help you get started!" : 
            "Let's take a quick tour of your dashboard. This will help you understand all the features available to manage your business efficiently.",
        element: ".mb-6.md\\:mb-8 h1, h1", // Dashboard title
        position: "bottom"
    },
    {
        title: isMobileDevice ? "Key Metrics 📊" : "Business Metrics at a Glance",
        description: isMobileDevice ?
            "View revenue, bills, and stock alerts here." :
            "Here you can see key performance indicators - today's revenue, total bills, stock alerts, and your CA connection status. These cards give you instant insights into your business performance.",
        element: "[data-walkthrough='stats-cards']",
        position: "bottom"
    },
    {
        title: isMobileDevice ? "Quick Actions ⚡" : "Quick Actions Hub",
        description: isMobileDevice ?
            "Create bills, manage inventory, and view reports." :
            "These are your most-used features! Create bills, manage existing ones, check inventory, and view reports. Everything you need for daily operations is just one click away.",
        element: "[data-walkthrough='quick-actions']",
        position: "bottom"
    },
    {
        title: isMobileDevice ? "Sales Chart 📈" : "Sales Trends & Analytics",
        description: isMobileDevice ?
            "Track your monthly sales performance." :
            "Track your business performance over time with this interactive chart. Monitor monthly sales trends to make informed business decisions.",
        element: "#monthlySalesChart",
        position: "right"
    },
    {
        title: isMobileDevice ? "Recent Bills 📋" : "Recent Activity",
        description: isMobileDevice ?
            "View your latest transactions and bills." :
            "Keep track of your latest transactions here. Quick access to recent bills with payment status and customer information. Click 'View All' to see your complete bill history.",
        element: "[data-walkthrough='recent-bills']",
        position: "left"
    },
    {
        title: isMobileDevice ? "CA Connect 🤝" : "Connect with CAs",
        description: isMobileDevice ?
            "Connect with Chartered Accountants for GST help." :
            "Connect with Chartered Accountants to streamline your GST compliance and financial management. If not connected yet, click here to browse available CAs in the marketplace.",
        element: "[data-walkthrough='ca-connect']",
        position: isMobileDevice ? "bottom" : "left"
    },
    {
        title: isMobileDevice ? "Navigation 🧭" : "Navigation & Settings",
        description: isMobileDevice ?
            "Access all features from the sidebar menu. Tap to open/close on mobile." :
            "The sidebar navigation on the left contains all your app features. Use it to access billing, inventory management, customer records, reports, and settings. The menu stays with you on every page.",
        element: isMobileDevice ? "#mobile-menu-btn" : "#sidebar",
        position: isMobileDevice ? "bottom" : "right"
    },
    {
        title: isMobileDevice ? "Profile ⚙️" : "Profile & Account",
        description: isMobileDevice ?
            "Manage account settings and preferences." :
            "Manage your account settings, business information, and preferences from here. You can also log out or switch between different views if you have multiple roles.",
        element: "[data-walkthrough='profile']",
        position: isMobileDevice ? "bottom" : "bottom-left"
    },
    {
        title: isMobileDevice ? "Ready to Go! 🚀" : "You're Ready to Go!",
        description: isMobileDevice ?
            "Tour complete! Use the profile menu to replay anytime." :
            "That completes the tour! You now know the key features of MyBillingApp. Start by creating your first bill or adding products to inventory. Need help anytime? Look for the compass icon to replay this tour.",
        element: null,
        position: "top"
    }
];

// Auto-start walkthrough for first-time users
document.addEventListener('DOMContentLoaded', function() {
    // Add walkthrough-specific CSS
    const walkthroughCSS = `
        .walkthrough-highlight {
            position: relative;
            z-index: 45;
            box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.4), 0 0 0 8px rgba(249, 115, 22, 0.2);
            border-radius: 8px;
            transition: all 0.3s ease-in-out;
            animation: walkthrough-pulse 2s infinite;
        }
        
        @keyframes walkthrough-pulse {
            0% { box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.4), 0 0 0 8px rgba(249, 115, 22, 0.2); }
            50% { box-shadow: 0 0 0 6px rgba(249, 115, 22, 0.6), 0 0 0 12px rgba(249, 115, 22, 0.1); }
            100% { box-shadow: 0 0 0 4px rgba(249, 115, 22, 0.4), 0 0 0 8px rgba(249, 115, 22, 0.2); }
        }
        
        .walkthrough-tooltip {
            animation: walkthrough-entrance 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        
        @keyframes walkthrough-entrance {
            0% {
                opacity: 0;
                transform: translate(-50%, -50%) scale(0.8) rotateY(90deg);
            }
            100% {
                opacity: 1;
                transform: translate(-50%, -50%) scale(1) rotateY(0deg);
            }
        }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = walkthroughCSS;
    document.head.appendChild(styleSheet);

    
    
    // Auto-start walkthrough for first-time users
    // Check if server indicates this user should see walkthrough (walkthrough_completed = 0)
    console.log('\n=== JS WALKTHROUGH CHECK ===');
    console.log('window.showWalkthrough type:', typeof window.showWalkthrough);
    console.log('window.showWalkthrough value:', window.showWalkthrough);
    
    // FOOLPROOF CHECK: Show walkthrough based on server decision
    // User requirement: "if walkthrough_completed = 0 then auto_start otherwise not"
    const shouldShowWalkthrough = (window.showWalkthrough === true || 
                                  window.showWalkthrough === 'true' ||
                                  window.showWalkthrough === "true");
    
    console.log('Final shouldShowWalkthrough decision:', shouldShowWalkthrough);
    console.log('Decision based on window.showWalkthrough:', window.showWalkthrough);
    console.log('===========================\n');
    
    if (shouldShowWalkthrough) {
        console.log('Auto-starting walkthrough for first-time user...');
        
        // Delay to ensure page is fully loaded
        setTimeout(() => {
            window.walkthrough.init(shopkeeperWalkthroughSteps, {
                onComplete: () => {
                    console.log('Walkthrough completed!');
                    // Mark walkthrough as completed on server (set walkthrough_completed = 1)
                    fetch('/api/walkthrough/complete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': window.walkthrough.getCSRFToken()
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log('Walkthrough completion saved to database');
                        } else {
                            console.error('Failed to save walkthrough completion:', data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error saving walkthrough completion:', error);
                    });
                },
                onSkip: () => {
                    console.log('Walkthrough skipped!');
                    // Mark walkthrough as completed even if skipped (set walkthrough_completed = 1)
                    fetch('/api/walkthrough/complete', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': window.walkthrough.getCSRFToken()
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            console.log('Walkthrough skip saved to database');
                        } else {
                            console.error('Failed to save walkthrough skip:', data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error saving walkthrough skip:', error);
                    });
                }
            });
            window.walkthrough.start();
        }, 1500); // Slightly longer delay for better UX
    } else {
        console.log('Walkthrough NOT STARTING');
        console.log('Reason: window.showWalkthrough =', window.showWalkthrough);
        console.log('Type:', typeof window.showWalkthrough);
        
        if (window.showWalkthrough === undefined) {
            console.error('CRITICAL ERROR: window.showWalkthrough is undefined!');
            console.error('This means the dashboard route did not pass show_walkthrough to template');
        }
    }
});

// Export for manual triggering (can be called from console or profile menu)
window.startWalkthrough = function() {
    if (window.walkthrough && window.walkthrough.isActive) {
        console.log('Walkthrough already active');
        return;
    }
    window.walkthrough.init(shopkeeperWalkthroughSteps, {
        onComplete: () => {
            console.log('Manual walkthrough completed!');
        },
        onSkip: () => {
            console.log('Manual walkthrough skipped!');
        }
    });
    window.walkthrough.start();
};

// Reset walkthrough for testing
window.resetWalkthrough = function() {
    fetch('/api/reset_walkthrough', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.walkthrough.getCSRFToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            localStorage.removeItem('walkthrough_completed');
            alert('Walkthrough reset! Refresh the page to see it again.');
        } else {
            alert('Error resetting walkthrough: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Reset error:', error);
        alert('Error resetting walkthrough');
    });
};