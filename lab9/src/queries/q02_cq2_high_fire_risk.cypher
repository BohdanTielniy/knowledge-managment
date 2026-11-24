// CQ2: Які метеозаміри означають високий пожежний ризик і в яких лісництвах?
// Конструкції: MATCH, OPTIONAL MATCH, складна фільтрація WHERE (пороги R8 з ЛР 7), ORDER BY.
MATCH (o:MeteoObservation)-[m:MONITORS_UNIT]->(f:Forestry)
WHERE o.airTemperatureC > 30.0
  AND o.airHumidityPercent < 30.0
  AND o.daysWithoutRain >= 7
OPTIONAL MATCH (a:Forester)-[:SUPERVISES]->(f)
RETURN o.observationDate AS obsDate,
       f.unitCode AS forestryCode,
       f.name AS forestryName,
       o.airTemperatureC AS tempC,
       o.airHumidityPercent AS humidityPct,
       o.daysWithoutRain AS dryDays,
       collect(DISTINCT a.name) AS supervisingForesters,
       m.validFrom AS validFrom
ORDER BY obsDate ASC;
