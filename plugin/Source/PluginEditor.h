// Keel plugin -- editor.
//
// The SIMPLE, master-only UI (ADR-0029), wearing the standalone GUI's visual
// language (KeelLookAndFeel: teal palette, Space Grotesk, the hull mark, gradient
// meters). It drops the standalone's file->label table and balance faders and
// keeps only the master controls (preset / target-LUFS reference / TP ceiling /
// Makeup / glue) plus the two live OUTPUT meters and a passive reference
// loudness/peak readout (ADR-0035). No Finalize button:
// the plugin is a self-contained real-time master; you deliver by exporting.

#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include "PluginProcessor.h"
#include "KeelLookAndFeel.h"

class KeelAudioProcessorEditor : public juce::AudioProcessorEditor,
                                 private juce::Timer
{
public:
    explicit KeelAudioProcessorEditor (KeelAudioProcessor&);
    ~KeelAudioProcessorEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;

    KeelAudioProcessor& processor;
    keel::KeelLookAndFeel look;

    keel::HullMark hullMark;
    juce::Label  titleLabel, subtitleLabel;

    juce::Label    presetLabel;
    juce::ComboBox presetBox;

    juce::Label  lufsLabel, tpLabel, makeupLabel;
    juce::Slider lufsSlider, tpSlider, makeupSlider;

    juce::ToggleButton glueToggle { "Bus glue" };
    juce::ToggleButton abToggle   { "A/B (matched)" };

    // Reference: a passive loudness/peak readout off a user-loaded file (ADR-0035),
    // NOT a live match. Load -> offline-measure -> show LUFS/TP next to the meters.
    juce::Label      referenceLabel, referenceReadout;
    juce::TextButton referenceLoadButton  { "Load reference..." };
    juce::TextButton referenceClearButton { "Clear" };
    std::unique_ptr<juce::FileChooser> referenceChooser;

    keel::Meter lufsMeter, tpMeter;
    keel::HistoryGraph loudnessGraph;   // short-term loudness over time (scrolling)
    keel::HistoryGraph grGraph;         // clip/limiter gain reduction over time
    // Short-term + momentary shown as a compact secondary line under the primary
    // (integrated) meter; the Reset button restarts the integrated measurement.
    juce::Label      lufsSecondary;
    juce::TextButton resetIntgButton { "Reset" };
    juce::Label      lraLabel;          // loudness range (EBU R128), LU
    juce::Label exportNote;

    // Card backgrounds: filled in resized(), painted in paint().
    juce::Rectangle<int> cardTargets, cardDrive, cardReference, cardMeters;

    using ComboAttachment  = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;
    std::unique_ptr<ComboAttachment>  presetAttachment;
    std::unique_ptr<SliderAttachment> lufsAttachment, tpAttachment, makeupAttachment;
    std::unique_ptr<ButtonAttachment> glueAttachment, abAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessorEditor)
};
