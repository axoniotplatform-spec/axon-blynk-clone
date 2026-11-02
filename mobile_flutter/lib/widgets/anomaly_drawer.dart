import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';
import '../services/api_client.dart';

class AnomalyDrawer extends StatelessWidget {
  final List<dynamic> anomalies;
  final AxonApiClient apiClient;
  final VoidCallback onRefresh;

  const AnomalyDrawer({
    super.key,
    required this.anomalies,
    required this.apiClient,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        color: AxonTheme.bgSurface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.warning_amber_rounded, color: AxonTheme.criticalRed, size: 24),
                  const SizedBox(width: 10),
                  Text(
                    "ACTIVE ANOMALY ALERTS (${anomalies.length})",
                    style: const TextStyle(
                      color: AxonTheme.textMain,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.close, color: AxonTheme.textMuted),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (anomalies.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 30),
              child: Center(
                child: Text(
                  "All telemetry streams nominal. Zero active faults.",
                  style: TextStyle(color: AxonTheme.textMuted, fontSize: 14),
                ),
              ),
            )
          else
            Flexible(
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: anomalies.length,
                separatorBuilder: (_, _) => const SizedBox(height: 10),
                itemBuilder: (context, index) {
                  final alert = anomalies[index];
                  final isCritical = alert['severity'] == 'CRITICAL';
                  return Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AxonTheme.bgCard,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: isCritical ? AxonTheme.criticalRed.withValues(alpha: 0.5) : AxonTheme.warningAmber.withValues(alpha: 0.5),
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                              decoration: BoxDecoration(
                                color: (isCritical ? AxonTheme.criticalRed : AxonTheme.warningAmber).withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                alert['anomalyType'] ?? 'ANOMALY',
                                style: TextStyle(
                                  color: isCritical ? AxonTheme.criticalRed : AxonTheme.warningAmber,
                                  fontSize: 11,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            Text(
                              "PIN V${alert['pin'] ?? '?'}",
                              style: const TextStyle(color: AxonTheme.neonCyan, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(
                          alert['message'] ?? 'Operational deviation detected',
                          style: const TextStyle(color: AxonTheme.textMain, fontSize: 13, height: 1.3),
                        ),
                        const SizedBox(height: 10),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton.icon(
                            style: TextButton.styleFrom(
                              foregroundColor: AxonTheme.activeGreen,
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                            ),
                            icon: const Icon(Icons.check_circle_outline, size: 16),
                            label: const Text("Acknowledge & Resolve", style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                            onPressed: () async {
                              await apiClient.resolveAnomaly(alert['id']);
                              onRefresh();
                              if (context.mounted) {
                                Navigator.pop(context);
                              }
                            },
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
        ],
      ),
    );
  }
}
