import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class TelemetryUpdate {
  final int deviceId;
  final String pin;
  final String value;

  TelemetryUpdate({
    required this.deviceId,
    required this.pin,
    required this.value,
  });

  factory TelemetryUpdate.fromJson(Map<String, dynamic> json) {
    return TelemetryUpdate(
      deviceId: json['deviceId'] ?? 0,
      pin: (json['stream'] ?? json['pin'] ?? '').toString().toUpperCase(),
      value: (json['value'] ?? '').toString(),
    );
  }
}

class AxonWebSocketService {
  WebSocketChannel? _channel;
  final StreamController<TelemetryUpdate> _telemetryController = StreamController<TelemetryUpdate>.broadcast();
  final StreamController<Map<String, dynamic>> _rawEventController = StreamController<Map<String, dynamic>>.broadcast();
  
  bool _isConnected = false;
  String _wsUrl = "ws://10.0.2.2:8000/ws";
  Timer? _reconnectTimer;

  Stream<TelemetryUpdate> get onTelemetryUpdated => _telemetryController.stream;
  Stream<Map<String, dynamic>> get onRawEvent => _rawEventController.stream;
  bool get isConnected => _isConnected;

  void connect(String httpBaseUrl) {
    final wsUri = '${httpBaseUrl.replaceFirst('http://', 'ws://').replaceFirst('https://', 'wss://')}/ws';
    _wsUrl = wsUri;
    _initSocket();
  }

  void _initSocket() {
    _reconnectTimer?.cancel();
    try {
      _channel = WebSocketChannel.connect(Uri.parse(_wsUrl));
      _isConnected = true;

      _channel!.stream.listen(
        (message) {
          try {
            final data = json.decode(message);
            if (data is Map<String, dynamic>) {
              _rawEventController.add(data);
              final eventType = data['type'] ?? data['event'];
              if (eventType == 'onValueUpdated' || data.containsKey('stream')) {
                _telemetryController.add(TelemetryUpdate.fromJson(data));
              }
            }
          } catch (_) {}
        },
        onError: (err) {
          _isConnected = false;
          _scheduleReconnect();
        },
        onDone: () {
          _isConnected = false;
          _scheduleReconnect();
        },
      );
    } catch (_) {
      _isConnected = false;
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 4), () {
      _initSocket();
    });
  }

  void dispose() {
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _telemetryController.close();
    _rawEventController.close();
  }
}
