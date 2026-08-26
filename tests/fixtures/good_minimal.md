# Fixture: good minimal

### RL-TEST-01 - A minimal valid rule

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
