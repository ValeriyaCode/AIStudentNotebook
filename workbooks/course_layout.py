GROUP_SIZES = [
    [5, 4, 6], [2, 2, 2, 2], [1, 1, 5], [1, 6], [1, 2, 2, 1],
    [1, 3, 3, 3, 1], [1, 4, 3, 1], [1, 3, 3, 2],
    [1, 3, 3, 3, 3, 1], [1, 3, 3, 3, 3, 3], [1, 7], [3, 1, 4, 1], [2],
]

def block_layout(page_index, block_index, label):
    offset = 0
    for group, size in enumerate(GROUP_SIZES[page_index]):
        if block_index < offset + size:
            return {'card_key': f'card-{group}',
                    'card_style': 'tool' if label.startswith('Інструменти,') else ('profile' if label == 'Про мене' else ''),
                    'half_width': label in {'Ім’я', 'Прізвище', 'Вік', 'Клас'}}
        offset += size
    return {}
