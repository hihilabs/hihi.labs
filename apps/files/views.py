import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DriveCredential, DriveFolder


def _drive_client(credential):
    """Build an authorized Google Drive service from stored tokens."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from datetime import datetime

    creds = Credentials(
        token=credential.access_token,
        refresh_token=credential.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_DRIVE_CLIENT_ID,
        client_secret=settings.GOOGLE_DRIVE_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/drive.readonly'],
    )
    service = build('drive', 'v3', credentials=creds)
    # Persist refreshed token
    if creds.token != credential.access_token:
        credential.access_token = creds.token
        if creds.expiry:
            credential.token_expiry = timezone.make_aware(creds.expiry) if creds.expiry.tzinfo is None else creds.expiry
        credential.save(update_fields=['access_token', 'token_expiry'])
    return service


def _auth_url():
    """Build Google OAuth2 authorization URL."""
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': settings.GOOGLE_DRIVE_CLIENT_ID,
                'client_secret': settings.GOOGLE_DRIVE_CLIENT_SECRET,
                'redirect_uris': [settings.GOOGLE_DRIVE_REDIRECT_URI],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=[
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid',
        ],
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI,
    )
    url, state = flow.authorization_url(access_type='offline', prompt='consent')
    return url, state, flow


@login_required
def index(request):
    try:
        credential = request.user.drive_credential
        connected = True
    except DriveCredential.DoesNotExist:
        credential = None
        connected = False

    folders = DriveFolder.objects.filter(owner=request.user).select_related('project', 'client')
    project_id = request.GET.get('project')
    client_id = request.GET.get('client')
    folder_id = request.GET.get('folder')

    files = []
    current_folder = None
    breadcrumb = []

    if connected and folder_id:
        try:
            service = _drive_client(credential)
            result = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields='files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink)',
                orderBy='name',
                pageSize=100,
            ).execute()
            files = result.get('files', [])
            meta = service.files().get(fileId=folder_id, fields='id,name,parents').execute()
            current_folder = meta
            breadcrumb = [{'id': folder_id, 'name': meta.get('name', folder_id)}]
        except Exception as e:
            files = []

    return render(request, 'files/index.html', {
        'connected': connected,
        'credential': credential,
        'folders': folders,
        'files': files,
        'current_folder': current_folder,
        'breadcrumb': breadcrumb,
        'active_project_id': project_id,
        'active_client_id': client_id,
        'active_folder_id': folder_id,
    })


@login_required
def oauth_start(request):
    url, state, flow = _auth_url()
    request.session['gdrive_oauth_state'] = state
    # Persist PKCE code_verifier (lives on flow.code_verifier in oauthlib 1.x)
    cv = getattr(flow, 'code_verifier', None)
    if cv:
        request.session['gdrive_code_verifier'] = cv
    return redirect(url)


@login_required
def oauth_callback(request):
    import requests as http_requests
    from google.oauth2 import id_token as google_id_token
    import google.auth.transport.requests

    code = request.GET.get('code')
    if not code:
        return redirect('files:index')

    # Exchange code for tokens directly to avoid PKCE verifier loss
    token_data = {
        'code': code,
        'client_id': settings.GOOGLE_DRIVE_CLIENT_ID,
        'client_secret': settings.GOOGLE_DRIVE_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_DRIVE_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    cv = request.session.pop('gdrive_code_verifier', None)
    if cv:
        token_data['code_verifier'] = cv

    token_resp = http_requests.post('https://oauth2.googleapis.com/token', data=token_data)
    tokens = token_resp.json()

    if 'error' in tokens:
        import logging
        logging.getLogger(__name__).error('Drive token exchange error: %s', tokens)
        return redirect('files:index')

    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')
    id_token_str = tokens.get('id_token', '')

    email = ''
    if id_token_str:
        try:
            req = google.auth.transport.requests.Request()
            info = google_id_token.verify_oauth2_token(id_token_str, req, settings.GOOGLE_DRIVE_CLIENT_ID)
            email = info.get('email', '')
        except Exception:
            pass

    import datetime
    expires_in = tokens.get('expires_in')
    token_expiry = None
    if expires_in:
        token_expiry = timezone.now() + datetime.timedelta(seconds=expires_in)

    DriveCredential.objects.update_or_create(
        owner=request.user,
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'email': email,
            'token_expiry': token_expiry,
        },
    )
    return redirect('files:index')


@login_required
@require_POST
def oauth_disconnect(request):
    DriveCredential.objects.filter(owner=request.user).delete()
    return redirect('files:index')


@login_required
def browse_api(request):
    """AJAX: list files/folders in a Drive folder."""
    folder_id = request.GET.get('folder_id', 'root')
    try:
        credential = request.user.drive_credential
    except DriveCredential.DoesNotExist:
        return JsonResponse({'error': 'not_connected'}, status=401)

    try:
        service = _drive_client(credential)
        result = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields='files(id,name,mimeType,size,modifiedTime,thumbnailLink,webViewLink,iconLink)',
            orderBy='folder,name',
            pageSize=200,
        ).execute()
        return JsonResponse({'files': result.get('files', [])})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def link_folder(request):
    """Link a Drive folder to a project or client."""
    data = json.loads(request.body)
    folder_id = data.get('folder_id')
    folder_name = data.get('folder_name', folder_id)
    project_id = data.get('project_id')
    client_id = data.get('client_id')

    DriveFolder.objects.update_or_create(
        owner=request.user,
        drive_folder_id=folder_id,
        defaults={
            'name': folder_name,
            'project_id': project_id or None,
            'client_id': client_id or None,
        },
    )
    return JsonResponse({'ok': True})


@login_required
@require_POST
def unlink_folder(request, pk):
    get_object_or_404(DriveFolder, pk=pk, owner=request.user).delete()
    return JsonResponse({'ok': True})


def _gmail_service(credential):
    """Build an authorized Gmail service from stored tokens."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(
        token=credential.access_token,
        refresh_token=credential.refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_DRIVE_CLIENT_ID,
        client_secret=settings.GOOGLE_DRIVE_CLIENT_SECRET,
        scopes=['https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/gmail.readonly'],
    )
    return build('gmail', 'v1', credentials=creds)
