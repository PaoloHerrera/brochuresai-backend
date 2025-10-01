from api.v1.brochures import _sanitize_filename_component


def test_default_name_when_empty():
    assert _sanitize_filename_component("", default="brochure") == "brochure"


def test_reserved_names_prefixed():
    assert _sanitize_filename_component("CON") == "file_CON"
    assert _sanitize_filename_component("LPT1") == "file_LPT1"
    # Case-insensitive y variantes comunes
    assert _sanitize_filename_component("con") == "file_con"
    assert _sanitize_filename_component("Com9") == "file_Com9"
    # COM0 no es reservado según Windows
    assert _sanitize_filename_component("COM0") == "COM0"


def test_illegal_chars_removed_and_spaces_to_underscores():
    name = "acme <corp> / brochure: 2024"
    out = _sanitize_filename_component(name)
    assert "<" not in out and ">" not in out and "/" not in out and ":" not in out
    assert "__" not in out  # espacios colapsados
    assert "_" in out  # espacios convertidos
    # Comillas y backslash también removidos
    name2 = '"acme\\corp" brochure'
    out2 = _sanitize_filename_component(name2)
    assert '"' not in out2 and "\\" not in out2


def test_max_length_truncated():
    long = "a" * 200
    out = _sanitize_filename_component(long, max_length=100)
    assert len(out) == 100


def test_strip_leading_trailing_dots_and_spaces():
    name = "   .acme brochure.   "
    out = _sanitize_filename_component(name)
    assert not out.startswith(".") and not out.endswith(".")
    assert not out.startswith(" ") and not out.endswith(" ")


def test_crlf_and_control_chars_removed():
    name = "acme\r\n\x00\x1f brochure"
    out = _sanitize_filename_component(name)
    # Control chars eliminados, CRLF removidos
    assert "\r" not in out and "\n" not in out
    for ch in ["\x00", "\x1f"]:
        assert ch not in out


def test_all_illegal_or_whitespace_becomes_default():
    name = "   ...   \r\n\t"
    out = _sanitize_filename_component(name, default="brochure")
    assert out == "brochure"


def test_reserved_with_extension_not_prefixed():
    # "CON.txt" no debe tratarse como reservado
    name = "CON.txt"
    out = _sanitize_filename_component(name)
    assert out == "CON.txt"
