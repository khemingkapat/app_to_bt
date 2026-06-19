from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class ProcessPdfRequest(_message.Message):
    __slots__ = ("pdf_bytes",)
    PDF_BYTES_FIELD_NUMBER: _ClassVar[int]
    pdf_bytes: bytes
    def __init__(self, pdf_bytes: _Optional[bytes] = ...) -> None: ...

class ProcessPdfResponse(_message.Message):
    __slots__ = ("pdf_id", "values", "registry_json")
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PDF_ID_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    REGISTRY_JSON_FIELD_NUMBER: _ClassVar[int]
    pdf_id: str
    values: _containers.ScalarMap[str, str]
    registry_json: str
    def __init__(self, pdf_id: _Optional[str] = ..., values: _Optional[_Mapping[str, str]] = ..., registry_json: _Optional[str] = ...) -> None: ...

class GeneratePdfRequest(_message.Message):
    __slots__ = ("pdf_bytes", "form_data")
    class FormDataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    PDF_BYTES_FIELD_NUMBER: _ClassVar[int]
    FORM_DATA_FIELD_NUMBER: _ClassVar[int]
    pdf_bytes: bytes
    form_data: _containers.ScalarMap[str, str]
    def __init__(self, pdf_bytes: _Optional[bytes] = ..., form_data: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GeneratePdfResponse(_message.Message):
    __slots__ = ("pdf_bytes",)
    PDF_BYTES_FIELD_NUMBER: _ClassVar[int]
    pdf_bytes: bytes
    def __init__(self, pdf_bytes: _Optional[bytes] = ...) -> None: ...

class GenerateDocxRequest(_message.Message):
    __slots__ = ("docx_bytes", "form_data")
    class FormDataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DOCX_BYTES_FIELD_NUMBER: _ClassVar[int]
    FORM_DATA_FIELD_NUMBER: _ClassVar[int]
    docx_bytes: bytes
    form_data: _containers.ScalarMap[str, str]
    def __init__(self, docx_bytes: _Optional[bytes] = ..., form_data: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GenerateDocxResponse(_message.Message):
    __slots__ = ("docx_bytes",)
    DOCX_BYTES_FIELD_NUMBER: _ClassVar[int]
    docx_bytes: bytes
    def __init__(self, docx_bytes: _Optional[bytes] = ...) -> None: ...

class StampSignatureRequest(_message.Message):
    __slots__ = ("pdf_bytes", "signature_image_bytes", "pdf_id", "registry_json", "cache_mapping_json")
    PDF_BYTES_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_IMAGE_BYTES_FIELD_NUMBER: _ClassVar[int]
    PDF_ID_FIELD_NUMBER: _ClassVar[int]
    REGISTRY_JSON_FIELD_NUMBER: _ClassVar[int]
    CACHE_MAPPING_JSON_FIELD_NUMBER: _ClassVar[int]
    pdf_bytes: bytes
    signature_image_bytes: bytes
    pdf_id: str
    registry_json: str
    cache_mapping_json: str
    def __init__(self, pdf_bytes: _Optional[bytes] = ..., signature_image_bytes: _Optional[bytes] = ..., pdf_id: _Optional[str] = ..., registry_json: _Optional[str] = ..., cache_mapping_json: _Optional[str] = ...) -> None: ...

class StampSignatureResponse(_message.Message):
    __slots__ = ("pdf_bytes",)
    PDF_BYTES_FIELD_NUMBER: _ClassVar[int]
    pdf_bytes: bytes
    def __init__(self, pdf_bytes: _Optional[bytes] = ...) -> None: ...
