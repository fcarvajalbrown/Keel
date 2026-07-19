#include "PluginEditor.h"

namespace
{
    // Where user presets live: <user app data>/Keel/Presets/*.keelpreset (XML).
    juce::File keelPresetsDir()
    {
        auto dir = juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory)
                       .getChildFile ("Keel").getChildFile ("Presets");
        dir.createDirectory();
        return dir;
    }
}

KeelAudioProcessorEditor::KeelAudioProcessorEditor (KeelAudioProcessor& p)
    : AudioProcessorEditor (&p), processor (p),
      lufsMeter ("INTEGRATED", "LUFS", -40.0f, 0.0f, look),
      tpMeter   ("TRUE PEAK", "dBTP", -24.0f, 0.0f, look),
      loudnessGraph ("LOUDNESS HISTORY", "LUFS", -40.0f, 0.0f, look),
      grGraph       ("GAIN REDUCTION", "dB", -12.0f, 0.0f, look)
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

    // --- Undo / redo of parameter edits ---
    undoButton.onClick = [this] { processor.undoManager.undo(); };
    redoButton.onClick = [this] { processor.undoManager.redo(); };
    undoButton.setTitle ("Undo"); undoButton.setTooltip ("Undo parameter change (Ctrl+Z)");
    redoButton.setTitle ("Redo"); redoButton.setTooltip ("Redo parameter change (Ctrl+Shift+Z)");
    addAndMakeVisible (undoButton);
    addAndMakeVisible (redoButton);
    setWantsKeyboardFocus (true);

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
    // Selecting a preset drives Target-LUFS + TP in the PROCESSOR (so host
    // automation of "preset" works headless too); no editor-side handler needed.
    presetAttachment = std::make_unique<ComboAttachment> (apvts, "preset", presetBox);

    // --- User presets (save/recall the full parameter snapshot) ---
    sectionLabel (userPresetLabel, "User presets");
    userPresetButton.setTooltip ("Save the current settings as a preset, or load one");
    userPresetButton.onClick = [this] { showUserPresetMenu(); };
    addAndMakeVisible (userPresetButton);

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

    // --- Bus-glue toggle + loudness-matched A/B toggle ---
    addAndMakeVisible (glueToggle);
    glueAttachment = std::make_unique<ButtonAttachment> (apvts, "glue", glueToggle);

    addAndMakeVisible (abToggle);
    abAttachment = std::make_unique<ButtonAttachment> (apvts, "abmatch", abToggle);

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
    // The primary meter reads INTEGRATED loudness -- the number streaming services
    // normalize on -- so Makeup is aimed at the right target.
    lufsMeter.setTarget (-14.0f);
    addAndMakeVisible (lufsMeter);

    lufsSecondary.setText ("Short-term  --    Momentary  --", juce::dontSendNotification);
    lufsSecondary.setFont (look.display (10.0f));
    lufsSecondary.setColour (juce::Label::textColourId, keel::palette::muted);
    addAndMakeVisible (lufsSecondary);

    addAndMakeVisible (resetIntgButton);
    resetIntgButton.onClick = [this]
    {
        processor.resetIntegrated();     // integrated + LRA + true-peak hold
        loudnessGraph.clearHistory();
        grGraph.clearHistory();
    };

    lraLabel.setText ("Loudness range  --", juce::dontSendNotification);
    lraLabel.setFont (look.display (10.0f));
    lraLabel.setColour (juce::Label::textColourId, keel::palette::muted);
    addAndMakeVisible (lraLabel);

    tpMeter.setTarget (-1.0f);
    tpMeter.setDangerAbove (-1.0f);
    addAndMakeVisible (tpMeter);

    // Loudness history: ~40 s of short-term loudness at the 30 Hz UI tick.
    loudnessGraph.setCapacity (40 * 30);
    loudnessGraph.setTarget (-14.0f);
    addAndMakeVisible (loudnessGraph);

    // Gain-reduction history: same span; hangs from 0 dB (no target line).
    grGraph.setCapacity (40 * 30);
    grGraph.setFillFromTop (true);
    addAndMakeVisible (grGraph);

    // --- Export note (no Finalize: this IS the master) ---
    exportNote.setText ("Reset, play a loud section, then raise Makeup so INTEGRATED "
                        "sits at target -- export with this on.",
                        juce::dontSendNotification);
    exportNote.setFont (look.display (9.0f));
    exportNote.setColour (juce::Label::textColourId, keel::palette::faint);
    exportNote.setJustificationType (juce::Justification::centredTop);
    addAndMakeVisible (exportNote);

    // --- Accessibility: name + describe every control and painted meter so
    //     screen readers can announce them (the painted meters/graphs expose their
    //     live value via createAccessibilityHandler; see KeelLookAndFeel).
    presetBox.setTitle ("Preset");
    presetBox.setHelpText ("Loudness preset; sets target LUFS and true-peak ceiling");
    lufsSlider.setTitle ("Target LUFS");
    lufsSlider.setHelpText ("Target integrated loudness the meter aims at");
    tpSlider.setTitle ("True-peak ceiling");
    tpSlider.setHelpText ("Maximum true-peak the limiter holds, in dBTP");
    makeupSlider.setTitle ("Makeup");
    makeupSlider.setHelpText ("Drive into the clip and limiter; raise until integrated sits at target");
    glueToggle.setTitle ("Bus glue");
    glueToggle.setHelpText ("Master glue compressor; on matches the CLI/GUI master");
    abToggle.setTitle ("A/B matched bypass");
    abToggle.setHelpText ("Monitor the dry input loudness-matched to the master");
    resetIntgButton.setTitle ("Reset meters");
    resetIntgButton.setHelpText ("Reset integrated loudness, loudness range, peak-hold and the graphs");
    referenceLoadButton.setTitle ("Load reference");
    referenceClearButton.setTitle ("Clear reference");
    lufsMeter.setTitle ("Integrated loudness");
    tpMeter.setTitle ("True peak");
    loudnessGraph.setTitle ("Loudness history");
    grGraph.setTitle ("Gain-reduction history");

    // --- Hover tooltips ---
    presetBox.setTooltip ("Loudness preset: sets Target LUFS + TP ceiling");
    lufsSlider.setTooltip ("Target integrated loudness the meter aims at");
    tpSlider.setTooltip ("True-peak ceiling the limiter holds (dBTP)");
    makeupSlider.setTooltip ("Drive into the clip/limiter -- raise until INTEGRATED hits target");
    glueToggle.setTooltip ("Master glue compressor (on = matches the CLI/GUI master)");
    abToggle.setTooltip ("Bypass to the dry input, loudness-matched -- hear character, not level");
    resetIntgButton.setTooltip ("Reset integrated, loudness range, peak-hold and the graphs");
    referenceLoadButton.setTooltip ("Measure a reference file's integrated LUFS + true-peak");
    lufsMeter.setTooltip ("Integrated loudness (what streaming normalizes on)");
    tpMeter.setTooltip ("True peak; the bright marker is the held maximum");
    loudnessGraph.setTooltip ("Short-term loudness over time");
    grGraph.setTooltip ("Clip/limiter gain reduction over time");

    // First-run note (once ever) + overlay covering the whole editor.
    addChildComponent (firstRunNote);
    showFirstRunNoteIfNeeded();

    // Seed the undo-coalescing snapshot with current values (no spurious edit).
    static const char* const undoIds[] = { "preset", "lufs", "tp", "makeup", "glue", "abmatch" };
    for (int i = 0; i < 6; ++i)
        lastParamValues[i] = processor.apvts.getRawParameterValue (undoIds[i])->load();

    setSize (440, 918);
    startTimerHz (30);
}

KeelAudioProcessorEditor::~KeelAudioProcessorEditor()
{
    stopTimer();
    setLookAndFeel (nullptr);
}

bool KeelAudioProcessorEditor::keyPressed (const juce::KeyPress& k)
{
    if (k.getModifiers().isCommandDown())
    {
        const int code = k.getKeyCode();
        if (code == 'Z' && k.getModifiers().isShiftDown()) { processor.undoManager.redo(); return true; }
        if (code == 'Z') { processor.undoManager.undo(); return true; }
        if (code == 'Y') { processor.undoManager.redo(); return true; }
    }
    return false;
}

void KeelAudioProcessorEditor::showUserPresetMenu()
{
    auto files = keelPresetsDir().findChildFiles (juce::File::findFiles, false, "*.keelpreset");
    files.sort();

    juce::PopupMenu menu;
    menu.addItem (1, "Save current preset...");
    menu.addSeparator();
    if (files.isEmpty())
    {
        menu.addItem (2, "(no saved presets)", false);
    }
    else
    {
        juce::PopupMenu loadMenu, deleteMenu;
        for (int i = 0; i < files.size(); ++i)
        {
            loadMenu.addItem   (100 + i, files[i].getFileNameWithoutExtension());
            deleteMenu.addItem (1000 + i, files[i].getFileNameWithoutExtension());
        }
        menu.addSubMenu ("Load", loadMenu);
        menu.addSubMenu ("Delete", deleteMenu);
    }

    menu.showMenuAsync (juce::PopupMenu::Options().withTargetComponent (userPresetButton),
        [this, files] (int r)
        {
            if (r == 1)                    saveUserPreset();
            else if (r >= 1000)            { const int i = r - 1000; if (i < files.size()) files[i].deleteFile(); }
            else if (r >= 100)             { const int i = r - 100;  if (i < files.size()) loadUserPreset (files[i]); }
        });
}

void KeelAudioProcessorEditor::saveUserPreset()
{
    auto* w = new juce::AlertWindow ("Save preset", "Name this preset:",
                                     juce::MessageBoxIconType::NoIcon);
    w->addTextEditor ("name", "My preset");
    w->addButton ("Save",   1, juce::KeyPress (juce::KeyPress::returnKey));
    w->addButton ("Cancel", 0, juce::KeyPress (juce::KeyPress::escapeKey));
    w->enterModalState (true, juce::ModalCallbackFunction::create (
        [this, w] (int result)
        {
            if (result == 1)
            {
                const auto name = w->getTextEditorContents ("name").trim();
                if (name.isNotEmpty())
                {
                    // A preset is master settings only -- drop the reference path.
                    auto state = processor.apvts.copyState();
                    state.removeProperty ("referencePath", nullptr);
                    if (auto xml = state.createXml())
                        xml->writeTo (keelPresetsDir().getChildFile (
                            juce::File::createLegalFileName (name) + ".keelpreset"));
                }
            }
            delete w;
        }), false);
}

void KeelAudioProcessorEditor::loadUserPreset (const juce::File& file)
{
    if (auto xml = juce::XmlDocument::parse (file))
        processor.setStateFromXml (*xml);
}

void KeelAudioProcessorEditor::showFirstRunNoteIfNeeded()
{
    // Persist "seen" as a marker file in the user app-data dir (once ever).
    const auto marker = juce::File::getSpecialLocation (
                            juce::File::userApplicationDataDirectory)
                        .getChildFile ("Keel").getChildFile ("firstrun.done");
    if (marker.existsAsFile())
        return;

    firstRunNote.setContent ("Keel IS the master",
        "There is no separate export step -- Keel masters live on your master bus, "
        "so you deliver by bouncing/exporting from your DAW with Keel active.\n\n"
        "Raise Makeup until INTEGRATED sits at your target; the -1 dBTP ceiling is "
        "held for you. For a guaranteed exact -14 LUFS file, use the Keel app or CLI.");
    firstRunNote.onDismiss = [this, marker]
    {
        marker.getParentDirectory().createDirectory();
        marker.create();
        firstRunNote.setVisible (false);
    };
    firstRunNote.setVisible (true);
    firstRunNote.toFront (false);
}

void KeelAudioProcessorEditor::timerCallback()
{
    // Coalesce parameter edits into one undo transaction each: reset the idle
    // counter on any change, and seal the transaction ~300 ms after edits settle.
    {
        static const char* const undoIds[] = { "preset", "lufs", "tp", "makeup", "glue", "abmatch" };
        bool changed = false;
        for (int i = 0; i < 6; ++i)
        {
            const float v = processor.apvts.getRawParameterValue (undoIds[i])->load();
            if (v != lastParamValues[i]) { lastParamValues[i] = v; changed = true; }
        }
        if (changed) { undoIdleTicks = 0; undoPendingSeal = true; }
        else if (undoPendingSeal && ++undoIdleTicks >= 9)
        {
            processor.undoManager.beginNewTransaction();
            undoPendingSeal = false;
        }
        undoButton.setEnabled (processor.undoManager.canUndo());
        redoButton.setEnabled (processor.undoManager.canRedo());
    }

    lufsMeter.setTarget (processor.apvts.getRawParameterValue ("lufs")->load());
    lufsMeter.setValue (processor.integratedLufs.load());

    // Secondary line: short-term + momentary (fast context under the integrated bar).
    auto fmtLufs = [] (float v) { return v <= -99.0f ? juce::String ("--")
                                                     : juce::String (v, 1); };
    const juce::String secText = "Short-term  " + fmtLufs (processor.shortTermLufs.load())
                               + "    Momentary  " + fmtLufs (processor.momentaryLufs.load());
    if (lufsSecondary.getText() != secText)
        lufsSecondary.setText (secText, juce::dontSendNotification);

    const float lra = processor.loudnessRange.load();
    const juce::String lraText = "Loudness range  "
        + (lra < 0.0f ? juce::String ("--") : juce::String (lra, 1) + " LU");
    if (lraLabel.getText() != lraText)
        lraLabel.setText (lraText, juce::dontSendNotification);

    loudnessGraph.setTarget (processor.apvts.getRawParameterValue ("lufs")->load());
    loudnessGraph.push (processor.shortTermLufs.load());
    grGraph.push (processor.gainReductionDb.load());

    const float tpCeil = processor.apvts.getRawParameterValue ("tp")->load();
    tpMeter.setTarget (tpCeil);
    tpMeter.setDangerAbove (tpCeil);
    tpMeter.setValue (processor.truePeakDb.load());
    tpMeter.setHold (processor.truePeakMaxDb.load());

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
    firstRunNote.setBounds (getLocalBounds());   // full-cover modal overlay

    auto r = getLocalBounds().reduced (16);

    // header
    auto header = r.removeFromTop (48);
    hullMark.setBounds (header.removeFromLeft (48).reduced (2));
    header.removeFromLeft (10);
    {
        auto row = header.removeFromRight (108).withSizeKeepingCentre (108, 24);
        undoButton.setBounds (row.removeFromLeft (50));
        row.removeFromLeft (8);
        redoButton.setBounds (row.removeFromLeft (50));
    }
    titleLabel.setBounds (header.removeFromTop (30));
    subtitleLabel.setBounds (header);
    r.removeFromTop (12);

    auto labelledRow = [] (juce::Rectangle<int> row, juce::Label& lab,
                           juce::Component& ctrl)
    {
        lab.setBounds (row.removeFromLeft (118));
        ctrl.setBounds (row);
    };

    // card: Targets (preset + LUFS + TP + user presets)
    cardTargets = r.removeFromTop (176);
    {
        auto c = cardTargets.reduced (14);
        labelledRow (c.removeFromTop (28), presetLabel, presetBox);
        c.removeFromTop (8);
        labelledRow (c.removeFromTop (28), lufsLabel, lufsSlider);
        c.removeFromTop (8);
        labelledRow (c.removeFromTop (28), tpLabel, tpSlider);
        c.removeFromTop (8);
        labelledRow (c.removeFromTop (28), userPresetLabel, userPresetButton);
    }
    r.removeFromTop (12);

    // card: Drive (makeup + glue toggle)
    cardDrive = r.removeFromTop (96);
    {
        auto c = cardDrive.reduced (14);
        labelledRow (c.removeFromTop (28), makeupLabel, makeupSlider);
        c.removeFromTop (10);
        auto toggles = c.removeFromTop (24);
        glueToggle.setBounds (toggles.removeFromLeft (toggles.getWidth() / 2));
        abToggle.setBounds (toggles);
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
    cardMeters = r.removeFromTop (374);
    {
        auto c = cardMeters.reduced (14);
        lufsMeter.setBounds (c.removeFromTop (58));
        c.removeFromTop (4);
        auto secRow = c.removeFromTop (22);
        resetIntgButton.setBounds (secRow.removeFromRight (60));
        secRow.removeFromRight (8);
        lufsSecondary.setBounds (secRow);
        c.removeFromTop (4);
        lraLabel.setBounds (c.removeFromTop (18));
        c.removeFromTop (8);
        tpMeter.setBounds (c.removeFromTop (58));
        c.removeFromTop (12);
        loudnessGraph.setBounds (c.removeFromTop (70));
        c.removeFromTop (12);
        grGraph.setBounds (c.removeFromTop (70));
    }
    r.removeFromTop (10);
    exportNote.setBounds (r);
}
