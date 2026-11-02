import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';
import 'glass_container.dart';

class LevelSliderWidget extends StatefulWidget {
  final String title;
  final String pin;
  final double value;
  final double min;
  final double max;
  final String units;
  final bool isReadOnly;
  final ValueChanged<double> onChanged;

  const LevelSliderWidget({
    super.key,
    required this.title,
    required this.pin,
    required this.value,
    this.min = 0,
    this.max = 255,
    this.units = "",
    this.isReadOnly = false,
    required this.onChanged,
  });

  @override
  State<LevelSliderWidget> createState() => _LevelSliderWidgetState();
}

class _LevelSliderWidgetState extends State<LevelSliderWidget> {
  late double _currentVal;

  @override
  void initState() {
    super.initState();
    _currentVal = widget.value.clamp(widget.min, widget.max);
  }

  @override
  void didUpdateWidget(covariant LevelSliderWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) {
      _currentVal = widget.value.clamp(widget.min, widget.max);
    }
  }

  @override
  Widget build(BuildContext context) {
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
                  const SizedBox(width: 12),
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
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(
                  color: AxonTheme.neonCyan.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: AxonTheme.neonCyan.withValues(alpha: 0.4)),
                ),
                child: Text(
                  "${_currentVal.toStringAsFixed(0)} ${widget.units}",
                  style: const TextStyle(
                    color: AxonTheme.neonCyan,
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SliderTheme(
            data: SliderTheme.of(context).copyWith(
              trackHeight: 6,
              thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 10),
              overlayShape: const RoundSliderOverlayShape(overlayRadius: 20),
              thumbColor: AxonTheme.neonCyan,
              activeTrackColor: AxonTheme.electricBlue,
              inactiveTrackColor: Colors.black.withValues(alpha: 0.35),
              overlayColor: AxonTheme.neonCyan.withValues(alpha: 0.2),
            ),
            child: Slider(
              value: _currentVal,
              min: widget.min,
              max: widget.max,
              onChanged: widget.isReadOnly
                  ? null
                  : (val) {
                      setState(() {
                        _currentVal = val;
                      });
                    },
              onChangeEnd: widget.isReadOnly
                  ? null
                  : (val) {
                      widget.onChanged(val);
                    },
            ),
          ),
        ],
      ),
    );
  }
}
