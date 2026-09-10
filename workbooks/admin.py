from django.contrib import admin
from .models import StudentAnswer, StudentWorkbook, WorkbookBlock, WorkbookPage, WorkbookTemplate


class WorkbookBlockInline(admin.StackedInline):
    model = WorkbookBlock
    extra = 0
    fields = ('position', 'block_type', 'label', 'help_text', 'required', 'config')
    ordering = ('position',)


@admin.register(WorkbookPage)
class WorkbookPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'template', 'position')
    list_filter = ('template',)
    ordering = ('template', 'position')
    inlines = [WorkbookBlockInline]


class WorkbookPageInline(admin.TabularInline):
    model = WorkbookPage
    extra = 0
    fields = ('position', 'title', 'subtitle')
    ordering = ('position',)


@admin.register(WorkbookTemplate)
class WorkbookTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    inlines = [WorkbookPageInline]


@admin.register(StudentWorkbook)
class StudentWorkbookAdmin(admin.ModelAdmin):
    list_display = ('student', 'template', 'updated_at')
    list_filter = ('template',)
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'student__email')


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('workbook', 'block', 'updated_at')
    list_filter = ('block__page__template', 'block__page')
    search_fields = ('workbook__student__username', 'block__label')
