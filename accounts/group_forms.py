from django import forms
from .models import StudyGroup


class StudentNamesForm(forms.Form):
    names = forms.CharField(label='Імена учнів — кожен з нового рядка', widget=forms.Textarea(attrs={'rows': 6}), max_length=10000)

    def clean_names(self):
        names = [line.strip() for line in self.cleaned_data['names'].splitlines() if line.strip()]
        if not names or len(names) > 100 or any(len(name) > 150 for name in names):
            raise forms.ValidationError('Введіть від 1 до 100 імен, до 150 символів кожне.')
        return names


class GroupForm(forms.ModelForm):
    class Meta:
        model = StudyGroup
        fields = ['name', 'start_date']
        labels = {'name': 'Назва групи', 'start_date': 'Дата запуску'}
        widgets = {'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}


class StudentEditForm(forms.Form):
    first_name = forms.CharField(label='Ім’я', max_length=150)
    last_name = forms.CharField(label='Прізвище', max_length=150, required=False)
    study_group = forms.ModelChoiceField(label='Група', queryset=StudyGroup.objects.none())

    def __init__(self, *args, groups, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['study_group'].queryset = groups
