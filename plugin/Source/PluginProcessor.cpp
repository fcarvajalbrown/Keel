#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <cmath>

namespace
{
    // BS.1770-4 K-weighting analog prototypes (designed digitally at the host
    // sample rate via JUCE's RBJ biquads -- correct at any rate, unlike hard-
    // coded 48 kHz coefficients).
    constexpr double kShelfFreq   = 1681.974450955533;
    constexpr double kShelfQ      = 0.7071752369554196;
    constexpr double kShelfGainDb = 3.999843853973347;
    constexpr double kHpFreq      = 38.13547087613982;
    constexpr double kHpQ         = 0.5003270373253953;

    constexpr float kSilenceFloor = -100.0f; // dB shown as "no signal"

    // --- LIVE master chain constants -- MIRROR of mastering.py._internal_master.
    //     DSP SYNC RULE (ADR-0027): if these change in Python, change them here too.
    constexpr double kHpfHz        = 28.0;    // sub-rumble high-pass
    constexpr double kLoShelfHz    = 110.0;   // low-shelf
    constexpr double kLoShelfQ     = 0.7;
    constexpr double kLoShelfGainDb= 1.0;
    constexpr double kAirHz        = 9000.0;  // air high-shelf
    constexpr double kAirQ         = 0.7;
    constexpr double kAirGainDb    = 1.5;
    constexpr float  kCompThreshDb = -14.0f;  // glue comp
    constexpr float  kCompRatio    = 1.6f;
    constexpr float  kCompAttackMs = 30.0f;
    constexpr float  kCompReleaseMs= 250.0f;
    constexpr float  kLimReleaseMs = 120.0f;  // matches pedalboard Limiter

    inline double dbToGain (double db) { return std::pow (10.0, db / 20.0); }
}

KeelAudioProcessor::KeelAudioProcessor()
    : AudioProcessor (BusesProperties()
          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, nullptr, "PARAMS", makeParameterLayout())
{
}

juce::AudioProcessorValueTreeState::ParameterLayout
KeelAudioProcessor::makeParameterLayout()
{
    using namespace juce;
    AudioProcessorValueTreeState::ParameterLayout layout;

    layout.add (std::make_unique<AudioParameterChoice> (
        ParameterID { "preset", 1 }, "Preset",
        StringArray { "Streaming (-14)", "Loud (-10)", "Broadcast (-16)" }, 0));

    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "lufs", 1 }, "Target LUFS",
        NormalisableRange<float> (-24.0f, -6.0f, 0.1f), -14.0f));

    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "tp", 1 }, "True-Peak Ceiling",
        NormalisableRange<float> (-3.0f, 0.0f, 0.1f), -1.0f));

    // Static drive into the clip/limiter -- you set it by ear against the meter.
    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "makeup", 1 }, "Makeup",
        NormalisableRange<float> (-12.0f, 24.0f, 0.1f), 0.0f));

    layout.add (std::make_unique<AudioParameterBool> (
        ParameterID { "reference", 1 }, "Use Reference", false));

    layout.add (std::make_unique<AudioParameterBool> (
        ParameterID { "glue", 1 }, "Bus Glue", false));

    return layout;
}

bool KeelAudioProcessor::isBusesLayoutSupported (const BusesLayout& layouts) const
{
    // Master-bus processor: stereo in == stereo out.
    const auto out = layouts.getMainOutputChannelSet();
    if (out != juce::AudioChannelSet::stereo())
        return false;
    return layouts.getMainInputChannelSet() == out;
}

void KeelAudioProcessor::prepareToPlay (double sampleRate, int samplesPerBlock)
{
    currentSampleRate = sampleRate > 0.0 ? sampleRate : 48000.0;

    auto shelf = juce::dsp::IIR::Coefficients<float>::makeHighShelf (
        currentSampleRate, (float) kShelfFreq, (float) kShelfQ,
        (float) std::pow (10.0, kShelfGainDb / 20.0));
    auto hp = juce::dsp::IIR::Coefficients<float>::makeHighPass (
        currentSampleRate, (float) kHpFreq, (float) kHpQ);

    juce::dsp::ProcessSpec spec { currentSampleRate,
                                  (juce::uint32) juce::jmax (1, samplesPerBlock),
                                  1 };
    for (int ch = 0; ch < 2; ++ch)
    {
        kShelf[ch].coefficients = shelf;
        kHighpass[ch].coefficients = hp;
        kShelf[ch].prepare (spec);
        kHighpass[ch].prepare (spec);
        kShelf[ch].reset();
        kHighpass[ch].reset();
    }

    windowCapacitySamples = juce::jmax (1, (int) std::round (currentSampleRate * 0.4));
    window.clear();
    window.reserve (256);

    const auto numCh = (size_t) juce::jmax (1, getTotalNumOutputChannels());
    const auto block = (size_t) juce::jmax (1, samplesPerBlock);

    oversampler = std::make_unique<juce::dsp::Oversampling<float>> (
        numCh, 2, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
    oversampler->initProcessing (block);

    // --- live master chain (mirror of mastering.py) ---
    // Tone filters: 1st-order HPF + low-shelf + air high-shelf, per channel.
    auto hpfCoef = juce::dsp::IIR::Coefficients<float>::makeFirstOrderHighPass (
        currentSampleRate, (float) kHpfHz);
    auto loCoef = juce::dsp::IIR::Coefficients<float>::makeLowShelf (
        currentSampleRate, (float) kLoShelfHz, (float) kLoShelfQ,
        (float) dbToGain (kLoShelfGainDb));
    auto airCoef = juce::dsp::IIR::Coefficients<float>::makeHighShelf (
        currentSampleRate, (float) kAirHz, (float) kAirQ,
        (float) dbToGain (kAirGainDb));

    juce::dsp::ProcessSpec monoSpec { currentSampleRate, (juce::uint32) block, 1 };
    for (int ch = 0; ch < 2; ++ch)
    {
        hpf[ch].coefficients     = hpfCoef;
        loShelf[ch].coefficients = loCoef;
        hiShelf[ch].coefficients = airCoef;
        for (auto* f : { &hpf[ch], &loShelf[ch], &hiShelf[ch] })
        {
            f->prepare (monoSpec);
            f->reset();
        }
    }

    // Glue compressor across the stereo bus (constant params; always on, like Python).
    juce::dsp::ProcessSpec stereoSpec { currentSampleRate, (juce::uint32) block, 2 };
    glueComp.prepare (stereoSpec);
    glueComp.setThreshold (kCompThreshDb);
    glueComp.setRatio (kCompRatio);
    glueComp.setAttack (kCompAttackMs);
    glueComp.setRelease (kCompReleaseMs);

    // True-peak limiter runs in the 4x-oversampled domain (threshold set per block).
    oversampleRate = currentSampleRate * 4.0;
    juce::dsp::ProcessSpec osSpec { oversampleRate, (juce::uint32) (block * 4), 2 };
    limiter.prepare (osSpec);
    limiter.setRelease (kLimReleaseMs);

    processOversampler = std::make_unique<juce::dsp::Oversampling<float>> (
        2, 2, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
    processOversampler->initProcessing (block);
    setLatencySamples ((int) std::round (processOversampler->getLatencyInSamples()));

    // Static makeup: declick knob drags over 30 ms; start AT the set value so a
    // fresh render has no ramp.
    makeupGain.reset (currentSampleRate, 0.03);
    const float makeupDb0 = apvts.getRawParameterValue ("makeup")->load();
    makeupGain.setCurrentAndTargetValue ((float) dbToGain (makeupDb0));

    resetMeters();
}

void KeelAudioProcessor::resetMeters()
{
    window.clear();
    windowSumSq[0] = windowSumSq[1] = 0.0;
    windowSamples = 0;
    truePeakHold = 0.0f;
    momentaryLufs.store (kSilenceFloor);
    truePeakDb.store (kSilenceFloor);
}

void KeelAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                       juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;
    const int numCh = juce::jmin (buffer.getNumChannels(), 2);
    const int numSamples = buffer.getNumSamples();

    const float tpCeilDb  = apvts.getRawParameterValue ("tp")->load();
    const float makeupDb  = apvts.getRawParameterValue ("makeup")->load();

    // ============================ LIVE MASTER CHAIN ============================
    // A faithful preview of mastering.py (ADR-0027). Audio IS altered here; the
    // meters below then measure the OUTPUT. Exact loudness is locked on Finalize.

    // 1) Tone: HPF -> low-shelf -> air high-shelf, per channel.
    for (int ch = 0; ch < numCh; ++ch)
    {
        float* x = buffer.getWritePointer (ch);
        for (int i = 0; i < numSamples; ++i)
        {
            float s = hpf[ch].processSample (x[i]);
            s = loShelf[ch].processSample (s);
            s = hiShelf[ch].processSample (s);
            x[i] = s;
        }
    }
    if (numSamples > 0)
    {
        juce::dsp::AudioBlock<float> toneBlock (buffer);
        glueComp.process (juce::dsp::ProcessContextReplacing<float> (toneBlock));
    }

    // 2) Static makeup: drive the post-tone signal into the clip/limiter by the
    //    user-set amount (declicked). Stands in for mastering.py's pre-normalize;
    //    static, so playback and a DAW bounce are identical (no intro ramp).
    if (numSamples > 0)
    {
        makeupGain.setTargetValue ((float) dbToGain (makeupDb));
        for (int i = 0; i < numSamples; ++i)
        {
            const float g = makeupGain.getNextValue();
            for (int ch = 0; ch < numCh; ++ch)
                buffer.getWritePointer (ch)[i] *= g;
        }
    }

    // 3) Oversampled tanh soft-clip (a hair above the limiter ceiling so the
    //    clipper takes the very top) + 4) 4x true-peak limiter to the ceiling.
    if (processOversampler != nullptr && numSamples > 0)
    {
        const double clipCeil = dbToGain (juce::jmin (0.0, (double) tpCeilDb + 1.0));
        juce::dsp::AudioBlock<float> outBlock (buffer);
        auto upBlock = processOversampler->processSamplesUp (outBlock);

        for (size_t ch = 0; ch < upBlock.getNumChannels(); ++ch)
        {
            float* u = upBlock.getChannelPointer (ch);
            for (size_t i = 0; i < upBlock.getNumSamples(); ++i)
                u[i] = (float) (clipCeil * std::tanh (u[i] / clipCeil));
        }

        limiter.setThreshold (tpCeilDb);
        limiter.process (juce::dsp::ProcessContextReplacing<float> (upBlock));

        processOversampler->processSamplesDown (outBlock);
    }
    // ===========================================================================

    // --- Below we only MEASURE the OUTPUT; we never write to the buffer. ---

    // 1) Momentary LUFS over a 400 ms sliding window (K-weighted mean square).
    Block blk { { 0.0, 0.0 }, numSamples };
    for (int ch = 0; ch < juce::jmin (numCh, 2); ++ch)
    {
        const float* in = buffer.getReadPointer (ch);
        double sumSq = 0.0;
        for (int i = 0; i < numSamples; ++i)
        {
            float s = kShelf[ch].processSample (in[i]);
            s = kHighpass[ch].processSample (s);
            sumSq += (double) s * (double) s;
        }
        blk.sumSq[ch] = sumSq;
    }

    window.push_back (blk);
    windowSumSq[0] += blk.sumSq[0];
    windowSumSq[1] += blk.sumSq[1];
    windowSamples  += numSamples;

    while (windowSamples - window.front().numSamples >= windowCapacitySamples
           && window.size() > 1)
    {
        const Block& old = window.front();
        windowSumSq[0] -= old.sumSq[0];
        windowSumSq[1] -= old.sumSq[1];
        windowSamples  -= old.numSamples;
        window.erase (window.begin());
    }

    if (windowSamples > 0)
    {
        // Channel-summed mean square with G=1.0 for L/R (BS.1770), then LKFS.
        const double z = (windowSumSq[0] + windowSumSq[1]) / (double) windowSamples;
        const float lufs = z > 1.0e-12
            ? (float) (-0.691 + 10.0 * std::log10 (z))
            : kSilenceFloor;
        momentaryLufs.store (juce::jmax (kSilenceFloor, lufs));
    }

    // 2) True peak: 4x oversample, inter-sample max, with a decay hold.
    float blockPeak = 0.0f;
    if (oversampler != nullptr && numSamples > 0)
    {
        juce::dsp::AudioBlock<float> block (buffer);
        auto upBlock = oversampler->processSamplesUp (block);
        for (size_t ch = 0; ch < upBlock.getNumChannels(); ++ch)
            for (size_t i = 0; i < upBlock.getNumSamples(); ++i)
                blockPeak = juce::jmax (blockPeak, std::abs (upBlock.getSample ((int) ch, (int) i)));
    }
    else
    {
        blockPeak = buffer.getMagnitude (0, numSamples);
    }

    // ~1.5 dB/s visual decay so the readout settles instead of latching.
    const float decay = (float) std::pow (10.0, -1.5 / 20.0
                          * (numSamples / currentSampleRate));
    truePeakHold = juce::jmax (blockPeak, truePeakHold * decay);
    truePeakDb.store (truePeakHold > 1.0e-6f
        ? juce::jmax (kSilenceFloor, juce::Decibels::gainToDecibels (truePeakHold))
        : kSilenceFloor);
}

juce::AudioProcessorEditor* KeelAudioProcessor::createEditor()
{
    return new KeelAudioProcessorEditor (*this);
}

void KeelAudioProcessor::getStateInformation (juce::MemoryBlock& destData)
{
    if (auto xml = apvts.copyState().createXml())
        copyXmlToBinary (*xml, destData);
}

void KeelAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (auto xml = getXmlFromBinary (data, sizeInBytes))
        if (xml->hasTagName (apvts.state.getType()))
            apvts.replaceState (juce::ValueTree::fromXml (*xml));
}

// JUCE entry point.
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new KeelAudioProcessor();
}
