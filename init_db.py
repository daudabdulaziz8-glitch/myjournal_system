from journal import create_app, db

# Create the Flask app
app = create_app()

# Initialize the database within the app context
with app.app_context():
    db.create_all()
    print("✅ Tables created successfully in instance/database.db")
