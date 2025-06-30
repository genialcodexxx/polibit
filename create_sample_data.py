#!/usr/bin/env python3
"""
Script to create sample products for the digital product store
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.models.user import db
from src.models.product import Product, Category
from src.main import app

def create_sample_products():
    with app.app_context():
        # Get categories
        ebook_cat = Category.query.filter_by(name='E-books').first()
        software_cat = Category.query.filter_by(name='Software').first()
        template_cat = Category.query.filter_by(name='Templates').first()
        course_cat = Category.query.filter_by(name='Courses').first()
        
        # Sample products
        products = [
            {
                'name': 'Complete Python Programming Guide',
                'description': 'A comprehensive guide to Python programming covering basics to advanced topics. Perfect for beginners and experienced developers.',
                'price': 29.99,
                'category_id': ebook_cat.id if ebook_cat else 1,
                'file_name': 'python_guide.pdf',
                'file_size': 5242880,  # 5MB
                'download_limit': 3
            },
            {
                'name': 'Web Development Toolkit',
                'description': 'Essential tools and utilities for web developers. Includes code generators, debugging tools, and productivity enhancers.',
                'price': 49.99,
                'category_id': software_cat.id if software_cat else 2,
                'file_name': 'web_dev_toolkit.zip',
                'file_size': 15728640,  # 15MB
                'download_limit': 5
            },
            {
                'name': 'Modern Website Templates Pack',
                'description': 'Collection of 10 responsive website templates for various industries. HTML, CSS, and JavaScript included.',
                'price': 39.99,
                'category_id': template_cat.id if template_cat else 3,
                'file_name': 'website_templates.zip',
                'file_size': 25165824,  # 24MB
                'download_limit': 10
            },
            {
                'name': 'Digital Marketing Masterclass',
                'description': 'Complete video course on digital marketing strategies, SEO, social media marketing, and analytics.',
                'price': 99.99,
                'category_id': course_cat.id if course_cat else 4,
                'file_name': 'marketing_course.zip',
                'file_size': 1073741824,  # 1GB
                'download_limit': 3
            },
            {
                'name': 'JavaScript Fundamentals eBook',
                'description': 'Learn JavaScript from scratch with practical examples and exercises. Includes ES6+ features.',
                'price': 19.99,
                'category_id': ebook_cat.id if ebook_cat else 1,
                'file_name': 'javascript_fundamentals.pdf',
                'file_size': 3145728,  # 3MB
                'download_limit': 5
            },
            {
                'name': 'Logo Design Templates',
                'description': 'Professional logo templates in various formats (AI, PSD, SVG). Perfect for startups and small businesses.',
                'price': 24.99,
                'category_id': template_cat.id if template_cat else 3,
                'file_name': 'logo_templates.zip',
                'file_size': 52428800,  # 50MB
                'download_limit': 15
            }
        ]
        
        # Create products
        for product_data in products:
            # Check if product already exists
            existing = Product.query.filter_by(name=product_data['name']).first()
            if not existing:
                product = Product(**product_data)
                db.session.add(product)
                print(f"Created product: {product_data['name']}")
            else:
                print(f"Product already exists: {product_data['name']}")
        
        db.session.commit()
        print(f"\nSample data creation completed!")
        print(f"Total products in database: {Product.query.count()}")

if __name__ == '__main__':
    create_sample_products()

