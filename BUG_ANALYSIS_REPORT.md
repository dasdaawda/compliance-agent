# Детальный анализ кода ai-compliance-agent на баги и ошибки

## Обзор
Проведен комплексный анализ всего репозитория ai-compliance-agent на наличие багов, ошибок и неправильной логики. Анализ охватил 5 ключевых аспектов: обработку ошибок, валидацию данных, логику бизнес-процессов, производительность и безопасность.

---

## 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. [КРИТИЧЕСКАЯ] Отсутствие валидации размера загружаемых файлов
**Файл:** `backend/projects/views.py`, строка 39-63  
**Категория:** Безопасность, Валидация данных  
**Критичность:** Critical

**Проблема:** Отсутствует проверка размера и типа загружаемых видеофайлов, что может привести к:
- Исчерпанию дискового пространства
- DoS атакам через загрузку огромных файлов
- Обработке вредоносных файлов

**Текущий код:**
```python
class VideoUploadView(LoginRequiredMixin, ClientAccessMixin, CreateView):
    # ... нет валидации файла
    def form_valid(self, form):
        # Прямая обработка файла без проверок
        response = super().form_valid(form)
```

**Рекомендация:**
```python
def form_valid(self, form):
    # Валидация размера файла (максимум 500MB)
    if form.cleaned_data['video_file'].size > 500 * 1024 * 1024:
        messages.error(self.request, 'Размер файла не должен превышать 500MB')
        return self.form_invalid(form)
    
    # Валидация типа файла
    allowed_types = ['video/mp4', 'video/avi', 'video/mov', 'video/wmv']
    if form.cleaned_data['video_file'].content_type not in allowed_types:
        messages.error(self.request, 'Неподдерживаемый формат видео')
        return self.form_invalid(form)
    
    # Проверка баланса с учетом длительности видео
    video_duration = self._get_video_duration(form.cleaned_data['video_file'])
    if not self.request.user.has_sufficient_balance(video_duration / 60):
        messages.error(self.request, 'Недостаточно минут на балансе')
        return self.form_invalid(form)
```

---

### 2. [КРИТИЧЕСКАЯ] Уязвимость в обработке URL видео
**Файл:** `backend/ai_pipeline/services/ffmpeg_service.py`, строка 10-30  
**Категория:** Безопасность  
**Критичность:** Critical

**Проблема:** Недостаточная валидация URL при скачивании видео может привести к SSRF (Server-Side Request Forgery) атакам.

**Текущий код:**
```python
def _is_valid_url(self, url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
```

**Рекомендация:**
```python
def _is_valid_url(self, url):
    try:
        result = urlparse(url)
        
        # Базовая проверка
        if not all([result.scheme, result.netloc]):
            return False
            
        # Разрешенные схемы
        if result.scheme not in ['http', 'https']:
            return False
            
        # Защита от SSRF - запрещаем локальные адреса
        hostname = result.hostname
        if hostname in ['localhost', '127.0.0.1', '0.0.0.0'] or hostname.startswith('192.168.') or hostname.startswith('10.'):
            return False
            
        return True
    except (ValueError, AttributeError):
        return False
```

---

### 3. [КРИТИЧЕСКАЯ] Race condition в обработке задач операторами
**Файл:** `backend/operators/tasks.py`, строка 30-48  
**Категория:** Логика бизнес-процессов  
**Критичность:** Critical

**Проблема:** Возможна ситуация, когда несколько операторов одновременно получат одну и ту же задачу из-за race condition.

**Текущий код:**
```python
task = (
    VerificationTask.objects
    .select_for_update(skip_locked=True)
    .filter(status=VerificationTask.Status.PENDING)
    .order_by('created_at')
    .first()
)
if not task:
    continue
assigned = TaskQueueService.get_next_task(operator)  # Может вернуть другую задачу!
```

**Рекомендация:**
```python
with transaction.atomic():
    task = (
        VerificationTask.objects
        .select_for_update(skip_locked=True)
        .filter(status=VerificationTask.Status.PENDING)
        .order_by('created_at')
        .first()
    )
    
    if not task:
        continue
        
    # Назначаем задачу непосредственно здесь
    task.operator = operator
    task.status = VerificationTask.Status.IN_PROGRESS
    task.started_at = timezone.now()
    task.save(update_fields=['operator', 'status', 'started_at'])
    assigned_count += 1
```

---

## 🔴 ВЫСОКИЕ ПРОБЛЕМЫ

### 4. [ВЫСОКАЯ] Недостаточная обработка ошибок в AI сервисах
**Файл:** `backend/ai_pipeline/services/ai_services.py`, строка 14-28  
**Категория:** Обработка ошибок  
**Критичность:** High

**Проблема:** Исключения в AI сервисах не обрабатываются должным образом, что может привести к падению всего пайплайна.

**Текущий код:**
```python
def transcribe(self, audio_path):
    try:
        with open(audio_path, 'rb') as audio_file:
            prediction = self.client.run(...)
        return prediction
    except Exception as e:
        logger.error(f"Error during transcription: {e}")
        raise  # Перебрасываем исключение без обработки
```

**Рекомендация:**
```python
def transcribe(self, audio_path):
    try:
        with open(audio_path, 'rb') as audio_file:
            prediction = self.client.run(
                settings.WHISPER_MODEL_ID,
                input={
                    "audio": audio_file,
                    "model": "small",
                    "language": "ru",
                }
            )
        return prediction
    except replicate.exceptions.ReplicateError as e:
        logger.error(f"Replicate API error during transcription: {e}")
        raise TranscriptionError(f"AI service unavailable: {e}")
    except FileNotFoundError:
        logger.error(f"Audio file not found: {audio_path}")
        raise TranscriptionError("Audio file not found")
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {e}")
        raise TranscriptionError(f"Transcription failed: {e}")
```

### 5. [ВЫСОКАЯ] Отсутствие timeout в внешних запросах
**Файл:** `backend/ai_pipeline/services/ai_services.py`, строка 48-67  
**Категория:** Производительность, Обработка ошибок  
**Критичность:** High

**Проблема:** Вызовы Replicate API не имеют timeout, что может привести к зависанию процессов.

**Текущий код:**
```python
yolo_results = self.client.run(
    settings.YOLO_MODEL_ID,
    input={"image": frame_file, "confidence": 0.25}
)
```

**Рекомендация:**
```python
# Добавить timeout в настройки
REPLICATE_API_TIMEOUT = env.int('REPLICATE_API_TIMEOUT', default=300)

# В сервисе:
yolo_results = self.client.run(
    settings.YOLO_MODEL_ID,
    input={"image": frame_file, "confidence": 0.25},
    timeout=settings.REPLICATE_API_TIMEOUT
)
```

### 6. [ВЫСОКАЯ] Небезопасное хранение ключей API
**Файл:** `backend/compliance_app/settings.py`, строка 168-171  
**Категория:** Безопасность  
**Критичность:** High

**Проблема:** API токены имеют небезопасные значения по умолчанию.

**Текущий код:**
```python
REPLICATE_API_TOKEN = env('REPLICATE_API_TOKEN', default='your_api_token')
```

**Рекомендация:**
```python
REPLICATE_API_TOKEN = env('REPLICATE_API_TOKEN')
if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN must be set in production")
```

---

## 🟡 СРЕДНИЕ ПРОБЛЕМЫ

### 7. [СРЕДНЯЯ] Неэффективные запросы к БД
**Файл:** `backend/operators/views.py`, строка 24-28  
**Категория:** Производительность  
**Критичность:** Medium

**Проблема:** N+1 запросов к БД при получении списка задач оператора.

**Текущий код:**
```python
context['operator_tasks'] = VerificationTask.objects.filter(operator=self.request.user)
```

**Рекомендация:**
```python
context['operator_tasks'] = VerificationTask.objects.filter(
    operator=self.request.user
).select_related('video', 'video__project').order_by('-created_at')
```

### 8. [СРЕДНЯЯ] Отсутствие валидации временных меток
**Файл:** `backend/ai_pipeline/models.py`, строка 21  
**Категория:** Валидация данных  
**Критичность:** Medium

**Проблема:** Отсутствует проверка, что timestamp_sec не отрицательный и не превышает длительность видео.

**Рекомендация:**
```python
class AITrigger(models.Model):
    timestamp_sec = models.DecimalField(_('временная метка (сек)'), max_digits=10, decimal_places=3)
    
    def clean(self):
        if self.timestamp_sec < 0:
            raise ValidationError({'timestamp_sec': 'Временная метка не может быть отрицательной'})
        if self.video and self.timestamp_sec > self.video.duration:
            raise ValidationError({'timestamp_sec': 'Временная метка превышает длительность видео'})
```

### 9. [СРЕДНЯЯ] Потенциальная утечка памяти при обработке видео
**Файл:** `backend/ai_pipeline/tasks.py`, строка 162-174  
**Категория:** Производительность  
**Критичность:** Medium

**Проблема:** Временные файлы не удаляются после обработки.

**Текущий код:**
```python
for i, frame_file in enumerate(frame_files[:5]):
    frame_path = os.path.join(frames_dir, frame_file)
    result = analytics_service.analyze_frame(frame_path, i)
    # Файлы не удаляются
```

**Рекомендация:**
```python
import shutil

def run_video_analytics(self, frames_dir, video_id):
    try:
        # ... обработка ...
    finally:
        # Удаляем временные файлы
        try:
            shutil.rmtree(frames_dir)
            logger.info(f"Cleaned up temporary frames directory: {frames_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup frames directory {frames_dir}: {e}")
```

---

## 🟢 НИЗКИЕ ПРОБЛЕМЫ

### 10. [НИЗКАЯ] Недостаточная логировка
**Файл:** `backend/users/views.py`, строка 22-39  
**Категория:** Обработка ошибок  
**Критичность:** Low

**Проблема:** Отсутствует логирование важных операций регистрации.

**Рекомендация:**
```python
def client_registration(request):
    if request.method == 'POST':
        form = ClientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info(f"New client registered: {user.email}, ID: {user.id}")
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('projects:project_list')
    else:
        logger.debug(f"Registration form accessed from IP: {request.META.get('REMOTE_ADDR')}")
```

### 11. [НИЗКАЯ] Отсутствие проверки уникальности имени проекта
**Файл:** `backend/projects/models.py`, строка 27-29  
**Категория:** Логика бизнес-процессов  
**Критичность:** Low

**Проблема:** Constraint на уникальность имени проекта в рамках одного пользователя есть, но нет дополнительной проверки на уровне формы.

**Рекомендация:**
```python
def clean(self):
    cleaned_data = super().clean()
    name = cleaned_data.get('name')
    owner = self.owner or getattr(self, 'owner', None)
    
    if name and owner:
        if Project.objects.filter(owner=owner, name=name).exclude(pk=self.pk).exists():
            raise ValidationError({'name': 'Проект с таким названием уже существует'})
```

### 12. [НИЗКАЯ] Хардкодные значения в сервисах
**Файл:** `backend/ai_pipeline/services/ai_services.py`, строка 72-73  
**Категория:** Валидация данных  
**Критичность:** Low

**Проблема:** Списки запретных слов и брендов захардкожены в коде.

**Рекомендация:**
```python
# В settings.py
PROFANITY_LIST = env.list('PROFANITY_LIST', default=['мат1', 'мат2', 'мат3'])
BRAND_LIST = env.list('BRAND_LIST', default=['coca cola', 'pepsi', 'nike', 'adidas'])

# В сервисе:
def __init__(self):
    self.profanity_list = settings.PROFANITY_LIST
    self.brand_list = settings.BRAND_LIST
```

---

## 📊 СТАТИСТИКА ПРОБЛЕМ

| Критичность | Количество | Процент |
|-------------|------------|---------|
| Критические | 3 | 25% |
| Высокие     | 3 | 25% |
| Средние     | 3 | 25% |
| Низкие      | 3 | 25% |
| **Итого**   | **12**     | **100%** |

| Категория | Количество | Процент |
|-----------|------------|---------|
| Безопасность | 3 | 25% |
| Обработка ошибок | 3 | 25% |
| Валидация данных | 3 | 25% |
| Производительность | 2 | 17% |
| Логика бизнес-процессов | 1 | 8% |
| **Итого** | **12** | **100%** |

---

## 🎯 ПРИОРИТЕТЫ ИСПРАВЛЕНИЯ

### 1. Немедленно (Критические проблемы):
1. Валидация размера загружаемых файлов
2. Защита от SSRF в URL обработке
3. Исправление race condition в задачах операторов

### 2. В ближайшее время (Высокие проблемы):
4. Улучшение обработки ошибок в AI сервисах
5. Добавление timeout во внешние запросы
6. Безопасное хранение API токенов

### 3. В следующем спринте (Средние проблемы):
7. Оптимизация запросов к БД
8. Валидация временных меток
9. Управление временными файлами

### 4. По возможности (Низкие проблемы):
10. Улучшение логирования
11. Дополнительная валидация форм
12. Вынос констант в настройки

---

## 🛠️ ОБЩИЕ РЕКОМЕНДАЦИИ

1. **Добавить comprehensive logging** для всех критических операций
2. **Внедрить monitoring** для отслеживания производительности и ошибок
3. **Создать unit тесты** для всех критических функций
4. **Добавить integration тесты** для проверки пайплайна обработки видео
5. **Внедрить rate limiting** для API endpoints
6. **Добавить health checks** для всех внешних сервисов
7. **Настроить регулярную очистку** временных файлов и логов
8. **Внедрить circuit breaker** для внешних API вызовов

---

## 📝 ЗАКЛЮЧЕНИЕ

В коде обнаружено 12 проблем разной степени критичности. Наиболее срочно требуют внимания проблемы безопасности, особенно связанные с загрузкой файлов и обработкой внешних URL. Рекомендуется немедленно приступить к исправлению критических проблем, так как они могут привести к серьезным последствиям в production среде.

После исправления всех выявленных проблем, код станет значительно более надежным, безопасным и производительным.
