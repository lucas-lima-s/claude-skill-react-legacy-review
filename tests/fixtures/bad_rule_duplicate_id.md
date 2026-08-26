# Fixture: duplicate id

### RL-TEST-01 - The first rule with this id

**Impact:** bug
**Symptom:** something observable goes wrong.

```jsx
// avoid
function Bad() {
  return null
}
```

```jsx
// prefer
function Good() {
  return null
}
```

**Accept when:** never.

### RL-TEST-01 - The second rule reusing the same id

**Impact:** perf
**Symptom:** something else observable goes wrong.

```jsx
// avoid
function AlsoBad() {
  return null
}
```

```jsx
// prefer
function AlsoGood() {
  return null
}
```

**Accept when:** never.
