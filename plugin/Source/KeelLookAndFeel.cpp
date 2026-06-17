#include "KeelLookAndFeel.h"
#include "BinaryData.h"

namespace keel
{

// --- find a bundled .ttf whose original filename contains `match` ---
static juce::Typeface::Ptr loadFace (const char* match)
{
    for (int i = 0; i < BinaryData::namedResourceListSize; ++i)
    {
        const juce::String fn (BinaryData::originalFilenames[i]);
        if (fn.contains (match) && fn.endsWithIgnoreCase (".ttf"))
        {
            int sz = 0;
            if (const char* d = BinaryData::getNamedResource (BinaryData::namedResourceList[i], sz))
                if (d != nullptr && sz > 0)
                    return juce::Typeface::createSystemTypefaceFor (d, (size_t) sz);
        }
    }
    return nullptr;
}

KeelLookAndFeel::KeelLookAndFeel()
{
    regular = loadFace ("Regular");
    medium  = loadFace ("Medium");
    bold    = loadFace ("Bold");

    using namespace palette;
    setColour (juce::ResizableWindow::backgroundColourId, bg);
    setColour (juce::Label::textColourId,                 text);
    setColour (juce::Slider::textBoxTextColourId,         text);
    setColour (juce::Slider::textBoxBackgroundColourId,   surface2);
    setColour (juce::Slider::textBoxOutlineColourId,      line);
    setColour (juce::ComboBox::backgroundColourId,        surface2);
    setColour (juce::ComboBox::textColourId,              text);
    setColour (juce::ComboBox::outlineColourId,           line);
    setColour (juce::ComboBox::arrowColourId,             muted);
    setColour (juce::PopupMenu::backgroundColourId,           surface2);
    setColour (juce::PopupMenu::textColourId,                 text);
    setColour (juce::PopupMenu::highlightedBackgroundColourId, teal_deep);
    setColour (juce::PopupMenu::highlightedTextColourId,      text);
    setColour (juce::ToggleButton::textColourId,          text);
    setColour (juce::TextEditor::highlightColourId,       teal_deep);
}

juce::Typeface::Ptr KeelLookAndFeel::getTypefaceForFont (const juce::Font& f)
{
    if (f.isBold() && bold != nullptr)         return bold;
    if (f.getTypefaceStyle() == "Medium" && medium != nullptr) return medium;
    if (regular != nullptr)                    return regular;
    return juce::LookAndFeel_V4::getTypefaceForFont (f);
}

juce::Font KeelLookAndFeel::display (float pointSize, bool useBold) const
{
    if (auto tf = (useBold && bold != nullptr) ? bold : regular)
        return juce::Font (juce::FontOptions().withTypeface (tf).withPointHeight (pointSize));
    return juce::Font (juce::FontOptions (pointSize, useBold ? juce::Font::bold
                                                            : juce::Font::plain));
}

void KeelLookAndFeel::drawLinearSlider (juce::Graphics& g, int x, int y, int w, int h,
                                        float sliderPos, float, float,
                                        juce::Slider::SliderStyle style,
                                        juce::Slider& s)
{
    if (style != juce::Slider::LinearHorizontal)
    {
        juce::LookAndFeel_V4::drawLinearSlider (g, x, y, w, h, sliderPos,
                                                0.0f, 0.0f, style, s);
        return;
    }

    const float cy = (float) y + (float) h * 0.5f;
    const float trackH = 4.0f;
    juce::Rectangle<float> groove ((float) x, cy - trackH * 0.5f, (float) w, trackH);
    g.setColour (palette::line);
    g.fillRoundedRectangle (groove, 2.0f);

    const float fillW = juce::jmax (0.0f, sliderPos - (float) x);
    if (fillW > 0.5f)
    {
        g.setColour (palette::teal_deep);
        g.fillRoundedRectangle ({ (float) x, cy - trackH * 0.5f, fillW, trackH }, 2.0f);
    }

    const float r = 7.0f;
    g.setColour (s.isEnabled() ? palette::teal : palette::faint);
    g.fillEllipse (sliderPos - r, cy - r, r * 2.0f, r * 2.0f);
}

void KeelLookAndFeel::drawToggleButton (juce::Graphics& g, juce::ToggleButton& b,
                                        bool highlighted, bool)
{
    const float box = 18.0f;
    const float by = ((float) b.getHeight() - box) * 0.5f;
    juce::Rectangle<float> ind (0.0f, by, box, box);

    g.setColour (b.getToggleState() ? palette::teal : palette::surface2);
    g.fillRoundedRectangle (ind, 5.0f);
    g.setColour (b.getToggleState() ? palette::teal
                                    : (highlighted ? palette::teal_deep : palette::line));
    g.drawRoundedRectangle (ind.reduced (0.5f), 5.0f, 1.0f);

    g.setColour (b.findColour (juce::ToggleButton::textColourId));
    g.setFont (display (10.0f));
    g.drawText (b.getButtonText(),
                juce::Rectangle<int> ((int) box + 8, 0,
                                      b.getWidth() - (int) box - 8, b.getHeight()),
                juce::Justification::centredLeft, true);
}

void KeelLookAndFeel::drawComboBox (juce::Graphics& g, int width, int height, bool,
                                    int, int, int, int, juce::ComboBox& box)
{
    juce::Rectangle<float> r (0.0f, 0.0f, (float) width, (float) height);
    g.setColour (palette::surface2);
    g.fillRoundedRectangle (r, 8.0f);
    g.setColour (box.hasKeyboardFocus (false) ? palette::teal : palette::line);
    g.drawRoundedRectangle (r.reduced (0.5f), 8.0f, 1.0f);

    // muted chevron
    const float cx = (float) width - 16.0f, cyc = (float) height * 0.5f;
    juce::Path chevron;
    chevron.startNewSubPath (cx - 4.0f, cyc - 2.0f);
    chevron.lineTo (cx,        cyc + 3.0f);
    chevron.lineTo (cx + 4.0f, cyc - 2.0f);
    g.setColour (palette::muted);
    g.strokePath (chevron, juce::PathStrokeType (1.6f, juce::PathStrokeType::curved,
                                                 juce::PathStrokeType::rounded));
}

// --------------------------------------------------------------------- HullMark
void HullMark::paint (juce::Graphics& g)
{
    const float mx = 8.0f, my = 18.0f, mw = 104.0f, mh = 102.0f, margin = 2.0f;
    auto bounds = getLocalBounds().toFloat();
    const float availW = bounds.getWidth()  - 2.0f * margin;
    const float availH = bounds.getHeight() - 2.0f * margin;
    const float s = juce::jmin (availW / mw, availH / mh);

    const auto t = juce::AffineTransform::translation (-mx, -my)
                       .scaled (s, s)
                       .translated (margin + (availW - mw * s) * 0.5f,
                                    margin + (availH - mh * s) * 0.5f);
    g.addTransform (t);

    juce::ColourGradient grad (palette::teal, 0.0f, my,
                               palette::teal_deep, 0.0f, my + mh, false);

    // closed hull, used to clip the waveform bars
    juce::Path hull;
    hull.startNewSubPath (8.0f, 18.0f);
    hull.lineTo (28.0f, 96.0f);
    hull.quadraticTo (60.0f, 120.0f, 92.0f, 96.0f);
    hull.lineTo (112.0f, 18.0f);
    hull.closeSubPath();

    static const float bars[7][4] = {
        { 56.5f, 30.0f, 7.0f, 80.0f }, { 45.5f, 40.0f, 7.0f, 70.0f },
        { 67.5f, 40.0f, 7.0f, 70.0f }, { 34.5f, 52.0f, 7.0f, 58.0f },
        { 78.5f, 52.0f, 7.0f, 58.0f }, { 23.5f, 66.0f, 7.0f, 44.0f },
        { 89.5f, 66.0f, 7.0f, 44.0f },
    };

    g.saveState();
    g.reduceClipRegion (hull);
    g.setGradientFill (grad);
    for (auto& b : bars)
        g.fillRoundedRectangle (b[0], b[1], b[2], b[3], 3.5f);
    g.restoreState();

    // open-top hull outline
    juce::Path outline;
    outline.startNewSubPath (8.0f, 18.0f);
    outline.lineTo (28.0f, 96.0f);
    outline.quadraticTo (60.0f, 120.0f, 92.0f, 96.0f);
    outline.lineTo (112.0f, 18.0f);
    g.setGradientFill (grad);
    g.strokePath (outline, juce::PathStrokeType (9.0f, juce::PathStrokeType::curved,
                                                 juce::PathStrokeType::rounded));
}

// ------------------------------------------------------------------------ Meter
Meter::Meter (juce::String t, juce::String u, float lo, float hi, KeelLookAndFeel& lnf)
    : title (std::move (t)), unit (std::move (u)), vmin (lo), vmax (hi), look (lnf)
{
}

void Meter::setValue (float v)
{
    if (v <= -99.0f) { hasValue = false; }
    else             { hasValue = true; value = v; }
    repaint();
}

float Meter::frac (float v) const
{
    return juce::jlimit (0.0f, 1.0f, (v - vmin) / (vmax - vmin));
}

void Meter::paint (juce::Graphics& g)
{
    const float w = (float) getWidth(), h = (float) getHeight();
    const bool over = hasValue && hasDanger && value > dangerAbove;

    // title (top-left)
    g.setColour (palette::muted);
    g.setFont (look.display (8.5f));
    g.drawText (title, juce::Rectangle<float> (0.0f, 0.0f, w, 18.0f),
                juce::Justification::centredLeft);

    // numeric readout (top-right)
    juce::String readout = hasValue ? juce::String (value, 1) + " " + unit : "--";
    g.setColour (! hasValue ? palette::faint : (over ? palette::red : palette::teal));
    g.setFont (look.display (16.0f, true));
    g.drawText (readout, juce::Rectangle<float> (0.0f, -2.0f, w, 24.0f),
                juce::Justification::centredRight);

    // track
    const float ty = h - 14.0f, th = 8.0f;
    g.setColour (palette::surface2);
    g.fillRoundedRectangle ({ 0.0f, ty, w, th }, 4.0f);

    // fill
    if (hasValue)
    {
        const float fw = w * frac (value);
        if (fw > 2.0f)
        {
            juce::ColourGradient grad (over ? palette::amber : palette::teal_deep, 0, 0,
                                       over ? palette::red   : palette::teal,
                                       juce::jmax (fw, w), 0.0f, false);
            g.setGradientFill (grad);
            g.fillRoundedRectangle ({ 0.0f, ty, fw, th }, 4.0f);
        }
    }

    // ticks: target (text) + ceiling/danger (red)
    auto tick = [&] (float val, juce::Colour col)
    {
        const float tx = w * frac (val);
        g.setColour (col);
        g.fillRect (juce::Rectangle<float> (tx - 1.0f, ty - 3.0f, 2.0f, th + 6.0f));
    };
    tick (target, palette::text);
    if (hasDanger)
        tick (dangerAbove, palette::red);
}

} // namespace keel
