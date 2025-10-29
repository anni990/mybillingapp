// Mobile Features Controller
const MobileFeatures = {
    // Feature detail content
    featureDetails: {
        billing: {
            title: 'Smart Billing',
            icon: 'file-text',
            gradient: 'gradient-primary',
            content: `
                <div class="space-y-4">
                    <div class="text-center mb-4">
                        <p class="text-body text-gray-600">Create professional GST-compliant bills in seconds</p>
                    </div>
                    
                    <div class="space-y-3">
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-primary rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="zap" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Quick Bill Creation</h4>
                                <p class="text-caption text-gray-600">Generate bills with product search, auto-calculations, and multiple templates</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-success rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="percent" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">GST Compliance</h4>
                                <p class="text-caption text-gray-600">Automatic GST calculations for all tax slabs (0%, 5%, 12%, 18%, 28%)</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-blue rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="credit-card" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Payment Tracking</h4>
                                <p class="text-caption text-gray-600">Track paid, unpaid, and partially paid bills with reminders</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-purple rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="printer" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Professional Templates</h4>
                                <p class="text-caption text-gray-600">Multiple bill formats with your business branding</p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        },
        
        inventory: {
            title: 'Inventory Management',
            icon: 'package',
            gradient: 'gradient-secondary',
            content: `
                <div class="space-y-4">
                    <div class="text-center mb-4">
                        <p class="text-body text-gray-600">Complete stock management solution</p>
                    </div>
                    
                    <div class="space-y-3">
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-secondary rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="database" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Product Catalog</h4>
                                <p class="text-caption text-gray-600">Organize products with categories, SKUs, pricing, and stock levels</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-warning rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="alert-triangle" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Low Stock Alerts</h4>
                                <p class="text-caption text-gray-600">Get notified when products are running low with customizable thresholds</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-purple rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="trending-up" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Stock Reports</h4>
                                <p class="text-caption text-gray-600">Analyze inventory trends, bestsellers, and optimize stock levels</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-teal rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="refresh-cw" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Auto Stock Updates</h4>
                                <p class="text-caption text-gray-600">Automatic stock deduction when bills are created</p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        },

        customers: {
            title: 'Customer Management',
            icon: 'users',
            gradient: 'gradient-success',
            content: `
                <div class="space-y-4">
                    <div class="text-center mb-4">
                        <p class="text-body text-gray-600">Digital khata system for customer relationships</p>
                    </div>
                    
                    <div class="space-y-3">
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-success rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="book-open" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Digital Khata</h4>
                                <p class="text-caption text-gray-600">Maintain customer ledger with credit/debit entries and balance tracking</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-blue rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="credit-card" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Payment History</h4>
                                <p class="text-caption text-gray-600">Complete transaction history with payment reminders</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-purple rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="pie-chart" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Customer Insights</h4>
                                <p class="text-caption text-gray-600">Purchase patterns, favorite products, and buying behavior</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-pink rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="bell" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Smart Reminders</h4>
                                <p class="text-caption text-gray-600">Automated payment reminders via WhatsApp and SMS</p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        },

        reports: {
            title: 'Analytics & Reports',
            icon: 'bar-chart-2',
            gradient: 'gradient-purple',
            content: `
                <div class="space-y-4">
                    <div class="text-center mb-4">
                        <p class="text-body text-gray-600">Data-driven insights for business growth</p>
                    </div>
                    
                    <div class="space-y-3">
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-purple rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="trending-up" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Sales Analytics</h4>
                                <p class="text-caption text-gray-600">Daily, monthly, and yearly sales performance tracking</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-blue rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="users" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Customer Analytics</h4>
                                <p class="text-caption text-gray-600">Top customers, buying patterns, and retention analysis</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-success rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="dollar-sign" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Profit Analysis</h4>
                                <p class="text-caption text-gray-600">Profit margins, cost analysis, and ROI tracking</p>
                            </div>
                        </div>
                        
                        <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded-xl">
                            <div class="w-8 h-8 gradient-warning rounded-lg flex items-center justify-center flex-shrink-0">
                                <i data-feather="download" class="w-4 h-4 text-white"></i>
                            </div>
                            <div>
                                <h4 class="text-subheading text-gray-900 mb-1">Export Reports</h4>
                                <p class="text-caption text-gray-600">Download reports in PDF, Excel formats for accounting</p>
                            </div>
                        </div>
                    </div>
                </div>
            `
        }
    },

    // Feature lists for different categories
    featureLists: {
        shopkeeper: {
            title: 'Shopkeeper Features',
            icon: 'store',
            gradient: 'gradient-primary',
            features: [
                { icon: 'file-text', title: 'Quick Bill Creation', desc: 'Generate bills in seconds' },
                { icon: 'printer', title: 'Professional Templates', desc: 'Multiple bill formats' },
                { icon: 'percent', title: 'GST Calculations', desc: 'Automatic tax computation' },
                { icon: 'credit-card', title: 'Payment Tracking', desc: 'Track all payments' },
                { icon: 'package', title: 'Inventory Management', desc: 'Stock level monitoring' },
                { icon: 'users', title: 'Customer Ledger', desc: 'Digital khata system' },
                { icon: 'smartphone', title: 'Mobile Optimized', desc: 'Works on all devices' },
                { icon: 'cloud', title: 'Cloud Backup', desc: 'Data security guaranteed' }
            ]
        },
        
        inventory: {
            title: 'Inventory Features',
            icon: 'package',
            gradient: 'gradient-secondary',
            features: [
                { icon: 'database', title: 'Product Catalog', desc: 'Organize all products' },
                { icon: 'alert-triangle', title: 'Low Stock Alerts', desc: 'Never run out of stock' },
                { icon: 'trending-up', title: 'Stock Reports', desc: 'Analyze inventory trends' },
                { icon: 'refresh-cw', title: 'Auto Updates', desc: 'Real-time stock tracking' },
                { icon: 'tag', title: 'Category Management', desc: 'Group products efficiently' },
                { icon: 'bar-chart', title: 'Bestseller Analysis', desc: 'Identify top products' }
            ]
        },

        customers: {
            title: 'Customer Features',
            icon: 'users',
            gradient: 'gradient-success',
            features: [
                { icon: 'book-open', title: 'Digital Khata', desc: 'Electronic ledger system' },
                { icon: 'credit-card', title: 'Payment History', desc: 'Complete transaction log' },
                { icon: 'bell', title: 'Payment Reminders', desc: 'Automated notifications' },
                { icon: 'pie-chart', title: 'Customer Insights', desc: 'Buying behavior analysis' },
                { icon: 'message-circle', title: 'WhatsApp Integration', desc: 'Send bills via WhatsApp' },
                { icon: 'star', title: 'Customer Rating', desc: 'Rate customer reliability' }
            ]
        },

        'ca-management': {
            title: 'CA Client Management',
            icon: 'briefcase',
            gradient: 'gradient-blue',
            features: [
                { icon: 'users', title: 'Multi-Client Dashboard', desc: 'Manage multiple clients' },
                { icon: 'eye', title: 'Client Bill Monitoring', desc: 'View all client activities' },
                { icon: 'shield-check', title: 'Compliance Tracking', desc: 'Monitor GST compliance' },
                { icon: 'calendar', title: 'Filing Schedule', desc: 'Track GST filing dates' },
                { icon: 'file-text', title: 'Client Reports', desc: 'Generate client summaries' },
                { icon: 'link', title: 'Client Connection', desc: 'Approve/manage connections' }
            ]
        },

        'gst-filing': {
            title: 'GST Filing Features',
            icon: 'percent',
            gradient: 'gradient-warning',
            features: [
                { icon: 'file-text', title: 'GSTR-1 Reports', desc: 'Auto-generate GSTR-1' },
                { icon: 'calculator', title: 'GSTR-3B Ready', desc: 'Summary for filing' },
                { icon: 'check-circle', title: 'Compliance Check', desc: 'Validate GST data' },
                { icon: 'calendar', title: 'Filing Reminders', desc: 'Never miss deadlines' },
                { icon: 'download', title: 'Export Data', desc: 'Download filing data' },
                { icon: 'shield', title: 'Data Validation', desc: 'Ensure accuracy' }
            ]
        },

        'team-management': {
            title: 'Team Management',
            icon: 'user-plus',
            gradient: 'gradient-teal',
            features: [
                { icon: 'user-plus', title: 'Add Employees', desc: 'Manage team members' },
                { icon: 'key', title: 'Role-based Access', desc: 'Control permissions' },
                { icon: 'shuffle', title: 'Client Assignment', desc: 'Delegate client work' },
                { icon: 'activity', title: 'Performance Tracking', desc: 'Monitor team productivity' },
                { icon: 'message-square', title: 'Team Communication', desc: 'Internal messaging' },
                { icon: 'award', title: 'Performance Reports', desc: 'Team analytics' }
            ]
        }
    },

    showFeatureDetail(featureKey) {
        const feature = this.featureDetails[featureKey];
        if (!feature) {
            console.warn(`Feature ${featureKey} not found`);
            return;
        }

        // Create sliding page for feature detail
        this.createSlidingPage(feature, 'detail');
    },

    showFeatureList(categoryKey) {
        const category = this.featureLists[categoryKey];
        if (!category) {
            console.warn(`Feature category ${categoryKey} not found`);
            return;
        }

        // Create sliding page for feature list
        this.createSlidingPage(category, 'list');
    },

    createSlidingPage(data, type) {
        // Remove any existing sliding page
        const existingPage = document.getElementById('sliding-page');
        if (existingPage) {
            existingPage.remove();
        }

        // Create sliding page HTML
        const slidingPage = document.createElement('div');
        slidingPage.id = 'sliding-page';
        slidingPage.className = 'fixed inset-0 z-50 bg-white transform translate-x-full transition-transform duration-300 ease-in-out';
        
        let content = '';
        if (type === 'detail') {
            content = this.generateDetailContent(data);
        } else if (type === 'list') {
            content = this.generateListContent(data);
        }
        
        slidingPage.innerHTML = `
            <div class="full-height flex flex-col">
                <!-- Header -->
                <div class="flex items-center justify-between p-4 border-b border-gray-200 safe-area-top bg-white sticky top-0 z-10">
                    <button onclick="MobileFeatures.closeSlidingPage()" class="w-10 h-10 flex items-center justify-center rounded-full bg-gray-100 touch-feedback">
                        <i data-feather="arrow-left" class="w-5 h-5 text-gray-600"></i>
                    </button>
                    <div class="flex items-center space-x-3">
                        <div class="w-8 h-8 ${data.gradient} rounded-lg flex items-center justify-center">
                            <i data-feather="${data.icon}" class="w-4 h-4 text-white"></i>
                        </div>
                        <h1 class="text-heading text-gray-900 font-semibold">${data.title}</h1>
                    </div>
                    <div class="w-10"></div> <!-- Spacer -->
                </div>

                <!-- Content -->
                <div class="flex-1 overflow-y-auto mobile-scroll">
                    <div class="section-padding">
                        ${content}
                    </div>
                </div>

                <!-- Footer -->
                <div class="p-4 border-t border-gray-200 safe-area-bottom bg-white">
                    <button onclick="MobileApp.goToDashboard()" class="w-full btn-primary touch-feedback">
                        <i data-feather="arrow-right" class="w-5 h-5 inline mr-2"></i>
                        Get Started
                    </button>
                </div>
            </div>
        `;

        // Add to body
        document.body.appendChild(slidingPage);

        // Trigger slide in animation
        setTimeout(() => {
            slidingPage.classList.remove('translate-x-full');
            slidingPage.classList.add('translate-x-0');
        }, 10);

        // Initialize feather icons in the new content
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    },

    generateDetailContent(feature) {
        return `
            <div class="space-y-6">
                <div class="text-center mb-6">
                    <div class="w-16 h-16 ${feature.gradient} rounded-2xl mx-auto mb-4 flex items-center justify-center">
                        <i data-feather="${feature.icon}" class="w-8 h-8 text-white"></i>
                    </div>
                    <p class="text-body text-gray-600">Discover all the features and capabilities</p>
                </div>
                
                ${feature.content}
                
                <!-- Additional CTA Section -->
                <div class="mt-8 p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-2xl">
                    <div class="text-center">
                        <h3 class="text-subheading text-gray-900 mb-2">Ready to get started?</h3>
                        <p class="text-caption text-gray-600 mb-4">Experience ${feature.title.toLowerCase()} and more with MyBillingApp</p>
                        <div class="flex space-x-2">
                            <button onclick="MobileFeatures.closeSlidingPage()" class="flex-1 px-4 py-2 bg-white border border-gray-300 rounded-xl text-gray-700 font-medium touch-feedback">
                                <i data-feather="eye" class="w-4 h-4 inline mr-2"></i>
                                Explore More
                            </button>
                            <button onclick="MobileApp.goToDashboard()" class="flex-1 btn-primary touch-feedback">
                                <i data-feather="arrow-right" class="w-4 h-4 inline mr-2"></i>
                                Start Now
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    generateListContent(category) {
        const featuresHTML = category.features.map(feature => `
            <div class="glass rounded-2xl p-4 mb-3 touch-feedback">
                <div class="flex items-start space-x-3">
                    <div class="w-10 h-10 ${category.gradient} rounded-xl flex items-center justify-center flex-shrink-0">
                        <i data-feather="${feature.icon}" class="w-5 h-5 text-white"></i>
                    </div>
                    <div class="flex-1">
                        <h4 class="text-subheading text-gray-900 mb-1">${feature.title}</h4>
                        <p class="text-body text-gray-600">${feature.desc}</p>
                    </div>
                </div>
            </div>
        `).join('');

        return `
            <div class="space-y-6">
                <div class="text-center mb-6">
                    <div class="w-16 h-16 ${category.gradient} rounded-2xl mx-auto mb-4 flex items-center justify-center">
                        <i data-feather="${category.icon}" class="w-8 h-8 text-white"></i>
                    </div>
                    <p class="text-body text-gray-600">Complete list of ${category.title.toLowerCase()}</p>
                </div>
                
                <div class="space-y-3">
                    ${featuresHTML}
                </div>
                
                <!-- Summary Section -->
                <div class="mt-8 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl">
                    <div class="text-center">
                        <h3 class="text-subheading text-gray-900 mb-2">Everything you need</h3>
                        <p class="text-caption text-gray-600 mb-4">${category.features.length} powerful features to help you manage your business efficiently</p>
                        <div class="flex items-center justify-center space-x-4 text-caption text-gray-600">
                            <div class="flex items-center space-x-1">
                                <i data-feather="check-circle" class="w-4 h-4 text-green-500"></i>
                                <span>Free to use</span>
                            </div>
                            <div class="flex items-center space-x-1">
                                <i data-feather="smartphone" class="w-4 h-4 text-blue-500"></i>
                                <span>Mobile ready</span>
                            </div>
                            <div class="flex items-center space-x-1">
                                <i data-feather="shield" class="w-4 h-4 text-purple-500"></i>
                                <span>Secure</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // Close sliding page
    closeSlidingPage() {
        const slidingPage = document.getElementById('sliding-page');
        if (slidingPage) {
            slidingPage.classList.remove('translate-x-0');
            slidingPage.classList.add('translate-x-full');
            
            // Remove from DOM after animation
            setTimeout(() => {
                slidingPage.remove();
            }, 300);
        }
    },

    // Legacy methods for backwards compatibility
    hideFeatureDetail() {
        this.closeSlidingPage();
    },

    createFeatureDetailPage(feature) {
        this.createSlidingPage(feature, 'detail');
    }
};

// Initialize features when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Mobile Features initialized');
});