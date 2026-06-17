# Keel plugin (Phase 5, ADR-0029)
#
# A self-contained JUCE/C++ master-bus plugin: it runs Keel's master chain live
# (a faithful C++ port of mastering.py) and you deliver by exporting from the DAW
# with it active. No offline step. The C++ chain mirrors the Python master
# character (DSP SYNC RULE); the CLI/GUI remain the byte-identical reference.
#
# Build (from this folder):
#   cmake -B build -G "Visual Studio 18 2026" -A x64
#   cmake --build build --config Release
# or use .\build.ps1

cmake_minimum_required(VERSION 3.22)

project(KeelPlugin VERSION 0.3.0 LANGUAGES C CXX)   # keep in sync with keel.py __version__ (unified versioning, CLAUDE.md)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- JUCE 8 via FetchContent (online; matches "GUI deps online, not vendored",
#     ADR-0020). Pinned to a stable tag; shallow clone to keep it light. ---
include(FetchContent)
FetchContent_Declare(
    JUCE
    GIT_REPOSITORY https://github.com/juce-framework/JUCE.git
    GIT_TAG        8.0.9
    GIT_SHALLOW    TRUE
)
FetchContent_MakeAvailable(JUCE)

# --- Auto-install the built plugin where the DAW will scan it. The JUCE Windows
#     default is C:/Program Files/Common Files/VST3, which needs admin; point it
#     at the per-user VST3 folder (the VST3 spec's user location) instead, so
#     every build drops Keel.vst3 straight into a scanned path with no elevation.
if (WIN32)
    set_directory_properties(PROPERTIES
        JUCE_VST3_COPY_DIR "$ENV{LOCALAPPDATA}/Programs/Common/VST3")
elseif (APPLE)
    set_directory_properties(PROPERTIES
        JUCE_VST3_COPY_DIR "$ENV{HOME}/Library/Audio/Plug-Ins/VST3")
endif()

# --- The plugin target: master-bus processor, VST3 + Standalone. ---
juce_add_plugin(KeelPlugin
    PRODUCT_NAME                "Keel"
    COMPANY_NAME                "Felipe Carvajal Brown"
    BUNDLE_ID                   com.felipecarvajalbrown.keel
    PLUGIN_MANUFACTURER_CODE    Fcbn
    PLUGIN_CODE                 Keel
    FORMATS                     VST3 Standalone
    IS_SYNTH                    FALSE
    NEEDS_MIDI_INPUT            FALSE
    NEEDS_MIDI_OUTPUT           FALSE
    IS_MIDI_EFFECT              FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS FALSE
    COPY_PLUGIN_AFTER_BUILD     TRUE
    VST3_CATEGORIES             "Mastering" "Dynamics"
    DESCRIPTION                 "Keel master-bus processor"
)

# Bundle the Space Grotesk family (SIL OFL) so the plugin UI matches the
# standalone GUI's visual language without depending on a system font.
juce_add_binary_data(KeelData SOURCES
    ../assets/fonts/SpaceGrotesk-Regular.ttf
    ../assets/fonts/SpaceGrotesk-Medium.ttf
    ../assets/fonts/SpaceGrotesk-Bold.ttf
)

target_sources(KeelPlugin PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp
    Source/KeelLookAndFeel.cpp
)

target_compile_definitions(KeelPlugin PUBLIC
    JUCE_WEB_BROWSER=0
    JUCE_USE_CURL=0
    JUCE_VST3_CAN_REPLACE_VST2=0
)

target_link_libraries(KeelPlugin
    PRIVATE
        KeelData
        juce::juce_audio_utils
        juce::juce_dsp
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_lto_flags
        juce::juce_recommended_warning_flags
)
