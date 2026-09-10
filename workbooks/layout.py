"""Render persisted card membership independently from editable labels."""
def prepare_groups(page, blocks):
    previous = None
    for index, block in enumerate(blocks):
        group = block.card_key or ('single', block.pk)
        block.continuation = index > 0 and group == previous
        block.ends_card = True
        block.tool_card = block.card_style == 'tool'
        block.profile_card = block.card_style == 'profile'
        if block.continuation:
            blocks[index - 1].ends_card = False
        previous = group
