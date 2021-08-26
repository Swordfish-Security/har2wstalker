import base64
import json
from haralyzer_3 import *
from urllib.parse import urlparse

HAR_FILENAME = 'stingray_more.har'  # file in HAR format
CSV_FILENAME = 'stingray_more.csv'  # file to import into the plugin
nl = '\r\n'
wstalker_out = ''

with open(HAR_FILENAME, 'r') as har_file:
    har = HarParser(json.loads(har_file.read()))
    har_page_entries = HarPage("unknown", har_parser=har).entries

for har_page_entry in har_page_entries:
    # Getting raw headers dictionary from the HAR contents
    req_raw_headers = har_page_entry.request.raw_entry['headers']
    resp_raw_headers = har_page_entry.response.raw_entry['headers']

    # Building a query string for request (ex, GET / HTTP/1.1) and server response code
    req_query = '%s %s HTTP/1.1' % (har_page_entry.request.method, urlparse(har_page_entry.request.url).path)
    resp_code = 'HTTP/1.1 %s %s' % (har_page_entry.response.status, har_page_entry.response.statusText)

    # Building HTTP headers for requests and response
    req_headers = ''
    for header in req_raw_headers:
        req_headers += "%s: %s" % (header['name'], header['value']) + nl
    resp_headers = ''
    for header in resp_raw_headers:
        resp_headers += "%s: %s" % (header['name'], header['value']) + nl

    # POST contents
    post_body = ''
    if har_page_entry.request.method in ['POST', 'PUT']:
        post_body = har_page_entry.request['postData']['text'] + nl
    # TODO: if needed it is possible to return response data as well
    req = req_query + nl + req_headers + nl + post_body
    resp = resp_code + nl + resp_headers
    print(req+nl+resp)

    # encoding to base64 according to wstalker format: b64(req),b64(resp),httpMethod,URL
    wstalker_out += base64.b64encode(req.encode('ascii')).decode() + ','
    wstalker_out += base64.b64encode(resp.encode('ascii')).decode() + ','
    wstalker_out += har_page_entry.request.method + ',' + har_page_entry.request.url
    wstalker_out += nl

print(wstalker_out)

with open(CSV_FILENAME, 'wb') as csv_file:
    csv_file.write(wstalker_out.encode('ascii'))
