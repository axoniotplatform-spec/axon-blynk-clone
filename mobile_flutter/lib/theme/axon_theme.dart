import 'package:flutter/material.dart';

class AxonTheme {
  // Deep Cyber Cosmic Palette
  static const Color bgCanvas = Color(0xFF070A12);
  static const Color bgSurface = Color(0xFF0E1524);
  static const Color bgCard = Color(0xFF131D31);

  // Frosted Glass Layer Colors
  static const Color glassWhite = Color(0x18FFFFFF);
  static const Color glassBorder = Color(0x30FFFFFF);
  static const Color glassSurface = Color(0x22131D31);

  // Neon Electric Accents
  static const Color neonCyan = Color(0xFF00E5FF);
  static const Color electricBlue = Color(0xFF0375DE);
  static const Color pulseGreen = Color(0xFF00E676);
  static const Color activeGreen = Color(0xFF00E676);
  static const Color warningAmber = Color(0xFFFF9500);
  static const Color criticalRed = Color(0xFFFF334B);

  // Typography Palette
  static const Color textMain = Color(0xFFF8FAFC);
  static const Color textSub = Color(0xFFCBD5E1);
  static const Color textMuted = Color(0xFF7E8B9F);
  static const Color borderDark = Color(0xFF26354F);

  // Gradients
  static const LinearGradient glassGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0x25FFFFFF),
      Color(0x10FFFFFF),
      Color(0x18000000),
    ],
    stops: [0.0, 0.45, 1.0],
  );

  static const LinearGradient glassActiveGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0x3500E5FF),
      Color(0x150375DE),
      Color(0x20070A12),
    ],
  );

  static const LinearGradient cardBorderGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0x5500E5FF),
      Color(0x20FFFFFF),
      Color(0x100375DE),
    ],
  );

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: bgCanvas,
      primaryColor: electricBlue,
      canvasColor: bgCanvas,
      colorScheme: const ColorScheme.dark(
        primary: electricBlue,
        secondary: neonCyan,
        surface: bgSurface,
        error: criticalRed,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textMain,
          fontSize: 19,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
        iconTheme: IconThemeData(color: textMain),
      ),
    );
  }
}
