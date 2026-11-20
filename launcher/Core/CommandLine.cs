namespace TimeLinkLauncher.Core;

public enum StartKind { Window, Launch, Play }

/// How the launcher was started: the shortcuts --play, and a folder's own launcher script --launch &lt;folder&gt;.
///   (nothing)                                    the window
///   --launch &lt;folder&gt;                            the window, on that build
///   --play [&lt;folder&gt;]                           start that build's game (else the default build's), with no window
/// Unknown arguments are kept in Ignored (and do not stop the start).
public sealed record StartRequest(StartKind Kind, string? Folder, IReadOnlyList<string> Ignored, string? Problem)
{
    /// A shortcut's start (--play) when the player chose that shortcuts open the launcher (LauncherSettings.ShortcutsOpenLauncher):
    /// the window, on the shortcut's build when it names one (as --launch &lt;folder&gt;), else as a plain start. Anything else as it was
    public StartRequest ForShortcuts(bool openLauncher) =>
        !openLauncher || Kind != StartKind.Play || Problem != null ? this
            : this with { Kind = Folder != null ? StartKind.Launch : StartKind.Window };

    public static StartRequest Parse(IReadOnlyList<string> args)
    {
        StartKind kind = StartKind.Window;
        string? folder = null, problem = null;
        var ignored = new List<string>();

        void Want(StartKind k, string? f)
        {
            if (kind != StartKind.Window && kind != k) problem ??= "--launch and --play go one at a time.";
            else kind = k;
            folder = f ?? folder;
        }

        for (var i = 0; i < args.Count; i++)
        {
            var a = args[i];
            var next = i + 1 < args.Count ? args[i + 1] : null;
            switch (a)
            {
                case "--launch" when next == null || next.StartsWith("--", StringComparison.Ordinal):
                    problem ??= a + " needs a game folder.";
                    break;
                case "--launch":
                    Want(StartKind.Launch, next);
                    i++;
                    break;
                case "--play":
                    var named = next != null && !next.StartsWith("--", StringComparison.Ordinal);
                    Want(StartKind.Play, named ? next : null);
                    if (named) i++;
                    break;
                default:
                    ignored.Add(a);
                    break;
            }
        }
        return new StartRequest(kind, folder, ignored, problem);
    }
}
