// Результат 2, C4: навмисне порушення обмеження унікальності id.
// Очікується помилка Neo.ClientError.Schema.ConstraintValidationFailed:
// "Node(...) already exists with label `Compartment` and property `id` = 'Compartment_V012'"
CREATE (:Compartment {id: 'Compartment_V012', unitCode: 'V-999', name: 'Дублікат для тесту'});
