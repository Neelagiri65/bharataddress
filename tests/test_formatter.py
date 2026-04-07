from bharataddress import format, parse


SAMPLE = "Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001"


def test_single_line_includes_pincode_and_state():
    p = parse(SAMPLE)
    s = format(p, style="single_line")
    assert "122001" in s
    assert "Haryana" in s
    assert "\n" not in s


def test_india_post_is_multiline():
    p = parse(SAMPLE)
    s = format(p, style="india_post")
    assert "\n" in s
    # State + pincode share the last line.
    assert s.splitlines()[-1].endswith("122001")
    assert "Haryana" in s.splitlines()[-1]


def test_label_style_has_field_labels():
    p = parse(SAMPLE)
    s = format(p, style="label")
    assert "Pincode: 122001" in s
    assert "State: Haryana" in s


def test_unknown_style_raises():
    p = parse(SAMPLE)
    try:
        format(p, style="bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_empty_address_does_not_crash():
    p = parse("")
    assert format(p, style="single_line") == ""
    assert format(p, style="india_post") == ""
