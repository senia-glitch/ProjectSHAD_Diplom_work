// Правила доступа броней. Единственное место правды о подписях
// и о том, какие правила требуют списка учеников.
export const RULE_LABELS = {
  EVERYONE: 'Все',
  ONLY: 'Только избранные',
  ALL_EXCEPT: 'Все кроме',
  NOBODY: 'Никому',
}

export const VALID_ACCESS_RULES = Object.keys(RULE_LABELS)

export const TARGETS_REQUIRED_RULES = ['ONLY', 'ALL_EXCEPT']

export function ruleRequiresTargets(rule) {
  return TARGETS_REQUIRED_RULES.includes(rule)
}
