import 'dart:ui';
import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';

class GlassContainer extends StatelessWidget {
  final Widget child;
  final double blur;
  final double opacity;
  final Color? color;
  final Color? borderColor;
  final BorderRadius? borderRadius;
  final EdgeInsetsGeometry? padding;
  final Gradient? gradient;
  final VoidCallback? onTap;
  final bool isInteractive;

  const GlassContainer({
    super.key,
    required this.child,
    this.blur = 16,
    this.opacity = 0.12,
    this.color,
    this.borderColor,
    this.borderRadius,
    this.padding,
    this.gradient,
    this.onTap,
    this.isInteractive = false,
  });

  @override
  Widget build(BuildContext context) {
    final radius = borderRadius ?? BorderRadius.circular(18);

    Widget content = ClipRRect(
      borderRadius: radius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          padding: padding ?? const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: radius,
            color: color ?? Colors.white.withValues(alpha: opacity),
            gradient: gradient ?? AxonTheme.glassGradient,
            border: Border.all(
              color: borderColor ?? Colors.white.withValues(alpha: 0.18),
              width: 1.2,
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.35),
                blurRadius: 18,
                offset: const Offset(0, 8),
              ),
              if (isInteractive)
                BoxShadow(
                  color: AxonTheme.neonCyan.withValues(alpha: 0.08),
                  blurRadius: 16,
                  spreadRadius: 1,
                ),
            ],
          ),
          child: child,
        ),
      ),
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: content,
      );
    }
    return content;
  }
}

class GlassScaffoldBackground extends StatelessWidget {
  final Widget child;

  const GlassScaffoldBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AxonTheme.bgCanvas,
      child: Stack(
        children: [
          // Ambient Neon Cyan Spot 1 (Top-Right)
          Positioned(
            top: -80,
            right: -80,
            child: Container(
              width: 280,
              height: 280,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Color(0x3500E5FF),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          // Ambient Deep Electric Blue Spot 2 (Middle-Left)
          Positioned(
            top: 250,
            left: -100,
            child: Container(
              width: 320,
              height: 320,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Color(0x280375DE),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          // Ambient Indigo Spot 3 (Bottom-Right)
          Positioned(
            bottom: -60,
            right: -40,
            child: Container(
              width: 260,
              height: 260,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    Color(0x207C4DFF),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          // Child widget tree
          SafeArea(child: child),
        ],
      ),
    );
  }
}
