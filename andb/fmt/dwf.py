
from __future__ import print_function, division

from mmap import mmap, ACCESS_READ, ACCESS_WRITE, PAGESIZE
import struct
from andb.utility import profiler

class Enum(object):
   
    @classmethod
    def Name(cls, num):
        for i in dir(cls):
            v = getattr(cls, i)
            if isinstance(v, int):
                if v == num:
                    return i
        return "unknown(0x%x)" % num

""" const definition begin
"""

DW_CHILDREN_no = 0
DW_CHILDREN_yes = 1

class TAG(Enum):
    DW_TAG_array_type = 0x0001
    DW_TAG_class_type = 0x0002
    DW_TAG_entry_point = 0x0003
    DW_TAG_enumeration_type = 0x0004
    DW_TAG_formal_parameter = 0x0005
    DW_TAG_imported_declaration = 0x0008
    DW_TAG_label = 0x000A
    DW_TAG_lexical_block = 0x000B
    DW_TAG_member = 0x000D
    DW_TAG_pointer_type = 0x000F
    DW_TAG_reference_type = 0x0010
    DW_TAG_compile_unit = 0x0011
    DW_TAG_string_type = 0x0012
    DW_TAG_structure_type = 0x0013
    DW_TAG_subroutine_type = 0x0015
    DW_TAG_typedef = 0x0016
    DW_TAG_union_type = 0x0017
    DW_TAG_unspecified_parameters = 0x0018
    DW_TAG_variant = 0x0019
    DW_TAG_common_block = 0x001A
    DW_TAG_common_inclusion = 0x001B
    DW_TAG_inheritance = 0x001C
    DW_TAG_inlined_subroutine = 0x001D
    DW_TAG_module = 0x001E
    DW_TAG_ptr_to_member_type = 0x001F
    DW_TAG_set_type = 0x0020
    DW_TAG_subrange_type = 0x0021
    DW_TAG_with_stmt = 0x0022
    DW_TAG_access_declaration = 0x0023
    DW_TAG_base_type = 0x0024
    DW_TAG_catch_block = 0x0025
    DW_TAG_const_type = 0x0026
    DW_TAG_constant = 0x0027
    DW_TAG_enumerator = 0x0028
    DW_TAG_file_type = 0x0029
    DW_TAG_friend = 0x002A
    DW_TAG_namelist = 0x002B
    DW_TAG_namelist_item = 0x002C
    DW_TAG_packed_type = 0x002D
    DW_TAG_subprogram = 0x002E
    DW_TAG_template_type_parameter = 0x002F
    DW_TAG_template_value_parameter = 0x0030
    DW_TAG_thrown_type = 0x0031
    DW_TAG_try_block = 0x0032
    DW_TAG_variant_part = 0x0033
    DW_TAG_variable = 0x0034
    DW_TAG_volatile_type = 0x0035
    DW_TAG_dwarf_procedure = 0x0036
    DW_TAG_restrict_type = 0x0037
    DW_TAG_interface_type = 0x0038
    DW_TAG_namespace = 0x0039
    DW_TAG_imported_module = 0x003A
    DW_TAG_unspecified_type = 0x003B
    DW_TAG_partial_unit = 0x003C
    DW_TAG_imported_unit = 0x003D
    DW_TAG_condition = 0x003F
    DW_TAG_shared_type = 0x0040
    DW_TAG_type_unit = 0x0041
    DW_TAG_rvalue_reference_type = 0x0042
    DW_TAG_template_alias = 0x0043
    DW_TAG_MIPS_loop = 0x4081
    DW_TAG_format_label = 0x4101
    DW_TAG_function_template = 0x4102
    DW_TAG_class_template = 0x4103
    DW_TAG_GNU_template_template_param = 0x4106
    DW_TAG_GNU_template_parameter_pack = 0x4107
    DW_TAG_GNU_formal_parameter_pack = 0x4108
    DW_TAG_APPLE_Property = 0x4200

    DW_TAG_lo_user = 0x4080
    DW_TAG_hi_user = 0xFFFF

class AT(Enum):
    DW_AT_sibling = 0x0001
    DW_AT_location = 0x0002
    DW_AT_name = 0x0003
    DW_AT_ordering = 0x0009
    DW_AT_byte_size = 0x000B
    DW_AT_bit_offset = 0x000C
    DW_AT_bit_size = 0x000D
    DW_AT_stmt_list = 0x0010
    DW_AT_low_pc = 0x0011
    DW_AT_high_pc = 0x0012
    DW_AT_language = 0x0013
    DW_AT_discr = 0x0015
    DW_AT_discr_value = 0x0016
    DW_AT_visibility = 0x0017
    DW_AT_import = 0x0018
    DW_AT_string_length = 0x0019
    DW_AT_common_reference = 0x001A
    DW_AT_comp_dir = 0x001B
    DW_AT_const_value = 0x001C
    DW_AT_containing_type = 0x001D
    DW_AT_default_value = 0x001E
    DW_AT_inline = 0x0020
    DW_AT_is_optional = 0x0021
    DW_AT_lower_bound = 0x0022
    DW_AT_producer = 0x0025
    DW_AT_prototyped = 0x0027
    DW_AT_return_addr = 0x002A
    DW_AT_start_scope = 0x002C
    DW_AT_bit_stride = 0x002E
    DW_AT_upper_bound = 0x002F
    DW_AT_abstract_origin = 0x0031
    DW_AT_accessibility = 0x0032
    DW_AT_address_class = 0x0033
    DW_AT_artificial = 0x0034
    DW_AT_base_types = 0x0035
    DW_AT_calling_convention = 0x0036
    DW_AT_count = 0x0037
    DW_AT_data_member_location = 0x0038
    DW_AT_decl_column = 0x0039
    DW_AT_decl_file = 0x003A
    DW_AT_decl_line = 0x003B
    DW_AT_declaration = 0x003C
    DW_AT_discr_list = 0x003D
    DW_AT_encoding = 0x003E
    DW_AT_external = 0x003F
    DW_AT_frame_base = 0x0040
    DW_AT_friend = 0x0041
    DW_AT_identifier_case = 0x0042
    DW_AT_macro_info = 0x0043
    DW_AT_namelist_item = 0x0044
    DW_AT_priority = 0x0045
    DW_AT_segment = 0x0046
    DW_AT_specification = 0x0047
    DW_AT_static_link = 0x0048
    DW_AT_type = 0x0049
    DW_AT_use_location = 0x004A
    DW_AT_variable_parameter = 0x004B
    DW_AT_virtuality = 0x004C
    DW_AT_vtable_elem_location = 0x004D
    DW_AT_allocated = 0x004E
    DW_AT_associated = 0x004F
    DW_AT_data_location = 0x0050
    DW_AT_byte_stride = 0x0051
    DW_AT_entry_pc = 0x0052
    DW_AT_use_UTF8 = 0x0053
    DW_AT_extension = 0x0054
    DW_AT_ranges = 0x0055
    DW_AT_trampoline = 0x0056
    DW_AT_call_column = 0x0057
    DW_AT_call_file = 0x0058
    DW_AT_call_line = 0x0059
    DW_AT_description = 0x005A
    DW_AT_binary_scale = 0x005B
    DW_AT_decimal_scale = 0x005C
    DW_AT_small = 0x005D
    DW_AT_decimal_sign = 0x005E
    DW_AT_digit_count = 0x005F
    DW_AT_picture_string = 0x0060
    DW_AT_mutable = 0x0061
    DW_AT_threads_scaled = 0x0062
    DW_AT_explicit = 0x0063
    DW_AT_object_pointer = 0x0064
    DW_AT_endianity = 0x0065
    DW_AT_elemental = 0x0066
    DW_AT_pure = 0x0067
    DW_AT_recursive = 0x0068
    DW_AT_signature = 0x0069
    DW_AT_main_subprogram = 0x006a
    DW_AT_data_bit_offset = 0x006b
    DW_AT_const_expr = 0x006c
    DW_AT_enum_class = 0x006d
    DW_AT_linkage_name = 0x006e

    DW_AT_string_length_bit_size = 0x006f
    DW_AT_string_length_byte_size = 0x0070
    DW_AT_rank = 0x0071
    DW_AT_str_offsets_base = 0x0072
    DW_AT_addr_base = 0x0073
    DW_AT_ranges_base = 0x0074
    DW_AT_dwo_id = 0x0075
    DW_AT_dwo_name = 0x0076

    DW_AT_reference = 0x0077
    DW_AT_rvalue_reference = 0x0078

    DW_AT_alignment = 0x0088

    DW_AT_lo_user = 0x2000
    DW_AT_hi_user = 0x3FFF
    DW_AT_MIPS_fde = 0x2001
    DW_AT_MIPS_loop_begin = 0x2002
    DW_AT_MIPS_tail_loop_begin = 0x2003
    DW_AT_MIPS_epilog_begin = 0x2004
    DW_AT_MIPS_loop_unroll_factor = 0x2005
    DW_AT_MIPS_software_pipeline_depth = 0x2006
    DW_AT_MIPS_linkage_name = 0x2007
    DW_AT_MIPS_stride = 0x2008
    DW_AT_MIPS_abstract_name = 0x2009
    DW_AT_MIPS_clone_origin = 0x200A
    DW_AT_MIPS_has_inlines = 0x200B
    DW_AT_MIPS_stride_byte = 0x200C
    DW_AT_MIPS_stride_elem = 0x200D
    DW_AT_MIPS_ptr_dopetype = 0x200E
    DW_AT_MIPS_allocatable_dopetype = 0x200F
    DW_AT_MIPS_assumed_shape_dopetype = 0x2010
    DW_AT_MIPS_assumed_size = 0x2011

    DW_AT_sf_names = 0x2101
    DW_AT_src_info = 0x2102
    DW_AT_mac_info = 0x2103
    DW_AT_src_coords = 0x2104
    DW_AT_body_begin = 0x2105
    DW_AT_body_end = 0x2106
    DW_AT_GNU_vector = 0x2107
    DW_AT_GNU_odr_signature = 0x210f
    DW_AT_GNU_template_name = 0x2110
    DW_AT_GNU_all_tail_call_sites = 0x2116
    DW_AT_APPLE_repository_file = 0x2501
    DW_AT_APPLE_repository_type = 0x2502
    DW_AT_APPLE_repository_name = 0x2503
    DW_AT_APPLE_repository_specification = 0x2504
    DW_AT_APPLE_repository_import = 0x2505
    DW_AT_APPLE_repository_abstract_origin = 0x2506

    DW_AT_APPLE_optimized = 0x3FE1
    DW_AT_APPLE_flags = 0x3FE2
    DW_AT_APPLE_isa = 0x3FE3
    DW_AT_APPLE_block = 0x3FE4
    DW_AT_APPLE_major_runtime_vers = 0x3FE5
    DW_AT_APPLE_runtime_class = 0x3FE6
    DW_AT_APPLE_omit_frame_ptr = 0x3FE7
    DW_AT_APPLE_property_name = 0x3fe8
    DW_AT_APPLE_property_getter = 0x3fe9
    DW_AT_APPLE_property_setter = 0x3fea
    DW_AT_APPLE_property_attribute = 0x3feb
    DW_AT_APPLE_objc_complete_type = 0x3fec
    DW_AT_APPLE_property = 0x3fed

class FORM(Enum):
    DW_FORM_addr = 0x01
    DW_FORM_block2 = 0x03
    DW_FORM_block4 = 0x04
    DW_FORM_data2 = 0x05
    DW_FORM_data4 = 0x06
    DW_FORM_data8 = 0x07
    DW_FORM_string = 0x08
    DW_FORM_block = 0x09
    DW_FORM_block1 = 0x0A
    DW_FORM_data1 = 0x0B
    DW_FORM_flag = 0x0C
    DW_FORM_sdata = 0x0D
    DW_FORM_strp = 0x0E
    DW_FORM_udata = 0x0F
    DW_FORM_ref_addr = 0x10
    DW_FORM_ref1 = 0x11
    DW_FORM_ref2 = 0x12
    DW_FORM_ref4 = 0x13
    DW_FORM_ref8 = 0x14
    DW_FORM_ref_udata = 0x15
    DW_FORM_indirect = 0x16
    DW_FORM_sec_offset = 0x17
    DW_FORM_exprloc = 0x18
    DW_FORM_flag_present = 0x19
    DW_FORM_ref_sig8 = 0x20
    DW_FORM_GNU_addr_index = 0x1f01
    DW_FORM_GNU_str_index = 0x1f02


class OP(Enum):
    DW_OP_addr = 0x03
    DW_OP_deref = 0x06
    DW_OP_const1u = 0x08
    DW_OP_const1s = 0x09
    DW_OP_const2u = 0x0A
    DW_OP_const2s = 0x0B
    DW_OP_const4u = 0x0C
    DW_OP_const4s = 0x0D
    DW_OP_const8u = 0x0E
    DW_OP_const8s = 0x0F
    DW_OP_constu = 0x10
    DW_OP_consts = 0x11
    DW_OP_dup = 0x12
    DW_OP_drop = 0x13
    DW_OP_over = 0x14
    DW_OP_pick = 0x15
    DW_OP_swap = 0x16
    DW_OP_rot = 0x17
    DW_OP_xderef = 0x18
    DW_OP_abs = 0x19
    DW_OP_and = 0x1A
    DW_OP_div = 0x1B
    DW_OP_minus = 0x1C
    DW_OP_mod = 0x1D
    DW_OP_mul = 0x1E
    DW_OP_neg = 0x1F
    DW_OP_not = 0x20
    DW_OP_or = 0x21
    DW_OP_plus = 0x22
    DW_OP_plus_uconst = 0x23
    DW_OP_shl = 0x24
    DW_OP_shr = 0x25
    DW_OP_shra = 0x26
    DW_OP_xor = 0x27
    DW_OP_skip = 0x2F
    DW_OP_bra = 0x28
    DW_OP_eq = 0x29
    DW_OP_ge = 0x2A
    DW_OP_gt = 0x2B
    DW_OP_le = 0x2C
    DW_OP_lt = 0x2D
    DW_OP_ne = 0x2E
    DW_OP_lit0 = 0x30
    DW_OP_lit1 = 0x31
    DW_OP_lit2 = 0x32
    DW_OP_lit3 = 0x33
    DW_OP_lit4 = 0x34
    DW_OP_lit5 = 0x35
    DW_OP_lit6 = 0x36
    DW_OP_lit7 = 0x37
    DW_OP_lit8 = 0x38
    DW_OP_lit9 = 0x39
    DW_OP_lit10 = 0x3A
    DW_OP_lit11 = 0x3B
    DW_OP_lit12 = 0x3C
    DW_OP_lit13 = 0x3D
    DW_OP_lit14 = 0x3E
    DW_OP_lit15 = 0x3F
    DW_OP_lit16 = 0x40
    DW_OP_lit17 = 0x41
    DW_OP_lit18 = 0x42
    DW_OP_lit19 = 0x43
    DW_OP_lit20 = 0x44
    DW_OP_lit21 = 0x45
    DW_OP_lit22 = 0x46
    DW_OP_lit23 = 0x47
    DW_OP_lit24 = 0x48
    DW_OP_lit25 = 0x49
    DW_OP_lit26 = 0x4A
    DW_OP_lit27 = 0x4B
    DW_OP_lit28 = 0x4C
    DW_OP_lit29 = 0x4D
    DW_OP_lit30 = 0x4E
    DW_OP_lit31 = 0x4F
    DW_OP_reg0 = 0x50
    DW_OP_reg1 = 0x51
    DW_OP_reg2 = 0x52
    DW_OP_reg3 = 0x53
    DW_OP_reg4 = 0x54
    DW_OP_reg5 = 0x55
    DW_OP_reg6 = 0x56
    DW_OP_reg7 = 0x57
    DW_OP_reg8 = 0x58
    DW_OP_reg9 = 0x59
    DW_OP_reg10 = 0x5A
    DW_OP_reg11 = 0x5B
    DW_OP_reg12 = 0x5C
    DW_OP_reg13 = 0x5D
    DW_OP_reg14 = 0x5E
    DW_OP_reg15 = 0x5F
    DW_OP_reg16 = 0x60
    DW_OP_reg17 = 0x61
    DW_OP_reg18 = 0x62
    DW_OP_reg19 = 0x63
    DW_OP_reg20 = 0x64
    DW_OP_reg21 = 0x65
    DW_OP_reg22 = 0x66
    DW_OP_reg23 = 0x67
    DW_OP_reg24 = 0x68
    DW_OP_reg25 = 0x69
    DW_OP_reg26 = 0x6A
    DW_OP_reg27 = 0x6B
    DW_OP_reg28 = 0x6C
    DW_OP_reg29 = 0x6D
    DW_OP_reg30 = 0x6E
    DW_OP_reg31 = 0x6F
    DW_OP_breg0 = 0x70
    DW_OP_breg1 = 0x71
    DW_OP_breg2 = 0x72
    DW_OP_breg3 = 0x73
    DW_OP_breg4 = 0x74
    DW_OP_breg5 = 0x75
    DW_OP_breg6 = 0x76
    DW_OP_breg7 = 0x77
    DW_OP_breg8 = 0x78
    DW_OP_breg9 = 0x79
    DW_OP_breg10 = 0x7A
    DW_OP_breg11 = 0x7B
    DW_OP_breg12 = 0x7C
    DW_OP_breg13 = 0x7D
    DW_OP_breg14 = 0x7E
    DW_OP_breg15 = 0x7F
    DW_OP_breg16 = 0x80
    DW_OP_breg17 = 0x81
    DW_OP_breg18 = 0x82
    DW_OP_breg19 = 0x83
    DW_OP_breg20 = 0x84
    DW_OP_breg21 = 0x85
    DW_OP_breg22 = 0x86
    DW_OP_breg23 = 0x87
    DW_OP_breg24 = 0x88
    DW_OP_breg25 = 0x89
    DW_OP_breg26 = 0x8A
    DW_OP_breg27 = 0x8B
    DW_OP_breg28 = 0x8C
    DW_OP_breg29 = 0x8D
    DW_OP_breg30 = 0x8E
    DW_OP_breg31 = 0x8F
    DW_OP_regx = 0x90
    DW_OP_fbreg = 0x91
    DW_OP_bregx = 0x92
    DW_OP_piece = 0x93
    DW_OP_deref_size = 0x94
    DW_OP_xderef_size = 0x95
    DW_OP_nop = 0x96
    DW_OP_push_object_address = 0x97
    DW_OP_call2 = 0x98
    DW_OP_call4 = 0x99
    DW_OP_call_ref = 0x9A
    DW_OP_form_tls_address = 0x9B
    DW_OP_call_frame_cfa = 0x9C
    DW_OP_bit_piece = 0x9D
    DW_OP_implicit_value = 0x9E
    DW_OP_stack_value = 0x9F
    DW_OP_lo_user = 0xE0
    DW_OP_GNU_push_tls_address = 0xE0
    DW_OP_APPLE_uninit = 0xF0
    DW_OP_hi_user = 0xFF


class ATE(Enum):
    DW_ATE_address = 0x01
    DW_ATE_boolean = 0x02
    DW_ATE_complex_float = 0x03
    DW_ATE_float = 0x04
    DW_ATE_signed = 0x05
    DW_ATE_signed_char = 0x06
    DW_ATE_unsigned = 0x07
    DW_ATE_unsigned_char = 0x08
    DW_ATE_imaginary_float = 0x09
    DW_ATE_packed_decimal = 0x0A
    DW_ATE_numeric_string = 0x0B
    DW_ATE_edited = 0x0C
    DW_ATE_signed_fixed = 0x0D
    DW_ATE_unsigned_fixed = 0x0E
    DW_ATE_decimal_float = 0x0F
    DW_ATE_UTF = 0x10
    DW_ATE_lo_user = 0x80
    DW_ATE_hi_user = 0xFF


class DS(Enum):
    DW_DS_unsigned = 0x01
    DW_DS_leading_overpunch = 0x02
    DW_DS_trailing_overpunch = 0x03
    DW_DS_leading_separate = 0x04
    DW_DS_trailing_separate = 0x05

class END(Enum):
    DW_END_default = 0x00
    DW_END_big = 0x01
    DW_END_little = 0x02
    DW_END_lo_user = 0x40
    DW_END_hi_user = 0xFF

class ACCESS(Enum):
    DW_ACCESS_public = 0x01
    DW_ACCESS_protected = 0x02
    DW_ACCESS_private = 0x03

class VIS(Enum):
    DW_VIS_local = 0x01
    DW_VIS_exported = 0x02
    DW_VIS_qualified = 0x03


class VIRTUALITY(Enum):
    DW_VIRTUALITY_none = 0x00
    DW_VIRTUALITY_virtual = 0x01
    DW_VIRTUALITY_pure_virtual = 0x02

class LANG(Enum):
    DW_LANG_C89 = 0x0001
    DW_LANG_C = 0x0002
    DW_LANG_Ada83 = 0x0003
    DW_LANG_C_plus_plus = 0x0004
    DW_LANG_Cobol74 = 0x0005
    DW_LANG_Cobol85 = 0x0006
    DW_LANG_Fortran77 = 0x0007
    DW_LANG_Fortran90 = 0x0008
    DW_LANG_Pascal83 = 0x0009
    DW_LANG_Modula2 = 0x000A
    DW_LANG_Java = 0x000B
    DW_LANG_C99 = 0x000C
    DW_LANG_Ada95 = 0x000D
    DW_LANG_Fortran95 = 0x000E
    DW_LANG_PLI = 0x000F
    DW_LANG_ObjC = 0x0010
    DW_LANG_ObjC_plus_plus = 0x0011
    DW_LANG_UPC = 0x0012
    DW_LANG_D = 0x0013
    DW_LANG_Python = 0x0014
    DW_LANG_OpenCL = 0x0015
    DW_LANG_Go = 0x0016
    DW_LANG_Modula3 = 0x0017
    DW_LANG_Haskell = 0x0018
    DW_LANG_C_plus_plus_03 = 0x0019
    DW_LANG_C_plus_plus_11 = 0x001a
    DW_LANG_OCaml = 0x001b
    DW_LANG_Rust = 0x001c
    DW_LANG_C11 = 0x001d
    DW_LANG_Swift = 0x001e
    DW_LANG_Julia = 0x001f
    DW_LANG_lo_user = 0x8000
    DW_LANG_hi_user = 0xFFFF

class ID(Enum):
    DW_ID_case_sensitive = 0x00
    DW_ID_up_case = 0x01
    DW_ID_down_case = 0x02
    DW_ID_case_insensitive = 0x03

class CC(Enum):
    DW_CC_normal = 0x01
    DW_CC_program = 0x02
    DW_CC_nocall = 0x03
    DW_CC_lo_user = 0x40
    DW_CC_hi_user = 0xFF

class INL(Enum):
    DW_INL_not_inlined = 0x00
    DW_INL_inlined = 0x01
    DW_INL_declared_not_inlined = 0x02
    DW_INL_declared_inlined = 0x03

class ORD(Enum):
    DW_ORD_row_major = 0x00
    DW_ORD_col_major = 0x01

class DSC(Enum):
    DW_DSC_label = 0x00
    DW_DSC_range = 0x01

class LNS(Enum):
    DW_LNS_copy = 0x01
    DW_LNS_advance_pc = 0x02
    DW_LNS_advance_line = 0x03
    DW_LNS_set_file = 0x04
    DW_LNS_set_column = 0x05
    DW_LNS_negate_stmt = 0x06
    DW_LNS_set_basic_block = 0x07
    DW_LNS_const_add_pc = 0x08
    DW_LNS_fixed_advance_pc = 0x09
    DW_LNS_set_prologue_end = 0x0A
    DW_LNS_set_epilogue_begin = 0x0B
    DW_LNS_set_isa = 0x0C

class LNE(Enum):
    DW_LNE_end_sequence = 0x01
    DW_LNE_set_address = 0x02
    DW_LNE_define_file = 0x03
    DW_LNE_set_discriminator = 0x04
    DW_LNE_lo_user = 0x80
    DW_LNE_hi_user = 0xFF

class MACINFO(Enum):
    DW_MACINFO_define = 0x01
    DW_MACINFO_undef = 0x02
    DW_MACINFO_start_file = 0x03
    DW_MACINFO_end_file = 0x04
    DW_MACINFO_vendor_ext = 0xFF

class CFA(Enum):
    DW_CFA_advance_loc = 0x40
    DW_CFA_offset = 0x80
    DW_CFA_restore = 0xC0
    DW_CFA_nop = 0x00
    DW_CFA_set_loc = 0x01
    DW_CFA_advance_loc1 = 0x02
    DW_CFA_advance_loc2 = 0x03
    DW_CFA_advance_loc4 = 0x04
    DW_CFA_offset_extended = 0x05
    DW_CFA_restore_extended = 0x06
    DW_CFA_undefined = 0x07
    DW_CFA_same_value = 0x08
    DW_CFA_register = 0x09
    DW_CFA_remember_state = 0x0A
    DW_CFA_restore_state = 0x0B
    DW_CFA_def_cfa = 0x0C
    DW_CFA_def_cfa_register = 0x0D
    DW_CFA_def_cfa_offset = 0x0E
    DW_CFA_def_cfa_expression = 0x0F
    DW_CFA_expression = 0x10
    DW_CFA_offset_extended_sf = 0x11
    DW_CFA_def_cfa_sf = 0x12
    DW_CFA_def_cfa_offset_sf = 0x13
    DW_CFA_val_offset = 0x14
    DW_CFA_val_offset_sf = 0x15
    DW_CFA_val_expression = 0x16
    DW_CFA_GNU_window_save = 0x2D
    DW_CFA_GNU_args_size = 0x2E
    DW_CFA_GNU_negative_offset_extended = 0x2F
    DW_CFA_lo_user = 0x1C
    DW_CFA_hi_user = 0x3F

class GNU_EH(Enum):
    DW_GNU_EH_PE_absptr = 0x00
    DW_GNU_EH_PE_uleb128 = 0x01
    DW_GNU_EH_PE_udata2 = 0x02
    DW_GNU_EH_PE_udata4 = 0x03
    DW_GNU_EH_PE_udata8 = 0x04
    DW_GNU_EH_PE_sleb128 = 0x09
    DW_GNU_EH_PE_sdata2 = 0x0A
    DW_GNU_EH_PE_sdata4 = 0x0B
    DW_GNU_EH_PE_sdata8 = 0x0C
    DW_GNU_EH_PE_signed = 0x08
    DW_GNU_EH_PE_MASK_ENCODING = 0x0F
    DW_GNU_EH_PE_pcrel = 0x10
    DW_GNU_EH_PE_textrel = 0x20
    DW_GNU_EH_PE_datarel = 0x30
    DW_GNU_EH_PE_funcrel = 0x40
    DW_GNU_EH_PE_aligned = 0x50
    DW_GNU_EH_PE_indirect = 0x80
    DW_GNU_EH_PE_omit = 0xFF

class APPLE_PROPERTY(Enum):
    DW_APPLE_PROPERTY_readonly = 0x01
    DW_APPLE_PROPERTY_readwrite = 0x02
    DW_APPLE_PROPERTY_assign = 0x04
    DW_APPLE_PROPERTY_retain = 0x08
    DW_APPLE_PROPERTY_copy = 0x10
    DW_APPLE_PROPERTY_nonatomic = 0x20

class UT(Enum):
    DW_UT_compile = 0x01
    DW_UT_type = 0x02
    DW_UT_partial = 0x03
    DW_UT_skeleton = 0x04
    DW_UT_split_compile = 0x05
    DW_UT_split_type = 0x06

""" const definition end
"""


def ReadCStr(sec):
    """ read section offset as c-style string """
    sz = []
    while True:
        c = sec.Read(1)
        c = c.decode('utf-8')
        #c = str(c, 'utf-8')
        if c == chr(0):
            return "".join(sz) 
        sz.append(c)

class Elf:

    class SHTYPE(Enum):
        NULL_TYPE = 0
        PROGBITS = 1
        SYMTAB = 2
        STRTAB = 3
        RELA = 4
        HASH = 5
        DYNAMIC = 6
        NOTE = 7
        NOBITS = 8
        REL = 9
        SHLIB = 10
        DYNSYM = 11
        INIT_ARRAY = 14
        FINI_ARRAY = 15
        PREINIT_ARRAY = 16
        GROUP = 17
        SYMTAB_SHNDX = 18

    class Section:
        """ represents a Section in Elf file. """

        def __init__(self, elf, name, offset, size):
            self._elf = elf
            self._name = name
            self._offset = offset
            self._size = size

        def Seek(self, offset):
            off = self._offset + offset
            self._elf._I_mmap.seek(off)

        def Tell(self):
            off = self._elf._I_mmap.tell()
            return off - self._offset

        def Read(self, size):
            return self._elf._I_mmap.read(size) 

        def ReadU8(self):
            return struct.unpack('B', self.Read(1))[0] 
        
        def ReadU16(self):
            return struct.unpack('H', self.Read(2))[0] 
        
        def ReadU32(self):
            return struct.unpack('I', self.Read(4))[0] 
        
        def ReadU64(self):
            return struct.unpack('Q', self.Read(8))[0] 
        
        def ReadI8(self):
            return struct.unpack('b', self.Read(1))[0] 
        
        def ReadI16(self):
            return struct.unpack('h', self.Read(2))[0] 
        
        def ReadI32(self):
            return struct.unpack('i', self.Read(4))[0] 
        
        def ReadI64(self):
            return struct.unpack('q', self.Read(8))[0] 
        
        def ReadUleb128(self):
            """ Extract a ULEB128 value """
            byte = self.ReadU8()
            if byte & 0x80:
                result = byte & 0x7f
                shift = 7
                while byte & 0x80:
                    byte = self.ReadU8()
                    result |= (byte & 0x7f) << shift
                    shift += 7
                return result
            else:
                return byte

        def ReadSleb128(self):
            """ Extract a SLEB128 value """
            result = 0
            shift = 0
            size = 64
            byte = 0
            bytecount = 0
            while 1:
                bytecount += 1
                byte = self.ReadU8()
                result |= (byte & 0x7f) << shift
                shift += 7
                if (byte & 0x80) == 0:
                    break
            result &= 0xFFFFFFFFFFFFFFFF

            # Sign bit of byte is 2nd high order bit (0x40)
            if (shift < size) and (byte & 0x40):
                result |= - (1 << shift)
            return result

    class StrTab(Section):
        """ strtab is a special secion holds all elf strings """ 

        def Str(self, index):
            self.Seek(index)
            return ReadCStr(self) 

    def ReadEhdr(self, fd, elfhdr):
        """ parse elf header """

        sd = '2HI3QI6H'
        size = struct.calcsize(sd)
        t = struct.unpack(sd, fd.read(size))
        elfhdr['e_type']= t[0]
        elfhdr['e_machine'] = t[1]
        elfhdr['e_version'] = t[2]
        elfhdr['e_entry'] = t[3]
        elfhdr['e_phoff'] = t[4]
        elfhdr['e_shoff'] = t[5]
        elfhdr['e_flags'] = t[6]
        elfhdr['e_ehsize'] = t[7]
        elfhdr['e_phentsize'] = t[8]
        elfhdr['e_phnum'] = t[9]
        elfhdr['e_shentsize'] = t[10]
        elfhdr['e_shnum'] = t[11]
        elfhdr['e_shstrndx'] = t[12]    
        return size

    def ReadShdr(self, fd, elfhdr, sechdrs):
        """ parse all sections header """

        off = elfhdr['e_shoff']
        num = elfhdr['e_shnum']
        size = elfhdr['e_shentsize']
        fd.seek(off)

        for i in range(num):
            t = struct.unpack('2I4Q2I2Q', fd.read(size))
            sec = {}
            sec['sh_name'] = t[0]
            sec['sh_type'] = t[1]
            sec['sh_flags'] = t[2]
            sec['sh_addr'] = t[3]
            sec['sh_offset'] = t[4]
            sec['sh_size'] = t[5]
            sec['sh_link'] = t[6]
            sec['sh_info'] = t[7]
            sec['sh_addralign'] = t[8]
            sec['sh_entsize'] = t[9]
            sechdrs.append(sec)
        return 0

    def SecEntry(self):
        """ for elf shares one mmap entry,
            SecEntry() is used for section switch.
            save current Section.Tell() and restore after Section finish.

            e.g.
            save = SecEntry()
            sec.Seek(xxx)
            SecExit(save)
        """
        return self._I_mmap.tell()

    def SecExit(self, save):
        self._I_mmap.seek(save)

    def GetSection(self, name):
        """ get Section by name """
        if name in self._I_cached_sections:
            return self._I_cached_sections[name]

        for s in self._I_shdrs:
            sh_name = self._I_strtab.Str(s['sh_name'])
            if sh_name == name:
                return Elf.Section(self, sh_name, s['sh_offset'], s['sh_size'])
        return None

    def Load(self, filename):
        
        # open file
        f = open(filename, 'rb')
        self._I_file = f

        # get file size
        f.seek(0, 2)
        size = f.tell()
        f.seek(0)

        # mmap
        m = mmap(f.fileno(), size, access = ACCESS_READ)
        self._I_mmap = m

        magic = m.read(16)
        
        # compact py2 and py3
        if isinstance(magic, str):
            magic = [ord(i) for i in magic]
        #print(magic)

        if magic[0] != 127 or \
           magic[1] != ord('E') or \
           magic[2] != ord('L') or \
           magic[3] != ord('F'):
            print ("error: not a valid dwarf file.")
            return

        # read elf header
        elfhdr = {}
        size = self.ReadEhdr(m, elfhdr)
        #print(elfhdr)
        self._I_ehdr = elfhdr

        # read section headers
        sechdrs = []
        size = self.ReadShdr(m, elfhdr, sechdrs)
        #print(sechdrs)
        self._I_shdrs = sechdrs

        # get strtab
        for s in sechdrs:
            if s['sh_type'] == Elf.SHTYPE.STRTAB:
                self._I_strtab = Elf.StrTab(self, '.shstrtab', s['sh_offset'], s['sh_size'])
                break
        if self._I_strtab is None:
            raise Exception

        # cache the sections
        secs = {}
        for s in self._I_shdrs:
            sh_name = self._I_strtab.Str(s['sh_name'])
            secs[sh_name] = Elf.Section(self, sh_name, s['sh_offset'], s['sh_size'])
        self._I_cached_sections = secs

    def Unload(self):
        self._I_mmap.close()
        self._I_file.close()
        self._I_mmap = None
        self._I_file = None
        print('Elf Unloaded')

class RawAbbr:
    """ represents a Abbrev entry """

    def __init__(self):
        self.attrs = [] 

    def Decode(self, sec):
        tell = sec.Tell()
       
        # read entry  
        self.entry = sec.ReadUleb128()
        if self.entry == 0:
            return 
       
        # read tag 
        self.tag = sec.ReadUleb128()
        self.has_child = sec.ReadU8()

        # read attributes
        while True:
            attr = sec.ReadUleb128()
            if attr == 0:
                break
            form = sec.ReadUleb128()
            self.attrs.append([attr, form])
        sec.ReadUleb128()

        # save size
        self.size = sec.Tell() - tell 

    def DebugPrint(self):
        print("  %-5d %s (%d) [ %s children ]" % 
                (self.entry, TAG.Name(self.tag), self.size, 
                 "has" if self.has_child else "no"))
        for i in self.attrs:
            print("    %-20s %s" % (AT.Name(i[0]), FORM.Name(i[1])))

class RawCu:
    """ represents a Cu entry """

    def __init__(self, dwarf):
        self.dwarf = dwarf
        self.abbrs = {} 

    def GetFirstDie(self):
        return RawDie(self, self.first_die_secoff)

    def GetAbbr(self, entry):
        return self.abbrs[entry]
    
    def GetEndOffset(self):
        return self.secoff + self.cu_len + 4 

    def Decode(self, sec):
        self.sec = sec
        self.secoff = sec.Tell()
        self.cu_len = sec.ReadU32()
        self.cu_ver = sec.ReadU16()
        self.abbr_off = sec.ReadU32()
        self.ptr_size = sec.ReadU8()
        self.first_die_secoff = sec.Tell()

    def DebugPrint(self):
        print("cu_len : %d" % self.cu_len) 
        print("cu_ver : %d" % self.cu_ver) 
        print("abbr_off : %d" % self.abbr_off) 
        print("ptr_size : %d" % self.ptr_size) 

class RawDie:
    """ represents a Die entry """
   
    def __init__(self, cu, secoff):
        self.cu = cu
        self.secoff = int(secoff)
        self.abbr = None

    def GetAt(self, at):
        for i in self.attrs:
            if at == i.at:
                return i
        return None

    def AtName(self):
        at = self.GetAt(AT.DW_AT_name)
        if at is None:
            return None
        return at.val

    def Tag(self):
        return self.abbr.tag

    def AtType(self):
        at = self.GetAt(AT.DW_AT_type)
        if at is None:
            return None
        return RawDie(self.cu, at.val)

    def AtByteSize(self):
        at = self.GetAt(AT.DW_AT_byte_size)
        if at is None:
            return None
        return int(at.val)

    def Sibling(self):
        at = self.GetAt(AT.DW_AT_sibling)
        if at is None:
            return None
        return RawDie(self.cu, at.val)

    def Next(self):
        off = self.secoff + self.size
        return RawDie(self.cu, off)

    def IsPadding(self):
        return self.entry == 0

    def Decode(self, parent=None):
        sec = self.cu.sec
        sec.Seek(self.secoff)

        # get entry
        self.entry = sec.ReadUleb128()
        if self.entry == 0:
            self.size = 1
            return

        # save attr_secoff
        self.attr_secoff = sec.Tell()
        self.abbr = self.cu.GetAbbr(self.entry) 

        # clac attrs size
        self.attrs = []
        for f in self.abbr.attrs:
            form = RawAtForm()
            form.Decode(self.cu, f[0], f[1]) 
            self.attrs.append(form)
         
        # update size
        self.size = sec.Tell() - self.secoff 

        # some die need parent's info, like DW_TAG_enumeration_type
        self.parent = parent

    class TypeChain:
        """ walk die's type chain and get type information.
        """

        # type is a signed value
        _is_signed = None

        # type is an array
        _is_array = False 
        
        # type is an struct
        _is_struct = False 
        
        # type is an enum 
        _is_enum = False 

        # type size (single size)
        _byte_size = 0

        def __init__(self, die):

            t = die.AtType()
            if t is None:
                if die.Tag() == TAG.DW_TAG_enumerator and die.parent is not None and \
                        die.parent.Tag() == TAG.DW_TAG_enumeration_type:
                    self.WalkType(die.parent)
                else:
                    print(TAG.Name(die.parent.Tag()), 
                            TAG.Name(die.Tag()), 
                            TAG.DW_TAG_enumeration_type)
                    die.parent.DebugPrint()
                    die.DebugPrint()
                    assert 0
            else:
                self.WalkType(die)

        def WalkType(self, die):
            t = die.AtType()
            while t:
                t.Decode()
                tag = t.Tag()

                # is array 
                if tag == TAG.DW_TAG_array_type:
                    self._is_array = True
               
                elif tag == TAG.DW_TAG_structure_type:
                    self._is_struct = True

                elif tag == TAG.DW_TAG_enumerator:
                    self._is_enum = True

                # get signed or unsgiend from type name 
                name = t.AtName()
                if name:
                    if self._is_signed is None:
                        if name == 'int' or name == 'short' or name == 'char':
                            self._is_signed = True
                        elif name == 'intptr_t' or name == 'uintptr_t':
                            self._is_signed = False 

                # basic type size
                size = t.AtByteSize()
                if size:
                    self._byte_size = size

                # unspecified_type : nullptr
                if tag == TAG.DW_TAG_unspecified_type:
                    self._byte_size = 8
                    self._is_signed = False

                t = t.AtType()

            # assumpt non-match is unsigned.
            if self._is_signed is None:
                self._is_signed = False

            assert self._byte_size > 0, die.DebugPrint()
            assert self._is_signed is not None

        @property
        def is_signed(self):
            return self._is_signed

        @property
        def is_array(self):
            return self._is_array

        @property
        def is_struct(self):
            return self._is_struct

        @property
        def is_enum(self):
            return self._is_enum

        @property
        def byte_size(self):
            return self._byte_size

    def GetConstValue(self):
        const = self.GetAt(AT.DW_AT_const_value)
        if const is None:
            return None

        tc = RawDie.TypeChain(self)
        if tc.is_array:
            return const.GetArray(tc.byte_size, tc.is_signed, tc.is_struct) 

        elif tc.is_struct:
            return const.bytes

        elif tc.is_signed:
            return const.signed
        return const.unsigned

    def DebugPrint(self):

        if self.IsPadding():
            print("<%x> Padding (%d)" % (self.secoff, self.size))
            return
        
        print("<%x> %s (%d) %s" % (
            self.secoff,
            TAG.Name(self.abbr.tag),
            self.size,
            "[ has_child ]" if self.abbr.has_child else ""
            ))
        for i in self.attrs:
            print(str(i))

class Block:
    """ represents a dwarf block holds the raw value """

    def __init__(self, size, data):
        self.size = size
        self.data = data

    def __int__(self):
        return self.signed

    @property
    def signed(self):
        return self.GetInt(self.size, is_signed=True)

    @property
    def unsigned(self):
        return self.GetInt(self.size, is_signed=False)
    
    def GetInt(self, size, off=0, is_signed=True):
        assert self.size > 0
        c = None
        if is_signed:
            if size == 4: c = 'i'
            elif size == 8: c = 'q'
            elif size == 1: c = 'b'
            elif size == 2: c = 'h'
        else:
            if size == 4: c = 'I'
            elif size == 8: c = 'Q'
            elif size == 1: c = 'B'
            elif size == 2: c = 'H'
       
        assert c, str(self)
        return struct.unpack(c, self.data[off:(off+size)])[0]

    def GetArray(self, byte_size, is_signed=False, is_struct=False):
        """ return decoded array from block.
            byte_size : single size of each item.
            is_signed : value is signed or not.
            is_struct : value is struct return the bytes
        """
        out = []
        for i in range(0, self.size, byte_size):
            if is_struct:
                v = self.GetBytes(byte_size, off=i)
            else:
                v = self.GetInt(byte_size, off=i, is_signed=is_signed)
            out.append(v)
        return out

    def GetBytes(self, size, off=0):
        return self.data[off:size]

    def __str__(self):
        a = []
        for i in range(min(self.size, 16)):
            a.append("%02x" % ord(self.data[i]))
        sz = "[ %d: %s ]" % (self.size, " ".join(a))
        return sz

class RawAtForm:
    """ At & Form pair for decoding """

    def Decode(self, cu, at, form):
        sec = cu.sec
        tell = sec.Tell()

        self.at = at
        self.form = form
        
        val = None
        if form == FORM.DW_FORM_addr:
            val = sec.ReadU64()
        elif form == FORM.DW_FORM_block1:
            i = sec.ReadU8()
            val = Block(i, sec.Read(i))
        elif form == FORM.DW_FORM_block2:
            i = sec.ReadU16()
            val = Block(i, sec.Read(i))
        elif form == FORM.DW_FORM_block4:
            i = sec.ReadU32()
            val = Block(i, sec.Read(i))
        elif form == FORM.DW_FORM_data1 or \
             form == FORM.DW_FORM_ref1:
            val = Block(1, sec.Read(1))
        elif form == FORM.DW_FORM_data2 or \
             form == FORM.DW_FORM_ref2:
            val = Block(2, sec.Read(2))
        elif form == FORM.DW_FORM_data4 or \
             form == FORM.DW_FORM_ref4:
            val = Block(4, sec.Read(4))
        elif form == FORM.DW_FORM_block or \
             form == FORM.DW_FORM_exprloc:
            i = sec.ReadUleb128()
            val = Block(i, sec.Read(i))
        elif form == FORM.DW_FORM_data8 or \
             form == FORM.DW_FORM_ref_sig8:
            val = Block(8, sec.Read(8))
        elif form == FORM.DW_FORM_strp:
            i = sec.ReadU32()
            val = cu.dwarf.ReadStr(i)
        elif form == FORM.DW_FORM_sec_offset:
            val = sec.ReadU32()
        elif form == FORM.DW_FORM_string:
            val = ReadCStr(sec)
        elif form == FORM.DW_FORM_flag_present:
            val = True 
        elif form == FORM.DW_FORM_sdata:
            val = sec.ReadSleb128()
        elif form == FORM.DW_FORM_udata or \
             form == FORM.DW_FORM_ref_udata:
            val = sec.ReadUleb128()
        else:
            print("error: form '%s' not handled." % FORM.Name(form))
            raise Exception
        
        self.val = val
        self.size = sec.Tell() - tell

    def __int__(self):
        return self.signed

    @property
    def signed(self):
        if isinstance(self.val, Block):
            return self.val.signed
        return int(self.val)

    @property
    def unsigned(self):
        if isinstance(self.val, Block):
            return self.val.unsigned
        return int(self.val)

    def GetArray(self, size, is_signed=False, is_struct=False):
        assert isinstance(self.val, Block)
        return self.val.GetArray(size, is_signed, is_struct)

    @property
    def bytes(self):
        return self.val.data

    def __str__(self):
        val = self.val
        at = self.at
        form = self.form
        if form == FORM.DW_FORM_data1 or \
           form == FORM.DW_FORM_data2 or \
           form == FORM.DW_FORM_data4:
            s = "%d" % val
        elif isinstance(val, int):
            s = "<%x>" % val
        else:
            s = str(val)
        
        return "  %-20s : %s (%s)" % (AT.Name(at), s, FORM.Name(form))

class RawDwarf:

    def __init__(self, filename):
        self.filename = filename
        self._elf = Elf() 
        self._cus = [] 
        self._cache = {}
        self._enum_cache = {}

    def __del__(self):
        self._elf = None
        self._cus = None

    def Load(self):
        """ Load from typ file then decode '.debug_info'
            after that, the RawDwarf is ready to read or search.
        """
        # load elf file to mmap
        self._elf.Load(self.filename)

        # decode typ file
        self.Decode()

    def ReadAbbr(self, cu):
        """ read cu's Abbrev list """

        elf = self._elf
        sec = elf.GetSection('.debug_abbrev')
        
        if sec is None:
            raise Exception
        
        # set to section begin
        sec.Seek(cu.abbr_off)
        
        size = 0
        while True: 
            abbr = RawAbbr()

            abbr.Decode(sec)
            if abbr.entry == 0:
                break

            #abbr.DebugPrint()
            
            # put in map
            cu.abbrs[abbr.entry] = abbr
    
    def ReadStr(self, off):
        """ read string from '.debug_str' """
        save = self._elf.SecEntry()
        sec = self._elf.GetSection('.debug_str') 
        sec.Seek(off)
        sz = ReadCStr(sec) 
        self._elf.SecExit(save)
        return sz

    def Decode(self):
        """ decode the typ file """
        sec = self._elf.GetSection('.debug_info')
       
        # set begin of the section
        sec.Seek(0)

        # parse all cus
        size = 0
        while size < sec._size:
            # new cu
            cu = RawCu(self)
            cu.Decode(sec)
            self._cus.append(cu) 
            size += 4 + cu.cu_len

        # load cu's abbrev
        for cu in self._cus:
            self.ReadAbbr(cu)

    def WalkCuDies(self, cu):
        """ walk all Dies in CU and DebugPrint() """
        off = cu.first_die_secoff
        while off < cu.GetEndOffset():
            die = RawDie(cu, off)
            die.Decode()
            die.DebugPrint()
            off += die.size

    def WalkDies(self, parent):
        if not parent.abbr.has_child:
            return
      
        stack = []
        stack.append(parent)

        # get the first child
        die = parent.Next()
        deep = 1  
        while die is not None: 
            
            # decode the die
            die.Decode(parent)

            # pop
            if die.IsPadding():
                parent = stack.pop()
                if len(stack) == 0:
                    break
                else:
                    die = die.Next()
                    continue

            # push
            if die.abbr.has_child:
                parent = die
                stack.append(parent)
                deep += 1

            yield die 

            # next die
            die = die.Next()

    def WalkDiesNoChild(self, parent):

        #assert parent.abbr.has_child, parent.DebugPrint()
        if not parent.abbr.has_child:
            return

        stack = []
        stack.append(parent)
        
        # get the first child
        die = parent.Next()
        while die is not None: 
            
            # decode the die
            die.Decode(parent)

            # exit condition
            if die.IsPadding():
                break
            
            #print("<%x> %s child(%d) sibling(%s)" % (
            #    die.secoff, TAG.Name(die.Tag()), 
            #    die.abbr.has_child, die.Sibling()))

            # name match
            yield die

            # next sibling
            next_die = die.Sibling()
            if next_die is None:
                # sibling chain but single last
                if die.abbr.has_child:
                    # last sibling entry
                    break
                next_die = die.Next()
            die = next_die

    def FindChild(self, parent, name):
        """ find parent's children by name
            (children's children is not included) 
        """
        if not parent.abbr.has_child:
            return None
     
        # get the first child
        die = parent.Next()
        while die is not None: 
            
            # decode the die
            die.Decode(parent)

            # exit condition
            if die.IsPadding():
                break

            # name match
            if die.AtName() == name:
                return die

            # next sibling
            next_die = die.Sibling()
            if next_die is None:
                next_die = die.Next()
            die = next_die

        # not found
        return None

    def FindChildByTag(self, parent, tag):
        """ find parent's children by tag
            (children's children is not included) 
        """
        if not parent.abbr.has_child:
            return None
      
        out = []

        # get the first child
        die = parent.Next()
        while die is not None: 
            
            # decode the die
            die.Decode(parent)

            # exit condition
            if die.IsPadding():
                break

            # type match
            if die.Tag() == tag:
                out.append(die) 

            # next sibling
            next_die = die.Sibling()
            if next_die is None:
                next_die = die.Next()
            die = next_die

        if len(out) > 0:
            return out 
        
        # not found
        return None

    def FindInChild(self, parent, name):
        """ find parent for all children (include children's) """

        if not parent.abbr.has_child:
            return None
      
        stack = []
        stack.append(parent)
        # get the first child
        die = parent.Next()
        #deep = 1 
        while die is not None: 
            
            # decode the die
            die.Decode(parent)

            # pop
            if die.IsPadding():
                parent = stack.pop()
                if len(stack) == 0:
                    break
                else:
                    die = die.Next()
                    continue

            # push
            if die.abbr.has_child:
                parent = die
                stack.append(parent)

            if die.AtName() == name:
                return die

            # next die
            die = die.Next()

        # not found
        return None

    def FindInheritsForConst(self, parent, const_name):
        """ find const in all inhertitace types,
            priority by search order.
        """
        i = 10
        search_list = [ parent ]
        while len(search_list) > 0 and i > 0:
            # get front
            base = search_list.pop()
            #base.DebugPrint()

            # search the base
            die = self.FindInChild(base, const_name)

            # if found
            if die is not None:
                return die

            # get base 's inherits types
            inherits = self.FindChildByTag(base, TAG.DW_TAG_inheritance)
            if inherits is None:
                continue

            # add to search_list
            for k in inherits:
                die = k.AtType()
                die.Decode()
                #die.DebugPrint()
                search_list.append(die)
            i -= 1

    def FindDie(self, name):
        """ find type node by name """
        if name in self._cache:
            #print("in cahe %s" % name)
            return self._cache[name]

        cu = self._cus[0]
        
        parent = cu.GetFirstDie()
        parent.Decode()
        
        cxy = name.split('::')
        xxx = []
        for i in cxy:
            die = self.FindChild(parent, i)
            if die is None: 
                break
            
            xxx.append(die)
            parent = die 
        
        if die is None:
            #print("not found")
            return None
       
        self._cache[name] = die
        return die

    def ReadConst(self, const_value):
        """ return const_value if found, or None

            e.g.
            const = ReadConst('v8::internal::kTagBits')
            print(const)   // 2
        """
        die = self.FindDie(const_value)
        if die is None:
            return None

        #die.DebugPrint()
        at_const = die.GetConstValue()
        if at_const is None:
            return None

        return int(at_const)

    def ReadNonDirectConst(self, cls_str, const_name):
        """ return const_value if found, or None

            e.g.
            const = ReadNonDirectConst('kThinStringTag')
            print(const)   // 5 
        """
        cls = self.FindDie(cls_str)
        if cls is None:
            return None

        die = None
       
        # check in enum_cache
        if cls in self._enum_cache:
            enums = self._enum_cache[cls]
            for i in enums:
                #print(1, len(self._enum_cache[cls]), i.AtName())
                die = self.FindChild(i, const_name)
                if die is not None:
                    #die.DebugPrint()
                    break;
 
        # const variable
        if die is None:
            die = self.FindChild(cls, const_name)

        # check in enums
        if die is None:
            enums = self.FindChildByTag(cls, TAG.DW_TAG_enumeration_type)
            if cls not in self._enum_cache:
                self._enum_cache[cls] = []
        
            for i in enums:
                die = self.FindChild(i, const_name)

                if die is not None:
                    self._enum_cache[cls].append(i)
                    #print(2, len(self._enum_cache[cls]), i.AtName())
                    break;

        if die is None:
            return None

        #die.DebugPrint()
        at_const = die.GetConstValue()
        if at_const is None:
            return None

        return int(at_const)

    def ReadTypeConst(self, cls_str, const_name):
        """ search const_name in cls_str, 
            return found, or None

            e.g.
            const = ReadTypeConst('v8::internal::HeapObject', 'kMapOffset')
            print(const)    // 0
        """
        cls = self.FindDie(cls_str)
        if cls is None:
            return None

        die = self.FindInheritsForConst(cls, const_name)
        if die is None:
            return None

        #die.DebugPrint()
        at_const = die.GetConstValue()
        if at_const is None:
            return None

        return int(at_const)

    @profiler
    def ReadAllConstsNoInheritesByList(self, cls_str, consts_list):
        """ search consts_list in cls_str, 
            return the const in array, not found value be None.
        """
        wait = { x:None for x in consts_list } 
        result = {}

        parent = self.FindDie(cls_str)
        if parent is None:
            return None
        
        dirs = [ parent ]
        while len(dirs) > 0 and len(wait) > 0:
            parent = dirs.pop()
            for die in self.WalkDiesNoChild(parent):
                const = die.GetConstValue() 
                if const is not None:
                    name = die.AtName()
                    if name in wait:
                        result[name] = int(const)
                        wait.pop(name)
                    continue
                
                tag = die.Tag()
                if tag == TAG.DW_TAG_enumeration_type or \
                    tag == TAG.DW_TAG_namespace:
                    dirs.append(die)

        return result

    def ReadAllConsts(self, cls_str):
        """ read out class's all consts.
        """
        parent = self.FindDie(cls_str)
        if parent is None:
            return None
        
        search_list = [ parent ]
        consts = {}
        for cls in search_list:
            cls_name = cls.AtName()
            #print(cls.AtName())

            for die in self.WalkDies(cls):
                if die.Tag() == TAG.DW_TAG_inheritance:
                    inherit_die = die.AtType()
                    inherit_die.Decode()
                    inherit_name = inherit_die.AtName()

                    # we only interesting TorqueGenerated or Base CPP classes
                    if inherit_die.AtName().startswith('TorqueGenerated') or \
                        inherit_die.AtName().startswith('HashTable<') or \
                        inherit_name.find(cls_name) >= 0 or \
                        cls_name.find(inherit_name) >= 0:
                        search_list.append(inherit_die)
                    
                    continue

                const = die.GetConstValue()
                if const is None:
                    continue
                
                name = die.AtName()
                #print(" - %s = %d" % (name, const))
                if name not in consts:
                    consts[name] = int(const)
        return consts 


    def ShowInherits(self, cls_str):
        """ show class's inherits. 
        """
        parent = self.FindDie(cls_str)
        if parent is None:
            return None
      
        def WalkInhert(parent, deep):
            print("%*s[%d] %s" % (deep, '', deep, parent.AtName()))
            for die in self.WalkDiesNoChild(parent):
                if die.Tag() == TAG.DW_TAG_inheritance:
                    inherit_die = die.AtType()
                    inherit_die.Decode()
                    WalkInhert(inherit_die, deep + 1)

        WalkInhert(parent, 0)


class Dwf:

    def __init__(self, filename):
        self.raw = RawDwarf(filename)
        self.raw.Load()
    
    def ReadConst(self, const_key):
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
            return self.raw.ReadTypeConst(arr[0], arr[1])
        else:
            return self.raw.ReadConst(const_key)

    def ReadClassConst(self, class_name, const_name):
        return self.raw.ReadTypeConst(class_name, const_name)

    def ReadNonDirectConst(self, class_name, const_name):
        return self.raw.ReadNonDirectConst(class_name, const_name)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('typ', type=str, help="which 'typ' file to read")
    parser.add_argument('const', type=str, help="const value name")
    args = parser.parse_args()

    dwf = Dwf(args.typ)
    val = dwf.ReadConst(args.const)
    if val is None:
        print("'%s' is not found." % (args.const))
    else:
        print("%s = %d" % (args.const, val))

    #kTagBits = dwf.ReadConst('v8::internal::kTagBits')
    #kMapOffset = dwf.ReadConst("'v8::internal::HeapObject'::kMapOffset")
    #print(kTagBits, kMapOffset)

