"""Provide common functions shared among different Go code generation modules."""
import re
from typing import List, Union, cast, Iterator

from icontract import ensure, require

from aas_core_codegen import intermediate
from aas_core_codegen.common import Stripped, assert_never
from aas_core_codegen.golang import naming as golang_naming


@ensure(lambda result: result.startswith('"'))
@ensure(lambda result: result.endswith('"'))
def string_literal(text: str) -> Stripped:
    """Generate a Go string literal from the ``text``."""
    escaped = []  # type: List[str]

    for character in text:
        if character == "\a":
            escaped.append("\\a")
        elif character == "\b":
            escaped.append("\\b")
        elif character == "\f":
            escaped.append("\\f")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif character == "\t":
            escaped.append("\\t")
        elif character == "\v":
            escaped.append("\\v")
        elif character == '"':
            escaped.append('\\"')
        elif character == "\\":
            escaped.append("\\\\")
        else:
            escaped.append(character)

    return Stripped('"{}"'.format("".join(escaped)))


def needs_escaping(text: str) -> bool:
    """Check whether the ``text`` contains a character that needs escaping."""
    for character in text:
        if character == "\a":
            return True
        elif character == "\b":
            return True
        elif character == "\f":
            return True
        elif character == "\n":
            return True
        elif character == "\r":
            return True
        elif character == "\t":
            return True
        elif character == "\v":
            return True
        elif character == '"':
            return True
        elif character == "\\":
            return True
        else:
            pass

    return False


PRIMITIVE_TYPE_MAP = {
    intermediate.PrimitiveType.BOOL: Stripped("bool"),
    intermediate.PrimitiveType.INT: Stripped("int64"),
    intermediate.PrimitiveType.FLOAT: Stripped("float64"),
    intermediate.PrimitiveType.STR: Stripped("string"),
    intermediate.PrimitiveType.BYTEARRAY: Stripped("[]byte"),
}


def _assert_all_primitive_types_are_mapped() -> None:
    """Assert that we have explicitly mapped all the primitive types to Go."""
    all_primitive_literals = set(literal.value for literal in PRIMITIVE_TYPE_MAP)

    mapped_primitive_literals = set(
        literal.value for literal in intermediate.PrimitiveType
    )

    all_diff = all_primitive_literals.difference(mapped_primitive_literals)
    mapped_diff = mapped_primitive_literals.difference(all_primitive_literals)

    messages = []  # type: List[str]
    if len(mapped_diff) > 0:
        messages.append(
            f"More primitive maps are mapped than there were defined "
            f"in the ``intermediate._types``: {sorted(mapped_diff)}"
        )

    if len(all_diff) > 0:
        messages.append(
            f"One or more primitive types in the ``intermediate._types`` were not "
            f"mapped in PRIMITIVE_TYPE_MAP: {sorted(all_diff)}"
        )

    if len(messages) > 0:
        raise AssertionError("\n\n".join(messages))


_assert_all_primitive_types_are_mapped()


def generate_type(type_annotation: intermediate.TypeAnnotationUnion) -> Stripped:
    """Generate the Go type for the given type annotation."""
    if isinstance(type_annotation, intermediate.PrimitiveTypeAnnotation):
        return PRIMITIVE_TYPE_MAP[type_annotation.a_type]

    elif isinstance(type_annotation, intermediate.OurTypeAnnotation):
        our_type = type_annotation.our_type

        if isinstance(our_type, intermediate.Enumeration):
            return Stripped(golang_naming.enum_name(type_annotation.our_type.name))

        elif isinstance(our_type, intermediate.ConstrainedPrimitive):
            return PRIMITIVE_TYPE_MAP[our_type.constrainee]

        elif isinstance(our_type, intermediate.Class):
            # NOTE (mristin, 2023-01-13):
            # Always prefer an interface to allow for discrimination. If there is
            # an interface based on the class, it means that there are one or more
            # descendants.

            if our_type.interface:
                return Stripped(golang_naming.interface_name(our_type.name))
            else:
                # NOTE (mristin, 2023-01-13):
                # We use pointers to avoid copying-by-value. This is arguable.
                # See https://stackoverflow.com/questions/28501976/embedding-in-go-with-pointer-or-with-value
                # for a discussion.
                return Stripped(f"*{golang_naming.class_name(our_type.name)}")

    elif isinstance(type_annotation, intermediate.ListTypeAnnotation):
        item_type = generate_type(type_annotation=type_annotation.items)

        return Stripped(f"[]{item_type}")

    elif isinstance(type_annotation, intermediate.OptionalTypeAnnotation):
        value = generate_type(type_annotation=type_annotation.value)
        if isinstance(type_annotation.value, intermediate.PrimitiveTypeAnnotation):
            return Stripped(f"*{value}")

        # NOTE (mristin, 2023-01-13):
        # All the other types are pointer types by our definition. Hence, we do not
        # prefix with a ``*``, as we would otherwise generate a pointer to a pointer.
        return value

    else:
        assert_never(type_annotation)

    raise AssertionError("Should not have gotten here")


# NOTE (mristin, 2023-01-13):
# See: https://stackoverflow.com/questions/19094704/indentation-in-go-tabs-or-spaces
INDENT = "\t"
INDENT2 = INDENT * 2
INDENT3 = INDENT * 3
INDENT4 = INDENT * 4
INDENT5 = INDENT * 5
INDENT6 = INDENT * 6


WARNING = Stripped(
    """\
/*
 * This code has been automatically generated by aas-core-codegen.
 * Do NOT edit or append.
 */"""
)
