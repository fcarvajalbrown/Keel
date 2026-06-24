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
}

KeelAudioProcessorEditor::KeelAudioProcessorEditor (KeelAudioProcessor& p)
    : AudioProcessorEditor (&p), processor (p),
      lufsMeter ("MOMENTARY", "LUFS", -40.0f, 0.0f, look),
      tpMeter   ("TRUE PEAK", "dBTP", -24.0f, 0.0f, look)
{
    setLookAndFeel (&look);
    auto& apvts = processor.apvts;

    addAndMakeVisible (hullMark);

    titleLabel.setText ("Keel", juce::dontSendNotification);
    titleLabel.setFont (look.display (26.0f, true));
    titleLabel.setColour (juce::Label::textColourId, keel::palette::text);
    addAndMakeVisible (titleLabel);

    subtitleLabel.setText ("self-contained master  |  master bus",
                           juce::dontSendNotification);
    subtitleLabel.setFont (look.display (9.5f));
    subtitleLabel.setColour (juce::Label::textColourId, keel::palette::muted);
    addAndMakeVisible (subtitleLabel);

    auto sectionLabel = [this] (juce::Label& l, const juce::String& t)
    {
        l.setText (t, juce::dontSendNotification);
        l.setFont (look.display (10.0f));
        l.setColour (juce::Label::textColourId, keel::palette::muted);
        addAndMakeVisible (l);
    };

    // --- Preset ---
    sectionLabel (presetLabel, "Preset");
    presetBox.addItem ("Streaming (-14)", 1);
    presetBox.addItem ("Loud (-10)", 2);
    presetBox.addItem ("Broadcast (-16)", 3);
    addAndMakeVisible (presetBox);
    presetAttachment = std::make_unique<ComboAttachment> (apvts, "preset", presetBox);
    presetBox.onChange = [this] { applyPresetToTargets(); };

    // --- Target LUFS (a meter reference, not an auto-driver) ---
    sectionLabel (lufsLabel, "Target LUFS");
    lufsSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    lufsSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 56, 22);
    addAndMakeVisible (lufsSlider);
    lufsAttachment = std::make_unique<SliderAttachment> (apvts, "lufs", lufsSlider);

    // --- True-peak ceiling ---
    sectionLabel (tpLabel, "TP ceiling (dBTP)");
    tpSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    tpSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 56, 22);
    addAndMakeVisible (tpSlider);
    tpAttachment = std::make_unique<SliderAttachment> (apvts, "tp", tpSlider);

    // --- Makeup (drive into the clip/limiter) ---
    sectionLabel (makeupLabel, "Makeup (dB)");
    makeupSlider.setSliderStyle (juce::Slider::LinearHorizontal);
    makeupSlider.setTextBoxStyle (juce::Slider::TextBoxRight, false, 56, 22);
    addAndMakeVisible (makeupSlider);
    makeupAttachment = std::make_unique<SliderAttachment> (apvts, "makeup", makeupSlider);

    // --- Bus-glue toggle ---
    addAndMakeVisible (glueToggle);
    glueAttachment = std::make_unique<ButtonAttachment> (apvts, "glue", glueToggle);

    // --- Reference readout (passive; load a file, see its LUFS/TP) ---
    sectionLabel (referenceLabel, "Reference");

    referenceReadout.setText ("No reference loaded", juce::dontSendNotification);
    referenceReadout.setFont (look.display (10.0f));
    referenceReadout.setColour (juce::Label::textColourId, keel::palette::text);
    addAndMakeVisible (referenceReadout);

    addAndMakeVisible (referenceLoadButton);
    referenceLoadButton.onClick = [this]
    {
        referenceChooser = std::make_unique<juce::FileChooser> (
            "Choose a reference track",
            juce::File::getSpecialLocation (juce::File::userMusicDirectory),
            "*.wav;*.aiff;*.aif;*.flac;*.mp3;*.ogg");

        const auto flags = juce::FileBrowserComponent::openMode
                         | juce::FileBrowserComponent::canSelectFiles;
        referenceChooser->launchAsync (flags, [this] (const juce::FileChooser& fc)
        {
            const auto file = fc.getResult();
            if (file.existsAsFile())
                processor.loadReference (file);
        });
    };

    addAndMakeVisible (referenceClearButton);
    referenceClearButton.onClick = [this] { processor.clearReference(); };

    // --- Live meters (display-only, reading the OUTPUT) ---
    lufsMeter.setTarget (-14.0f);
    addAndMakeVisible (lufsMeter);
    tpMeter.setTarget (-1.0f);
    tpMeter.setDangerAbove (-1.0f);
    addAndMakeVisible (tpMeter);

    // --- Export note (no Finalize: this IS the master) ---
    exportNote.setText ("Raise Makeup so MOMENTARY hits target, then export "
                        "with this on.", juce::dontSendNotification);
    exportNote.setFont (look.display (9.0f));
    exportNote.setColour (juce::Label::textColourId, keel::palette::faint);
    exportNote.setJustificationType (juce::Justification::centredTop);
    addAndMakeVisible (exportNote);

    setSize (440, 668);
    startTimerHz (30);
}

KeelAudioProcessorEditor::~KeelAudioProcessorEditor()
{
    stopTimer();
    setLookAndFeel (nullptr);
}

void KeelAudioProcessorEditor::applyPresetToTargets()
{
    const int idx = (int) processor.apvts.getRawParameterValue ("preset")->load();
    if (idx >= 0 && idx < (int) (sizeof (kPresets) / sizeof (kPresets[0])))
    {
        if (auto* lufs = processor.apvts.getParameter ("lufs"))
            lufs->setValueNotifyingHost (lufs->convertTo0to1 (kPresets[idx].lufs));
        if (auto* tp = processor.apvts.getParameter ("tp"))
            tp->setValueNotifyingHost (tp->convertTo0to1 (kPresets[idx].tp));
    }
}

void KeelAudioProcessorEditor::timerCallback()
{
    lufsMeter.setTarget (processor.apvts.getRawParameterValue ("lufs")->load());
    lufsMeter.setValue (processor.momentaryLufs.load());

    const float tpCeil = processor.apvts.getRawParameterValue ("tp")->load();
    tpMeter.setTarget (tpCeil);
    tpMeter.setDangerAbove (tpCeil);
    tpMeter.setValue (processor.truePeakDb.load());

    // Reference readout: "measuring..." -> "<name>:  -14.2 LUFS   -0.8 dBTP".
    juce::String refText;
    if (processor.referenceLoading.load())
        refText = "Measuring " + processor.referenceName + "...";
    else
    {
        const float rl = processor.referenceLufs.load();
        const float rt = processor.referenceTruePeak.load();
        if (processor.referenceName.isEmpty())
            refText = "No reference loaded";
        else if (rl <= -99.0f)
            refText = processor.referenceName + ":  (could not measure)";
        else
            refText = processor.referenceName + ":  "
                    + juce::String (rl, 1) + " LUFS    "
                    + juce::String (rt, 1) + " dBTP";
    }
    if (referenceReadout.getText() != refText)
        referenceReadout.setText (refText, juce::dontSendNotification);
}

void KeelAudioProcessorEditor::paint (juce::Graphics& g)
{
    g.fillAll (keel::palette::bg);

    auto card = [&g] (juce::Rectangle<int> r, const juce::String&)
    {
        g.setColour (keel::palette::surface);
        g.fillRoundedRectangle (r.toFloat(), 12.0f);
        g.setColour (keel::palette::line);
        g.drawRoundedRectangle (r.toFloat().reduced (0.5f), 12.0f, 1.0f);
    };
    card (cardTargets, {});
    card (cardDrive, {});
    card (cardReference, {});
    card (cardMeters, {});
}

void KeelAudioProcessorEditor::resized()
{
    auto r = getLocalBounds().reduced (16);

    // header
    auto header = r.removeFromTop (48);
    hullMark.setBounds (header.removeFromLeft (48).reduced (2));
    header.removeFromLeft (10);
    titleLabel.setBounds (header.removeFromTop (30));
    subtitleLabel.setBounds (header);
    r.removeFromTop (12);

    auto labelledRow = [] (juce::Rectangle<int> row, juce::Label& lab,
                           juce::Component& ctrl)
    {
        lab.setBounds (row.removeFromLeft (118));
        ctrl.setBounds (row);
    };

    // card: Targets (preset + LUFS + TP)
    cardTargets = r.removeFromTop (140);
    {
        auto c = cardTargets.reduced (14);
        labelledRow (c.removeFromTop (28), presetLabel, presetBox);
        c.removeFromTop (8);
        labelledRow (c.removeFromTop (28), lufsLabel, lufsSlider);
        c.removeFromTop (8);
        labelledRow (c.removeFromTop (28), tpLabel, tpSlider);
    }
    r.removeFromTop (12);

    // card: Drive (makeup + glue toggle)
    cardDrive = r.removeFromTop (96);
    {
        auto c = cardDrive.reduced (14);
        labelledRow (c.removeFromTop (28), makeupLabel, makeupSlider);
        c.removeFromTop (10);
        glueToggle.setBounds (c.removeFromTop (24));
    }
    r.removeFromTop (12);

    // card: Reference (passive LUFS/TP readout off a loaded file)
    cardReference = r.removeFromTop (104);
    {
        auto c = cardReference.reduced (14);
        referenceLabel.setBounds (c.removeFromTop (20));
        referenceReadout.setBounds (c.removeFromTop (24));
        c.removeFromTop (8);
        auto row = c.removeFromTop (26);
        referenceClearButton.setBounds (row.removeFromRight (84));
        row.removeFromRight (8);
        referenceLoadButton.setBounds (row);
    }
    r.removeFromTop (12);

    // card: Meters
    cardMeters = r.removeFromTop (170);
    {
        auto c = cardMeters.reduced (14);
        lufsMeter.setBounds (c.removeFromTop (58));
        c.removeFromTop (12);
        tpMeter.setBounds (c.removeFromTop (58));
    }
    r.removeFromTop (10);
    exportNote.setBounds (r);
}
