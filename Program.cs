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
using SOHModel.Multimodal.Model;

namespace SOHCarletonWalkingBox;

internal static class Program
{
    public static void Main(string[] args)
    {
        Thread.CurrentThread.CurrentCulture = new CultureInfo("EN-US");
        LoggerFactory.SetLogLevel(LogLevel.Off);

        var description = new ModelDescription();
        description.AddLayer<CarLayer>();
        description.AddAgent<CarDriver, CarLayer>();
        description.AddEntity<Car>();

        ISimulationContainer application;
        if (args is { Length: > 0 })
        {
            var configPath = args[0];
            var configText = File.ReadAllText(configPath);
            var simConfig = SimulationConfig.Deserialize(configText);
            if (configText.Contains("CarDriverSchedulerLayer", StringComparison.Ordinal))
                description.AddLayer<CarDriverSchedulerLayer>();
            application = SimulationStarter.BuildApplication(description, simConfig);
        }
        else
        {
            var simConfig = SimulationConfig.Deserialize(File.ReadAllText("config.json"));
            description.AddLayer<CarDriverSchedulerLayer>();
            application = SimulationStarter.BuildApplication(description, simConfig);
        }

        var simulation = application.Resolve<ISimulation>();

        var watch = Stopwatch.StartNew();
        var state = simulation.StartSimulation();
        watch.Stop();

        Console.WriteLine($"Executed iterations {state.Iterations} lasted {watch.Elapsed}");
        application.Dispose();
    }
}
