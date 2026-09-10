from django import forms
from .models import WorkbookBlock


def build_block_field(block: WorkbookBlock, current=None):
    config = block.config or {}
    common = {
        'label': block.label,
        'help_text': block.help_text,
        'required': block.required,
    }

    if block.block_type == WorkbookBlock.Type.TEXT:
        return forms.CharField(**common, max_length=20000, initial=current or '', widget=forms.TextInput(attrs={'placeholder': config.get('placeholder', '')}))

    if block.block_type == WorkbookBlock.Type.TEXTAREA:
        return forms.CharField(**common, max_length=20000, initial=current or '', widget=forms.Textarea(attrs={'rows': config.get('rows', 5), 'placeholder': config.get('placeholder', '')}))

    if block.block_type == WorkbookBlock.Type.CHECKBOXES:
        choices = [(item, item) for item in config.get('options', [])]
        return forms.MultipleChoiceField(**common, choices=choices, initial=current or [], widget=forms.CheckboxSelectMultiple)

    if block.block_type == WorkbookBlock.Type.SELECT:
        choices = [('', '— Оберіть —')] + [(item, item) for item in config.get('options', [])]
        return forms.ChoiceField(**common, choices=choices, initial=current or '')

    if block.block_type == WorkbookBlock.Type.RATING:
        max_value = int(config.get('max', 5))
        choices = [(str(i), '★' * i) for i in range(1, max_value + 1)]
        return forms.ChoiceField(**common, choices=choices, initial=str(current) if current else '', widget=forms.RadioSelect)

    if block.block_type == WorkbookBlock.Type.TABLE:
        # Table values are handled separately in the template and view.
        return None

    return None


def extract_answer_value(block: WorkbookBlock, post_data):
    key = f'block_{block.id}'
    if block.block_type == WorkbookBlock.Type.CHECKBOXES:
        return post_data.getlist(key)
    if block.block_type == WorkbookBlock.Type.TABLE:
        rows = (block.config or {}).get('rows', [])
        if f'{key}_rows_present' in post_data:
            rows = post_data.getlist(f'{key}_row')
        columns = (block.config or {}).get('columns', [])
        table = []
        for r_idx, row_label in enumerate(rows):
            row = {'_row': row_label}
            for c_idx, col_label in enumerate(columns):
                row[col_label] = post_data.get(f'{key}_{r_idx}_{c_idx}', '').strip()
            table.append(row)
        return table
    return post_data.get(key, '').strip()


class WorkbookPageForm(forms.Form):
    def __init__(self, blocks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocks = blocks
        for block in blocks:
            field = build_block_field(block)
            if field is not None:
                self.fields[f'block_{block.pk}'] = field

    def clean(self):
        cleaned = super().clean()
        for block in self.blocks:
            if block.block_type != WorkbookBlock.Type.TABLE:
                continue
            key = f'block_{block.pk}'
            rows = self.data.getlist(f'{key}_row') if f'{key}_rows_present' in self.data else (block.config or {}).get('rows', [])
            if len(rows) > 100:
                self.add_error(None, f'{block.label}: максимум 100 рядків.')
                continue
            value = extract_answer_value(block, self.data)
            if any(len(str(cell)) > 20000 for row in value for cell in row.values()):
                self.add_error(None, f'{block.label}: текст у клітинці завеликий.')
            if block.required and not any(cell for row in value for name, cell in row.items() if name != '_row'):
                self.add_error(None, f'{block.label}: заповніть таблицю.')
            cleaned[key] = value
        return cleaned
