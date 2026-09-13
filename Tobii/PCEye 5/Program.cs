using System;
using System.Drawing;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
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
        private static bool _firstGazeMovedLogged = false;
        private static bool _firstEyeGazePosLogged = false;

        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

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

            // Create a WinForms UI Window to establish an active WinRT UI View Context for GetForCurrentView()
            var form = new Form
            {
                Text = "Tobii PCEye 5 - Continuous Windows Gaze Streamer",
                Width = 580,
                Height = 380,
                StartPosition = FormStartPosition.CenterScreen
            };

            var textBox = new TextBox
            {
                Multiline = true,
                ReadOnly = true,
                Dock = DockStyle.Fill,
                ScrollBars = ScrollBars.Vertical,
                Font = new Font("Consolas", 9.5f),
                BackColor = Color.Black,
                ForeColor = Color.LightGreen
            };
            form.Controls.Add(textBox);

            void Log(string msg)
            {
                if (form.IsHandleCreated)
                {
                    form.BeginInvoke((Action)(() =>
                    {
                        textBox.AppendText($"[{DateTime.Now:HH:mm:ss}] {msg}{Environment.NewLine}");
                    }));
                }
            };

            Log("========================================================================");
            Log(" Tobii PCEye 5 - Continuous Gaze Streamer & Mouse Control");
            Log(" Uses Windows.Devices.Input.Preview & Continuous SetCursorPos");
            Log("========================================================================\n");
            Log($"OSC Endpoint: {_oscIp}:{_oscPort}");
            Log($"Mouse Cursor Control: {(_moveMouse ? "ENABLED" : "DISABLED")} ({_screenWidth}x{_screenHeight})\n");

            form.Shown += async (s, e) =>
            {
                Log("Scanning Windows Gaze Devices via GazeInputSourcePreview.CreateWatcher()...");
                bool deviceAddedEmitted = false;
                try
                {
                    var watcher = GazeInputSourcePreview.CreateWatcher();
                    if (watcher != null)
                    {
                        watcher.Added += (w, devArgs) =>
                        {
                            deviceAddedEmitted = true;
                            Log(" [CHECK 1] GazeInputSourcePreview.CreateWatcher() emitted Added event.");
                            var device = devArgs.Device;
                            if (device != null)
                            {
                                try
                                {
                                    Log($"   -> [CHECK 2] Tracker CanTrackEyes: {device.CanTrackEyes}");
                                    Log($"   -> [CHECK 3] Tracker ConfigurationState: {device.ConfigurationState}");
                                    Log($"   -> Tracker Id: {device.Id}");
                                }
                                catch (Exception ex)
                                {
                                    Log($"   -> Notice reading GazeDevicePreview properties: {ex.Message}");
                                }
                            }
                            else
                            {
                                Log($"   -> GazeDevicePreview object in Added event is null.");
                            }
                        };
                        watcher.EnumerationCompleted += (w, obj) =>
                        {
                            Log(" [Gaze Device Scan Completed]");
                        };
                        watcher.Start();
                        await Task.Delay(1500);
                        watcher.Stop();
                    }
                }
                catch (Exception ex)
                {
                    Log($" Gaze Device Watcher Notice: {ex.Message}");
                }

                if (!deviceAddedEmitted)
                {
                    Log(" [CHECK 1 NOTICE] GazeInputSourcePreview.CreateWatcher() did not emit an Added event during scan.");
                }

                Log("\nObtaining GazeInputSourcePreview instance in UI View Context...");
                GazeInputSourcePreview? gazeSource = null;

                try
                {
                    gazeSource = GazeInputSourcePreview.GetForCurrentView();
                }
                catch (COMException comEx) when (comEx.HResult == unchecked((int)0x80070490)) // 0x80070490: Element not found
                {
                    Log("\n========================================================================");
                    Log(" ERROR: Windows GazeInputSourcePreview returned 'Element Not Found' (0x80070490).");
                    Log(" [CHECK 4] GazeInputSourcePreview.GetForCurrentView(): FAILED (0x80070490)");
                    Log("========================================================================");
                    Log(" Why this occurs:");
                    Log(" 1. Application lacks package identity / gazeInput capability registration.");
                    Log(" 2. Windows Eye Control / PCEye 5 driver does not expose raw gaze to GetForCurrentView().");
                    Log("\n Troubleshooting Guidance:");
                    Log("  A. Run register_gaze_capability.ps1 to register AppxManifest.xml with gazeInput capability.");
                    Log("  B. If TD Control functions but Windows Gaze API throws 0x80070490, PCEye 5 software");
                    Log("     operates exclusively via Tobii's proprietary service, not Microsoft's public Gaze API.");
                    Log("========================================================================\n");
                    return;
                }
                catch (Exception ex)
                {
                    Log($"\n [CHECK 4] GazeInputSourcePreview.GetForCurrentView(): FAILED ({ex.GetType().Name} - {ex.Message})");
                    return;
                }

                if (gazeSource == null)
                {
                    Log("\n [CHECK 4] GazeInputSourcePreview.GetForCurrentView(): returned null.");
                    Log("Ensure PCEye 5 is connected and calibrated in TD Control.");
                    return;
                }

                Log(" [CHECK 4] GazeInputSourcePreview.GetForCurrentView() SUCCEEDED (Manifest capability & consent prompt active).");

                gazeSource.GazeMoved += (sender, args) =>
                {
                    OnGazeMoved(sender, args, Log);
                };

                Log("\nSubscribed to Windows GazeInputSourcePreview GazeMoved events.");
                Log("Monitoring incoming gaze points...\n");

                var statusTimer = new System.Windows.Forms.Timer { Interval = 2000 };
                statusTimer.Tick += (st, se) =>
                {
                    Log($"[STATUS] Frames: {_frameCount} | Mouse Moves: {_mouseMoveCount}");
                };
                statusTimer.Start();
            };

            Application.Run(form);
            _udpClient?.Close();
        }

        private static void OnGazeMoved(GazeInputSourcePreview sender, GazeMovedPreviewEventArgs args, Action<string> log)
        {
            _frameCount++;
            if (!_firstGazeMovedLogged)
            {
                _firstGazeMovedLogged = true;
                log(" [CHECK 5] GazeMoved event FIRED!");
            }

            var currentPoint = args.CurrentPoint;
            if (currentPoint == null) return;

            if (!_firstEyeGazePosLogged)
            {
                _firstEyeGazePosLogged = true;
                bool isEyeGazePosNonNull = CheckEyeGazePositionNonNull(currentPoint, out string gazePosInfo);
                log($" [CHECK 6] args.CurrentPoint.EyeGazePosition non-null: {isEyeGazePosNonNull} ({gazePosInfo})");
            }

            if (TryExtractXY(currentPoint, out double px, out double py, log))
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

        private static bool CheckEyeGazePositionNonNull(object pointObj, out string info)
        {
            info = "null";
            if (pointObj == null) return false;

            Type type = pointObj.GetType();
            string[] candidateNames = new string[] { "EyeGazePosition", "EyeGazePositionInPixels", "Point", "Position", "GazePoint", "Location" };

            foreach (var name in candidateNames)
            {
                var prop = type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance | BindingFlags.IgnoreCase);
                if (prop != null)
                {
                    object? val = prop.GetValue(pointObj);
                    if (val != null)
                    {
                        if (TryGetSubXY(val, out double x, out double y))
                        {
                            info = $"{name} = ({x:F1}, {y:F1})";
                            return true;
                        }
                        info = $"{name} = {val}";
                        return true;
                    }
                }
            }

            return false;
        }

        private static bool TryExtractXY(object pointObj, out double x, out double y, Action<string> log)
        {
            x = 0;
            y = 0;
            if (pointObj == null) return false;

            Type type = pointObj.GetType();

            if (!_loggedProperties)
            {
                _loggedProperties = true;
                log($"[GazePointPreview Type] {type.FullName}");
                foreach (var prop in type.GetProperties())
                {
                    log($"  -> Property: {prop.Name} ({prop.PropertyType.Name})");
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
