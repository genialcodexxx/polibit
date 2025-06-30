from flask import Blueprint, jsonify, request, session, send_file, abort
from src.models.user import db
from src.models.download import Download, LicenseKey
from src.models.product import Product
from src.models.order import Order
import os

download_bp = Blueprint('download', __name__)

def require_auth():
    """Check if user is authenticated"""
    if 'user_id' not in session:
        return False
    return True

@download_bp.route('/downloads', methods=['GET'])
def get_user_downloads():
    """Get user's available downloads"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = session['user_id']
    downloads = Download.query.filter_by(user_id=user_id).order_by(
        Download.created_at.desc()
    ).all()
    
    return jsonify([download.to_dict() for download in downloads])

@download_bp.route('/downloads/<download_token>', methods=['GET'])
def download_file(download_token):
    """Download a file using download token"""
    download = Download.query.filter_by(download_token=download_token).first()
    
    if not download:
        return jsonify({'error': 'Invalid download token'}), 404
    
    if not download.is_valid():
        return jsonify({'error': 'Download link has expired or exceeded limit'}), 403
    
    product = download.product
    if not product or not product.file_path:
        return jsonify({'error': 'File not found'}), 404
    
    # Check if file exists on disk
    if not os.path.exists(product.file_path):
        return jsonify({'error': 'File not available'}), 404
    
    # Increment download count
    download.increment_download()
    
    try:
        return send_file(
            product.file_path,
            as_attachment=True,
            download_name=product.file_name or f"product_{product.id}",
            mimetype='application/octet-stream'
        )
    except Exception as e:
        return jsonify({'error': 'Failed to download file'}), 500

@download_bp.route('/downloads/<download_token>/info', methods=['GET'])
def get_download_info(download_token):
    """Get download information without downloading"""
    download = Download.query.filter_by(download_token=download_token).first()
    
    if not download:
        return jsonify({'error': 'Invalid download token'}), 404
    
    return jsonify(download.to_dict())

@download_bp.route('/license-keys', methods=['GET'])
def get_user_license_keys():
    """Get user's license keys"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = session['user_id']
    license_keys = LicenseKey.query.filter_by(user_id=user_id).order_by(
        LicenseKey.created_at.desc()
    ).all()
    
    return jsonify([key.to_dict() for key in license_keys])

@download_bp.route('/license-keys/<license_key>/validate', methods=['POST'])
def validate_license_key(license_key):
    """Validate a license key"""
    key = LicenseKey.query.filter_by(license_key=license_key).first()
    
    if not key:
        return jsonify({
            'valid': False,
            'error': 'Invalid license key'
        }), 404
    
    is_valid = key.is_valid()
    
    response_data = {
        'valid': is_valid,
        'license_key': license_key,
        'product_id': key.product_id,
        'product_name': key.product.name if key.product else None,
        'activation_count': key.activation_count,
        'max_activations': key.max_activations,
        'expires_at': key.expires_at.isoformat() if key.expires_at else None
    }
    
    if not is_valid:
        if not key.is_active:
            response_data['error'] = 'License key is deactivated'
        elif key.expires_at and key.expires_at < key.expires_at.utcnow():
            response_data['error'] = 'License key has expired'
        elif key.activation_count >= key.max_activations:
            response_data['error'] = 'License key activation limit exceeded'
    
    return jsonify(response_data)

@download_bp.route('/license-keys/<license_key>/activate', methods=['POST'])
def activate_license_key(license_key):
    """Activate a license key"""
    key = LicenseKey.query.filter_by(license_key=license_key).first()
    
    if not key:
        return jsonify({
            'success': False,
            'error': 'Invalid license key'
        }), 404
    
    if key.activate():
        return jsonify({
            'success': True,
            'message': 'License key activated successfully',
            'activation_count': key.activation_count,
            'max_activations': key.max_activations
        })
    else:
        return jsonify({
            'success': False,
            'error': 'License key cannot be activated',
            'activation_count': key.activation_count,
            'max_activations': key.max_activations
        }), 400

@download_bp.route('/purchases', methods=['GET'])
def get_user_purchases():
    """Get user's completed purchases with downloads and license keys"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = session['user_id']
    
    # Get completed orders
    orders = Order.query.filter_by(
        user_id=user_id,
        status='completed'
    ).order_by(Order.created_at.desc()).all()
    
    purchases = []
    for order in orders:
        order_data = order.to_dict()
        
        # Add downloads for this order
        downloads = Download.query.filter_by(
            user_id=user_id,
            order_id=order.id
        ).all()
        order_data['downloads'] = [download.to_dict() for download in downloads]
        
        # Add license keys for this order
        license_keys = LicenseKey.query.filter_by(
            user_id=user_id,
            order_id=order.id
        ).all()
        order_data['license_keys'] = [key.to_dict() for key in license_keys]
        
        purchases.append(order_data)
    
    return jsonify(purchases)

# Admin routes
@download_bp.route('/admin/downloads', methods=['GET'])
def admin_get_downloads():
    """Get all downloads (admin only)"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    if not session.get('is_admin', False):
        return jsonify({'error': 'Admin privileges required'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    downloads = Download.query.order_by(Download.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return jsonify({
        'downloads': [download.to_dict() for download in downloads.items],
        'total': downloads.total,
        'pages': downloads.pages,
        'current_page': page,
        'per_page': per_page
    })

@download_bp.route('/admin/license-keys', methods=['GET'])
def admin_get_license_keys():
    """Get all license keys (admin only)"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    if not session.get('is_admin', False):
        return jsonify({'error': 'Admin privileges required'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    license_keys = LicenseKey.query.order_by(LicenseKey.created_at.desc()).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    return jsonify({
        'license_keys': [key.to_dict() for key in license_keys.items],
        'total': license_keys.total,
        'pages': license_keys.pages,
        'current_page': page,
        'per_page': per_page
    })

@download_bp.route('/admin/license-keys/<int:key_id>/deactivate', methods=['POST'])
def admin_deactivate_license_key(key_id):
    """Deactivate a license key (admin only)"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    if not session.get('is_admin', False):
        return jsonify({'error': 'Admin privileges required'}), 403
    
    license_key = LicenseKey.query.get(key_id)
    if not license_key:
        return jsonify({'error': 'License key not found'}), 404
    
    license_key.is_active = False
    db.session.commit()
    
    return jsonify({
        'message': 'License key deactivated',
        'license_key': license_key.to_dict()
    })

@download_bp.route('/admin/downloads/<int:download_id>/reset', methods=['POST'])
def admin_reset_download(download_id):
    """Reset download count (admin only)"""
    if not require_auth():
        return jsonify({'error': 'Authentication required'}), 401
    
    if not session.get('is_admin', False):
        return jsonify({'error': 'Admin privileges required'}), 403
    
    download = Download.query.get(download_id)
    if not download:
        return jsonify({'error': 'Download not found'}), 404
    
    download.download_count = 0
    download.last_downloaded_at = None
    db.session.commit()
    
    return jsonify({
        'message': 'Download count reset',
        'download': download.to_dict()
    })

