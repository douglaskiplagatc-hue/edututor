import requests
import jwt
import time
from datetime import datetime, timedelta
from flask import current_app
import uuid

class VideoMeetingService:
    """Unified video meeting service supporting multiple providers"""
    
    @staticmethod
    def create_meeting(provider='zoom', **kwargs):
        """Create meeting with specified provider"""
        if provider == 'zoom':
            return VideoMeetingService.create_zoom_meeting(**kwargs)
        elif provider == 'daily':
            return VideoMeetingService.create_daily_meeting(**kwargs)
        elif provider == 'jitsi':
            return VideoMeetingService.create_jitsi_meeting(**kwargs)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    @staticmethod
    def create_zoom_meeting(topic, duration, start_time, host_email, 
                          password=None, settings=None):
        """Create Zoom meeting"""
        api_key = current_app.config.get('ZOOM_API_KEY')
        api_secret = current_app.config.get('ZOOM_API_SECRET')
        
        if not api_key or not api_secret:
            raise ValueError("Zoom API credentials not configured")
        
        # Generate JWT token
        payload = {
            'iss': api_key,
            'exp': int(time.time()) + 5000
        }
        token = jwt.encode(payload, api_secret, algorithm='HS256')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Format start time
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        
        # Default settings
        default_settings = {
            'host_video': True,
            'participant_video': True,
            'join_before_host': False,
            'mute_upon_entry': True,
            'watermark': False,
            'audio': 'both',
            'auto_recording': 'cloud',
            'waiting_room': True,
            'registrants_email_notification': True
        }
        
        if settings:
            default_settings.update(settings)
        
        # Generate password if not provided
        if not password:
            import random
            password = ''.join(random.choices('0123456789', k=6))
        
        payload = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time,
            'duration': duration,
            'timezone': 'Africa/Nairobi',
            'password': password,
            'agenda': 'EduTutor Kenya Tutoring Session',
            'settings': default_settings
        }
        
        try:
            response = requests.post(
                f'https://api.zoom.us/v2/users/{host_email}/meetings',
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            meeting_data = response.json()
            
            return {
                'provider': 'zoom',
                'meeting_id': meeting_data['id'],
                'join_url': meeting_data['join_url'],
                'start_url': meeting_data['start_url'],
                'password': meeting_data['password'],
                'meeting_data': meeting_data
            }
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'Zoom meeting creation error: {e}')
            return None
    
    @staticmethod
    def create_daily_meeting(room_name=None, properties=None):
        """Create Daily.co meeting room"""
        api_key = current_app.config.get('DAILY_CO_API_KEY')
        
        if not api_key:
            raise ValueError("Daily.co API key not configured")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        if not room_name:
            room_name = f'edututor-{uuid.uuid4().hex[:8]}'
        
        default_properties = {
            'exp': int(time.time()) + 3600 * 2,  # 2 hours expiry
            'enable_chat': True,
            'enable_hand_raising': True,
            'lang': 'en',
            'max_participants': 2,
            'start_audio_off': False,
            'start_video_off': False,
            'enable_recording': 'cloud',
            'enable_prejoin_ui': True,
            'enable_network_ui': True
        }
        
        if properties:
            default_properties.update(properties)
        
        payload = {
            'name': room_name,
            'privacy': 'public',
            'properties': default_properties
        }
        
        try:
            response = requests.post(
                'https://api.daily.co/v1/rooms',
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            room_data = response.json()
            
            return {
                'provider': 'daily',
                'room_name': room_data['name'],
                'room_url': room_data['url'],
                'expires_at': room_data.get('config', {}).get('exp'),
                'room_data': room_data
            }
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'Daily.co room creation error: {e}')
            return None
    
    @staticmethod
    def create_jitsi_meeting(room_name=None, options=None):
        """Create Jitsi meeting (open source alternative)"""
        if not room_name:
            room_name = f'EduTutor{int(time.time())}'
        
        jitsi_domain = current_app.config.get('JITSI_DOMAIN', 'meet.jit.si')
        
        # Jitsi doesn't require API keys for basic usage
        meeting_url = f'https://{jitsi_domain}/{room_name}'
        
        # Generate config for embedded iframe
        config = {
            'roomName': room_name,
            'width': '100%',
            'height': 500,
            'parentNode': None,
            'configOverwrite': {
                'startWithAudioMuted': True,
                'startWithVideoMuted': False,
                'enableWelcomePage': False,
                'prejoinPageEnabled': False
            },
            'interfaceConfigOverwrite': {
                'SHOW_JITSI_WATERMARK': False,
                'SHOW_WATERMARK_FOR_GUESTS': False,
                'DEFAULT_BACKGROUND': '#f8f9fa',
                'TOOLBAR_BUTTONS': [
                    'microphone', 'camera', 'closedcaptions', 'desktop',
                    'fullscreen', 'fodeviceselection', 'hangup', 'profile',
                    'chat', 'recording', 'livestreaming', 'settings',
                    'raisehand', 'videoquality', 'filmstrip', 'feedback',
                    'stats', 'shortcuts', 'tileview', 'videobackgroundblur',
                    'help', 'mute-everyone'
                ]
            }
        }
        
        if options:
            config.update(options)
        
        return {
            'provider': 'jitsi',
            'room_name': room_name,
            'meeting_url': meeting_url,
            'embed_config': config,
            'iframe_code': f'<iframe allow="camera; microphone; fullscreen; display-capture" src="{meeting_url}" style="height: 500px; width: 100%; border: 0px;"></iframe>'
        }
    
    @staticmethod
    def get_meeting_recordings(meeting_id, provider='zoom'):
        """Get meeting recordings"""
        if provider == 'zoom':
            return VideoMeetingService.get_zoom_recordings(meeting_id)
        else:
            return None
    
    @staticmethod
    def get_zoom_recordings(meeting_id):
        """Get Zoom meeting recordings"""
        api_key = current_app.config.get('ZOOM_API_KEY')
        api_secret = current_app.config.get('ZOOM_API_SECRET')
        
        if not api_key or not api_secret:
            return None
        
        # Generate JWT token
        payload = {
            'iss': api_key,
            'exp': int(time.time()) + 5000
        }
        token = jwt.encode(payload, api_secret, algorithm='HS256')
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        try:
            response = requests.get(
                f'https://api.zoom.us/v2/meetings/{meeting_id}/recordings',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    @staticmethod
    def end_meeting(meeting_id, provider='zoom'):
        """End a meeting"""
        if provider == 'zoom':
            return VideoMeetingService.end_zoom_meeting(meeting_id)
        else:
            return False
    
    @staticmethod
    def end_zoom_meeting(meeting_id):
        """End Zoom meeting"""
        api_key = current_app.config.get('ZOOM_API_KEY')
        api_secret = current_app.config.get('ZOOM_API_SECRET')
        
        if not api_key or not api_secret:
            return False
        
        # Generate JWT token
        payload = {
            'iss': api_key,
            'exp': int(time.time()) + 5000
        }
        token = jwt.encode(payload, api_secret, algorithm='HS256')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'action': 'end'
        }
        
        try:
            response = requests.put(
                f'https://api.zoom.us/v2/meetings/{meeting_id}/status',
                headers=headers,
                json=payload,
                timeout=30
            )
            return response.status_code == 204
        except requests.exceptions.RequestException:
            return False