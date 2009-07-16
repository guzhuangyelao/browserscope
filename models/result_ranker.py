#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License')
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__author__ = 'slamm@google.com (Stephen Lamm)'

import hashlib
import logging

from google.appengine.api import datastore
from google.appengine.api import datastore_errors
from google.appengine.api import datastore_types
from google.appengine.api import memcache
from google.appengine.ext import db

from models import result_ranker_storage

# Two alternative rankers here
import score_ranker
from google_app_engine_ranklist import ranker


class ResultRankerParent(db.Model):
  category = db.StringProperty()
  test_key = db.StringProperty()
  user_agent_version = db.StringProperty()
  params = db.StringProperty()
  min_value = db.IntegerProperty()
  max_value = db.IntegerProperty()
  branching_factor = db.IntegerProperty()


class MedianRanker(score_ranker.Ranker):

  def GetMedian(self, num_scores=None):
    return self.GetMedianAndNumScores(num_scores)[0]

  def GetMedianAndNumScores(self, num_scores=None):
    if num_scores is None:
      num_scores = self.TotalRankedScores()
    median_index = int(round(num_scores/2))
    try:
      median = self.FindScore(median_index)
    # TODO: Give exact exceptions to catch
    except:
      median = None
    return median, num_scores


class ResultRanker(MedianRanker):

  def __init__(self, category, test, user_agent_version, params=None):
    """Return an existing or new ranker.

    Args:
      category: a test category string (e.g. 'network' or 'reflow')
      test: a test instance (e.g. NetworkTest or ReflowTest)
      user_agent_version: browser name and version (e.g. 'Safari 4.0' or 'IE 8')
      params: addional parameters to add to the key
    Returns:
      a Ranker instance
    """
    query = ResultRankerParent.all()
    query.filter('category =', category)
    query.filter('test_key =', test.key)
    query.filter('user_agent_version =', user_agent_version)
    params_str = ''
    if params:
      params_str = "&".join(sorted(params))
      query.filter('params =', params_str)
    ranker_parent = query.get()
    if not ranker_parent:
      ranker_parent = ResultRankerParent(
          category=category,
          test_key=test.key,
          user_agent_version=user_agent_version,
          params=params_str,
          min_value=test.min_value,
          max_value=test.max_value,
          branching_factor=score_ranker.GetShallowBranchingFactor(
              test.min_value, test.max_value))
      ranker_parent.put()
    self.storage = result_ranker_storage.ScoreDatastore(
        ranker_parent.key())
    score_ranker.Ranker.__init__(
        self,
        self.storage,
        ranker_parent.min_value,
        ranker_parent.max_value,
        ranker_parent.branching_factor)


class RankListRanker(MedianRanker):
  MAX_TEST_MSEC = 60000
  BRANCHING_FACTOR = 100

  def __init__(self, category, test, user_agent_version, params=None):
    self.key_name = self.KeyName(category, test.key, user_agent_version, params)
    key = datastore_types.Key.from_path('app', self.key_name)
    try:
      self.ranker = ranker.Ranker(datastore.Get(key)['ranker'])
      logging.warn("Found ranker: %s", self.key_name)
    except datastore_errors.EntityNotFoundError:
      logging.warn("Create ranker: %s", self.key_name)
      self.ranker = ranker.Ranker.Create(
          [0, self.MAX_TEST_MSEC], self.BRANCHING_FACTOR)
      app = datastore.Entity('app', name=self.key_name)
      app['ranker'] = self.ranker.rootkey
      datastore.Put(app)

  @staticmethod
  def KeyName(category, test_key, user_agent_version, params=None):
    key_parts = [category, test_key, user_agent_version]
    if params:
      key_parts.append(hashlib.md5(','.join(params)).hexdigest())
    return '_'.join(key_parts)

  def Add(self, score):
    self.Update([score])

  def Update(self, scores):
    # The old code used 'created' as part of the score key.
    # That had the problem where if two tests had the same created time,
    # only one would get counted. This version is not much better.
    import datetime
    now = str(datetime.datetime.now())
    user_scores = dict(("n_%s_%s" % (now, i), [score])
                       for i, score in enumerate(scores))
    self.ranker.SetScores(user_scores)
    logging.warn("Total after adding %s score(s): %s", len(scores), self.TotalRankedScores())

  #def Remove
  #def RemoveMultiple

  def FindScore(self, rank):
    return self.ranker.FindScore(rank)[0][0]

  def TotalRankedScores(self):
    return self.ranker.TotalRankedScores()


def Factory(category, test, user_agent_version, params=None):
  #return ResultRanker(category, test, user_agent_version, params)
  return RankListRanker(category, test, user_agent_version, params)