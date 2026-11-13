from camera_daily_merger.app.probe import FIELDS, Probe, compatibility_differences


def stream(**values):
    return tuple(values.get(field) for field in FIELDS)


def test_layout_and_frame_rate_differences_are_named_without_relaxing_policy():
    reference = Probe(
        1, (stream(codec_type="video", codec_name="h264", r_frame_rate="25/1"),)
    )
    assert compatibility_differences(reference, reference) == []
    changed = Probe(
        1, (stream(codec_type="video", codec_name="h264", r_frame_rate="20/1"),)
    )
    assert compatibility_differences(reference, changed) == [
        {"stream": 0, "field": "r_frame_rate", "expected": "25/1", "actual": "20/1"}
    ]
    audio = Probe(1, (*reference.streams, stream(codec_type="audio", codec_name="aac")))
    assert compatibility_differences(reference, audio)[0]["field"] == "stream_count"


def test_comparison_output_is_bounded_and_control_characters_are_removed():
    reference = Probe(1, (tuple(None for _ in FIELDS),))
    candidate = Probe(1, (tuple("x" * 80 + "\n" for _ in FIELDS),))
    differences = compatibility_differences(reference, candidate)
    assert len(differences) == 12
    assert all(
        len(item["actual"]) <= 40 and "\n" not in item["actual"] for item in differences
    )
