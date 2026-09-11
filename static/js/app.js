document.querySelectorAll('.editable-table').forEach(table => {
    const body = table.querySelector('tbody');
    const prefix = `block_${table.dataset.blockId}`;
    const actions = table.querySelector('.row-actions');
    function alignActions() {
        Array.from(body.rows).forEach((row, index) => {
            const button = actions.children[index];
            if (button) button.style.top = `${row.getBoundingClientRect().top - actions.getBoundingClientRect().top + row.getBoundingClientRect().height / 2}px`;
        });
    }
    function syncActions() {
        actions.replaceChildren();
        Array.from(body.rows).forEach((row, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'remove-row';
            button.textContent = '\u00d7';
            button.setAttribute('aria-label', `Видалити рядок ${index + 1}`);
            button.addEventListener('click', () => {
                row.remove();
                table.closest('form')?.dispatchEvent(new Event('input', {bubbles:true}));
                renumber();
                syncActions();
            });
            actions.append(button);
        });
        alignActions();
    }
    new ResizeObserver(alignActions).observe(table.querySelector('.input-table'));
    window.addEventListener('resize', alignActions);
    syncActions();
    function renumber() {
        Array.from(body.rows).forEach((row, index) => {
            row.querySelector('.row-number').textContent = index + 1;
            row.querySelector('input[type=hidden]').value = index + 1;
            row.querySelectorAll('textarea').forEach((cell, column) => {
                cell.name = `${prefix}_${index}_${column}`;
            });
        });
    }
    table.querySelector('.add-row').addEventListener('click', () => {
        if (body.rows.length >= 100) return;
        body.append(table.querySelector('template').content.cloneNode(true));
        table.closest('form')?.dispatchEvent(new Event('input', {bubbles:true}));
        renumber();
        syncActions();
        body.lastElementChild.querySelector('textarea')?.focus();
    });
});

const avatarInput = document.querySelector('#avatar-upload');
if (avatarInput) {
    let previewUrl;
    avatarInput.addEventListener('change', () => {
        const file = avatarInput.files[0];
        if (!file) return;
        const editor = avatarInput.closest('.avatar-editor');
        const status = editor.querySelector('.avatar-status');
        if (file.size > 5 * 1024 * 1024) {
            status.textContent = 'Оберіть фото до 5 МБ.';
            avatarInput.value = '';
            return;
        }
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(file);
        const image = editor.querySelector('.avatar-preview');
        image.onload = () => {
            image.hidden = false;
            editor.querySelector('.avatar-placeholder').hidden = true;
            status.textContent = 'Натисніть «Зберегти», щоб зберегти фото.';
        };
        image.onerror = () => {
            image.hidden = true;
            editor.querySelector('.avatar-placeholder').hidden = false;
            status.textContent = 'Оберіть коректне зображення.';
            avatarInput.value = '';
        };
        image.src = previewUrl;
    });
}
const sideArtwork = document.querySelector('.assignment-art');
if (sideArtwork) {
    const reveal = async () => {
        try { await sideArtwork.decode(); } catch (_) {}
        requestAnimationFrame(() => requestAnimationFrame(() => {
            setTimeout(() => sideArtwork.classList.add('art-visible'), 180);
        }));
    };
    reveal();
}
