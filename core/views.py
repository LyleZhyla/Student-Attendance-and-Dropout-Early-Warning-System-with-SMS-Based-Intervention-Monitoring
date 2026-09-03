from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def react_app(request):
    index_file = Path(settings.REACT_BUILD_DIR) / 'index.html'
    if not index_file.exists():
        return HttpResponse(
            'The TardyTrack interface has not been built. Run run-system.cmd to create it.', status=503
        )
    return FileResponse(index_file.open('rb'), content_type='text/html')


def react_asset(request, filename):
    asset_file = Path(settings.REACT_BUILD_DIR) / filename
    if not asset_file.is_file() or asset_file.parent != Path(settings.REACT_BUILD_DIR):
        raise Http404
    content_types = {'favicon.svg': 'image/svg+xml', 'asset-manifest.json': 'application/json'}
    return FileResponse(asset_file.open('rb'), content_type=content_types.get(filename, 'application/octet-stream'))
