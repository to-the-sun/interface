using System;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using Windows.Devices.Input.Preview;

namespace PCEyeWinGaze
{
    class Program
    {
        [DllImport("user32.dll")]
        public static extern bool SetCursorPos(int X, int Y);

        [DllImport("user32.dll")]
        public static extern bool SetProcessDPIAware();

        [DllImport("user32.dll")]
        public static extern int GetSystemMetrics(int nIndex);

        private static UdpClient? _udpClient;
        private static string _oscIp = "127.0.0.1";
        private static int _oscPort = 6731;
        private static bool _moveMouse = true;
        private static int _screenWidth = 1920;
        private static int _screenHeight = 1080;

        private static long _frameCount = 0;
        private static long _mouseMoveCount = 0;
        private static bool _loggedProperties = false;

        static async Task Main(string[] args)
        {
            Console.WriteLine("========================================================================");
            Console.WriteLine(" Tobii PCEye 5 - C# Windows Gaze Input API Streamer & Mouse Control");
            Console.WriteLine(" Uses Windows.Devices.Input.Preview & SetCursorPos");
            Console.WriteLine("========================================================================\n");

            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--ip" && i + 1 < args.Length) _oscIp = args[i + 1];
                if (args[i] == "--port" && i + 1 < args.Length && int.TryParse(args[i + 1], out int p)) _oscPort = p;
                if (args[i] == "--no-mouse") _moveMouse = false;
            }

            try
            {
                SetProcessDPIAware();
                int sw = GetSystemMetrics(0);
                int sh = GetSystemMetrics(1);
                if (sw > 0 && sh > 0)
                {
                    _screenWidth = sw;
                    _screenHeight = sh;
                }
            }
            catch { }

            _udpClient = new UdpClient();
            _udpClient.Connect(_oscIp, _oscPort);

            Console.WriteLine($"OSC Endpoint: {_oscIp}:{_oscPort}");
            Console.WriteLine($"Mouse Cursor Control: {(_moveMouse ? "ENABLED" : "DISABLED")} ({_screenWidth}x{_screenHeight})\n");

            // 1. Inspect registered Windows Gaze Devices using GazeDeviceWatcherPreview
            Console.WriteLine("Scanning Windows Gaze Devices via GazeDeviceWatcherPreview...");
            try
            {
                var watcher = GazeDeviceWatcherPreview.CreateWatcher();
                watcher.Added += (w, dev) =>
                {
                    Console.WriteLine($" [Gaze Device Found] Id: {dev.Id} | Model: {dev.Model} | Firmware: {dev.FirmwareVersion}");
                };
                watcher.EnumerationCompleted += (w, obj) =>
                {
                    Console.WriteLine(" [Gaze Device Scan Completed]");
                };
                watcher.Start();
                await Task.Delay(1000);
                watcher.Stop();
            }
            catch (Exception ex)
            {
                Console.WriteLine($" Gaze Device Watcher Error: {ex.Message}");
            }

            Console.WriteLine("\nObtaining GazeInputSourcePreview instance...");
            GazeInputSourcePreview? gazeSource = null;

            try
            {
                gazeSource = GazeInputSourcePreview.GetForCurrentView();
            }
            catch (COMException comEx) when (comEx.HResult == unchecked((int)0x80070490)) // 0x80070490: Element not found
            {
                Console.WriteLine("\n========================================================================");
                Console.WriteLine(" ERROR: Windows GazeInputSourcePreview returned 'Element Not Found' (0x80070490).");
                Console.WriteLine("========================================================================");
                Console.WriteLine(" Why this occurs:");
                Console.WriteLine(" 1. GetForCurrentView() requires a UWP/XAML UI Window or active Windows Eye Control.");
                Console.WriteLine(" 2. Windows Eye Control is currently OFF or PCEye 5 driver is not registered with Windows.");
                Console.WriteLine("\n Quick Fix Instructions:");
                Console.WriteLine("  A. Open Windows Settings -> Ease of Access -> Eye control.");
                Console.WriteLine("  B. Toggle 'Eye control' to ON.");
                Console.WriteLine("  C. Ensure the red gaze cursor appears on screen, then run this app again.");
                Console.WriteLine("========================================================================\n");
                Console.WriteLine("Press Enter to exit...");
                Console.ReadLine();
                return;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"\nFailed to obtain GazeInputSourcePreview: {ex.GetType().Name} - {ex.Message}");
                Console.WriteLine("Ensure PCEye 5 is connected and Windows Eye Control is toggled ON in Settings.");
                Console.ReadLine();
                return;
            }

            if (gazeSource == null)
            {
                Console.WriteLine("\nERROR: GazeInputSourcePreview.GetForCurrentView() returned null.");
                Console.WriteLine("Ensure PCEye 5 is connected, calibrated in TD Control, and Windows Eye Control is toggled ON in Settings.");
                Console.WriteLine("Press Enter to exit...");
                Console.ReadLine();
                return;
            }

            gazeSource.GazeMoved += OnGazeMoved;
            Console.WriteLine("\nSubscribed to Windows GazeInputSourcePreview GazeMoved events.");
            Console.WriteLine("Monitoring incoming gaze points... Press Ctrl+C to exit.\n");

            var timer = new System.Threading.Timer((_) =>
            {
                Console.WriteLine($"[STATUS] Frames: {_frameCount} | Mouse Moves: {_mouseMoveCount}");
            }, null, 2000, 2000);

            var tcs = new TaskCompletionSource<bool>();
            Console.CancelKeyPress += (s, e) =>
            {
                e.Cancel = true;
                tcs.SetResult(true);
            };
            await tcs.Task;

            gazeSource.GazeMoved -= OnGazeMoved;
            _udpClient?.Close();
            timer.Dispose();
            Console.WriteLine("Unsubscribed and stopped successfully.");
        }

        private static void OnGazeMoved(GazeInputSourcePreview sender, GazeMovedPreviewEventArgs args)
        {
            _frameCount++;
            var currentPoint = args.CurrentPoint;
            if (currentPoint == null) return;

            if (TryExtractXY(currentPoint, out double px, out double py))
            {
                double avgX = Math.Max(0.0, Math.Min(1.0, px / _screenWidth));
                double avgY = Math.Max(0.0, Math.Min(1.0, py / _screenHeight));

                SendOscMessage("/Tobii/gaze_x", (float)avgX);
                SendOscMessage("/Tobii/gaze_y", (float)avgY);
                SendOscMessage("/OpenFace/gaze_left_right", (float)((avgX - 0.5) * 60.0));
                SendOscMessage("/OpenFace/gaze_up_down", (float)((avgY - 0.5) * -60.0));

                if (_moveMouse)
                {
                    if (SetCursorPos((int)px, (int)py))
                    {
                        _mouseMoveCount++;
                    }
                }
            }
        }

        private static bool TryExtractXY(object pointObj, out double x, out double y)
        {
            x = 0;
            y = 0;
            if (pointObj == null) return false;

            Type type = pointObj.GetType();

            if (!_loggedProperties)
            {
                _loggedProperties = true;
                Console.WriteLine($"[GazePointPreview Type] {type.FullName}");
                foreach (var prop in type.GetProperties())
                {
                    Console.WriteLine($"  -> Property: {prop.Name} ({prop.PropertyType.Name})");
                }
            }

            string[] candidateNames = new string[] { "EyeGazePositionInPixels", "Point", "Position", "GazePoint", "Location" };
            foreach (var name in candidateNames)
            {
                var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                if (prop != null)
                {
                    object? val = prop.GetValue(pointObj);
                    if (val != null && TryGetSubXY(val, out x, out y))
                    {
                        return true;
                    }
                }
            }

            if (TryGetSubXY(pointObj, out x, out y))
            {
                return true;
            }

            return false;
        }

        private static bool TryGetSubXY(object obj, out double x, out double y)
        {
            x = 0;
            y = 0;
            if (obj == null) return false;

            Type t = obj.GetType();
            if (t.IsGenericType && t.GetGenericTypeDefinition() == typeof(Nullable<>))
            {
                var hasValueProp = t.GetProperty("HasValue");
                if (hasValueProp != null && (bool)hasValueProp.GetValue(obj)! == false)
                    return false;
                var valueProp = t.GetProperty("Value");
                if (valueProp != null)
                {
                    obj = valueProp.GetValue(obj)!;
                    if (obj == null) return false;
                    t = obj.GetType();
                }
            }

            var xProp = t.GetProperty("X", BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
            var yProp = t.GetProperty("Y", BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);

            if (xProp != null && yProp != null)
            {
                object? xVal = xProp.GetValue(obj);
                object? yVal = yProp.GetValue(obj);
                if (xVal != null && yVal != null)
                {
                    x = Convert.ToDouble(xVal);
                    y = Convert.ToDouble(yVal);
                    return true;
                }
            }

            return false;
        }

        private static void SendOscMessage(string address, float value)
        {
            if (_udpClient == null) return;
            try
            {
                byte[] addrBytes = Encoding.UTF8.GetBytes(address);
                int addrPad = 4 - (addrBytes.Length % 4);
                byte[] typeBytes = Encoding.UTF8.GetBytes(",f");
                int typePad = 4 - (typeBytes.Length % 4);

                byte[] valBytes = BitConverter.GetBytes(value);
                if (BitConverter.IsLittleEndian)
                    Array.Reverse(valBytes);

                int totalLen = addrBytes.Length + addrPad + typeBytes.Length + typePad + 4;
                byte[] packet = new byte[totalLen];

                int offset = 0;
                Array.Copy(addrBytes, 0, packet, offset, addrBytes.Length);
                offset += addrBytes.Length + addrPad;

                Array.Copy(typeBytes, 0, packet, offset, typeBytes.Length);
                offset += typeBytes.Length + typePad;

                Array.Copy(valBytes, 0, packet, offset, 4);

                _udpClient.Send(packet, packet.Length);
            }
            catch { }
        }
    }
}
