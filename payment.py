from flask import Blueprint, jsonify, request, session
import stripe
import os
from src.models.user import db
from src.models.order import Order, OrderItem
from src.models.product import Product
from src.models.download import Download, LicenseKey

payment_bp = Blueprint('payment', __name__)

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_51234567890abcdef')  # Use test key for demo
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_51234567890abcdef')

def require_auth():
    """Check if user is authenticated"""
    if 'user_id' not in session:
        return False
    return True

@payment_bp.route('/config', methods=['GET'])
def get_stripe_config():
    """Get Stripe publishable key for frontend"""
    return jsonify({
        'publishable_key': STRIPE_PUBLISHABLE_KEY
    })

@payment_bp.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    """Create a Stripe payment intent for the current cart"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        user_id = session['user_id']
        
        # Get the user's pending order (cart)
        pending_order = Order.query.filter_by(
            user_id=user_id, 
            status='pending'
        ).first()
        
        if not pending_order or not pending_order.order_items:
            return jsonify({'error': 'No items in cart'}), 400
        
        # Calculate total amount in cents
        total_amount_cents = int(float(pending_order.total_amount) * 100)
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=total_amount_cents,
            currency='usd',
            metadata={
                'order_id': pending_order.id,
                'user_id': user_id
            }
        )
        
        # Store payment intent ID in order
        pending_order.payment_intent_id = intent.id
        db.session.commit()
        
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
            'amount': total_amount_cents,
            'order': pending_order.to_dict()
        })
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Payment intent creation failed'}), 500

@payment_bp.route('/confirm-payment', methods=['POST'])
def confirm_payment():
    """Confirm payment and complete the order"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.json
    if not data or 'payment_intent_id' not in data:
        return jsonify({'error': 'Payment intent ID required'}), 400
    
    try:
        payment_intent_id = data['payment_intent_id']
        
        # Retrieve payment intent from Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status != 'succeeded':
            return jsonify({'error': 'Payment not completed'}), 400
        
        # Find the order
        order = Order.query.filter_by(payment_intent_id=payment_intent_id).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        # Verify ownership
        if order.user_id != session['user_id']:
            return jsonify({'error': 'Access denied'}), 403
        
        # Complete the order
        order.status = 'completed'
        order.payment_status = 'succeeded'
        
        # Create download links and license keys for each product
        for item in order.order_items:
            product = item.product
            
            # Create download link
            download = Download(
                user_id=order.user_id,
                product_id=product.id,
                order_id=order.id,
                max_downloads=product.download_limit
            )
            db.session.add(download)
            
            # Create license key
            license_key = LicenseKey(
                user_id=order.user_id,
                product_id=product.id,
                order_id=order.id
            )
            db.session.add(license_key)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment confirmed and order completed',
            'order': order.to_dict(),
            'downloads_created': len(order.order_items),
            'license_keys_created': len(order.order_items)
        })
        
    except stripe.error.StripeError as e:
        return jsonify({'error': f'Stripe error: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': 'Payment confirmation failed'}), 500

@payment_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_test123')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Find the order
        order = Order.query.filter_by(
            payment_intent_id=payment_intent['id']
        ).first()
        
        if order and order.status == 'pending':
            # Complete the order
            order.status = 'completed'
            order.payment_status = 'succeeded'
            
            # Create download links and license keys if not already created
            existing_downloads = Download.query.filter_by(order_id=order.id).count()
            if existing_downloads == 0:
                for item in order.order_items:
                    product = item.product
                    
                    # Create download link
                    download = Download(
                        user_id=order.user_id,
                        product_id=product.id,
                        order_id=order.id,
                        max_downloads=product.download_limit
                    )
                    db.session.add(download)
                    
                    # Create license key
                    license_key = LicenseKey(
                        user_id=order.user_id,
                        product_id=product.id,
                        order_id=order.id
                    )
                    db.session.add(license_key)
            
            db.session.commit()
    
    return jsonify({'status': 'success'})

@payment_bp.route('/payment-methods', methods=['GET'])
def get_payment_methods():
    """Get available payment methods"""
    return jsonify({
        'methods': [
            {
                'id': 'card',
                'name': 'Credit/Debit Card',
                'description': 'Visa, Mastercard, American Express',
                'enabled': True
            },
            {
                'id': 'paypal',
                'name': 'PayPal',
                'description': 'Pay with your PayPal account',
                'enabled': False  # Not implemented yet
            },
            {
                'id': 'apple_pay',
                'name': 'Apple Pay',
                'description': 'Pay with Apple Pay',
                'enabled': False  # Not implemented yet
            },
            {
                'id': 'google_pay',
                'name': 'Google Pay',
                'description': 'Pay with Google Pay',
                'enabled': False  # Not implemented yet
            }
        ]
    })

# Demo/Test endpoints
@payment_bp.route('/demo/create-test-payment', methods=['POST'])
def create_test_payment():
    """Create a test payment for demo purposes"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.json
    if not data or 'amount' not in data:
        return jsonify({'error': 'Amount required'}), 400
    
    try:
        # Create a test payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(data['amount'] * 100),  # Convert to cents
            currency='usd',
            metadata={
                'test_payment': 'true',
                'user_id': session['user_id']
            }
        )
        
        return jsonify({
            'client_secret': intent.client_secret,
            'payment_intent_id': intent.id,
            'amount': int(data['amount'] * 100)
        })
        
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 400

@payment_bp.route('/demo/simulate-success', methods=['POST'])
def simulate_payment_success():
    """Simulate successful payment for demo purposes"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = session['user_id']
    
    # Get the user's pending order
    pending_order = Order.query.filter_by(
        user_id=user_id, 
        status='pending'
    ).first()
    
    if not pending_order:
        return jsonify({'error': 'No pending order found'}), 404
    
    # Simulate payment success
    pending_order.status = 'completed'
    pending_order.payment_status = 'succeeded'
    pending_order.payment_intent_id = f'pi_demo_{pending_order.id}'
    
    # Create download links and license keys
    for item in pending_order.order_items:
        product = item.product
        
        # Create download link
        download = Download(
            user_id=pending_order.user_id,
            product_id=product.id,
            order_id=pending_order.id,
            max_downloads=product.download_limit
        )
        db.session.add(download)
        
        # Create license key
        license_key = LicenseKey(
            user_id=pending_order.user_id,
            product_id=product.id,
            order_id=pending_order.id
        )
        db.session.add(license_key)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Payment simulated successfully',
        'order': pending_order.to_dict(),
        'downloads_created': len(pending_order.order_items),
        'license_keys_created': len(pending_order.order_items)
    })

