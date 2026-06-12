import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const ResponderApp());
}

class ResponderApp extends StatelessWidget {
  const ResponderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DAITFO Responder',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primaryColor: Colors.deepOrange,
        scaffoldBackgroundColor: const Color(0xFF121212),
        useMaterial3: true,
      ),
      home: const DashboardPage(),
    );
  }
}

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  bool _isRequesting = false;

  void _requestGreenCorridor() async {
    setState(() => _isRequesting = true);
    
    try {
      // In a real local dev env with a physical device, use the machine's local IP (e.g., 10.0.2.2 for Android Emulator)
      final url = Uri.parse('http://localhost:8000/api/emergency/request');
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'device_id': 'AMB_DELHI_092',
          'start': 'INT_005',
          'end': 'INT_001',
        }),
      );

      if (response.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('🚨 GREEN CORRIDOR ACTUATED! Paths Cleared.'))
        );
      } else {
        throw Exception('Server Error: ${response.statusCode}');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connection Failed: Check DAITFO Backend Status'))
      );
    } finally {
      setState(() => _isRequesting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('EMERGENCY OPS'),
        centerTitle: true,
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.emergency, size: 100, color: Colors.redAccent),
            const SizedBox(height: 40),
            ElevatedButton(
              onPressed: _isRequesting ? null : _requestGreenCorridor,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                padding: const EdgeInsets.symmetric(horizontal: 50, vertical: 20),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
              ),
              child: _isRequesting
                  ? const CircularProgressIndicator(color: Colors.white)
                  : const Text('REQUEST GREEN CORRIDOR', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            ),
            const SizedBox(height: 20),
            const Text('ID: AMB_DELHI_092', style: TextStyle(color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}
