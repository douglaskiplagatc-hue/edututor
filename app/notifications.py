import requests
import json
from flask import current_app

class PushNotificationService:
    @staticmethod
    def send_fcm_notification(device_token, title, body, data=None):
        """Send Firebase Cloud Messaging notification"""
        if not device_token:
            return False
        
        fcm_key = current_app.config.get('FCM_SERVER_KEY')
        
        if not fcm_key:
            print("FCM key not configured")
            return False
        
        headers = {
            'Authorization': f'key={fcm_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': device_token,
            'notification': {
                'title': title,
                'body': body,
                'sound': 'default',
                'badge': '1'
            },
            'data': data or {},
            'priority': 'high'
        }
        
        try:
            response = requests.post(
                'https://fcm.googleapis.com/fcm/send',
                headers=headers,
                json=payload
            )
            return response.status_code == 200
        except Exception as e:
            print(f"FCM error: {e}")
            return False
    
    @staticmethod
    def send_sms_notification(phone_number, message):
        """Send SMS notification (Africa's Talking)"""
        api_key = current_app.config.get('AT_API_KEY')
        username = current_app.config.get('AT_USERNAME')
        
        if not api_key or not username:
            return False
        
        headers = {
            'apiKey': api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        data = {
            'username': username,
            'to': phone_number,
            'message': message,
            'from': 'EDUTUTOR'
        }
        
        try:
            response = requests.post(
                'https://api.africastalking.com/version1/messaging',
                headers=headers,
                data=data
            )
            return response.status_code == 201
        except Exception as e:
            print(f"SMS error: {e}")
            return False
    
    @staticmethod
    def send_email_notification(to_email, subject, template_name, context):
        """Send email notification using templates"""
        from flask_mail import Message
        from app import mail
        
        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=render_template(f'emails/{template_name}.html', **context)
        )
        
        try:
            mail.send(msg)
            return True
        except Exception as e:
            print(f"Email error: {e}")
            return False