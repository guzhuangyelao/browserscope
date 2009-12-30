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

"""Shared models."""

import logging
import sys

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue

from categories import all_test_sets
from models.user_agent import UserAgent

BROWSER_NAV = (
  # version_level, label
  ('top', 'Top Browsers'),
  ('0', 'Browser Families'),
  ('1', 'Major Versions'),
  ('2', 'Minor Versions'),
  ('3', 'All Versions')
)

TOP_BROWSERS = (
  'Chrome 3', 'Chrome 4',
  'Firefox 3.0', 'Firefox 3.5',
  'IE 6', 'IE 7', 'IE 8',
  'iPhone 2.2', 'iPhone 3.1',
  'Opera 9.64', 'Opera 10',
  'Safari 3.2', 'Safari 4.0'
)


class CategoryBrowserManager(db.Model):
  """Track the browsers that belong in each category/version level."""

  MEMCACHE_NAMESPACE = 'category_level_browsers'

  browsers = db.StringListProperty(default=[], indexed=False)

  @classmethod
  def AddUserAgent(cls, category, user_agent):
    """Adds a user agent's browser strings to version-level groups.

    AddUserAgent assumes that it does not receive overlapping calls.
    - It should only get called by the update-user-groups task queue.

    Adds a browser for every version level.
    If a level does not have a string, then use the one from the previous level.
    For example, "Safari 4.3" would increment the following:
        level  browser
            0  Safari
            1  Safari 4
            2  Safari 4.3
            3  Safari 4.3
    Args:
      category: a category string like 'network' or 'reflow'.
      user_agent: a UserAgent instance.
    """
    key_names = [cls.KeyName(category, version_level)
                 for version_level in range(4)]
    level_browsers = memcache.get_multi(key_names,
                                        namespace=cls.MEMCACHE_NAMESPACE)

    browser_key_names = []
    ua_browsers = user_agent.get_string_list()
    max_ua_browsers_index = len(ua_browsers) - 1
    for version_level, key_name in enumerate(key_names):
      browser = ua_browsers[min(max_ua_browsers_index, version_level)]
      if browser not in level_browsers.get(key_name, []):
        browser_key_names.append((browser, key_name))
    managers = cls.get_by_key_name([x[1] for x in browser_key_names])

    updated_managers = []
    memcache_mapping = {}
    for (browser, key_name), manager in zip(browser_key_names, managers):
      if manager is None:
        manager = cls.get_or_insert(key_name)
      if browser not in manager.browsers:
        cls.InsortBrowser(manager.browsers, browser)
        updated_managers.append(manager)
        memcache_mapping[key_name] = manager.browsers
    if updated_managers:
      db.put(updated_managers)
      memcache.set_multi(memcache_mapping, namespace=cls.MEMCACHE_NAMESPACE)

  @classmethod
  def GetBrowsers(cls, category, version_level):
    """Get all the browsers for a version level.

    Args:
      category: a category string like 'network' or 'reflow'.
      version_level: 'top', 0 (family), 1 (major), 2 (minor), 3 (3rd)
    Returns:
      ('Firefox 3.1', 'Safari 4.0', 'Safari 4.5', ...)
    """
    if version_level == 'top':
      browsers = TOP_BROWSERS
    else:
      key_name = cls.KeyName(category, version_level)
      browsers = memcache.get(key_name, namespace=cls.MEMCACHE_NAMESPACE)
      if browsers is None:
        manager = cls.get_by_key_name(key_name)
        browsers = manager and manager.browsers or []
        memcache.set(key_name, browsers, namespace=cls.MEMCACHE_NAMESPACE)
    return browsers

  @classmethod
  def GetAllBrowsers(cls, category):
    """Get all the browsers for a category.

    Args:
      category: a category string like 'network' or 'reflow'.
    Returns:
      ('Firefox', 'Firefox 3', 'Firefox 3.1', 'Safari', 'Safari 4', ...)
      # Order is undefined
    """
    all_browsers = set()
    for version_level in range(4):
      all_browsers.update(cls.GetBrowsers(category, version_level))
    return list(all_browsers)

  @classmethod
  def GetFilteredBrowsers(cls, category, filter):
    """Get browsers based on a filter (prefixes for now).

    Args:
      category: a category string like 'network' or 'reflow'.
      filter: a string such as 'Firefox', 'Opera 9'
    Returns:
      ('Firefox 3.1', 'Safari 4.0', 'Safari 4.5', ...)
    """
    filtered_browsers = [
        browser for browser in cls.GetBrowsers(category, version_level=3)
        if (browser.startswith(filter) and
            (filter != 'Opera' or not browser.startswith('Opera Mini')))]
    return filtered_browsers

  @classmethod
  def SetBrowsers(cls, category, version_level, browsers):
    cls.SortBrowsers(browsers)
    key_name = cls.KeyName(category, version_level)
    memcache.set(key_name, browsers, namespace=cls.MEMCACHE_NAMESPACE)
    manager = cls.get_or_insert(key_name)
    manager.browsers = browsers
    manager.put()


  @classmethod
  def SortBrowsers(cls, browsers):
    """Sort browser strings in-place.

    Args:
      browsers: a list of strings
          e.g. ['iPhone 3.1', 'Firefox 3.01', 'Safari 4.1']
    """
    browsers.sort(key=cls.BrowserKey)

  @classmethod
  def InsortBrowser(cls, browsers, browser):
    """Insert a browser, in-place, into a sorted list of browsers.

    Args:
      browsers: a list of strings (e.g. ['iPhone 3.1', 'Safari 4.1'])
      browser: a list of strings
    """
    browser_key = cls.BrowserKey(browser)
    low, high = 0, len(browsers)
    while low < high:
      mid = (low + high) / 2
      if browser_key < cls.BrowserKey(browsers[mid]):
        high = mid
      else:
        low = mid + 1
    browsers.insert(low, browser)

  @classmethod
  def BrowserKey(cls, browser):
    VERSION_DIGITS = 8
    MAX_VERSION = 99999999
    family, v1, v2, v3 = UserAgent.parse_pretty(browser.lower())
    return (family.lower(),
            cls._BrowserKeyPart(v1),
            cls._BrowserKeyPart(v2),
            cls._BrowserKeyPart(v3))

  @classmethod
  def _BrowserKeyPart(cls, v):
    if v is None:
      return ''
    elif v.isdigit():
      digits = int(v or 0) + 1
      nondigits = ' ' * 8
    else:
      nondigit_index = 0
      while v[nondigit_index].isdigit():
        nondigit_index += 1
      digits, nondigits = int(v[:nondigit_index]), v[nondigit_index:]
    return '%.08d %-8s' % (digits, nondigits)


  @classmethod
  def KeyName(cls, category, version_level):
    return '%s_%s' % (category, version_level)

  @classmethod
  def DeleteMemcacheValue(cls, category, version_level):
    key_name = cls.KeyName(category, version_level)
    memcache.delete(key_name, namespace=cls.MEMCACHE_NAMESPACE)


class CategoryStatsManager(object):
  """Manage statistics for a category."""

  MEMCACHE_NAMESPACE_PREFIX = 'category_stats'

  @classmethod
  def GetStats(cls, test_set, browsers, use_memcache=True):
    """Get stats table for a given test_set.

    Args:
      test_set: a TestSet instance
      browsers: a list of browsers to use instead of version level
      use_memcache: whether to use memcache or not
    Returns:
      {
          browser: {
              'summary_score': summary_score,
              'summary_display': summary_display,
              'total_runs': total_runs,
              'results': {
                  test_key_1: {
                      'raw_score': raw_score_1,
                      'score': score_1,
                      'display': display_1,
                      'expando': expando_1
                      },
                  test_key_2: {...},
                  },
              },
          ...
      }
    """
    category = test_set.category
    if use_memcache:
      memcache_params = cls.MemcacheParams(category)
      stats = memcache.get_multi(browsers, **memcache_params)
    for browser in browsers:
      if browser not in stats:
        medians, num_scores = test_set.GetMediansAndNumScores(browser)
        stats[browser] = test_set.GetStats(medians, num_scores)
    if use_memcache:
      memcache.set_multi(stats, **memcache_params)
    return stats

  @classmethod
  def UpdateStatsCache(cls, category, browsers):
    logging.info('UpdateStatsCache: category=%s, browsers=%s', category, browsers)
    test_set = all_test_sets.GetTestSet(category)
    ua_stats = {}
    for browser in browsers:
      medians, num_scores = test_set.GetMediansAndNumScores(browser)
      ua_stats[browser] = test_set.GetStats(medians, num_scores)
    memcache.set_multi(ua_stats, **cls.MemcacheParams(category))

  @classmethod
  def MemcacheParams(cls, category):
    return {
        'namespace': '_'.join((cls.MEMCACHE_NAMESPACE_PREFIX, category))
        }

  @classmethod
  def DeleteMemcacheValues(cls, category, browsers):
    memcache.delete_multi(browsers, **cls.MemcacheParams(category))


def UpdateCategory(category, user_agent):
  logging.info('result.stats.UpdateCategory')
  CategoryBrowserManager.AddUserAgent(category, user_agent)
  CategoryStatsManager.UpdateStatsCache(category, user_agent.get_string_list())


def ScheduleCategoryUpdate(category, user_agent):
  """Add a task to update a category's statistic.

  The task is handled by base.cron.UserAgentGroup().
  That method calls UpdateCategory().
  """
  task = taskqueue.Task(method='GET', params={
      'category': category,
      'user_agent_key': user_agent.key(),
      })
  try:
    task.add(queue_name='user-agent-group')
  except:
    logging.info('Cannot add task: %s:%s' % (sys.exc_type, sys.exc_value))
