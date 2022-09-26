from __future__ import print_function, division

import gdb

class Dwf:
    """
        There are different const implemtations in v8 engine.
        the Dwf helps to find the correct const value for object difinition.

        definition,

        type 1: class const variable 
        class A : Object {
            static const int kValueOneOffset = 8;
        }
    
        type 2: torque generate constxpr 
        class B : TorqueGenerateClass {
            ...
        }
        Class TorqueGenerateClass<D, P> {
            static constxpr int kValueTwoOffset = 16;
        }

        type 1 and type 2 generates class member directly in Class.

        type 3: using macro
        class C {
            #define OBJECT_FIELDS(V) \ 
               V(kValueThreeOffset, kTaggedSize*3),
               V(kHeaderSize, 0)
            DEFINE_FIELD_OFFET_CONSTANTS(OBJECT_FIELDS)
        }
        
        type 3 generages a Enum in class C, but without a name.

        reference,

        for type 1 and type 2, gdb using 'type'::value for const reference.

        p 'v8::internal::A'::kValueOne
        p 'v8::internal::A'::kValueTwo

        for type 3, the anonymous Enum type only can reference directly by its value.

        p 'v8::internal::C::kValueTreeOffset'

        And because of the class inheritance, a subclass my have same named const value 
        but different type of parent class. eg,

        Class A {
            static const int kHeaderSize = 8;
        }

        Class B : A {
            enum {
                kHeaderSize = 16,
                kHeaderSizeEnd = 15,
            }
        }

    """
 
    @classmethod
    def getEnum(cls, typ, name):
        try:
            v = gdb.parse_and_eval("'%s::%s'"%(typ, name))
            if v.type.code == gdb.TYPE_CODE_ENUM:
                return v
        except Exception, e:
            return None
        return None 

    @classmethod
    def getConst(cls, typ, name):
        try:
            v = gdb.parse_and_eval("'%s'::%s"%(typ, name))
            return v
        except Exception, e:
            return None
        return None 

    @classmethod
    def LoadConst(cls, typ, name):
        # class inheritance
        t = gdb.lookup_type(typ)
        cl = [t] 

        while len(cl) > 0:
            t = cl.pop()
            # first, lookup a Enum value
            v = cls.getEnum(t.tag, name)
            if v is not None:   # found
                return v

            # then, const value
            for i in t.fields():
                if i.name == name:
                    v = cls.getConst(t.tag, name)
                    if v is not None:
                        return v

                if i.type.code == gdb.TYPE_CODE_STRUCT:
                    cl.append(i.type)
   
        return None

    @classmethod
    def LoadInternalConst(cls, name):
        try:
            v = gdb.parse_and_eval("\'v8::internal::%s\'" % name);
            return v 
        except Exception, e:
            #print(e)
            return None
        return None

    @classmethod
    def ReadClassConst(cls, class_name, const_name):
        return cls.getConst(class_name, const_name) 

    @classmethod
    def ReadNonDirectConst(cls, class_name, const_name):
        return cls.LoadConst(class_name, const_name) 

    @classmethod
    def showClassInheritance(cls, typ):
        t = gdb.lookup_type(typ)
        cl = [[t,1]] 

        print("Class Inheritance '%s':" % (typ))

        p = 0
        while len(cl) > 0:
            t,p = cl.pop()
            print("%*s%s" % (p, " ", t.tag))

            for i in t.fields():
                if i.is_base_class and i.type.code == gdb.TYPE_CODE_STRUCT:
                    cl.append([i.type, p+1])

    @classmethod
    def showClass(cls, typ):
        t = gdb.lookup_type(typ)
        for i in t.fields():
            print (i.type, i.name, i.is_base_class)

        cls.showClassInheritance(typ)

    @classmethod
    def Load(cls, filename):
        pass

