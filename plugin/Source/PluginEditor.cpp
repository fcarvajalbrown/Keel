#include "PluginEditor.h"

namespace
{
    // Keep these in sync with recipes.PRESETS in the Python engine.
    struct Preset { float lufs, tp; };
    const Preset kPresets[] = {
        { -14.0f, -1.0f },   // Streaming (default, ADR-0003)
        { -10.0f, -1.0f },   // Loud
        { -16.0f, -1.0f },   // Broadcast
    };

    juce::String fmtMeter (float db)
    {
        if (db <= -99.0f)
            return "--.- ";
        return juce::String (db, 1);
    }
}

KeelAudioProcessorEditor::KeelAudioProcessorEditor (KeelAudioProcessor& p)
    : AudioProcessorEditor (&p), processor (p)
{
    auto& apvts = processor.apvts;

    titleLabel.setText ("Keel", juce::dontSendNotification);
    titleLabel.setFont (juce::Font (juce::FontOptions (28.0f, juce::Font::bold)));
    titleLabel.setColour (juce::Label::textColourId, juce::Colours::white);
    addAndMakeVisible (titleLabel);

    subtitleLabel.setText ("self-contained master (master bus)", juce::dontSendNotification);
    subtitleLabel.setColour (juce::Label::textColourId, juce::Colours::grey);
    addAndMakeVisible (subtitleLabel);

    // --- Preset ---
    presetLabel.setText ("Preset", juce::dontSendNotification);
    addAndMakeVisible (presetLabel);
    presetBox.addItem ("Streaming (-14)", 1);
    presetBox.addItem ("Loud (-10)", 2);
    presetBox.addItem ("Broadcast (-16)", 3);
    addAndMakeVisible (presetBox);
    presetAttachment = std::make_unique<ComboAttachment> (apvts, "preset", presetBox);
    presetBox.onChange = [this] { applyPresetToTargets(); };

    // --- Target LUFS ---
    lufsLabel.setText ("Target LUFS", juce::dontSendNotification);
    addAndMakeVisible (lufsLabel);
    lufsSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    lufsSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 64, 20);
    addAndMakeVisible (lufsSlider);
    lufsAttachment = std::make_unique<SliderAttachment> (apvts, "lufs", lufsSlider);

    // --- True-peak ceiling ---
    tpLabel.setText ("TP ceiling (dBTP)", juce::dontSendNotification);
    addAndMakeVisible (tpLabel);
    tpSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    tpSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 64, 20);
    addAndMakeVisible (tpSlider);
    tpAttachment = std::make_unique<SliderAttachment> (apvts, "tp", tpSlider);

    // --- Makeup (drive into the clip/limiter) ---
    makeupLabel.setText ("Makeup (dB)", juce::dontSendNotification);
    addAndMakeVisible (makeupLabel);
    makeupSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    makeupSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 64, 20);
    addAndMakeVisible (makeupSlider);
    makeupAttachment = std::make_unique<SliderAttachment> (apvts, "makeup", makeupSlider);

    // --- Optional toggles ---
    addAndMakeVisible (referenceToggle);
    addAndMakeVisible (glueToggle);
    referenceAttachment = std::make_unique<ButtonAttachment> (apvts, "reference", referenceToggle);
    glueAttachment      = std::make_unique<ButtonAttachment> (apvts, "glue", glueToggle);

    // --- Live meters ---
    lufsMeterLabel.setJustificationType (juce::Justification::centred);
    lufsMeterLabel.setFont (juce::Font (juce::FontOptions (20.0f, juce::Font::bold)));
    lufsMeterLabel.setColour (juce::Label::textColourId, juce::Colours::aqua);
    addAndMakeVisible (lufsMeterLabel);

    tpMeterLabel.setJustificationType (juce::Justification::centred);
    tpMeterLabel.setFont (juce::Font (juce::FontOptions (20.0f, juce::Font::bold)));
    tpMeterLabel.setColour (juce::Label::textColourId, juce::Colours::aqua);
    addAndMakeVisible (tpMeterLabel);

    // --- Export note (no Finalize: this IS the master) ---
    exportNote.setText ("Self-contained master. Set Makeup so the LUFS meter sits "
                        "at target, then export from your DAW with this active.",
                        juce::dontSendNotification);
    exportNote.setColour (juce::Label::textColourId, juce::Colours::grey);
    exportNote.setJustificationType (juce::Justification::centred);
    exportNote.setMinimumHorizontalScale (1.0f);
    addAndMakeVisible (exportNote);

    setSize (420, 400);
    startTimerHz (30);
}

KeelAudioProcessorEditor::~KeelAudioProcessorEditor()
{
    stopTimer();
}

void KeelAudioProcessorEditor::applyPresetToTargets()
{
    const int idx = (int) processor.apvts.getRawParameterValue ("preset")->load();
    if (idx >= 0 && idx < (int) (sizeof (kPresets) / sizeof (kPresets[0])))
    {
        if (auto* lufs = processor.apvts.getParameter ("lufs"))
            lufs->setValueNotifyingHost (
                lufs->convertTo0to1 (kPresets[idx].lufs));
        if (auto* tp = processor.apvts.getParameter ("tp"))
            tp->setValueNotifyingHost (
                tp->convertTo0to1 (kPresets[idx].tp));
    }
}

void KeelAudioProcessorEditor::timerCallback()
{
    const float lufs = processor.momentaryLufs.load();
    const float tp   = processor.truePeakDb.load();

    if (! juce::approximatelyEqual (lufs, lufsMeterValue))
    {
        lufsMeterValue = lufs;
        lufsMeterLabel.setText ("M: " + fmtMeter (lufs) + " LUFS",
                                juce::dontSendNotification);
    }
    if (! juce::approximatelyEqual (tp, tpMeterValue))
    {
        tpMeterValue = tp;
        const bool over = tp > -1.0f;
        tpMeterLabel.setColour (juce::Label::textColourId,
            over ? juce::Colours::orangered : juce::Colours::aqua);
        tpMeterLabel.setText ("TP: " + fmtMeter (tp) + " dBTP",
                              juce::dontSendNotification);
    }
}

void KeelAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (juce::Colour (0xff14181c));

    auto meterArea = getLocalBounds().reduced (16).removeFromBottom (150)
                       .removeFromTop (64);
    g.setColour (juce::Colour (0xff0c0f12));
    g.fillRoundedRectangle (meterArea.toFloat(), 6.0f);
}

void KeelAudioProcessorEditor::resized()
{
    auto r = getLocalBounds().reduced (16);

    titleLabel.setBounds (r.removeFromTop (32));
    subtitleLabel.setBounds (r.removeFromTop (18));
    r.removeFromTop (8);

    auto row = [&r] (int h, int gap = 6) { auto a = r.removeFromTop (h); r.removeFromTop (gap); return a; };

    {
        auto a = row (24);
        presetLabel.setBounds (a.removeFromLeft (120));
        presetBox.setBounds (a);
    }
    {
        auto a = row (24);
        lufsLabel.setBounds (a.removeFromLeft (120));
        lufsSlider.setBounds (a);
    }
    {
        auto a = row (24);
        tpLabel.setBounds (a.removeFromLeft (120));
        tpSlider.setBounds (a);
    }
    {
        auto a = row (24);
        makeupLabel.setBounds (a.removeFromLeft (120));
        makeupSlider.setBounds (a);
    }
    {
        auto a = row (24);
        referenceToggle.setBounds (a.removeFromLeft (160));
        glueToggle.setBounds (a);
    }

    r.removeFromTop (6);
    auto meters = r.removeFromTop (64);
    lufsMeterLabel.setBounds (meters.removeFromLeft (meters.getWidth() / 2));
    tpMeterLabel.setBounds (meters);

    r.removeFromTop (8);
    exportNote.setBounds (r.removeFromTop (40));
}
