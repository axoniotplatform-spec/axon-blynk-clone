import 'package:flutter_test/flutter_test.dart';
import 'package:axon_mobile/main.dart';
import 'package:axon_mobile/services/api_client.dart';
import 'package:axon_mobile/services/websocket_service.dart';

void main() {
  testWidgets('Axon App bootstrap smoke test', (WidgetTester tester) async {
    final client = AxonApiClient();
    final ws = AxonWebSocketService();
    await tester.pumpWidget(AxonIoTApp(apiClient: client, wsService: ws));
    expect(find.text('AXON IOT'), findsOneWidget);
  });
}
