// Stealth script to evade bot detection - matches working Playwright context
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', {
  get: () => false,
});

// Mock chrome object (critical for Chromium detection)
window.chrome = {
  runtime: {},
};

// Mock plugins (5 plugins like real Chrome)
Object.defineProperty(navigator, 'plugins', {
  get: () => [1, 2, 3, 4, 5],
});

// Mock languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['en-US', 'en'],
});

// Mock hardware (from working session)
Object.defineProperty(navigator, 'hardwareConcurrency', {
  get: () => 16,
});

Object.defineProperty(navigator, 'deviceMemory', {
  get: () => 8,
});

// Platform
Object.defineProperty(navigator, 'platform', {
  get: () => 'MacIntel',
});

// Vendor
Object.defineProperty(navigator, 'vendor', {
  get: () => 'Google Inc.',
});

// Permissions API
if (!navigator.permissions) {
  navigator.permissions = {
    query: () => Promise.resolve({ state: 'prompt' }),
  };
}
