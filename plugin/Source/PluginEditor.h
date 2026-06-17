// Keel plugin spike -- editor.
//
// Deliberately the SIMPLE, master-only UI (ADR-0026): it drops the standalone
// GUI's file->label table and balance faders, keeping only the master controls
// (preset / target LUFS / TP ceiling / reference / glue), the two live meters,
// and an Apply button. Apply is a non-functional stub in this spike.

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

    juce::Label  lufsLabel, tpLabel;
    juce::Slider lufsSlider, tpSlider;

    juce::ToggleButton referenceToggle { "Reference" };
    juce::ToggleButton glueToggle      { "Bus glue" };

    // Live meters (display-only).
    juce::Label lufsMeterLabel, tpMeterLabel;
    float lufsMeterValue { -100.0f };
    float tpMeterValue   { -100.0f };

    juce::TextButton applyButton { "Apply master" };
    juce::Label      applyNote;

    using ComboAttachment  = juce::AudioProcessorValueTreeState::ComboBoxAttachment;
    using SliderAttachment = juce::AudioProcessorValueTreeState::SliderAttachment;
    using ButtonAttachment = juce::AudioProcessorValueTreeState::ButtonAttachment;
    std::unique_ptr<ComboAttachment>  presetAttachment;
    std::unique_ptr<SliderAttachment> lufsAttachment, tpAttachment;
    std::unique_ptr<ButtonAttachment> referenceAttachment, glueAttachment;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessorEditor)
};
