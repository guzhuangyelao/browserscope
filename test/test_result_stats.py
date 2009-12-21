#!/usr/bin/python2.5
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License')
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test Result Stats."""

__author__ = 'slamm@google.com (Stephen Lamm)'

import logging
import random
import unittest

from google.appengine.api import memcache
from google.appengine.ext import db
from models import result_stats
from models.result import ResultParent

import mock_data


class CategoryBrowserManagerTest(unittest.TestCase):

  def setUp(self):
    db.delete(result_stats.CategoryBrowserManager.all(keys_only=True).fetch(1000))
    memcache.flush_all()

  def tearDown(self):
    db.delete(result_stats.CategoryBrowserManager.all(keys_only=True).fetch(1000))
    memcache.flush_all()

  def testEmpty(self):
    category = 'network'
    version_level = 1
    browsers = result_stats.CategoryBrowserManager.GetBrowsers(
        category, version_level)
    self.assertEqual([], browsers)

  def testAddUserAgentBasic(self):
    category = 'network'
    result_stats.CategoryBrowserManager.AddUserAgent(
        category, mock_data.GetUserAgent('Firefox 3.5'))
    result_stats.CategoryBrowserManager.AddUserAgent(
        category, mock_data.GetUserAgent('Firefox 3.0.7'))
    for version_level, expected_browsers in enumerate((
        ['Firefox'],
        ['Firefox 3'],
        ['Firefox 3.0', 'Firefox 3.5'],
        ['Firefox 3.0.7', 'Firefox 3.5'])):
      browsers = result_stats.CategoryBrowserManager.GetBrowsers(
        category, version_level)
      self.assertEqual(expected_browsers, browsers)

  def testGetBrowsersTop(self):
    expected_browsers = result_stats.TOP_BROWSERS
    browsers = result_stats.CategoryBrowserManager.GetBrowsers(
        category='foo', version_level='top')
    self.assertEqual(expected_browsers, browsers)

  def testGetBrowsersDbAndMemcacheUse(self):
    category = 'network'
    version_level = 3
    cls = result_stats.CategoryBrowserManager
    cls.AddUserAgent(category, mock_data.GetUserAgent('Firefox 3.5'))
    self.assertEqual(['Firefox 3.5'], cls.GetBrowsers(category, version_level))

    # Load browsers from db into memcache and return.
    memcache.flush_all()
    self.assertEqual(['Firefox 3.5'], cls.GetBrowsers(category, version_level))

    # Load browsers memcache (db is not changed).
    cls.get_by_key_name(cls.KeyName(category, version_level)).delete()
    self.assertEqual(['Firefox 3.5'], cls.GetBrowsers(category, version_level))

    # db and memcache are cleared.
    memcache.flush_all()
    self.assertEqual([], cls.GetBrowsers(category, version_level))

  def testSetBrowsers(self):
    category = 'basil'
    version_level = 1
    expected_browsers = ['Firefox 3.0', 'IE 8', 'Safari 5.8.2']
    result_stats.CategoryBrowserManager.SetBrowsers(
        category, version_level, expected_browsers)
    browsers = result_stats.CategoryBrowserManager.GetBrowsers(
        category, version_level)
    self.assertEqual(expected_browsers, browsers)

  def testSetBrowsersDbAndMemcacheUse(self):
    category = 'basil'
    version_level = 1
    expected_browsers = ['Firefox 3.0', 'IE 8', 'Safari 5.8.2']
    result_stats.CategoryBrowserManager.SetBrowsers(
        category, version_level, expected_browsers)
    browsers = result_stats.CategoryBrowserManager.GetBrowsers(
        category, version_level)
    self.assertEqual(expected_browsers, browsers)

  def testSortBrowsers(self):
    cls = result_stats.CategoryBrowserManager
    expected_browsers = [
        'Firefox',
        'Firefox 3',
        'Firefox 3.0a3pre',
        'Firefox 3.0b5',
        'Firefox 3.0pre',
        'Firefox 3.0',
        'Firefox 3.0.1',
        'Firefox 3.4',
        'Firefox 3.4.1',
        'Firefox 3.5a1pre',
        'Firefox 3.5a4',
        'Firefox 3.5',
        'Firefox 3.5.1a3',
        'Firefox 3.5.1',
        'Firefox 3.5.2',
        'iPhone 1.1',
        'Safari 5.0',
        ]
    browsers = expected_browsers[:]
    random.seed(5)
    random.shuffle(browsers)
    cls.SortBrowsers(browsers)
    self.assertEqual(expected_browsers, browsers)

  def testInsortBrowser(self):
    cls = result_stats.CategoryBrowserManager
    browsers = ['Firefox 3.0', 'Firefox 3.5', 'Safari 5.0']
    cls.InsortBrowser(browsers, 'iPhone 1.1')
    self.assertEqual(['Firefox 3.0', 'Firefox 3.5', 'iPhone 1.1', 'Safari 5.0'],
                     browsers)


class CategoryBrowserManagerFilterTest(unittest.TestCase):

  def setUp(self):
    self.cls = result_stats.CategoryBrowserManager
    self.category = 'network'
    db.delete(self.cls.all(keys_only=True).fetch(1000))
    result_stats.CategoryBrowserManager.AddUserAgent(
        self.category, mock_data.GetUserAgent('Firefox 2.5.1'))
    result_stats.CategoryBrowserManager.AddUserAgent(
        self.category, mock_data.GetUserAgent('Firefox 3.1.8'))
    result_stats.CategoryBrowserManager.AddUserAgent(
        self.category, mock_data.GetUserAgent('Firefox 3.0.7'))
    result_stats.CategoryBrowserManager.AddUserAgent(
        self.category, mock_data.GetUserAgent('Firefox 3.1.7'))
    result_stats.CategoryBrowserManager.AddUserAgent(
        self.category, mock_data.GetUserAgent('IE 7.0'))
    memcache.flush_all()

  def tearDown(self):
    db.delete(self.cls.all(keys_only=True).fetch(1000))
    memcache.flush_all()

  def testGetFilteredBrowsersFamily(self):
    expected_browsers = [
        'Firefox 2.5.1', 'Firefox 3.0.7', 'Firefox 3.1.7', 'Firefox 3.1.8']
    browsers = self.cls.GetFilteredBrowsers(self.category, 'Firefox')
    self.assertEqual(expected_browsers, browsers)

  def testGetFilteredBrowsersMajorVersion(self):
    expected_browsers = ['Firefox 3.0.7', 'Firefox 3.1.7', 'Firefox 3.1.8']
    browsers = self.cls.GetFilteredBrowsers(self.category, 'Firefox 3')
    self.assertEqual(expected_browsers, browsers)

  def testGetFilteredBrowsersMinorVersion(self):
    expected_browsers = ['Firefox 3.1.7', 'Firefox 3.1.8']
    browsers = self.cls.GetFilteredBrowsers(self.category, 'Firefox 3.1')
    self.assertEqual(expected_browsers, browsers)


class CategoryStatsManagerTest(unittest.TestCase):

  MANAGER_QUERY = result_stats.CategoryBrowserManager.all(keys_only=True)

  def setUp(self):
    db.delete(self.MANAGER_QUERY.fetch(1000))

  def tearDown(self):
    db.delete(self.MANAGER_QUERY.fetch(1000))

  def testGetStats(self):
    test_set = mock_data.MockTestSet()
    add_result_params = (
        # ((apple, banana, coconut), firefox_version)
        ((0, 0, 500), 'Firefox 3.0.7'),
        ((1, 1, 200), 'Firefox 3.0.7'),
        ((0, 2, 300), 'Firefox 3.0.7'),
        ((1, 3, 100), 'Firefox 3.5'),
        ((0, 4, 400), 'Firefox 3.5')
        )
    for scores, browser in add_result_params:
      parent = ResultParent.AddResult(
          test_set, '12.2.2.25', mock_data.GetUserAgentString(browser),
          'apple=%s,banana=%s,coconut=%s' % scores)
    level_1_stats = {
        'Firefox 3': {
            'summary_score': 605,
            'summary_display': '302',
            'total_runs': 5,
            'results': {
                'coconut': {'score': 600, 'raw_score': 300, 'display': 'd:600'},
                'apple': {'score': 1, 'raw_score': 0, 'display': 'no'},
                'banana': {'score': 4, 'raw_score': 2, 'display': 'd:4'}
                }
            }
        }
    self.assertEqual(level_1_stats, result_stats.CategoryStatsManager.GetStats(
        test_set, browsers=('Firefox 3',)))

    level_3_stats = {
        'Firefox 3.0.7': {
            'summary_score': 603,
            'summary_display': '301',
            'total_runs': 3,
            'results': {
                'coconut': {'score': 600, 'raw_score': 300, 'display': 'd:600'},
                'apple': {'score': 1, 'raw_score': 0, 'display': 'no'},
                'banana': {'score': 2, 'raw_score': 1, 'display': 'd:2'}
                }
            },
        'Firefox 3.5': {
            'summary_score': 818,
            'summary_display': '405',
            'total_runs': 2,
            'results': {
                'coconut': {'score': 800, 'raw_score': 400, 'display': 'd:800'},
                'apple': {'score': 10, 'raw_score': 1, 'display': 'yes'},
                'banana': {'score': 8, 'raw_score': 4, 'display': 'd:8'}
                }
            },
        }
    self.assertEqual(level_3_stats, result_stats.CategoryStatsManager.GetStats(
        test_set, browsers=('Firefox 3.0.7', 'Firefox 3.5')))
