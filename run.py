from app import create_app
from app.extensions import db
import pyodbc

app = create_app()

if __name__ == "__main__":
    # with app.app_context():
    #     db.create_all()  # Create tables if not exist
    app.run(debug=True)
