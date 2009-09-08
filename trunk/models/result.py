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

import logging
import sys

from google.appengine.ext import db
from google.appengine.api import memcache

from categories import all_test_sets
from models import user_agent
from models.user_agent import UserAgent

import settings

class ResultTime(db.Model):
  test = db.StringProperty()
  score = db.IntegerProperty()
  dirty = db.BooleanProperty(default=True)

  def increment_all_counts(self):
    for ranker in self.GetRankers():
      ranker.Add(self.score)
    self.dirty = False
    self.put()

  def GetRankers(self):
    parent = self.parent()
    test_set = all_test_sets.GetTestSet(parent.category)
    try:
      test = test_set.GetTest(self.test)
    except KeyError:
      logging.warn('No rankers for test: %s', self.test)
    else:
      for user_agent_string in parent.user_agent.get_string_list():
        yield test.GetRanker(user_agent_string, parent.params)


class ResultParent(db.Expando):
  """A parent entity for a test run.

  Inherits from db.Expando instead of db.Model to allow the network_loader
  to add an attribute for 'loader_id'.
  """
  category = db.StringProperty()
  user_agent = db.ReferenceProperty(UserAgent)
  user_agent_pretty = db.StringProperty()
  ip = db.StringProperty()
  # TODO(elsigh) remove user in favor of user_id
  user = db.UserProperty()
  user_id = db.StringProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  params = db.StringListProperty(default=[])

  @classmethod
  def AddResult(cls, test_set, ip, user_agent_string, results, **kwds):
    """Create result models and stores them as one transaction.

    Args:
      test_set: an instance of test_set_base.
      ip: a string to store as the user's IP. This should be hashed beforehand.
      user_agent_string: The full user agent string.
      results: a list of dictionaries.

    Returns:
      A ResultParent instance.
    """
    logging.debug('ResultParent.AddResult')
    user_agent = UserAgent.factory(user_agent_string)
    parent = cls(category=test_set.category,
                 ip=ip,
                 user_agent=user_agent,
                 user_agent_pretty=user_agent.pretty(),
                 **kwds)

    # Call the TestSet's ParseResults method
    results = test_set.ParseResults(results)

    if len(results) != len(test_set.tests):
      logging.debug('len(results)[%s] != len(test_set.tests)[%s] for %s.' %
                    (len(results), len(test_set.tests), test_set.category))
      return


    for results_dict in results:
      # Make sure this test is is legit.
      try:
        test = test_set.GetTest(results_dict['key'])
      except:
        logging.debug('Got a test(%s) not in the test_set for %s' %
                      (results_dict['key'], test_set.category))
        return

      # Are there expandos after calling ParseResults?
      if results_dict.has_key('expando'):
        parent.__setattr__(str(results_dict['key']), results_dict['expando'])

    def _AddResultInTransaction():
      parent.put()
      for results_dict in results:
        db.put(ResultTime(parent=parent, test=str(results_dict['key']),
               score=int(results_dict['score'])))
    db.run_in_transaction(_AddResultInTransaction)
    return parent

  def invalidate_ua_memcache(self):
    memcache_ua_keys = ['%s_%s' % (self.category, user_agent)
                        for user_agent in self._get_user_agent_list()]
    #logging.debug('invalidate_ua_memcache, memcache_ua_keys: %s' %
    #             memcache_ua_keys)
    memcache.delete_multi(keys=memcache_ua_keys, seconds=0,
                          namespace=settings.STATS_MEMCACHE_UA_ROW_NS)

  def increment_all_counts(self):
    """This is not efficient enough to be used in prod."""
    result_times = self.get_result_times_as_query()
    for result_time in result_times:
      #logging.debug('ResultTime key is %s ' % (result_time.key()))
      #logging.debug('w/ ua: %s' %  result_time.parent().user_agent)
      result_time.increment_all_counts()

  def get_result_times_as_query(self):
    return ResultTime.all().ancestor(self)

  def get_result_times(self):
    """As long as a parent has less than 1000 result times,
       this will return them all.
    """
    return self.get_result_times_as_query().fetch(1000, 0)

  def _get_user_agent_list(self):
    """Build user_agent_list on-the-fly from user_agent_pretty.

    In the past, we stored user_agent_list.
    """
    return UserAgent.parse_to_string_list(self.user_agent_pretty)