import 'dart:math';
import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';
import 'glass_container.dart';

class RadialGaugeWidget extends StatelessWidget {
  final String title;
  final String pin;
  final double value;
  final double min;
  final double max;
  final String units;

  const RadialGaugeWidget({
    super.key,
    required this.title,
    required this.pin,
    required this.value,
    this.min = 0,
    this.max = 100,
    this.units = "",
  });

  @override
  Widget build(BuildContext context) {
    final clampedVal = value.clamp(min, max);
    final ratio = (clampedVal - min) / (max - min == 0 ? 1 : max - min);

    return GlassContainer(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title,
                style: const TextStyle(
                  color: AxonTheme.textMain,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
                ),
                child: Text(
                  pin,
                  style: const TextStyle(
                    color: AxonTheme.neonCyan,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),
          SizedBox(
            width: 150,
            height: 150,
            child: CustomPaint(
              painter: _GlassGaugePainter(ratio: ratio),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      value.toStringAsFixed(1),
                      style: const TextStyle(
                        color: AxonTheme.textMain,
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                        shadows: [
                          Shadow(
                            color: Color(0x6600E5FF),
                            blurRadius: 12,
                          ),
                        ],
                      ),
                    ),
                    if (units.isNotEmpty)
                      Text(
                        units,
                        style: const TextStyle(
                          color: AxonTheme.textSub,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(min.toStringAsFixed(0), style: const TextStyle(color: AxonTheme.textMuted, fontSize: 11, fontWeight: FontWeight.bold)),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.3),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  "${(ratio * 100).toStringAsFixed(0)}%",
                  style: const TextStyle(color: AxonTheme.neonCyan, fontSize: 10, fontWeight: FontWeight.bold),
                ),
              ),
              Text(max.toStringAsFixed(0), style: const TextStyle(color: AxonTheme.textMuted, fontSize: 11, fontWeight: FontWeight.bold)),
            ],
          ),
        ],
      ),
    );
  }
}

class _GlassGaugePainter extends CustomPainter {
  final double ratio;

  _GlassGaugePainter({required this.ratio});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 12;
    const startAngle = 135 * (pi / 180);
    const sweepAngle = 270 * (pi / 180);

    // Outer Glass Track
    final trackPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.08)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      trackPaint,
    );

    // Glowing Active Arc
    Color arcColor = AxonTheme.neonCyan;
    if (ratio > 0.85) {
      arcColor = AxonTheme.criticalRed;
    } else if (ratio > 0.65) {
      arcColor = AxonTheme.warningAmber;
    } else if (ratio > 0.35) {
      arcColor = AxonTheme.electricBlue;
    }

    final activePaint = Paint()
      ..color = arcColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle * ratio,
      false,
      activePaint,
    );
  }

  @override
  bool shouldRepaint(covariant _GlassGaugePainter oldDelegate) {
    return oldDelegate.ratio != ratio;
  }
}
