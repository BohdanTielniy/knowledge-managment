// Результат 2, C4: навмисне порушення обмеження унікальності бізнес-ключа unitCode.
// Очікується помилка ConstraintValidationFailed для `Compartment` та `unitCode` = 'V-012'.
CREATE (:Compartment {id: 'Compartment_TEST', unitCode: 'V-012', name: 'Тест порушення unitCode'});
