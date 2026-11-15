using System.Text;
using TimeLinkLauncher.Core;

/// Fetching as this fork does it, with no Cloudflare edge in front (CdnFetcher went with MagicBeanDev's): a release file and a
/// release list go to the address they name, and a part goes to its link then each of its mirrors once each, in order.
static partial class Program
{
    /// A server whose files can fail: Status (null: no answer) once FailAt bytes have gone out (0: before any)
    sealed record Served(byte[] Bytes, int? FailAt = null, int? Status = null);

    sealed class FailingFetcher : IFetcher
    {
        public readonly Dictionary<string, Served> Files = new();
        public readonly List<string> Asked = new();

        /// A text: "text of <url>", or the failure a Served with FailAt 0 has for it
        public Task<string> GetTextAsync(string url, string? accept, CancellationToken cancel)
        {
            Asked.Add(url);
            if (Files.TryGetValue(url, out var s) && s.FailAt == 0) throw new FetchException("authored failure", s.Status);
            return Task.FromResult("text of " + url);
        }

        public async Task DownloadAsync(string url, Stream to, Action<long>? progress, CancellationToken cancel)
        {
            Asked.Add(url);
            if (!Files.TryGetValue(url, out var s)) throw new FetchException("not found: " + url, 404);
            for (var at = 0; at < s.Bytes.Length; at += 7)
            {
                if (s.FailAt is { } fail && at >= fail) throw new FetchException("authored failure", s.Status);
                var n = Math.Min(7, s.Bytes.Length - at);
                await to.WriteAsync(s.Bytes.AsMemory(at, n), cancel);
                progress?.Invoke(at + n);
            }
        }
    }

    static async Task FetchChecks()
    {
        const string release = "https://github.com/HanYolo1/timeLink/releases/download/v3.1.0/timeLink-v3.1.0-x86_64.AppImage";
        const string mirror = "https://example.invalid/timeLink-v3.1.0-x86_64.AppImage";
        const string upstream = "https://github.com/mstorsjo/llvm-mingw/releases/download/20261104/llvm-mingw-20261104-ucrt-x86_64.zip";
        const string list = "https://api.github.com/repos/HanYolo1/timeLink/releases";
        var bytes = Encoding.UTF8.GetBytes(string.Concat(Enumerable.Range(0, 20).Select(i => $"release file line {i}\n")));
        var other = Encoding.UTF8.GetBytes(string.Concat(Enumerable.Range(0, 20).Select(i => $"release FILE line {i}\n")));
        var server = new FailingFetcher();
        var root = Folder("fetch");
        server.Files[release] = new Served(bytes);
        server.Files[list] = new Served(other);

        // (a release file and a release list go to the address given: there is no edge to try first)
        server.Asked.Clear();
        using (var to = new MemoryStream())
        {
            await server.DownloadAsync(release, to, null, CancellationToken.None);
            Require(to.ToArray().SequenceEqual(bytes) && server.Asked.SequenceEqual(new[] { release }), "A release file from its address.");
        }
        server.Asked.Clear();
        Require(await server.GetTextAsync(list, "application/json", CancellationToken.None) == "text of " + list
                && server.Asked.SequenceEqual(new[] { list }), "A release list from its address.");

        // (a part through Toolchains: its link, then each mirror in turn, each once, in order)
        var app = Zip(("timeLinkBuilder/timeLinkBuilder.exe", "MZ", null, 0x1A4), ("timeLinkBuilder/tools/nx2/make_game.py", "w", null, 0x1A4),
                      ("timeLinkBuilder/tools/python/python.exe", "MZ", null, 0x1A4));
        const string appUrl = "https://github.com/HanYolo1/timeLink/releases/download/v3.6.0/timeLinkBuilder-v3.6.0-windows-x64.zip";
        server.Files[appUrl] = new Served(app);
        var llvm = Zip(("llvm-mingw-20261104-ucrt-x86_64/bin/clang.exe", "MZ", null, 0x1A4));
        server.Files[upstream] = new Served(llvm);
        server.Files[mirror] = new Served(other, 0, 503);   // (a mirror that answers another file is not the one the list names)
        PartsList Setup(string tag, string toolLinks) => new(ListKind.Setup, tag,
            new List<Part> { new(ShaOf(app), app.Length, ".", null, null, appUrl) }
                .Concat(ToolsLock.Parse($"tool llvm-mingw 20261104 windows-x64 {ShaOf(llvm)} {llvm.Length} timeLinkBuilder/tools/llvm-mingw "
                                        + $"llvm-mingw-20261104-ucrt-x86_64 {toolLinks}", "windows-x64")).ToList(), ToolsLock.Run);
        var chains = new Toolchains(Path.Combine(root, "toolchains"), server);
        server.Asked.Clear();
        var w = await chains.InstallAsync(Setup("v3.6.0", $"{mirror} {upstream}"));
        Require(File.Exists(Path.Combine(w.ToolsRoot, "llvm-mingw", "bin", "clang.exe")) && File.Exists(w.MakeGame),
                "A builder and a tool from the tool's last link.");
        Require(server.Asked.SequenceEqual(new[] { appUrl, mirror, upstream }),
                "Its link, then each mirror once, in order: " + string.Join(", ", server.Asked));

        // (a link listed as its own mirror is tried once, at its first place)
        chains.Prune(Array.Empty<string>());
        server.Asked.Clear();
        await chains.InstallAsync(Setup("v3.6.2", $"{upstream} {upstream}"));
        Require(server.Asked.SequenceEqual(new[] { appUrl, upstream }),
                "A link repeated among the mirrors is tried once: " + string.Join(", ", server.Asked));

        // (a builder that is another file is refused, and no mirror of it is taken on: the part is one file, checked)
        server.Files[appUrl] = new Served(other);
        chains.Prune(Array.Empty<string>());
        server.Asked.Clear();
        await ThrowsAsync<InvalidDataException>(() => chains.InstallAsync(Setup("v3.6.3", $"{upstream}")),
                                                "A builder that is another file, its SHA-256 not the list's, was installed.");
        Require(!chains.IsInstalled("v3.6.3"), "Another builder than the list names was installed.");
    }
}
