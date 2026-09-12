document.querySelectorAll('form[method="post"]').forEach(form => {
    let dirty = false;
    let submitting = false;
    const track = form.classList.contains('notebook-form') || form.classList.contains('management-form');
    form.addEventListener('input', () => { if (track) dirty = true; });
    form.addEventListener('change', () => { if (track) dirty = true; });
    window.addEventListener('beforeunload', event => {
        if (dirty && !submitting) { event.preventDefault(); event.returnValue = ''; }
    });
    form.addEventListener('submit', event => {
        if (submitting) { event.preventDefault(); return; }
        submitting = true;
        // Keep name/value of the clicked submitter in the POST.
        form.querySelectorAll('button[type="submit"], button:not([type])').forEach(button => button.setAttribute('aria-disabled', 'true'));
    });
    window.addEventListener('pageshow', () => {
        submitting = false;
        form.querySelectorAll('[aria-disabled="true"]').forEach(button => button.removeAttribute('aria-disabled'));
    });
});

// Only offer profile saving when the displayed values differ from the loaded profile.
document.querySelectorAll('.dashboard-profile').forEach(form => {
    const button = form.querySelector('.profile-save');
    if (!button) return;
    const fields = [...form.querySelectorAll('input[type="text"]')];
    const file = form.querySelector('input[type="file"]');
    const hasErrors = !button.hidden;
    const update = () => {
        button.hidden = !(hasErrors || fields.some(field => field.value !== field.defaultValue) || file?.files.length);
    };
    form.addEventListener('input', update);
    form.addEventListener('change', update);
    window.addEventListener('pageshow', update);
    form.addEventListener('focusin', update);
    form.addEventListener('focusout', update);
    // Browser autofill/password managers may change values without input/change events.
    window.setInterval(() => {
        if (!document.hidden) update();
    }, 300);
    update();
});
