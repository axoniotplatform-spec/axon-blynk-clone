import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';
import 'glass_container.dart';

class IosSwitchWidget extends StatelessWidget {
  final String title;
  final String pin;
  final bool value;
  final bool isReadOnly;
  final ValueChanged<bool> onChanged;

  const IosSwitchWidget({
    super.key,
    required this.title,
    required this.pin,
    required this.value,
    required this.onChanged,
    this.isReadOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    return GlassContainer(
      isInteractive: value,
      borderColor: value ? AxonTheme.neonCyan.withValues(alpha: 0.55) : Colors.white.withValues(alpha: 0.12),
      gradient: value ? AxonTheme.glassActiveGradient : AxonTheme.glassGradient,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: value ? AxonTheme.neonCyan.withValues(alpha: 0.2) : Colors.white.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: value ? AxonTheme.neonCyan : Colors.white.withValues(alpha: 0.15),
                    width: 1,
                  ),
                ),
                child: Text(
                  pin,
                  style: TextStyle(
                    color: value ? AxonTheme.neonCyan : AxonTheme.textSub,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const SizedBox(width: 14),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      color: AxonTheme.textMain,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.3,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: value ? AxonTheme.pulseGreen : AxonTheme.textMuted,
                          boxShadow: value
                              ? [
                                  BoxShadow(
                                    color: AxonTheme.pulseGreen.withValues(alpha: 0.7),
                                    blurRadius: 6,
                                  ),
                                ]
                              : null,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        value ? "ACTIVE RELAY ON" : "RELAY DISENGAGED",
                        style: TextStyle(
                          color: value ? AxonTheme.pulseGreen : AxonTheme.textMuted,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          if (isReadOnly)
            const Tooltip(
              message: "Actuator Interlocked (Read-Only Mode)",
              child: Icon(Icons.shield_outlined, color: AxonTheme.warningAmber, size: 22),
            )
          else
            Switch(
              value: value,
              activeThumbColor: Colors.white,
              activeTrackColor: AxonTheme.electricBlue,
              inactiveTrackColor: Colors.black.withValues(alpha: 0.4),
              inactiveThumbColor: AxonTheme.textMuted,
              onChanged: onChanged,
            ),
        ],
      ),
    );
  }
}
