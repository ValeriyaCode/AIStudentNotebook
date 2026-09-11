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
        const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
        const offset = document.body.classList.contains('art-left') ? '-160px' : '160px';
        const animation = sideArtwork.animate([
            {opacity: 0, translate: reduced ? '0 0' : `${offset} 0`, filter: reduced ? 'none' : 'blur(18px)'},
            {opacity: 1, translate: '0 0', filter: 'blur(0px)'}
        ], {duration: reduced ? 1200 : 2400, delay: 150, easing: 'cubic-bezier(.22,.61,.36,1)', fill: 'both'});
        await animation.finished;
        sideArtwork.classList.add('art-visible');
        animation.cancel();
    };
    reveal();
}
