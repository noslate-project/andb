# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import re

from functools import wraps

import andb.dbg as dbg
import andb.py23 as py23
from .internal import (
    Internal,
    Struct,
    Value,
    Enum,
    ObjectSlot,
    ObjectSlots,
    ALStruct,
    BitField
)

from .object import (
    HeapObject,
    FixedArray,
    DescriptorArray,
    SmiTagged,
)


class ScopeFlags(BitField):
    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "scope_type", "bits": 4},
            {"name": "sloppy_eval_can_extend_vars", "bits": 1},
            {"name": "language_mode", "bits": 1},
            {"name": "declaration_scope", "bits": 1},
            {"name": "receiver_variable", "bits": 2, "type": VariableAllocationInfo},
            {"name": "has_class_brand", "bits": 1},
            {"name": "has_saved_class_variable_index", "bits": 1},
            {"name": "has_new_target", "bits": 1},
            {"name": "function_variable", "bits": 2, "type": VariableAllocationInfo},
            {"name": "has_inferred_function_name", "bits": 1},
            {"name": "is_asm_module", "bits": 1},
            {"name": "has_simple_parameters", "bits": 1},
            {"name": "function_kind", "bits": 5, "type": FunctionKind},
            {"name": "has_outer_scope_info", "bits": 1},
            {"name": "is_debug_evaluate_scope", "bits": 1},
            {"name": "force_context_allocation", "bits": 1},
            {"name": "private_name_lookup_skips_outer_class", "bits": 1},
            {"name": "has_context_extension_slot", "bits": 1},
            {"name": "is_repl_mode_scope", "bits": 1},
            {"name": "has_locals_block_list", "bits": 1},
            {"name": "is_empty", "bits": 1},
        ]}


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
        return {"layout": [
            {"name": "name", "type": Object},
            {"name": "context_or_stack_slot_index", "type": Smi}
        ]}

    @classmethod
    def SizeOf(cls):
        return 16


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


class ScopeInfo(HeapObject):
    """ V8 ScopeInfo """

    _typeName = 'v8::internal::ScopeInfo'

    kFlagsOffset = 8
    kParameterCountOffset = 16
    kContextLocalCountOffset = 24
    kContextLocalNamesOffset = 32

    kFlags = 0
    kParameterCount = 1
    kContextLocalCount = 2
    kVariablePartIndex = 3

    kPositionInfoEntries = 2
    kFunctionNameEntries = 2
    kModuleVariableEntryLength = 3

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "flags", "type": SmiTagged(ScopeFlags)},
            {"name": "parameter_count", "type": Smi},
            {"name": "context_local_count", "type": SmiTagged(int)},
            {"name": "context_local_names[context_local_count]", "type": String},
            {"name": "context_local_infos[context_local_count]", "type": SmiTagged(VariableProperties)},
            {"name": "saved_class_variable_info?[has_saved_class_variable_index]", "type":  Smi},
            {"name": "receiver_info?[has_receiver_info]", "type": Smi},
            {"name": "function_variable_info?[has_function_variable_info]", "type": FunctionVariableInfo},
            {"name": "inferred_function_name?[has_inferred_function_name]", "type": Object},  # String | Undefined
            {"name": "position_info?[has_position_info]", "type": PositionInfo},
            {"name": "outer_scope_info?[has_outer_scope_info]", "type": Object},  # ScopeInfo | TheHole
            {"name": "locals_block_list?[has_locals_block_list]", "type": Object},  # HashTable
            {"name": "module_info?[has_module_info]", "type": Object},  # SouceTextModuleInfo
            {"name": "module_variable_count?[has_module_info]", "type": Smi},
            {"name": "module_variables[module_variable_count]", "type": ModuleVariable},
        ]}

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

    def AllocateSize(self):
        return self.module_variables__offset_end

    """ Value Functions """
    # def InferredFunctionName(self):
    #     idx = self.InferredFunctionNameIndex()
    #     return self.LoadFieldTag(idx)

    # def ModuleVariableCount(self):
    #     idx = self.ModuleVariableCount()
    #     return self.LoadFieldSmi(idx)

    # def PrintScopeInfoList(self, start, length):
    #     end = start + length
    #     for i in range(start, end):
    #         o = self.LoadFieldTag(i)
    #         print("   - %d: %s" % (i, o.Brief()))

    def FunctionName(self):
        if self.has_function_variable_info:
            o = String.Bind(self.function_variable_info.name)
            if o and o.IsString() and o.length > 0:
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
            if o and o.IsString() and o.length > 0:
                return o.ToString()
        return None
    
    def NameStr(self):
        v = self.Name()
        if v is None:
            return ""
        return v

    def Size(self):
        return self.AllocateSize()

    def DebugPrint2(self):
        print("[ScopeInfo]")
        print(" - parameters: %d" % self.parameter_count)
        print(" - context locals: %d" % self.context_local_count)
        print(" - flags: (0x%x)" % self.flags)
        print("   - scope_type: %s (%d)" % (ScopeType.Name(self.scope_type), self.scope_type))
        if self.slopyy_eval_can_extend_vars:
            print("   - sloppy eval")
        print("   - language mode: %d" % (self.language_mode))
        if self.declaration_scope:
            print("   - declaration scope")
        print("   - receiver: %d" % self.receiver_variable)
        if self.has_class_brand:
            print("   - has class brand")
        if self.has_saved_class_variable_index:
            print("   - has saved class variable index")
        if self.has_new_target:
            print("   - needs new target")
        if self.is_asm_module:
            print("   - asm module")
        if self.has_simple_parameters:
            print("   - simple parameters")
        print("   - function kind: %d" % (self.function_kind))
        if self.has_outer_scope_info:
            print("   - outer scope info: %s" % (self.OuterScopeInfo().Brief()))
        if self.has_locals_black_list:
            print("   - locals blacklist: %s" % (self.LocalsBlackList().Brief()))
        if self.HasFunctionName():
            print("   - function name: %s" % (self.FunctionName().Brief()))
        if self.has_inferred_function_name:
            print("   - inferred function name: %s" % (self.InferredFunctionName().Brief()))
        if self.has_context_extension_slot:
            print("   - has context extension slot")

        if self.context_local_count > 0:
            print(" - context slots")
            self.PrintScopeInfoList(
                self.ContextLocalNamesIndex(),
                self.context_local_count)


class SloppyArgumentsElements(FixedArray):
    _typeName = 'v8::internal::SloppyArgumentsElements'

    kHeaderSize = 32


class StrongDescriptorArray(DescriptorArray):
    _typeName = 'v8::internal::StrongDescriptorArray'


class SwissNameDictionary(HeapObject):
    _typeName = 'v8::internal::SwissNameDictionary'

    kHeaderSize = 8
    kDataTableEntryCount = 2
    kGroupWidth = 16

    def PrefixOffset(self):
        return self.kHeaderSize

    def CapacityOffset(self):
        return self.PrefixOffset() + 4

    def MetaTablePointerOffset(self):
        return self.CapacityOffset() + 4

    def DataTableStartOffset(self):
        return self.MetaTablePointerOffset() + Internal.kTaggedSize

    def DataTableEndOffset(self, capacity):
        return self.CtrlTableStartOffset(capacity)

    def CtrlTableStartOffset(self, capacity):
        return self.DataTableStartOffset() + self.DataTableSize(capacity)

    def PropertyDetailsTableStartOffset(self, capacity):
        return self.CtrlTableStartOffset(capacity) + self.CtrlTableSize(capacity)

    def DataTableSize(self, capacity):
        return capacity * Internal.kTaggedSize * self.kDataTableEntryCount

    def CtrlTableSize(self, capacity):
        return (capacity + self.kGroupWidth) * 1

    def SizeFor(self, capacity):
        return self.PropertyDetailsTableStartOffset(capacity) + capacity

    @property
    def capacity(self):
        return self.LoadU32(self.CapacityOffset())

    def Size(self):
        return self.SizeFor(self.capacity)


class StringTable(Struct):
    _typeName = 'v8::internal::StringTable'
    
    class Data(Struct):
        _typeName = 'v8::internal::StringTable::Data'
        
        @property
        def capacity(self):
            return int(self['capacity_'])

        @property
        def number_of_elements(self):
            return int(self['number_of_elements_'])

        @property
        def previous_data(self):
            return StringTable.Data(self['previous_data_']._unsigned)

        def GetElement(self, index):
            assert index <= self.capacity
            return self['elements_'][index]

    @property
    def data(self):
        return StringTable.Data(self['data_']._unsigned) 

    def Iterate(self, v):
        data = self.data
        first = data.GetElement(0).address
        last = data.GetElement(data.capacity).address
        v.VisitRootPointers(Root.kStringTable, None, first, last)

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

from .struct import (
    Isolate,
)

from .object import (
    Object,
    String,
    Smi,
)
