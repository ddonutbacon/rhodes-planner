from rhodes.core.formatting import fmt_num


def test_fmt_num_handles_integer_and_fractional_quantities():
    assert fmt_num(3) == "3"
    assert fmt_num(1000) == "1,000"
    assert fmt_num(2.5) == "2.5"
    assert fmt_num(2.125) == "2.12"
