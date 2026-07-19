#include "PluginProcessor.h"
#include "PluginEditor.h"
#include <juce_audio_formats/juce_audio_formats.h>  // AudioFormatManager/Reader (reference readout)
#include <ebur128.h>                                // canonical BS.1770 (reference readout)
#include <algorithm>
#include <cmath>
#include <vector>

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

    // Integrated-loudness histogram (BS.1770-4 gated measurement). Gating-block
    // loudness values are binned at 0.1 LU from the -70 LKFS absolute-gate floor
    // upward; 760 bins reach +6 LKFS, comfortably above any mastered material.
    constexpr double kIntgMinLufs  = -70.0;
    constexpr double kIntgBinWidth = 0.1;
    constexpr int    kIntgNumBins  = 760;

    // Preset macro table -- keep in sync with recipes.PRESETS and the editor combo.
    struct PresetTargets { float lufs, tp; };
    const PresetTargets kPresetTargets[] = {
        { -14.0f, -1.0f },   // Streaming (default, ADR-0003)
        { -10.0f, -1.0f },   // Loud
        { -16.0f, -1.0f },   // Broadcast
    };

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
    // Integrated LUFS + true-peak of a whole buffer via libebur128 (canonical
    // ITU-R BS.1770), so the readout matches what meters.py / pyloudnorm report
    // for the same file (both target BS.1770-4) more tightly than a hand-rolled
    // K-weighting did. Static, NOT real-time: libebur128's integrated mode
    // allocates per 100 ms block, which is fine on this reference worker thread
    // but must never touch the live chain. Returns { integratedLufs, dBTP }, each
    // kSilenceFloor when there is nothing to show.
    std::pair<float, float> measureReferenceStats (const juce::AudioBuffer<float>& buf,
                                                   double sr)
    {
        const int numCh = juce::jmin (buf.getNumChannels(), 2);
        const int n     = buf.getNumSamples();
        if (numCh <= 0 || n <= 0 || sr <= 0.0)
            return { kSilenceFloor, kSilenceFloor };

        ebur128_state* st = ebur128_init ((unsigned) numCh,
                                          (unsigned long) std::lround (sr),
                                          EBUR128_MODE_I | EBUR128_MODE_TRUE_PEAK);
        if (st == nullptr)
            return { kSilenceFloor, kSilenceFloor };

        // libebur128 wants interleaved frames; JUCE buffers are planar. Interleave
        // in chunks so the temp buffer stays small even for a whole song.
        constexpr int kChunk = 1 << 15;   // 32k frames
        std::vector<float> inter ((size_t) kChunk * (size_t) numCh);
        for (int start = 0; start < n; start += kChunk)
        {
            const int frames = juce::jmin (kChunk, n - start);
            for (int ch = 0; ch < numCh; ++ch)
            {
                const float* x = buf.getReadPointer (ch);
                for (int i = 0; i < frames; ++i)
                    inter[(size_t) i * (size_t) numCh + (size_t) ch] = x[start + i];
            }
            if (ebur128_add_frames_float (st, inter.data(), (size_t) frames)
                != EBUR128_SUCCESS)
            {
                ebur128_destroy (&st);
                return { kSilenceFloor, kSilenceFloor };
            }
        }

        float integrated = kSilenceFloor;
        double lufs = 0.0;
        if (ebur128_loudness_global (st, &lufs) == EBUR128_SUCCESS
            && std::isfinite (lufs))
            integrated = (float) lufs;

        float tp = kSilenceFloor;
        double peakLin = 0.0;
        for (int ch = 0; ch < numCh; ++ch)
        {
            double p = 0.0;   // libebur128 true-peak is linear amplitude (1.0 = 0 dBTP)
            if (ebur128_true_peak (st, (unsigned) ch, &p) == EBUR128_SUCCESS)
                peakLin = juce::jmax (peakLin, p);
        }
        if (peakLin > 1.0e-9)
            tp = (float) (20.0 * std::log10 (peakLin));

        ebur128_destroy (&st);
        return { integrated, tp };
    }
}

KeelAudioProcessor::KeelAudioProcessor()
    : AudioProcessor (BusesProperties()
          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
          .withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      apvts (*this, &undoManager, "PARAMS", makeParameterLayout())
{
    apvts.addParameterListener ("preset", this);
    apvts.addParameterListener ("osquality", this);
}

KeelAudioProcessor::~KeelAudioProcessor()
{
    apvts.removeParameterListener ("preset", this);
    apvts.removeParameterListener ("osquality", this);
    cancelPendingUpdate();
}

void KeelAudioProcessor::parameterChanged (const juce::String& id, float)
{
    if (id == "osquality")
        osQualityDirty.store (true);
    if (id == "preset" || id == "osquality")
        triggerAsyncUpdate();   // apply on the message thread
}

int KeelAudioProcessor::osFactorExponent() const
{
    // param index 0/1/2 -> exponent 1/2/3 -> 2x/4x/8x
    return (int) apvts.getRawParameterValue ("osquality")->load() + 1;
}

void KeelAudioProcessor::rebuildProcessOversampler()
{
    if (currentBlockSize <= 0)
        return;

    const int exp = osFactorExponent();
    suspendProcessing (true);
    processOversampler = std::make_unique<juce::dsp::Oversampling<float>> (
        2, exp, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
    processOversampler->initProcessing ((size_t) currentBlockSize);

    oversampleRate = currentSampleRate * std::pow (2.0, exp);
    juce::dsp::ProcessSpec osSpec {
        oversampleRate, (juce::uint32) (currentBlockSize << exp), 2 };
    limiter.prepare (osSpec);
    limiter.setRelease (kLimReleaseMs);

    setLatencySamples ((int) std::round (processOversampler->getLatencyInSamples()));
    suspendProcessing (false);
}

void KeelAudioProcessor::handleAsyncUpdate()
{
    if (osQualityDirty.exchange (false))
        rebuildProcessOversampler();

    const int idx = (int) apvts.getRawParameterValue ("preset")->load();
    if (idx == lastAppliedPreset)
        return;                 // no genuine change (e.g. state restore)
    lastAppliedPreset = idx;
    if (idx < 0 || idx >= (int) (sizeof (kPresetTargets) / sizeof (kPresetTargets[0])))
        return;

    if (auto* p = apvts.getParameter ("lufs"))
        p->setValueNotifyingHost (p->convertTo0to1 (kPresetTargets[idx].lufs));
    if (auto* p = apvts.getParameter ("tp"))
        p->setValueNotifyingHost (p->convertTo0to1 (kPresetTargets[idx].tp));
}

juce::AudioProcessorValueTreeState::ParameterLayout
KeelAudioProcessor::makeParameterLayout()
{
    using namespace juce;
    AudioProcessorValueTreeState::ParameterLayout layout;

    // Preset is a meta parameter: changing it drives Target-LUFS + TP.
    layout.add (std::make_unique<AudioParameterChoice> (
        ParameterID { "preset", 1 }, "Preset",
        StringArray { "Streaming (-14)", "Loud (-10)", "Broadcast (-16)" }, 0,
        AudioParameterChoiceAttributes().withMeta (true)));

    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "lufs", 1 }, "Target LUFS",
        NormalisableRange<float> (-24.0f, -6.0f, 0.1f), -14.0f,
        AudioParameterFloatAttributes().withLabel ("LUFS")));

    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "tp", 1 }, "True-Peak Ceiling",
        NormalisableRange<float> (-3.0f, 0.0f, 0.1f), -1.0f,
        AudioParameterFloatAttributes().withLabel ("dBTP")));

    // Static drive into the clip/limiter -- you set it by ear against the meter.
    layout.add (std::make_unique<AudioParameterFloat> (
        ParameterID { "makeup", 1 }, "Makeup",
        NormalisableRange<float> (-12.0f, 24.0f, 0.1f), 0.0f,
        AudioParameterFloatAttributes().withLabel ("dB")));

    // NOTE: there is intentionally no "reference" parameter. The reference is a
    // user-loaded file measured offline for a passive LUFS/TP readout (ADR-0035),
    // not an automatable on/off match -- so it lives in the state tree (the file
    // path), not as a host-automatable parameter.

    // Default ON: this gates the master tone-stage glue comp, which mastering.py
    // ALWAYS applies. Default-on keeps the out-of-box master in sync with the
    // CLI/GUI (DSP SYNC RULE); turning it OFF is a deliberate plugin-only deviation.
    layout.add (std::make_unique<AudioParameterBool> (
        ParameterID { "glue", 1 }, "Bus Glue", true));

    // Loudness-matched A/B: when on, monitor the dry input gain-matched to the
    // master's loudness. Automatable so it can be toggled from the host.
    layout.add (std::make_unique<AudioParameterBool> (
        ParameterID { "abmatch", 1 }, "A/B (matched)", false));

    // Plugin-only oversampling quality on the live clip/limiter (ADR-0033).
    // 0 = 2x (eco), 1 = 4x (default), 2 = 8x (high). Meta: it re-preps the chain.
    layout.add (std::make_unique<AudioParameterChoice> (
        ParameterID { "osquality", 1 }, "Oversampling",
        StringArray { "2x (eco)", "4x", "8x (high)" }, 1,
        AudioParameterChoiceAttributes().withMeta (true)));

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

        kShelfDry[ch].coefficients = shelf;
        kHighpassDry[ch].coefficients = hp;
        kShelfDry[ch].prepare (spec);
        kHighpassDry[ch].prepare (spec);
        kShelfDry[ch].reset();
        kHighpassDry[ch].reset();
    }

    windowCapacitySamples = juce::jmax (1, (int) std::round (currentSampleRate * 0.4));
    window.clear();
    window.reserve (256);

    // Short-term (3 s) window + integrated-loudness gating state.
    stCapacitySamples = juce::jmax (1, (int) std::round (currentSampleRate * 3.0));
    stWindow.clear();
    stWindow.reserve (512);

    gateHopSamples = juce::jmax (1, (int) std::round (currentSampleRate * 0.1));
    intgHist.assign ((size_t) kIntgNumBins, 0);
    lraHist.assign ((size_t) kIntgNumBins, 0);
    intgBinEnergy.resize ((size_t) kIntgNumBins);
    for (int b = 0; b < kIntgNumBins; ++b)
    {
        const double centre = kIntgMinLufs + (b + 0.5) * kIntgBinWidth;
        intgBinEnergy[(size_t) b] = std::pow (10.0, (centre + 0.691) / 10.0);
    }

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

    // True-peak limiter runs in the oversampled domain (factor from the quality
    // selector, ADR-0033; threshold set per block). Default index -> 4x.
    currentBlockSize = (int) block;
    const int osExp = osFactorExponent();
    oversampleRate = currentSampleRate * std::pow (2.0, osExp);
    juce::dsp::ProcessSpec osSpec {
        oversampleRate, (juce::uint32) (block << (size_t) osExp), 2 };
    limiter.prepare (osSpec);
    limiter.setRelease (kLimReleaseMs);

    processOversampler = std::make_unique<juce::dsp::Oversampling<float>> (
        2, osExp, juce::dsp::Oversampling<float>::filterHalfBandPolyphaseIIR);
    processOversampler->initProcessing (block);
    setLatencySamples ((int) std::round (processOversampler->getLatencyInSamples()));

    // Static makeup: declick knob drags over 30 ms; start AT the set value so a
    // fresh render has no ramp.
    makeupGain.reset (currentSampleRate, 0.03);
    const float makeupDb0 = apvts.getRawParameterValue ("makeup")->load();
    makeupGain.setCurrentAndTargetValue ((float) dbToGain (makeupDb0));

    // Loudness-matched A/B state.
    dryBuffer.setSize (2, juce::jmax (1, samplesPerBlock), false, false, true);
    dryEnergyEma = wetEnergyEma = 0.0;
    abMixSmoothed.reset (currentSampleRate, 0.02);
    abMixSmoothed.setCurrentAndTargetValue (
        apvts.getRawParameterValue ("abmatch")->load() > 0.5f ? 1.0f : 0.0f);
    matchGainSmoothed.reset (currentSampleRate, 0.05);
    matchGainSmoothed.setCurrentAndTargetValue (1.0f);

    resetMeters();
}

void KeelAudioProcessor::resetMeters()
{
    window.clear();
    windowSumSq[0] = windowSumSq[1] = 0.0;
    windowSamples = 0;
    stWindow.clear();
    stSumSq[0] = stSumSq[1] = 0.0;
    stSamples = 0;
    std::fill (intgHist.begin(), intgHist.end(), 0);
    std::fill (lraHist.begin(), lraHist.end(), 0);
    samplesSinceGate = 0;
    integratedResetRequested.store (false);
    truePeakHold = 0.0f;
    truePeakMaxLin = 0.0f;
    grHold = 0.0f;
    momentaryLufs.store (kSilenceFloor);
    shortTermLufs.store (kSilenceFloor);
    integratedLufs.store (kSilenceFloor);
    loudnessRange.store (-1.0f);
    gainReductionDb.store (0.0f);
    truePeakDb.store (kSilenceFloor);
    truePeakMaxDb.store (kSilenceFloor);
}

// Recompute the integrated loudness from the gating-block histogram: the -10 LU
// relative gate is applied on top of the -70 LKFS absolute gate (all binned blocks
// already clear the absolute gate), then integrated = mean energy of the surviving
// blocks, expressed as LKFS. Called on the audio thread every 100 ms; the histogram
// is only ever written on the audio thread, so this needs no lock.
void KeelAudioProcessor::updateIntegrated()
{
    long long total = 0;
    double sumEnergy = 0.0;
    for (int b = 0; b < kIntgNumBins; ++b)
    {
        const int c = intgHist[(size_t) b];
        if (c > 0) { total += c; sumEnergy += (double) c * intgBinEnergy[(size_t) b]; }
    }
    if (total <= 0) { integratedLufs.store (kSilenceFloor); return; }

    const double meanAbs   = sumEnergy / (double) total;
    const double relThresh = (-0.691 + 10.0 * std::log10 (meanAbs)) - 10.0;
    int relBin = (int) std::floor ((relThresh - kIntgMinLufs) / kIntgBinWidth);
    relBin = juce::jlimit (0, kIntgNumBins, relBin);

    long long countRel   = 0;
    double    sumEnergyRel = 0.0;
    for (int b = relBin; b < kIntgNumBins; ++b)
    {
        const int c = intgHist[(size_t) b];
        if (c > 0) { countRel += c; sumEnergyRel += (double) c * intgBinEnergy[(size_t) b]; }
    }
    if (countRel <= 0) { integratedLufs.store (kSilenceFloor); return; }

    const double meanRel = sumEnergyRel / (double) countRel;
    integratedLufs.store (juce::jmax (kSilenceFloor,
        (float) (-0.691 + 10.0 * std::log10 (meanRel))));
}

// Recompute the loudness range (EBU R128 / Tech 3342) from the short-term
// histogram: absolute-gate at -70 LKFS (all binned values already clear it), apply
// the -20 LU relative gate, then LRA = P95 - P10 of the surviving short-term
// loudness distribution. Bin-centre percentiles are accurate to the 0.1 LU bin
// width, ample for a readout. Audio thread only; lraHist is written here only.
void KeelAudioProcessor::updateLra()
{
    long long total = 0;
    double sumEnergy = 0.0;
    for (int b = 0; b < kIntgNumBins; ++b)
    {
        const int c = lraHist[(size_t) b];
        if (c > 0) { total += c; sumEnergy += (double) c * intgBinEnergy[(size_t) b]; }
    }
    if (total < 2) { loudnessRange.store (-1.0f); return; }

    const double meanAbs   = sumEnergy / (double) total;
    const double relThresh = (-0.691 + 10.0 * std::log10 (meanAbs)) - 20.0;
    int relBin = (int) std::floor ((relThresh - kIntgMinLufs) / kIntgBinWidth);
    relBin = juce::jlimit (0, kIntgNumBins, relBin);

    long long gated = 0;
    for (int b = relBin; b < kIntgNumBins; ++b)
        gated += lraHist[(size_t) b];
    if (gated < 2) { loudnessRange.store (-1.0f); return; }

    const long long lowRank  = (long long) std::floor ((double) (gated - 1) * 0.10 + 0.5);
    const long long highRank = (long long) std::floor ((double) (gated - 1) * 0.95 + 0.5);

    long long cum = 0;
    double lLow = kIntgMinLufs, lHigh = kIntgMinLufs;
    bool gotLow = false;
    for (int b = relBin; b < kIntgNumBins; ++b)
    {
        const int c = lraHist[(size_t) b];
        if (c == 0) continue;
        const long long next = cum + c;
        const double centre = kIntgMinLufs + (b + 0.5) * kIntgBinWidth;
        if (! gotLow && lowRank < next) { lLow = centre; gotLow = true; }
        if (highRank < next)            { lHigh = centre; break; }
        cum = next;
    }
    loudnessRange.store ((float) juce::jmax (0.0, lHigh - lLow));
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
    const bool  abOn      = apvts.getRawParameterValue ("abmatch")->load() > 0.5f;

    // Capture the dry input before the chain alters it (loudness-matched A/B).
    for (int ch = 0; ch < numCh; ++ch)
        dryBuffer.copyFrom (ch, 0, buffer, ch, 0, numSamples);

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
    //    Peak in-vs-out across this stage gives the gain reduction to display.
    const float preLimPeak = numSamples > 0 ? buffer.getMagnitude (0, numSamples) : 0.0f;
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

    // Gain reduction (dB, <= 0): how much the clip/limiter pulled the peak down.
    // Fast attack (jump to a deeper reduction) + slow release (~8 dB/s toward 0)
    // so brief limiting stays legible on the history graph.
    if (numSamples > 0)
    {
        const float postLimPeak = buffer.getMagnitude (0, numSamples);
        float grDb = 0.0f;
        if (preLimPeak > 1.0e-6f && postLimPeak > 1.0e-9f)
            grDb = juce::jmin (0.0f,
                juce::Decibels::gainToDecibels (postLimPeak / preLimPeak));
        const float release = 8.0f * (float) (numSamples / currentSampleRate);
        grHold = juce::jmin (grDb, grHold + release);
        gainReductionDb.store (grHold);
    }
    // ===========================================================================

    // --- Below we only MEASURE the OUTPUT; we never write to the buffer. ---

    // Honour a pending reset before folding in this block's energy. Integrated,
    // loudness range and the true-peak peak-hold share one measurement session.
    if (integratedResetRequested.exchange (false))
    {
        std::fill (intgHist.begin(), intgHist.end(), 0);
        std::fill (lraHist.begin(), lraHist.end(), 0);
        samplesSinceGate = 0;
        truePeakMaxLin = 0.0f;
        integratedLufs.store (kSilenceFloor);
        loudnessRange.store (-1.0f);
        truePeakMaxDb.store (kSilenceFloor);
    }

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

    // 1a) Loudness-matched A/B: K-weight the captured dry input and track wet vs
    //     dry energy as an EMA (~0.4 s), so the dry passthrough can be replayed
    //     gain-matched to the master's loudness. Metering above/below stays on the
    //     wet master, so the A/B monitor never pollutes the integrated reading.
    if (numSamples > 0)
    {
        double drySumSq = 0.0;
        for (int ch = 0; ch < juce::jmin (numCh, 2); ++ch)
        {
            const float* in = dryBuffer.getReadPointer (ch);
            double s2 = 0.0;
            for (int i = 0; i < numSamples; ++i)
            {
                float s = kShelfDry[ch].processSample (in[i]);
                s = kHighpassDry[ch].processSample (s);
                s2 += (double) s * (double) s;
            }
            drySumSq += s2;
        }
        const double a = std::exp (- (double) numSamples / (currentSampleRate * 0.4));
        const double zWet = (blk.sumSq[0] + blk.sumSq[1]) / (double) numSamples;
        const double zDry = drySumSq / (double) numSamples;
        wetEnergyEma = a * wetEnergyEma + (1.0 - a) * zWet;
        dryEnergyEma = a * dryEnergyEma + (1.0 - a) * zDry;
    }

    // 1b) Short-term LUFS over a 3 s window (same K-weighted block energies).
    stWindow.push_back (blk);
    stSumSq[0] += blk.sumSq[0];
    stSumSq[1] += blk.sumSq[1];
    stSamples  += numSamples;
    while (stSamples - stWindow.front().numSamples >= stCapacitySamples
           && stWindow.size() > 1)
    {
        const Block& old = stWindow.front();
        stSumSq[0] -= old.sumSq[0];
        stSumSq[1] -= old.sumSq[1];
        stSamples  -= old.numSamples;
        stWindow.erase (stWindow.begin());
    }
    if (stSamples > 0)
    {
        const double z = (stSumSq[0] + stSumSq[1]) / (double) stSamples;
        shortTermLufs.store (z > 1.0e-12
            ? juce::jmax (kSilenceFloor, (float) (-0.691 + 10.0 * std::log10 (z)))
            : kSilenceFloor);
    }

    // 1c) Integrated LUFS: once the 400 ms window is full, take its energy as a
    //     BS.1770 gating block every 100 ms, absolute-gate at -70 LKFS, bin it, and
    //     re-evaluate the gated integrated loudness.
    samplesSinceGate += numSamples;
    if (samplesSinceGate >= gateHopSamples && windowSamples >= windowCapacitySamples)
    {
        samplesSinceGate = 0;
        const double z = (windowSumSq[0] + windowSumSq[1]) / (double) windowSamples;
        if (z > 1.0e-12)
        {
            const double l = -0.691 + 10.0 * std::log10 (z);
            if (l >= kIntgMinLufs)
            {
                int b = (int) std::floor ((l - kIntgMinLufs) / kIntgBinWidth);
                b = juce::jlimit (0, kIntgNumBins - 1, b);
                ++intgHist[(size_t) b];
                updateIntegrated();
            }
        }

        // Loudness range: bin the current short-term (3 s) loudness at the same
        // cadence, once the short-term window has filled.
        if (stSamples >= stCapacitySamples)
        {
            const double zst = (stSumSq[0] + stSumSq[1]) / (double) stSamples;
            if (zst > 1.0e-12)
            {
                const double lst = -0.691 + 10.0 * std::log10 (zst);
                if (lst >= kIntgMinLufs)
                {
                    int b = (int) std::floor ((lst - kIntgMinLufs) / kIntgBinWidth);
                    b = juce::jlimit (0, kIntgNumBins - 1, b);
                    ++lraHist[(size_t) b];
                    updateLra();
                }
            }
        }
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

    // Latched peak-hold: the maximum true-peak reached since the last reset.
    truePeakMaxLin = juce::jmax (truePeakMaxLin, blockPeak);
    if (truePeakMaxLin > 1.0e-6f)
        truePeakMaxDb.store (juce::jmax (kSilenceFloor,
            juce::Decibels::gainToDecibels (truePeakMaxLin)));

    // --- Loudness-matched A/B OUTPUT (last, so meters above measured the wet
    //     master). Blends the buffer toward the gain-matched dry input when
    //     engaged; a smoothed mix declicks the toggle.
    if (numSamples > 0)
    {
        float matchLin = 1.0f;
        if (dryEnergyEma > 1.0e-12 && wetEnergyEma > 1.0e-12)
            matchLin = juce::jlimit (0.0625f, 16.0f,          // clamp to +/-24 dB
                (float) std::sqrt (wetEnergyEma / dryEnergyEma));
        abMixSmoothed.setTargetValue (abOn ? 1.0f : 0.0f);
        matchGainSmoothed.setTargetValue (matchLin);

        for (int i = 0; i < numSamples; ++i)
        {
            const float mix = abMixSmoothed.getNextValue();
            const float mg  = matchGainSmoothed.getNextValue();
            if (mix <= 1.0e-5f) continue;   // pure wet master; nothing to blend
            for (int ch = 0; ch < numCh; ++ch)
            {
                float* x = buffer.getWritePointer (ch);
                const float dry = dryBuffer.getReadPointer (ch)[i];
                x[i] = x[i] + (dry * mg - x[i]) * mix;
            }
        }
    }
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

void KeelAudioProcessor::setStateFromXml (const juce::XmlElement& xml)
{
    if (! xml.hasTagName (apvts.state.getType()))
        return;

    apvts.replaceState (juce::ValueTree::fromXml (xml));

    // Adopt the restored preset as already-applied so the queued async (fired by
    // replaceState) does NOT overwrite the restored LUFS/TP.
    lastAppliedPreset = (int) apvts.getRawParameterValue ("preset")->load();

    // Re-measure a saved reference, if any, so its readout returns.
    const auto path = apvts.state.getProperty ("referencePath", juce::String()).toString();
    if (path.isNotEmpty())
        loadReference (juce::File (path));
}

void KeelAudioProcessor::setStateInformation (const void* data, int sizeInBytes)
{
    if (auto xml = getXmlFromBinary (data, sizeInBytes))
        setStateFromXml (*xml);
}

// JUCE entry point.
juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new KeelAudioProcessor();
}
