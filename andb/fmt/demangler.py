# encoding:utf-8


name = "itanium_demangler"

"""
This module implements a C++ Itanium ABI demangler.

The demangler provides a single entry point, `demangle`, and returns either `None`
or an abstract syntax tree. All nodes have, at least, a `kind` field.

Name nodes:
    * `name`: `node.value` (`str`) holds an unqualified name
    * `ctor`: `node.value` is one of `"complete"`, `"base"`, or `"allocating"`, specifying
      the type of constructor
    * `dtor`: `node.value` is one of `"deleting"`, `"complete"`, or `"base"`, specifying
      the type of destructor
    * `oper`: `node.value` (`str`) holds a symbolic operator name, without the keyword
      "operator"
    * `oper_cast`: `node.value` holds a type node
    * `tpl_args`: `node.value` (`tuple`) holds a sequence of type nodes
    * `qual_name`: `node.value` (`tuple`) holds a sequence of `name` and `tpl_args` nodes,
      possibly ending in a `ctor`, `dtor` or `operator` node
    * `abi`: `node.value` holds a name node, `node.qual` (`frozenset`) holds a set of ABI tags

Type nodes:
    * `name` and `qual_name` specify a type by its name
    * `builtin`: `node.value` (`str`) specifies a builtin type by its name
    * `pointer`, `lvalue` and `rvalue`: `node.value` holds a pointee type node
    * `cv_qual`: `node.value` holds a type node, `node.qual` (`frozenset`) is any of
      `"const"`, `"volatile"`, or `"restrict"`
    * `literal`: `node.value` (`str`) holds the literal representation as-is,
      `node.ty` holds a type node specifying the type of the literal
    * `function`: `node.name` holds a name node specifying the function name,
      `node.ret_ty` holds a type node specifying the return type of a template function,
      if any, or `None`, ``node.arg_tys` (`tuple`) holds a sequence of type nodes
      specifying thefunction arguments

Special nodes:
    * `vtable`, `vtt`, `typeinfo`, and `typeinfo_name`: `node.value` holds a type node
      specifying the type described by this RTTI data structure
    * `nonvirt_thunk`, `virt_thunk`: `node.value` holds a function node specifying
      the function to which the thunk dispatches

https://github.com/whitequark/python-itanium_demangler
"""

import re
from collections import namedtuple


class _Cursor:
    def __init__(self, raw, pos=0):
        self._raw = raw
        self._pos = pos
        self._substs = {}

    def at_end(self):
        return self._pos == len(self._raw)

    def accept(self, delim):
        if self._raw[self._pos:self._pos + len(delim)] == delim:
            self._pos += len(delim)
            return True

    def advance(self, amount):
        if self._pos + amount > len(self._raw):
            return None
        result = self._raw[self._pos:self._pos + amount]
        self._pos += amount
        return result

    def advance_until(self, delim):
        new_pos = self._raw.find(delim, self._pos)
        if new_pos == -1:
            return None
        result = self._raw[self._pos:new_pos]
        self._pos = new_pos + len(delim)
        return result

    def match(self, pattern):
        match = pattern.match(self._raw, self._pos)
        if match:
            self._pos = match.end(0)
        return match

    def add_subst(self, node):
        # print("S[{}] = {}".format(len(self._substs), str(node)))
        if not node in self._substs.values():
            self._substs[len(self._substs)] = node

    def resolve_subst(self, seq_id):
        if seq_id in self._substs:
            return self._substs[seq_id]

    def __repr__(self):
        return "_Cursor({}, {})".format(self._raw[:self._pos] + '→' + self._raw[self._pos:],
                                        self._pos)


class Node(namedtuple('Node', 'kind value')):
    def __repr__(self):
        return "<Node {} {}>".format(self.kind, repr(self.value))

    def __str__(self):
        if self.kind in ('name', 'builtin'):
            return self.value
        elif self.kind == 'qual_name':
            result = ''
            for node in self.value:
                if result != '' and node.kind != 'tpl_args':
                    result += '::'
                result += str(node)
            return result
        elif self.kind == 'tpl_args':
            return '<' + ', '.join(map(str, self.value)) + '>'
        elif self.kind == 'ctor':
            if self.value == 'complete':
                return '{ctor}'
            elif self.value == 'base':
                return '{base ctor}'
            elif self.value == 'allocating':
                return '{allocating ctor}'
            else:
                assert False
        elif self.kind == 'dtor':
            if self.value == 'deleting':
                return '{deleting dtor}'
            elif self.value == 'complete':
                return '{dtor}'
            elif self.value == 'base':
                return '{base dtor}'
            else:
                assert False
        elif self.kind == 'oper':
            if self.value.startswith('new') or self.value.startswith('delete'):
                return 'operator ' + self.value
            else:
                return 'operator' + self.value
        elif self.kind == 'oper_cast':
            return 'operator ' + str(self.value)
        elif self.kind == 'pointer':
            return self.value.left() + '*' + self.value.right()
        elif self.kind == 'lvalue':
            return self.value.left() + '&' + self.value.right()
        elif self.kind == 'rvalue':
            return self.value.left() + '&&' + self.value.right()
        elif self.kind == 'tpl_param':
            return '{T' + str(self.value) + '}'
        elif self.kind == 'subst':
            return '{S' + str(self.value) + '}'
        elif self.kind == 'vtable':
            return 'vtable for ' + str(self.value)
        elif self.kind == 'vtt':
            return 'vtt for ' + str(self.value)
        elif self.kind == 'typeinfo':
            return 'typeinfo for ' + str(self.value)
        elif self.kind == 'typeinfo_name':
            return 'typeinfo name for ' + str(self.value)
        elif self.kind == 'nonvirt_thunk':
            return 'non-virtual thunk for ' + str(self.value)
        elif self.kind == 'virt_thunk':
            return 'virtual thunk for ' + str(self.value)
        elif self.kind == 'guard_variable':
            return 'guard variable for ' + str(self.value)
        elif self.kind == 'transaction_clone':
            return 'transaction clone for ' + str(self.value)
        else:
            return repr(self)

    def left(self):
        if self.kind == "pointer":
            return self.value.left() + "*"
        elif self.kind == "lvalue":
            return self.value.left() + "&"
        elif self.kind == "rvalue":
            return self.value.left() + "&&"
        else:
            return str(self)

    def right(self):
        if self.kind in ("pointer", "lvalue", "rvalue"):
            return self.value.right()
        else:
            return ""

    def map(self, f):
        if self.kind in ('oper_cast', 'pointer', 'lvalue', 'rvalue', 'expand_arg_pack',
                         'vtable', 'vtt', 'typeinfo', 'typeinfo_name'):
            return self._replace(value=f(self.value))
        elif self.kind in ('qual_name', 'tpl_args', 'tpl_arg_pack'):
            return self._replace(value=tuple(map(f, self.value)))
        else:
            return self


class QualNode(namedtuple('QualNode', 'kind value qual')):
    def __repr__(self):
        return "<QualNode {} {} {}>".format(self.kind, repr(self.qual), repr(self.value))

    def __str__(self):
        if self.kind == 'abi':
            return str(self.value) + "".join(['[abi:' + tag + ']' for tag in self.qual])
        elif self.kind == 'cv_qual':
            return ' '.join([str(self.value)] + list(self.qual))
        else:
            return repr(self)

    def left(self):
        return str(self)

    def right(self):
        return ""

    def map(self, f):
        if self.kind == 'cv_qual':
            return self._replace(value=f(self.value))
        else:
            return self


class CastNode(namedtuple('CastNode', 'kind value ty')):
    def __repr__(self):
        return "<CastNode {} {} {}>".format(self.kind, repr(self.ty), repr(self.value))

    def __str__(self):
        if self.kind == 'literal':
            return '(' + str(self.ty) + ')' + str(self.value)
        else:
            return repr(self)

    def left(self):
        return str(self)

    def right(self):
        return ""

    def map(self, f):
        if self.kind == 'literal':
            return self._replace(ty=f(self.ty))
        else:
            return self


class FuncNode(namedtuple('FuncNode', 'kind name arg_tys ret_ty')):
    def __repr__(self):
        return "<FuncNode {} {} {} {}>".format(self.kind, repr(self.name),
                                               repr(self.arg_tys), repr(self.ret_ty))

    def __str__(self):
        if self.kind == 'func':
            result = ""
            if self.ret_ty is not None:
                result += str(self.ret_ty) + ' '
            if self.name is not None:
                result += str(self.name)
            if self.arg_tys == (Node('builtin', 'void'),):
                result += '()'
            else:
                result += '(' + ', '.join(map(str, self.arg_tys)) + ')'
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'func':
            result = ""
            if self.ret_ty is not None:
                result += str(self.ret_ty) + ' '
            result += "("
            if self.name is not None:
                result += str(self.name)
            return result
        else:
            return str(self)

    def right(self):
        if self.kind == 'func':
            result = ")"
            if self.arg_tys == (Node('builtin', 'void'),):
                result += '()'
            else:
                result += '(' + ', '.join(map(str, self.arg_tys)) + ')'
            return result
        else:
            return ""

    def map(self, f):
        if self.kind == 'func':
            return self._replace(name=f(self.name) if self.name else None,
                                 arg_tys=tuple(map(f, self.arg_tys)),
                                 ret_ty=f(self.ret_ty) if self.ret_ty else None)
        else:
            return self


class ArrayNode(namedtuple('ArrayNode', 'kind dimension ty')):
    def __repr__(self):
        return "<ArrayNode {} {} {}>".format(self.kind, repr(self.dimension), repr(self.ty))

    def __str__(self):
        if self.kind == 'array':
            result = ""
            result += str(self.ty)
            result += "[" + str(self.dimension) + "]"
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'array':
            result = str(self.ty) + "("
            return result
        else:
            return str(self)

    def right(self):
        if self.kind == 'array':
            result = ")[" + str(self.dimension) + "]"
            return result
        else:
            return ""

    def map(self, f):
        if self.kind == 'array':
            return self._replace(dimension=f(self.dimension) if self.dimension else None,
                                 ty=f(self.ty) if self.ty else None)
        else:
            return self


class MemberNode(namedtuple('MemberNode', 'kind cls_ty member_ty')):
    def __repr__(self):
        return "<MemberNode {} {} {}>".format(self.kind, repr(self.cls_ty), repr(self.member_ty))

    def __str__(self):
        if self.kind == 'data':
            result = str(self.member_ty) + " " + str(self.cls_ty) + "::*"
            return result
        elif self.kind == 'method':
            result = self.member_ty.left() + str(self.cls_ty) + "::*" + self.member_ty.right()
            return result
        else:
            return repr(self)

    def left(self):
        if self.kind == 'method':
            return self.member_ty.left() + str(self.cls_ty) + "::*"
        else:
            return str(self)

    def right(self):
        if self.kind == 'method':
            return self.member_ty.right()
        else:
            return ""

    def map(self, f):
        if self.kind in ('data', 'func'):
            return self._replace(cls_ty=f(self.cls_ty) if self.cls_ty else None,
                                 member_ty=f(self.member_ty) if self.member_ty else None)
        else:
            return self


_ctor_dtor_map = {
    'C1': 'complete',
    'C2': 'base',
    'C3': 'allocating',
    'D0': 'deleting',
    'D1': 'complete',
    'D2': 'base'
}

_std_names = {
    'St': [Node('name', 'std')],
    'Sa': [Node('name', 'std'), Node('name', 'allocator')],
    'Sb': [Node('name', 'std'), Node('name', 'basic_string')],
    'Ss': [Node('name', 'std'), Node('name', 'string')],
    'Si': [Node('name', 'std'), Node('name', 'istream')],
    'So': [Node('name', 'std'), Node('name', 'ostream')],
    'Sd': [Node('name', 'std'), Node('name', 'iostream')],
}

_operators = {
    'nw': 'new',
    'na': 'new[]',
    'dl': 'delete',
    'da': 'delete[]',
    'ps': '+', # (unary)
    'ng': '-', # (unary)
    'ad': '&', # (unary)
    'de': '*', # (unary)
    'co': '~',
    'pl': '+',
    'mi': '-',
    'ml': '*',
    'dv': '/',
    'rm': '%',
    'an': '&',
    'or': '|',
    'eo': '^',
    'aS': '=',
    'pL': '+=',
    'mI': '-=',
    'mL': '*=',
    'dV': '/=',
    'rM': '%=',
    'aN': '&=',
    'oR': '|=',
    'eO': '^=',
    'ls': '<<',
    'rs': '>>',
    'lS': '<<=',
    'rS': '>>=',
    'eq': '==',
    'ne': '!=',
    'lt': '<',
    'gt': '>',
    'le': '<=',
    'ge': '>=',
    'nt': '!',
    'aa': '&&',
    'oo': '||',
    'pp': '++', # (postfix in <expression> context)
    'mm': '--', # (postfix in <expression> context)
    'cm': ',',
    'pm': '->*',
    'pt': '->',
    'cl': '()',
    'ix': '[]',
    'qu': '?',
}

_builtin_types = {
    'v':  Node('builtin', 'void'),
    'w':  Node('builtin', 'wchar_t'),
    'b':  Node('builtin', 'bool'),
    'c':  Node('builtin', 'char'),
    'a':  Node('builtin', 'signed char'),
    'h':  Node('builtin', 'unsigned char'),
    's':  Node('builtin', 'short'),
    't':  Node('builtin', 'unsigned short'),
    'i':  Node('builtin', 'int'),
    'j':  Node('builtin', 'unsigned int'),
    'l':  Node('builtin', 'long'),
    'm':  Node('builtin', 'unsigned long'),
    'x':  Node('builtin', 'long long'),
    'y':  Node('builtin', 'unsigned long long'),
    'n':  Node('builtin', '__int128'),
    'o':  Node('builtin', 'unsigned __int128'),
    'f':  Node('builtin', 'float'),
    'd':  Node('builtin', 'double'),
    'e':  Node('builtin', '__float80'),
    'g':  Node('builtin', '__float128'),
    'z':  Node('builtin', '...'),
    'Dd': Node('builtin', '_Decimal64'),
    'De': Node('builtin', '_Decimal128'),
    'Df': Node('builtin', '_Decimal32'),
    'Dh': Node('builtin', '_Float16'),
    'Di': Node('builtin', 'char32_t'),
    'Ds': Node('builtin', 'char16_t'),
    'Da': Node('builtin', 'auto'),
    'Dn': Node('qual_name', (Node('name', 'std'), Node('builtin', 'nullptr_t')))
}


def _handle_cv(qualifiers, node):
    qualifier_set = set()
    if 'r' in qualifiers:
        qualifier_set.add('restrict')
    if 'V' in qualifiers:
        qualifier_set.add('volatile')
    if 'K' in qualifiers:
        qualifier_set.add('const')
    if qualifier_set:
        return QualNode('cv_qual', node, frozenset(qualifier_set))
    return node

def _handle_indirect(qualifier, node):
    if qualifier == 'P':
        return Node('pointer', node)
    elif qualifier == 'R':
        return Node('lvalue', node)
    elif qualifier == 'O':
        return Node('rvalue', node)
    return node


_NUMBER_RE = re.compile(r"\d+")

def _parse_number(cursor):
    match = cursor.match(_NUMBER_RE)
    if match is None:
        return None
    return int(match.group(0))

def _parse_seq_id(cursor):
    seq_id = cursor.advance_until('_')
    if seq_id is None:
        return None
    if seq_id == '':
        return 0
    else:
        return 1 + int(seq_id, 36)

def _parse_until_end(cursor, kind, fn):
    nodes = []
    while not cursor.accept('E'):
        node = fn(cursor)
        if node is None or cursor.at_end():
            return None
        nodes.append(node)
    return Node(kind, tuple(nodes))


_SOURCE_NAME_RE = re.compile(r"\d+")

def _parse_source_name(cursor):
    match = cursor.match(_SOURCE_NAME_RE)
    name_len = int(match.group(0))
    name = cursor.advance(name_len)
    if name is None:
        return None
    return name


_NAME_RE = re.compile(r"""
(?P<source_name>        (?= \d)) |
(?P<ctor_name>          C[123]) |
(?P<dtor_name>          D[012]) |
(?P<std_name>           S[absiod]) |
(?P<operator_name>      nw|na|dl|da|ps|ng|ad|de|co|pl|mi|ml|dv|rm|an|or|
                        eo|aS|pL|mI|mL|dV|rM|aN|oR|eO|ls|rs|lS|rS|eq|ne|
                        lt|gt|le|ge|nt|aa|oo|pp|mm|cm|pm|pt|cl|ix|qu) |
(?P<operator_cv>        cv) |
(?P<std_prefix>         St) |
(?P<substitution>       S) |
(?P<nested_name>        N (?P<cv_qual> [rVK]*) (?P<ref_qual> [RO]?)) |
(?P<template_param>     T) |
(?P<template_args>      I) |
(?P<constant>           L) |
(?P<local_name>         Z) |
(?P<unnamed_type>       Ut) |
(?P<closure_type>       Ul)
""", re.X)

def _parse_name(cursor, is_nested=False):
    match = cursor.match(_NAME_RE)
    if match is None:
        return None
    elif match.group('source_name') is not None:
        name = _parse_source_name(cursor)
        if name is None:
            return None
        node = Node('name', name)
    elif match.group('ctor_name') is not None:
        node = Node('ctor', _ctor_dtor_map[match.group('ctor_name')])
    elif match.group('dtor_name') is not None:
        node = Node('dtor', _ctor_dtor_map[match.group('dtor_name')])
    elif match.group('std_name') is not None:
        node = Node('qual_name', _std_names[match.group('std_name')])
    elif match.group('operator_name') is not None:
        node = Node('oper', _operators[match.group('operator_name')])
    elif match.group('operator_cv') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = Node('oper_cast', ty)
    elif match.group('std_prefix') is not None:
        name = _parse_name(cursor, is_nested=True)
        if name is None:
            return None
        if name.kind == 'qual_name':
            node = Node('qual_name', (Node('name', 'std'),) + name.value)
        else:
            node = Node('qual_name', (Node('name', 'std'), name))
    elif match.group('substitution') is not None:
        seq_id = _parse_seq_id(cursor)
        if seq_id is None:
            return None
        node = cursor.resolve_subst(seq_id)
        if node is None:
            return None
    elif match.group('nested_name') is not None:
        nodes = []
        while True:
            name = _parse_name(cursor, is_nested=True)
            if name is None or cursor.at_end():
                return None
            if name.kind == 'qual_name':
                nodes += name.value
            else:
                nodes.append(name)
            if cursor.accept('E'):
                break
            else:
                cursor.add_subst(Node('qual_name', tuple(nodes)))
        node = Node('qual_name', tuple(nodes))
        node = _handle_cv(match.group('cv_qual'), node)
        node = _handle_indirect(match.group('ref_qual'), node)
    elif match.group('template_param') is not None:
        seq_id = _parse_seq_id(cursor)
        if seq_id is None:
            return None
        node = Node('tpl_param', seq_id)
        cursor.add_subst(node)
    elif match.group('template_args') is not None:
        node = _parse_until_end(cursor, 'tpl_args', _parse_type)
    elif match.group('constant') is not None:
        # not in the ABI doc, but probably means `const`
        return _parse_name(cursor, is_nested)
    elif match.group('local_name') is not None:
        raise NotImplementedError("local names are not supported")
    elif match.group('unnamed_type') is not None:
        raise NotImplementedError("unnamed types are not supported")
    elif match.group('closure_type') is not None:
        raise NotImplementedError("closure (lambda) types are not supported")
    if node is None:
        return None

    abi_tags = []
    while cursor.accept('B'):
        abi_tags.append(_parse_source_name(cursor))
    if abi_tags:
        node = QualNode('abi', node, frozenset(abi_tags))

    if not is_nested and cursor.accept('I') and (
            node.kind in ('name', 'oper', 'oper_cast') or
            match.group('std_prefix') is not None or
            match.group('std_name') is not None or
            match.group('substitution') is not None):
        if node.kind in ('name', 'oper', 'oper_cast') or match.group('std_prefix') is not None:
            cursor.add_subst(node) # <unscoped-template-name> ::= <substitution>
        templ_args = _parse_until_end(cursor, 'tpl_args', _parse_type)
        if templ_args is None:
            return None
        node = Node('qual_name', (node, templ_args))
        if ((match.group('std_prefix') is not None or
                match.group('std_name') is not None) and
                node.value[0].value[1].kind not in ('oper', 'oper_cast')):
            cursor.add_subst(node)

    return node


_TYPE_RE = re.compile(r"""
(?P<builtin_type>       v|w|b|c|a|h|s|t|i|j|l|m|x|y|n|o|f|d|e|g|z|
                        Dd|De|Df|Dh|DF|Di|Ds|Da|Dc|Dn) |
(?P<qualified_type>     [rVK]+) |
(?P<indirect_type>      [PRO]) |
(?P<function_type>      F) |
(?P<expression>         X) |
(?P<expr_primary>       (?= L)) |
(?P<template_arg_pack>  J) |
(?P<arg_pack_expansion> Dp) |
(?P<decltype>           D[tT]) |
(?P<array_type>         A) |
(?P<member_type>        M)
""", re.X)

def _parse_type(cursor):
    match = cursor.match(_TYPE_RE)
    if match is None:
        node = _parse_name(cursor)
        cursor.add_subst(node)
    elif match.group('builtin_type') is not None:
        node = _builtin_types[match.group('builtin_type')]
    elif match.group('qualified_type') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = _handle_cv(match.group('qualified_type'), ty)
        cursor.add_subst(node)
    elif match.group('indirect_type') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        node = _handle_indirect(match.group('indirect_type'), ty)
        cursor.add_subst(node)
    elif match.group('function_type') is not None:
        ret_ty = _parse_type(cursor)
        if ret_ty is None:
            return None
        arg_tys = []
        while not cursor.accept('E'):
            arg_ty = _parse_type(cursor)
            if arg_ty is None:
                return None
            arg_tys.append(arg_ty)
        node = FuncNode('func', None, tuple(arg_tys), ret_ty)
        cursor.add_subst(node)
    elif match.group('expression') is not None:
        raise NotImplementedError("expressions are not supported")
    elif match.group('expr_primary') is not None:
        node = _parse_expr_primary(cursor)
    elif match.group('template_arg_pack') is not None:
        node = _parse_until_end(cursor, 'tpl_arg_pack', _parse_type)
    elif match.group('arg_pack_expansion') is not None:
        node = _parse_type(cursor)
        node = Node('expand_arg_pack', node)
    elif match.group('decltype') is not None:
        raise NotImplementedError("decltype is not supported")
    elif match.group('array_type') is not None:
        dimension = _parse_number(cursor)
        if dimension is None:
            return None
        else:
            dimension = CastNode('literal', dimension, Node('builtin', 'int'))
        if not cursor.accept('_'):
            return None
        type = _parse_type(cursor)
        node = ArrayNode('array', dimension, type)
        cursor.add_subst(node)
    elif match.group('member_type') is not None:
        cls_ty = _parse_type(cursor)
        member_ty = _parse_type(cursor)
        if member_ty.kind == 'func':
            kind = "method"
        else:
            kind = "data"
        node = MemberNode(kind, cls_ty, member_ty)
    else:
        return None
    return node


_EXPR_PRIMARY_RE = re.compile(r"""
(?P<mangled_name>       L (?= _Z)) |
(?P<literal>            L)
""", re.X)

def _parse_expr_primary(cursor):
    match = cursor.match(_EXPR_PRIMARY_RE)
    if match is None:
        return None
    elif match.group('mangled_name') is not None:
        mangled_name = cursor.advance_until('E')
        return _parse_mangled_name(_Cursor(mangled_name))
    elif match.group('literal') is not None:
        ty = _parse_type(cursor)
        if ty is None:
            return None
        value = cursor.advance_until('E')
        if value is None:
            return None
        return CastNode('literal', value, ty)


def _expand_template_args(func):
    if func.name.kind == 'qual_name':
        name_suffix = func.name.value[-1]
        if name_suffix.kind == 'tpl_args':
            tpl_args = name_suffix.value
            def mapper(node):
                if node.kind == 'tpl_param' and node.value < len(tpl_args):
                    return tpl_args[node.value]
                return node.map(mapper)
            return mapper(func)
    return func

def _parse_encoding(cursor):
    name = _parse_name(cursor)
    if name is None:
        return None
    if cursor.at_end():
        return name

    if name.kind == 'qual_name' \
            and name.value[-1].kind == 'tpl_args' \
            and name.value[-2].kind not in ('ctor', 'dtor', 'oper_cast'):
        ret_ty = _parse_type(cursor)
        if ret_ty is None:
            return None
    else:
        ret_ty = None

    arg_tys = []
    while not cursor.at_end():
        arg_ty = _parse_type(cursor)
        if arg_ty is None:
            return None
        arg_tys.append(arg_ty)

    if arg_tys:
        func = FuncNode('func', name, tuple(arg_tys), ret_ty)
        return _expand_template_args(func)
    else:
        return name


_SPECIAL_RE = re.compile(r"""
(?P<rtti>               T (?P<kind> [VTIS])) |
(?P<nonvirtual_thunk>   Th (?P<nv_offset> n? \d+) _) |
(?P<virtual_thunk>      Tv (?P<v_offset> n? \d+) _ (?P<vcall_offset> n? \d+) _) |
(?P<covariant_thunk>    Tc) |
(?P<guard_variable>     GV) |
(?P<extended_temporary> GR) |
(?P<transaction_clone>  GTt)
""", re.X)

def _parse_special(cursor):
    match = cursor.match(_SPECIAL_RE)
    if match is None:
        return None
    elif match.group('rtti') is not None:
        name = _parse_type(cursor)
        if name is None:
            return None
        if match.group('kind') == 'V':
            return Node('vtable', name)
        elif match.group('kind') == 'T':
            return Node('vtt', name)
        elif match.group('kind') == 'I':
            return Node('typeinfo', name)
        elif match.group('kind') == 'S':
            return Node('typeinfo_name', name)
    elif match.group('nonvirtual_thunk') is not None:
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('nonvirt_thunk', func)
    elif match.group('virtual_thunk') is not None:
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('virt_thunk', func)
    elif match.group('covariant_thunk') is not None:
        raise NotImplementedError("covariant thunks are not supported")
    elif match.group('guard_variable'):
        name = _parse_type(cursor)
        if name is None:
            return None
        return Node('guard_variable', name)
    elif match.group('extended_temporary'):
        raise NotImplementedError("extended temporaries are not supported")
    elif match.group('transaction_clone'):
        func = _parse_encoding(cursor)
        if func is None:
            return None
        return Node('transaction_clone', func)


_MANGLED_NAME_RE = re.compile(r"""
(?P<mangled_name>       _?_Z)
""", re.X)

def _parse_mangled_name(cursor):
    match = cursor.match(_MANGLED_NAME_RE)
    if match is None:
        return None
    else:
        special = _parse_special(cursor)
        if special is not None:
            return special

        return _parse_encoding(cursor)


def _expand_arg_packs(ast):
    def mapper(node):
        if node.kind == 'tpl_args':
            exp_args = []
            for arg in node.value:
                if arg.kind in ['tpl_arg_pack', 'tpl_args']:
                    exp_args += arg.value
                else:
                    exp_args.append(arg)
            return Node('tpl_args', tuple(map(mapper, exp_args)))
        elif node.kind == 'func':
            node = node.map(mapper)
            exp_arg_tys = []
            for arg_ty in node.arg_tys:
                if arg_ty.kind == 'expand_arg_pack' and \
                        arg_ty.value.kind == 'rvalue' and \
                            arg_ty.value.value.kind in ['tpl_arg_pack', 'tpl_args']:
                    exp_arg_tys += arg_ty.value.value.value
                else:
                    exp_arg_tys.append(arg_ty)
            return node._replace(arg_tys=tuple(exp_arg_tys))
        else:
            return node.map(mapper)
    return mapper(ast)

def parse(raw):
    ast = _parse_mangled_name(_Cursor(raw))
    if ast is not None:
        ast = _expand_arg_packs(ast)
    return ast

def is_ctor_or_dtor(ast):
    if ast.kind == 'func':
        return _is_ctor_or_dtor(ast.name)
    elif ast.kind == 'qual_name':
        kind = ast.value[-1].kind
        return kind == 'ctor' or kind == 'dtor'
    else:
       return False

# ================================================================================================


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        while True:
            name = sys.stdin.readline()
            if not name:
                break
            print(parse(name.strip()))
    else:
        for name in sys.argv[1:]:
            ast = parse(name)
            print(repr(ast))
            print(ast)
