const vehicle = {speedMps: 7};
console.log(JSON.stringify([
  vehicle.sp\u0065edMps,
  vehicle.sp\u{65}edMps,
  vehicle["speed\u004dps"],
  vehicle['speed\x4dps'],
  vehicle[`speedMps`],
  {"speed\u004dps": 1}.speedMps,
  vehicle.ｓｐｅｅｄMps ?? null,
]));
