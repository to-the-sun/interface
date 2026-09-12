using System;
using System.Net;
using System.Net.Sockets;
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
            Console.WriteLine($"Mouse Cursor Control: {(_moveMouse ? "ENABLED" : "DISABLED")} ({_screenWidth}x{_screenHeight})");
            Console.WriteLine("Requesting Windows Gaze Input Access...");

            try
            {
                var accessStatus = await GazeInputSourcePreview.RequestAccessAsync();
                Console.WriteLine($"Windows Gaze Input Access Status: {accessStatus}");
                if (accessStatus != GazeInputAccessStatus.Allowed)
                {
                    Console.WriteLine("WARNING: Windows Eye Tracker access is not allowed under Windows Privacy Settings.");
                    Console.WriteLine("Go to: Windows Settings -> Privacy & Security -> Eye tracker -> Enable access.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Access Request Exception: {ex.Message}");
            }

            var gazeSource = GazeInputSourcePreview.GetForCurrentView();
            if (gazeSource == null)
            {
                Console.WriteLine("\nERROR: GazeInputSourcePreview.GetForCurrentView() returned null.");
                Console.WriteLine("Ensure PCEye 5 is connected, calibrated in TD Control, and Windows Eye Control is toggled ON.");
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

            var eyePos = currentPoint.EyeGazePositionInPixels;
            if (eyePos == null) return;

            double px = eyePos.Value.X;
            double py = eyePos.Value.Y;

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
