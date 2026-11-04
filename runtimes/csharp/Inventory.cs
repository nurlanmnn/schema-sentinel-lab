using System.Globalization;
using System.Text.Json;
using Google.Protobuf;

static class InventoryRuntime
{
    public static void Run()
    {
        var requests = JsonSerializer.Deserialize<InventoryRequest[]>(Console.In.ReadToEnd(),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)) ?? throw new JsonException("Missing requests");
        var results = requests.Select(request => {
            var entity = Simulation.Inventory.StockItem.Parser.ParseFrom(Convert.FromBase64String(request.Payload));
            var sample = new Simulation.Inventory.StockItem { Sku = request.Sku, Quantity = int.Parse(request.Quantity, CultureInfo.InvariantCulture) };
            sample.DisplayLabels.Add(request.DisplayLabels ?? Array.Empty<string>());
            var fields = new Dictionary<string, object> { ["sku"] = entity.Sku, ["quantity"] = entity.Quantity.ToString(CultureInfo.InvariantCulture) };
            if (request.DisplayLabels is not null)
                fields["display_labels"] = entity.DisplayLabels.ToArray();
            return new { fields, in_stock = entity.Quantity > 0 && entity.State == Simulation.Inventory.StockState.Unspecified, constructed_payload = Convert.ToBase64String(sample.ToByteArray()) };
        });
        Console.WriteLine(JsonSerializer.Serialize(results));
    }
}
record InventoryRequest(string Payload, string Sku, string Quantity, [property: System.Text.Json.Serialization.JsonPropertyName("display_labels")] string[]? DisplayLabels);
