import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'theme/axon_theme.dart';
import 'services/api_client.dart';
import 'services/websocket_service.dart';
import 'screens/auth_screen.dart';
import 'screens/device_list_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Immersive edge-to-edge styling for dark glassmorphism
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: AxonTheme.bgCanvas,
    systemNavigationBarIconBrightness: Brightness.light,
  ));

  final apiClient = AxonApiClient();
  await apiClient.loadSavedSession();
  final wsService = AxonWebSocketService();

  runApp(AxonIoTApp(
    apiClient: apiClient,
    wsService: wsService,
  ));
}

class AxonIoTApp extends StatelessWidget {
  final AxonApiClient apiClient;
  final AxonWebSocketService wsService;

  const AxonIoTApp({
    super.key,
    required this.apiClient,
    required this.wsService,
  });

  @override
  Widget build(BuildContext context) {
    // If auth token is present, go directly to fleet overview; otherwise present login/signup
    final initialHome = apiClient.authToken != null
        ? DeviceListScreen(apiClient: apiClient, wsService: wsService)
        : AuthScreen(apiClient: apiClient, wsService: wsService);

    return MaterialApp(
      title: "Axon IoT",
      // STRICT ZERO-BRANDING: Never display debug ribbon
      debugShowCheckedModeBanner: false,
      theme: AxonTheme.darkTheme,
      home: initialHome,
    );
  }
}
