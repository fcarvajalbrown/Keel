// Keel plugin -- master-bus processor (ADR-0027).
//
// Runs the LIVE C++ master chain (a faithful PREVIEW of the Python master): tone
// (HPF 28 / low-shelf / air / glue comp) -> Ozone-style auto makeup toward the
// target -> oversampled tanh soft-clip -> 4x oversampled true-peak limiter. You
// hear the Keel master and tweak it in real time; the two meters (BS.1770-4
// momentary LUFS + 4x true-peak) read the OUTPUT.
//
// Loudness is APPROXIMATE live (the makeup chases a slow loudness estimate toward
// the target; exact integrated LUFS is whole-program, so it cannot be live). The
// byte-identical, exact -14 LUFS / -1 dBTP master is produced by the Python engine
// on Finalize (still a stub here).
//
// >>> DSP SYNC RULE (ADR-0027, load-bearing): this chain and mastering.py are two
//     disconnected impls of the same master character. Any change to the Python
//     master math MUST be mirrored here (and re-A/B'd), or the preview drifts from
//     the Finalized file.

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

    // --- LIVE master chain (ADR-0027 preview; mirror of mastering.py) ---
    // Tone stage: 1st-order HPF + low-shelf + air high-shelf (per channel), then a
    // gentle glue compressor across the stereo bus. Same blocks pedalboard wraps.
    juce::dsp::IIR::Filter<float> hpf[2], loShelf[2], hiShelf[2];
    juce::dsp::Compressor<float>  glueComp;
    // True-peak limiter, run on the 4x-oversampled signal (intersample peaks become
    // real samples it can catch), paired with an oversampled tanh soft-clip above.
    juce::dsp::Limiter<float>     limiter;
    std::unique_ptr<juce::dsp::Oversampling<float>> processOversampler;
    double oversampleRate { 192000.0 };

    // Ozone-style auto makeup: a slow K-weighted loudness estimate of the post-tone
    // signal drives a heavily-smoothed makeup gain toward the target LUFS, standing
    // in for mastering.py's whole-program pre-normalize (which can't run live).
    juce::dsp::IIR::Filter<float> detShelf[2], detHighpass[2];
    double detEmaMeanSq[2] { 0.0, 0.0 };
    juce::SmoothedValue<float> makeupGain;

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
