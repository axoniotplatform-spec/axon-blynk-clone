import 'package:flutter/material.dart';
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

  @override
  void initState() {
    super.initState();
    _loadData();
    widget.wsService.connect(widget.apiClient.baseUrl);
    widget.wsService.onRawEvent.listen((event) {
      if (event['type'] == 'ANOMALY_ALERTS') {
        _loadAnomalies();
      }
    });
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
                      // Anomaly Alert Bell with Badge
                      Stack(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.notifications_none_rounded, color: AxonTheme.textMain, size: 26),
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
                        icon: const Icon(Icons.refresh_rounded, color: AxonTheme.textMain, size: 24),
                        onPressed: _loadData,
                      ),
                      IconButton(
                        icon: const Icon(Icons.logout_rounded, color: AxonTheme.textMuted, size: 22),
                        tooltip: "Sign Out",
                        onPressed: () async {
                          await widget.apiClient.clearSession();
                          if (context.mounted) {
                            Navigator.pushReplacement(
                              context,
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

            // Fleet Device Section Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                  Text(
                    "${_devices.length} NODES",
                    style: const TextStyle(
                      color: AxonTheme.neonCyan,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
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

                            return GlassContainer(
                              isInteractive: true,
                              onTap: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) => DeviceDashboardScreen(
                                      deviceId: dev['id'],
                                      deviceName: dev['name'] ?? 'Device ${dev['id']}',
                                      token: dev['token'] ?? dev['auth_token'] ?? dev['authToken'] ?? 'bc26634b58b05e31a7cf38d88fa78346',
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
