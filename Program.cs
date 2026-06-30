using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Threading;
using Mars.Common.Core.Logging;
using Mars.Components.Starter;
using Mars.Core.Simulation;
using Mars.Interfaces;
using Mars.Interfaces.Model;
using SOHModel.Car.Model;

namespace SOHCarletonDrivingV1Box;

internal static class Program
{
    public static void Main(string[] args)
    {
        Thread.CurrentThread.CurrentCulture = new CultureInfo("EN-US");
        LoggerFactory.SetLogLevel(LogLevel.Warning);

        var description = new ModelDescription();
        description.AddLayer<CarLayer>();
        description.AddLayer<CarletonParkingSchedulerLayer>();
        description.AddAgent<CarDriver, CarLayer>();
        description.AddEntity<Car>();

        var configPath = args is { Length: > 0 } ? args[0] : "config.json";
        var simConfig = SimulationConfig.Deserialize(File.ReadAllText(configPath));
        var application = SimulationStarter.BuildApplication(description, simConfig);
        var simulation = application.Resolve<ISimulation>();

        var watch = Stopwatch.StartNew();
        var state = simulation.StartSimulation();
        watch.Stop();

        Console.WriteLine($"Executed iterations {state.Iterations} lasted {watch.Elapsed}");
        CarletonParkingSchedulerLayer.PrintSpawnSummary();

        application.Dispose();
    }
}
