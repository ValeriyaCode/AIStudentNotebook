from django.shortcuts import redirect


def register(request):
    return redirect('login')


from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from .models import User


@login_required
@never_cache
def avatar_media(request, filename):
    owner = get_object_or_404(User.objects.select_related('study_group'), avatar='avatars/' + filename)
    can_teach = request.user.is_admin_user and owner.study_group_id and owner.study_group.teacher_id == request.user.pk
    if owner.pk != request.user.pk and not request.user.is_superuser and not can_teach:
        raise PermissionDenied
    try:
        return FileResponse(owner.avatar.open('rb'), content_type='image/jpeg')
    except FileNotFoundError:
        raise Http404
