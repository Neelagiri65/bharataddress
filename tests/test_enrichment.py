from bharataddress import extract_state_from_gstin


def test_karnataka_gstin():
    # 29 = Karnataka. Synthetic structurally-valid GSTIN.
    assert extract_state_from_gstin("29ABCDE1234F1Z5") == "Karnataka"


def test_maharashtra_gstin():
    assert extract_state_from_gstin("27ABCDE1234F1Z5") == "Maharashtra"


def test_telangana_gstin():
    assert extract_state_from_gstin("36ABCDE1234F1Z5") == "Telangana"


def test_malformed_returns_none():
    assert extract_state_from_gstin("not a gstin") is None
    assert extract_state_from_gstin("") is None
    assert extract_state_from_gstin("27ABCDE1234F1Z") is None  # too short


def test_lowercase_is_normalised():
    assert extract_state_from_gstin("29abcde1234f1z5") == "Karnataka"
