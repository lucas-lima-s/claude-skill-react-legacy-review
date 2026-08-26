# Fixture: missing accept-when

### RL-TEST-01 - A rule with no accept-when clause

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
