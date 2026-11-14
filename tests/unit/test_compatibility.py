from camera_daily_merger.app.probe import FIELDS, Probe, compatibility_differences


def stream(**values):
    return tuple(values.get(field) for field in FIELDS)


def test_derived_video_rate_is_informational_and_layout_stays_strict():
    reference = Probe(
        1, (stream(codec_type="video", codec_name="h264", r_frame_rate="25/1"),)
    )
    assert compatibility_differences(reference, reference) == []
    changed = Probe(
        1, (stream(codec_type="video", codec_name="h264", r_frame_rate="20/1"),)
    )
    assert compatibility_differences(reference, changed) == []
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


def test_timebase_codec_headers_and_audio_rate_remain_strict():
    reference = Probe(
        1,
        (
            stream(
                codec_type="video",
                codec_name="h264",
                time_base="1/23900",
                extradata_hash="SHA256:aaa",
            ),
        ),
    )
    for values, field in [
        (
            {
                "codec_name": "hevc",
                "time_base": "1/23900",
                "extradata_hash": "SHA256:aaa",
            },
            "codec_name",
        ),
        (
            {
                "codec_name": "h264",
                "time_base": "1/24000",
                "extradata_hash": "SHA256:aaa",
            },
            "time_base",
        ),
        (
            {
                "codec_name": "h264",
                "time_base": "1/23900",
                "extradata_hash": "SHA256:bbb",
            },
            "extradata_hash",
        ),
    ]:
        candidate = Probe(1, (stream(codec_type="video", **values),))
        assert compatibility_differences(reference, candidate)[0]["field"] == field
    audio_a = Probe(1, (stream(codec_type="audio", r_frame_rate="0/0"),))
    audio_b = Probe(1, (stream(codec_type="audio", r_frame_rate="1/1"),))
    assert compatibility_differences(audio_a, audio_b)[0]["field"] == "r_frame_rate"
