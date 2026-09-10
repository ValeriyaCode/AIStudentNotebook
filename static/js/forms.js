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
