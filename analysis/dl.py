from eeinit import ee
import urllib.request, sys
def download(img, region, scale, path):
    url=img.getDownloadURL({'region':region,'scale':scale,'format':'GEO_TIFF','crs':'EPSG:4326'})
    urllib.request.urlretrieve(url,path); print('saved',path)
