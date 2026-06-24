#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <juce_audio_formats/juce_audio_formats.h>  // AudioFormatManager/Reader (reference readout)
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

    // --- Offline reference measurement (ADR-0035) -----------------------------
    // Integrated LUFS (BS.1770-4, full gating) + 4x-oversampled true-peak of a
    // whole buffer. Static, not real-time: this matches what meters.py reports for
    // the same file (pyloudnorm is also BS.1770-4 integrated). Returns
    // { integratedLufs, dBTP }, each kSilenceFloor when there is nothing to show.
    std::pair<float, float> measureReferenceStats (const juce::AudioBuffer<float>& buf,
                                                   double sr)
    {
        const int numCh = juce::jmin (buf.getNumChannels(), 2);
        const int n     = buf.getNumSamples();
        if (numCh <= 0 || n <= 0 || sr <= 0.0)
            return { kSilenceFloor, kSilenceFloor };

        // K-weight a copy (same prefilters as the live momentary meter).
        juce::AudioBuffer<float> k (numCh, n);
        auto shelf = juce::dsp::IIR::Coefficients<float>::makeHighShelf (
            sr, (float) kShelfFreq, (float) kShelfQ,
            (float) std::pow (10.0, kShelfGainDb / 20.0));
        auto hp = juce::dsp::IIR::Coefficients<float>::makeHighPass (
            sr, (float) kHpFreq, (float) kHpQ);
        for (int ch = 0; ch < numCh; ++ch)
        {
            juce::dsp::IIR::Filter<float> f1, f2;
            f1.coefficients = shelf;
            f2.coefficients = hp;
            const juce::dsp::ProcessSpec spec { sr, (juce::uint32) juce::jmax (1, n), 1 };
            f1.prepare (spec); f2.prepare (spec);
            f1.reset();        f2.reset();
            const float* src = buf.getReadPointer (ch);
            float* dst = k.getWritePointer (ch);
            for (int i = 0; i < n; ++i)
                dst[i] = f2.processSample (f1.processSample (src[i]));
        }

        // Integrated loudness over 400 ms blocks at a 100 ms hop (75% overlap),
        // with the absolute (-70 LUFS) then relative (-10 LU) gates.
        const int blockLen = juce::jmax (1, (int) std::round (sr * 0.4));
        const int hop      = juce::jmax (1, (int) std::round (sr * 0.1));
        std::vector<double> blockZ, blockL;
        for (int start = 0; start + blockLen <= n; start += hop)
        {
            double z = 0.0;
            for (int ch = 0; ch < numCh; ++ch)
            {
                const float* x = k.getReadPointer (ch);
                double s = 0.0;
                for (int i = 0; i < blockLen; ++i)
                    s += (double) x[start + i] * (double) x[start + i];
                z += s / blockLen;            // channel weight G = 1.0 for L/R
            }
            blockZ.push_back (z);
            blockL.push_back (z > 1.0e-12 ? -0.691 + 10.0 * std::log10 (z) : -1000.0);
        }

        float integrated = kSilenceFloor;
        if (! blockZ.empty())
        {
            double sumAbs = 0.0; int cntAbs = 0;
            for (size_t i = 0; i < blockZ.size(); ++i)
                if (blockL[i] >= -70.0) { sumAbs += blockZ[i]; ++cntAbs; }

            if (cntAbs > 0)
            {
                const double relThresh =
                    -0.691 + 10.0 * std::log10 (sumAbs / cntAbs) - 10.0;
                double sumRel = 0.0; int cntRel = 0;
                for (size_t i = 0; i < blockZ.size(); ++i)
                    if (blockL[i] >= -70.0 && blockL[i] >= relThresh)
                        { sumRel += blockZ[i]; ++cntRel; }

                if (cntRel > 0)
                {
                    const double meanRel = sumRel / cntRel;
                    integrated = meanRel > 1.0e-12
                        ? (float) (-0.691 + 10.0 * std::log10 (meanRel))
                        : kSilenceFloor;
                }
            }
        }

        // True peak: 4x oversample the whole buffer, take the inter-sample max.
        float tp = kSilenceFloor;
        {
            juce::AudioBuffer<float> tpBuf (numCh, n);
            for (int ch = 0; ch < numCh; ++ch)
                tpBuf.copyFrom (ch, 0, buf, ch, 0, n);
            juce::dsp::Oversampling<float> os (
                (size_t) numCh, 2,
                juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
            os.initProcessing ((size_t) n);
            juce::dsp::AudioBlock<float> blk (tpBuf);
            auto up = os.processSamplesUp (blk);
            float peak = 0.0f;
            for (size_t ch = 0; ch < up.getNumChannels(); ++ch)
                for (size_t i = 0; i < up.getNumSamples(); ++i)
                    peak = juce::jmax (peak, std::abs (up.getSample ((int) ch, (int) i)));
            tp = peak > 1.0e-9f ? juce::Decibels::gainToDecibels (peak) : kSilenceFloor;
        }

        return { integrated, tp };
    }
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

    // NOTE: there is intentionally no "reference" parameter. The reference is a
    // user-loaded file measured offline for a passive LUFS/TP readout (ADR-0035),
    // not an automatable on/off match -- so it lives in the state tree (the file
    // path), not as a host-automatable parameter.

    // Default ON: this gates the master tone-stage glue comp, which mastering.py
    // ALWAYS applies. Default-on keeps the out-of-box master in sync with the
    // CLI/GUI (DSP SYNC RULE); turning it OFF is a deliberate plugin-only deviation.
    layout.add (std::make_unique<AudioParameterBool> (
        ParameterID { "glue", 1 }, "Bus Glue", true));

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

    // Glue compressor across the stereo bus (constant params; gated by the "glue"
    // toggle in processBlock, default ON to match mastering.py's always-on glue).
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

void KeelAudioProcessor::loadReference (const juce::File& file)
{
    if (! file.existsAsFile())
    {
        clearReference();
        return;
    }

    referenceName = file.getFileName();
    referenceLoading.store (true);
    referenceLufs.store (kSilenceFloor);
    referenceTruePeak.store (kSilenceFloor);
    apvts.state.setProperty ("referencePath", file.getFullPathName(), nullptr);

    // Measure off the message thread -- a full song is a few million samples.
    juce::Thread::launch ([this, file]
    {
        juce::AudioFormatManager fm;
        fm.registerBasicFormats();
        std::unique_ptr<juce::AudioFormatReader> reader (fm.createReaderFor (file));
        if (reader == nullptr)
        {
            referenceLoading.store (false);
            return;
        }

        const int numCh = (int) juce::jlimit (1, 2, (int) reader->numChannels);
        // Cap at 12 min so a stray huge file can't exhaust memory; references are
        // single songs, far under this.
        const auto maxLen = (juce::int64) (reader->sampleRate * 60.0 * 12.0);
        const int  n      = (int) juce::jmin (maxLen, reader->lengthInSamples);
        if (n <= 0)
        {
            referenceLoading.store (false);
            return;
        }

        juce::AudioBuffer<float> buf (juce::jmax (1, numCh), n);
        reader->read (&buf, 0, n, 0, true, true);

        const auto stats = measureReferenceStats (buf, reader->sampleRate);
        referenceLufs.store (stats.first);
        referenceTruePeak.store (stats.second);
        referenceLoading.store (false);
    });
}

void KeelAudioProcessor::clearReference()
{
    referenceName = {};
    referenceLoading.store (false);
    referenceLufs.store (kSilenceFloor);
    referenceTruePeak.store (kSilenceFloor);
    apvts.state.setProperty ("referencePath", juce::String(), nullptr);
}

void KeelAudioProcessor::processBlock (juce::AudioBuffer<float>& buffer,
                                       juce::MidiBuffer&)
{
    juce::ScopedNoDenormals noDenormals;
    const int numCh = juce::jmin (buffer.getNumChannels(), 2);
    const int numSamples = buffer.getNumSamples();

    const float tpCeilDb  = apvts.getRawParameterValue ("tp")->load();
    const float makeupDb  = apvts.getRawParameterValue ("makeup")->load();
    const bool  glueOn    = apvts.getRawParameterValue ("glue")->load() > 0.5f;

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
    // Glue comp gated by the toggle. ON by default == mastering.py's always-on
    // master glue (DSP SYNC RULE); OFF is a deliberate plugin-only deviation.
    if (glueOn && numSamples > 0)
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
        {
            apvts.replaceState (juce::ValueTree::fromXml (*xml));

            // Re-measure a saved reference, if any, so its readout returns.
            const auto path = apvts.state.getProperty ("referencePath",
                                                       juce::String()).toString();
            if (path.isNotEmpty())
                loadReference (juce::File (path));
        }
}

// JUCE entry point.
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new KeelAudioProcessor();
}
