using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using Mars.Components.Layers;
using Mars.Interfaces.Agents;
using Mars.Interfaces.Data;
using Mars.Interfaces.Layers;
using SOHModel.Car.Model;

namespace SOHCarletonDrivingV1Box;

/// <summary>
///     Releases CarDriver agents on the DEVS parking-lot schedule (one row per vehicle).
/// </summary>
public sealed class CarletonParkingSchedulerLayer : AbstractActiveLayer
{
    private static CarletonParkingSchedulerLayer? _latest;
    private readonly CarLayer _carLayer;
    private readonly List<SpawnEvent> _events = [];
    private int _nextIndex;

    public int EventsLoaded => _events.Count;
    public int SpawnedCount { get; private set; }
    public int FailedCount { get; private set; }

    public static void PrintSpawnSummary()
    {
        if (_latest == null)
            return;
        Console.WriteLine(
            $"Scenario spawns: loaded={_latest.EventsLoaded}, spawned={_latest.SpawnedCount}, failed={_latest.FailedCount}");
    }

    public CarletonParkingSchedulerLayer(CarLayer carLayer)
    {
        _carLayer = carLayer;
        _latest = this;
    }

    public override bool InitLayer(
        LayerInitData layerInitData,
        RegisterAgent? registerAgentHandle = null,
        UnregisterAgent? unregisterAgent = null)
    {
        base.InitLayer(layerInitData, registerAgentHandle, unregisterAgent);
        var file = layerInitData.LayerInitConfig?.File;
        if (!string.IsNullOrWhiteSpace(file))
        {
            var resolved = File.Exists(file) ? file : Path.Combine(AppContext.BaseDirectory, file);
            LoadEvents(resolved);
        }
        return true;
    }

    public override void PreTick()
    {
        if (RegisterAgent == null || UnregisterAgent == null || Context?.CurrentTimePoint == null)
            return;

        var now = Context.CurrentTimePoint.Value;
        while (_nextIndex < _events.Count && _events[_nextIndex].ReleaseTime <= now)
        {
            var ev = _events[_nextIndex++];
            try
            {
                var driver = new CarDriver(
                    _carLayer,
                    RegisterAgent,
                    UnregisterAgent,
                    3,
                    ev.StartLat,
                    ev.StartLon,
                    ev.DestLat,
                    ev.DestLon,
                    trafficCode: "german");
                driver.StableId = ev.StableId;
                _carLayer.Driver[driver.ID] = driver;
                RegisterAgent(_carLayer, driver);
                SpawnedCount++;
            }
            catch (Exception ex)
            {
                FailedCount++;
                Console.WriteLine($"Spawn failed for {ev.StableId}: {ex.Message}");
            }
        }
    }

    private void LoadEvents(string path)
    {
        _events.Clear();
        _nextIndex = 0;

        using var reader = new StreamReader(path);
        var header = reader.ReadLine();
        if (header == null)
            return;

        var columns = header.Split(',');
        var index = columns
            .Select((name, i) => (name.Trim(), i))
            .ToDictionary(pair => pair.Item1, pair => pair.Item2, StringComparer.OrdinalIgnoreCase);

        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            if (string.IsNullOrWhiteSpace(line))
                continue;

            var parts = line.Split(',');
            var releaseTime = ParseReleaseTime(parts[index["releaseTime"]]);
            _events.Add(new SpawnEvent(
                releaseTime,
                parts[index["stableId"]],
                double.Parse(parts[index["startLat"]], CultureInfo.InvariantCulture),
                double.Parse(parts[index["startLon"]], CultureInfo.InvariantCulture),
                double.Parse(parts[index["destLat"]], CultureInfo.InvariantCulture),
                double.Parse(parts[index["destLon"]], CultureInfo.InvariantCulture)));
        }

        _events.Sort((a, b) => a.ReleaseTime.CompareTo(b.ReleaseTime));
    }

    private static DateTime ParseReleaseTime(string value)
    {
        var formats = new[]
        {
            "yyyy-MM-ddTHH:mm:ss",
            "yyyy-MM-dd HH:mm:ss",
            "HH:mm:ss",
            "HH:mm"
        };

        foreach (var format in formats)
        {
            if (DateTime.TryParseExact(value.Trim(), format, CultureInfo.InvariantCulture,
                    DateTimeStyles.None, out var parsed))
                return parsed;
        }

        return DateTime.Parse(value.Trim(), CultureInfo.InvariantCulture);
    }

    private sealed record SpawnEvent(
        DateTime ReleaseTime,
        string StableId,
        double StartLat,
        double StartLon,
        double DestLat,
        double DestLon);
}
