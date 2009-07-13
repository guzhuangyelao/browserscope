#!/usr/bin/python2.4
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

"""Test set class."""

__author__ = 'slamm@google.com (Stephen Lamm)'


class ExampleTest(object):
  def __init__(self, key, name, doc):
    self.key = key
    self.name = name
    self.url = key
    self.score_type = 'custom'
    self.doc = doc
    self.min_value = 0
    self.max_value = 1


class TestSet(object):
  def __init__(self, category, category_name, tests, subnav, home_intro,
               default_params=None):
    """Initialize a test set.

    A test set has all the tests for a category.

    Args:
      category: a string
      category_name: a string, human-readable
      tests: a list of test instances
      subnav: a dict of labels to urls
      home_intro: a string, possibly HTML, to give an introduction
    """
    self.category = category
    self.category_name = category_name
    self.tests = tests
    self.subnav = subnav
    self.home_intro = home_intro
    self.default_params = default_params
    self._test_dict = dict((test.key, test) for test in tests)

  def GetTest(self, test_key):
    return self._test_dict[test_key]
