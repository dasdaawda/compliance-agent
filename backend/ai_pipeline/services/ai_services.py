import replicate
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class WhisperASRService:
    def __init__(self):
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings.")
        self.client = replicate.Client(api_token)
    
    def transcribe(self, audio_path):
        try:
            with open(audio_path, 'rb') as audio_file:
                prediction = self.client.run(
                    settings.WHISPER_MODEL_ID,  # Вынесено в настройки
                    input={
                        "audio": audio_file,
                        "model": "small",
                        "language": "ru",
                    }
                )
            return prediction
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise


class VideoAnalyticsService:
    def __init__(self):
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings.")
        self.client = replicate.Client(api_token)
    
    def analyze_frame(self, frame_path, timestamp):
        results = {
            'timestamp': timestamp,
            'yolo_objects': [],
            'nsfw_score': 0.0,
            'violence_score': 0.0,
            'ocr_text': []
        }
        
        try:
            with open(frame_path, 'rb') as frame_file:
                # YOLO objects
                yolo_results = self.client.run(
                    settings.YOLO_MODEL_ID,  # Вынесено в настройки
                    input={"image": frame_file, "confidence": 0.25}
                )
                results['yolo_objects'] = yolo_results
                
                # NSFW detection
                frame_file.seek(0)
                nsfw_results = self.client.run(
                    settings.NSFW_MODEL_ID,  # Вынесено в настройки
                    input={"image": frame_file}
                )
                results['nsfw_score'] = nsfw_results.get('nsfw', 0.0)
            
            return results
        except Exception as e:
            logger.error(f"Error during frame analysis: {e}")
            raise


class NLPDictionaryService:
    def __init__(self):
        self.profanity_list = ['мат1', 'мат2', 'мат3']
        self.brand_list = ['coca cola', 'pepsi', 'nike', 'adidas']
    
    def analyze_transcription(self, transcription):
        triggers = []
        if not transcription or 'segments' not in transcription:
            return triggers
        
        for segment in transcription['segments']:
            text = segment['text'].lower()
            timestamp = segment['start']
            
            for word in self.profanity_list:
                if word in text:
                    triggers.append({
                        'timestamp': timestamp,
                        'type': 'profanity',
                        'source': 'whisper_profanity',
                        'confidence': 0.9,
                        'data': {'text': text, 'matched_word': word}
                    })
                    break
            
            for brand in self.brand_list:
                if brand in text:
                    triggers.append({
                        'timestamp': timestamp,
                        'type': 'brand',
                        'source': 'whisper_brand',
                        'confidence': 0.8,
                        'data': {'text': text, 'matched_brand': brand}
                    })
        
        return triggers


class ReportCompiler:
    def save_triggers_to_db(self, video, triggers):
        from ..models import AITrigger
        for trigger in triggers:
            try:
                AITrigger.objects.create(
                    video=video,
                    timestamp_sec=trigger['timestamp'],
                    trigger_source=trigger['source'],
                    confidence=trigger['confidence'],
                    data=trigger['data']
                )
            except Exception as e:
                logger.error(f"Error saving trigger to DB: {e}")
                raise
    
    def compile_final_report(self, video, triggers):
        report = {
            'video_id': str(video.id),
            'total_triggers': len(triggers),
            'triggers_by_type': {},
            'risks': []
        }
        
        for trigger in triggers:
            trigger_type = trigger['type']
            if trigger_type not in report['triggers_by_type']:
                report['triggers_by_type'][trigger_type] = 0
            report['triggers_by_type'][trigger_type] += 1
            
            report['risks'].append({
                'timestamp': trigger['timestamp'],
                'type': trigger_type,
                'source': trigger['source'],
                'confidence': trigger['confidence'],
                'description': self._get_risk_description(trigger),
            })
        
        return report
    
    def _get_risk_description(self, trigger):
        source = trigger['source']
        data = trigger['data']
        
        if source == 'whisper_profanity':
            return f"Обнаружена нецензурная лексика: '{data.get('matched_word', '')}'"
        elif source == 'whisper_brand':
            return f"Упоминание бренда: '{data.get('matched_brand', '')}'"
        elif source == 'falconsai_nsfw':
            return f"NSFW контент (уверенность: {trigger['confidence']:.2f})"
        else:
            return f"Риск типа: {trigger['type']}"