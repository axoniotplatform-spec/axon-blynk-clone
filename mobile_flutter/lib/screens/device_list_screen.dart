import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/axon_theme.dart';
import '../services/api_client.dart';
import '../services/websocket_service.dart';
import '../widgets/glass_container.dart';
import '../widgets/anomaly_drawer.dart';
import 'device_dashboard_screen.dart';
import 'auth_screen.dart';

class DeviceListScreen extends StatefulWidget {
  final AxonApiClient apiClient;
  final AxonWebSocketService wsService;

  const DeviceListScreen({
    super.key,
    required this.apiClient,
    required this.wsService,
  });

  @override
  State<DeviceListScreen> createState() => _DeviceListScreenState();
}

class _DeviceListScreenState extends State<DeviceListScreen> {
  List<dynamic> _devices = [];
  List<dynamic> _anomalies = [];
  bool _isLoading = true;
  String _serverStatus = "connecting...";
  bool _simRunning = false;

  @override
  void initState() {
    super.initState();
    _loadData();
    _checkSimStatus();
    widget.wsService.connect(widget.apiClient.baseUrl);
    widget.wsService.onRawEvent.listen((event) {
      if (event['type'] == 'ANOMALY_ALERTS') {
        _loadAnomalies();
      } else if (event['type'] == 'onDeviceCreated' || event['type'] == 'onDeviceDeleted') {
        _loadData();
      } else if (event['type'] == 'onSimulatorStateChanged') {
        if (mounted && event['data'] != null && event['data']['running'] != null) {
          setState(() {
            _simRunning = event['data']['running'] == true;
          });
        }
      }
    });
  }

  Future<void> _checkSimStatus() async {
    final st = await widget.apiClient.fetchSimulatorStatus();
    if (mounted) {
      setState(() {
        _simRunning = st['running'] == true;
      });
    }
  }

  Future<void> _toggleSimulator() async {
    final next = !_simRunning;
    final ok = await widget.apiClient.toggleSimulator(next);
    if (ok && mounted) {
      setState(() {
        _simRunning = next;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(next ? "Live Telemetry Simulator started!" : "Simulator stopped."),
          backgroundColor: next ? AxonTheme.pulseGreen : AxonTheme.electricBlue,
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final health = await widget.apiClient.checkHealth();
    final devs = await widget.apiClient.fetchDevices();
    final anoms = await widget.apiClient.fetchAnomalies();

    setState(() {
      _serverStatus = health['status'] == 'healthy' ? 'ONLINE' : 'DEGRADED';
      _devices = devs;
      _anomalies = anoms;
      _isLoading = false;
    });
  }

  Future<void> _loadAnomalies() async {
    final anoms = await widget.apiClient.fetchAnomalies();
    setState(() {
      _anomalies = anoms;
    });
  }

  void _showAddDeviceDialog() {
    final nameCtrl = TextEditingController(text: "Industrial ESP32 Node");
    String selectedMcu = "ESP32";

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AxonTheme.bgSurface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: AxonTheme.neonCyan.withValues(alpha: 0.3)),
          ),
          title: const Row(
            children: [
              Icon(Icons.add_circle_outline, color: AxonTheme.neonCyan, size: 20),
              SizedBox(width: 8),
              Text("PROVISION NEW NODE", style: TextStyle(color: AxonTheme.textMain, fontSize: 14, fontWeight: FontWeight.bold)),
            ],
          ),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text("DEVICE NAME", style: TextStyle(color: AxonTheme.textSub, fontSize: 11, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              TextField(
                controller: nameCtrl,
                style: const TextStyle(color: AxonTheme.textMain, fontSize: 13),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.black26,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                ),
              ),
              const SizedBox(height: 14),
              const Text("TARGET HARDWARE MCU", style: TextStyle(color: AxonTheme.textSub, fontSize: 11, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              DropdownButton<String>(
                value: selectedMcu,
                isExpanded: true,
                dropdownColor: AxonTheme.bgCard,
                style: const TextStyle(color: AxonTheme.textMain, fontSize: 13),
                items: ["ESP32", "ESP8266", "RP2040", "ARDUINO_UNO_R4"]
                    .map((mcu) => DropdownMenuItem(value: mcu, child: Text(mcu)))
                    .toList(),
                onChanged: (val) {
                  if (val != null) {
                    setDialogState(() => selectedMcu = val);
                  }
                },
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text("CANCEL", style: TextStyle(color: AxonTheme.textMuted)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: AxonTheme.neonCyan),
              onPressed: () async {
                Navigator.pop(ctx);
                final res = await widget.apiClient.createDevice(nameCtrl.text.trim(), mcu: selectedMcu);
                if (res != null) {
                  _loadData();
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text("Provisioned: ${res['name']} (Token: ${res['authToken'] ?? res['token']})")),
                    );
                  }
                }
              },
              child: const Text("PROVISION", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
            ),
          ],
        ),
      ),
    );
  }

  void _showAnomalyDrawer() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => AnomalyDrawer(
        anomalies: _anomalies,
        apiClient: widget.apiClient,
        onRefresh: _loadData,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GlassScaffoldBackground(
        child: Column(
          children: [
            // Top Glassmorphic Navigation Bar
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: const LinearGradient(
                            colors: [AxonTheme.neonCyan, AxonTheme.electricBlue],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: AxonTheme.neonCyan.withValues(alpha: 0.4),
                              blurRadius: 12,
                            ),
                          ],
                        ),
                        child: const Icon(Icons.bolt, color: Colors.black, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            "AXON IOT",
                            style: TextStyle(
                              color: AxonTheme.textMain,
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.2,
                            ),
                          ),
                          Row(
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: _serverStatus == 'ONLINE' ? AxonTheme.pulseGreen : AxonTheme.warningAmber,
                                ),
                              ),
                              const SizedBox(width: 5),
                              Text(
                                "CORE $_serverStatus",
                                style: TextStyle(
                                  color: _serverStatus == 'ONLINE' ? AxonTheme.pulseGreen : AxonTheme.warningAmber,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      // Simulator Toggle Action
                      IconButton(
                        icon: Icon(
                          _simRunning ? Icons.sensors_rounded : Icons.sensors_off_rounded,
                          color: _simRunning ? AxonTheme.pulseGreen : AxonTheme.textMuted,
                          size: 22,
                        ),
                        tooltip: _simRunning ? "Simulator Active" : "Start Live Simulator",
                        onPressed: _toggleSimulator,
                      ),
                      // Anomaly Alert Bell with Badge
                      Stack(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.notifications_none_rounded, color: AxonTheme.textMain, size: 24),
                            onPressed: _showAnomalyDrawer,
                          ),
                          if (_anomalies.isNotEmpty)
                            Positioned(
                              top: 8,
                              right: 8,
                              child: Container(
                                padding: const EdgeInsets.all(4),
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AxonTheme.criticalRed,
                                ),
                                constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                                child: Text(
                                  "${_anomalies.length}",
                                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                  textAlign: TextAlign.center,
                                ),
                              ),
                            ),
                        ],
                      ),
                      IconButton(
                        icon: const Icon(Icons.refresh_rounded, color: AxonTheme.textMain, size: 22),
                        onPressed: _loadData,
                      ),
                      IconButton(
                        icon: const Icon(Icons.logout_rounded, color: AxonTheme.textMuted, size: 20),
                        tooltip: "Sign Out",
                        onPressed: () async {
                          final nav = Navigator.of(context);
                          await widget.apiClient.clearSession();
                          if (mounted) {
                            nav.pushReplacement(
                              MaterialPageRoute(
                                builder: (_) => AuthScreen(
                                  apiClient: widget.apiClient,
                                  wsService: widget.wsService,
                                ),
                              ),
                            );
                          }
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Fleet Device Section Header with + Add Button
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Text(
                        "FLEET DEVICES",
                        style: TextStyle(
                          color: AxonTheme.textSub,
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.0,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Text(
                        "(${_devices.length})",
                        style: const TextStyle(
                          color: AxonTheme.neonCyan,
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AxonTheme.neonCyan.withValues(alpha: 0.15),
                      foregroundColor: AxonTheme.neonCyan,
                      side: BorderSide(color: AxonTheme.neonCyan.withValues(alpha: 0.4)),
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    icon: const Icon(Icons.add, size: 14),
                    label: const Text("PROVISION", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    onPressed: _showAddDeviceDialog,
                  ),
                ],
              ),
            ),

            // Device List
            Expanded(
              child: _isLoading
                  ? const Center(child: CircularProgressIndicator(color: AxonTheme.neonCyan))
                  : _devices.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.developer_board, size: 48, color: AxonTheme.textMuted.withValues(alpha: 0.5)),
                              const SizedBox(height: 12),
                              const Text("No active hardware registered", style: TextStyle(color: AxonTheme.textMuted)),
                              const SizedBox(height: 14),
                              ElevatedButton(
                                onPressed: _showAddDeviceDialog,
                                style: ElevatedButton.styleFrom(backgroundColor: AxonTheme.neonCyan),
                                child: const Text("+ Provision Device", style: TextStyle(color: Colors.black)),
                              ),
                            ],
                          ),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                          itemCount: _devices.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 14),
                          itemBuilder: (context, index) {
                            final dev = _devices[index];
                            final isOnline = dev['status'] == 'ONLINE' || dev['isOnline'] == true;
                            final devToken = dev['token'] ?? dev['auth_token'] ?? dev['authToken'] ?? 'bc26634b58b05e31a7cf38d88fa78346';

                            return GlassContainer(
                              isInteractive: true,
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => DeviceDashboardScreen(
                                      deviceId: dev['id'],
                                      deviceName: dev['name'] ?? 'Device ${dev['id']}',
                                      token: devToken,
                                      apiClient: widget.apiClient,
                                      wsService: widget.wsService,
                                    ),
                                  ),
                                );
                              },
                              child: Row(
                                children: [
                                  Container(
                                    width: 48,
                                    height: 48,
                                    decoration: BoxDecoration(
                                      color: isOnline ? AxonTheme.neonCyan.withValues(alpha: 0.15) : Colors.white.withValues(alpha: 0.06),
                                      borderRadius: BorderRadius.circular(14),
                                      border: Border.all(
                                        color: isOnline ? AxonTheme.neonCyan.withValues(alpha: 0.4) : Colors.white.withValues(alpha: 0.1),
                                      ),
                                    ),
                                    child: Icon(
                                      Icons.memory,
                                      color: isOnline ? AxonTheme.neonCyan : AxonTheme.textMuted,
                                      size: 26,
                                    ),
                                  ),
                                  const SizedBox(width: 14),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          dev['name'] ?? 'Device ${dev['id']}',
                                          style: const TextStyle(
                                            color: AxonTheme.textMain,
                                            fontSize: 16,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        const SizedBox(height: 3),
                                        Row(
                                          children: [
                                            Container(
                                              width: 7,
                                              height: 7,
                                              decoration: BoxDecoration(
                                                shape: BoxShape.circle,
                                                color: isOnline ? AxonTheme.pulseGreen : AxonTheme.textMuted,
                                                boxShadow: isOnline
                                                    ? [
                                                        BoxShadow(
                                                          color: AxonTheme.pulseGreen.withValues(alpha: 0.8),
                                                          blurRadius: 6,
                                                        ),
                                                      ]
                                                    : null,
                                              ),
                                            ),
                                            const SizedBox(width: 6),
                                            Text(
                                              isOnline ? "CONNECTED • PORT 8080" : "STANDBY / OFFLINE",
                                              style: TextStyle(
                                                color: isOnline ? AxonTheme.pulseGreen : AxonTheme.textMuted,
                                                fontSize: 11,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.copy_rounded, color: AxonTheme.textMuted, size: 16),
                                    tooltip: "Copy Token",
                                    onPressed: () {
                                      Clipboard.setData(ClipboardData(text: devToken));
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(content: Text("Auth Token copied to clipboard"), duration: Duration(seconds: 1)),
                                      );
                                    },
                                  ),
                                  const Icon(Icons.arrow_forward_ios_rounded, color: AxonTheme.textMuted, size: 16),
                                ],
                              ),
                            );
                          },
                        ),
            ),
          ],
        ),
      ),
    );
  }
}
