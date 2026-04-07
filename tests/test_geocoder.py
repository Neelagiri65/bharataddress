from bharataddress import geocode, parse, reverse_geocode


def test_geocode_returns_centroid_for_known_pincode():
    p = parse("Flat 302, Sector 31, Gurgaon 122001")
    ll = geocode(p)
    assert ll is not None
    lat, lng = ll
    # Gurgaon is roughly (28.46, 77.03). Allow generous bounds — this is a
    # pincode-area centroid, not a point geocode.
    assert 28.0 < lat < 29.0
    assert 76.5 < lng < 77.5


def test_reverse_geocode_finds_nearest_pincode():
    # Same Gurgaon coordinates should round-trip to a pincode in the 1220xx range.
    r = reverse_geocode(28.46, 77.03)
    assert r["pincode"] is not None
    assert r["pincode"].startswith("122")
    assert r["distance_km"] is not None and r["distance_km"] < 50


def test_geocode_none_for_no_pincode():
    p = parse("just some random text")
    assert geocode(p) is None


def test_reverse_geocode_always_returns_digipin():
    r = reverse_geocode(28.6129, 77.2295)  # India Gate, Delhi
    assert r["digipin"] is not None
    assert len(r["digipin"].replace("-", "")) == 10


def test_reverse_geocode_out_of_bounds_digipin_none():
    r = reverse_geocode(0.0, 0.0)
    assert r["digipin"] is None
