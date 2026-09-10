document.querySelector('#download-credentials').addEventListener('click', () => {
    const text = Array.from(document.querySelectorAll('#credentials tr')).map(row => Array.from(row.cells).slice(0, 3).map(cell => cell.textContent.trim()).join(' | ')).join('\r\n');
    const url = URL.createObjectURL(new Blob(['\ufeff' + text], {type: 'text/plain;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'student-logins.txt'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
});
