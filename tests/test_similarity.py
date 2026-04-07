from bharataddress import address_similarity


def test_identical_addresses_score_high():
    a = "Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001"
    assert address_similarity(a, a) > 0.8


def test_bengaluru_and_bangalore_match():
    a = "MG Road, Bengaluru 560001"
    b = "Mahatma Gandhi Road, Bangalore 560001"
    assert address_similarity(a, b) > 0.7


def test_different_pincodes_score_low():
    a = "Sector 31, Gurgaon 122001"
    b = "Sector 31, Noida 201301"
    assert address_similarity(a, b) < 0.5


def test_completely_different_addresses_low():
    a = "Sector 31, Gurgaon 122001"
    b = "Anna Salai, Chennai 600002"
    assert address_similarity(a, b) < 0.3


def test_score_is_bounded():
    s = address_similarity("a", "b")
    assert 0.0 <= s <= 1.0
