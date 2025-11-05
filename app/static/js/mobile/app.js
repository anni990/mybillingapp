// Mobile App Core functionality
const MobileApp = {
    init() {
        console.log('🚀 MyBillingApp Mobile initialized');
        this.initializeFeatherIcons();
        this.setupEventListeners();
        this.preventBodyScroll();
        this.initializeUserMenu();
    },

    initializeFeatherIcons() {
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    },

    setupEventListeners() {
        // Close modals on outside click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                this.closeAllModals();
            }
        });

        // Close user menu on outside click
        document.addEventListener('click', (e) => {
            const userMenu = document.getElementById('user-menu');
            const menuButton = e.target.closest('[onclick*="toggleUserMenu"]');
            
            if (userMenu && !menuButton && !userMenu.contains(e.target)) {
                this.hideUserMenu();
            }
        });

        // Handle back button
        window.addEventListener('popstate', (e) => {
            this.closeAllModals();
        });
    },

    preventBodyScroll() {
        // Prevent body scrolling on mobile
        document.body.addEventListener('touchmove', (e) => {
            if (!e.target.closest('.custom-scroll')) {
                e.preventDefault();
            }
        }, { passive: false });

        // Prevent overscroll
        document.body.style.overscrollBehavior = 'contain';
    },

    initializeUserMenu() {
        const userMenu = document.getElementById('user-menu');
        if (userMenu) {
            userMenu.style.display = 'none';
        }
    },

    // Modal Management
    showLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.classList.add('no-scroll');
        }
    },

    hideLoginModal() {
        const modal = document.getElementById('loginModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.classList.remove('no-scroll');
        }
    },

    showFeatureModal() {
        const modal = document.getElementById('featureModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.classList.add('no-scroll');
        }
    },

    hideFeatureModal() {
        const modal = document.getElementById('featureModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.classList.remove('no-scroll');
        }
    },

    showFeatureListModal() {
        const modal = document.getElementById('featureListModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.classList.add('no-scroll');
        }
    },

    hideFeatureListModal() {
        const modal = document.getElementById('featureListModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.classList.remove('no-scroll');
        }
    },

    showLoadingModal() {
        const modal = document.getElementById('loadingModal');
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        }
    },

    hideLoadingModal() {
        const modal = document.getElementById('loadingModal');
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    },

    closeAllModals() {
        this.hideLoginModal();
        this.hideFeatureModal();
        this.hideFeatureListModal();
        this.hideLoadingModal();
        this.hideUserMenu();
    },

    // User Menu Management
    toggleUserMenu() {
        const userMenu = document.getElementById('user-menu');
        if (userMenu) {
            const isHidden = userMenu.classList.contains('hidden');
            if (isHidden) {
                this.showUserMenu();
            } else {
                this.hideUserMenu();
            }
        }
    },

    showUserMenu() {
        const userMenu = document.getElementById('user-menu');
        if (userMenu) {
            userMenu.classList.remove('hidden');
            userMenu.style.display = 'block';
        }
    },

    hideUserMenu() {
        const userMenu = document.getElementById('user-menu');
        if (userMenu) {
            userMenu.classList.add('hidden');
            userMenu.style.display = 'none';
        }
    },

    // Navigation Functions
    goToLogin() {
        this.showLoadingModal();
        setTimeout(() => {
            window.location.href = '/auth/login';
        }, 500);
    },

    goToRegister() {
        this.showLoadingModal();
        setTimeout(() => {
            window.location.href = '/auth/register';
        }, 500);
    },

    goToDashboard() {
        this.showLoadingModal();
        
        // Get authentication status from template variables
        const isAuthenticated = document.querySelector('meta[name="is_authenticated"]')?.content === 'true' ||
                               document.body.dataset.authenticated === 'true';
        
        if (isAuthenticated) {
            // Get user role and redirect accordingly
            const userRole = document.querySelector('meta[name="user_role"]')?.content ||
                           document.body.dataset.userRole;
            
            let dashboardUrl = '/dashboard'; // fallback
            
            switch(userRole) {
                case 'shopkeeper':
                    dashboardUrl = '/shopkeeper/dashboard';
                    break;
                case 'CA':
                    dashboardUrl = '/ca/dashboard';
                    break;
                case 'employee':
                    dashboardUrl = '/ca/employee_dashboard';
                    break;
                default:
                    dashboardUrl = '/dashboard'; // Let server handle redirection
            }
            
            setTimeout(() => {
                window.location.href = dashboardUrl;
            }, 500);
        } else {
            this.hideLoadingModal();
            this.showLoginModal();
        }
    },

    goToProfile() {
        this.hideUserMenu();
        this.showLoadingModal();
        // Implement profile navigation based on user role
        setTimeout(() => {
            // This would be dynamic based on user role
            window.location.href = '/profile';
        }, 500);
    },

    logout() {
        this.hideUserMenu();
        this.showLoadingModal();
        setTimeout(() => {
            window.location.href = '/auth/logout';
        }, 500);
    },

    // Utility Functions
    updateHeaderTitle(title) {
        const headerTitle = document.getElementById('header-title');
        if (headerTitle) {
            headerTitle.textContent = title;
        }
    },

    showToast(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `fixed top-20 left-4 right-4 p-4 rounded-2xl text-white z-50 slide-down ${
            type === 'success' ? 'bg-green-500' : 
            type === 'error' ? 'bg-red-500' : 
            type === 'warning' ? 'bg-yellow-500' : 
            'bg-blue-500'
        }`;
        toast.innerHTML = `
            <div class="flex items-center space-x-2">
                <i data-feather="${
                    type === 'success' ? 'check-circle' : 
                    type === 'error' ? 'x-circle' : 
                    type === 'warning' ? 'alert-triangle' : 
                    'info'
                }" class="w-5 h-5"></i>
                <span class="font-medium">${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        feather.replace();
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            toast.remove();
        }, 3000);
    },

    // Theme and Appearance
    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('mobile-theme', theme);
    },

    getTheme() {
        return localStorage.getItem('mobile-theme') || 'light';
    }
};

// Initialize when DOM is loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => MobileApp.init());
} else {
    MobileApp.init();
}