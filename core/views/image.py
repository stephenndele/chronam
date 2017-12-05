from __future__ import absolute_import

import gzip
import logging
import os.path
import urllib2
import urlparse
from cStringIO import StringIO

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseServerError

from chronam.core import models
from chronam.core.decorator import cors
from chronam.core.utils.utils import get_page

LOGGER = logging.getLogger(__name__)

if settings.USE_TIFF:
    LOGGER.info("Configured to use TIFFs. Set USE_TIFF=False if you want to use the JPEG2000s.")
    from PIL import Image
else:
    import NativeImaging

    for backend in ('aware_cext', 'aware', 'graphicsmagick'):
        try:
            Image = NativeImaging.get_image_class(backend)
            LOGGER.info("Using NativeImage backend '%s'", backend)
            break
        except ImportError as e:
            LOGGER.info("NativeImage backend '%s' not available.", backend)
    else:
        raise Exception("No suitable NativeImage backend found.")

def image_tile(request, path, width, height, x1, y1, x2, y2):
    if 'download' in request.GET and request.GET['download']:
        response = HttpResponse(content_type="binary/octet-stream")
    else:
        response = HttpResponse(content_type="image/jpeg")

    width, height = int(width), int(height)
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    try:
        p = os.path.join(settings.BATCH_STORAGE, path)
        im = Image.open(p)
    except IOError as e:
        return HttpResponseServerError("Unable to create image tile: %s" % e)

    width = min(width, (x2-x1))
    height = min(height, (y2-y1))

    c = im.crop((x1, y1, x2, y2))
    f = c.resize((width, height))
    f.save(response, "JPEG")
    return response

def resize(request, path, width, height):
    response = HttpResponse(content_type="image/jpeg")

    width, height = int(width), int(height)
    try:
        p = os.path.join(settings.BATCH_STORAGE, path)
        im = Image.open(p)
    except IOError as e:
        return HttpResponseServerError("Unable to read image for resizing: %s" % e)

    actual_width, actual_height = im.size

    # Accommodate "fit to width" requests as these are how thumbnails work
    if height == 0:
        height = int(round(width / float(actual_width) * float(actual_height)))

    f = im.resize((width, height))
    f.save(response, "JPEG")
    return response

@cors
def coordinates(request, lccn, date, edition, sequence, words=None):
    url_parts = dict(lccn=lccn, date=date, edition=edition, sequence=sequence)

    file_path = models.coordinates_path(url_parts)

    try:
        with gzip.open(file_path, 'rb') as i:
            return HttpResponse(i.read(), content_type='application/json')
    except IOError:
        LOGGER.warning('Word coordinates file %s does not exist', file_path)
        raise Http404
