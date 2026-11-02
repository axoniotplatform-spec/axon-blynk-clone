import 'package:flutter/material.dart';
import '../theme/axon_theme.dart';

class TerminalCliWidget extends StatefulWidget {
  final Function(String command) onCommandSubmitted;

  const TerminalCliWidget({super.key, required this.onCommandSubmitted});

  @override
  State<TerminalCliWidget> createState() => TerminalCliWidgetState();
}

class TerminalCliWidgetState extends State<TerminalCliWidget> {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<String> _logs = [
    "[SYSTEM] Axon Terminal Engine v2.2 Initialized",
    "[HARDWARE] Connected to Port 8080 Binary Gateway",
    "[READY] Type 'ping', 'set V0 1', or 'help'",
  ];

  void addLog(String message) {
    setState(() {
      _logs.add(message);
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _submit() {
    final cmd = _controller.text.trim();
    if (cmd.isEmpty) return;
    _controller.clear();
    addLog("> $cmd");

    // Local echo/handling
    if (cmd.toLowerCase() == "ping") {
      addLog("[RESP] PONG (Latency: 2ms)");
    } else if (cmd.toLowerCase() == "clear") {
      setState(() {
        _logs.clear();
      });
      return;
    } else if (cmd.toLowerCase().startsWith("set ")) {
      addLog("[CMD] Parameter set applied: $cmd");
    }

    widget.onCommandSubmitted(cmd);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF070B14),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AxonTheme.borderDark, width: 1),
      ),
      child: Column(
        children: [
          // Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: const BoxDecoration(
              color: AxonTheme.bgSurface,
              borderRadius: BorderRadius.vertical(top: Radius.circular(14)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(color: AxonTheme.activeGreen, shape: BoxShape.circle)),
                    const SizedBox(width: 8),
                    const Text(
                      "AXON VIRTUAL TERMINAL (V7)",
                      style: TextStyle(
                        color: AxonTheme.textMain,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
                GestureDetector(
                  onTap: () {
                    setState(() {
                      _logs.clear();
                      _logs.add("[TERMINAL BUFFER CLEARED]");
                    });
                  },
                  child: const Icon(Icons.delete_outline, color: AxonTheme.textMuted, size: 18),
                ),
              ],
            ),
          ),
          // Console Log Output
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(12),
              itemCount: _logs.length,
              itemBuilder: (context, index) {
                final log = _logs[index];
                Color color = const Color(0xFF81C784); // Greenish
                if (log.startsWith(">")) {
                  color = AxonTheme.neonCyan;
                } else if (log.contains("ALERT") || log.contains("ERROR")) {
                  color = AxonTheme.criticalRed;
                }
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(
                    log,
                    style: TextStyle(
                      color: color,
                      fontFamily: "monospace",
                      fontSize: 12,
                      height: 1.3,
                    ),
                  ),
                );
              },
            ),
          ),
          // Input Bar
          Container(
            padding: const EdgeInsets.all(8),
            decoration: const BoxDecoration(
              color: AxonTheme.bgSurface,
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(14)),
            ),
            child: Row(
              children: [
                const Text(
                  ">",
                  style: TextStyle(color: AxonTheme.neonCyan, fontWeight: FontWeight.bold),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: const TextStyle(color: Colors.white, fontFamily: "monospace", fontSize: 13),
                    decoration: const InputDecoration(
                      hintText: "Enter CLI command...",
                      hintStyle: TextStyle(color: AxonTheme.textMuted, fontSize: 13),
                      border: InputBorder.none,
                      isDense: true,
                    ),
                    onSubmitted: (_) => _submit(),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.send_rounded, color: AxonTheme.neonCyan, size: 20),
                  onPressed: _submit,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
