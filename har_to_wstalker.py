import argparse
import base64
import json
import logging
from haralyzer_3 import *
from urllib.parse import urlparse


def filename_sanitizer(filename):
    """ replaces potentially unsafe characters """

    logging.debug('Little bit of filename sanitizing')
    unacceptable = ['\\', '/', '&', '<', '>', '$', '|', '%', '?', '*', '"', ' ']
    for character in unacceptable:
        filename = filename.replace(character, '_')
    return filename


def parse_parameters():
    """ Parsing incoming parameters in one place and assigning them variables """

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', action='store', help='Input HAR file',
                        default='data.har')
    parser.add_argument('-o', '--output', action='store', help='Output CSV file',
                        default='data.csv')

    args = parser.parse_args()
    parsed_args = (args.input, args.output)
    return parsed_args


def main():
    nl = '\r\n'
    wstalker_out = ''

    #  workaround with encoding to parse Telerik Fiddler's .har files
    with open(filename_sanitizer(HAR_FILENAME), 'r', encoding='utf-8-sig') as har_file:
        logging.info('Reading file')
        har_contents = har_file.read()
        har = HarParser(json.loads(har_contents))
        har_page_entries = HarPage("unknown", har_parser=har).entries

    logging.info('Parsing file')
    for har_page_entry in har_page_entries:
        # Getting raw headers dictionary from the HAR contents
        req_raw_headers = har_page_entry.request.raw_entry['headers']
        resp_raw_headers = har_page_entry.response.raw_entry['headers']

        # Some HTTP requests (esp. in HTTP/2) doesn't have a separate  Host: header so we'll build it ourselves
        if not har_page_entry.request.host:
            req_raw_headers.append({'name': 'Host', 'value': urlparse(har_page_entry.request.url).netloc})

        # Building a query string for request (ex, GET / HTTP/1.1) and server response code
        req_query = '%s %s %s' % (har_page_entry.request.method,
                                  urlparse(har_page_entry.request.url).path,
                                  har_page_entry.request.httpVersion)
        resp_code = '%s %s %s' % (har_page_entry.request.httpVersion,
                                  har_page_entry.response.status,
                                  har_page_entry.response.statusText)

        # Building HTTP headers for requests and response
        req_headers = ''
        for header in req_raw_headers:
            # workaround as Burp doesn't support Brotli compression algorithm so we wouldn't want to request it
            if header['name'] == 'Accept-Encoding' and 'br' in header['value']:
                header['value'] = header['value'].replace(', br', '')
            req_headers += "%s: %s" % (header['name'], header['value']) + nl

        resp_headers = ''
        for header in resp_raw_headers:
            resp_headers += "%s: %s" % (header['name'], header['value']) + nl

        # POST contents
        post_body = ''
        if not har_page_entry.request['postData']['text'] == '':
            post_body = har_page_entry.request['postData']['text']

        # TODO: if needed it is possible to return response data as well
        req = req_query + nl + req_headers + nl + post_body
        resp = resp_code + nl + resp_headers

        # encoding to base64 according to wstalker format: b64(req),b64(resp),httpMethod,URL
        wstalker_out += base64.b64encode(req.encode()).decode() + ','
        wstalker_out += base64.b64encode(resp.encode()).decode() + ','
        wstalker_out += har_page_entry.request.method + ',' + har_page_entry.request.url
        wstalker_out += nl

    with open(CSV_FILENAME, 'wb') as csv_file:
        logging.info('Writing output file')
        csv_file.write(wstalker_out.encode('ascii'))


if __name__ == '__main__':
    # retrieving command-line parameters
    parameters = parse_parameters()

    # Configuring logging parameters
    log_level = logging.DEBUG
    log_format = "[%(levelname)s] (%(asctime)s): %(message)s"
    logging.getLogger('chardet.charsetprober').setLevel(logging.INFO)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.basicConfig(level=log_level, format=log_format)

    logging.info('Starting main module')
    HAR_FILENAME = parameters[0]  # file in HAR format
    CSV_FILENAME = parameters[1]  # file to import into the plugin

    main()
