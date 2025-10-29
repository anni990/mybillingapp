// Mobile Navigation Controller
const MobileNav = {
    currentSection: 'home',
    sections: ['home', 'features', 'about'],

    init() {
        this.updateNavigation();
        this.setupSwipeGestures();
    },

    showSection(sectionName) {
        if (!this.sections.includes(sectionName)) {
            console.warn(`Section ${sectionName} not found`);
            return;
        }

        // Hide all sections
        this.sections.forEach(section => {
            const element = document.getElementById(`${section}-section`);
            if (element) {
                element.classList.add('hidden');
                element.classList.remove('fade-in');
            }
        });

        // Show target section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.remove('hidden');
            targetSection.classList.add('fade-in');
        }

        // Update current section
        this.currentSection = sectionName;
        this.updateNavigation();
        this.updateHeaderTitle(sectionName);

        // Scroll to top of the section
        if (targetSection) {
            targetSection.scrollTop = 0;
        }
    },

    updateNavigation() {
        // Reset all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Activate current nav item
        const activeNav = document.getElementById(`nav-${this.currentSection}`);
        if (activeNav) {
            activeNav.classList.add('active');
        }
    },

    updateHeaderTitle(sectionName) {
        const titleMap = {
            home: 'MyBillingApp',
            features: 'Features',
            about: 'About Us'
        };
        
        const title = titleMap[sectionName] || 'MyBillingApp';
        MobileApp.updateHeaderTitle(title);
    },

    // Swipe gesture support
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        let isScrolling = false;

        document.addEventListener('touchstart', (e) => {
            const touch = e.touches[0];
            startX = touch.clientX;
            startY = touch.clientY;
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!startX || !startY) return;

            const touch = e.touches[0];
            const diffX = startX - touch.clientX;
            const diffY = startY - touch.clientY;

            // Determine if user is scrolling vertically
            if (Math.abs(diffY) > Math.abs(diffX)) {
                isScrolling = true;
                return;
            }

            isScrolling = false;
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            if (!startX || !startY || isScrolling) {
                startX = 0;
                startY = 0;
                isScrolling = false;
                return;
            }

            const touch = e.changedTouches[0];
            const diffX = startX - touch.clientX;
            const threshold = 50;

            if (Math.abs(diffX) > threshold) {
                if (diffX > 0) {
                    // Swipe left - next section
                    this.navigateNext();
                } else {
                    // Swipe right - previous section
                    this.navigatePrevious();
                }
            }

            startX = 0;
            startY = 0;
            isScrolling = false;
        }, { passive: true });
    },

    navigateNext() {
        const currentIndex = this.sections.indexOf(this.currentSection);
        const nextIndex = (currentIndex + 1) % this.sections.length;
        this.showSection(this.sections[nextIndex]);
    },

    navigatePrevious() {
        const currentIndex = this.sections.indexOf(this.currentSection);
        const prevIndex = currentIndex === 0 ? this.sections.length - 1 : currentIndex - 1;
        this.showSection(this.sections[prevIndex]);
    },

    // Keyboard navigation support
    handleKeyNavigation(event) {
        switch(event.key) {
            case 'ArrowLeft':
                event.preventDefault();
                this.navigatePrevious();
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.navigateNext();
                break;
            case 'Escape':
                MobileApp.closeAllModals();
                break;
        }
    }
};

// Initialize navigation
document.addEventListener('DOMContentLoaded', () => {
    MobileNav.init();
    
    // Add keyboard navigation
    document.addEventListener('keydown', (e) => {
        MobileNav.handleKeyNavigation(e);
    });
});

// Handle browser back/forward buttons
window.addEventListener('popstate', (e) => {
    const section = e.state?.section || 'home';
    MobileNav.showSection(section);
});

// Update browser history when navigating
const originalShowSection = MobileNav.showSection;
MobileNav.showSection = function(sectionName) {
    originalShowSection.call(this, sectionName);
    
    // Update browser history
    const title = `MyBillingApp - ${sectionName.charAt(0).toUpperCase() + sectionName.slice(1)}`;
    const url = `/mobile-view#${sectionName}`;
    
    if (history.pushState) {
        history.pushState({ section: sectionName }, title, url);
    }
};