import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class AxonApiClient {
  String baseUrl;
  String? authToken;
  Map<String, dynamic>? currentUser;

  AxonApiClient({String? baseUrl}) 
      : baseUrl = baseUrl ?? _resolveDefaultBaseUrl();

  static String _resolveDefaultBaseUrl() {
    if (kIsWeb) {
      final serverParam = Uri.base.queryParameters['server'];
      if (serverParam != null && serverParam.trim().isNotEmpty) {
        return serverParam.trim().replaceAll(RegExp(r'/+$'), '');
      }
      final origin = Uri.base.origin;
      if (origin.isNotEmpty && !origin.contains("null") && origin != "file://") {
        return origin;
      }
      return "http://127.0.0.1:8000";
    }
    return "http://10.0.2.2:8000";
  }

  void setBaseUrl(String url) {
    baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
  }

  Future<void> saveBaseUrl(String url) async {
    setBaseUrl(url);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('axon_server_url', baseUrl);
    } catch (_) {}
  }

  Map<String, String> _headers() {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (authToken != null && authToken!.isNotEmpty) {
      h['Authorization'] = 'Bearer $authToken';
    }
    if (currentUser != null && currentUser!['role'] != null) {
      h['X-Axon-Role'] = currentUser!['role'].toString();
    }
    return h;
  }

  Future<void> loadSavedSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedUrl = prefs.getString('axon_server_url');
      if (savedUrl != null && savedUrl.trim().isNotEmpty) {
        setBaseUrl(savedUrl);
      }
      authToken = prefs.getString('axon_auth_token');
      final userJson = prefs.getString('axon_user_data');
      if (userJson != null) {
        currentUser = json.decode(userJson);
      }
    } catch (_) {}
  }

  Future<void> saveSession(String token, Map<String, dynamic> user) async {
    authToken = token;
    currentUser = user;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('axon_auth_token', token);
      await prefs.setString('axon_user_data', json.encode(user));
    } catch (_) {}
  }

  Future<void> clearSession() async {
    authToken = null;
    currentUser = null;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('axon_auth_token');
      await prefs.remove('axon_user_data');
    } catch (_) {}
  }

  // --- Auth Endpoints ---

  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/auth/login');
      final res = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'email': email.trim(), 'password': password}),
      ).timeout(const Duration(seconds: 6));

      final data = json.decode(res.body);
      if (res.statusCode == 200 && data['token'] != null) {
        await saveSession(data['token'], data['user'] ?? {});
        return {'success': true, 'data': data};
      }
      return {'success': false, 'error': data['detail'] ?? 'Login failed. Please check credentials.'};
    } catch (e) {
      return {'success': false, 'error': 'Cannot connect to Axon Server: $e'};
    }
  }

  Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    String? organizationName,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/api/v1/auth/register');
      final res = await http.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': name.trim(),
          'email': email.trim().toLowerCase(),
          'password': password,
          'organization_name': organizationName?.trim() ?? 'Default Organization',
          'role': 'Admin',
        }),
      ).timeout(const Duration(seconds: 6));

      final data = json.decode(res.body);
      if (res.statusCode == 200 && data['token'] != null) {
        await saveSession(data['token'], data['user'] ?? {});
        return {'success': true, 'data': data};
      }
      return {'success': false, 'error': data['detail'] ?? 'Registration failed.'};
    } catch (e) {
      return {'success': false, 'error': 'Connection error: $e'};
    }
  }

  // --- Fleet & Device Endpoints ---

  Future<Map<String, dynamic>> checkHealth() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/health')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return {'status': 'disconnected'};
  }

  Future<List<dynamic>> fetchDevices() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/devices'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return [];
  }

  Future<Map<String, dynamic>?> fetchDeviceDetail(int deviceId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/devices/$deviceId'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<bool> updatePinValue(String token, String pin, String value) async {
    try {
      final pinParam = pin.toUpperCase().startsWith('V') ? pin.toUpperCase() : 'V$pin';
      final uri = Uri.parse('$baseUrl/external/api/update?token=$token&$pinParam=$value');
      final res = await http.get(uri).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<dynamic>> fetchAnomalies({int? deviceId, bool unresolvedOnly = true}) async {
    try {
      String query = unresolvedOnly ? '?unresolved_only=true' : '';
      if (deviceId != null) {
        query += unresolvedOnly ? '&device_id=$deviceId' : '?device_id=$deviceId';
      }
      final res = await http.get(Uri.parse('$baseUrl/api/v1/anomalies$query'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return [];
  }

  Future<bool> resolveAnomaly(int alertId) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/v1/anomalies/$alertId/resolve'), headers: _headers()).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // --- Step 1: Mobile Developer Mode & Widgets ---

  Future<Map<String, dynamic>?> createDevice(String name, {String mcu = "ESP32", String connectionType = "WI_FI"}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/devices'),
        headers: _headers(),
        body: json.encode({'name': name, 'hardware_mcu': mcu, 'connection_type': connectionType}),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200 || res.statusCode == 201) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<bool> deleteDevice(int deviceId) async {
    try {
      final res = await http.delete(Uri.parse('$baseUrl/api/v1/devices/$deviceId'), headers: _headers()).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<dynamic>> fetchDeviceWidgets(int deviceId) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/devices/$deviceId/widgets'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return [];
  }

  Future<Map<String, dynamic>?> createWidget(int deviceId, {
    required String widgetType,
    required String label,
    required String pin,
    double min = 0.0,
    double max = 100.0,
    String units = "",
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/devices/$deviceId/widgets'),
        headers: _headers(),
        body: json.encode({
          'widget_type': widgetType,
          'label': label,
          'pin': pin,
          'min_value': min,
          'max_value': max,
          'units': units,
        }),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200 || res.statusCode == 201) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return null;
  }

  // --- Step 3: Fleet Telemetry Simulator ---

  Future<Map<String, dynamic>> fetchSimulatorStatus() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/simulator/status')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return {'running': false, 'frames_sent': 0};
  }

  Future<bool> toggleSimulator(bool start) async {
    try {
      final endpoint = start ? '$baseUrl/api/v1/simulator/start' : '$baseUrl/api/v1/simulator/stop';
      final res = await http.post(Uri.parse(endpoint), headers: _headers(), body: json.encode({'interval_sec': 2.0})).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // --- Step 4: Enterprise Team & Reports ---

  Future<List<dynamic>> fetchTeamMembers() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/team/members'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return [];
  }

  Future<Map<String, dynamic>?> inviteTeamMember({required String email, required String name, required String role}) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/v1/team/invite'),
        headers: _headers(),
        body: json.encode({'email': email, 'name': name, 'role': role}),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200 || res.statusCode == 201) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return null;
  }

  Future<Map<String, dynamic>> fetchExecutiveDigest() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/api/v1/reports/digest'), headers: _headers()).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (_) {}
    return {};
  }
}
