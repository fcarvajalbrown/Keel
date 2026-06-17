// Keel plugin spike -- master-bus processor (ADR-0026).
//
// Real-time stereo PASS-THROUGH (the audio is not altered) while driving two
// display-only meters: a BS.1770-4 K-weighted momentary LUFS meter and a 4x
// oversampled true-peak meter. The authoritative numbers still come from the
// Python engine on Apply; these are live guidance, exactly like the GUI's
// playback meters. Apply itself is a stub in this spike.

#pragma once

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_dsp/juce_dsp.h>
#include <atomic>
#include <vector>

class KeelAudioProcessor : public juce::AudioProcessor
{
public:
    KeelAudioProcessor();
    ~KeelAudioProcessor() override = default;

    void prepareToPlay (double sampleRate, int samplesPerBlock) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout& layouts) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }

    const juce::String getName() const override { return "Keel"; }
    bool acceptsMidi() const override { return false; }
    bool producesMidi() const override { return false; }
    bool isMidiEffect() const override { return false; }
    double getTailLengthSeconds() const override { return 0.0; }

    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return {}; }
    void changeProgramName (int, const juce::String&) override {}

    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    // --- spike API for the editor ---
    juce::AudioProcessorValueTreeState apvts;

    // Display-only meter values, written on the audio thread, read on the UI
    // thread. -100.0f means "no signal yet".
    std::atomic<float> momentaryLufs { -100.0f };
    std::atomic<float> truePeakDb    { -100.0f };

private:
    static juce::AudioProcessorValueTreeState::ParameterLayout makeParameterLayout();

    // BS.1770-4 K-weighting: a high-shelf pre-filter followed by an RLB
    // high-pass, one of each per channel.
    juce::dsp::IIR::Filter<float> kShelf[2], kHighpass[2];

    // 400 ms sliding window of K-weighted mean-square energy, per channel.
    struct Block { double sumSq[2]; int numSamples; };
    std::vector<Block> window;
    double windowSumSq[2] { 0.0, 0.0 };
    int    windowSamples  { 0 };
    int    windowCapacitySamples { 1 };

    // True-peak: 4x oversample the block, take the inter-sample max. Built in
    // prepareToPlay for the host's actual channel count.
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampler;
    float truePeakHold { 0.0f };       // linear, with decay for display
    double currentSampleRate { 48000.0 };

    void resetMeters();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessor)
};
