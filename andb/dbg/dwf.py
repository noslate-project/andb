
from __future__ import print_function, division

from andb.fmt import RawDwarf

class Dwf:
    """ singleton
    """
    @classmethod
    def Load(cls, filename):
        cls.raw = RawDwarf(filename)
        cls.raw.Load()
   
    @classmethod
    def ReadConst(cls, const_key):
        """ read const from typ file.
            
            the function accept two kinds of const path. (same with GDB)
            
            e.g. 
            1) 'v8::internal::HeapObject'::kMapOffset
                find 'kMapOffset' in 'v8::internal::HeapObject' type.
            2) v8::internal::kTagBits
                find only 'v8::internal::kTagBits' 
        """
        if const_key[0] == "'":
            arr = const_key[1:].split("'::")
            return cls.raw.ReadTypeConst(arr[0], arr[1])
        else:
            return cls.raw.ReadConst(const_key)

    @classmethod
    def ReadClassConst(cls, class_name, const_name):
        return cls.raw.ReadTypeConst(class_name, const_name)

    @classmethod
    def ReadNonDirectConst(cls, class_name, const_name):
        return cls.raw.ReadNonDirectConst(class_name, const_name)

    @classmethod
    def ReadAllConsts(cls, class_name):
        """ read all consts the class_name has (include inherits).
        """
        return cls.raw.ReadAllConsts(class_name)

    @classmethod
    def ReadAllConstsNoInheritesByList(cls, class_name, consts_list):
        """ read specified consts in class_name. (not include inherits or children's)  
        """
        return cls.raw.ReadAllConstsNoInheritesByList(class_name, consts_list)

    @classmethod
    def ShowInherits(cls, class_name):
        return cls.raw.ShowInherits(class_name)
