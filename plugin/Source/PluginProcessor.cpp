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
        currentSampleRate, kShelfFreq, kShelfQ,
        (float) std::pow (10.0, kShelfGainDb / 20.0));
    auto hp = juce::dsp::IIR::Coefficients<float>::makeHighPass (
        currentSampleRate, kHpFreq, kHpQ);

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
    oversampler = std::make_unique<juce::dsp::Oversampling<float>> (
        numCh, 2, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
    oversampler->initProcessing ((size_t) juce::jmax (1, samplesPerBlock));

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
    const int numCh = buffer.getNumChannels();
    const int numSamples = buffer.getNumSamples();

    // --- This is a PASS-THROUGH: the dry audio is left exactly as it came in.
    //     Mastering happens offline on Apply (stubbed in this spike). Below we
    //     only MEASURE; we never write to the buffer. ---

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
