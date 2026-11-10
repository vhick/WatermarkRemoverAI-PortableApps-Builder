// Community PortableApps launcher for the official D-Ogi Windows portable release.
// This file is intentionally readable and uses only Windows/.NET Framework APIs.
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("WatermarkRemover-AI Portable (Community)")]
[assembly: AssemblyProduct("WatermarkRemover-AI Portable (Community)")]
[assembly: AssemblyCompany("Community package; upstream application by D-Ogi")]
[assembly: AssemblyVersion("1.0.0.0")]

internal static class WatermarkRemoverAIPortable
{
    private static string Fingerprint(string text)
    {
        using (SHA256 sha = SHA256.Create())
        {
            byte[] bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(text.ToUpperInvariant()));
            return BitConverter.ToString(bytes, 0, 12).Replace("-", "");
        }
    }

    private static void EnsureDirectory(string directory)
    {
        Directory.CreateDirectory(directory);
        if (!Directory.Exists(directory)) throw new IOException("Cannot create " + directory);
    }

    [STAThread]
    private static int Main(string[] args)
    {
        bool silent = args.Length == 1 && args[0] == "--check";
        try
        {
            string root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory);
            string app = Path.Combine(root, @"App\WatermarkRemoverAI\WatermarkRemover-AI.exe");
            string data = Path.Combine(root, "Data");
            if (!File.Exists(app)) throw new FileNotFoundException("Application is missing. Extract the complete PortableApps ZIP.", app);
            string[] folders = { data, Path.Combine(data, "models"), Path.Combine(data, @"models\torch"),
                                 Path.Combine(data, @"models\huggingface") };
            foreach (string dir in folders) EnsureDirectory(dir);
            // Only one launcher instance for this portable folder; installed copies remain independent.
            string mutexName = @"Local\DogiWatermarkRemoverAI-Portable-" + Fingerprint(root);
            bool created;
            using (Mutex unique = new Mutex(true, mutexName, out created))
            {
                if (!created) throw new InvalidOperationException("This portable copy is already running.");
                try
                {
                    ProcessStartInfo start = new ProcessStartInfo(app);
                    start.WorkingDirectory = Path.GetDirectoryName(app);
                    start.UseShellExecute = false;
                    start.CreateNoWindow = true;
                    start.Arguments = QuoteArguments(args);
                    start.EnvironmentVariables.Remove("PYTHONHOME");
                    start.EnvironmentVariables.Remove("PYTHONPATH");
                    start.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
                    start.EnvironmentVariables["PYTHONUTF8"] = "1";
                    start.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
                    // Explicit overrides intentionally prevent inherited system cache paths
                    // from redirecting model data into a different (installed) application.
                    start.EnvironmentVariables["WMR_DATA_DIR"] = data;
                    start.EnvironmentVariables["TORCH_HOME"] = Path.Combine(data, @"models\torch");
                    start.EnvironmentVariables["HF_HOME"] = Path.Combine(data, @"models\huggingface");
                    start.EnvironmentVariables["HF_HUB_CACHE"] = Path.Combine(data, @"models\huggingface\hub");
                    start.EnvironmentVariables["HUGGINGFACE_HUB_CACHE"] = start.EnvironmentVariables["HF_HUB_CACHE"];
                    start.EnvironmentVariables["XDG_CACHE_HOME"] = Path.Combine(data, "xdg-cache");
                    // Avoid speculative changes to APPDATA/LOCALAPPDATA/TEMP or OS registry.
                    using (Process child = Process.Start(start))
                    {
                        if (child == null) throw new IOException("Could not start upstream executable.");
                        child.WaitForExit(); // Upstream EXE waits for Python GUI and owned workers.
                        return child.ExitCode;
                    }
                }
                finally { unique.ReleaseMutex(); }
            }
        }
        catch (Exception ex)
        {
            if (silent) Console.Error.WriteLine(ex.ToString());
            else MessageBox.Show(ex.Message, "WatermarkRemover-AI Portable", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    // Upstream currently accepts only --check; forward arguments faithfully for future releases.
    private static string QuoteArguments(string[] args)
    {
        StringBuilder builder = new StringBuilder();
        foreach (string arg in args)
        {
            if (builder.Length > 0) builder.Append(' ');
            builder.Append('"');
            int slashes = 0;
            foreach (char c in arg)
            {
                if (c == '\\') { slashes++; continue; }
                if (c == '"')
                {
                    builder.Append('\\', slashes * 2 + 1);
                    builder.Append('"');
                    slashes = 0;
                    continue;
                }
                builder.Append('\\', slashes);
                slashes = 0;
                builder.Append(c);
            }
            builder.Append('\\', slashes * 2);
            builder.Append('"');
        }
        return builder.ToString();
    }
}
