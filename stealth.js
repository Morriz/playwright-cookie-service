// Comprehensive stealth patches to evade X/Twitter bot detection
// Hide webdriver flag
Object.defineProperty(navigator, 'webdriver', {
  get: () => false,
});

// Detect browser type
const isChrome = navigator.userAgent.includes('Chrome') || navigator.userAgent.includes('Chromium');
const isFirefox = navigator.userAgent.includes('Firefox');

// Mock chrome object (critical for detection) - ONLY for Chrome-based browsers
if (isChrome && !window.chrome) {
  window.chrome = {
    runtime: {},
  };
}

// chrome.csi - Chrome Site Information timing
if (isChrome && window.chrome && !window.chrome.csi) {
  window.chrome.csi = function() {
    return {
      startE: Date.now(),
      onloadT: Date.now(),
      pageT: Math.random() * 1000,
      tran: 15
    };
  };
}

// chrome.loadTimes - Page load timing
if (isChrome && window.chrome && !window.chrome.loadTimes) {
  window.chrome.loadTimes = function() {
    return {
      requestTime: Date.now() / 1000,
      startLoadTime: Date.now() / 1000,
      commitLoadTime: Date.now() / 1000,
      finishDocumentLoadTime: Date.now() / 1000,
      finishLoadTime: Date.now() / 1000,
      firstPaintTime: Date.now() / 1000,
      firstPaintAfterLoadTime: 0,
      navigationType: 'Other',
      wasFetchedViaSpdy: false,
      wasNpnNegotiated: true,
      npnNegotiatedProtocol: 'h2',
      wasAlternateProtocolAvailable: false,
      connectionInfo: 'h2'
    };
  };
}

// chrome.app
if (isChrome && window.chrome && !window.chrome.app) {
  window.chrome.app = {
    isInstalled: false,
    InstallState: {
      DISABLED: 'disabled',
      INSTALLED: 'installed',
      NOT_INSTALLED: 'not_installed'
    },
    RunningState: {
      CANNOT_RUN: 'cannot_run',
      READY_TO_RUN: 'ready_to_run',
      RUNNING: 'running'
    }
  };
}

// Mock plugins - Browser specific
Object.defineProperty(navigator, 'plugins', {
  get: () => {
    if (isFirefox) {
      // Firefox typically has different plugins or none in modern versions
      return [];
    }
    // Chrome has ~3-5 plugins typically
    return [1, 2, 3, 4, 5];
  },
});

// Mock languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['en-US', 'en'],
});

// Mock hardware specs (from real system)
Object.defineProperty(navigator, 'hardwareConcurrency', {
  get: () => 16,
});

Object.defineProperty(navigator, 'deviceMemory', {
  get: () => 8,
});

// Platform - Keep consistent with user agent
// Note: User agent claims macOS, so platform should match
Object.defineProperty(navigator, 'platform', {
  get: () => 'MacIntel',
});

// Vendor - Browser specific
Object.defineProperty(navigator, 'vendor', {
  get: () => {
    if (isFirefox) {
      return ''; // Firefox has empty vendor string
    }
    return 'Google Inc.'; // Chrome/Chromium
  },
});

// Permissions API - Fix inconsistencies
const originalQuery = navigator.permissions?.query;
if (navigator.permissions) {
  navigator.permissions.query = function(parameters) {
    // Handle notification permission consistently
    if (parameters.name === 'notifications') {
      return Promise.resolve({
        state: Notification.permission,
        onchange: null
      });
    }
    // For other permissions, use original or return prompt
    if (originalQuery) {
      return originalQuery.call(navigator.permissions, parameters);
    }
    return Promise.resolve({ state: 'prompt', onchange: null });
  };
} else {
  navigator.permissions = {
    query: (parameters) => {
      if (parameters.name === 'notifications') {
        return Promise.resolve({
          state: Notification.permission,
          onchange: null
        });
      }
      return Promise.resolve({ state: 'prompt', onchange: null });
    }
  };
}

// WebGL fingerprinting protection - CRITICAL for bot detection
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
  if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
    if (isFirefox) {
      return 'Mozilla'; // Firefox uses Mozilla as vendor
    }
    return 'Google Inc. (Apple)'; // Chrome uses Google Inc.
  }
  if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
    if (isFirefox) {
      // Firefox on software rendering or llvmpipe
      return 'llvmpipe (LLVM 15.0.7, 256 bits)';
    }
    return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)'; // Chrome uses ANGLE
  }
  return getParameter.apply(this, arguments);
};

// Also spoof WebGL2
if (typeof WebGL2RenderingContext !== 'undefined') {
  const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
  WebGL2RenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
      if (isFirefox) {
        return 'Mozilla';
      }
      return 'Google Inc. (Apple)';
    }
    if (parameter === 37446) {
      if (isFirefox) {
        return 'llvmpipe (LLVM 15.0.7, 256 bits)';
      }
      return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)';
    }
    return getParameter2.apply(this, arguments);
  };
}

// Canvas fingerprinting protection
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
  // Add tiny random noise to prevent canvas fingerprinting
  const context = this.getContext('2d');
  if (context) {
    const imageData = context.getImageData(0, 0, this.width, this.height);
    for (let i = 0; i < imageData.data.length; i += 4) {
      imageData.data[i] += Math.floor(Math.random() * 2);
    }
    context.putImageData(imageData, 0, 0);
  }
  return toDataURL.apply(this, arguments);
};

// iframe.contentWindow - Fix iframe detection
try {
  if (window.top !== window.self) {
    // In iframe - proxy contentWindow to avoid detection
    Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
      get: function() {
        return window;
      }
    });
  }
} catch (e) {
  // Ignore if we can't access window.top (cross-origin)
}

// media.codecs - Spoof realistic codec support
const videoElement = document.createElement('video');
const audioElement = document.createElement('audio');
const originalCanPlayType = HTMLMediaElement.prototype.canPlayType;

HTMLMediaElement.prototype.canPlayType = function(type) {
  // Return realistic codec support for Chrome
  const codecSupport = {
    'video/ogg': '',
    'video/mp4': 'probably',
    'video/webm': 'probably',
    'audio/ogg': 'probably',
    'audio/mpeg': 'probably',
    'audio/wav': 'probably',
    'audio/x-m4a': 'maybe',
    'audio/mp4': 'probably',
    'video/mp4; codecs="avc1.42E01E"': 'probably',
    'video/mp4; codecs="avc1.42E01E, mp4a.40.2"': 'probably',
    'video/mp4; codecs="avc1.58A01E"': 'probably',
    'video/webm; codecs="vp8"': 'probably',
    'video/webm; codecs="vp9"': 'probably',
    'audio/webm; codecs="vorbis"': 'probably',
    'audio/webm; codecs="opus"': 'probably'
  };

  if (type in codecSupport) {
    return codecSupport[type];
  }

  return originalCanPlayType.call(this, type);
};

// window.outerdimensions - Set realistic window dimensions
Object.defineProperty(window, 'outerWidth', {
  get: () => window.innerWidth,
});

Object.defineProperty(window, 'outerHeight', {
  get: () => window.innerHeight + 85, // Add typical browser chrome height
});

// Firefox-specific evasions
if (isFirefox) {
  // Remove automation markers that Firefox might set
  delete navigator.__webdriver_script_fn;
  delete navigator.__selenium_unwrapped;
  delete navigator.__webdriver_unwrapped;
  delete navigator.__driver_evaluate;
  delete navigator.__webdriver_evaluate;
  delete navigator.__fxdriver_evaluate;
  delete navigator.__driver_unwrapped;
  delete navigator.__fxdriver_unwrapped;
  delete navigator.__webdriver_script_func;
  delete navigator.__webdriver_script_function;

  // Firefox has specific properties that shouldn't exist in automation
  // Make sure mozInnerScreenX/Y exist (real Firefox has these)
  if (typeof window.mozInnerScreenX === 'undefined') {
    Object.defineProperty(window, 'mozInnerScreenX', {
      get: () => window.screenX || 0,
    });
  }
  if (typeof window.mozInnerScreenY === 'undefined') {
    Object.defineProperty(window, 'mozInnerScreenY', {
      get: () => window.screenY || 0,
    });
  }

  // Older Firefox versions had window.sidebar - avoid adding it as it's deprecated
  // Modern detection doesn't rely on this anymore

  // Firefox should NOT have chrome object
  if (window.chrome) {
    delete window.chrome;
  }
}
