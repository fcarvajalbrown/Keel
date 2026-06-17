// Keel plugin -- visual language.
//
// Ports the standalone GUI's look (gui_theme.py) into JUCE so the plugin and the
// desktop app share one identity: the teal brand palette, the Space Grotesk
// family (embedded, SIL OFL), card panels, the hull+waveform mark, and the
// gradient LUFS / true-peak meter with target + ceiling ticks. Presentation only;
// nothing here touches the DSP.

#pragma once

#include <juce_gui_basics/juce_gui_basics.h>

namespace keel
{

// Palette -- lifted verbatim from gui_theme.COLORS (the logo gradient is teal ->
// teal_deep). Keep these in sync with the Python theme if it changes.
namespace palette
{
    const juce::Colour bg        { 0xff0E1314 };  // window background
    const juce::Colour surface   { 0xff151B1D };  // cards / panels
    const juce::Colour surface2  { 0xff1C2427 };  // inputs / elevated controls
    const juce::Colour line      { 0xff283133 };  // hairline borders / grooves
    const juce::Colour text      { 0xffE7EEED };  // primary text
    const juce::Colour muted     { 0xff8A9A9C };  // secondary text / labels
    const juce::Colour faint     { 0xff5C6B6E };  // tertiary / disabled
    const juce::Colour teal      { 0xff27D2C0 };  // accent (logo top stop)
    const juce::Colour teal_hi   { 0xff46E2D2 };  // accent hover
    const juce::Colour teal_deep { 0xff0C8C81 };  // accent deep (logo bottom)
    const juce::Colour ink       { 0xff06201E };  // text on a teal fill
    const juce::Colour amber     { 0xffE8B14C };  // caution
    const juce::Colour red       { 0xffF0594F };  // over a ceiling / danger
}

// Registers the bundled Space Grotesk weights and hands them out. Falls back to
// the JUCE default sans if the binary data is missing.
class KeelLookAndFeel : public juce::LookAndFeel_V4
{
public:
    KeelLookAndFeel();

    juce::Typeface::Ptr getTypefaceForFont (const juce::Font&) override;

    // teal sub-page + round teal handle, like the GUI's QSlider.
    void drawLinearSlider (juce::Graphics&, int x, int y, int w, int h,
                           float sliderPos, float minPos, float maxPos,
                           juce::Slider::SliderStyle, juce::Slider&) override;

    // teal-filled rounded check, like the GUI's QCheckBox indicator.
    void drawToggleButton (juce::Graphics&, juce::ToggleButton&,
                           bool shouldDrawButtonAsHighlighted,
                           bool shouldDrawButtonAsDown) override;

    // rounded combo with a muted chevron.
    void drawComboBox (juce::Graphics&, int width, int height, bool isButtonDown,
                       int buttonX, int buttonY, int buttonW, int buttonH,
                       juce::ComboBox&) override;

    // A display font in the embedded family at a point size / weight.
    juce::Font display (float pointSize, bool bold = false) const;

private:
    juce::Typeface::Ptr regular, medium, bold;
};

// The hull + balanced-waveform logo, painted in the teal gradient (geometry from
// assets/keel-logo.svg, same drawing as gui_theme.HullMark).
class HullMark : public juce::Component
{
public:
    void paint (juce::Graphics&) override;
};

// A horizontal LUFS / true-peak meter: title (top-left) + big readout (top-right)
// + gradient bar with target / ceiling ticks. Display-only; fed setValue().
class Meter : public juce::Component
{
public:
    Meter (juce::String title, juce::String unit, float vmin, float vmax,
           KeelLookAndFeel& lnf);

    void setTarget (float t)       { target = t; }
    void setDangerAbove (float d)  { dangerAbove = d; hasDanger = true; }
    void setValue (float v);       // pass -100 (or below floor) for "no signal"

    void paint (juce::Graphics&) override;

private:
    float frac (float v) const;

    juce::String title, unit;
    float vmin, vmax;
    float target { 0.0f };
    float dangerAbove { 0.0f };
    bool  hasDanger { false };
    bool  hasValue { false };
    float value { 0.0f };
    KeelLookAndFeel& look;
};

} // namespace keel
