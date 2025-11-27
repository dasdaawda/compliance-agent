# ✅ Fixes Applied - November 27, 2024

This document summarizes the critical fixes and improvements applied to the AI-Compliance Agent MVP based on the comprehensive compliance audit (see `SPEC_COMPLIANCE_AUDIT.md`).

## Priority 1: Critical Bug Fixes

### ✅ Fix #1: RiskDefinition.code Default Bug (CRITICAL)

**Issue:** `RiskDefinition.code` field had `default=uuid.uuid4` which evaluates once at model definition, causing all instances to share the same UUID and violating the `unique=True` constraint.

**File:** `backend/ai_pipeline/models.py:103`

**Before:**
```python
code = models.CharField(..., default=uuid.uuid4, ...)
```

**After:**
```python
code = models.CharField(..., unique=True, db_index=True)  # No default - requires explicit value
```

**Impact:** Critical - prevents IntegrityError on RiskDefinition creation.

---

### ✅ Fix #2: NLP Dictionaries Missing (CRITICAL)

**Issue:** `NLPDictionaryService` was using placeholder lists instead of real dictionaries, making Whisper profanity/brand detection ineffective.

**Files Created:**
- `backend/ai_pipeline/dictionaries/profanity_ru.txt` (10 Russian profanity words)
- `backend/ai_pipeline/dictionaries/brands.txt` (65 international brands)
- `backend/ai_pipeline/dictionaries/stopwords_legal.txt` (30 legal/compliance keywords)

**Settings Updated:** `backend/compliance_app/settings/base.py:181-184`
```python
PROFANITY_DICT_PATH = env('PROFANITY_DICT_PATH', default=str(BASE_DIR / 'ai_pipeline' / 'dictionaries' / 'profanity_ru.txt'))
BRAND_DICT_PATH = env('BRAND_DICT_PATH', default=str(BASE_DIR / 'ai_pipeline' / 'dictionaries' / 'brands.txt'))
STOPWORDS_DICT_PATH = env('STOPWORDS_DICT_PATH', default=str(BASE_DIR / 'ai_pipeline' / 'dictionaries' / 'stopwords_legal.txt'))
```

**Impact:** Critical - enables real NLP trigger detection (Whisper + dictionaries).

---

### ✅ Fix #3: Incomplete Operator Label Categories (CRITICAL)

**Issue:** Only 6 out of 16+ required label categories implemented, violating the "Data-as-an-Asset" philosophy (Spec Module 5.2, Table 3).

**File:** `backend/operators/models.py:62-91`

**Categories Added:**
- `AD_WEBSITE_PHONE` - "Реклама (сайт/телефон)"
- `AD_NATIVE` - "Рекламная интеграция (нативная)"
- `ALCOHOL_VISIBLE` - "Алкоголь (в кадре)"
- `TOBACCO_VAPE` - "Табак/Вейп (в кадре)"
- `PROFANITY_TEXT` - "Мат (в тексте)"
- `EROTICA_16` - "Эротика (16+)"
- `FIGHT_BLOOD_16` - "Драка/Кровь (16+)"
- `PROHIBITED_INFO` - "Запрещ. информация (призыв)"
- `PROHIBITED_SYMBOLS` - "Запрещ. символика"
- `TATTOO_GENERAL` - "Тату (общее)"

**Total:** 19 categories (6 existing + 10 new + 3 grouped)

**Impact:** Critical - enables complete labeling map per spec, proper dataset collection for v2.0 AI training.

---

### ✅ Fix #4: LabelingService Mapping Incomplete

**Issue:** Mapping only covered 4 trigger sources, missing OCR and Whisper_Brand.

**File:** `backend/operators/services.py:44-83`

**Mappings Added:**
- `AITrigger.TriggerSource.YOLO_OBJECT` → [OK, AD_BRAND, **ALCOHOL_VISIBLE, TOBACCO_VAPE, PROHIBITED_SYMBOLS, TATTOO_GENERAL**]
- `AITrigger.TriggerSource.WHISPER_BRAND` → [OK_FALSE, **AD_NATIVE**] (NEW)
- `AITrigger.TriggerSource.FALCONSAI_NSFW` → [OK, **EROTICA_16**, PORNOGRAPHY_18]
- `AITrigger.TriggerSource.VIOLENCE_DETECTOR` → [OK, **FIGHT_BLOOD_16**, VIOLENCE_18]
- `AITrigger.TriggerSource.EASYOCR_TEXT` → [OK, **AD_WEBSITE_PHONE, PROFANITY_TEXT, PROHIBITED_INFO**] (NEW)

**Impact:** High - ensures correct label button sets displayed for each trigger type (Spec Table 3).

---

## Priority 2: Missing Features

### ✅ Fix #5: Manual Risk Addition (US-O9) Implemented

**Issue:** Operator had no UI button to manually add risks that AI missed (False Negatives).

**Files Modified:**
- `backend/operators/views.py` - Added `AddManualLabelView` class
- `backend/operators/urls.py:10` - Added route `/workspace/<uuid>/manual-label/`
- `backend/templates/operators/workspace.html:134-139` - Added button
- `backend/templates/operators/workspace.html:44` - Added `final_label_choices` JSON data

**New View:**
```python
class AddManualLabelView(LoginRequiredMixin, OperatorRequiredMixin, View):
    """Добавление риска вручную оператором (US-O9)."""
    def post(self, request, task_id):
        # Creates OperatorLabel with ai_trigger=None
        LabelingService.create_operator_label(
            video=task.video,
            operator=request.user,
            ai_trigger=None,  # Manual addition
            final_label=final_label,
            comment=comment,
            start_time_sec=start_time_sec
        )
```

**JavaScript Functions:**
- `openManualRiskModal()` - Displays form with timestamp, category dropdown, comment
- `submitManualRisk()` - POSTs to `/workspace/<uuid>/manual-label/`
- `closeManualRiskModal()` - Returns to default state

**Impact:** Medium - enables operators to add risks AI missed, improving report completeness.

---

## Summary

| Fix | Priority | Status | Impact |
|-----|----------|--------|--------|
| #1 RiskDefinition.code | 🔴 Critical | ✅ Fixed | Prevents IntegrityError |
| #2 NLP Dictionaries | 🔴 Critical | ✅ Fixed | Enables real trigger detection |
| #3 Label Categories | 🔴 Critical | ✅ Fixed | Enables dataset collection |
| #4 Label Mapping | 🟠 High | ✅ Fixed | Correct UI buttons per spec |
| #5 Manual Risk (US-O9) | 🟡 Medium | ✅ Implemented | Operator can add missed risks |

## Migration Required

After these fixes, run Django migrations:

```bash
cd backend
python manage.py makemigrations operators
python manage.py migrate
```

**Migration changes:**
- `OperatorLabel.final_label` field choices expanded (10 new categories)

## Testing Recommendations

1. **Test RiskDefinition creation:** Create multiple RiskDefinition instances with unique codes
2. **Test NLP dictionaries:** Upload video with profanity/brands, verify triggers generated
3. **Test operator labels:** Verify all 19 categories available in operator workspace dropdown
4. **Test label mapping:** Click different trigger types, verify correct button sets shown
5. **Test manual addition:** Click "Добавить риск вручную", submit form, verify label created

## Remaining Issues (Out of Scope)

These issues were identified in the audit but NOT fixed in this session:

- ❌ **US-C4:** Video URL download (yt-dlp integration) - requires VideoDownloader service
- ❌ **US-A5:** Admin statistics dashboard - requires custom Django Admin view
- ❌ **Documentation:** `docs/` directory missing (API.md, ARCHITECTURE.md, DEVELOPMENT.md)

See `SPEC_COMPLIANCE_AUDIT.md` for complete analysis and roadmap.

---

**Total Files Modified:** 10  
**Total Files Created:** 5  
**Lines of Code:** ~200 added/modified  
**Completion:** 75% → 82% (estimated)
