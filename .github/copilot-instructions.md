# MyBillingApp AI Agent Instructions

This is a Flask-based billing and accounting management system with multiple user roles (Shopkeepers, Chartered Accountants, and Employees).

## Architecture Overview

### Core Components
- **User Authentication**: Multi-role system (`shopkeeper`, `CA`, `employee`) implemented in `app/models.py`
- **Blueprints**:
  - `shopkeeper/`: Shop management, billing, inventory
  - `ca/`: Chartered accountant features
  - `auth/`: Authentication routes
  - `api/`: API endpoints

### Key Patterns
1. **Database**:
   - Uses SQLAlchemy with MS SQL Server
   - Models defined in `app/models.py`
   - Environment-based connection config in `app/config.py`

2. **Authentication Flow**:
   - Role-based access using decorators (see `@shopkeeper_required` in `shopkeeper/routes.py`)
   - Session management with filesystem storage

3. **File Handling**:
   - Document uploads stored in `static/{bills,ca_upload,uploads}/`
   - Generated bills saved as HTML in `static/bills/`

## Development Workflow

### Environment Setup
1. Required environment variables:
   ```
   AZURE_SQL_USERNAME
   AZURE_SQL_PASSWORD
   AZURE_SQL_SERVER
   AZURE_SQL_DATABASE
   SECRET_KEY
   ```

2. Database initialization:
   ```python
   # Uncomment in run.py to create tables
   with app.app_context():
       db.create_all()
   ```

### Key Development Patterns

1. **Route Protection**:
   ```python
   @login_required
   @shopkeeper_required  # or equivalent role decorator
   def protected_route():
       # ...
   ```

2. **Database Operations**:
   Always use SQLAlchemy models and sessions through `db` from `app.extensions`
   ```python
   from app.extensions import db
   from app.models import User
   # Use: db.session.add(), db.session.commit()
   ```

3. **Form Handling**:
   Forms defined in `app/forms.py`, use with WTForms validation

## Integration Points

1. **External Services**:
   - Azure SQL Database (primary data store)
   - File storage for documents and bills

2. **Cross-Component Communication**:
   - Shopkeeper-CA connections through `CAConnection` model
   - Bill generation and document sharing between roles

## Common Tasks

1. **Adding New Features**:
   - Add routes to appropriate blueprint
   - Update models if needed
   - Create/update templates in `templates/<blueprint>/`

2. **Security Considerations**:
   - Always use role decorators for route protection
   - Validate file uploads and form inputs
   - Use parameterized queries (handled by SQLAlchemy)

## Testing

Local development server:
```bash
python run.py  # Runs on port 5500
```
