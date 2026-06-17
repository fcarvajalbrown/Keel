// Keel plugin -- editor.
//
// Deliberately the SIMPLE, master-only UI (ADR-0029): it drops the standalone
// GUI's file->label table and balance faders, keeping only the master controls
// (preset / target LUFS reference / TP ceiling / Makeup / reference / glue) and
// the two live meters reading the master OUTPUT. There is no Finalize button --
// the plugin is a self-contained real-time master; you deliver by exporting from
// the DAW with it active.

#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include "PluginProcessor.h"

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

    juce::Label  titleLabel, subtitleLabel;

    juce::Label    presetLabel;
    juce::ComboBox presetBox;

    juce::Label  lufsLabel, tpLabel, makeupLabel;
    juce::Slider lufsSlider, tpSlider, makeupSlider;

    juce::ToggleButton referenceToggle { "Reference" };
    juce::ToggleButton glueToggle      { "Bus glue" };

    // Live meters (display-only).
    juce::Label lufsMeterLabel, tpMeterLabel;
    float lufsMeterValue { -100.0f };
    float tpMeterValue   { -100.0f };

    juce::Label exportNote;

    using ComboAttachment  = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;
    std::unique_ptr<ComboAttachment>  presetAttachment;
    std::unique_ptr<SliderAttachment> lufsAttachment, tpAttachment, makeupAttachment;
    std::unique_ptr<ButtonAttachment> referenceAttachment, glueAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessorEditor)
};
