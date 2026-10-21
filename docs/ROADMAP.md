# Development roadmap / 開発計画

## v0.1 (implemented): zero-cost offline baseline

- Windows / Tkinter GUI, import or record a trigger sample.
- Persist enrolled examples on local disk.
- Choose one or more samples and apply template-based spectrogram attenuation to an input file.
- Save a processed WAV without sending audio to any server.
- Unit tests with synthetic audio.

**Known limitations:** Not a learned sound recognition or high-quality separation model. Cannot reliably remove chewing/mouth sounds from overlapping speech. Only max 120 seconds per file; no realtime capture or playback replacement. No binaural transparency, no ANC.

## v0.2: evaluate genuinely selective audio-source separation

- Prepare consented test mixtures and objective preservation metrics.
- Compare zero-cost, locally runnable open-source example-conditioned separation models (for example SoloAudio / CLAPSep) and their **model weight licenses**, hardware requirements, and latency.
- Favor reproducible comparisons using recordings of actual trigger sounds and non-trigger sounds.
- Preserve voices and warning sounds; measure false suppression as well as trigger attenuation.

## v0.3: Windows PC-audio realtime prototype

- WASAPI capture and virtual audio routing to a separate output endpoint.
- Streaming buffering and performance measurement. Implement a true streaming model rather than assuming an offline model is low-latency.
- Explicit bypass, output gain limits, no-feedback checks, and CPU/GPU failover.

## Future: microphone + isolating headphone passthrough

A microphone-based environmental audio filter is **not** equivalent to canceling incoming airborne sound. Standard speakers or unsealed headphones cannot prevent direct sound reaching the ear. Validate acoustic leakage, end-to-end delay, clipping, emergency-audibility, physical comfort, and ethical implications before pursuing this.

## Research considerations

Treat this as an accommodation/assistive tool; efficacy as a treatment for misophonia is not established. Keep acute discomfort, functional participation, false cancellation, and longer-term symptom trajectories as separate endpoints.
