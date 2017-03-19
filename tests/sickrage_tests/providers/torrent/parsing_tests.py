# coding=utf-8
# This file is part of SickRage.
#
# URL: https://SickRage.GitHub.io
# Git: https://github.com/SickRage/SickRage.git
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage. If not, see <http://www.gnu.org/licenses/>.
# pylint: disable=fixme
"""
Test Provider Result Parsing
When recording new cassettes:
    Set overwrite_cassettes = True on line 43
    Delete the cassette yml file with the same base filename as this file in the cassettes dir next to this file
    Be sure to adjust the self.search_strings so they return results. They must be identical to search strings generated by SickRage
"""

from __future__ import print_function, unicode_literals
from functools import wraps

import re
import sys

import unittest
from vcr_unittest import VCRTestCase

# Have to do this before importing sickbeard
sys.path.insert(1, 'lib')

import sickbeard
sickbeard.CPU_PRESET = 'NORMAL'

import validators

import six


overwrite_cassettes = False

disabled_provider_tests = {
    # ???
    'Cpasbien': ['test_rss_search', 'test_episode_search', 'test_season_search'],
# ???
    'Torrent9': ['test_rss_search', 'test_episode_search', 'test_season_search'],
    # api_maintenance still
    'TorrentProject': ['test_rss_search', 'test_episode_search', 'test_season_search'],
    # Have to trick it into thinking is an anime search, and add string overrides
    'TokyoToshokan': ['test_rss_search', 'test_episode_search', 'test_season_search'],
    # 'Torrrentz': ['test_rss_search', 'test_episode_search', 'test_season_search'],

}
test_string_overrides = {
    'Cpasbien': {'Episode': ['The 100 S02E16'], 'Season': ['The 100 S02']},
    'Torrent9': {'Episode': ['NCIS S14E09'], 'Season': ['NCIS S14']},
    'NyaaTorrents': {'Episode': ['Fairy Tail S2'], 'Season': ['Fairy Tail S2']},
    'TokyoToshokan': {'Episode': ['Fairy Tail S2'], 'Season': ['Fairy Tail S2']},
    'HorribleSubs': {'Episode': ['Fairy Tail S2'], 'Season': ['Fairy Tail S2']},
}

magnet_regex = re.compile(r'magnet:\?xt=urn:btih:\w{32,40}(:?&dn=[\w. %+-]+)*(:?&tr=(:?tcp|https?|udp)[\w%. +-]+)*')


class BaseParser(type):

    class TestCase(VCRTestCase):
        provider = None

        def __init__(self, test):
            """Initialize the test suite"""
            VCRTestCase.__init__(self, test)

            self.provider.session.verify = False

            self.provider.username = self.username
            self.provider.password = self.password

        @property
        def username(self):  # pylint: disable=no-self-use
            # TODO: Make this read usernames from somewhere
            return ''

        @property
        def password(self):  # pylint: disable=no-self-use
            # TODO: Make this read passwords from somewhere
            return ''

        def search_strings(self, mode):
            _search_strings = {
                'RSS': [''],
                'Episode': ['Game of Thrones S05E08'],
                'Season': ['Game of Thrones S05']
            }
            _search_strings.update(self.provider.cache.search_params)
            _search_strings.update(test_string_overrides.get(self.provider.name, {}))
            return {mode: _search_strings[mode]}

        def magic_skip(func):  # pylint:disable=no-self-argument
            @wraps(func)
            def magic(self, *args, **kwargs):
                # pylint:disable=no-member
                if func.func_name in disabled_provider_tests.get(self.provider.name, []):
                    print("skipped")
                    return unittest.skip(str(self.provider.name))
                func(self, *args, **kwargs)
            return magic

        def _get_vcr_kwargs(self):
            """Don't allow the suite to write to cassettes unless we say so"""
            if overwrite_cassettes:
                return {'record_mode': 'new_episodes'}
            return {'record_mode': 'once'}

        def _get_cassette_name(self):
            """Returns the filename to use for the cassette"""
            return self.provider.get_id() + '.yaml'

        def shortDescription(self):
            if self._testMethodDoc:
                return self._testMethodDoc.replace('the provider', self.provider.name)
            return None

        @magic_skip
        def test_rss_search(self):
            """Check that the provider parses rss search results"""
            results = self.provider.search(self.search_strings('RSS'))

            if self.provider.enable_daily:
                self.assertTrue(self.cassette.requests)
                self.assertTrue(results, self.cassette.requests[-1].url)
                self.assertTrue(len(self.cassette))

        @magic_skip
        def test_episode_search(self):
            """Check that the provider parses episode search results"""
            results = self.provider.search(self.search_strings('Episode'))

            self.assertTrue(self.cassette.requests)
            self.assertTrue(results, results)
            self.assertTrue(results, self.cassette.requests[-1].url)
            self.assertTrue(len(self.cassette))

        @magic_skip
        def test_season_search(self):
            """Check that the provider parses season search results"""
            results = self.provider.search(self.search_strings('Season'))

            self.assertTrue(self.cassette.requests)
            self.assertTrue(results, self.cassette.requests[-1].url)
            self.assertTrue(len(self.cassette))

        @magic_skip
        def test_cache_update(self):
            """Check that the provider's cache parses rss search results"""
            self.provider.cache.updateCache()

        def test_result_values(self):
            """Check that the provider returns results in proper format"""
            results = self.provider.search(self.search_strings('Episode'))
            for result in results:
                self.assertIsInstance(result, dict)
                self.assertEqual(sorted(result.keys()), ['hash', 'leechers', 'link', 'seeders', 'size', 'title'])

                self.assertIsInstance(result[b'title'], six.text_type)
                self.assertIsInstance(result[b'link'], six.text_type)
                self.assertIsInstance(result[b'hash'], six.string_types)
                self.assertIsInstance(result[b'seeders'], six.integer_types)
                self.assertIsInstance(result[b'leechers'], six.integer_types)
                self.assertIsInstance(result[b'size'], six.integer_types)

                self.assertTrue(len(result[b'title']))
                self.assertTrue(len(result[b'link']))
                self.assertTrue(len(result[b'hash']) in (0, 32, 40))
                self.assertTrue(result[b'seeders'] >= 0)
                self.assertTrue(result[b'leechers'] >= 0)

                self.assertTrue(result[b'size'] >= -1)

                if result[b'link'].startswith('magnet'):
                    self.assertTrue(magnet_regex.match(result[b'link']))
                else:
                    self.assertTrue(validators.url(result[b'link'], require_tld=False))

                self.assertIsInstance(self.provider._get_size(result), six.integer_types)  # pylint: disable=protected-access
                self.assertTrue(all(self.provider._get_title_and_url(result)))  # pylint: disable=protected-access
                self.assertTrue(self.provider._get_size(result))  # pylint: disable=protected-access

            @unittest.skip('Not yet implemented')
            def test_season_search_strings_format(self):  # pylint: disable=no-self-use, unused-argument, unused-variable
                """Check format of the provider's season search strings"""
                pass

            @unittest.skip('Not yet implemented')
            def test_episode_search_strings_format(self):  # pylint: disable=no-self-use, unused-argument, unused-variable
                """Check format of the provider's season search strings"""
                pass


def generate_test_cases():
    """
    Auto Generate TestCases from providers and add them to globals()
    """
    for p in sickbeard.providers.__all__:
        provider = sickbeard.providers.getProviderModule(p).provider
        if provider.supports_backlog and provider.provider_type == 'torrent' and provider.public:
            generated_class = type(str(provider.name), (BaseParser.TestCase,), {'provider': provider})
            globals()[generated_class.__name__] = generated_class
            del generated_class

generate_test_cases()

if __name__ == '__main__':
    import inspect
    print('=====> Testing %s', __file__)

    def override_log(msg, *args, **kwargs):
        """Override the SickRage logger so we can see the debug output from providers"""
        _ = args, kwargs
        print(msg)

    sickbeard.logger.log = override_log

    suite = unittest.TestSuite()
    members = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    for _, provider_test_class in members:
        if provider_test_class not in (BaseParser, BaseParser.TestCase):
            suite.addTest(unittest.TestLoader().loadTestsFromTestCase(provider_test_class))

    unittest.TextTestRunner(verbosity=3).run(suite)
