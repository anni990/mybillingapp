# 🧾 MyBillingApp

A comprehensive **multi-tenant Flask ERP system** designed for the GST billing and accounting ecosystem in India. MyBillingApp connects Shopkeepers, Chartered Accountants (CAs), and CA Employees in a seamless billing and tax management platform.

## 🌟 Key Features

### For Shopkeepers
- **Digital Bill Creation** with automatic GST calculations
- **Inventory Management** with product catalog
- **Customer Ledger System** (Khata) with running balances
- **PDF Bill Generation** with professional templates
- **Sales Reports & Analytics** with graphical insights
- **CA Marketplace** to connect with certified accountants
- **Document Management** for GST, PAN, and business documents

### For Chartered Accountants (CAs)
- **Multi-Client Management** dashboard
- **Employee Delegation** system for client handling
- **Client Document Access** for GST filing preparation
- **Approval-based Client Connections**
- **Comprehensive Client Analytics**

### For CA Employees
- **Assigned Client Management** via delegation
- **Limited Access Control** based on CA permissions
- **Client Bill and Document Access**

## 🏗️ Architecture Overview

MyBillingApp follows a **modular blueprint architecture** with role-based access control and multi-tenant design patterns.

### Core Business Flow
```
Shopkeepers ↔ Chartered Accountants ↔ CA Employees
     ↓              ↓                    ↓
   Bills        Client Mgmt          Delegated
 Products       GST Filing           Client Care
 Customers      Analytics            Limited Access
```

### Technology Stack
- **Backend**: Flask (Python 3.8+)
- **Database**: MySQL with PyMySQL driver
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **PDF Generation**: WeasyPrint
- **Authentication**: Flask-Login with role-based access
- **Session Management**: Filesystem-based sessions
- **File Uploads**: Flask-Uploads for document management

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- MySQL Server 5.7+
- Git

### Installation

1. **Clone the repository**
   ```powershell
   git clone https://github.com/anni990/mybillingapp.git
   cd mybillingapp
   ```

2. **Create virtual environment**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key-here
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your-mysql-username
   DB_PASSWORD=your-mysql-password
   DB_NAME=mybillingapp
   FLASK_ENV=development
   ```

5. **Database Setup**
   ```powershell
   # Create database in MySQL
   mysql -u root -p
   CREATE DATABASE mybillingapp;
   exit;
   ```

6. **Run the application**
   ```powershell
   python run.py
   ```

The application will be available at `http://localhost:5000`

## 📁 Project Structure

```
mybillingapp/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── config.py                   # Configuration settings
│   ├── models.py                   # Database models
│   ├── extensions.py               # Flask extensions
│   ├── forms.py                    # WTForms definitions
│   ├── utils.py                    # Utility functions
│   │
│   ├── auth/                       # Authentication module
│   │   └── routes.py               # Login/Register routes
│   │
│   ├── shopkeeper/                 # Shopkeeper module
│   │   ├── __init__.py             # Blueprint registration
│   │   ├── utils.py                # Shopkeeper utilities
│   │   ├── views/                  # Route handlers
│   │   │   ├── dashboard.py        # Dashboard & analytics
│   │   │   ├── bills.py            # Bill management
│   │   │   ├── products.py         # Product catalog
│   │   │   ├── customers.py        # Customer & ledger
│   │   │   ├── reports.py          # Sales reports
│   │   │   ├── profile.py          # Profile management
│   │   │   └── ca_connections.py   # CA marketplace
│   │   └── services/               # Business logic
│   │       ├── bill_service.py     # Bill generation
│   │       ├── customer_service.py # Customer management
│   │       └── report_service.py   # Analytics
│   │
│   ├── ca/                         # CA module
│   │   ├── views/                  # CA route handlers
│   │   │   ├── dashboard.py        # CA dashboard
│   │   │   ├── clients.py          # Client management
│   │   │   ├── employees.py        # Employee management
│   │   │   ├── bills.py            # Client bill access
│   │   │   └── reports.py          # Client analytics
│   │   └── utils.py                # CA utilities
│   │
│   ├── api/                        # API endpoints
│   │   ├── routes.py               # General API routes
│   │   ├── walkthrough_routes.py   # User onboarding
│   │   └── gst_preview.py          # GST preview API
│   │
│   ├── static/                     # Static assets
│   │   ├── css/                    # Stylesheets
│   │   ├── js/                     # JavaScript files
│   │   ├── images/                 # Image assets
│   │   ├── uploads/                # Shopkeeper uploads
│   │   └── ca_upload/              # CA uploads
│   │
│   ├── templates/                  # Jinja2 templates
│   │   ├── auth/                   # Authentication pages
│   │   ├── shopkeeper/             # Shopkeeper pages
│   │   ├── ca/                     # CA pages
│   │   └── home/                   # Landing pages
│   │
│   └── utils/                      # Shared utilities
│       └── gst.py                  # GST calculation utilities
│
├── flask_session/                  # Session storage
├── Docx/                          # Documentation
├── temp/                          # Temporary files
├── requirements.txt               # Python dependencies
├── run.py                         # Application entry point
└── Complete Schema.sql            # Database schema
```

## 🔧 Configuration

### Database Configuration
The application supports MySQL databases. Configure your database connection in the `.env` file:

```env
DB_HOST=your-mysql-host
DB_PORT=3306
DB_USER=your-username
DB_PASSWORD=your-password
DB_NAME=mybillingapp
```

### Security Configuration
```env
SECRET_KEY=your-super-secret-key
FLASK_ENV=production  # For production deployment
FLASK_COOKIE_SECURE=True  # For HTTPS deployments
```

## 🗄️ Database Schema

The application uses a comprehensive multi-tenant database schema with the following key entities:

- **Users**: Base user accounts with role-based access
- **Shopkeepers**: Shopkeeper profiles with business details
- **Chartered Accountants**: CA firm profiles and credentials
- **CA Employees**: Employee accounts under CA supervision
- **Bills**: Invoice records with GST calculations
- **Products**: Inventory management
- **Customers**: Customer profiles and ledger management
- **CA Connections**: Approval-based CA-Shopkeeper relationships

### Critical Foreign Key Patterns
⚠️ **Important**: Different tables use different foreign key references:

```python
# Use shopkeeper.shopkeeper_id for:
bills = Bill.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)
products = Product.query.filter_by(shopkeeper_id=shopkeeper.shopkeeper_id)

# Use shopkeeper.user_id for:
customers = Customer.query.filter_by(shopkeeper_id=shopkeeper.user_id)
ledger = CustomerLedger.query.filter_by(shopkeeper_id=shopkeeper.user_id)
```

## 🎨 Frontend Architecture

### Responsive Design
- **Desktop-first** approach with mobile adaptations
- **Tailwind CSS** for utility-first styling
- **Dual view system**: Table view (desktop) + Card view (mobile)

### JavaScript Features
- **Dynamic bill creation** with real-time calculations
- **Product search** with 300ms debouncing
- **Modal systems** with blur backgrounds
- **Real-time notifications**
- **Chart.js integration** for analytics

### Template Structure
```
{role}/{action}.html  # Template naming convention
├── shopkeeper/s_base.html      # Shopkeeper base template
├── ca/ca_base.html             # CA base template
└── auth/auth_base.html         # Authentication base template
```

## 🔐 Security Features

- **Role-based Access Control** (RBAC)
- **Session-based Authentication**
- **CSRF Protection** via Flask-WTF
- **Secure file uploads** with validation
- **SQL Injection Protection** via SQLAlchemy ORM
- **Password hashing** with bcrypt

### Access Control Decorators
```python
@login_required
@shopkeeper_required  # or @ca_required, @employee_required
def protected_route():
    # Route logic here
```

## 📊 Business Logic

### GST Calculations
- **Accurate decimal arithmetic** using Python Decimal
- **Multiple GST rates** support (0%, 5%, 12%, 18%, 28%)
- **CGST/SGST splitting** for intra-state transactions
- **IGST handling** for inter-state transactions

### Customer Ledger System (Khata)
```python
Transaction Types:
- PURCHASE: Customer buys goods (debit)
- PAYMENT: Customer makes payment (credit)
- ADJUSTMENT: Manual balance corrections
```

### Bill Generation
- **Professional PDF templates** with company branding
- **Sequential invoice numbering** with custom prefixes
- **Digital signatures** and company logos
- **GST-compliant formatting**

## 🚀 Deployment

### Local Development
```powershell
python run.py  # Runs on http://localhost:5000
```

### Production Deployment

#### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:8000 run:app
```

#### Docker Deployment
```dockerfile
# Dockerfile included in repository
docker build -t mybillingapp .
docker run -p 8000:8000 mybillingapp
```

#### Environment Variables for Production
```env
FLASK_ENV=production
DB_HOST=your-production-db-host
SECRET_KEY=your-production-secret-key
FLASK_COOKIE_SECURE=True
```

## 🧪 Testing

### Quick Health Check
```powershell
# Test application startup
python -c "from app import create_app; app = create_app(); print('✅ App ready')"

# Test database connection
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.session.execute(db.text('SELECT 1')); print('✅ Connected')"
```

## 📖 API Documentation

### Walkthrough API
- `POST /api/walkthrough/complete` - Mark user walkthrough as complete
- `GET /api/walkthrough/status` - Get walkthrough completion status

### GST Preview API
- `POST /api/preview/gst` - Preview GST calculations before bill creation

### Bill Management API
- Internal APIs for dynamic bill creation and product search

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow **PEP 8** Python style guidelines
- Use **descriptive commit messages**
- Add **docstrings** to all functions and classes
- Test **foreign key relationships** carefully
- Maintain **role-based access control**

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Support

For support and questions:
- Create an issue in the GitHub repository
- Contact the development team

## 🎯 Roadmap

- [ ] **Mobile App** development (React Native)
- [ ] **Advanced Analytics** with ML insights
- [ ] **Multi-language Support** (Hindi, regional languages)
- [ ] **API Gateway** for third-party integrations
- [ ] **Cloud Storage** integration for documents
- [ ] **Automated GST Filing** through government APIs

---

**MyBillingApp** - Empowering Indian businesses with digital billing and GST management solutions. 🇮🇳