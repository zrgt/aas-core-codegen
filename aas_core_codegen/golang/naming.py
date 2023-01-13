"""
Generate Go identifiers based on the identifiers from the meta-model.

The methods all generate public names (capitalized), unless their prefix indicates
otherwise.
"""
from typing import Union, List

from icontract import require

import aas_core_codegen.naming
from aas_core_codegen import intermediate
from aas_core_codegen.common import Identifier, assert_never


@require(lambda identifier_part: len(identifier_part) > 0)
@require(lambda identifier_part: '_' not in identifier_part)
def _capitalize_or_leave_abbreviation(identifier_part: str) -> str:
    """
    Capitalize the first letter of ``text`` if it does not start with a capital letter.

    If the text already starts with a capital letter or a number, it is returned as-is.
    We thus assume that ``text`` is an abbreviation.

    >>> _capitalize_or_leave_abbreviation("something")
    'Something'

    >>> _capitalize_or_leave_abbreviation("SoMeThing")
    'SoMeThing'

    >>> _capitalize_or_leave_abbreviation("1something")
    '1something'

    >>> _capitalize_or_leave_abbreviation("URL")
    'URL'
    """
    if identifier_part[0].isupper():
        return identifier_part

    return identifier_part.capitalize()


def _capital_camel_case(identifier: Identifier) -> Identifier:
    """
    Generate a capital Go camel-case name for something.

    This is usually used for public methods, members *etc.*

    >>> _capital_camel_case(Identifier("something"))
    'Something'

    >>> _capital_camel_case(Identifier("URL_to_something"))
    'URLToSomething'

    >>> _capital_camel_case(Identifier("something_to_URL"))
    'SomethingToURL'
    """
    parts = identifier.split("_")

    return Identifier(
        "".join(
            _capitalize_or_leave_abbreviation(part)
            for part in parts
            if len(part) > 0
        )
    )


def _lower_camel_case(identifier: Identifier) -> Identifier:
    """
    Generate a lower-case Go camel-case name for something.

    This is usually used for private methods, members *etc.*

    >>> _lower_camel_case(Identifier("something"))
    'something'

    >>> _lower_camel_case(Identifier("Something"))
    'something'

    >>> _lower_camel_case(Identifier("URL_to_something"))
    'urlToSomething'

    >>> _lower_camel_case(Identifier("Something_to_URL"))
    'somethingToURL'
    """
    parts = identifier.split("_")

    cased = []  # type: List[str]
    parts_it = iter(parts)
    part = next(parts_it, None)
    assert part is not None, "Expected a non-empty identifier"

    cased.append(part.lower())

    part = next(parts_it, None)
    while part is not None:
        cased.append(_capitalize_or_leave_abbreviation(part))
        part = next(parts_it, None)

    return Identifier("".join(cased))


def interface_name(identifier: Identifier) -> Identifier:
    """Generate a Go public interface name based on its meta-model ``identifier``."""
    return _capital_camel_case(identifier)


def enum_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a public enum based on its meta-model ``identifier``.

    >>> enum_name(Identifier("something"))
    'Something'

    >>> enum_name(Identifier("URL_to_something"))
    'URLToSomething'
    """
    return _capital_camel_case(identifier)


def enum_literal_name(enumeration_name: Identifier, literal_name: Identifier) -> Identifier:
    """
    Generate a Go name for a public enum literal by prefixing it with the enumeration.

    >>> enum_literal_name(Identifier("URL"), Identifier("ID_short"))
    'URLIDShort'
    """
    return _capital_camel_case(enumeration_name) + _capital_camel_case(literal_name)


def class_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a public class based on its meta-model ``identifier``.

    >>> class_name(Identifier("something"))
    'Something'

    >>> class_name(Identifier("URL_to_something"))
    'URLToSomething'
    """
    return _capital_camel_case(identifier)


def property_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a public property based on its meta-model ``identifier``.

    >>> property_name(Identifier("something"))
    'Something'

    >>> property_name(Identifier("something_to_URL"))
    'SomethingToURL'
    """
    return _capital_camel_case(identifier)


def private_property_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a private property based on the ``identifier``.

    >>> private_property_name(Identifier("something"))
    'something'

    >>> private_property_name(Identifier("something_to_URL"))
    'somethingToURL'
    """
    return _lower_camel_case(identifier)


def private_method_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a private method based on the ``identifier``.

    >>> private_method_name(Identifier("something"))
    'something'

    >>> private_method_name(Identifier("something_to_URL"))
    'somethingToURL'
    """
    return _lower_camel_case(identifier)


def method_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a member method based on its meta-model ``identifier``.

    >>> method_name(Identifier("do_something"))
    'DoSomething'

    >>> method_name(Identifier("do_something_to_URL"))
    'DoSomethingToURL'
    """
    return _capital_camel_case(identifier)


def argument_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for an argument based on its meta-model ``identifier``.

    >>> argument_name(Identifier("something"))
    'something'

    >>> argument_name(Identifier("something_to_URL"))
    'somethingToURL'
    """
    return _lower_camel_case(identifier)


def variable_name(identifier: Identifier) -> Identifier:
    """
    Generate a Go name for a variable based on its meta-model ``identifier``.

    >>> variable_name(Identifier("something"))
    'something'

    >>> variable_name(Identifier("something_to_URL"))
    'somethingToURL'
    """
    return _lower_camel_case(identifier)
