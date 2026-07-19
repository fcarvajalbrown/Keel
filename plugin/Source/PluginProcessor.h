// Keel plugin -- self-contained master-bus processor (ADR-0029).
//
// Runs the Keel master chain LIVE in C++, a faithful port of the Python master:
// tone (HPF 28 / low-shelf / air / glue comp) -> static user Makeup gain ->
// oversampled tanh soft-clip -> 4x oversampled true-peak limiter. You hear the
// master and tweak it in real time; the two meters (BS.1770-4 momentary LUFS +
// 4x true-peak) read the OUTPUT. Deliver by exporting from the DAW with this
// active -- there is no separate offline step.
//
// Loudness is APPROXIMATE (you set Makeup by ear against the live meter; exact
// integrated LUFS is whole-program, so it cannot be a single-pass real-time
// value). The true-peak ceiling IS enforced live by the oversampled limiter, so
// exports are TP-safe. Exact -14 LUFS / -1 dBTP delivery lives only in the CLI /
// GUI (the Python engine); the plugin trades exactness for a live, self-contained
// master (ADR-0029, supersedes ADR-0027's Finalize model).
//
// >>> DSP SYNC RULE (load-bearing): this chain and mastering.py are two
//     disconnected impls of the same master character. Any change to the Python
//     master math MUST be mirrored here (and re-A/B'd), or the preview drifts from
//     the CLI/GUI master.

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
    //
    // momentary  = 400 ms K-weighted window (fast, for transients).
    // shortTerm  = 3 s K-weighted window (BS.1770 S).
    // integrated = whole-program gated loudness (BS.1770 I) -- THE number streaming
    //              services normalize on, so it is what Makeup should be aimed at.
    std::atomic<float> momentaryLufs  { -100.0f };
    std::atomic<float> shortTermLufs  { -100.0f };
    std::atomic<float> integratedLufs { -100.0f };
    std::atomic<float> truePeakDb     { -100.0f };
    // Latched maximum true-peak since the last reset (the "did I cross the ceiling"
    // peak-hold). -100.0f = nothing yet.
    std::atomic<float> truePeakMaxDb  { -100.0f };

    // Loudness range (EBU R128 / Tech 3342), LU. -1.0f means "not enough gated
    // short-term data yet". Shares the integrated measurement session (same reset).
    std::atomic<float> loudnessRange  { -1.0f };

    // Gain reduction applied by the clip/limiter stage, dB (0 = none, negative =
    // reduction). Peak-in-vs-out per block, fast attack + slow release for display.
    std::atomic<float> gainReductionDb { 0.0f };

    // Reset the integrated measurement (call from the UI thread). Integrated
    // accumulates from the last reset, so the user dials Makeup, resets, then lets
    // a representative loud section play and reads where it lands. RT-safe: this
    // only raises a flag the audio thread honours at the top of the next block.
    void resetIntegrated() { integratedResetRequested.store (true); }

    // --- Reference loudness/peak READOUT (ADR-0035) ---
    // A user-loaded reference file is measured ONCE, offline, on a background
    // thread, and its integrated LUFS + true-peak are shown next to the live
    // master meters. This is a passive readout, NOT a live match -- the spectral
    // / ML reference match stays the offline Matchering path in the CLI/GUI. The
    // measured values are written by the worker thread, read on the UI thread.
    // -100.0f means "no reference / not measured yet".
    std::atomic<float> referenceLufs     { -100.0f };  // integrated, BS.1770-4 gated
    std::atomic<float> referenceTruePeak { -100.0f };  // dBTP, 4x oversampled
    std::atomic<bool>  referenceLoading  { false };
    juce::String       referenceName;                  // touched on the UI thread only

    // Load + offline-measure a reference file (call from the message thread); pass
    // an empty/non-existent file via clearReference() to drop it.
    void loadReference (const juce::File& file);
    void clearReference();

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

    // Makeup gain: a STATIC, user-set drive (dB) applied before the clip/limiter,
    // standing in for mastering.py's whole-program pre-normalize. Static (not
    // adaptive) so playback and a DAW bounce are identical -- no intro ramp. The
    // SmoothedValue only declicks the user dragging the knob; on prepare it is set
    // to the current value, so a fresh render starts already at the set gain.
    juce::SmoothedValue<float> makeupGain;

    // BS.1770-4 K-weighting: a high-shelf pre-filter followed by an RLB
    // high-pass, one of each per channel. A second set (…Dry) K-weights the
    // captured dry input so the loudness-matched A/B knows the wet-vs-dry ratio.
    juce::dsp::IIR::Filter<float> kShelf[2], kHighpass[2];
    juce::dsp::IIR::Filter<float> kShelfDry[2], kHighpassDry[2];

    // Loudness-matched A/B: play the dry input gain-matched to the master's
    // loudness so the comparison exposes character, not the deliberate loudness
    // lift. Dry is captured pre-chain; wet/dry K-weighted energy is tracked as an
    // EMA (~0.4 s) to derive the match gain; the blend is smoothed to declick.
    juce::AudioBuffer<float> dryBuffer;
    double dryEnergyEma { 0.0 };
    double wetEnergyEma { 0.0 };
    juce::SmoothedValue<float> abMixSmoothed;      // 0 = wet master, 1 = matched dry
    juce::SmoothedValue<float> matchGainSmoothed;  // linear gain applied to dry

    // 400 ms sliding window of K-weighted mean-square energy, per channel.
    struct Block { double sumSq[2]; int numSamples; };
    std::vector<Block> window;
    double windowSumSq[2] { 0.0, 0.0 };
    int    windowSamples  { 0 };
    int    windowCapacitySamples { 1 };

    // 3 s short-term window, a parallel deque fed the same per-block K-weighted
    // energies as the momentary window above.
    std::vector<Block> stWindow;
    double stSumSq[2] { 0.0, 0.0 };
    int    stSamples  { 0 };
    int    stCapacitySamples { 1 };

    // Integrated loudness (BS.1770-4 gated). The 400 ms momentary energy is sampled
    // every 100 ms as a gating block, absolute-gated at -70 LKFS, and binned into a
    // fixed 0.1 LU histogram; the -10 LU relative gate + integrated value are then
    // evaluated over that histogram in constant memory. Hand-rolled precisely
    // because libebur128's integrated mode allocates per block and must stay off
    // the audio thread (it powers the offline reference readout only).
    std::vector<int>    intgHist;        // count per 0.1 LU bin
    std::vector<double> intgBinEnergy;   // precomputed linear energy at each bin centre
    int    gateHopSamples   { 1 };
    int    samplesSinceGate { 0 };
    std::atomic<bool> integratedResetRequested { false };

    // Loudness range: short-term loudness values sampled at the same 100 ms cadence
    // into a parallel histogram (same 0.1 LU bins), so LRA = P95 - P10 over the
    // -20 LU relatively-gated distribution can be read off in constant memory.
    std::vector<int> lraHist;

    void updateIntegrated();   // recompute the integrated value from the histogram
    void updateLra();          // recompute the loudness range from the ST histogram

    // True-peak: 4x oversample the block, take the inter-sample max. Built in
    // prepareToPlay for the host's actual channel count.
    std::unique_ptr<juce::dsp::Oversampling<float>> oversampler;
    float truePeakHold { 0.0f };       // linear, with decay for display
    float truePeakMaxLin { 0.0f };     // linear, latched max for peak-hold
    float grHold { 0.0f };             // dB (<= 0), fast attack + slow release
    double currentSampleRate { 48000.0 };

    void resetMeters();

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (KeelAudioProcessor)
};
