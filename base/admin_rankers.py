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

"""Handle administrative tasks for rankers (i.e. median trees)."""

__author__ = 'slamm@google.com (Stephen Lamm)'

import logging
import urllib

from google.appengine.runtime import DeadlineExceededError
from google.appengine.api import datastore
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

import settings
from base import manage_dirty
from base import util
from categories import all_test_sets
from categories import test_set_params
from models import result_ranker
from models.result import ResultParent
from models.user_agent import UserAgent

from third_party.gaefy.db import pager

import django
from django import http
from django.utils import simplejson


def AllRankers(request):
  pass

def AllUserAgents(request):
  pass


def Render(request, template_file, params):
  """Render network test pages."""

  return util.Render(request, template_file, params)


class PagerQuery(pager.PagerQuery):
  def GetBookmark(self, entity):
    """Return a bookmark for the given entity.

    The returned bookmark causes a PagerQuery to start after the given
    entity--it is not included.
    """
    return pager.encode_bookmark(self._get_bookmark_values(entity))


class ResultParentQuery(object):
  def __init__(self, category, fetch_limit, bookmark):
    self.bookmark = bookmark
    self.query = PagerQuery(ResultParent, keys_only=True)
    self.query.filter('category =', category)
    self.query.order('user_agent_pretty')
    prev_bookmark, self.results, self.next_bookmark = self.query.fetch(
        fetch_limit, bookmark)
    self.num_results = len(self.results)
    self.index = 0

  def HasNext(self):
    return self.index < self.num_results

  def GetNext(self):
    if self.HasNext():
      result_parent_key = self.results[self.index]
      self.index += 1
      return ResultParent.get(result_parent_key)
    else:
      return None

  def PushBack(self):
    self.index -= 1
    assert self.index >= 0

  def GetBookmark(self):
    if self.index == 0:
      return self.bookmark
    elif not self.HasNext():
      return self.next_bookmark
    else:
      return self.query.GetBookmark(self.results[self.index - 1])

  def GetCountUsed(self):
    return self.index


class ResultTimeQuery(object):
  def __init__(self):
    self.query = db.GqlQuery(
        "SELECT * FROM ResultTime WHERE ANCESTOR IS :1 AND dirty = False")

  def fetch(self, fetch_limit, result_parent):
    self.query.bind(result_parent)
    return self.query.fetch(fetch_limit)


def _AddRankerScores(ranker_scores, user_agent_list, params_str, result_times):
  """Modify ranker_scores to have all result_times added for each user agent."""
  for user_agent_version in user_agent_list:
    for result_time in result_times:
      ranker_key = result_time.test, user_agent_version, params_str
      ranker_scores.setdefault(ranker_key, []).append(result_time.score)


def _CollectScores(result_parent_query, ranker_limit, num_tests):
  """Collect the scores for each result parent.

  Stop when all the result_parents are processed or when the
  the next result_parent would go over the ranker limit.

  Args:
    result_parent_query: a ResultParentQuery instance
    ranker_limit: the number of rankers that may be updated.
    num_tests: the number of tests each result parent has.
  Returns:
    {user_agent_version: [score_1, score_2, ...], ...}
  """
  ranker_scores = {}
  user_agent_versions = {}
  result_time_query = ResultTimeQuery()
  while result_parent_query.HasNext():
    result_parent = result_parent_query.GetNext()
    logging.info('_CollectScores: %s', result_parent.user_agent_pretty)
    user_agent_pretty = result_parent.user_agent_pretty
    if user_agent_pretty not in user_agent_versions:
      user_agent_list = UserAgent.parse_to_string_list(user_agent_pretty)
      user_agent_versions[user_agent_pretty] = user_agent_list
      if len(ranker_scores) + num_tests * len(user_agent_list) > ranker_limit:
        result_parent_query.PushBack()  # Save this result_parent for later
        break
    else:
      user_agent_list = user_agent_versions[user_agent_pretty]

    result_times = result_time_query.fetch(MAX_TESTS, result_parent)
    _AddRankerScores(
        ranker_scores, user_agent_list, result_parent.params_str, result_times)
  return ranker_scores


def _UpdateRankers(ranker_scores, test_set, bookmark):
  """Add items in ranker_scores to their respective rankers.

  Args:
    ranker_scores:
    test_set:
    bookmark:
  """
  category = test_set.category
  logging.debug('_UpdateRankers: ranker_scores=%s', ranker_scores)
  for ranker_key, scores in ranker_scores.iteritems():
    test_key, user_agent_version, params_str = ranker_key
    try:
      test = test_set.GetTest(test_key)
    except KeyError:
      # 'test' is needed so GetOrCreate can have test.key, test.min_value,
      # and test.max_value
      logging.warn('RebuildRankers: test not found: %s', test_key)
      continue
    ranker = result_ranker.ResultRanker.GetOrCreate(
        category, test, user_agent_version, params_str, ranker_version='next')
    if not bookmark and ranker.TotalRankedScores():
      logging.warn('RebuildRankers: reset ranker: %s', ', '.join(map(str, [
          category, test_key, user_agent_version, params_str,
          'ranker_version="next"'])))
      ranker.Reset()
    ranker.Update(scores)


MAX_TESTS = 100
def RebuildRankers(request):
  """Rebuild rankers."""
  bookmark = request.GET.get('bookmark')
  logging.info('bookmark in: %s', (bookmark == 'None' and '"None"' or bookmark))
  if bookmark == 'None':
    bookmark = None
  category_index = int(request.GET.get('category_index', 0))
  total_results = int(request.GET.get('total_results', 0))
  fetch_limit = int(request.GET.get('fetch_limit', 100))

  # Rankers per result_parent <= num_tests_per_category * user_agents_versions
  #            reflow rankers <= 13 * 4 <= 52
  #           network rankers <= 12 * 4 <= 48
  ranker_limit = int(request.GET.get('ranker_limit', 80))

  try:
    if not manage_dirty.UpdateDirtyController.IsPaused():
      manage_dirty.UpdateDirtyController.SetPaused(True)

    category = settings.CATEGORIES[category_index]
    result_parent_query = ResultParentQuery(category, fetch_limit, bookmark)
    test_set = all_test_sets.GetTestSet(category)
    num_tests = len(test_set.tests)
    ranker_scores = _CollectScores(result_parent_query, ranker_limit, num_tests)
    _UpdateRankers(ranker_scores, test_set, bookmark)

    is_done = False
    bookmark = result_parent_query.GetBookmark()
    if not bookmark:
      category_index += 1
      is_done = category_index >= len(settings.CATEGORIES)
    logging.info('bookmark out: %s', (bookmark == 'None' and '"None"' or bookmark))
    return http.HttpResponse(simplejson.dumps({
        'is_done': is_done,
        'bookmark': bookmark,
        'category_index': category_index,
        'fetch_limit': fetch_limit,
        'rankers_updated': len(ranker_scores),
        'total_results': total_results + result_parent_query.GetCountUsed(),
        }))
  except DeadlineExceededError:
    logging.warn('DeadlineExceededError in RebuildRankers:'
                 ' bookmark=%s, category=%s, test=%s, user_agent_pretty=%s,'
                 ' total_scores=%s',
                 bookmark, category, test.key, user_agent_pretty,
                 total_results)
    return http.HttpResponse('RebuildRankers: DeadlineExceededError.',
                             status=403)


def _MapNextRankers(request, parent_func):
  total = int(request.GET.get('total', 0))
  fetch_limit = int(request.GET.get('fetch_limit', 50))
  query = result_ranker.ResultRankerParent.all()
  query.filter('ranker_version =', 'next')
  ranker_parents = query.fetch(fetch_limit)
  for parent in ranker_parents:
    parent_func(parent)
  num_mapped = len(ranker_parents)
  total += num_mapped
  is_done = num_mapped < fetch_limit
  if is_done:
    manage_dirty.UpdateDirtyController.SetPaused(False)
    datastore.Put(datastore.Entity('ranker migration', name='complete'))
  return http.HttpResponse(simplejson.dumps({
      'fetch_limit': fetch_limit,
      'is_done': is_done,
      'total': total
      }))


def ReleaseNextRankers(request):
  def _ReleaseParent(parent):
    parent.Release()
  _MapNextRankers(request, _ReleaseParent)


def ResetNextRankers(request):
  def _ResetParent(parent):
    ranker = result_ranker.ResultRanker(parent)
    ranker.Reset()
  _MapNextRankers(request, _ResetParent)


def UpdateResultParents(request):
  bookmark = request.GET.get('bookmark', None)
  total_scanned = int(request.GET.get('total_scanned', 0))
  total_updated = int(request.GET.get('total_updated', 0))
  use_taskqueue = request.GET.get('use_taskqueue', '') == '1'

  query = pager.PagerQuery(ResultParent)
  try:
    prev_bookmark, results, next_bookmark = query.fetch(100, bookmark)
    total_scanned += len(results)
    changed_results = []
    for result in results:
      if hasattr(result, 'user_agent_list') and result.user_agent_list:
        result.user_agent_pretty = result.user_agent_list[-1]
        result.user_agent_list = []
        changed_results.append(result)
      if hasattr(result, 'params') and result.params:
        result.params_str = str(test_set_params.Params(
            [urllib.unquote(x) for x in result.params]))
        result.params = []
        changed_results.append(result)
    if changed_results:
      db.put(changed_results)
      total_updated += len(changed_results)
  except DeadlineExceededError:
    logging.warn('DeadlineExceededError in UpdateResultParents:'
                 ' total_scanned=%s, total_updated=%s.',
                 total_scanned, total_updated)
    return http.HttpResponse('UpdateResultParent: DeadlineExceededError.',
                             status=403)
  if use_taskqueue:
    if next_bookmark:
      taskqueue.Task(
          method='GET',
          url='/admin/update_result_parents',
          params={
              'bookmark': next_bookmark,
              'total_scanned': total_scanned,
              'total_updated': total_updated,
              'use_taskqueue': 1,
              }).add(queue_name='default')
    else:
      logging.info('Finished UpdateResultParents tasks:'
                   ' total_scanned=%s, total_updated=%s',
                   total_scanned, total_updated)
      return http.HttpResponse('UpdateResultParent: Done.')
  return http.HttpResponse(simplejson.dumps({
      'is_done': next_bookmark is None,
      'bookmark': next_bookmark,
      'total_scanned': total_scanned,
      'total_updated': total_updated,
      }))
