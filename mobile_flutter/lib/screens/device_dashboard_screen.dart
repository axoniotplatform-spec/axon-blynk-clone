import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme/axon_theme.dart';
import '../services/api_client.dart';
import '../services/websocket_service.dart';
import '../widgets/glass_container.dart';
import '../widgets/ios_switch_widget.dart';
import '../widgets/level_slider_widget.dart';
import '../widgets/radial_gauge_widget.dart';
import '../widgets/superchart_widget.dart';
import '../widgets/terminal_cli_widget.dart';

class DeviceDashboardScreen extends StatefulWidget {
  final int deviceId;
  final String deviceName;
  final String token;
  final AxonApiClient apiClient;
  final AxonWebSocketService wsService;

  const DeviceDashboardScreen({
    super.key,
    required this.deviceId,
    required this.deviceName,
    required this.token,
    required this.apiClient,
    required this.wsService,
  });

  @override
  State<DeviceDashboardScreen> createState() => _DeviceDashboardScreenState();
}

class _DeviceDashboardScreenState extends State<DeviceDashboardScreen> {
  String _activeSubtab = "Controls";
  final List<String> _subtabs = ["Controls", "Gauges", "SuperChart", "Terminal", "All"];

  // Real-time pin states
  bool _v0Led = false;
  double _v1Brightness = 128.0;
  double _v2Temperature = 26.5;
  bool _v3FanRelay = false;
  double _v4TargetSetpoint = 30.0;
  double _v5Humidity = 55.0;
  final List<FlSpot> _chartSpots = [
    const FlSpot(0, 24),
    const FlSpot(1, 25),
    const FlSpot(2, 26),
    const FlSpot(3, 27),
    const FlSpot(4, 26.5),
  ];

  @override
  void initState() {
    super.initState();
    _listenTelemetry();
  }

  void _listenTelemetry() {
    widget.wsService.onTelemetryUpdated.listen((update) {
      if (!mounted) return;
      if (update.deviceId == widget.deviceId || update.deviceId == 0) {
        setState(() {
          final pin = update.pin;
          final val = update.value;

          if (pin == "V0") {
            _v0Led = val == "1" || val.toLowerCase() == "true";
          } else if (pin == "V1") {
            _v1Brightness = double.tryParse(val) ?? _v1Brightness;
          } else if (pin == "V2") {
            _v2Temperature = double.tryParse(val) ?? _v2Temperature;
            _chartSpots.add(FlSpot(_chartSpots.length.toDouble(), _v2Temperature));
            if (_chartSpots.length > 20) _chartSpots.removeAt(0);
          } else if (pin == "V3") {
            _v3FanRelay = val == "1" || val.toLowerCase() == "true";
          } else if (pin == "V4") {
            _v4TargetSetpoint = double.tryParse(val) ?? _v4TargetSetpoint;
          } else if (pin == "V5") {
            _v5Humidity = double.tryParse(val) ?? _v5Humidity;
          }
        });
      }
    });
  }

  void _onSwitchChanged(String pin, bool val) {
    setState(() {
      if (pin == "V0") _v0Led = val;
      if (pin == "V3") _v3FanRelay = val;
    });
    widget.apiClient.updatePinValue(widget.token, pin, val ? "1" : "0");
  }

  void _onSliderChanged(String pin, double val) {
    setState(() {
      if (pin == "V1") _v1Brightness = val;
      if (pin == "V4") _v4TargetSetpoint = val;
    });
    widget.apiClient.updatePinValue(widget.token, pin, val.toStringAsFixed(0));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GlassScaffoldBackground(
        child: Column(
          children: [
            // Top Navigation & Device Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AxonTheme.textMain, size: 20),
                    onPressed: () => Navigator.pop(context),
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.deviceName,
                          style: const TextStyle(
                            color: AxonTheme.textMain,
                            fontSize: 17,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const Text(
                          "HARDWARE GATEWAY: PORT 8080 (BLYNK V1 WIRE)",
                          style: TextStyle(
                            color: AxonTheme.neonCyan,
                            fontSize: 10,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                    decoration: BoxDecoration(
                      color: AxonTheme.pulseGreen.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AxonTheme.pulseGreen.withValues(alpha: 0.4)),
                    ),
                    child: const Text(
                      "ONLINE",
                      style: TextStyle(
                        color: AxonTheme.pulseGreen,
                        fontSize: 11,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Glassmorphic Subtabs Bar
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: _subtabs.map((tab) {
                  final isActive = _activeSubtab == tab;
                  return GestureDetector(
                    onTap: () {
                      setState(() {
                        _activeSubtab = tab;
                      });
                    },
                    child: Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: isActive ? AxonTheme.neonCyan.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isActive ? AxonTheme.neonCyan : Colors.white.withValues(alpha: 0.12),
                          width: 1.2,
                        ),
                        boxShadow: isActive
                            ? [
                                BoxShadow(
                                  color: AxonTheme.neonCyan.withValues(alpha: 0.25),
                                  blurRadius: 10,
                                ),
                              ]
                            : null,
                      ),
                      child: Text(
                        tab.toUpperCase(),
                        style: TextStyle(
                          color: isActive ? AxonTheme.neonCyan : AxonTheme.textSub,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.6,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ),

            // Dynamic Widget Canvas
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: _buildCanvas(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCanvas() {
    switch (_activeSubtab) {
      case "Controls":
        return ListView(
          children: [
            IosSwitchWidget(
              title: "Fan Cooling Relay",
              pin: "V3",
              value: _v3FanRelay,
              onChanged: (val) => _onSwitchChanged("V3", val),
            ),
            const SizedBox(height: 12),
            IosSwitchWidget(
              title: "Primary Indicator LED",
              pin: "V0",
              value: _v0Led,
              onChanged: (val) => _onSwitchChanged("V0", val),
            ),
            const SizedBox(height: 12),
            LevelSliderWidget(
              title: "LED Brightness Level",
              pin: "V1",
              value: _v1Brightness,
              min: 0,
              max: 255,
              units: "PWM",
              onChanged: (val) => _onSliderChanged("V1", val),
            ),
            const SizedBox(height: 12),
            LevelSliderWidget(
              title: "Target Temperature Setpoint",
              pin: "V4",
              value: _v4TargetSetpoint,
              min: 15,
              max: 50,
              units: "°C",
              onChanged: (val) => _onSliderChanged("V4", val),
            ),
          ],
        );

      case "Gauges":
        return GridView.count(
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 0.85,
          children: [
            RadialGaugeWidget(
              title: "Core Temp",
              pin: "V2",
              value: _v2Temperature,
              min: 0,
              max: 80,
              units: "°C",
            ),
            RadialGaugeWidget(
              title: "Humidity",
              pin: "V5",
              value: _v5Humidity,
              min: 0,
              max: 100,
              units: "%",
            ),
          ],
        );

      case "SuperChart":
        return ListView(
          children: [
            SuperChartWidget(
              title: "Real-Time Temperature Stream",
              pin: "V2",
              spots: _chartSpots,
              units: "°C",
            ),
          ],
        );

      case "Terminal":
        return TerminalCliWidget(
          onCommandSubmitted: (cmd) {
            // Echo command
          },
        );

      case "All":
      default:
        return ListView(
          children: [
            IosSwitchWidget(
              title: "Fan Cooling Relay",
              pin: "V3",
              value: _v3FanRelay,
              onChanged: (val) => _onSwitchChanged("V3", val),
            ),
            const SizedBox(height: 12),
            LevelSliderWidget(
              title: "LED Brightness Level",
              pin: "V1",
              value: _v1Brightness,
              min: 0,
              max: 255,
              units: "PWM",
              onChanged: (val) => _onSliderChanged("V1", val),
            ),
            const SizedBox(height: 12),
            RadialGaugeWidget(
              title: "Core Temperature",
              pin: "V2",
              value: _v2Temperature,
              min: 0,
              max: 80,
              units: "°C",
            ),
            const SizedBox(height: 12),
            SuperChartWidget(
              title: "Telemetry Trend",
              pin: "V2",
              spots: _chartSpots,
              units: "°C",
            ),
          ],
        );
    }
  }
}
