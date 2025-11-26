from django import forms
from .models import OperatorLabel


class OperatorDecisionForm(forms.Form):
    """Форма для принятия решения по AI триггеру"""
    final_label = forms.ChoiceField(
        choices=OperatorLabel.FinalLabel.choices,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'hx-trigger': 'change',
            'hx-get': '',
            'hx-target': '#decision-preview',
        }),
        label='Решение'
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Добавить комментарий (необязательно)...'
        }),
        required=False,
        label='Комментарий'
    )


class TaskCompletionForm(forms.Form):
    """Форма для завершения задачи верификации"""
    decision_summary = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Краткое итоговое описание принятых решений...'
        }),
        required=False,
        label='Итоговое решение'
    )