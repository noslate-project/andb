# -*- coding: UTF-8 -*-
from __future__ import print_function, division

import re

#from functools import wraps
from andb.utility import Logging as log, oneshot, CachedProperty
#from andb.errors import AndbError as err

import andb.dbg as dbg
from .internal import (
    Internal,
    Struct,
    Value,
    Enum,
    AutoLayout,
    ObjectSlot,
    ObjectSlots,
    ALStruct,
    BitField,
    Version
)
from .enum import (
    ElementsKind,
    InstanceType,
)

import andb.py23 as py23


class CommonFrameConstants(Value):
    _typeName = 'v8::internal::CommonFrameConstants'

    """
    //  slot      JS frame
    //       +-----------------+--------------------------------
    //  -n-1 |   parameter n   |                            ^
    //       |- - - - - - - - -|                            |
    //  -n   |  parameter n-1  |                          Caller
    //  ...  |       ...       |                       frame slots
    //  -2   |   parameter 1   |                       (slot < 0)
    //       |- - - - - - - - -|                            |
    //  -1   |   parameter 0   |                            v
    //  -----+-----------------+--------------------------------
    //   0   |   return addr   |   ^                        ^
    //       |- - - - - - - - -|   |                        |
    //   1   | saved frame ptr | Fixed                      |
    //       |- - - - - - - - -| Header <-- frame ptr       |
    //   2   | [Constant Pool] |   |                        |
    //       |- - - - - - - - -|   |                        |
    // 2+cp  |Context/Frm. Type|   v   if a constant pool   |
    //       |-----------------+----    is used, cp = 1,    |
    // 3+cp  |                 |   ^   otherwise, cp = 0    |
    //       |- - - - - - - - -|   |                        |
    // 4+cp  |                 |   |                      Callee
    //       |- - - - - - - - -|   |                   frame slots
    //  ...  |                 | Frame slots           (slot >= 0)
    //       |- - - - - - - - -|   |                        |
    //       |                 |   v                        |
    //  -----+-----------------+----- <-- stack ptr -------------
    //
    """

    kCallerFPOffset = 0 
    kCallerPCOffset = 8 
    kCallerSPOffset = 16 
    kContextOrFrameTypeOffset = -8 

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "caller_fp", "type": int, "offset": cls.kCallerFPOffset},
            {"name": "caller_pc", "type": int, "offset": cls.kCallerPCOffset},
            {"name": "caller_sp", "type": int, "offset": cls.kCallerSPOffset},
            {"name": "context_or_frame_type", "type": Object, "offset": cls.kContextOrFrameTypeOffset},
        ]}


class StandardFrameConstants(CommonFrameConstants):
    _typeName = 'v8::internal::StandardFrameConstants'

    """
    // StandardFrames are used for both unoptimized and optimized JavaScript
    // frames. They always have a context below the saved fp/constant
    // pool, below that the JSFunction of the executing function and below that an
    // integer (not a Smi) containing the actual number of arguments passed to the
    // JavaScript code.
    //
    //  slot      JS frame
    //       +-----------------+--------------------------------
    //  -n-1 |   parameter 0   |                            ^
    //       |- - - - - - - - -|                            |
    //  -n   |                 |                          Caller
    //  ...  |       ...       |                       frame slots
    //  -2   |  parameter n-1  |                       (slot < 0)
    //       |- - - - - - - - -|                            |
    //  -1   |   parameter n   |                            v
    //  -----+-----------------+--------------------------------
    //   0   |   return addr   |   ^                        ^
    //       |- - - - - - - - -|   |                        |
    //   1   | saved frame ptr | Fixed                      |
    //       |- - - - - - - - -| Header <-- frame ptr       |
    //   2   | [Constant Pool] |   |                        |
    //       |- - - - - - - - -|   |                        |
    // 2+cp  |     Context     |   |   if a constant pool   |
    //       |- - - - - - - - -|   |    is used, cp = 1,    |
    // 3+cp  |    JSFunction   |   v   otherwise, cp = 0    |
    //       +-----------------+----                        |
    // 4+cp  |                 |   ^                      Callee
    //       |- - - - - - - - -|   |                   frame slots
    //  ...  |                 | Frame slots           (slot >= 0)
    //       |- - - - - - - - -|   |                        |
    //       |                 |   v                        |
    //  -----+-----------------+----- <-- stack ptr -------------
    """

    kFunctionOffset = -16
    kExpressionsOffset = -24

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "function", "type": JSFunction, "offset": cls.kFunctionOffset},
            {"name": "expressions", "type": Object, "offset": cls.kExpressionsOffset},
        ]}


class StackFrameType(Enum):
    _typeName = 'v8::internal::StackFrame::Type'


def MarkerType(cls):
    """ Stack Frame uses Marker for frame_type storage.
        A frame_type Marker is used in TypedFrameConstants, 
        from frame_type left shift a kSmiTag.
    """ 
    def Wrap(val):
        return cls(val >> 1)
    return Wrap


class TypedFrameConstants(CommonFrameConstants):
    _typeName = 'v8::internal::TypedFrameConstants'

    """
    // TypedFrames have a type maker value below the saved FP/constant pool to
    // distinguish them from StandardFrames, which have a context in that position
    // instead.
    //
    //  slot      JS frame
    //       +-----------------+--------------------------------
    //  -n-1 |   parameter n   |                            ^
    //       |- - - - - - - - -|                            |
    //  -n   |  parameter n-1  |                          Caller
    //  ...  |       ...       |                       frame slots
    //  -2   |   parameter 1   |                       (slot < 0)
    //       |- - - - - - - - -|                            |
    //  -1   |   parameter 0   |                            v
    //  -----+-----------------+--------------------------------
    //   0   |   return addr   |   ^                        ^
    //       |- - - - - - - - -|   |                        |
    //   1   | saved frame ptr | Fixed                      |
    //       |- - - - - - - - -| Header <-- frame ptr       |
    //   2   | [Constant Pool] |   |                        |
    //       |- - - - - - - - -|   |                        |
    // 2+cp  |Frame Type Marker|   v   if a constant pool   |
    //       |-----------------+----    is used, cp = 1,    |
    // 3+cp  |  pushed value 0 |   ^   otherwise, cp = 0    |
    //       |- - - - - - - - -|   |                        |
    // 4+cp  |  pushed value 1 |   |                      Callee
    //       |- - - - - - - - -|   |                   frame slots
    //  ...  |                 | Frame slots           (slot >= 0)
    //       |- - - - - - - - -|   |                        |
    //       |                 |   v                        |
    //  -----+-----------------+----- <-- stack ptr -------------
    """

    kFrameTypeOffset = -8 

    @classmethod
    def __autoLayout(cls):
        return {"layout": [
            {"name": "frame_type", "type": MarkerType(StackFrameType), "offset": cls.kFrameTypeOffset},
        ]}


class StackFrame(dbg.Frame):
    """ represents a Frame on Stack.
    """
    _typeName = None

    # decoded
    _context_or_frame_type = None

    def __init__(self, frame):
        if isinstance(frame, dbg.Frame):
            dbg.Frame.__init__(self, frame)
            self._address = frame.GetFP()
        elif isinstance(frame, StackFrame):
            self._I_frame = frame._I_frame
            self._address = frame._address
            self._context_or_frame_type = frame._context_or_frame_type

    def ParseTypedFrame(self):
        frame = TypedFrame(self)
        return frame.Parse(self._context_or_frame_type)

    def ParseStandardFrame(self):
        frame = StandardFrame(self)
        return frame.Parse(self._context_or_frame_type)

    def Parse(self):
        if self._address == 0:
            return None
 
        if not self.MightBeV8Frame():
            return None
       
        # get context or marker
        frame = CommonFrameConstants(self._address)
        context_or_frame_type = frame.context_or_frame_type
        self._context_or_frame_type = context_or_frame_type

        # a smi should be the marker
        if context_or_frame_type.IsSmi():
            return self.ParseTypedFrame()

        # otherwise maybe a v8 frame.
        context = Context(context_or_frame_type)
        if context.IsContext():
            return self.ParseStandardFrame()
        
        return None

    def MightBeV8Frame(self):
        name = self.GetFunctionName()
        if name is None:
            return True
        elif name.startswith('Builtins_'):
            return True
        return False


class StandardFrame(StackFrame, StandardFrameConstants):
    """ Standard javascript frame.
    """
    _typeName = None

    def __init__(self, frame):
        StackFrame.__init__(self, frame)
        StandardFrameConstants.__init__(self, frame)
        self._context = frame._context_or_frame_type

    def Parse(self, context):
        fn = self.function
        if fn.IsJSFunction():
            frame = JavaScriptFrame(self)
            return frame.Parse(fn)
        return None

    def GetParameter(self, index):
        off = self.GetParameterOffset(index)
        return Object(self.LoadPtr(off))

    def GetParameterOffset(self, index):
        fn = self._function
        param_count = fn.shared_function_info.parameter_count
        assert -1 <= index < param_count
        offset = (param_count - index - 1) * Internal.kSystemPointerSize
        return self.caller_sp__offset + offset

class TypedFrame(StackFrame, TypedFrameConstants):
    
    _typeName = None

    def __init__(self, frame):
        StackFrame.__init__(self, frame)
        TypedFrameConstants.__init__(self, frame)
        #self._frame_type = StackFrameType(frame._context_or_frame_type)

    def Parse(self, frame_type):
        return self 

    def GetArgs(self):
        return []

    def GetFunctionName(self):
        return "<%s>" % (self.frame_type.name.lower())

    def GetLocals(self):
        return []

    def GetPosition(self):
        return (None, None) 

class JavaScriptFrame(StandardFrame):
    """ class for read js frame on stack.
    """

    _functon = None
    _context = None

    @CachedProperty
    def receiver(self):
        p = self.GetParameter(-1)  
        return p

    @CachedProperty
    def script(self):
        fn = self._function
        script = Script(fn.shared_function_info.script_or_debug_info)
        return script 

    def GetArgAt(self, index):
        p = self.GetParameter(index)
        return Object(p)

    def GetArgs(self):
        args = []
        
        receiver = self.receiver
        args.append(dbg.Symval("this", str(receiver)))
       
        fn = self._function
        argc = fn.shared_function_info.parameter_count
        for i in range(argc):
            x = self.GetArgAt(i)
            args.append(dbg.Symval("arg%d"%i, str(x)))
        return args

    def Parse(self, func):
        self._function = func

        return self

    def GetFunctionName(self):
        fn = self._function
        if not fn:
            return None
        return fn.FunctionName()

    def GetLocals(self):
        return [] 
    
    def GetPosition(self):
        script = self.script
        filename = str(script.name)
        # TBD: implement slow GetPositionInfo
        fileline = int(script.line_offset)
        return (filename, fileline) 

    def Stringify(self):
        pass

    def __str__(self):
        return "0x%x %s()" % (
            self._frame.GetPC(),
            self.function_name
        )


""" Tail import
"""
from .object import (
    Object,
    HeapObject,
    SmiTagged,
    JSFunction,
    Context,
    Script,
)

