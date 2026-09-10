# AI Student Workbook

Веб-тетрадь для учнів: дитина реєструється, заповнює динамічні сторінки, відповіді зберігаються в БД, адміністратор переглядає тетради та редагує структуру шаблону.

## Уже реалізовано

- реєстрація та авторизація учнів;
- окремий доступ адміністратора;
- динамічна модель `Шаблон → Сторінки → Елементи`;
- типи елементів: короткий текст, велике поле, чекліст, список, рейтинг, таблиця, статичний текст;
- збереження відповідей кожного учня в БД;
- сторінка адміністратора зі списком тетрадей;
- редагування шаблону через Django Admin;
- експорт особистої тетради у PDF через WeasyPrint;
- стартовий seed на 8 розділів тетради.

## Стек

- Python 3.12+
- Django 5
- SQLite для MVP (потім PostgreSQL без зміни моделей)
- Django templates + CSS
- WeasyPrint для PDF

## Запуск

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_workbook
python manage.py createsuperuser
python manage.py runserver
```

Міграції вже включені в проєкт. Для перевірки: `python manage.py check` та
`python manage.py test`.

### Windows: повторний локальний запуск

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Налаштування читаються зі змінних середовища; файл `.env.example` є прикладом,
а `.env` автоматично не завантажується.

### PDF у Windows

Окрім Python-пакетів, WeasyPrint потребує системних бібліотек Pango/GObject.
Якщо вони відсутні, сайт працює, а експорт показує повідомлення про недоступність.
Встановіть MSYS2 та виконайте в його UCRT64 shell:

```bash
pacman -S mingw-w64-ucrt-x86_64-pango
```

Перед запуском Django в PowerShell задайте шлях і перевірте генерацію PDF:

```powershell
$env:WEASYPRINT_DLL_DIRECTORIES = 'C:\msys64\ucrt64\bin'
.\.venv\Scripts\python.exe -c "from weasyprint import HTML; print(len(HTML(string='<p>Test</p>').write_pdf()))"
```

Докладніше: [офіційна інструкція WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows).

Відкрити:

- `http://127.0.0.1:8000/` — учнівська частина;
- `http://127.0.0.1:8000/admin-panel/` — зручний список тетрадей;
- `http://127.0.0.1:8000/django-admin/` — конструктор шаблону.

## Як працює конструктор

`WorkbookBlock.config` зберігає налаштування конкретного типу елемента у JSON.

Приклади:

```json
{"options": ["Варіант 1", "Варіант 2"]}
```

для чекліста / select;

```json
{"max": 5}
```

для рейтингу;

```json
{"columns": ["Тема", "Що зрозумів"], "rows": ["Урок 1", "Урок 2"]}
```

для таблиці.

## Наступний технічний етап

1. drag-and-drop конструктор замість JSON у Django Admin;
2. автоматичне збереження полів без кнопки;
3. кілька шаблонів тетрадей / курси / групи;
4. PostgreSQL + деплой;
5. красивіший PDF із брендингом.
