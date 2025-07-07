from core.schema import *

def format_annotation_for_display(annotation: FieldAnnotation) -> str:
    """Format FieldAnnotation for readable display."""
    if annotation.container == ContainerType.OPTIONAL and annotation.args:
        inner = format_annotation_for_display(annotation.args[0])
        return f"Optional[{inner}]"
    elif annotation.container == ContainerType.ARRAY and annotation.args:
        inner = format_annotation_for_display(annotation.args[0])
        return f"Array[{inner}]"
    elif annotation.container == ContainerType.UNION and annotation.args:
        inner_types = [format_annotation_for_display(arg) for arg in annotation.args]
        return f"Union[{', '.join(inner_types)}]"
    elif annotation.custom_type:
        return annotation.custom_type
    elif annotation.base_type:
        return annotation.base_type.value
    else:
        return "unknown"
