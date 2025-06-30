import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory
from flask_cors import CORS
from src.models.user import db

# Import all models to ensure they're registered
from src.models.user import User
from src.models.product import Product, Category
from src.models.order import Order, OrderItem
from src.models.download import Download, LicenseKey

# Import all blueprints
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.product import product_bp
from src.routes.order import order_bp
from src.routes.download import download_bp
from src.routes.payment import payment_bp

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Register all blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(product_bp, url_prefix='/api')
app.register_blueprint(order_bp, url_prefix='/api')
app.register_blueprint(download_bp, url_prefix='/api')
app.register_blueprint(payment_bp, url_prefix='/api/payment')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()
    
    # Create default admin user if it doesn't exist
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            is_admin=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Create sample categories
        categories = [
            Category(name='E-books', description='Digital books and publications'),
            Category(name='Software', description='Applications and tools'),
            Category(name='Templates', description='Design templates and themes'),
            Category(name='Courses', description='Online courses and tutorials'),
            Category(name='Music', description='Audio files and music'),
            Category(name='Graphics', description='Images, icons, and graphics')
        ]
        
        for category in categories:
            existing = Category.query.filter_by(name=category.name).first()
            if not existing:
                db.session.add(category)
        
        db.session.commit()
        print("Default admin user and categories created!")

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404

# API health check
@app.route('/api/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy',
        'message': 'Digital Product Store API is running',
        'version': '1.0.0'
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
