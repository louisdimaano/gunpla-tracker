from datetime import date
from kits import read_kit_form, decide_finished_on

TODAY = date(2026, 11, 16)


def good_form(**changes):
    form = {"name": "Gundam Exia", "grade": "HG", "series": "HG Gundam 00",
            "kit_number": "", "status": "Not Started", "difficulty": "",
            "build_quality": "", "finished_on": "", "notes": ""}
    form.update(changes)
    return form


def test_valid_form_has_no_errors():
    values, errors = read_kit_form(good_form(kit_number="15", difficulty="3"))
    assert errors == []
    assert values["name"] == "Gundam Exia"
    assert values["kit_number"] == 15
    assert values["difficulty"] == 3
    assert values["build_quality"] is None
    assert values["notes"] is None


def test_blank_name_is_rejected():
    _, errors = read_kit_form(good_form(name="   "))
    assert errors == ["Give the kit a name."]


def test_unknown_grade_is_rejected():
    _, errors = read_kit_form(good_form(grade="XX"))
    assert errors == ["Pick a grade from the list."]


def test_unknown_status_is_rejected():
    _, errors = read_kit_form(good_form(status="Half done"))
    assert errors == ["Pick a status from the list."]


def test_bad_kit_number_is_rejected():
    for bad in ("15a", "-3", "0"):
        _, errors = read_kit_form(good_form(kit_number=bad))
        assert errors == ["Kit number must be a whole number above 0."]


def test_rating_out_of_range_is_rejected():
    _, errors = read_kit_form(good_form(build_quality="6"))
    assert errors == ["Ratings must be from 1 to 5."]


def test_bad_date_is_rejected():
    _, errors = read_kit_form(good_form(status="Built", finished_on="2026-13-40"))
    assert errors == ["Finished date must be a real date."]


def test_new_painted_kit_gets_todays_date():
    assert decide_finished_on(None, "Painted", None, None, TODAY) == "2026-11-16"


def test_backfilled_date_is_kept():
    assert decide_finished_on(None, "Built", None, "2025-03-01", TODAY) == "2025-03-01"


def test_built_to_painted_moves_date_to_today():
    assert decide_finished_on("Built", "Painted", "2026-01-10", "2026-01-10", TODAY) == "2026-11-16"


def test_date_typed_by_hand_wins():
    assert decide_finished_on("Built", "Painted", "2026-01-10", "2026-02-01", TODAY) == "2026-02-01"


def test_same_status_keeps_its_date():
    assert decide_finished_on("Painted", "Painted", "2026-01-10", "2026-01-10", TODAY) == "2026-01-10"


def test_unfinished_status_clears_date():
    assert decide_finished_on("Built", "Not Started", "2026-01-10", "2026-01-10", TODAY) is None