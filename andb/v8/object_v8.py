# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import re

from functools import wraps

import andb.dbg as dbg
from .internal import (
    Internal, 
    Value, 
    Enum, 
    ObjectSlot, 
    ObjectSlots,
    ALStruct,
    BitField,
    AutoLayout,
)
import andb.py23 as py23

from .object import (
    FixedArray,
    Object,
    HeapObject,
    HashTable,
    Smi,
    SmiTagged,
    Version,
)


class StringTableShape():
    _typeName = "v8::internal::StringTableShape"

    kPrefixSize = 0
    kEntrySize = 1

class StringTable(HashTable, StringTableShape):
    _typeName = 'v8::internal::StringTable'

    # Must have
    kEntryKeyIndex = 0
    kElementsStartIndex = 3 

class ScopeFlags(BitField):
    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        cfg.Add({"name": "scope_type", "bits": 4})
        cfg.Add({"name": "sloppy_eval_can_extend_vars", "bits": 1})
        cfg.Add({"name": "language_mode", "bits": 1})
        cfg.Add({"name": "declaration_scope", "bits": 1})
        cfg.Add({"name": "receiver_variable", "bits": 2, "type": VariableAllocationInfo})
        cfg.Add({"name": "has_class_brand", "bits": 1})
        if Version.major > 7:
            cfg.Add({"name": "has_saved_class_variable_index", "bits": 1})
        cfg.Add({"name": "has_new_target", "bits": 1})
        cfg.Add({"name": "function_variable", "bits": 2, "type": VariableAllocationInfo})
        cfg.Add({"name": "has_inferred_function_name", "bits": 1})
        cfg.Add({"name": "is_asm_module", "bits": 1})
        cfg.Add({"name": "has_simple_parameters", "bits": 1})
        cfg.Add({"name": "function_kind", "bits": 5, "type": FunctionKind})
        cfg.Add({"name": "has_outer_scope_info", "bits": 1})
        cfg.Add({"name": "is_debug_evaluate_scope", "bits": 1})
        cfg.Add({"name": "force_context_allocation", "bits": 1})
        if Version.major > 7:
            cfg.Add({"name": "private_name_lookup_skips_outer_class", "bits": 1})
            cfg.Add({"name": "has_context_extension_slot", "bits": 1})
            cfg.Add({"name": "is_repl_mode_scope", "bits": 1})
            cfg.Add({"name": "has_locals_block_list", "bits": 1})
        return cfg.Generate()

class PositionInfo(ALStruct):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "start", "type": Smi},
            {"name": "end", "type": Smi},
        ]}

    @classmethod
    def SizeOf(cls):
        return 16


class FunctionVariableInfo(ALStruct):
    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        cfg.Add({"name": "name", "type": Object})
        cfg.Add({"name": "context_or_stack_slot_index", "type": Smi})
        return cfg.Generate()

    @classmethod
    def SizeOf(cls):
        return 16

class VariableProperties(BitField):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "variable_mode", "bits": 4, "type": VariableMode},
            {"name": "init_flag", "bits": 1, "type": InitializationFlag},
            {"name": "maybe_assigned_flag", "bits": 1, "type": MaybeAssignedFlag},
            {"name": "parameter_number", "bits": 16},
            {"name": "is_static_flag", "bits": 1, "type": IsStaicFlag},
        ]}


class ModuleVariable(ALStruct):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "name", "type": String},
            {"name": "index", "type": Smi},
            {"name": "properties", "type": SmiTagged(VariableProperties)},
        ]}

    @classmethod
    def SizeOf(cls):
        return 24


class ScopeInfo(FixedArray):
    _typeName = 'v8::internal::ScopeInfo'

    kFlagsOffset = 16
    kFlags = 0
    kParameterCount = 1
    kContextLocalCount = 2
    kVariablePartIndex = 3

    kPositionInfoEntries = 2
    kFunctionNameEntries = 2

    """ Layout
        // The layout of the variable part of a ScopeInfo is as follows:
        // 1. ContextLocalNames:
        //    Contains the names of local variables and parameters that are allocated
        //    in the context. They are stored in increasing order of the context slot
        //    index starting with Context::MIN_CONTEXT_SLOTS. One slot is used per
        //    context local, so in total this part occupies ContextLocalCount() slots
        //    in the array.
        // 2. ContextLocalInfos:
        //    Contains the variable modes and initialization flags corresponding to
        //    the context locals in ContextLocalNames. One slot is used per
        //    context local, so in total this part occupies ContextLocalCount()
        //    slots in the array.
        // 3. SavedClassVariableInfo:
        //    If the scope is a class scope and it has static private methods that
        //    may be accessed directly or through eval, one slot is reserved to hold
        //    the context slot index for the class variable.
        // 4. ReceiverInfo:
        //    If the scope binds a "this" value, one slot is reserved to hold the
        //    context or stack slot index for the variable.
        // 5. FunctionNameInfo:
        //    If the scope belongs to a named function expression this part contains
        //    information about the function variable. It always occupies two array
        //    slots:  a. The name of the function variable.
        //            b. The context or stack slot index for the variable.
        // 6. InferredFunctionName:
        //    Contains the function's inferred name.
        // 7. SourcePosition:
        //    Contains two slots with a) the startPosition and b) the endPosition if
        //    the scope belongs to a function or script.
        // 8. OuterScopeInfoIndex:
        //    The outer scope's ScopeInfo or the hole if there's none.
        // 9. LocalsBlackList: List of stack allocated local variables. Used by
        //    debug evaluate to properly abort variable lookup when a name clashes
        //    with a stack allocated local that can't be materialized.
        // 10. SourceTextModuleInfo, ModuleVariableCount, and ModuleVariables:
        //     For a module scope, this part contains the SourceTextModuleInfo, the
        //     number of MODULE-allocated variables, and the metadata of those
        //     variables.  For non-module scopes it is empty.
    """
    @classmethod
    def __autoLayout(cls):
        cfg = AutoLayout.Builder()
        if Version.major > 7:
            cfg.Add({"name": "flags", "type": SmiTagged(ScopeFlags)})
        else:
            cfg.Add({"name": "flags", "type": SmiTagged(ScopeFlags), "offset_func": cls.GetOffset})
        cfg.Add({"name": "parameter_count", "type": SmiTagged(int), "offset_func": cls.GetOffset})
        cfg.Add({"name": "context_local_count", "type": SmiTagged(int), "offset_func": cls.GetOffset})
        #cfg.Add({"name": "variable_part", "type": int, "alias": ["kVariablePartIndex"]})
        cfg.Add({"name": "context_local_names[context_local_count]", "type": Object})
        cfg.Add({"name": "context_local_infos[context_local_count]", "type": Smi})
        if Version.major > 7:
            cfg.Add({"name": "saved_class_variable_infos?[has_saved_class_variable_index]", "type": Object})
        cfg.Add({"name": "receiver_info?[has_receiver_info]", "type": Object})
        cfg.Add({"name": "function_variable_info?[has_function_variable_info]", "type": FunctionVariableInfo})
        cfg.Add({"name": "inferred_function_name?[has_inferred_function_name]", "type": Object})
        cfg.Add({"name": "position_info?[has_position_info]", "type": PositionInfo})
        cfg.Add({"name": "outer_scope_info?[has_outer_scope_info]", "type": Object})  # ScopeInfo | TheHole
        if Version.major > 7:
            cfg.Add({"name": "locals_block_list?[has_locals_block_list]", "type": Object})  # HashTable
        cfg.Add({"name": "module_info?[has_module_info]", "type": Object})  # SouceTextModuleInfo
        cfg.Add({"name": "module_variable_count?[has_module_info]", "type": Smi})
        cfg.Add({"name": "module_variables[module_variable_count]", "type": ModuleVariable})
        return cfg.Generate()

    def GetOffset(self, index):
        """ index to offset
        """
        return self.kFlagsOffset + (index * Internal.kTaggedSize)
 
    @property
    def is_empty(self):
        if self.length == 0:
            return True
        return False
   
    @property
    def has_saved_class_variable_index(self):
        return self.flags.has_saved_class_variable_index

    @property
    def has_receiver_info(self):
        x = self.flags.receiver_variable
        if x == VariableAllocationInfo.STACK or \
           x == VariableAllocationInfo.CONTEXT:
            return True
        return False

    @property
    def has_function_variable_info(self):
        x = self.flags.function_variable
        return not VariableAllocationInfo.isNone(x)

    @property
    def has_inferred_function_name(self):
        return self.flags.has_inferred_function_name

    @property
    def has_position_info(self):
        x = self.flags.scope_type
        if x == ScopeType.FUNCTION_SCOPE or \
           x == ScopeType.SCRIPT_SCOPE or \
           x == ScopeType.EVAL_SCOPE or \
           x == ScopeType.MODULE_SCOPE:
            return True
        return False

    @property
    def has_outer_scope_info(self):
        return self.flags.has_outer_scope_info

    @property
    def has_locals_block_list(self):
        return self.flags.has_locals_block_list
    
    @property
    def has_module_info(self):
        x = self.flags.scope_type
        if x == ScopeType.MODULE_SCOPE:
            return True
        return False

    """ Value Functions """
    def FunctionName(self):
        if self.has_function_variable_info:
            o = String.Bind(self.function_variable_info.name)
            if o and o.IsHeapObject() and o.IsString() and o.length > 0:
                return o.ToString()

        if self.has_inferred_function_name:
            o = String.Bind(self.inferred_function_name)
            if o and o.IsString() and o.length > 0:
                return o.ToString()
       
        return None

    def FunctionNameStr(self):
        v = self.FunctionName()
        if v is None:
            return ''
        return v 

    def Name(self):
        if self.has_function_variable_info:
            o = String.Bind(self.function_variable_info.name)
            if o and o.IsHeapObject() and o.IsString() and o.length > 0:
                return o.ToString()
        return None 

    def NameStr(self):
        v = self.Name()
        if v is None:
            return ''
        return v

    def GetContextLocalName(self, index):
        return self.context_local_names(index)


""" tail imports
"""
from .enum import (
    AllocationSpace,
    AllocationType,
    BuiltinsName,
    ElementsKind, 
    InstanceType,
    LanguageMode,
    PropertyAttributes,
    PropertyFilter,
    PropertyKind,
    PropertyLocation,
    PropertyConstness,
    PropertyCellType,
    PropertyCellConstantType,
    Root,
    RootIndex,
    ScopeType,
    VariableAllocationInfo,
    FunctionKind,
    FunctionSyntaxKind,
    VariableMode,
    InitializationFlag,
    MaybeAssignedFlag,
    IsStaicFlag,
)

from .structure import (
    Isolate,
)

from .object import (
    String,
)

from andb.utility import (
    DCHECK,
    Logging as log, 
)
