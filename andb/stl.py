
#import itertools
#import re
#import sys
#from itertools import imap, izip

from andb.py23 import IteratorBase

class StlHashtableIterator(IteratorBase):
    def __init__(self, hash):
        self.node = hash['_M_before_begin']['_M_nxt']
        self.node_type = find_type(hash.type, '__node_type').pointer()

    def __iter__(self):
        return self

    def __next__(self):
        if self.node == 0:
            raise StopIteration
        elt = self.node.cast(self.node_type).dereference()
        self.node = elt['_M_nxt']
        valptr = elt['_M_storage'].address
        valptr = valptr.cast(elt.type.template_argument(0).pointer())
        return valptr.dereference()

class StlUnorderedMap:
    "std::unordered_map"

    def __init__(self, val):
        self.val = val

    def __getitem__ (self, i):
        pass
 
    @staticmethod
    def flatten (list):
        for elt in list:
            for i in elt:
                yield i

    def hashtable(self):
        return self.val['_M_h']

    def element_count(self):
        return self.hashtable()['_M_element_count']

    def keys(self):
        keys = []
        for d in StlHashtableIterator (self.hashtable()):
            keys.append (d['first'])
        return keys

class UniquePtr:

    def __init__(self, val):
        self.val = val

    def get(self):
        return self.val['_M_t']['_M_t']['_M_head_impl']

class SharedPtr:
    pass

class Vector:
    "std::vector"

    class Iterator(IteratorBase):

        def __init__(self, vec):
            self._current = vec._M_start
            self._finish = vec._M_finish

        def __iter__(self):
            return self

        def __next__(self):
            if self._finish == self._current:
                raise StopIteration
            value = self._current.Dereference()
            self._current = self._current + 1
            return value

    def __init__(self, val):
        # save the Value
        self.val = val

        # element type in Vector
        self.element_type = val.GetType().GetTemplateArgument(0)

    def __getitem__(self, i):
        return self.at(i) 

    def __iter__(self):
        return Vector.Iterator(self)

    def at(self, i):
        return (self._M_start + i).Dereference()

    @property
    def _M_start(self):
        return self.val['_M_impl']['_M_start']
    
    @property
    def _M_finish(self):
        return self.val['_M_impl']['_M_finish']
    
    @property
    def _M_end_of_storage(self):
        return self.val['_M_impl']['_M_end_of_storage']

    @property
    def capacity(self):
        return (self._M_end_of_storage - self._M_start) / self.element_type.SizeOf() 

    @property
    def size(self):
        return (self._M_finish - self._M_start) / self.element_type.SizeOf()

class Map(object):
    "std::map"

    @property 
    def _M_impl(self):
        return self['_M_t']['_M_impl']

    @property
    def node_count(self):
        return self._M_impl['_M_node_count']

class String(object):
    "std::string"

    def __init__(self, val):
        self._val = val

    @property
    def _M_p(self):
        return self._val['_M_dataplus']['_M_p']

    def __str__(self):
        return self._M_p.GetCString()
