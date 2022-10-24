# -*- coding: UTF-8 -*-

from __future__ import print_function, division

""" v8 engine support
"""

from .internal import Enum, Version
from andb.utility import CachedProperty

""" v8 c++ Enum 
"""
class AbortReason(Enum):
    _typeName = 'v8::internal::AbortReason'


class AllocationSpace(Enum):
    _typeName = "v8::internal::AllocationSpace"

    RO_SPACE = 0
    NEW_SPACE = 1
    OLD_SPACE = 2
    CODE_SPACE = 3
    MAP_SPACE = 4
    LO_SPACE = 5
    CODE_LO_SPACE = 6
    NEW_LO_SPACE = 7
    FIRST_SPACE = 0
    LAST_SPACE = 7

    @classmethod
    def SpaceName(cls, id):
        if id == cls.RO_SPACE:
            return "read_only_space"
        elif id == cls.NEW_SPACE:
            return "new_space"
        elif id == cls.OLD_SPACE:
            return "old_space"
        elif id == cls.CODE_SPACE:
            return "code_space"
        elif id == cls.MAP_SPACE:
            return "map_space"
        elif id == cls.LO_SPACE:
            return "lo_space"
        elif id == cls.CODE_LO_SPACE:
            return "code_lo_space"
        elif id == cls.NEW_LO_SPACE:
            return "new_lo_space"
        raise ValueError

    @classmethod
    def SpaceId(cls, name):
        if name == 'new' or name == 'new_space':
            return cls.NEW_SPACE
        elif name == 'old' or name == 'old_space':
            return cls.OLD_SPACE
        elif name == 'map' or name == 'map_space':
            return cls.MAP_SPACE
        elif name == 'code' or name == 'code_space':
            return cls.CODE_SPACE
        elif name == 'lo' or name == 'lo_space':
            return cls.LO_SPACE
        elif name == 'code_lo' or name == 'code_lo_space':
            return cls.CODE_LO_SPACE
        elif name == 'new_lo' or name == 'new_lo_space':
            return cls.NEW_LO_SPACE
        elif name == 'read_only' or name == 'ro' or name == 'readonly' or \
                name == "ro_space" or name == 'read_only_space' or name == 'readonly_space':
            return cls.RO_SPACE
        return None

    @classmethod
    def AllSpaces(cls):
        return [
            cls.RO_SPACE,
            cls.MAP_SPACE,
            cls.CODE_SPACE,
            cls.CODE_LO_SPACE,
            cls.OLD_SPACE,
            cls.LO_SPACE,
            cls.NEW_LO_SPACE,
            cls.NEW_SPACE,
        ]

    @classmethod
    def NonROSpaces(cls):
        return [
            cls.MAP_SPACE,
            cls.CODE_SPACE,
            cls.CODE_LO_SPACE,
            cls.OLD_SPACE,
            cls.LO_SPACE,
            cls.NEW_LO_SPACE,
            cls.NEW_SPACE,
        ]

    @classmethod
    def OnlyOldSpaces(cls):
        return [
            cls.MAP_SPACE,
            cls.CODE_SPACE,
            cls.CODE_LO_SPACE,
            cls.OLD_SPACE,
            cls.LO_SPACE,
        ]


class AllocationType(Enum):
    _typeName = "v8::internal::AllocationType"

    kYoung = 0
    kOld = 1
    kCode = 2
    kMap = 3
    kReadOnly = 4


class BailoutReason(Enum):
    _typeName = 'v8::internal::BailoutReason'


class BuiltinsName(Enum):
    # from node-v16(v8-v9.4.146) Builtin Enumerator changed name to 'v8::i::Builtin'
    if Version.major >= 9:
        _typeName = 'v8::internal::Builtin'
    else:
        _typeName = 'v8::internal::Builtins::Name'

class ElementsKind(Enum):
    _typeName = "v8::internal::ElementsKind"

    def IsTypedArrayElementsKind(self, elements_kind):
        return self.inRange("FIRST_FIXED_TYPED_ARRAY_ELEMENTS_KIND",
                "LAST_FIXED_TYPED_ARRAY_ELEMENTS_KIND", elements_kind) 

class FunctionKind(Enum):
    _typeName = "v8::internal::FunctionKind"


class FunctionSyntaxKind(Enum):
    _typeName = 'v8::internal::FunctionSyntaxKind'


class InstanceType(Enum):
    
    _typeName = "v8::internal::InstanceType"

    FIRST_NONSTRING_TYPE = 64 
    FIRST_FIXED_ARRAY_BASE_TYPE = 0
    LAST_FIXED_ARRAY_BASE_TYPE = 0
    FIRST_HASH_TABLE_TYPE = 0
    LAST_HASH_TABLE_TYPE = 0
    FIRST_STRING_TYPE = 0
    LAST_STRING_TYPE = 63

    # boundary for JSReceiver that needs special property lookup handling.
    LAST_SPECIAL_RECEIVER_TYPE = 0 

    """ Fixed Array
    """
    @classmethod
    def isFixedArray(cls, num):
        return cls.inRange("FIRST_FIXED_ARRAY_TYPE", "LAST_FIXED_ARRAY_TYPE", num)

    @classmethod
    def isWeakFixedArray(cls, num):
        return cls.inRange("FIRST_WEAK_FIXED_ARRAY_TYPE", "LAST_WEAK_FIXED_ARRAY_TYPE", num)
 
    @classmethod
    def isWeakArrayList(cls, num):
        return cls.isType("WEAK_ARRAY_LIST_TYPE", num)

    @classmethod
    def isByteArray(cls, num):
        return cls.isType("BYTE_ARRAY_TYPE", num)
   
    @classmethod
    def isFixedDoubleArray(cls, num):
        return cls.isType("FIXED_DOUBLE_ARRAY_TYPE", num)
  
    @classmethod
    def isEphemeronHashTable(cls, num):
        return cls.isType("EPHEMERON_HASH_TABLE_TYPE", num)

    @classmethod
    def isArrayBoilerplateDescription(cls, num):
        return cls.isType("ARRAY_BOILERPLATE_DESCRIPTION_TYPE", num)

    """ Hash Tables
    """
    @classmethod
    def IsNameDictionary(cls, num):
        return cls.isType("NAME_DICTIONARY_TYPE", num)
    
    @classmethod
    def IsGlobalDictionary(cls, num):
        return cls.isType("GLOBAL_DICTIONARY_TYPE", num)
   
    """ Context
    """
    @classmethod
    def isContext(cls, num):
        return cls.inRange("FIRST_CONTEXT_TYPE", "LAST_CONTEXT_TYPE", num)

    @classmethod
    def isNativeContext(cls, num):
        return cls.isType("NATIVE_CONTEXT_TYPE", num)
    
    @classmethod
    def isFunctionContext(cls, num):
        return cls.isType("FUNCTION_CONTEXT_TYPE", num)

    @classmethod
    def isScopeInfo(cls, num):
        return cls.isType("SCOPE_INFO_TYPE", num)

    """ Map
    """
    @classmethod
    def isMap(cls, num):
        return cls.isType("MAP_TYPE", num)

    """ Oddball
    """
    @classmethod
    def isOddball(cls, num):
        return cls.isType("ODDBALL_TYPE", num)
    
    @classmethod
    def isForeign(cls, num):
        return cls.isType("FOREIGN_TYPE", num)

    """ Symbol
    """
    @classmethod
    def isSymbol(cls, num):
        return cls.isType("SYMBOL_TYPE", num)
    
    @classmethod
    def isCell(cls, num):
        return cls.isType("CELL_TYPE", num)

    @classmethod
    def isPropertyCell(cls, num):
        return cls.isType("PROPERTY_CELL_TYPE", num)

    """ Code / Script
    """
    @classmethod
    def isCode(cls, num):
        return cls.isType("CODE_TYPE", num)
    
    @classmethod
    def isScript(cls, num):
        return cls.isType("SCRIPT_TYPE", num)

    @classmethod
    def isBytecodeArray(cls, num):
        return cls.isType("BYTECODE_ARRAY_TYPE", num)
   
    @classmethod
    def isEmbedderDataArray(cls, num):
        return cls.isType("EMBEDDER_DATA_ARRAY_TYPE", num)
    
    @classmethod
    def isAllocationSite(cls, num):
        return cls.isType("ALLOCATION_SITE_TYPE", num)

    """ Number
    """
    @classmethod
    def isBigInt(cls, num):
        return cls.isType('BIGINT_TYPE', num)
    
    @classmethod
    def isHeapNumber(cls, num):
        return cls.isType("HEAP_NUMBER_TYPE", num)

    """ JSObject
    """
    #@classmethod
    #def isJSObject(cls, num):
    #    return cls.isType("JS_OBJECT_TYPE", num)
        
    @classmethod
    def isJSObject(cls, num):
        return cls.inRange("FIRST_JS_OBJECT_TYPE", "LAST_JS_OBJECT_TYPE", num)

    @classmethod
    def isDescriptorArray(cls, num):
        return cls.isType("DESCRIPTOR_ARRAY_TYPE", num)

    @classmethod
    def isPropertyArray(cls, num):
        return cls.isType("PROPERTY_ARRAY_TYPE", num)
   
    @classmethod
    def isSwissNameDictionary(cls, num):
        return cls.isType("SWISS_NAME_DICTIONARY_TYPE", num)

    """ JS Objects
    """
    @classmethod
    def isJSFunction(cls, num):
        if cls.isType("JS_FUNCTION_TYPE", num):
            return True
        # from node-
        return cls.inRange("FIRST_JS_FUNCTION_TYPE", "LAST_JS_FUNCTION_TYPE", num)
    
    @classmethod
    def isJSBoundFunction(cls, num):
        return cls.isType("JS_BOUND_FUNCTION_TYPE", num)

    @classmethod
    def isJSRegExp(cls, num):
        return cls.isType("JS_REG_EXP_TYPE", num)
   
    @classmethod
    def isJSGlobalObject(cls, num):
        return cls.isType("JS_GLOBAL_OBJECT_TYPE", num)
 
    @classmethod
    def isJSGlobalProxy(cls, num):
        return cls.isType("JS_GLOBAL_PROXY_TYPE", num)
  
    @classmethod
    def isJSArray(cls, num):
        return cls.isType("JS_ARRAY_TYPE", num)

    @classmethod
    def isJSArrayBuffer(cls, num):
        return cls.isType("JS_ARRAY_BUFFER_TYPE", num)

    @classmethod
    def isJSArrayIterator(cls, num):
        return cls.isType("JS_ARRAY_ITERATOR_TYPE", num)
    
    @classmethod
    def isJSArgumentsObject(cls, num):
        return cls.isType("JS_ARGUMENTS_OBJECT_TYPE", num)

    @classmethod
    def isJSDate(cls, num):
        return cls.isType("JS_DATE_TYPE", num)
    
    @classmethod
    def isJSError(cls, num):
        return cls.isType("JS_ERROR_TYPE", num)

    @classmethod
    def isJSMap(cls, num):
        return cls.isType("JS_MAP_TYPE", num)
    
    @classmethod
    def isJSSet(cls, num):
        return cls.isType("JS_SET_TYPE", num)

    @classmethod
    def isJSWeakMap(cls, num):
        return cls.isType("JS_WEAK_MAP_TYPE", num)
    
    @classmethod
    def isJSWeakSet(cls, num):
        return cls.isType("JS_WEAK_SET_TYPE", num)

    @classmethod
    def isJSProxy(cls, num):
        return cls.isType("JS_PROXY_TYPE", num)
    
    @classmethod
    def isJSTypedArray(cls, num):
        return cls.isType("JS_TYPED_ARRAY_TYPE", num)

    @classmethod
    def isJSPrimitiveWrapper(cls, num):
        return cls.isType("JS_PRIMITIVE_WRAPPER_TYPE", num)
    
    @classmethod
    def isJSGeneratorObject(cls, num):
        return cls.inRange("FIRST_JS_GENERATOR_OBJECT_TYPE", "LAST_JS_GENERATOR_OBJECT_TYPE", num)

    @classmethod
    def isJSMapIterator(cls, num):
        return cls.inRange("FIRST_JS_MAP_ITERATOR_TYPE", "LAST_JS_MAP_ITERATOR_TYPE", num)
    
    @classmethod
    def isJSSetIterator(cls, num):
        return cls.inRange("FIRST_JS_SET_ITERATOR_TYPE", "LAST_JS_SET_ITERATOR_TYPE", num)

    @classmethod
    def isString(cls, num):
        return cls.inRange("FIRST_STRING_TYPE", "LAST_STRING_TYPE", num)
   
    @classmethod
    def isSharedFunctionInfo(cls, num):
        return cls.isType("SHARED_FUNCTION_INFO_TYPE", num)

    @classmethod
    def isAccessorInfo(cls, num):
        return cls.isType("ACCESSOR_INFO_TYPE", num)
    
    @classmethod
    def isAccessorPair(cls, num):
        return cls.isType("ACCESSOR_PAIR_TYPE", num)

    @classmethod
    def isFeedbackCell(cls, num):
        return cls.isType("FEEDBACK_CELL_TYPE", num)

    @classmethod
    def isFeedbackVector(cls, num):
        return cls.isType("FEEDBACK_VECTOR_TYPE", num)
    
    @classmethod
    def isFeedbackMetadata(cls, num):
        return cls.isType("FEEDBACK_METADATA_TYPE", num)
   
    @classmethod
    def isTransitionArray(cls, num):
        return cls.isType("TRANSITION_ARRAY_TYPE", num)

    """ template info
    """
    @classmethod
    def isFunctionTemplateInfo(cls, num):
        return cls.isType("FUNCTION_TEMPLATE_INFO_TYPE", num)
    
    @classmethod
    def isObjectTemplateInfo(cls, num):
        return cls.isType("OBJECT_TEMPLATE_INFO_TYPE", num)

    """ Free/Fill
    """
    @classmethod
    def isFreeSpace(cls, num):
        return cls.isType("FREE_SPACE_TYPE", num)

    """ boundary
    """
    @classmethod
    def isSpecialReceiverInstanceType(cls, num):
        return num <= cls.LAST_SPECIAL_RECEIVER_TYPE

    """ Pretty names
    """
    @classmethod
    def CamelName(cls, num):
        """ cut tail 'Type' """
        s = super(InstanceType, cls).CamelName(num)
        i = s.rfind('Type')
        if i > 1:
            return s[:i]
        return s

    @CachedProperty
    def camel_name(self):
        return self.CamelName(int(self))

    @classmethod
    def instance_type_list(cls):
        """ return the instance type list
        """
        pass

class RepresentationKind(Enum):
    _typeName = "v8::internal::Representation::Kind"

    kNone = 0
    kSmi = 1
    kDouble = 2
    kHeapObject = 3
    kTagged = 4


class LanguageMode(Enum):
    _typeName = 'v8::internal::LanguageMode'


class PromiseState(Enum):
    _typeName = 'v8::Promise::PromiseState'



class PropertyAttributes(Enum):
    """ control the property eg READ_ONLY, SEALD, FROZEN etc.
    """
    _typeName = 'v8::internal::PropertyAttributes'


class PropertyFilter(Enum):
    """ Filter in Properties
    """
    _typeName = 'v8::internal::PropertyFilter'


class PropertyKind(Enum):
    """ Data or Accessor
    """
    _typeName = 'v8::internal::PropertyKind'


class PropertyLocation(Enum):
    """ Field or Descriptor
    """
    _typeName = 'v8::internal::PropertyLocation'


class PropertyConstness(Enum):
    """ Mutable or Const
    """
    _typeName = 'v8::internal::PropertyConstness'


class PropertyCellType(Enum):
    """ A PropertyCell's property details contains a cell type that is meaningful if
        the cell is still valid (does nt hold the hole)
    """
    _typeName = 'v8::internal::PropertyCellType'


class PropertyCellConstantType(Enum):
    #_typeName = 'v8::internal::PropertyCellConstantType'
    pass

class Root(Enum):
    _typeName = 'v8::internal::Root'

    # kStringTable = 0
    # kExternalStringsTable = 1
    # kReadOnlyRootList = 2
    # kStrongRootList = 3
    # kSmiRootList = 4
    # kBootstrapper = 5
    # kTop = 6
    # kRelocatable = 7
    # kDebug = 8
    # kCompilationCache = 9
    # kHandleScope = 10
    # kBuiltins = 11
    # kGlobalHandles = 12
    # kEternalHandles = 13
    # kThreadManager = 14
    # kStrongRoots = 15
    # kExtensions = 16
    # kCodeFlusher = 17
    # kStartupObjectCache = 18
    # kReadOnlyObjectCache = 19
    # kWeakCollections = 20
    # kWrapperTracing = 21
    # kUnknown = 22
    kNumberOfRoots = 23 

    @classmethod
    def LoadDwf(cls):
        # load enums from Dwarf
        super(Enum, cls).LoadDwf()
       
        # makeup RootName Table
        ROOT_ID_TBL = {
            "kStringTable": "(Internalized strings)",
            "kExternalStringsTable": "(External strings)",
            "kReadOnlyRootList": "(Read-only roots)",
            "kStrongRootList": "(Strong roots)",
            "kSmiRootList": "(Smi roots)",
            "kBootstrapper": "(Bootstrapper)",
            # kTop was removed by V8-v9
            "kTop": "(Isolate)",
            # kStackRoots was introduced by V8-v9
            "kStackRoots": "(Stack roots)",
            "kRelocatable": "(Relocatable)",
            "kDebug": "(Debugger)",
            "kCompilationCache": "(Compilation cache)",
            "kHandleScope": "(Handle scope)",
            # Dispatch table was removed by V8-v8
            "kDispatchTable": "(Dispatch table)",
            "kBuiltins": "(Builtins)",
            "kGlobalHandles": "(Global handles)",
            "kEternalHandles": "(Eternal handles)",
            "kThreadManager": "(Thread manager)",
            "kStrongRoots": "(Strong roots)",
            "kExtensions": "(Extensions)",
            "kCodeFlusher": "(Code flusher)",
            # partial snapshot cached was removed by V8-v8 
            "kPartialSnapshotCache": "(Partial snapshot cache)",
            # Startup Object Cache was instroduced by V8-v8
            "kStartupObjectCache": "(Startup object cache)",
            "kReadOnlyObjectCache": "(Read-only object cache)",
            "kWeakCollections": "(Weak collections)",
            "kWrapperTracing": "(Wrapper tracing)",
            "kWriteBarrier": "(Write barrier)",
            "kRetainMaps": "(Retain maps)",
            # following two types were introduced by V8-v9
            "kWriteBarrier": "(Write barrier)",
            "kRetainMaps": "(Retain maps)",
            # following types were introduced by v8-10
            "kSharedHeapObjectCache": "(Shareable object cache)",
            "kClientHeap": "(Client heap)",
            # kClientHeap was introduced by V8-v10
            "kUnknown": "(Unknown)",
        }

        cls._root_name_table = [None] * cls.kNumberOfRoots
        for k,v in ROOT_ID_TBL.items():
            e = cls.Find(k)
            if e is not None:
                # skipped None const.
                cls._root_name_table[e] = v
      
        # all types should be all resolved.
        for i in range(cls.kNumberOfRoots):
            assert cls._root_name_table[i] is not None, i

    @classmethod
    def RootName(cls, root):
        """ get Root's Name
        """
        assert root < cls.kNumberOfRoots
        return cls._root_name_table[root] 

class RootIndex(Enum):
    _typeName = "v8::internal::RootIndex"

    kFirstRoot = 0
    kLastRoot = 0
    kFirstReadOnlyRoot = 0
    kLastReadOnlyRoot = 0
    kFirstStrongRoot = 0 
    kLastStrongRoot = 0 
    kFirstStrongOrReadOnlyRoot = 0
    kLastStrongOrReadOnlyRoot = 0


class ScopeType(Enum):
    _typeName = 'v8::internal::ScopeType'

class VariableAllocationInfo(Enum):
    _typeName = 'v8::internal::VariableAllocationInfo'

    NONE = 0
    STACK = 1
    CONTEXT = 2

    @classmethod
    def isNone(cls, num):
        return num == cls.NONE

class CodeKind(Enum):

    if Version.major >= 9:
        _typeName = 'v8::internal::CodeKind'
    else:
        _typeName = 'v8::internal::Code::Kind'

class VariableMode(Enum):
    _typeName = 'v8::internal::VariableMode'

class InitializationFlag(Enum):
    _typeName = 'v8::internal::InitializationFlag'

class MaybeAssignedFlag(Enum):
    _typeName = 'v8::internal::MaybeAssignedFlag'

class IsStaicFlag(Enum):
    _typeName = 'v8::internal::IsStaticFlag'


