import uuid
from django.core import signing
from django.core.exceptions import PermissionDenied
from .models import SubmissionReceipt


def issue(user, scope):
    return signing.dumps({'id': str(uuid.uuid4()), 'owner': user.pk, 'scope': scope}, salt='form-submission')


def claim(request, scope):
    try:
        value = signing.loads(request.POST.get('submission_token', ''), salt='form-submission', max_age=86400)
        if value['owner'] != request.user.pk or value['scope'] != scope:
            raise PermissionDenied
        token = uuid.UUID(value['id'])
    except (signing.BadSignature, KeyError, ValueError, TypeError):
        raise PermissionDenied('Форма застаріла. Оновіть сторінку й повторіть дію.')
    receipt, created = SubmissionReceipt.objects.get_or_create(token=token, defaults={'owner': request.user, 'scope': scope})
    return receipt, created
