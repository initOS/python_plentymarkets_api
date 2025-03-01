import copy
import pytest
import requests

from plenty_api.utils import (
    get_route, build_endpoint, check_date_range, parse_date, build_date_range,
    get_utc_offset, build_query_date, create_vat_mapping, date_to_timestamp,
    get_language, shrink_price_configuration, sanity_check_parameter,
    attribute_variation_mapping
)


# ======== SAMPLE INPUT DATA ==========


@pytest.fixture
def sample_date_ranges() -> list:
    samples = [
        {'start': '2020-09-14T08:00:00+02:00',  # Normal date => CORRECT
         'end': '2020-09-15T08:00:00+02:00'},
        {'start': '2020-09-16T08:00:00+02:00',  # End before start => FAIL
         'end': '2020-09-13T08:00:00+02:00'},
        {'start': '2019-09-16T08:00:00+02:00',  # Past date => CORRECT
         'end': '2019-10-13T08:00:00+02:00'},
        {'start': '2021-09-16T08:00:00+02:00',  # Future date => FAIL
         'end': '2021-10-13T08:00:00+02:00'}
    ]
    return samples


@pytest.fixture
def sample_input_date() -> list:
    samples = [
        '2020-09-14',
        '14-09-2020',
        '2020-09-14T08:00Z',
        '2020-09-14T08:00',
        '2020-09-14T08:00:00+02:00',
        'abc',
        ''
    ]
    return samples


@pytest.fixture
def expected_date() -> list:
    expected = [
        str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
        str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
        '2020-09-14T08:00:00+00:00',
        str(f'2020-09-14T08:00:00+{get_utc_offset()}'),
        '2020-09-14T08:00:00+02:00',
        '',
        ''
    ]
    return expected


@pytest.fixture
def sample_date_range_input() -> list:
    samples = [
        {'start': '2020-09-14', 'end': '2020-09-15'},
        {'start': '2020-09-14', 'end': '2020-09-13'},
        {'start': '2020-09-14T08:00Z', 'end': '2020-09-14T09:00Z'},
        {'start': '2020-09-14T08:00:00+02:00',
         'end': '2020-09-14T10:00:30+02:00'},
        {'start': 'abc', 'end': 'def'},
        {'start': '', 'end': ''}
    ]
    return samples


@pytest.fixture
def sample_price_response() -> list:
    samples = [
        {
            'accounts': [],
            'clients': [{'createdAt': '1990-07-09T15:33:46+02:00',
                         'plentyId': 1234, 'salesPriceId': 1,
                         'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'countries': [{'countryId': -1,
                           'createdAt': '1990-07-09T15:33:46+02:00',
                           'salesPriceId': 1,
                           'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'createdAt': '1990-09-05 13:24:53',
            'currencies': [{'createdAt': '1990-07-09T15:33:46+02:00',
                            'currency': 'EUR',
                            'salesPriceId': 1,
                            'updatedAt': '1990-07-09T15:33:46+02:00'},
                           {'createdAt': '1990-07-09T15:33:46+02:00',
                            'currency': 'GBP',
                            'salesPriceId': 1,
                            'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'customerClasses': [{'createdAt': '1990-07-09T15:33:46+02:00',
                                 'customerClassId': -1,
                                 'salesPriceId': 1,
                                 'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'id': 1,
            'interval': 'none',
            'isCustomerPrice': False,
            'isDisplayedByDefault': True,
            'isLiveConversion': False,
            'minimumOrderQuantity': 1,
            'names': [{'createdAt': '1990-09-05T13:24:53+02:00',
                       'lang': 'de',
                       'nameExternal': 'Preis',
                       'nameInternal': 'Preis',
                       'salesPriceId': 1,
                       'updatedAt': '1990-09-05T14:46:34+02:00'},
                      {'createdAt': '1990-09-05T13:24:53+02:00',
                       'lang': 'en',
                       'nameExternal': 'Price',
                       'nameInternal': 'Price',
                       'salesPriceId': 1,
                       'updatedAt': '1990-09-05T14:46:34+02:00'}],
            'position': 0,
            'referrers': [{'createdAt': '1990-07-09T15:33:46+02:00',
                           'referrerId': 0,
                           'salesPriceId': 1,
                           'updatedAt': '1990-07-09T15:33:46+02:00'}],
            'type': 'default',
            'updatedAt': '1990-07-09 15:33:46'
        },
        {}
    ]
    return samples


@pytest.fixture
def expected_date_range() -> list:
    expected = [
        {'start': str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
         'end': str(f'2020-09-15T00:00:00+{get_utc_offset()}')},
        {'start': str(f'2020-09-14T00:00:00+{get_utc_offset()}'),
         'end': str(f'2020-09-13T00:00:00+{get_utc_offset()}')},
        {'start': '2020-09-14T08:00:00+00:00',
         'end': '2020-09-14T09:00:00+00:00'},
        {'start': '2020-09-14T08:00:00+02:00',
         'end': '2020-09-14T10:00:30+02:00'},
        None,
        None
    ]
    return expected


@pytest.fixture
def sample_query_data() -> list:
    samples = [
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Creation'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Payment'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Change'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Delivery'},
        {'date_range': {},
         'date_type': 'Creation'},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': ''},
        {'date_range': {'start': '2020-09-14T08:00:00+02:00',
                        'end': '2020-09-14T10:00:30+02:00'},
         'date_type': 'Creation'}
    ]
    return samples


@pytest.fixture
def sample_vat_data() -> list:
    samples = [
        [
            {
                'id': 1,
                'countryId': 1,
                'taxIdNumber': 'DE12345678910',
                'locationId': 1
            },
            {
                'id': 2,
                'countryId': 2,
                'taxIdNumber': 'GB12345678910',
                'locationId': 2
            },
            {
                'id': 3,
                'countryId': 2,
                'taxIdNumber': 'GB12345678910',
                'locationId': 2
            },
            {
                'id': 4,
                'countryId': 3,
                'taxIdNumber': 'FR12345678910',
                'locationId': 3
            },
            {
                'id': 5,
                'countryId': 1,
                'taxIdNumber': 'DE12345678910',
                'locationId': 1
            }
        ],
        [
            ''
        ]
    ]

    return samples


@pytest.fixture
def sample_sanity_check_parameter() -> list:
    samples = [
        {
            'domain': 'manufacturer',
            'query': {},
            'refine': {},
            'additional': [],
            'lang': ''
        },
        {
            'domain': 'variation',
            'query': {},
            'refine': {'id': 1234, 'itemId': 10234},
            'additional': ['properties', 'stock'],
            'lang': 'de'
        },
        {
            'domain': 'item',
            'query': {},
            'refine': {'id': 10234, 'wrong': 'wrong'},
            'additional': ['variations', 'itemImages'],
            'lang': ''
        },
        {
            'domain': 'order',
            'query': {'orderType': 1},
            'refine': {'wrong': 'wrong'},
            'additional': ['wrong', 'addresses', 'documents'],
            'lang': ''
        },
        {
            'domain': 'wrong',
            'query': {'shall': 'not_appear'},
            'refine': {'should': 'be_insignificant'},
            'additional': ['nono'],
            'lang': 'de'
        }
    ]
    return samples


@pytest.fixture
def sample_attributes() -> list:
    samples = [
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '1',
                                'name': 'rot'
                            },
                            {
                                'lang': 'en',
                                'valueId': '1',
                                'name': 'red'
                            }
                        ],
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '2',
                                'name': 'grau'
                            },
                            {
                                'lang': 'en',
                                'valueId': '2',
                                'name': 'grey'
                            }
                        ],
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {
                                'lang': 'de',
                                'valueId': '2',
                                'name': 'gelb'
                            },
                            {
                                'lang': 'en',
                                'valueId': '2',
                                'name': 'yellow'
                            }
                        ],
                    }
                ]
            }
        ]
    ]

    return samples


@pytest.fixture
def sample_variation_data() -> list:
    samples = [
        {
            'id': 1234,
            'number': 'test-variation_1',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 2345,
            'number': 'test-variation_2',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 3456,
            'number': 'test-variation_3',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 1}],
        },
        {
            'id': 4567,
            'number': 'test-variation_4',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 2}],
        },
        {
            'id': 5678,
            'number': 'test-variation_5',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 2}],
        },
        {
            'id': 6789,
            'number': 'test-variation_6',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 4}],
        },
        {
            'id': 7891,
            'number': 'test-variation_7',
            'variationAttributeValues': [{'attributeId': 1, 'valueId': 4}],
        }
    ]
    return samples


# ======== EXPECTED DATA ==========


@pytest.fixture
def expected_date_query() -> list:
    expected = [
        'createdAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&createdAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'paidAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&paidAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'updatedAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&updatedAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        'outgoingItemsBookedAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&outgoingItemsBookedAtTo=2020-09-14T10%3A00%3A30%2B02%3A00',
        '',
        '',
        'createdAtFrom=2020-09-14T08%3A00%3A00%2B02%3A00' +
        '&createdAtTo=2020-09-14T10%3A00%3A30%2B02%3A00'
    ]
    return expected


@pytest.fixture
def expected_query_attributes() -> list:
    expected = [
        '&with%5B%5D=documents',
        '&with%5B%5D=documents&with%5B%5D=comments&orderType=1,4&referrerId=1',
        '&with%5B%5D=shippingPackages&countryId=1',
        '&with%5B%5D=documents'
    ]
    return expected


@pytest.fixture
def expected_prices() -> list:
    expected = [
        {
            'id': 1,
            'type': 'default',
            'position': 0,
            'names': {'de': 'Preis', 'en': 'Price'},
            'referrers': [0],
            'accounts': [],
            'clients': [1234],
            'countries': [-1],
            'currencies': ['EUR', 'GBP'],
            'customerClasses': [-1]
         }, {}
    ]
    return expected


@pytest.fixture
def expected_sanity_check_query() -> list:
    expected = [
        # empty query
        {},
        # domain: variation
        # valid domain, 2 refine, 2 additional, lang all valid arguments
        {'id': 1234, 'itemId': 10234,
         'with': 'properties,stock', 'lang': 'de'},
        # domain: item
        # valid domain 2 refine, 1 additional, 1 invalid refine
        {'id': 10234, 'with': 'variations,itemImages'},
        # domain: order
        # invalid & valid arguments, but preexisting query
        # check if the 'additional' field is handled differently for 'order'
        {'orderType': 1, 'with[]': ['addresses', 'documents']},
        # domain: wrong
        # invalid domain
        {}
    ]
    return expected


@pytest.fixture
def expected_attribute_variation_map() -> list:
    expected = [
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '1', 'name': 'rot'},
                            {'lang': 'en', 'valueId': '1', 'name': 'red'}
                        ],
                        'linked_variations': [
                            1234, 2345, 3456
                        ]
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'grau'},
                            {'lang': 'en', 'valueId': '2', 'name': 'grey'}
                        ],
                        'linked_variations': [
                            4567, 5678
                        ]
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'gelb'},
                            {'lang': 'en', 'valueId': '2', 'name': 'yellow'}
                        ]
                    }
                ]
            }
        ],
        # Missing variation data
        [
            {
                'id': 1,
                'position': 1,
                'values': [
                    {
                        'id': 1,
                        'attributeId': 1,
                        'position': 1,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '1', 'name': 'rot'},
                            {'lang': 'en', 'valueId': '1', 'name': 'red'}
                        ],
                    },
                    {
                        'id': 2,
                        'attributeId': 1,
                        'position': 2,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'grau'},
                            {'lang': 'en', 'valueId': '2', 'name': 'grey'}
                        ],
                    },
                    {
                        'id': 3,
                        'attributeId': 1,
                        'position': 3,
                        'valueNames': [
                            {'lang': 'de', 'valueId': '2', 'name': 'gelb'},
                            {'lang': 'en', 'valueId': '2', 'name': 'yellow'}
                        ],
                    }
                ]
            }
        ],
        # Missing attribute dat
        {}
    ]
    return expected


# ======== UNIT TESTS ==========


def test_get_route() -> None:
    sample_data = ['order', 'item', 'ITEMS', 'oRdErS', 'wrong', '',
                   'manufacturer', 'manfacturer', 'attribute']
    result = []
    expected = ['/rest/orders', '/rest/items', '/rest/items', '/rest/orders',
                '', '', '/rest/items/manufacturers', '',
                '/rest/items/attributes']

    for domain in sample_data:
        result.append(get_route(domain=domain))

    assert expected == result


def test_build_endpoint() -> None:
    sample_data = [
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/orders'},
        {'url': 'https://invalid.com',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': '/rest/invalid'},
        {'url': '',
         'route': '/rest/orders'},
        {'url': 'https://test.plentymarkets-cloud01.com',
         'route': ''}
    ]

    expected = ['https://test.plentymarkets-cloud01.com/rest/orders',
                'https://test.plentymarkets-cloud01.com/rest/orders', '', '',
                '', '']
    result = []

    for sample in sample_data:
        result.append(build_endpoint(url=sample['url'],
                                     route=sample['route']))

    assert expected == result


def test_check_date_range(sample_date_ranges: list) -> None:
    expected = [True, False, True, False]
    result = []

    for sample in sample_date_ranges:
        result.append(check_date_range(date_range=sample))

    assert expected == result


def test_parse_date(sample_input_date: list,
                    expected_date: list) -> None:
    result = []

    for sample in sample_input_date:
        result.append(parse_date(date=sample))

    assert expected_date == result


def test_build_date_range(sample_date_range_input: list,
                          expected_date_range: list) -> None:
    result = []
    for sample in sample_date_range_input:
        result.append(build_date_range(start=sample['start'],
                                       end=sample['end']))

    assert expected_date_range == result


def test_F_date(sample_query_data: list,
                expected_date_query: list) -> None:
    result = []

    for sample in sample_query_data:
        query = build_query_date(date_range=sample['date_range'],
                                 date_type=sample['date_type'])
        req = requests.Request('POST', 'https://httpbin.org/get', params=query)
        prepped = req.prepare()
        result += (prepped.url.split('?')[1:])
        if not prepped.url.split('?')[1:]:
            result.append('')
    assert expected_date_query == result


def test_create_vat_mapping(sample_vat_data: list) -> None:
    subset = [[], [1, 2]]
    expected = [
        {
            '1': {'config': ['1', '5'], 'TaxId': 'DE12345678910'},
            '2': {'config': ['2', '3'], 'TaxId': 'GB12345678910'},
            '3': {'config': ['4'], 'TaxId': 'FR12345678910'}
        },
        {
            '1': {'config': ['1', '5'], 'TaxId': 'DE12345678910'},
            '2': {'config': ['2', '3'], 'TaxId': 'GB12345678910'}
        },
        {},
        {}
    ]
    result = []

    for sample in sample_vat_data:
        for sub in subset:
            result.append(create_vat_mapping(data=sample, subset=sub))

    assert expected == result


def test_date_to_timestamp() -> None:
    samples = ['2020-08-01', '2020-08-01T15:00', '2020-08-01T15:00:00+02:00',
               '01-08-2020', '2020.08.01', 'abc', '']
    expected = [1596232800, 1596286800, 1596290400,
                -1, 1596232800, -1, -1]
    result = []

    for sample in samples:
        result.append(date_to_timestamp(date=sample))

    assert expected == result


def test_get_language() -> None:
    samples = ['de', 'EN', 'fR', 'Greece', '12', '']
    expected = ['de', 'en', 'fr', 'INVALID_LANGUAGE',
                'INVALID_LANGUAGE', 'INVALID_LANGUAGE']
    result = []

    for sample in samples:
        result.append(get_language(lang=sample))

    assert expected == result


def test_shrink_price_configuration(sample_price_response: list,
                                    expected_prices: list) -> None:
    result = []

    for sample in sample_price_response:
        result.append(shrink_price_configuration(data=sample))

    assert expected_prices == result


def test_sanity_check_parameter(sample_sanity_check_parameter: list,
                                expected_sanity_check_query: list) -> None:
    result = []

    for sample in sample_sanity_check_parameter:
        result.append(sanity_check_parameter(domain=sample['domain'],
                                             query=sample['query'],
                                             refine=sample['refine'],
                                             additional=sample['additional'],
                                             lang=sample['lang']))

    assert expected_sanity_check_query == result


def test_attribute_variation_mapping(sample_attributes: list,
                                     sample_variation_data: list,
                                     expected_attribute_variation_map: list):
    result = []

    for sample in sample_attributes:
        first = sample
        second = copy.deepcopy(sample)
        # Test with variations and attribute
        result.append(attribute_variation_mapping(
            variation=sample_variation_data, attribute=first))
        # Test with attributes and without variations
        result.append(attribute_variation_mapping(
            variation=None, attribute=second))

    # Test without attributes and without variations
    result.append(attribute_variation_mapping(variation=None, attribute=None))

    assert expected_attribute_variation_map == result
