# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import os,sys
import traceback

from andb.utility import Logging as log

class AndbException(Exception):
    pass

class AndbError(object):
   
    @classmethod
    def NotImplemented(cls, obj, method):
        log.critical('NotImplemented %s.%s' % (obj.__class__.__name__, method))
        raise AndbException()

    @classmethod
    def DecodeFailed(cls, obj, msg = None):
        # assume obj is v8.Object
        log.critical('DecodeFailed %s 0x%x %s' %(obj.__class__.__name__, obj.tag, msg))
        raise AndbException()

    @classmethod
    def ObjectError(cls, obj, msg):
        log.critical('ObjectError %s 0x%x %s' %(obj.__class__.__name__, obj.tag, msg))
        traceback.print_exc()

