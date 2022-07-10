"""Render descriptions to C# documentation comments."""
import io
import textwrap
import xml.sax.saxutils
from typing import Tuple, Optional, List

import docutils.nodes
import docutils.parsers.rst.roles
import docutils.utils
from icontract import require

from aas_core_codegen import intermediate
from aas_core_codegen.common import Stripped, Error, assert_never, Identifier
from aas_core_codegen.csharp import (
    naming as csharp_naming,
)
from aas_core_codegen.csharp.common import INDENT as I
from aas_core_codegen.intermediate import (
    doc as intermediate_doc,
    rendering as intermediate_rendering,
    _translate as intermediate_translate,
)


class _ElementRenderer(intermediate_rendering.DocutilsElementTransformer[str]):
    """Render descriptions as C# docstring XML."""

    def transform_text(
        self, element: docutils.nodes.Text
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        return xml.sax.saxutils.escape(element.astext()), None

    def transform_reference_to_our_type_in_doc(
        self, element: intermediate_doc.ReferenceToOurType
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        name = None  # type: Optional[str]

        if isinstance(element.our_type, intermediate.Enumeration):
            name = csharp_naming.enum_name(element.our_type.name)

        elif isinstance(element.our_type, intermediate.ConstrainedPrimitive):
            # NOTE (mristin, 2021-12-17):
            # We do not generate a class for constrained primitives, but we
            # leave it as class name, as that is what we used for ``Verify*`` function.
            name = csharp_naming.class_name(element.our_type.name)

        elif isinstance(element.our_type, intermediate.Class):
            if isinstance(element.our_type, intermediate.AbstractClass):
                # NOTE (mristin, 2021-12-25):
                # We do not generate C# code for abstract classes, so we have to refer
                # to the interface.
                name = csharp_naming.interface_name(element.our_type.name)

            elif isinstance(element.our_type, intermediate.ConcreteClass):
                # NOTE (mristin, 2021-12-25):
                # Though a concrete class can have multiple descendants and the writer
                # might actually want to refer to the *interface* instead of
                # the concrete class, we do the best effort here and resolve it to the
                # name of the concrete class.
                name = csharp_naming.class_name(element.our_type.name)

            else:
                assert_never(element.our_type)

        else:
            # NOTE (mristin, 2022-03-30):
            # This is a very special case where we had problems with an interface.
            # We leave this check here, just in case the bug resurfaces.
            if isinstance(element.our_type, intermediate_translate._PlaceholderOurType):
                return None, [
                    f"Unexpected placeholder for our type: {element.our_type}; "
                    f"this is a bug"
                ]

            assert_never(element.our_type)

        assert name is not None

        # NOTE (mristin, 2022-06-19):
        # We need to prefix the cref in case there are naming conflicts.
        prefixed_name = f"Aas.{name}"

        return f"<see cref={xml.sax.saxutils.quoteattr(prefixed_name)} />", None

    def transform_reference_to_attribute_in_doc(
        self, element: intermediate_doc.ReferenceToAttribute
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        cref = None  # type: Optional[str]

        if isinstance(element.reference, intermediate_doc.ReferenceToProperty):
            name_of_our_type = None  # type: Optional[str]

            if isinstance(element.reference.cls, intermediate.AbstractClass):
                # We do not generate C# code for abstract classes, so we have to refer
                # to the interface.
                name_of_our_type = csharp_naming.interface_name(
                    element.reference.cls.name
                )
            elif isinstance(element.reference.cls, intermediate.ConcreteClass):
                # NOTE (mristin, 2021-12-25):
                # Though a concrete class can have multiple descendants and the writer
                # might actually want to refer to the *interface* instead of
                # the concrete class, we do the best effort here and resolve it to the
                # name of the concrete class.

                name_of_our_type = csharp_naming.class_name(element.reference.cls.name)
            else:
                assert_never(element.reference.cls)

            prop_name = csharp_naming.property_name(element.reference.prop.name)

            assert name_of_our_type is not None
            cref = f"{name_of_our_type}.{prop_name}"
        elif isinstance(
            element.reference, intermediate_doc.ReferenceToEnumerationLiteral
        ):
            name_of_our_type = csharp_naming.enum_name(
                element.reference.enumeration.name
            )
            literal_name = csharp_naming.enum_literal_name(
                element.reference.literal.name
            )

            cref = f"{name_of_our_type}.{literal_name}"
        else:
            # NOTE (mristin, 2022-03-30):
            # This is a very special case where we had problems with an interface.
            # We leave this check here, just in case the bug resurfaces.
            if isinstance(
                element.reference,
                intermediate_translate._PlaceholderReferenceToAttribute,
            ):
                return None, [
                    f"Unexpected placeholder "
                    f"for the attribute reference: {element.reference}; "
                    f"this is a bug"
                ]

            assert_never(element.reference)

        assert cref is not None

        # NOTE (mristin, 2022-06-19):
        # We need to prefix the cref in case there are naming conflicts.
        prefixed_cref = f"Aas.{cref}"

        return f"<see cref={xml.sax.saxutils.quoteattr(prefixed_cref)} />", None

    def transform_reference_to_argument_in_doc(
        self, element: intermediate_doc.ReferenceToArgument
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        arg_name = csharp_naming.argument_name(Identifier(element.reference))
        return f"<paramref name={xml.sax.saxutils.quoteattr(arg_name)} />", None

    def transform_reference_to_constraint_in_doc(
        self, element: intermediate_doc.ReferenceToConstraint
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        return f"Constraint {element.reference}", None

    def transform_reference_to_constant_in_doc(
        self, element: intermediate_doc.ReferenceToConstant
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        constant_as_prop_name = csharp_naming.property_name(element.constant.name)
        cref = f"Aas.Constants.{constant_as_prop_name}"

        return f"<see cref={xml.sax.saxutils.quoteattr(cref)} />", None

    def transform_literal(
        self, element: docutils.nodes.literal
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        return f"<c>{xml.sax.saxutils.escape(element.astext())}</c>", None

    def transform_paragraph(
        self, element: docutils.nodes.paragraph
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "".join(parts), None

    def transform_emphasis(
        self, element: docutils.nodes.emphasis
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = []  # type: List[str]
        for child in element.children:
            text, error = self.transform(child)
            if error is not None:
                return None, error

            assert text is not None
            parts.append(text)

        return "<em>{}</em>".format("".join(parts)), None

    def transform_list_item(
        self, element: docutils.nodes.list_item
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = []  # type: List[str]
        errors = []  # type: List[str]

        for child in element.children:
            text, child_errors = self.transform(child)
            if child_errors is not None:
                errors.extend(child_errors)
            else:
                assert text is not None
                parts.append(text)

        if len(errors) > 0:
            return None, errors

        return "<li>{}</li>".format("".join(parts)), None

    def transform_bullet_list(
        self, element: docutils.nodes.bullet_list
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = ["<ul>\n"]
        errors = []  # type: List[str]

        for child in element.children:
            text, child_errors = self.transform(child)
            if child_errors is not None:
                errors.extend(child_errors)
            else:
                assert text is not None
                parts.append(f"{text}\n")

        if len(errors) > 0:
            return None, errors

        parts.append("</ul>")

        return "".join(parts), None

    def transform_note(
        self, element: docutils.nodes.note
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = []  # type: List[str]
        errors = []  # type: List[str]

        for child in element.children:
            text, child_errors = self.transform(child)
            if child_errors is not None:
                errors.extend(child_errors)
            else:
                assert text is not None
                parts.append(text)

        if len(errors) > 0:
            return None, errors

        return "".join(parts), None

    def transform_reference(
        self, element: docutils.nodes.reference
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        parts = []  # type: List[str]
        errors = []  # type: List[str]

        for child in element.children:
            text, child_errors = self.transform(child)
            if child_errors is not None:
                errors.extend(child_errors)
            else:
                assert text is not None
                parts.append(text)

        if len(errors) > 0:
            return None, errors

        return "".join(parts), None

    def _transform_children_joined_with_double_new_line(
        self, element: docutils.nodes.Element
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        """Transform the ``element``'s children and join them with a double new-line."""
        if len(element.children) == 0:
            return "", None

        if len(element.children) == 1:
            return self.transform(element.children[0])

        parts = []  # type: List[str]
        errors = []  # type: List[str]

        for child in element.children:
            part, child_errors = self.transform(child)
            if child_errors is not None:
                errors.extend(child_errors)
            else:
                assert part is not None
                parts.append(part)

        if len(errors) > 0:
            return None, errors

        return "\n\n".join(parts), None

    def transform_field_body(
        self, element: docutils.nodes.field_body
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        return self._transform_children_joined_with_double_new_line(element=element)

    def transform_document(
        self, element: docutils.nodes.field_body
    ) -> Tuple[Optional[str], Optional[List[str]]]:
        return self._transform_children_joined_with_double_new_line(element=element)


@require(lambda line: "\n" not in line)
def _slash_slash_slash_line(line: str) -> str:
    """Prepend ``///`` to the ``line``."""
    if len(line) == 0:
        return "///"

    return f"/// {line}"


def _generate_summary_remarks(
    description: intermediate.SummaryRemarksDescription,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for a summary-remarks-constraints."""
    errors = []  # type: List[Error]
    renderer = _ElementRenderer()

    summary, summary_errors = renderer.transform(description.summary)
    if summary_errors is not None:
        errors.extend(
            Error(description.parsed.node, message) for message in summary_errors
        )

    remarks = []  # type: List[str]
    for remark in description.remarks:
        remark, remark_errors = renderer.transform(remark)
        if remark_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in remark_errors
            )
        else:
            assert remark is not None
            remarks.append(remark)

    if len(errors) > 0:
        return None, errors

    assert summary is not None

    # Don't use textwrap.dedent to preserve the formatting

    blocks = [
        Stripped(
            f"""\
<summary>
{summary}
</summary>"""
        )
    ]

    if len(remarks) > 0:
        remarks_joined = "\n\n".join(remarks)
        blocks.append(
            Stripped(
                f"""\
<remarks>
{remarks_joined}
</remarks>"""
            )
        )

    commented_lines = [
        _slash_slash_slash_line(line) for block in blocks for line in block.splitlines()
    ]

    return Stripped("\n".join(commented_lines)), None


def _generate_summary_remarks_constraints(
    description: intermediate.SummaryRemarksConstraintsDescription,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for a summary-remarks-constraints."""
    errors = []  # type: List[Error]
    renderer = _ElementRenderer()

    summary, summary_errors = renderer.transform(description.summary)
    if summary_errors is not None:
        errors.extend(
            Error(description.parsed.node, message) for message in summary_errors
        )

    remarks = []  # type: List[str]
    for remark in description.remarks:
        remark, remark_errors = renderer.transform(remark)
        if remark_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in remark_errors
            )
        else:
            assert remark is not None
            remarks.append(remark)

    constraints = []  # type: List[str]
    for identifier, body_element in description.constraints_by_identifier.items():
        body, body_errors = renderer.transform(body_element)
        if body_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in body_errors
            )
        else:
            assert body is not None

            constraints.append(
                f"Constraint {xml.sax.saxutils.escape(identifier)}:\n{body}"
            )

    if len(errors) > 0:
        return None, errors

    assert summary is not None

    # Don't use textwrap.dedent to preserve the formatting

    blocks = [
        Stripped(
            f"""\
<summary>
{summary}
</summary>"""
        )
    ]

    if len(constraints) > 0:
        constraints_writer = io.StringIO()
        constraints_writer.write("Constraints:\n<ul>\n")
        for constraint in constraints:
            constraints_writer.write(textwrap.indent(f"<li>\n{constraint}\n</li>\n", I))
        constraints_writer.write("</ul>")
        remarks.append(constraints_writer.getvalue())

    if len(remarks) > 0:
        remarks_joined = "\n\n".join(remarks)
        blocks.append(
            Stripped(
                f"""\
<remarks>
{remarks_joined}
</remarks>"""
            )
        )

    commented_lines = [
        _slash_slash_slash_line(line) for block in blocks for line in block.splitlines()
    ]

    return Stripped("\n".join(commented_lines)), None


def generate_comment_for_meta_model(
    description: intermediate.DescriptionOfMetaModel,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for the given meta-model."""
    return _generate_summary_remarks_constraints(description)


def generate_comment_for_our_type(
    description: intermediate.DescriptionOfOurType,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for our type."""
    return _generate_summary_remarks_constraints(description)


def generate_comment_for_property(
    description: intermediate.DescriptionOfProperty,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for the given property."""
    return _generate_summary_remarks_constraints(description)


def generate_comment_for_enumeration_literal(
    description: intermediate.DescriptionOfEnumerationLiteral,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """Generate the documentation comment for the given enumeration literal."""
    return _generate_summary_remarks(description)


def generate_comment_for_signature(
    description: intermediate.DescriptionOfSignature,
) -> Tuple[Optional[Stripped], Optional[List[Error]]]:
    """
    Generate the documentation comment for the given signature.

    A signature, in this context, means a function or a method signature.
    """
    errors = []  # type: List[Error]
    renderer = _ElementRenderer()

    summary, summary_errors = renderer.transform(description.summary)
    if summary_errors is not None:
        errors.extend(
            Error(description.parsed.node, message) for message in summary_errors
        )

    remarks = []  # type: List[str]
    for remark in description.remarks:
        remark, remark_errors = renderer.transform(remark)
        if remark_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in remark_errors
            )
        else:
            assert remark is not None
            remarks.append(remark)

    params = []  # type: List[Stripped]
    for name, body_element in description.arguments_by_name.items():
        body, body_errors = renderer.transform(body_element)
        if body_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in body_errors
            )
        else:
            assert body is not None

            # Don't use textwrap.dedent to preserve the formatting
            params.append(
                Stripped(
                    f"""\
<param name={xml.sax.saxutils.quoteattr(name)}>
{body}
</param>"""
                )
            )

    returns = None  # type: Optional[str]
    if description.returns is not None:
        # We need to help the type checker in PyCharm a bit.
        assert isinstance(description.returns, docutils.nodes.field_body)

        returns, returns_errors = renderer.transform(description.returns)
        if returns_errors is not None:
            errors.extend(
                Error(description.parsed.node, message) for message in returns_errors
            )
        else:
            assert returns is not None

    if len(errors) > 0:
        return None, errors

    assert summary is not None

    # Don't use textwrap.dedent to preserve the formatting

    blocks = [
        Stripped(
            f"""\
<summary>
{summary}
</summary>"""
        )
    ]

    if len(remarks) > 0:
        remarks_joined = "\n\n".join(remarks)
        blocks.append(
            Stripped(
                f"""\
<remarks>
{remarks_joined}
</remarks>"""
            )
        )

    if len(params) > 0:
        params_joined = "\n".join(params)
        blocks.append(Stripped(params_joined))

    if returns is not None:
        blocks.append(
            Stripped(
                f"""\
<returns>
{returns}
</returns>"""
            )
        )

    commented_lines = [
        _slash_slash_slash_line(line) for block in blocks for line in block.splitlines()
    ]

    return Stripped("\n".join(commented_lines)), None
