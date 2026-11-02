# Axon IoT — Glassmorphic Mobile & Web Client

Enterprise mobile and web operator application for the **Axon IoT** self-hosted industrial telemetry & Blynk-compatible hardware gateway platform.

## Key Capabilities
- **Glassmorphic Authentication**: Multi-tenant **Sign In** and **Create Enterprise Tenant** workflows with persistent JWT/Bearer session management and configurable Gateway Server URL.
- **Fleet Overview**: Real-time online/offline telemetry pulse, signal strength, and instant hardware drill-down.
- **5-Subtab Hardware Dashboard**: Interactive **Controls** (switches & sliders), **Gauges**, **SuperChart** real-time waveforms, **Terminal CLI**, and unified **All** view synchronized over WebSockets and `/external/api/update`.
- **Anomaly Alert Center**: Real-time severity-graded anomaly alert drawer with one-tap resolution.
- **Zero Third-Party Branding**: Custom Axon IoT cyber-bolt launcher icons, native `#070A12` dark cold-boot splash screen, and zero third-party watermarks or debug banners.

## Build Targets
- **Android Release APK**: `flutter build apk --release --split-per-abi`
- **Production Web App (`/flutter/`)**: `flutter build web --release --base-href /flutter/`
