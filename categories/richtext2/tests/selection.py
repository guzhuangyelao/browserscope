#!/usr/bin/python2.5
#
# Copyright 2010 Google Inc.
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

"""Selection tests"""

__author__ = 'rolandsteiner@google.com (Roland Steiner)'

# Selection specifications used in 'id':
#
# Caret/collapsed selections:
#
# SC: 'caret'    caret/collapsed selection
# SB: 'before'   caret/collapsed selection before element
# SA: 'after'    caret/collapsed selection after element
# SS: 'start'    caret/collapsed selection at the start of the element (before first child/at text pos. 0)
# SE: 'end'      caret/collapsed selection at the end of the element (after last child/at text pos. n)
# SX: 'betwixt'  collapsed selection between elements
#
# Range selections:
#
# SO: 'outside'  selection wraps element in question
# SI: 'inside'   selection is inside of element in question
# SW: 'wrap'     as SI, but also wraps all children of element
# SL: 'left'     oblique selection - starts outside element and ends inside
# SR: 'right'    oblique selection - starts inside element and ends outside
# SM: 'mixed'    selection starts and ends in different elements
#
# SxR: selection is reversed
#
# Sxn or SxRn    selection applies to element #n of several identical

SELECTION_TESTS = {
  'id':            'S',
  'caption':       'Selection Tests',
  'checkAttrs':    True,
  'checkStyle':    True,
  'checkSel':      True,
  'styleWithCSS':  False,

  'RFC': [
    # selectall
    { 'id':         'SELALL_TEXT-1_SI',
      'desc':       'select all, text only',
      'command':    'selectall',
      'pad':        'foo [bar] baz',
      'expected':   [ '[foo bar baz]',
                      '{foo bar baz}' ] },

    { 'id':         'SELALL_I-1_SI',
      'desc':       'select all, with outer tags',
      'command':    'selectall',
      'pad':        '<i>foo [bar] baz</i>',
      'expected':   '{<i>foo bar baz</i>}' },

    # unselect
    { 'id':         'UNSEL_TEXT-1_SI',
      'desc':       'unselect',
      'command':    'unselect',
      'pad':        'foo [bar] baz',
      'expected':   'foo bar baz' },

    # sel.modify
    { 'id':         'SM:m.f.c_TEXT-1_SC-1',
      'desc':       'move caret 1 character forward',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'foo b^ar baz',
      'expected':   'foo ba^r baz' },

    { 'id':         'SM:m.b.c_TEXT-1_SC-1',
      'desc':       'move caret 1 character backward',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo b^ar baz',
      'expected':   'foo ^bar baz' },

    { 'id':         'SM:m.f.c_TEXT-1_SI-1',
      'desc':       'move caret forward (sollapse selection)',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'foo [bar] baz',
      'expected':   'foo bar^ baz' },

    { 'id':         'SM:m.b.c_TEXT-1_SI-1',
      'desc':       'move caret backward (collapse selection)',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo [bar] baz',
      'expected':   'foo ^bar baz' },

    { 'id':         'SM:m.f.w_TEXT-1_SC-1',
      'desc':       'move caret 1 word forward',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        'foo b^ar baz',
      'expected':   'foo bar^ baz' },

    { 'id':         'SM:m.f.w_TEXT-1_SC-2',
      'desc':       'move caret 1 word forward',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        'foo^ bar baz',
      'expected':   'foo bar^ baz' },

    { 'id':         'SM:m.f.w_TEXT-1_SI-1',
      'desc':       'move caret 1 word forward from non-collapsed selection',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        'foo [bar] baz',
      'expected':   'foo bar baz^' },

    { 'id':         'SM:m.b.w_TEXT-1_SC-1',
      'desc':       'move caret 1 word backward',
      'function':   'sel.modify("move", "backward", "word");',
      'pad':        'foo b^ar baz',
      'expected':   'foo ^bar baz' },

    { 'id':         'SM:m.b.w_TEXT-1_SC-3',
      'desc':       'move caret 1 word backward',
      'function':   'sel.modify("move", "backward", "word");',
      'pad':        'foo bar ^baz',
      'expected':   'foo ^bar baz' },

    { 'id':         'SM:m.b.w_TEXT-1_SI-1',
      'desc':       'move caret 1 word backward from non-collapsed selection',
      'function':   'sel.modify("move", "backward", "word");',
      'pad':        'foo [bar] baz',
      'expected':   '^foo bar baz' },

    # --- move forward over combining diacritics, etc.
    { 'id':         'SM:m.f.c_CHAR-2_SC-1',
      'desc':       'move 1 character forward over combined o with diaeresis',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^&#xF6;barbaz',
      'expected':   'fo&#xF6;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-3_SC-1',
      'desc':       'move 1 character forward over character with combining diaeresis above',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^o&#x0308;barbaz',
      'expected':   'foo&#x0308;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-4_SC-1',
      'desc':       'move 1 character forward over character with combining diaeresis below',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^o&#x0324;barbaz',
      'expected':   'foo&#x0324;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-5_SC-1',
      'desc':       'move 1 character forward over character with combining diaeresis above and below',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^o&#x0308;&#x0324;barbaz',
      'expected':   'foo&#x0308;&#x0324;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-5_SI-1',
      'desc':       'move 1 character forward over character with combining diaeresis above and below, selection on diaeresis above',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'foo[&#x0308;]&#x0324;barbaz',
      'expected':   'foo&#x0308;&#x0324;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-5_SI-2',
      'desc':       'move 1 character forward over character with combining diaeresis above and below, selection on diaeresis below',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'foo&#x0308;[&#x0324;]barbaz',
      'expected':   'foo&#x0308;&#x0324;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-5_SL',
      'desc':       'move 1 character forward over character with combining diaeresis above and below, selection oblique on diaeresis and preceding text',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo[o&#x0308;]&#x0324;barbaz',
      'expected':   'foo&#x0308;&#x0324;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-5_SR',
      'desc':       'move 1 character forward over character with combining diaeresis above and below, selection oblique on diaeresis and following text',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'foo&#x0308;[&#x0324;bar]baz',
      'expected':   'foo&#x0308;&#x0324;bar^baz' },

    { 'id':         'SM:m.f.c_CHAR-6_SC-1',
      'desc':       'move 1 character forward over character with enclosing square',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^o&#x20DE;barbaz',
      'expected':   'foo&#x20DE;^barbaz' },

    { 'id':         'SM:m.f.c_CHAR-7_SC-1',
      'desc':       'move 1 character forward over character with combining long solidus overlay',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        'fo^o&#x0338;barbaz',
      'expected':   'foo&#x0338;^barbaz' },

    # --- move backward over combining diacritics, etc.
    { 'id':         'SM:m.b.c_CHAR-2_SC-1',
      'desc':       'move 1 character backward over combined o with diaeresis',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'fo&#xF6;^barbaz',
      'expected':   'fo^&#xF6;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-3_SC-1',
      'desc':       'move 1 character backward over character with combining diaeresis above',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0308;^barbaz',
      'expected':   'fo^o&#x0308;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-4_SC-1',
      'desc':       'move 1 character backward over character with combining diaeresis below',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0324;^barbaz',
      'expected':   'fo^o&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-5_SC-1',
      'desc':       'move 1 character backward over character with combining diaeresis above and below',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0308;&#x0324;^barbaz',
      'expected':   'fo^o&#x0308;&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-5_SI-1',
      'desc':       'move 1 character backward over character with combining diaeresis above and below, selection on diaeresis above',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo[&#x0308;]&#x0324;barbaz',
      'expected':   'fo^o&#x0308;&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-5_SI-2',
      'desc':       'move 1 character backward over character with combining diaeresis above and below, selection on diaeresis below',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0308;[&#x0324;]barbaz',
      'expected':   'fo^o&#x0308;&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-5_SL',
      'desc':       'move 1 character backward over character with combining diaeresis above and below, selection oblique on diaeresis and preceding text',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'fo[o&#x0308;]&#x0324;barbaz',
      'expected':   'fo^o&#x0308;&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-5_SR',
      'desc':       'move 1 character backward over character with combining diaeresis above and below, selection oblique on diaeresis and following text',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0308;[&#x0324;bar]baz',
      'expected':   'fo^o&#x0308;&#x0324;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-6_SC-1',
      'desc':       'move 1 character backward over character with enclosing square',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x20DE;^barbaz',
      'expected':   'fo^o&#x20DE;barbaz' },

    { 'id':         'SM:m.b.c_CHAR-7_SC-1',
      'desc':       'move 1 character backward over character with combining long solidus overlay',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        'foo&#x0338;^barbaz',
      'expected':   'fo^o&#x0338;barbaz' },

    # --- move forward/backward/left/right in RTL text
    { 'id':         'SM:m.f.c_Pdir:rtl-1_SC-1',
      'desc':       'move caret forward 1 character in right-to-left text',
      'function':   'sel.modify("move", "forward", "character");',
      'pad':        '<p dir="rtl">foo b^ar baz</p>',
      'expected':   '<p dir="rtl">foo ^bar baz</p>' },
    
    { 'id':         'SM:m.b.c_Pdir:rtl-1_SC-1',
      'desc':       'move caret backward 1 character in right-to-left text',
      'function':   'sel.modify("move", "backward", "character");',
      'pad':        '<p dir="rtl">foo b^ar baz</p>',
      'expected':   '<p dir="rtl">foo ba^r baz</p>' },
    
    { 'id':         'SM:m.r.c_Pdir:rtl-1_SC-1',
      'desc':       'move caret 1 character to the right in right-to-left text',
      'function':   'sel.modify("move", "right", "character");',
      'pad':        '<p dir="rtl">foo b^ar baz</p>',
      'expected':   '<p dir="rtl">foo ba^r baz</p>' },
    
    { 'id':         'SM:m.l.c_Pdir:rtl-1_SC-1',
      'desc':       'move caret 1 character to the left in right-to-left text',
      'function':   'sel.modify("move", "left", "character");',
      'pad':        '<p dir="rtl">foo b^ar baz</p>',
      'expected':   '<p dir="rtl">foo ^bar baz</p>' },
    
    # --- move forward/backward over words in Japanese text
    { 'id':         'SM:m.f.w_TEXT-jp_SC-1',
      'desc':       'move caret forward 1 word in Japanese text (adjective)',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        '^&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
      'expected':   '&#x9762;&#x767D;&#x3044;^&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;' },
    
    { 'id':         'SM:m.f.w_TEXT-jp_SC-2',
      'desc':       'move caret forward 1 word in Japanese text (in the middle of a word)',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        '&#x9762;^&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
      'expected':   '&#x9762;&#x767D;&#x3044;^&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;' },
    
    { 'id':         'SM:m.f.w_TEXT-jp_SC-3',
      'desc':       'move caret forward 1 word in Japanese text (noun)',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        '&#x9762;&#x767D;&#x3044;^&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
      'expected':   [ '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;^&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
                      '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;^&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;' ] },
    
    { 'id':         'SM:m.f.w_TEXT-jp_SC-4',
      'desc':       'move caret forward 1 word in Japanese text (Katakana)',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;^&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
      'expected':   '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;^&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;' },
    
    { 'id':         'SM:m.f.w_TEXT-jp_SC-5',
      'desc':       'move caret forward 1 word in Japanese text (verb)',
      'function':   'sel.modify("move", "forward", "word");',
      'pad':        '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;^&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;&#x3002;',
      'expected':   '&#x9762;&#x767D;&#x3044;&#x4F8B;&#x6587;&#x3092;&#x30C6;&#x30B9;&#x30C8;&#x3057;&#x307E;&#x3057;&#x3087;&#x3046;^&#x3002;' },
    
    # sel.selectAllChildren(<element>)
    { 'id':         'SAC:div_DIV-1_SC-1',
      'desc':       'selectAllChildren(<div>)',
      'function':   'sel.selectAllChildren(doc.getElementById("div"));',
      'pad':        'foo<div id="div">bar <span>ba^z</span></div>qoz',
      'expected':   [ 'foo<div id="div">{bar <span>baz</span>}</div>qoz',
                       'foo<div id="div">[bar <span>baz</span>}</div>qoz' ] }
  ]
}
