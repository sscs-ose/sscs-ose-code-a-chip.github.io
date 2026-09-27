import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from presentation.figure_style import (
    FigureProfile, contrast_ink, contrast_ratio, luminance, publication_style, review_artists,
)


def test_ieee_final_size_and_type_profile():
    profile = FigureProfile()
    assert profile.width_in == 7.16
    assert profile.png_dpi > 300
    assert 9 <= profile.font_pt <= 10


def test_sequential_palette_remains_ordered_in_grayscale():
    colors = plt.get_cmap("cividis")(np.linspace(0, 1, 256))
    lightness = np.array([luminance(color) for color in colors])
    assert np.all(np.diff(lightness) >= -1e-8)


def test_all_heatmap_annotations_have_high_contrast_without_depending_on_hue():
    for color in plt.get_cmap("cividis")(np.linspace(0, 1, 256)):
        assert contrast_ratio(contrast_ink(color), color) >= 4.5


def test_profile_is_local_and_does_not_change_other_figures_defaults():
    original = matplotlib.rcParams["font.size"]
    with publication_style():
        assert matplotlib.rcParams["font.size"] == 9
    assert matplotlib.rcParams["font.size"] == original


def test_review_rejects_small_labels_and_wrong_export_size():
    profile = FigureProfile()
    with publication_style(profile):
        fig = plt.figure(figsize=(profile.width_in, profile.height_in))
        text = fig.text(0.5, 0.5, "Readable at final size", fontsize=9, ha="center")
    review_artists(fig, profile)
    text.set_fontsize(6)
    with pytest.raises(ValueError, match="9-10 pt"):
        review_artists(fig, profile)
    text.set_fontsize(9)
    fig.set_size_inches(13.5, 3.25)
    with pytest.raises(ValueError, match="physical size"):
        review_artists(fig, profile)
    plt.close(fig)


def test_review_rejects_clipped_text():
    profile = FigureProfile()
    with publication_style(profile):
        fig = plt.figure(figsize=(profile.width_in, profile.height_in))
        fig.text(1.0, 0.5, "Outside page", fontsize=9, ha="left")
    with pytest.raises(ValueError, match="outside"):
        review_artists(fig, profile)
    plt.close(fig)


def test_review_rejects_labels_that_overlap_at_final_size():
    profile = FigureProfile()
    with publication_style(profile):
        fig = plt.figure(figsize=(profile.width_in, profile.height_in))
        fig.text(0.5, 0.5, "First label", fontsize=9, ha="center")
        fig.text(0.5, 0.5, "Second label", fontsize=9, ha="center")
    with pytest.raises(ValueError, match="overlap"):
        review_artists(fig, profile)
    plt.close(fig)


def test_standalone_pvt_figures_disclose_unqualified_rc_model_without_changing_data():
    from presentation import pvt45_results as pvt

    data = pvt.load_results()
    frame = data["frame"]
    before = frame.copy(deep=True)
    for factory, height in (
        (lambda: pvt.timing_figure(frame), 1.95),
        (lambda: pvt.tradeoff_figure(frame), 2.90),
        (lambda: pvt.worst_case_figure(data), 2.55),
    ):
        fig = factory()
        try:
            assert pvt.RC_MODEL_LABEL in [text.get_text() for text in fig.texts]
            review_artists(fig, FigureProfile(height_in=height))
        finally:
            plt.close(fig)
    assert frame.equals(before)
    table = pvt.comparison_table(frame).set_index("implementation")
    assert table.loc["Extracted RC", "correct_at_1ns"] == 156
    assert table.loc["Extracted RC", "correct_at_2ns"] == 180
