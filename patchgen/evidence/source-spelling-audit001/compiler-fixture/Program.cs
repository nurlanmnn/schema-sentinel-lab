var vehicle = new Vehicle();
Console.WriteLine(vehicle.Sp\u0065edMps);
Console.WriteLine(vehicle.@SpeedMps);
Console.WriteLine(vehicle.Speed‌Mps);
Console.WriteLine(vehicle["Speed\u004dps"]);
Console.WriteLine(vehicle[@"SpeedMps"]);
Console.WriteLine(vehicle["Speed\x004dps"]);
Console.WriteLine(vehicle["Speed\U0000004dps"]);
Console.WriteLine(typeof(Vehicle).GetPro\u0070erty("SpeedMps")!.Name);
Console.WriteLine(vehicle[@"Speed\u004dps"]);
class Vehicle {
  public int SpeedMps => 7;
  public string this[string key] => key;
}
