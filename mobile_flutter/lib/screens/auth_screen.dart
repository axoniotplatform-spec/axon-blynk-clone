import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';
import '../services/api_client.dart';
import '../services/websocket_service.dart';
import '../widgets/glass_container.dart';
import 'device_list_screen.dart';

class AuthScreen extends StatefulWidget {
  final AxonApiClient apiClient;
  final AxonWebSocketService wsService;

  const AuthScreen({
    super.key,
    required this.apiClient,
    required this.wsService,
  });

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isLogin = true;
  bool _isLoading = false;
  bool _obscurePassword = true;
  String? _errorMessage;

  // Form Controllers
  final _nameController = TextEditingController();
  final _orgController = TextEditingController(text: "Acme Industrial IoT");
  final _emailController = TextEditingController(text: "samblynkk@gmail.com");
  final _passwordController = TextEditingController(text: "change-me");

  @override
  void dispose() {
    _nameController.dispose();
    _orgController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _showServerConfigDialog() async {
    final urlCtrl = TextEditingController(text: widget.apiClient.baseUrl);
    String? pingStatus;
    bool pingSuccess = false;

    await showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setModalState) {
            return Dialog(
              backgroundColor: Colors.transparent,
              child: GlassContainer(
                blur: 22,
                opacity: 0.18,
                borderColor: AxonTheme.neonCyan.withValues(alpha: 0.35),
                padding: const EdgeInsets.all(20),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.dns_rounded, color: AxonTheme.neonCyan, size: 20),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            "AXON GATEWAY ENDPOINT",
                            style: TextStyle(
                              color: AxonTheme.textMain,
                              fontSize: 13,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      "Point this client to your Axon IoT Cloud URL or local LAN IP (e.g. http://192.168.1.50:8000).",
                      style: TextStyle(color: AxonTheme.textSub, fontSize: 12),
                    ),
                    const SizedBox(height: 14),
                    _buildInputField(
                      controller: urlCtrl,
                      label: "SERVER BASE URL",
                      hint: "http://192.168.1.100:8000",
                      icon: Icons.link_rounded,
                      keyboardType: TextInputType.url,
                    ),
                    if (pingStatus != null) ...[
                      const SizedBox(height: 10),
                      Text(
                        pingStatus!,
                        style: TextStyle(
                          color: pingSuccess ? AxonTheme.pulseGreen : AxonTheme.criticalRed,
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            style: OutlinedButton.styleFrom(
                              side: BorderSide(color: AxonTheme.neonCyan.withValues(alpha: 0.5)),
                              foregroundColor: AxonTheme.neonCyan,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            onPressed: () async {
                              final candidate = urlCtrl.text.trim();
                              if (candidate.isEmpty) return;
                              widget.apiClient.setBaseUrl(candidate);
                              final health = await widget.apiClient.checkHealth();
                              setModalState(() {
                                pingSuccess = health['status'] == 'healthy' || health['status'] == 'ok';
                                pingStatus = pingSuccess
                                    ? "Gateway Online (${health['database'] ?? 'Ready'})"
                                    : "Gateway unreachable at $candidate";
                              });
                            },
                            child: const Text("TEST PING", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AxonTheme.neonCyan,
                              foregroundColor: Colors.black,
                              padding: const EdgeInsets.symmetric(vertical: 12),
                            ),
                            onPressed: () async {
                              final candidate = urlCtrl.text.trim();
                              if (candidate.isNotEmpty) {
                                await widget.apiClient.saveBaseUrl(candidate);
                              }
                              if (ctx.mounted) Navigator.pop(ctx);
                              if (mounted) setState(() {});
                            },
                            child: const Text("SAVE URL", style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _handleAuth() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    final email = _emailController.text.trim();
    final password = _passwordController.text;

    if (email.isEmpty || password.isEmpty) {
      setState(() {
        _isLoading = false;
        _errorMessage = "Please enter both email and password.";
      });
      return;
    }

    Map<String, dynamic> result;
    if (_isLogin) {
      result = await widget.apiClient.login(email, password);
    } else {
      final name = _nameController.text.trim();
      if (name.isEmpty) {
        setState(() {
          _isLoading = false;
          _errorMessage = "Please provide your full name.";
        });
        return;
      }
      result = await widget.apiClient.register(
        name: name,
        email: email,
        password: password,
        organizationName: _orgController.text.trim(),
      );
    }

    setState(() => _isLoading = false);

    if (result['success'] == true) {
      if (!mounted) return;
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => DeviceListScreen(
            apiClient: widget.apiClient,
            wsService: widget.wsService,
          ),
        ),
      );
    } else {
      setState(() {
        _errorMessage = result['error'] ?? "Authentication failed.";
      });
    }
  }

  void _bypassAsGuest() {
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(
        builder: (_) => DeviceListScreen(
          apiClient: widget.apiClient,
          wsService: widget.wsService,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: GlassScaffoldBackground(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Glowing Cyber Axon Logo Badge
                Container(
                  width: 68,
                  height: 68,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [AxonTheme.neonCyan, AxonTheme.electricBlue],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AxonTheme.neonCyan.withValues(alpha: 0.5),
                        blurRadius: 24,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.bolt, color: Colors.black, size: 38),
                ),
                const SizedBox(height: 16),
                const Text(
                  "AXON IOT",
                  style: TextStyle(
                    color: AxonTheme.textMain,
                    fontSize: 24,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 2.0,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _isLogin ? "INDUSTRIAL CLOUD ACCESS" : "CREATE ENTERPRISE TENANT",
                  style: const TextStyle(
                    color: AxonTheme.neonCyan,
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.0,
                  ),
                ),
                const SizedBox(height: 12),

                // Configurable Gateway Endpoint Chip
                GestureDetector(
                  onTap: _showServerConfigDialog,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.35),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.dns_rounded, color: AxonTheme.neonCyan, size: 13),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text(
                            widget.apiClient.baseUrl,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: AxonTheme.textSub,
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        const Icon(Icons.tune_rounded, color: AxonTheme.textMuted, size: 13),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 18),

                // Main Frosted Glass Card
                GlassContainer(
                  blur: 20,
                  opacity: 0.14,
                  borderColor: Colors.white.withValues(alpha: 0.2),
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Animated Tab Switcher
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: 0.35),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                        ),
                        child: Row(
                          children: [
                            Expanded(
                              child: GestureDetector(
                                onTap: () => setState(() => _isLogin = true),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  decoration: BoxDecoration(
                                    color: _isLogin ? AxonTheme.neonCyan.withValues(alpha: 0.2) : Colors.transparent,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color: _isLogin ? AxonTheme.neonCyan.withValues(alpha: 0.5) : Colors.transparent,
                                    ),
                                  ),
                                  child: Text(
                                    "SIGN IN",
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: _isLogin ? AxonTheme.neonCyan : AxonTheme.textMuted,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            Expanded(
                              child: GestureDetector(
                                onTap: () => setState(() => _isLogin = false),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(vertical: 10),
                                  decoration: BoxDecoration(
                                    color: !_isLogin ? AxonTheme.neonCyan.withValues(alpha: 0.2) : Colors.transparent,
                                    borderRadius: BorderRadius.circular(10),
                                    border: Border.all(
                                      color: !_isLogin ? AxonTheme.neonCyan.withValues(alpha: 0.5) : Colors.transparent,
                                    ),
                                  ),
                                  child: Text(
                                    "CREATE ACCOUNT",
                                    textAlign: TextAlign.center,
                                    style: TextStyle(
                                      color: !_isLogin ? AxonTheme.neonCyan : AxonTheme.textMuted,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Error Banner
                      if (_errorMessage != null) ...[
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          decoration: BoxDecoration(
                            color: AxonTheme.criticalRed.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(color: AxonTheme.criticalRed.withValues(alpha: 0.5)),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.error_outline, color: AxonTheme.criticalRed, size: 18),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _errorMessage!,
                                  style: const TextStyle(color: AxonTheme.criticalRed, fontSize: 12, fontWeight: FontWeight.w600),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // Full Name (Only on Registration)
                      if (!_isLogin) ...[
                        _buildInputField(
                          controller: _nameController,
                          label: "FULL NAME",
                          hint: "Alex Embedded",
                          icon: Icons.person_outline,
                        ),
                        const SizedBox(height: 14),
                        _buildInputField(
                          controller: _orgController,
                          label: "ORGANIZATION / TENANT",
                          hint: "Company or Project Name",
                          icon: Icons.business_outlined,
                        ),
                        const SizedBox(height: 14),
                      ],

                      // Email Field
                      _buildInputField(
                        controller: _emailController,
                        label: "WORK EMAIL",
                        hint: "operator@axon-iot.internal",
                        icon: Icons.alternate_email_rounded,
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 14),

                      // Password Field
                      _buildInputField(
                        controller: _passwordController,
                        label: "PASSWORD",
                        hint: "••••••••",
                        icon: Icons.lock_outline_rounded,
                        obscureText: _obscurePassword,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                            color: AxonTheme.textMuted,
                            size: 18,
                          ),
                          onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                        ),
                      ),
                      const SizedBox(height: 22),

                      // Submit Action Button
                      GestureDetector(
                        onTap: _isLoading ? null : _handleAuth,
                        child: Container(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [AxonTheme.electricBlue, AxonTheme.neonCyan],
                            ),
                            borderRadius: BorderRadius.circular(12),
                            boxShadow: [
                              BoxShadow(
                                color: AxonTheme.neonCyan.withValues(alpha: 0.35),
                                blurRadius: 16,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Center(
                            child: _isLoading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(color: Colors.black, strokeWidth: 2.5),
                                  )
                                : Text(
                                    _isLogin ? "SIGN IN TO PLATFORM" : "CREATE ENTERPRISE TENANT",
                                    style: const TextStyle(
                                      color: Colors.black,
                                      fontSize: 13,
                                      fontWeight: FontWeight.w900,
                                      letterSpacing: 1.0,
                                    ),
                                  ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 14),

                      // Helper Action Links
                      if (_isLogin)
                        Center(
                          child: TextButton(
                            onPressed: () {
                              _emailController.text = "samblynkk@gmail.com";
                              _passwordController.text = "change-me";
                            },
                            child: const Text(
                              "Fill Seed Admin Credentials (Demo)",
                              style: TextStyle(color: AxonTheme.neonCyan, fontSize: 12, fontWeight: FontWeight.w700),
                            ),
                          ),
                        ),

                      Center(
                        child: TextButton(
                          onPressed: _bypassAsGuest,
                          child: const Text(
                            "Skip Login • Continue in Offline Gateway Mode",
                            style: TextStyle(color: AxonTheme.textMuted, fontSize: 12),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInputField({
    required TextEditingController controller,
    required String label,
    required String hint,
    required IconData icon,
    bool obscureText = false,
    Widget? suffixIcon,
    TextInputType? keyboardType,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: AxonTheme.textSub,
            fontSize: 10,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.8,
          ),
        ),
        const SizedBox(height: 6),
        Container(
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
          ),
          child: TextField(
            controller: controller,
            obscureText: obscureText,
            keyboardType: keyboardType,
            style: const TextStyle(color: AxonTheme.textMain, fontSize: 14, fontWeight: FontWeight.w600),
            decoration: InputDecoration(
              prefixIcon: Icon(icon, color: AxonTheme.textMuted, size: 18),
              suffixIcon: suffixIcon,
              hintText: hint,
              hintStyle: TextStyle(color: AxonTheme.textMuted.withValues(alpha: 0.6), fontSize: 13),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            ),
          ),
        ),
      ],
    );
  }
}
