from bharataddress import geocode, parse, reverse_geocode


def test_geocode_returns_none_when_dataset_lacks_centroids():
    # Shipped pincodes.json has no latitude/longitude today, so this is the
    # documented behaviour. The day centroids are added, this test should be
    # updated to assert a coordinate.
    p = parse("Flat 302, Sector 31, Gurgaon 122001")
    assert geocode(p) is None


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
