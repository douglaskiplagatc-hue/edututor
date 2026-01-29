import requests
import base64
import json
from datetime import datetime
from flask import current_app, request
from app import db
from app.models import Payment, Booking, User
import hashlib

class MpesaService:
    """Complete M-Pesa integration service"""
    
    @staticmethod
    def get_access_token():
        """Get OAuth access token from M-Pesa"""
        consumer_key = current_app.config.get('MPESA_CONSUMER_KEY')
        consumer_secret = current_app.config.get('MPESA_CONSUMER_SECRET')
        environment = current_app.config.get('MPESA_ENV', 'sandbox')
        
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
        
        url = f'{base_url}/oauth/v1/generate?grant_type=client_credentials'
        auth_string = f'{consumer_key}:{consumer_secret}'
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {encoded_auth}'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get('access_token')
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'M-Pesa token error: {e}')
            return None
    
    @staticmethod
    def initiate_stk_push(phone_number, amount, booking_id, description="Tutoring Session"):
        """Initiate STK Push payment"""
        access_token = MpesaService.get_access_token()
        if not access_token:
            return None
        
        environment = current_app.config.get('MPESA_ENV', 'sandbox')
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
        
        shortcode = current_app.config.get('MPESA_SHORTCODE')
        passkey = current_app.config.get('MPESA_PASSKEY')
        callback_url = current_app.config.get('MPESA_CALLBACK_URL')
        
        # Format phone number (remove +254 or 0)
        if phone_number.startswith('+254'):
            phone_number = phone_number[1:]  # Remove +
        elif phone_number.startswith('254'):
            phone_number = phone_number
        elif phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f'{shortcode}{passkey}{timestamp}'.encode()
        ).decode()
        
        # Generate unique transaction reference
        transaction_ref = f"EDUTUTOR{booking_id}{int(datetime.now().timestamp())}"
        
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": phone_number,
            "PartyB": shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": f"{callback_url}/api/mpesa/callback",
            "AccountReference": transaction_ref,
            "TransactionDesc": description
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f'{base_url}/mpesa/stkpush/v1/processrequest',
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Save payment record
            payment = Payment(
                booking_id=booking_id,
                amount=amount,
                phone_number=phone_number,
                checkout_request_id=result.get('CheckoutRequestID'),
                merchant_request_id=result.get('MerchantRequestID'),
                transaction_reference=transaction_ref,
                status='pending'
            )
            db.session.add(payment)
            db.session.commit()
            
            return {
                'success': True,
                'response_code': result.get('ResponseCode'),
                'customer_message': result.get('CustomerMessage'),
                'checkout_request_id': result.get('CheckoutRequestID'),
                'merchant_request_id': result.get('MerchantRequestID'),
                'payment_id': payment.id
            }
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'M-Pesa STK Push error: {e}')
            return None
    
    @staticmethod
    def handle_callback():
        """Handle M-Pesa callback"""
        data = request.get_json()
        
        if not data:
            current_app.logger.error('Empty callback received')
            return {'ResultCode': 1, 'ResultDesc': 'Invalid callback'}
        
        # Log the callback for debugging
        current_app.logger.info(f'M-Pesa callback: {json.dumps(data, indent=2)}')
        
        body = data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        # Find payment record
        payment = Payment.query.filter_by(
            checkout_request_id=checkout_request_id
        ).first()
        
        if not payment:
            current_app.logger.error(f'Payment not found: {checkout_request_id}')
            return {'ResultCode': 1, 'ResultDesc': 'Payment not found'}
        
        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            
            mpesa_receipt = None
            transaction_date = None
            phone_number = None
            
            for item in callback_metadata:
                if item.get('Name') == 'MpesaReceiptNumber':
                    mpesa_receipt = item.get('Value')
                elif item.get('Name') == 'TransactionDate':
                    transaction_date = item.get('Value')
                elif item.get('Name') == 'PhoneNumber':
                    phone_number = item.get('Value')
            
            # Update payment
            payment.status = 'completed'
            payment.mpesa_receipt = mpesa_receipt
            payment.transaction_date = transaction_date
            payment.phone_number = phone_number
            payment.completed_at = datetime.utcnow()
            
            # Update booking
            booking = payment.booking
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            
            # Send notifications
            from app.notifications import NotificationService
            NotificationService.send_payment_success_notification(booking)
            
            db.session.commit()
            
            current_app.logger.info(f'Payment successful: {mpesa_receipt}')
            return {'ResultCode': 0, 'ResultDesc': 'Success'}
        
        else:
            # Payment failed
            payment.status = 'failed'
            payment.failure_reason = result_desc
            db.session.commit()
            
            current_app.logger.warning(f'Payment failed: {result_desc}')
            return {'ResultCode': 1, 'ResultDesc': result_desc}
    
    @staticmethod
    def check_transaction_status(checkout_request_id):
        """Check transaction status"""
        access_token = MpesaService.get_access_token()
        if not access_token:
            return None
        
        environment = current_app.config.get('MPESA_ENV', 'sandbox')
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
        
        shortcode = current_app.config.get('MPESA_SHORTCODE')
        passkey = current_app.config.get('MPESA_PASSKEY')
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password = base64.b64encode(
            f'{shortcode}{passkey}{timestamp}'.encode()
        ).decode()
        
        payload = {
            "BusinessShortCode": shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f'{base_url}/mpesa/stkpushquery/v1/query',
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'M-Pesa status check error: {e}')
            return None
    
    @staticmethod
    def process_bulk_payout(tutor_id, amount, description="Tutor Payout"):
        """Process bulk payout to tutor (B2C)"""
        access_token = MpesaService.get_access_token()
        if not access_token:
            return None
        
        environment = current_app.config.get('MPESA_ENV', 'sandbox')
        if environment == 'production':
            base_url = 'https://api.safaricom.co.ke'
        else:
            base_url = 'https://sandbox.safaricom.co.ke'
        
        tutor = User.query.get(tutor_id)
        if not tutor or not tutor.phone:
            return None
        
        phone_number = tutor.phone
        # Format phone number
        if phone_number.startswith('+254'):
            phone_number = phone_number[1:]
        elif phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]
        
        # Generate unique transaction reference
        transaction_ref = f"PAYOUT{tutor_id}{int(datetime.now().timestamp())}"
        
        payload = {
            "OriginatorConversationID": transaction_ref,
            "InitiatorName": current_app.config.get('MPESA_INITIATOR_NAME'),
            "SecurityCredential": current_app.config.get('MPESA_SECURITY_CREDENTIAL'),
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": current_app.config.get('MPESA_SHORTCODE'),
            "PartyB": phone_number,
            "Remarks": description,
            "QueueTimeOutURL": f"{current_app.config.get('MPESA_CALLBACK_URL')}/api/mpesa/b2c_timeout",
            "ResultURL": f"{current_app.config.get('MPESA_CALLBACK_URL')}/api/mpesa/b2c_result",
            "Occasion": "Tutor Payment"
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.post(
                f'{base_url}/mpesa/b2c/v1/paymentrequest',
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'M-Pesa B2C error: {e}')
            return None