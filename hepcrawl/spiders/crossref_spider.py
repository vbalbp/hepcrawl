# -*- coding: utf-8 -*-
#
# This file is part of hepcrawl.
# Copyright (C) 2015, 2016, 2017 CERN.
#
# hepcrawl is a free software; you can redistribute it and/or modify it
# under the terms of the Revised BSD License; see LICENSE file for
# more details.

"""Spider for Crossref."""

from __future__ import absolute_import, division, print_function

import json
import link_header

from furl import furl

from scrapy import Request

from inspire_utils.record import get_value

from . import StatefulSpider
from ..items import HEPRecord
from ..loaders import HEPLoader
from ..parsers import JatsParser
from ..utils import (
    get_licenses,
    build_dict,
    ParsedItem,
    strict_kwargs,
)


class APSSpider(StatefulSpider):
    """APS crawler.

    Uses the Crossref Metadata API v2.
    .. _See documentation here:
        https://github.com/CrossRef/rest-api-doc

    Example:
        Using the Crossref spider::

            $ scrapy crawl Crossref -a 'query=global+state' -a 'filter_name=has-orcid' -a 'filter_value=true'
    """
    name = 'Crossref'
    crossref_base_url = "https://api.crossref.org/works"

    @strict_kwargs
    def __init__(self, url=None, query=None, filter_name=None, filter_value=None, rows=100,
                 **kwargs):
        """Construct Crossref spider."""
        super(CrossrefSpider, self).__init__(**kwargs)
        if url is None:
            # We Construct.
            params = {}
            if query:
                params['query'] = query
            if filterp:
                params['filter'] = {filter_name: filter_value}
            params['rows'] = rows

            url = furl(CrossrefSpider.crossref_base_url).add(params).url
        self.url = url

    def start_requests(self):
        """Just yield the url."""
        yield Request(self.url)

    def parse(self, response):
        """Parse a Crossref record into a HEP record."""
        crossref_response = json.loads(response.body_as_unicode())

        for article in crossref_response['message']['items']:
            doi = get_value(article, 'DOI', default='')

            if doi:
                request = Request(url='{}/{}'.format(self.crossref_base_url, doi),
                              callback=self._parse_json)
                request.meta['json_article'] = article
                request.meta['original_response'] = response
                yield request

        # Pagination support. Will yield until no more "next" pages are found
        if len(crossref_response['message']['items']) == 100:
            cursor = request['message']['next-cursor']
            next_url = furl(self.url).set({'cursor':cursor}).url
            yield Request(next_url)

    def _parse_json(self, response):
        """Parse a JSON article entry."""
        parser = CrossrefParser(response.meta)

        return ParsedItem(
            record=parser.parse(),
            record_format='hep',
        )
