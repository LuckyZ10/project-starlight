# E2E Tests

This directory contains end-to-end tests using Playwright.

## Running Tests

### Run all tests (headless)
```bash
npm run test:e2e
```

### Run tests in headed mode (with browser visible)
```bash
npm run test:e2e:headed
```

### Run tests in UI mode
```bash
npm run test:e2e:ui
```

### View test report
```bash
npm run test:e2e:report
```

## Test Structure

### login.spec.ts
Tests the login flow including:
- Form display
- Validation (empty fields, email format, password length)
- Successful login
- Wrong credentials handling

### register.spec.ts
Tests the registration flow including:
- Form display
- Validation
- Successful registration
- Duplicate email handling

### learn.spec.ts
Tests the complete learning flow including:
- Cartridge selection
- Node selection
- Conversation interface
- Answer submission
- Node navigation
- Stats page
- Dark mode toggle

## Prerequisites

1. Backend must be running on port 8000
2. Frontend must be running on port 3000
3. Database should have test data or the tests will create new users

## Test Data

Tests create temporary test users with random emails to avoid conflicts.

## Troubleshooting

If tests fail, check:
1. Backend and frontend are running
2. Database connection is working
3. No conflicting users exist (use different test emails)

## CI/CD

Tests are configured to run in CI with retries and video capture on failure.
