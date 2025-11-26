import replicate
import logging
import os
import io
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
    """Запускает AI модели Replicate для анализа кадров видео."""

    CONFIDENCE_KEYS = ('confidence', 'score', 'conf', 'probability')

    def __init__(self):
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings.")
        self.client = replicate.Client(api_token)
        self.model_ids = {
            'yolo': getattr(settings, 'YOLO_MODEL_ID', ''),
            'nsfw': getattr(settings, 'NSFW_MODEL_ID', ''),
            'violence': getattr(settings, 'VIOLENCE_MODEL_ID', ''),
            'ocr': getattr(settings, 'OCR_MODEL_ID', ''),
        }
        self.enabled_models = {k: v for k, v in self.model_ids.items() if v}
        if not self.enabled_models:
            raise ValueError("No AI models configured for VideoAnalyticsService.")
        self.api_calls_per_frame = len(self.enabled_models)
    
    def analyze_frame(self, frame_path, timestamp):
        if not os.path.exists(frame_path):
            raise FileNotFoundError(f"Frame not found: {frame_path}")
        triggers = []
        frame_bytes = self._read_frame_bytes(frame_path)
        try:
            if 'yolo' in self.enabled_models:
                triggers.extend(self._run_yolo(frame_bytes, timestamp))
            if 'nsfw' in self.enabled_models:
                triggers.extend(self._run_nsfw(frame_bytes, timestamp))
            if 'violence' in self.enabled_models:
                triggers.extend(self._run_violence(frame_bytes, timestamp))
            if 'ocr' in self.enabled_models:
                triggers.extend(self._run_ocr(frame_bytes, timestamp))
            return triggers
        except Exception as e:
            logger.error(f"Error during frame analysis: {e}")
            raise
    
    def _read_frame_bytes(self, frame_path):
        with open(frame_path, 'rb') as frame_file:
            return frame_file.read()
    
    def _create_file_obj(self, frame_bytes):
        buffer = io.BytesIO(frame_bytes)
        buffer.name = 'frame.jpg'
        buffer.seek(0)
        return buffer
    
    def _invoke_model(self, model_key, frame_bytes, extra_input=None):
        model_id = self.enabled_models.get(model_key)
        if not model_id:
            return None
        buffer = self._create_file_obj(frame_bytes)
        try:
            payload = extra_input.copy() if extra_input else {}
            payload.setdefault('image', buffer)
            return self.client.run(model_id, input=payload)
        finally:
            buffer.close()
    
    def _build_trigger(self, timestamp, trigger_type, source, confidence, data):
        return {
            'timestamp': timestamp,
            'type': trigger_type,
            'source': source,
            'confidence': float(confidence or 0.0),
            'data': data
        }
    
    def _extract_confidence(self, data):
        if isinstance(data, dict):
            for key in self.CONFIDENCE_KEYS:
                if key in data and data[key] is not None:
                    return data[key]
            box = data.get('box') or data.get('bbox')
            if isinstance(box, dict):
                for key in self.CONFIDENCE_KEYS:
                    if key in box and box[key] is not None:
                        return box[key]
        return 0.0
    
    def _run_yolo(self, frame_bytes, timestamp):
        results = self._invoke_model('yolo', frame_bytes, {"confidence": 0.25})
        triggers = []
        if isinstance(results, list):
            for detection in results:
                triggers.append(self._build_trigger(
                    timestamp,
                    'object',
                    'yolo_object',
                    self._extract_confidence(detection),
                    detection
                ))
        elif results is not None:
            triggers.append(self._build_trigger(timestamp, 'object', 'yolo_object', 0.0, results))
        return triggers
    
    def _run_nsfw(self, frame_bytes, timestamp):
        results = self._invoke_model('nsfw', frame_bytes)
        if results is None:
            return []
        score = 0.0
        if isinstance(results, dict):
            score = results.get('nsfw') or results.get('score') or results.get('probability') or 0.0
        return [self._build_trigger(timestamp, 'nsfw', 'falconsai_nsfw', score, results)]
    
    def _run_violence(self, frame_bytes, timestamp):
        results = self._invoke_model('violence', frame_bytes)
        if results is None:
            return []
        score = 0.0
        if isinstance(results, dict):
            score = results.get('confidence') or results.get('violence_score') or 0.0
        return [self._build_trigger(timestamp, 'violence', 'violence_detector', score, results)]
    
    def _run_ocr(self, frame_bytes, timestamp):
        results = self._invoke_model('ocr', frame_bytes)
        triggers = []
        if isinstance(results, list):
            for item in results:
                text, confidence = self._parse_ocr_item(item)
                if text:
                    triggers.append(self._build_trigger(timestamp, 'text', 'easyocr_text', confidence, {
                        'text': text,
                        'raw': item,
                    }))
        elif isinstance(results, dict):
            text = results.get('text')
            if text:
                triggers.append(self._build_trigger(timestamp, 'text', 'easyocr_text', self._extract_confidence(results), results))
        elif isinstance(results, str):
            triggers.append(self._build_trigger(timestamp, 'text', 'easyocr_text', 0.0, {'text': results}))
        return triggers
    
    def _parse_ocr_item(self, item):
        text = None
        confidence = 0.0
        if isinstance(item, dict):
            text = item.get('text')
            confidence = self._extract_confidence(item)
        elif isinstance(item, (list, tuple)):
            if len(item) >= 2 and isinstance(item[1], str):
                text = item[1]
                confidence = float(item[2]) if len(item) >= 3 else 0.0
        elif isinstance(item, str):
            text = item
        if text:
            text = text.strip()
        return text, confidence


class NLPDictionaryService:
    def __init__(self):
        self.profanity_list = self._load_dictionary(
            settings.PROFANITY_DICT_PATH, 
            default=['мат1', 'мат2', 'мат3']
        )
        self.brand_list = self._load_dictionary(
            settings.BRAND_DICT_PATH,
            default=['coca cola', 'pepsi', 'nike', 'adidas']
        )
        self.stopwords_list = self._load_dictionary(
            settings.STOPWORDS_DICT_PATH,
            default=[]
        )
    
    def _load_dictionary(self, path, default=None):
        """Загружает словарь из файла или возвращает дефолтный."""
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    words = [line.strip().lower() for line in f if line.strip()]
                    logger.info(f"Loaded dictionary from {path}: {len(words)} words")
                    return words
            except Exception as e:
                logger.warning(f"Failed to load dictionary from {path}: {e}. Using default.")
        
        return default or []
    
    def analyze_transcription(self, transcription):
        triggers = []
        if not transcription or 'segments' not in transcription:
            return triggers
        
        for segment in transcription['segments']:
            text = segment['text'].lower()
            timestamp = segment['start']
            
            # Проверка на мат
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
            
            # Проверка на бренды
            for brand in self.brand_list:
                if brand in text:
                    triggers.append({
                        'timestamp': timestamp,
                        'type': 'brand',
                        'source': 'whisper_brand',
                        'confidence': 0.8,
                        'data': {'text': text, 'matched_brand': brand}
                    })
            
            # Проверка на запрещенные слова
            for stopword in self.stopwords_list:
                if stopword in text:
                    triggers.append({
                        'timestamp': timestamp,
                        'type': 'stopword',
                        'source': 'whisper_stopword',
                        'confidence': 0.85,
                        'data': {'text': text, 'matched_stopword': stopword}
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
    
    def compile_final_report_from_db(self, video):
        """
        Builds final report from database, filtering only PENDING AITriggers.
        Includes RiskDefinition metadata.
        """
        from ..models import AITrigger, RiskDefinition
        
        # Get all pending triggers for this video
        db_triggers = AITrigger.objects.filter(
            video=video,
            status=AITrigger.Status.PENDING
        ).order_by('timestamp_sec')
        
        report = {
            'video_id': str(video.id),
            'total_triggers': db_triggers.count(),
            'triggers_by_type': {},
            'triggers_by_source': {},
            'risks': []
        }
        
        for db_trigger in db_triggers:
            trigger_type = db_trigger.get_trigger_source_display()
            source = db_trigger.trigger_source
            
            # Track by type
            if trigger_type not in report['triggers_by_type']:
                report['triggers_by_type'][trigger_type] = 0
            report['triggers_by_type'][trigger_type] += 1
            
            # Track by source
            if source not in report['triggers_by_source']:
                report['triggers_by_source'][source] = 0
            report['triggers_by_source'][source] += 1
            
            # Get risk definition metadata
            risk_def = None
            try:
                risk_def = RiskDefinition.objects.get(trigger_source=source)
            except RiskDefinition.DoesNotExist:
                pass
            
            # Build risk entry
            risk_entry = {
                'id': str(db_trigger.id),
                'timestamp': float(db_trigger.timestamp_sec),
                'type': trigger_type,
                'source': source,
                'confidence': float(db_trigger.confidence),
                'description': self._get_risk_description_from_trigger(db_trigger),
                'data': db_trigger.data,
            }
            
            # Add risk definition metadata if available
            if risk_def:
                risk_entry['risk_level'] = risk_def.risk_level
                risk_entry['risk_name'] = risk_def.name
            
            report['risks'].append(risk_entry)
        
        logger.info(f"Built report from DB for video {video.id}: {report['total_triggers']} triggers")
        return report
    
    def _get_risk_description_from_trigger(self, db_trigger):
        """Gets description from a database trigger object."""
        source = db_trigger.trigger_source
        data = db_trigger.data or {}
        
        if source == 'whisper_profanity':
            return f"Обнаружена нецензурная лексика: '{data.get('matched_word', '')}'"
        elif source == 'whisper_brand':
            return f"Упоминание бренда: '{data.get('matched_brand', '')}'"
        elif source == 'falconsai_nsfw':
            return f"NSFW контент (уверенность: {db_trigger.confidence:.2f})"
        elif source == 'violence_detector':
            return f"Обнаружено насилие (уверенность: {db_trigger.confidence:.2f})"
        elif source == 'yolo_object':
            return f"Обнаружен объект: {data.get('class', 'unknown')}"
        elif source == 'easyocr_text':
            return f"Обнаруженный текст: {data.get('text', '')[:50]}"
        else:
            return f"Риск типа: {source}"
    
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