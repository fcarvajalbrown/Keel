// Keel plugin -- editor.
//
// The SIMPLE, master-only UI (ADR-0029), wearing the standalone GUI's visual
// language (KeelLookAndFeel: teal palette, Space Grotesk, the hull mark, gradient
// meters). It drops the standalone's file->label table and balance faders and
// keeps only the master controls (preset / target-LUFS reference / TP ceiling /
// Makeup / reference / glue) plus the two live OUTPUT meters. No Finalize button:
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
    void applyPresetToTargets();

    KeelAudioProcessor& processor;
    keel::KeelLookAndFeel look;

    keel::HullMark hullMark;
    juce::Label  titleLabel, subtitleLabel;

    juce::Label    presetLabel;
    juce::ComboBox presetBox;

    juce::Label  lufsLabel, tpLabel, makeupLabel;
    juce::Slider lufsSlider, tpSlider, makeupSlider;

    juce::ToggleButton referenceToggle { "Reference" };
    juce::ToggleButton glueToggle      { "Bus glue" };

    keel::Meter lufsMeter, tpMeter;
    juce::Label exportNote;

    // Card backgrounds: filled in resized(), painted in paint().
    juce::Rectangle<int> cardTargets, cardDrive, cardMeters;

    using ComboAttachment  = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;
    std::unique_ptr<ComboAttachment>  presetAttachment;
    std::unique_ptr<SliderAttachment> lufsAttachment, tpAttachment, makeupAttachment;
    std::unique_ptr<ButtonAttachment> referenceAttachment, glueAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessorEditor)
};
