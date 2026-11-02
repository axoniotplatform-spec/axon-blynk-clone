import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../theme/axon_theme.dart';
import 'glass_container.dart';

class SuperChartWidget extends StatefulWidget {
  final String title;
  final String pin;
  final List<FlSpot> spots;
  final String units;

  const SuperChartWidget({
    super.key,
    required this.title,
    required this.pin,
    required this.spots,
    this.units = "",
  });

  @override
  State<SuperChartWidget> createState() => _SuperChartWidgetState();
}

class _SuperChartWidgetState extends State<SuperChartWidget> {
  String _selectedPeriod = "1h";

  @override
  Widget build(BuildContext context) {
    final effectiveSpots = widget.spots.isNotEmpty
        ? widget.spots
        : [
            const FlSpot(0, 24),
            const FlSpot(1, 26),
            const FlSpot(2, 25),
            const FlSpot(3, 28),
            const FlSpot(4, 32),
            const FlSpot(5, 30),
            const FlSpot(6, 35),
          ];

    return GlassContainer(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
                    ),
                    child: Text(
                      widget.pin,
                      style: const TextStyle(
                        color: AxonTheme.neonCyan,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Text(
                    widget.title,
                    style: const TextStyle(
                      color: AxonTheme.textMain,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
              Row(
                children: ["1h", "6h", "1d", "1w"].map((p) {
                  final isSelected = _selectedPeriod == p;
                  return GestureDetector(
                    onTap: () {
                      setState(() {
                        _selectedPeriod = p;
                      });
                    },
                    child: Container(
                      margin: const EdgeInsets.only(left: 4),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: isSelected ? AxonTheme.neonCyan.withValues(alpha: 0.2) : Colors.transparent,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: isSelected ? AxonTheme.neonCyan : Colors.transparent,
                          width: 1,
                        ),
                      ),
                      child: Text(
                        p.toUpperCase(),
                        style: TextStyle(
                          color: isSelected ? AxonTheme.neonCyan : AxonTheme.textMuted,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
          const SizedBox(height: 20),
          SizedBox(
            height: 160,
            child: LineChart(
              LineChartData(
                gridData: FlGridData(
                  show: true,
                  drawVerticalLine: false,
                  getDrawingHorizontalLine: (val) => FlLine(
                    color: Colors.white.withValues(alpha: 0.06),
                    strokeWidth: 1,
                  ),
                ),
                titlesData: FlTitlesData(
                  show: true,
                  rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  leftTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 32,
                      getTitlesWidget: (val, meta) {
                        return Text(
                          val.toStringAsFixed(0),
                          style: const TextStyle(color: AxonTheme.textMuted, fontSize: 10, fontWeight: FontWeight.bold),
                        );
                      },
                    ),
                  ),
                ),
                borderData: FlBorderData(show: false),
                lineBarsData: [
                  LineChartBarData(
                    spots: effectiveSpots,
                    isCurved: true,
                    curveSmoothness: 0.35,
                    color: AxonTheme.neonCyan,
                    barWidth: 3.2,
                    isStrokeCapRound: true,
                    dotData: const FlDotData(show: false),
                    belowBarData: BarAreaData(
                      show: true,
                      gradient: LinearGradient(
                        colors: [
                          AxonTheme.neonCyan.withValues(alpha: 0.35),
                          AxonTheme.electricBlue.withValues(alpha: 0.0),
                        ],
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
