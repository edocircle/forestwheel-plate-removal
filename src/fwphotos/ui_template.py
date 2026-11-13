"""Bright, minimal, Apple-style Stitch UI template for the Forest Wheel Plate Removal System.

Implements the 4 Stitch MCP screens from Project 'ForestWheel Plate Removal System':
1. SCREEN 1 — UPLOAD ('Web Upload & Plate Detection' / 'Upload & Plate Detection'):
   - Large dashed drop zone with 'Upload photos' / 'Select Multiple Photos' button (bulk upload).
   - Thumbnail grid with animated radial SVG progress ring per photo
     (Detecting plate → Removing plate → Done).
   - Input field 'Plate number' per batch (auto-filled when files are selected/detected, editable),
     plus vehicle title/price metadata and masking style selector.
   - Primary button 'Process & Save'.
2. SCREEN 2 — GALLERY ('Web Vehicle Gallery' / 'Vehicle Gallery', grouped by plate number):
   - Top search bar (search by plate number or model) + status filter pills.
   - Top-right 'Select' button to enter selection mode.
   - Each car is a group card: plate number title badge (e.g. SXX 1234 A), editable vehicle title,
     photo count, Before/After toggle (Original vs Plate Removed), and 3-4 preview thumbnails.
   - Tap a group to open a full grid view of all photos for that car with Before/After toggle,
     single-photo delete, edit group details, or open in Frame Studio.
3. SCREEN 3 — FRAME TEMPLATE EDITOR ('Web Frame Studio' / 'Frame Template Editor'):
   - Pick any photo from any car group, then choose frame ratio with a segmented control: 1:1, 16:9, 9:16.
   - Canvas preview shows the photo inside the chosen frame.
   - Fit mode toggle:
     • 'Fit to frame': whole photo is visible, empty space filled with a blurred, enlarged copy of the same photo.
     • 'Fill frame': photo is cropped to cover the whole frame, with drag/pinch to reposition.
   - Apple-style template row below the canvas: Clean White, Soft Grey, Minimal Border, Rounded Card, Glass Overlay.
     Each has an optional toggleable small caption area (car model, price).
   - Buttons: 'Save to Gallery' and 'Export'.
4. SCREEN 4 — DELETE / SELECTION MODE ('Web Selection & Delete Modal' / 'Gallery Selection & Delete Modal'):
   - In Gallery, tapping 'Select' shows checkmarks on photos and on car groups.
   - Floating bottom action bar: 'Select All', 'Delete Selected (n)', plus scope options:
     'Delete selected photos only', 'Delete entire car group', and 'Delete all photos'.
   - Confirmation bottom sheet / modal with red destructive button and Cancel, showing exact item count.
"""

STITCH_UI_HTML = r"""<!DOCTYPE html>
<html class="light" lang="en">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0, viewport-fit=cover" name="viewport"/>
<title>ForestWheel — Apple-Style Plate Removal &amp; Studio</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
tailwind.config = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface": "#fcf8fb",
        "surface-bright": "#fcf8fb",
        "surface-dim": "#dcd9dc",
        "surface-container-lowest": "#ffffff",
        "surface-container-low": "#f6f3f5",
        "surface-container": "#f0edef",
        "surface-container-high": "#eae7ea",
        "surface-container-highest": "#e4e2e4",
        "on-surface": "#1b1b1d",
        "on-surface-variant": "#414755",
        "primary": "#0058bc",
        "primary-container": "#0070eb",
        "primary-fixed": "#d8e2ff",
        "on-primary": "#ffffff",
        "secondary": "#505f76",
        "secondary-container": "#d0e1fb",
        "tertiary": "#bc000a",
        "error": "#ba1a1a",
        "error-container": "#ffdad6",
        "on-error": "#ffffff",
        "outline": "#717786",
        "outline-variant": "#c1c6d7"
      },
      fontFamily: {
        "sans": ["-apple-system", "BlinkMacSystemFont", "SF Pro Display", "SF Pro Text", "Inter", "sans-serif"]
      },
      boxShadow: {
        "apple-card": "0 8px 30px rgba(27, 27, 29, 0.04), 0 2px 6px rgba(27, 27, 29, 0.02)",
        "apple-float": "0 20px 50px rgba(27, 27, 29, 0.12), 0 4px 12px rgba(27, 27, 29, 0.05)",
        "apple-sheet": "0 -12px 48px rgba(27, 27, 29, 0.16)"
      }
    }
  }
}
</script>
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Inter", sans-serif;
    background-color: #fcf8fb;
    color: #1b1b1d;
    -webkit-font-smoothing: antialiased;
  }
  .material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 450, 'GRAD' 0, 'opsz' 24;
    vertical-align: middle;
  }
  .material-fill {
    font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
  }
  .apple-glass {
    background: rgba(252, 248, 251, 0.82);
    backdrop-filter: saturate(180%) blur(20px);
    -webkit-backdrop-filter: saturate(180%) blur(20px);
  }
  .apple-card-white {
    background: #ffffff;
    border: 1px solid rgba(193, 198, 215, 0.28);
    box-shadow: 0 8px 30px rgba(27, 27, 29, 0.04), 0 2px 6px rgba(27, 27, 29, 0.02);
  }
  .no-scrollbar::-webkit-scrollbar { display: none; }
  .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
  @keyframes spinSlow { to { transform: rotate(360deg); } }
  .spin-ring { animation: spinSlow 1.3s linear infinite; transform-origin: center; }
</style>
</head>
<body class="bg-surface text-on-surface min-h-screen pb-28 md:pb-16 selection:bg-primary-fixed selection:text-primary">

<!-- Top Translucent Apple Navigation Bar -->
<header class="sticky top-0 z-40 apple-glass border-b border-outline-variant/25">
  <div class="max-w-7xl mx-auto px-4 sm:px-8 h-16 flex items-center justify-between gap-4">
    <div onclick="switchTab('upload')" class="flex items-center gap-3 cursor-pointer">
      <div class="w-9 h-9 rounded-xl bg-white border border-outline-variant/30 flex items-center justify-center shadow-sm overflow-hidden p-1">
        <img id="header-brand-logo-img" src="/media/brand-logo" alt="Brand Logo" class="max-h-full max-w-full object-contain"/>
      </div>
      <div>
        <span id="header-dealer-name" class="text-lg font-bold tracking-tight text-on-surface">Forest Wheel</span>
        <span id="header-dealer-tagline" class="hidden sm:inline-block ml-2 text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant">Plate Studio</span>
      </div>
    </div>

    <!-- Desktop Segmented 4-Tab Switcher (Upload, Gallery, Frames, Profile) -->
    <nav class="hidden md:flex items-center bg-surface-container p-1 rounded-full border border-outline-variant/20">
      <button id="nav-desk-upload" onclick="switchTab('upload')" class="px-5 py-1.5 rounded-full text-sm font-semibold transition-all flex items-center gap-1.5 bg-white text-primary shadow-sm">
        <span class="material-symbols-outlined text-[18px]">cloud_upload</span>
        <span>Upload</span>
      </button>
      <button id="nav-desk-gallery" onclick="switchTab('gallery')" class="px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">photo_library</span>
        <span>Gallery</span>
        <span id="badge-desk-gallery" class="ml-1 px-1.5 py-0.2 text-[11px] rounded-full bg-surface-container-highest text-on-surface font-bold">0</span>
      </button>
      <button id="nav-desk-frames" onclick="switchTab('frames')" class="px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">crop_free</span>
        <span>Frames</span>
      </button>
      <button id="nav-desk-profile" onclick="switchTab('profile')" class="px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">account_circle</span>
        <span>Profile</span>
      </button>
    </nav>

    <!-- Right Quick Actions -->
    <div class="flex items-center gap-2">
      <button type="button" onclick="switchTab('profile')" id="header-user-pill"
              class="px-3 py-1.5 rounded-full bg-white hover:bg-surface-container border border-outline-variant/30 text-xs font-semibold text-on-surface shadow-sm transition-all flex items-center gap-1.5"
              title="Dealership Profile &amp; Security Settings">
        <span class="w-5 h-5 rounded-full bg-primary-fixed text-primary flex items-center justify-center font-bold text-[11px]" id="header-user-avatar">S</span>
        <span id="header-username-label" class="hidden sm:inline">Sign In</span>
      </button>
      <button type="button" id="header-signout-btn" onclick="logoutProfileAccount()"
              class="hidden px-3 py-1.5 rounded-full bg-surface-container hover:bg-error-container/60 text-on-surface-variant hover:text-error text-xs font-semibold transition-all items-center gap-1"
              title="Sign out of current account session">
        <span class="material-symbols-outlined text-[15px]">logout</span>
        <span class="hidden sm:inline">Sign Out</span>
      </button>
    </div>
  </div>
</header>

<!-- ========================================================================= -->
<!-- GLOBAL ACCOUNT SESSION GATE (BINDS UPLOAD, GALLERY, FRAMES & PROFILE)     -->
<!-- ========================================================================= -->
<div id="profile-auth-view" class="hidden max-w-md mx-auto px-4 py-8 sm:py-14">
  <div class="apple-card-white rounded-[28px] p-7 sm:p-9 space-y-6 border border-outline-variant/30">
    <!-- Top Icon & Title -->
    <div class="text-center space-y-2">
      <div class="w-14 h-14 rounded-2xl bg-primary-fixed text-primary mx-auto flex items-center justify-center shadow-sm">
        <span class="material-symbols-outlined text-3xl">account_circle</span>
      </div>
      <span id="auth-target-tab-pill" class="inline-block px-3 py-0.5 rounded-full bg-primary-fixed/60 text-primary text-[11px] font-bold uppercase tracking-wider">
        Account Session Required
      </span>
      <h1 id="auth-card-title" class="text-2xl font-bold tracking-tight text-on-surface">Sign in to Your Workspace</h1>
      <p id="auth-card-subtitle" class="text-xs sm:text-sm text-on-surface-variant">
        Sign in or create an account to access your bound <strong>Upload</strong>, <strong>Gallery</strong>, <strong>Frames</strong>, and <strong>Profile</strong> workspace.
      </p>
    </div>

    <!-- Segmented Control: Sign In vs Create Account -->
    <div class="grid grid-cols-2 bg-surface-container p-1 rounded-2xl">
      <button type="button" id="auth-tab-signin" onclick="setProfileAuthMode('signin')"
              class="py-2 rounded-xl text-xs font-bold bg-white text-on-surface shadow-sm transition-all">
        Sign In
      </button>
      <button type="button" id="auth-tab-signup" onclick="setProfileAuthMode('signup')"
              class="py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">
        Create Account
      </button>
    </div>

    <!-- Continue with Google Email Logon Button -->
    <button type="button" onclick="openGoogleLoginModal()"
            class="w-full py-3 px-4 rounded-2xl bg-white hover:bg-surface border border-outline-variant/50 text-on-surface font-semibold text-xs sm:text-sm shadow-sm transition-all flex items-center justify-center gap-2.5">
      <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
        <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.2 1.3-1.6 3.8-5.5 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 6.6 2.2 2.2 6.6 2.2 12S6.6 21.8 12 21.8c6.9 0 9.6-4.8 9.6-7.3 0-.5-.1-.9-.1-1.3H12z"/>
        <path fill="#34A853" d="M3.3 7.3l3.2 2.4C7.4 7.5 9.5 5.9 12 5.9c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 8.2 2.2 4.9 4.3 3.3 7.3z"/>
        <path fill="#FBBC05" d="M12 21.8c2.6 0 4.8-.9 6.4-2.4l-3-2.5c-.8.6-1.9 1-3.4 1-2.5 0-4.7-1.7-5.5-4.1l-3.2 2.5c1.6 3.2 4.9 5.5 8.7 5.5z"/>
        <path fill="#4285F4" d="M21.6 14.5c.1-.5.2-1.1.2-1.8 0-.6-.1-1.2-.2-1.7H12v3.9h5.5c-.3 1.3-1.1 2.4-2.1 3.1l3 2.5c1.8-1.6 3.2-4 3.2-6z"/>
      </svg>
      <span>Continue with Google</span>
    </button>

    <!-- Divider -->
    <div class="relative flex items-center justify-center">
      <div class="border-t border-outline-variant/30 w-full"></div>
      <span class="bg-white px-3 text-[11px] font-medium text-outline uppercase tracking-wider shrink-0">or with email</span>
      <div class="border-t border-outline-variant/30 w-full"></div>
    </div>

    <!-- Email & Password Form -->
    <div class="space-y-3.5">
      <div>
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Email Address</label>
        <input id="auth-email-input" type="email" autocomplete="email" placeholder="you@company.com"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>

      <div>
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Password</label>
        <input id="auth-password-input" type="password" autocomplete="current-password" placeholder="Enter password"
               onkeydown="if(event.key==='Enter') submitProfileAuth();"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>

      <div id="auth-confirm-wrap" class="hidden">
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Confirm Password</label>
        <input id="auth-confirm-input" type="password" autocomplete="new-password" placeholder="Re-enter password"
               onkeydown="if(event.key==='Enter') submitProfileAuth();"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>
    </div>

    <p id="profile-auth-feedback" class="text-xs font-semibold text-center hidden"></p>

    <button type="button" id="auth-submit-btn" onclick="submitProfileAuth()"
            class="w-full py-3 rounded-2xl bg-gradient-to-b from-primary-container to-primary hover:opacity-95 text-white font-semibold text-sm shadow-md transition-all flex items-center justify-center gap-2">
      <span class="material-symbols-outlined text-[18px]">login</span>
      <span id="auth-submit-label">Sign In</span>
    </button>

    <p class="text-xs text-center text-on-surface-variant">
      <span id="auth-switch-prompt">Don't have an account?</span>
      <button type="button" id="auth-switch-link" onclick="toggleProfileAuthMode()" class="font-bold text-primary hover:underline ml-1">
        Create account
      </button>
    </p>
  </div>
</div>

<!-- ========================================================================= -->
<!-- SCREEN 1: UPLOAD & PLATE DETECTION                                        -->
<!-- ========================================================================= -->
<main id="screen-upload" class="max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <div class="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
    <div>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface">Upload &amp; Plate Removal</h1>
      <p class="text-sm sm:text-base text-on-surface-variant mt-1">Select multiple car photos to automatically detect and mask license plates.</p>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
    <!-- Left Column: Dashed Drop Zone + Photo Progress Grid -->
    <div class="lg:col-span-8 space-y-6">
      <!-- Hidden file input -->
      <input id="upload-file-input" type="file" multiple accept=".jpg,.jpeg,.png,.heic,image/*" class="hidden" onchange="handleFilesSelected(this.files)"/>

      <!-- Large Dashed Drop Zone -->
      <div id="upload-dropzone"
           onclick="document.getElementById('upload-file-input').click()"
           ondragover="event.preventDefault(); this.classList.add('border-primary', 'bg-primary-fixed/20');"
           ondragleave="this.classList.remove('border-primary', 'bg-primary-fixed/20');"
           ondrop="event.preventDefault(); this.classList.remove('border-primary', 'bg-primary-fixed/20'); handleFilesSelected(event.dataTransfer.files);"
           class="apple-card-white rounded-[24px] p-8 sm:p-12 border-2 border-dashed border-primary/35 hover:border-primary transition-all cursor-pointer flex flex-col items-center justify-center text-center group">
        <div class="w-16 h-16 rounded-2xl bg-primary-fixed/60 text-primary flex items-center justify-center mb-4 group-hover:scale-105 transition-transform">
          <span class="material-symbols-outlined text-4xl">add_photo_alternate</span>
        </div>
        <h2 class="text-lg sm:text-xl font-semibold text-on-surface mb-1">Drop car photos here</h2>
        <p class="text-xs sm:text-sm text-on-surface-variant max-w-md mb-6">
          Bulk upload raw showroom photos (JPEG, PNG, HEIC). Plates are automatically detected and covered.
        </p>
        <button type="button" onclick="event.stopPropagation(); document.getElementById('upload-file-input').click();"
                class="bg-gradient-to-b from-primary-container to-primary text-white font-semibold px-7 py-3 rounded-full shadow-md hover:opacity-95 active:scale-[0.98] transition-all flex items-center gap-2 text-sm">
          <span class="material-symbols-outlined text-[20px]">upload_file</span>
          <span>Upload photos</span>
        </button>
      </div>

      <!-- Selected Photos Grid with Progress Rings (Detecting plate -> Removing plate -> Done) -->
      <div id="upload-queue-section" class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <h3 class="text-base sm:text-lg font-bold text-on-surface">Batch Queue</h3>
            <span id="upload-queue-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-fixed text-primary">0 Photos</span>
          </div>
          <button type="button" onclick="clearUploadQueue()" class="text-xs font-semibold text-on-surface-variant hover:text-error transition-colors">
            Clear queue
          </button>
        </div>

        <div id="upload-thumbnails-grid" class="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <!-- Populated dynamically by JS -->
        </div>
      </div>
    </div>

    <!-- Right Column: Batch Plate Number & Process Inspector -->
    <div class="lg:col-span-4 lg:sticky lg:top-24">
      <div class="apple-card-white rounded-[24px] p-6 sm:p-7 space-y-6">
        <div class="flex items-center justify-between border-b border-surface-container pb-4">
          <div>
            <span class="text-[11px] font-bold uppercase tracking-widest text-primary block">Batch Settings</span>
            <h3 class="text-lg font-bold text-on-surface mt-0.5">Vehicle Group</h3>
          </div>
          <span id="upload-detection-pill" class="px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 flex items-center gap-1">
            <span class="material-symbols-outlined text-[14px] material-fill">verified</span>
            <span>Auto-Grouping</span>
          </span>
        </div>

        <!-- Input Field: Plate Number per batch (auto-filled when detected/selected, editable) -->
        <div class="space-y-3">
          <div>
            <label for="input-plate-number" class="block text-xs font-semibold text-on-surface-variant mb-1.5">
              Plate number <span class="text-outline font-normal">(Car group ID, editable)</span>
            </label>
            <div class="relative">
              <input id="input-plate-number" type="text" value="SXX 1234 A" placeholder="e.g. SXX 1234 A"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-2xl px-4 py-3 text-base font-bold tracking-wider uppercase text-on-surface focus:ring-2 focus:ring-primary/15 transition-all"/>
              <span class="material-symbols-outlined text-primary text-lg absolute right-3.5 top-3.5" title="Auto-filled on batch selection">pin</span>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="input-car-model" class="block text-xs font-semibold text-on-surface-variant mb-1">Car Model</label>
              <input id="input-car-model" type="text" value="2023 Porsche 911 GT3" placeholder="e.g. Porsche 911"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-xl px-3 py-2 text-xs font-semibold text-on-surface"/>
            </div>
            <div>
              <label for="input-car-price" class="block text-xs font-semibold text-on-surface-variant mb-1">Listing Price <span class="text-outline font-normal">(optional)</span></label>
              <input id="input-car-price" type="text" value="" placeholder="Leave empty for no price"
                     class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-xl px-3 py-2 text-xs font-semibold text-primary"/>
            </div>
          </div>

          <div>
            <label for="input-car-specs" class="block text-xs font-semibold text-on-surface-variant mb-1">Subtitle / Specs <span class="text-outline font-normal">(shown below car title)</span></label>
            <input id="input-car-specs" type="text" value="4,200 mi • PDK • Shark Blue" placeholder="e.g. 4,200 mi • PDK • Verified Pre-Owned"
                   class="w-full bg-surface-container-low border border-outline-variant/40 focus:border-primary focus:bg-white rounded-xl px-3 py-2 text-xs text-on-surface"/>
          </div>
        </div>

        <!-- Default Frame Ratio for Batch -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <label class="block text-xs font-semibold text-on-surface-variant">Output Aspect Ratio</label>
            <button type="button" onclick="switchTab('frames')" class="text-[11px] font-semibold text-primary hover:underline flex items-center gap-0.5">
              <span>Preset: <strong id="upload-active-preset-pill">Clean White • Fit</strong></span>
              <span class="material-symbols-outlined text-[13px]">tune</span>
            </button>
          </div>
          <div class="grid grid-cols-3 gap-1.5 bg-surface-container p-1 rounded-2xl">
            <button type="button" onclick="setUploadRatio('1:1')" id="up-ratio-1:1" class="py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">1:1</button>
            <button type="button" onclick="setUploadRatio('16:9')" id="up-ratio-16:9" class="py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all">16:9</button>
            <button type="button" onclick="setUploadRatio('9:16')" id="up-ratio-9:16" class="py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">9:16</button>
          </div>
        </div>

        <!-- Primary Button: Process & Save -->
        <div class="pt-2 space-y-2.5">
          <button id="btn-process-save" type="button" onclick="submitUploadBatch()"
                  class="w-full py-4 rounded-2xl bg-gradient-to-b from-primary-container to-primary text-white font-semibold text-base shadow-lg shadow-primary/20 hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-2">
            <span class="material-symbols-outlined text-[20px]">bolt</span>
            <span id="btn-process-save-label">Process &amp; Save</span>
          </button>
          <p id="upload-status-msg" class="text-[11px] text-center text-on-surface-variant">
            Original photos are never modified. Uncertain plates route to Review.
          </p>
        </div>
      </div>
    </div>
  </div>
</main>

<!-- ========================================================================= -->
<!-- SCREEN 2: VEHICLE GALLERY (GROUPED BY PLATE NUMBER) + SELECTION MODE      -->
<!-- ========================================================================= -->
<main id="screen-gallery" class="hidden max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <!-- Header Row + Search Bar + Top-Right "Select" Button -->
  <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
    <div>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface">Vehicle Gallery</h1>
      <p id="gallery-subtitle" class="text-sm text-on-surface-variant mt-0.5">Grouped by plate number • Toggle Original vs Plate Removed</p>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <!-- Search Bar at Top (search by plate number) -->
      <div class="relative flex-1 sm:w-72">
        <span class="material-symbols-outlined text-outline text-[20px] absolute left-3.5 top-2.5">search</span>
        <input id="gallery-search-input" type="text" oninput="renderGallery()" placeholder="Search by plate number (e.g. SXX1234A)..."
               class="w-full pl-10 pr-4 py-2.5 bg-white border border-outline-variant/40 rounded-full text-sm text-on-surface placeholder:text-outline focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all shadow-sm"/>
      </div>

      <!-- Top-Right "Select" Button to enter Selection Mode -->
      <button id="btn-toggle-select-mode" type="button" onclick="toggleSelectionMode()"
              class="px-5 py-2.5 rounded-full font-semibold text-sm border border-outline-variant/50 bg-white hover:bg-surface-container-low text-on-surface transition-all flex items-center gap-1.5 shadow-sm">
        <span class="material-symbols-outlined text-[18px] text-primary" id="icon-select-mode">check_circle</span>
        <span id="label-select-mode">Select</span>
      </button>
    </div>
  </div>

  <!-- Filter Pills & Global Before/After Toggle -->
  <div class="flex flex-wrap items-center justify-between gap-3 mb-7 pb-3 border-b border-outline-variant/25">
    <div class="flex items-center gap-2 overflow-x-auto no-scrollbar">
      <button type="button" onclick="setGalleryFilter('all')" id="flt-all" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-on-surface text-white transition-all">All Cars</button>
      <button type="button" onclick="setGalleryFilter('ready')" id="flt-ready" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all">Plate Removed</button>
      <button type="button" onclick="setGalleryFilter('review')" id="flt-review" class="px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all">Needs Review</button>
    </div>

    <div class="flex items-center gap-2">
      <!-- Global Before / After Default Toggle -->
      <div class="inline-flex items-center bg-surface-container p-1 rounded-full border border-outline-variant/25">
        <button type="button" onclick="setGlobalCompareMode('after')" id="btn-global-after" class="px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all">Plate Removed</button>
        <button type="button" onclick="setGlobalCompareMode('before')" id="btn-global-before" class="px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">Original (Before)</button>
      </div>

      <!-- More Menu for "Delete all photos" -->
      <button type="button" onclick="openDeleteModal('all')" class="px-3.5 py-1.5 rounded-full text-xs font-semibold text-error hover:bg-error-container/40 transition-colors flex items-center gap-1" title="Delete all photos in inventory">
        <span class="material-symbols-outlined text-[16px]">delete_sweep</span>
        <span class="hidden sm:inline">Delete All</span>
      </button>
    </div>
  </div>

  <!-- Gallery Group Cards Grid (2 columns on desktop, 1 on mobile) -->
  <div id="gallery-cards-container" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Populated dynamically by renderGallery() -->
  </div>
</main>

<!-- ========================================================================= -->
<!-- SCREEN 3: FRAME TEMPLATE EDITOR (FRAMES)                                  -->
<!-- ========================================================================= -->
<main id="screen-frames" class="hidden max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">
  <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-6">
    <div>
      <span class="text-xs font-bold uppercase tracking-widest text-primary">Showroom Studio</span>
      <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface mt-0.5">Frame Template Editor</h1>
    </div>
    <!-- Vehicle & Photo Picker -->
    <div class="flex flex-wrap items-center gap-2.5">
      <select id="frame-car-select" onchange="onFrameCarChange()" class="bg-white border border-outline-variant/40 rounded-full px-4 py-2 text-xs font-semibold text-on-surface shadow-sm focus:border-primary focus:ring-primary">
      </select>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
    <!-- Left / Center: Interactive Frame Canvas + Apple Template Row -->
    <div class="lg:col-span-8 space-y-5">
      <!-- Top Controls Bar: Segmented Ratio (1:1, 16:9, 9:16) + Fit Mode Toggle (Fit to Frame vs Fill Frame) -->
      <div class="apple-card-white rounded-2xl p-3 flex flex-wrap items-center justify-between gap-3">
        <!-- Segmented Control: 1:1, 16:9, 9:16 -->
        <div class="flex items-center bg-surface-container p-1 rounded-xl">
          <button type="button" onclick="setStudioRatio('1:1')" id="st-ratio-1:1" class="px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all">1:1 Square</button>
          <button type="button" onclick="setStudioRatio('16:9')" id="st-ratio-16:9" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">16:9 Wide</button>
          <button type="button" onclick="setStudioRatio('9:16')" id="st-ratio-9:16" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all">9:16 Story</button>
        </div>

        <!-- Fit Mode Toggle + Adjust Plate Cover Toggle -->
        <div class="flex flex-wrap items-center gap-2">
          <div class="flex items-center bg-surface-container p-1 rounded-xl">
            <button type="button" onclick="setStudioFitMode('fit')" id="st-fit-fit" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[16px]">fit_screen</span>
              <span>Fit (Blur BG)</span>
            </button>
            <button type="button" onclick="setStudioFitMode('fill')" id="st-fit-fill" class="px-3 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[16px]">aspect_ratio</span>
              <span>Fill (Crop)</span>
            </button>
          </div>

          <button type="button" onclick="togglePlateAdjustMode()" id="btn-toggle-plate-adjust"
                  class="px-3.5 py-2 rounded-xl text-xs font-bold border border-primary/30 bg-primary-fixed/40 text-primary hover:bg-primary hover:text-white transition-all flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[16px]">transform</span>
            <span id="lbl-toggle-plate-adjust">Adjust Plate Cover</span>
          </button>
        </div>
      </div>

      <!-- Canvas Preview Stage (switches between Framed Preview and Interactive 4-Corner Plate Calibration) -->
      <div class="apple-card-white rounded-[28px] p-4 sm:p-8 flex flex-col items-center justify-center min-h-[380px] sm:min-h-[480px] relative overflow-hidden bg-surface-container-low">
        <!-- Standard Framed Preview -->
        <div id="studio-canvas-wrapper"
             onmousedown="startCanvasPan(event)"
             onmousemove="moveCanvasPan(event)"
             onmouseup="endCanvasPan()"
             onmouseleave="endCanvasPan()"
             ontouchstart="startCanvasPan(event)"
             ontouchmove="moveCanvasPan(event)"
             ontouchend="endCanvasPan()"
             class="relative rounded-2xl overflow-hidden shadow-apple-float transition-all select-none cursor-grab active:cursor-grabbing bg-white flex items-center justify-center max-h-[440px]">
          <img id="studio-preview-img" src="/api/frame-render?ratio=1:1&fit_mode=fit&template_style=clean_white" alt="Frame Studio Preview" class="max-h-[420px] w-auto object-contain pointer-events-none"/>
          <div id="studio-pan-hint" class="hidden absolute top-3 left-1/2 -translate-x-1/2 apple-glass px-3.5 py-1 rounded-full text-[11px] font-semibold text-on-surface shadow-sm border border-white/50 flex items-center gap-1.5">
            <span class="material-symbols-outlined text-[14px] text-primary">open_with</span>
            <span>Drag photo to reposition crop</span>
          </div>
        </div>

        <!-- Interactive Plate Cover Calibration Stage (Move & Drag 4 Corners over Original Photo) -->
        <div id="plate-adjust-stage" class="hidden w-full flex flex-col items-center space-y-3">
          <div class="w-full flex flex-wrap items-center justify-between gap-2 px-1">
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 text-[11px] font-bold flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">pan_tool_alt</span>
                <span>Drag plate cover to move • Drag 4 corners to match angle</span>
              </span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" onclick="resetPlateQuadToAuto()" class="px-3 py-1.5 rounded-full bg-white border border-outline-variant/40 text-xs font-semibold text-on-surface-variant hover:text-on-surface">
                Auto-Detect Reset
              </button>
              <button type="button" onclick="removePlateCoverAction()" class="px-3 py-1.5 rounded-full bg-amber-500/15 hover:bg-amber-500 hover:text-white text-amber-900 border border-amber-500/30 text-xs font-bold transition-all flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">visibility_off</span>
                <span id="stage-remove-cover-btn-label">Remove Plate Cover</span>
              </button>
              <button type="button" onclick="togglePlateAdjustMode(false)" class="px-3.5 py-1.5 rounded-full bg-primary text-white text-xs font-semibold flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">visibility</span>
                <span>Preview in Frame</span>
              </button>
              <button type="button" onclick="approveOrSaveCurrentStudioPhoto()" class="px-4 py-1.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm flex items-center gap-1">
                <span class="material-symbols-outlined text-[14px]">verified</span>
                <span id="stage-approve-btn-label">Approve &amp; Save</span>
              </button>
            </div>
          </div>

          <div id="plate-calib-container"
               onmousemove="onPlateCalibMove(event)"
               onmouseup="onPlateCalibUp()"
               onmouseleave="onPlateCalibUp()"
               ontouchmove="onPlateCalibMove(event)"
               ontouchend="onPlateCalibUp()"
               class="relative inline-block rounded-2xl overflow-hidden shadow-apple-float border border-outline-variant/40 bg-black select-none max-h-[420px]">
            <img id="plate-calib-orig-img" src="" alt="Original Vehicle" class="max-h-[420px] w-auto block pointer-events-none select-none"/>

            <!-- SVG Polygon, Live Plate Cover Preview & Draggable Handles Overlay -->
            <svg id="plate-calib-svg" viewBox="0 0 100 100" preserveAspectRatio="none"
                 class="absolute inset-0 w-full h-full overflow-visible">
              <polygon id="plate-calib-poly" points="36,62 64,62 64,74 36,74"
                       onmousedown="startPlateBoxDrag(event)"
                       ontouchstart="startPlateBoxDrag(event)"
                       fill="rgba(0, 88, 188, 0.32)" stroke="#ffffff" stroke-width="0.7"
                       class="cursor-move"/>
              <image id="plate-calib-cover-img" href="/media/plate-overlay"
                     x="36" y="62" width="28" height="12"
                     preserveAspectRatio="none" pointer-events="none" opacity="0.92"/>
            </svg>

            <!-- 4 Corner Drag Handles (TL, TR, BR, BL) + Center Move Handle -->
            <div id="handle-corner-0" onmousedown="startCornerDrag(0, event)" ontouchstart="startCornerDrag(0, event)"
                 class="absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full bg-white border-2 border-primary shadow-md cursor-nwse-resize z-20 flex items-center justify-center" title="Drag Top-Left Corner">
              <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
            </div>
            <div id="handle-corner-1" onmousedown="startCornerDrag(1, event)" ontouchstart="startCornerDrag(1, event)"
                 class="absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full bg-white border-2 border-primary shadow-md cursor-nesw-resize z-20 flex items-center justify-center" title="Drag Top-Right Corner">
              <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
            </div>
            <div id="handle-corner-2" onmousedown="startCornerDrag(2, event)" ontouchstart="startCornerDrag(2, event)"
                 class="absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full bg-white border-2 border-primary shadow-md cursor-nwse-resize z-20 flex items-center justify-center" title="Drag Bottom-Right Corner">
              <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
            </div>
            <div id="handle-corner-3" onmousedown="startCornerDrag(3, event)" ontouchstart="startCornerDrag(3, event)"
                 class="absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full bg-white border-2 border-primary shadow-md cursor-nesw-resize z-20 flex items-center justify-center" title="Drag Bottom-Left Corner">
              <div class="w-1.5 h-1.5 rounded-full bg-primary"></div>
            </div>
            <div id="handle-plate-center" onmousedown="startPlateBoxDrag(event)" ontouchstart="startPlateBoxDrag(event)"
                 class="absolute w-7 h-7 -ml-3.5 -mt-3.5 rounded-full bg-primary text-white border-2 border-white shadow-md cursor-move z-10 flex items-center justify-center" title="Drag to move entire plate cover">
              <span class="material-symbols-outlined text-[14px]">open_with</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Apple-style Template Row below Canvas: Clean White, Soft Grey, Minimal Border, Rounded Card, Glass Overlay -->
      <div class="apple-card-white rounded-[24px] p-5">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Apple Studio Templates</span>
          <span id="studio-active-template-label" class="text-xs font-semibold text-primary">Clean White</span>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <button type="button" onclick="setStudioTemplate('clean_white')" id="tpl-clean_white" class="p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all">
            <div class="h-12 rounded-xl bg-white border border-outline-variant/40 mb-2 flex items-end p-1.5 shadow-sm">
              <div class="w-full h-2 rounded bg-surface-container-high"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Clean White</p>
            <p class="text-[10px] text-on-surface-variant">Pure gallery card</p>
          </button>

          <button type="button" onclick="setStudioTemplate('soft_grey')" id="tpl-soft_grey" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-[#e4e2e4] border border-outline-variant/40 mb-2 flex items-end p-1.5">
              <div class="w-full h-2 rounded bg-white"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Soft Grey</p>
            <p class="text-[10px] text-on-surface-variant">Warm ambient matte</p>
          </button>

          <button type="button" onclick="setStudioTemplate('minimal_border')" id="tpl-minimal_border" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-white border-2 border-on-surface mb-2 flex items-center justify-center p-1.5">
              <div class="w-full h-full border border-outline-variant/60 rounded-sm"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Minimal Border</p>
            <p class="text-[10px] text-on-surface-variant">Crisp keyline inset</p>
          </button>

          <button type="button" onclick="setStudioTemplate('rounded_card')" id="tpl-rounded_card" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-surface-container-high p-2 mb-2 flex items-center justify-center">
              <div class="w-full h-full rounded-xl bg-white shadow-sm"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Rounded Card</p>
            <p class="text-[10px] text-on-surface-variant">iOS floating radius</p>
          </button>

          <button type="button" onclick="setStudioTemplate('glass_overlay')" id="tpl-glass_overlay" class="p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all">
            <div class="h-12 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 mb-2 flex items-end p-1.5">
              <div class="w-full h-3 rounded-lg bg-white/80 backdrop-blur-sm border border-white"></div>
            </div>
            <p class="text-xs font-bold text-on-surface">Glass Overlay</p>
            <p class="text-[10px] text-on-surface-variant">Frosted caption bar</p>
          </button>
        </div>
      </div>
    </div>

    <!-- Right Column: Plate Cover Upload + Photo Angle Selector + Optional Caption + Save Preset -->
    <div class="lg:col-span-4 space-y-6">
      <div class="apple-card-white rounded-[24px] p-6 space-y-5">
        <!-- Custom Plate Cover Image Upload -->
        <div class="space-y-3 pb-4 border-b border-surface-container">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-on-surface">Plate Cover Template</h4>
              <p class="text-[11px] text-on-surface-variant">Upload the graphic/logo used to cover license plates</p>
            </div>
            <span id="overlay-status-badge" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary-fixed text-primary">Active</span>
          </div>

          <input id="plate-overlay-file-input" type="file" accept=".png,.jpg,.jpeg,.webp,image/*" class="hidden" onchange="uploadCustomPlateOverlay(this.files)"/>

          <div class="flex items-center gap-3 bg-surface-container-low p-3 rounded-2xl border border-outline-variant/30">
            <div class="w-24 h-12 rounded-xl bg-white border border-outline-variant/40 flex items-center justify-center overflow-hidden shrink-0 p-1 shadow-xs">
              <img id="plate-overlay-preview-img" src="/media/plate-overlay" alt="Plate Cover" class="max-h-full max-w-full object-contain"/>
            </div>
            <div class="flex-1 flex flex-col gap-1.5">
              <button type="button" onclick="document.getElementById('plate-overlay-file-input').click()"
                      class="w-full py-1.5 px-3 rounded-xl bg-primary text-white text-xs font-semibold hover:opacity-95 transition-all flex items-center justify-center gap-1">
                <span class="material-symbols-outlined text-[15px]">upload</span>
                <span>Upload Plate Cover</span>
              </button>
              <button type="button" onclick="resetCustomPlateOverlay()"
                      class="w-full py-1 px-3 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-[11px] font-semibold transition-all">
                Reset to Default
              </button>
            </div>
          </div>
          <p id="overlay-upload-feedback" class="text-[11px] text-emerald-700 font-medium hidden"></p>
        </div>

        <!-- Angle / Photo Queue for Selected Car (Supports Multi-Select for Batch Approval & Remove Plate Cover) -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <label class="block text-xs font-bold uppercase tracking-wider text-on-surface-variant">Preview Photo</label>
              <span id="studio-selection-count-badge" class="hidden px-2 py-0.5 rounded-full text-[10px] font-bold bg-primary text-white">0 selected</span>
            </div>
            <span id="studio-photo-status-badge" class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">Approved</span>
          </div>

          <!-- Multi-Select Quick Controls -->
          <div class="flex flex-wrap items-center justify-between gap-1.5 bg-surface-container-low px-2.5 py-1.5 rounded-xl border border-outline-variant/30">
            <span class="text-[10px] font-semibold text-on-surface-variant">Check photos for batch actions:</span>
            <div class="flex items-center gap-1">
              <button type="button" onclick="studioSelectAllPhotos()" class="px-2 py-0.5 rounded-md bg-white hover:bg-primary hover:text-white text-[10px] font-bold text-on-surface border border-outline-variant/40 transition-colors">
                Select All
              </button>
              <button type="button" onclick="studioSelectReviewPhotos()" id="btn-studio-select-review" class="px-2 py-0.5 rounded-md bg-amber-50 hover:bg-amber-500 hover:text-white text-[10px] font-bold text-amber-900 border border-amber-300/60 transition-colors">
                Needs Review
              </button>
              <button type="button" onclick="studioClearPhotoSelection()" id="btn-studio-clear-sel" class="hidden px-2 py-0.5 rounded-md bg-surface-container hover:bg-surface-container-high text-[10px] font-semibold text-on-surface-variant transition-colors">
                Clear
              </button>
            </div>
          </div>

          <div id="frame-photo-strip" class="grid grid-cols-4 gap-2 max-h-48 overflow-y-auto p-1">
            <!-- Populated by JS -->
          </div>
        </div>

        <!-- Photo Review & Plate Cover Position Actions -->
        <div class="pt-3 border-t border-surface-container space-y-2.5">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-on-surface">Plate Cover Position &amp; Review</h4>
              <p id="studio-current-photo-name" class="text-[11px] text-on-surface-variant">Drag plate cover over photo to fix tilt or placement</p>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <div class="grid grid-cols-2 gap-2">
              <button type="button" onclick="togglePlateAdjustMode()" id="btn-sidebar-adjust-plate"
                      class="py-2.5 px-3 rounded-xl border border-primary/30 bg-primary-fixed/40 hover:bg-primary hover:text-white text-primary font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
                <span class="material-symbols-outlined text-[16px]">open_with</span>
                <span id="lbl-sidebar-adjust-plate">Adjust Plate Cover</span>
              </button>
              <button type="button" onclick="removePlateCoverAction()" id="btn-remove-plate-cover"
                      class="py-2.5 px-3 rounded-xl border border-amber-500/40 bg-amber-50 hover:bg-amber-500 hover:text-white text-amber-900 font-semibold text-xs transition-all flex items-center justify-center gap-1.5"
                      title="Remove plate cover from selected photo(s) (e.g. interior or side shots without plates)">
                <span class="material-symbols-outlined text-[16px]">visibility_off</span>
                <span id="lbl-remove-plate-cover">Remove Plate Cover</span>
              </button>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" onclick="approveOrSaveCurrentStudioPhoto()" id="btn-studio-approve-save"
                      class="flex-1 py-3 px-4 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-1.5">
                <span class="material-symbols-outlined text-[17px]">verified</span>
                <span id="lbl-studio-approve-save">Approve &amp; Save Photo to Gallery</span>
              </button>
              <button type="button" onclick="rejectCurrentStudioPhoto()" id="btn-studio-reject"
                      class="hidden py-3 px-3.5 rounded-2xl bg-error-container hover:bg-error hover:text-white text-error font-bold text-xs transition-all flex items-center justify-center gap-1" title="Reject this review photo">
                <span class="material-symbols-outlined text-[16px]">block</span>
                <span>Reject</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Optional Small Caption Area (Car Model, Price) -->
        <div class="pt-4 border-t border-surface-container space-y-3">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-bold text-on-surface">Showroom Caption</h4>
              <p class="text-[11px] text-on-surface-variant">Optional car model &amp; price badge</p>
            </div>
            <input id="studio-caption-toggle" type="checkbox" checked onchange="saveGlobalFramePreset(true)"
                   class="w-5 h-5 rounded-md text-primary focus:ring-primary border-outline-variant"/>
          </div>

          <div id="studio-caption-inputs" class="space-y-2.5">
            <div>
              <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Car Model</label>
              <input id="studio-model-input" type="text" value="2023 Porsche 911 GT3" oninput="debouncedRefreshStudio()"
                     class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs font-semibold text-on-surface"/>
            </div>
            <div class="grid grid-cols-2 gap-2.5">
              <div>
                <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Price</label>
                <input id="studio-price-input" type="text" value="$248,900" oninput="debouncedRefreshStudio()"
                       class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs font-bold text-primary"/>
              </div>
              <div>
                <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Subtitle / Specs</label>
                <input id="studio-specs-input" type="text" value="4,200 mi • PDK" oninput="debouncedRefreshStudio()"
                       class="w-full bg-surface-container-low border border-outline-variant/40 rounded-xl px-3.5 py-2 text-xs text-on-surface"/>
              </div>
            </div>
          </div>
        </div>

        <!-- Primary Action Buttons: Apply Frame Config to All Uploads & Export -->
        <div class="pt-3 border-t border-surface-container space-y-2.5">
          <button type="button" onclick="saveGlobalFramePreset(false)" id="btn-save-frame-preset"
                  class="w-full py-3 rounded-2xl bg-gradient-to-b from-primary-container to-primary text-white font-semibold text-xs shadow-lg shadow-primary/20 hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-2">
            <span class="material-symbols-outlined text-[18px]">check_circle</span>
            <span>Save as Default Upload Frame</span>
          </button>
          <div class="grid grid-cols-2 gap-2.5">
            <button type="button" onclick="saveStudioFrameToGallery(false)" id="btn-save-frame-gallery"
                    class="py-2.5 rounded-2xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
              <span class="material-symbols-outlined text-[17px] text-primary">bookmark_add</span>
              <span>Save Copy</span>
            </button>
            <button type="button" onclick="exportStudioFrame()"
                    class="py-2.5 rounded-2xl bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-semibold text-xs transition-all flex items-center justify-center gap-1.5">
              <span class="material-symbols-outlined text-[17px] text-primary">ios_share</span>
              <span>Export JPG</span>
            </button>
          </div>
          <p id="studio-save-feedback" class="text-[11px] text-center text-emerald-700 font-medium hidden"></p>
        </div>
      </div>
    </div>
  </div>
</main>

<!-- ========================================================================= -->
<!-- SCREEN 4: PROFILE & DEALERSHIP SETTINGS                                   -->
<!-- ========================================================================= -->
<main id="screen-profile" class="hidden max-w-7xl mx-auto px-4 sm:px-8 pt-6 sm:pt-10">

  <!-- AUTHENTICATED PROFILE DASHBOARD (Shown once signed in) -->
  <div id="profile-dashboard-view">
    <div class="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl sm:text-4xl font-bold tracking-tight text-on-surface">Profile &amp; Dealership Settings</h1>
        <p class="text-sm sm:text-base text-on-surface-variant mt-1">Manage your dealership brand logo, watermark defaults, and account security.</p>
      </div>
      <div class="flex items-center gap-2.5">
        <span id="profile-signed-in-pill" class="px-3.5 py-1.5 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold flex items-center gap-1.5 border border-emerald-200/60">
          <span class="material-symbols-outlined text-[15px] material-fill">verified_user</span>
          <span id="profile-signed-in-email">user@forestwheel.com</span>
        </span>
        <button type="button" onclick="logoutProfileAccount()"
                class="px-3.5 py-1.5 rounded-full bg-surface-container hover:bg-error-container/60 text-on-surface-variant hover:text-error text-xs font-semibold transition-all flex items-center gap-1">
          <span class="material-symbols-outlined text-[16px]">logout</span>
          <span>Sign Out</span>
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
      <!-- Left Column: Brand Logo + Dealership Identity -->
      <div class="lg:col-span-7 space-y-6">
        <!-- Card 1: Dealership Brand Logo & Watermark -->
        <div class="apple-card-white rounded-[24px] p-6 sm:p-8 space-y-5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-primary-fixed text-primary flex items-center justify-center">
                <span class="material-symbols-outlined text-[20px]">verified</span>
              </div>
              <div>
                <h2 class="text-base font-bold text-on-surface">Dealership Brand Logo</h2>
                <p class="text-xs text-on-surface-variant">Displayed in the top navigation bar and optional frame watermark badge.</p>
              </div>
            </div>
            <span id="profile-logo-custom-badge" class="hidden text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700">Custom Logo Active</span>
          </div>

          <input id="profile-logo-file-input" type="file" accept=".png,.jpg,.jpeg,.webp,image/*" class="hidden" onchange="uploadBrandLogo(this.files)"/>

          <div class="flex flex-col sm:flex-row items-center gap-5 p-4 rounded-2xl bg-surface border border-outline-variant/30">
            <!-- Checkered Preview Box -->
            <div class="w-32 h-24 rounded-xl bg-white border border-outline-variant/40 flex items-center justify-center p-3 shadow-inner shrink-0">
              <img id="profile-logo-preview-img" src="/media/brand-logo" alt="Dealership Logo Preview" class="max-h-full max-w-full object-contain"/>
            </div>
            <div class="flex-1 space-y-3 text-center sm:text-left">
              <p class="text-xs text-on-surface-variant">Recommended: Transparent PNG or WebP (at least 300×120 px). Automatically scaled for header &amp; frame watermark.</p>
              <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2.5">
                <button type="button" onclick="document.getElementById('profile-logo-file-input').click()"
                        class="px-4 py-2 rounded-xl bg-primary hover:bg-primary-container text-white text-xs font-semibold shadow-sm transition-all flex items-center gap-1.5">
                  <span class="material-symbols-outlined text-[16px]">upload</span>
                  <span>Upload Logo</span>
                </button>
                <button type="button" onclick="resetBrandLogo()"
                        class="px-3.5 py-2 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-xs font-semibold transition-all flex items-center gap-1">
                  <span class="material-symbols-outlined text-[16px]">restart_alt</span>
                  <span>Reset to Default</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Show Watermark Toggle -->
          <label class="flex items-center justify-between p-4 rounded-2xl bg-surface border border-outline-variant/25 cursor-pointer hover:border-primary/40 transition-all">
            <div class="pr-4">
              <span class="text-sm font-semibold text-on-surface block">Show Logo Badge on Framed Photos</span>
              <span class="text-xs text-on-surface-variant">Automatically places a clean frosted dealership logo badge in the top-right corner of exported &amp; processed photos.</span>
            </div>
            <input id="profile-watermark-toggle" type="checkbox" onchange="saveProfileSettings()" class="w-5 h-5 rounded text-primary focus:ring-primary"/>
          </label>
        </div>

        <!-- Card 2: Dealership Identity & Listing Defaults -->
        <div class="apple-card-white rounded-[24px] p-6 sm:p-8 space-y-5">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-primary-fixed text-primary flex items-center justify-center">
              <span class="material-symbols-outlined text-[20px]">storefront</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-on-surface">Dealership Identity &amp; Defaults</h2>
              <p class="text-xs text-on-surface-variant">Customize your workspace title and default listing caption specs.</p>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1.5">Dealership / Brand Name</label>
              <input id="profile-dealer-name" type="text" placeholder="Forest Wheel"
                     class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm font-semibold text-on-surface focus:outline-none focus:border-primary"/>
            </div>
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1.5">Header Tagline Badge</label>
              <input id="profile-dealer-tagline" type="text" placeholder="Plate Studio"
                     class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
            </div>
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="sm:col-span-2">
              <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1.5">Default Subtitle / Specs Text</label>
              <input id="profile-default-specs" type="text" placeholder="e.g. Certified Pre-Owned • Low Mileage"
                     class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
            </div>
            <div>
              <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1.5">Currency Prefix</label>
              <input id="profile-currency-prefix" type="text" placeholder="S$"
                     class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm font-semibold text-on-surface focus:outline-none focus:border-primary"/>
            </div>
          </div>

          <div class="pt-1 flex items-center justify-between gap-4">
            <p id="profile-brand-feedback" class="text-xs font-semibold text-emerald-700 hidden"></p>
            <button type="button" onclick="saveProfileSettings()"
                    class="ml-auto px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-container text-white font-semibold text-xs shadow-sm transition-all flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[17px]">save</span>
              <span>Save Brand Settings</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Right Column: Account & Password Menu + Workspace Overview -->
      <div class="lg:col-span-5 space-y-6">
        <!-- Card 3: Account & Password Setup (Menu style, SQLite-backed, Google Link, Sessions & Audit Log) -->
        <div class="apple-card-white rounded-[24px] p-6 sm:p-8 space-y-5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <div class="w-9 h-9 rounded-xl bg-primary-fixed text-primary flex items-center justify-center">
                <span class="material-symbols-outlined text-[20px]">shield_lock</span>
              </div>
              <div>
                <h2 class="text-base font-bold text-on-surface">Account &amp; Password Setup</h2>
                <p class="text-xs text-on-surface-variant">SQLite account security, Google link &amp; sessions.</p>
              </div>
            </div>
            <span id="profile-acct-id-badge" class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-surface-container text-on-surface-variant">
              DB #1
            </span>
          </div>

          <!-- Signed-in Email Summary Row -->
          <div class="p-4 rounded-2xl bg-surface border border-outline-variant/30 space-y-3">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-3 min-w-0">
                <div class="w-9 h-9 rounded-full bg-primary-fixed/80 text-primary flex items-center justify-center font-bold text-xs shrink-0" id="profile-acct-avatar">
                  U
                </div>
                <div class="min-w-0">
                  <span class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider block">Primary Account Email</span>
                  <span id="profile-acct-email-display" class="text-sm font-bold text-on-surface truncate block">user@forestwheel.com</span>
                </div>
              </div>
              <span id="profile-acct-provider-badge" class="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-primary-fixed text-primary shrink-0">
                Email
              </span>
            </div>

            <!-- Linked Google Account Status Bar -->
            <div class="pt-2.5 border-t border-outline-variant/25 flex items-center justify-between gap-2 text-xs">
              <div class="flex items-center gap-2 min-w-0">
                <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" aria-hidden="true">
                  <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.2 1.3-1.6 3.8-5.5 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 6.6 2.2 2.2 6.6 2.2 12S6.6 21.8 12 21.8c6.9 0 9.6-4.8 9.6-7.3 0-.5-.1-.9-.1-1.3H12z"/>
                  <path fill="#34A853" d="M3.3 7.3l3.2 2.4C7.4 7.5 9.5 5.9 12 5.9c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 8.2 2.2 4.9 4.3 3.3 7.3z"/>
                  <path fill="#FBBC05" d="M12 21.8c2.6 0 4.8-.9 6.4-2.4l-3-2.5c-.8.6-1.9 1-3.4 1-2.5 0-4.7-1.7-5.5-4.1l-3.2 2.5c1.6 3.2 4.9 5.5 8.7 5.5z"/>
                  <path fill="#4285F4" d="M21.6 14.5c.1-.5.2-1.1.2-1.8 0-.6-.1-1.2-.2-1.7H12v3.9h5.5c-.3 1.3-1.1 2.4-2.1 3.1l3 2.5c1.8-1.6 3.2-4 3.2-6z"/>
                </svg>
                <span id="profile-google-link-status" class="text-on-surface-variant truncate">Google not linked</span>
              </div>
              <button type="button" id="btn-google-link-action" onclick="handleGoogleLinkAction()"
                      class="text-xs font-bold text-primary hover:underline shrink-0">
                Link Google
              </button>
            </div>
          </div>

          <!-- Menu Options List (Opens Dedicated Modals) -->
          <div class="rounded-2xl bg-surface border border-outline-variant/30 divide-y divide-outline-variant/25 overflow-hidden">
            <button type="button" onclick="openChangePasswordModal()"
                    class="w-full px-4 py-3.5 hover:bg-surface-container/70 transition-all flex items-center justify-between text-left group">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-xl bg-white border border-outline-variant/30 flex items-center justify-center text-primary shadow-2xs">
                  <span class="material-symbols-outlined text-[18px]">key</span>
                </div>
                <div>
                  <span class="text-sm font-semibold text-on-surface block">Change Password</span>
                  <span class="text-[11px] text-on-surface-variant">Update your PBKDF2-SHA256 account password</span>
                </div>
              </div>
              <span class="material-symbols-outlined text-[20px] text-outline group-hover:text-on-surface group-hover:translate-x-0.5 transition-all">chevron_right</span>
            </button>

            <button type="button" onclick="openGoogleLoginModal(true)"
                    class="w-full px-4 py-3.5 hover:bg-surface-container/70 transition-all flex items-center justify-between text-left group">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-xl bg-white border border-outline-variant/30 flex items-center justify-center text-primary shadow-2xs">
                  <span class="material-symbols-outlined text-[18px]">add_link</span>
                </div>
                <div>
                  <span class="text-sm font-semibold text-on-surface block">Google OAuth &amp; Email Link</span>
                  <span class="text-[11px] text-on-surface-variant">Link Google email or configure OAuth Client ID</span>
                </div>
              </div>
              <span class="material-symbols-outlined text-[20px] text-outline group-hover:text-on-surface group-hover:translate-x-0.5 transition-all">chevron_right</span>
            </button>

            <button type="button" onclick="openSecuritySessionsModal()"
                    class="w-full px-4 py-3.5 hover:bg-surface-container/70 transition-all flex items-center justify-between text-left group">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-xl bg-white border border-outline-variant/30 flex items-center justify-center text-primary shadow-2xs">
                  <span class="material-symbols-outlined text-[18px]">devices</span>
                </div>
                <div>
                  <span class="text-sm font-semibold text-on-surface block">Active Sessions &amp; Security Log</span>
                  <span class="text-[11px] text-on-surface-variant">Inspect SQLite sessions and login audit trail</span>
                </div>
              </div>
              <span class="material-symbols-outlined text-[20px] text-outline group-hover:text-on-surface group-hover:translate-x-0.5 transition-all">chevron_right</span>
            </button>

            <button type="button" onclick="logoutProfileAccount()"
                    class="w-full px-4 py-3.5 hover:bg-error-container/30 transition-all flex items-center justify-between text-left group">
              <div class="flex items-center gap-3">
                <div class="w-8 h-8 rounded-xl bg-white border border-outline-variant/30 flex items-center justify-center text-error shadow-2xs">
                  <span class="material-symbols-outlined text-[18px]">logout</span>
                </div>
                <div>
                  <span class="text-sm font-semibold text-error block">Sign Out</span>
                  <span class="text-[11px] text-on-surface-variant">Revoke session cookie and return to sign-in</span>
                </div>
              </div>
              <span class="material-symbols-outlined text-[20px] text-outline group-hover:text-error transition-all">chevron_right</span>
            </button>
          </div>

          <p id="profile-cred-feedback" class="text-xs font-semibold hidden"></p>
        </div>

        <!-- Card 4: Workspace Overview -->
        <div class="apple-card-white rounded-[24px] p-6 sm:p-8 space-y-4">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-xl bg-surface-container text-on-surface-variant flex items-center justify-center">
              <span class="material-symbols-outlined text-[20px]">analytics</span>
            </div>
            <div>
              <h2 class="text-base font-bold text-on-surface">Workspace Overview</h2>
              <p class="text-xs text-on-surface-variant">Live inventory &amp; template summary.</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div class="p-3.5 rounded-2xl bg-surface border border-outline-variant/25">
              <span class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider block">Car Groups</span>
              <span id="stat-total-cars" class="text-2xl font-bold text-on-surface mt-0.5 block">0</span>
            </div>
            <div class="p-3.5 rounded-2xl bg-surface border border-outline-variant/25">
              <span class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider block">Ready Photos</span>
              <span id="stat-ready-photos" class="text-2xl font-bold text-emerald-600 mt-0.5 block">0</span>
            </div>
            <div class="p-3.5 rounded-2xl bg-surface border border-outline-variant/25">
              <span class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider block">Needs Review</span>
              <span id="stat-review-photos" class="text-2xl font-bold text-amber-600 mt-0.5 block">0</span>
            </div>
            <div class="p-3.5 rounded-2xl bg-surface border border-outline-variant/25">
              <span class="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider block">Active Frame</span>
              <span id="stat-active-preset" class="text-sm font-bold text-primary mt-1.5 block truncate">1:1 • Fit</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</main>

<!-- ========================================================================= -->
<!-- CHANGE PASSWORD MODAL MENU                                                -->
<!-- ========================================================================= -->
<div id="change-password-modal" class="fixed inset-0 z-50 hidden bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
  <div class="bg-white rounded-[28px] max-w-md w-full p-6 sm:p-7 space-y-5 shadow-apple-float border border-outline-variant/30">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-xl bg-primary-fixed text-primary flex items-center justify-center">
          <span class="material-symbols-outlined text-[20px]">key</span>
        </div>
        <div>
          <h3 class="text-base font-bold text-on-surface">Change Password</h3>
          <p class="text-xs text-on-surface-variant">Enter your current and new password below.</p>
        </div>
      </div>
      <button type="button" onclick="closeChangePasswordModal()" class="w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>

    <div class="space-y-3.5">
      <div>
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Current Password <span class="text-error">*</span></label>
        <input id="profile-current-password" type="password" autocomplete="current-password" placeholder="Enter current password"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>

      <div>
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">New Password <span class="text-error">*</span></label>
        <input id="profile-new-password" type="password" autocomplete="new-password" placeholder="Minimum 4 characters"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>

      <div>
        <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Confirm New Password <span class="text-error">*</span></label>
        <input id="profile-confirm-password" type="password" autocomplete="new-password" placeholder="Re-enter new password"
               onkeydown="if(event.key==='Enter') saveProfileCredentials();"
               class="w-full px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
      </div>
    </div>

    <p id="modal-password-feedback" class="text-xs font-semibold hidden"></p>

    <div class="flex items-center justify-end gap-2.5 pt-2">
      <button type="button" onclick="closeChangePasswordModal()"
              class="px-4 py-2.5 rounded-xl bg-surface-container hover:bg-surface-container-high text-on-surface-variant text-xs font-semibold transition-all">
        Cancel
      </button>
      <button type="button" onclick="saveProfileCredentials()"
              class="px-5 py-2.5 rounded-xl bg-primary hover:bg-primary-container text-white text-xs font-semibold shadow-sm transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[16px]">check</span>
        <span>Update Password</span>
      </button>
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- GOOGLE OAUTH 2.0 & EMAIL CONNECTION MODAL                                 -->
<!-- ========================================================================= -->
<div id="google-login-modal" class="fixed inset-0 z-50 hidden bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
  <div class="bg-white rounded-[28px] max-w-lg w-full p-6 sm:p-7 space-y-5 shadow-apple-float border border-outline-variant/30 max-h-[90vh] overflow-y-auto">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-xl bg-surface border border-outline-variant/40 flex items-center justify-center">
          <svg class="w-5 h-5" viewBox="0 0 24 24" aria-hidden="true">
            <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.2 1.3-1.6 3.8-5.5 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 6.6 2.2 2.2 6.6 2.2 12S6.6 21.8 12 21.8c6.9 0 9.6-4.8 9.6-7.3 0-.5-.1-.9-.1-1.3H12z"/>
            <path fill="#34A853" d="M3.3 7.3l3.2 2.4C7.4 7.5 9.5 5.9 12 5.9c1.9 0 3.2.8 3.9 1.5l2.7-2.6C16.9 3.2 14.7 2.2 12 2.2 8.2 2.2 4.9 4.3 3.3 7.3z"/>
            <path fill="#FBBC05" d="M12 21.8c2.6 0 4.8-.9 6.4-2.4l-3-2.5c-.8.6-1.9 1-3.4 1-2.5 0-4.7-1.7-5.5-4.1l-3.2 2.5c1.6 3.2 4.9 5.5 8.7 5.5z"/>
            <path fill="#4285F4" d="M21.6 14.5c.1-.5.2-1.1.2-1.8 0-.6-.1-1.2-.2-1.7H12v3.9h5.5c-.3 1.3-1.1 2.4-2.1 3.1l3 2.5c1.8-1.6 3.2-4 3.2-6z"/>
          </svg>
        </div>
        <div>
          <h3 id="google-modal-title" class="text-base font-bold text-on-surface">Connect with Google</h3>
          <p id="google-modal-subtitle" class="text-xs text-on-surface-variant">Sign in or link your account with Google OAuth 2.0.</p>
        </div>
      </div>
      <button type="button" onclick="closeGoogleLoginModal()" class="w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>

    <!-- Real Google OAuth 2.0 Redirect & GIS Button Section -->
    <div id="google-oauth-live-box" class="p-4 rounded-2xl bg-primary-fixed/30 border border-primary/20 space-y-3">
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-primary flex items-center gap-1.5">
          <span class="material-symbols-outlined text-[16px]">verified</span>
          <span>Google OAuth 2.0 Verification</span>
        </span>
        <span id="google-oauth-status-pill" class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
          Client ID Not Set
        </span>
      </div>
      <div id="g_id_signin_container" class="flex justify-center"></div>
      <button type="button" id="btn-google-oauth-redirect" onclick="startGoogleOAuthRedirect()"
              class="w-full py-2.5 px-4 rounded-xl bg-white hover:bg-surface border border-outline-variant/50 text-xs font-bold text-on-surface shadow-2xs transition-all flex items-center justify-center gap-2">
        <span class="material-symbols-outlined text-[16px] text-primary">open_in_new</span>
        <span>Redirect to Google OAuth 2.0 Consent Screen</span>
      </button>
    </div>

    <!-- Direct Google Email Link / Sign-In -->
    <div class="space-y-2">
      <label class="block text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Google Email Address</label>
      <div class="flex gap-2">
        <input id="google-email-input" type="email" autocomplete="email" placeholder="yourname@gmail.com"
               onkeydown="if(event.key==='Enter') submitGoogleEmailLogin();"
               class="flex-1 px-3.5 py-2.5 rounded-xl bg-surface border border-outline-variant/40 text-sm text-on-surface focus:outline-none focus:border-primary"/>
        <button type="button" onclick="submitGoogleEmailLogin()"
                class="px-4 py-2.5 rounded-xl bg-primary hover:bg-primary-container text-white text-xs font-semibold shadow-sm transition-all shrink-0">
          Connect Email
        </button>
      </div>
    </div>

    <!-- Expandable Google Cloud OAuth 2.0 Client ID / Secret Configuration -->
    <div class="pt-2 border-t border-outline-variant/30">
      <button type="button" onclick="document.getElementById('oauth-config-drawer').classList.toggle('hidden')"
              class="w-full flex items-center justify-between text-xs font-semibold text-on-surface-variant hover:text-on-surface py-1">
        <span class="flex items-center gap-1.5">
          <span class="material-symbols-outlined text-[16px]">settings</span>
          <span>Configure Google Cloud OAuth 2.0 Client ID &amp; Secret</span>
        </span>
        <span class="material-symbols-outlined text-[18px]">expand_more</span>
      </button>

      <div id="oauth-config-drawer" class="hidden mt-3 p-4 rounded-2xl bg-surface border border-outline-variant/30 space-y-3">
        <p class="text-[11px] text-on-surface-variant leading-relaxed">
          In <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener" class="text-primary font-semibold underline">Google Cloud Console → Credentials</a>, create an <strong>OAuth 2.0 Web Client ID</strong> and add this Authorized Redirect URI:
          <code id="oauth-callback-uri-hint" class="block mt-1 px-2.5 py-1.5 rounded-lg bg-white border border-outline-variant/40 text-[11px] font-mono text-on-surface select-all">http://127.0.0.1:8000/api/auth/google/callback</code>
        </p>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Google OAuth Client ID</label>
          <input id="oauth-client-id-input" type="text" placeholder="1234567890-abc...apps.googleusercontent.com"
                 class="w-full px-3 py-2 rounded-xl bg-white border border-outline-variant/40 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-1">Google OAuth Client Secret</label>
          <input id="oauth-client-secret-input" type="password" placeholder="GOCSPX-..."
                 class="w-full px-3 py-2 rounded-xl bg-white border border-outline-variant/40 text-xs font-mono text-on-surface focus:outline-none focus:border-primary"/>
        </div>
        <div class="flex justify-end">
          <button type="button" onclick="saveGoogleOAuthConfig()"
                  class="px-4 py-2 rounded-xl bg-on-surface hover:opacity-90 text-white text-xs font-semibold transition-all">
            Save OAuth Credentials
          </button>
        </div>
      </div>
    </div>

    <p id="google-login-feedback" class="text-xs font-semibold text-error hidden"></p>
  </div>
</div>

<!-- ========================================================================= -->
<!-- ACTIVE SESSIONS & SECURITY AUDIT LOG MODAL                                -->
<!-- ========================================================================= -->
<div id="security-sessions-modal" class="fixed inset-0 z-50 hidden bg-black/40 backdrop-blur-sm flex items-center justify-center p-4">
  <div class="bg-white rounded-[28px] max-w-2xl w-full p-6 sm:p-7 space-y-5 shadow-apple-float border border-outline-variant/30 max-h-[88vh] flex flex-col">
    <div class="flex items-center justify-between shrink-0">
      <div class="flex items-center gap-2.5">
        <div class="w-9 h-9 rounded-xl bg-primary-fixed text-primary flex items-center justify-center">
          <span class="material-symbols-outlined text-[20px]">devices</span>
        </div>
        <div>
          <h3 class="text-base font-bold text-on-surface">Active Sessions &amp; Security Audit Log</h3>
          <p class="text-xs text-on-surface-variant">Live SQLite session tokens (`accounts.db`) and authentication events.</p>
        </div>
      </div>
      <button type="button" onclick="closeSecuritySessionsModal()" class="w-8 h-8 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface">
        <span class="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>

    <div class="overflow-y-auto space-y-5 pr-1">
      <!-- Active Sessions List -->
      <div class="space-y-2.5">
        <div class="flex items-center justify-between">
          <h4 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Active Login Sessions</h4>
          <button type="button" onclick="revokeOtherSessions()"
                  class="text-xs font-bold text-error hover:underline">
            Revoke Other Sessions
          </button>
        </div>
        <div id="security-sessions-list" class="space-y-2">
          <!-- Populated dynamically -->
        </div>
      </div>

      <!-- Security Audit Trail -->
      <div class="space-y-2.5">
        <h4 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">Recent Security Audit Log</h4>
        <div id="security-audit-list" class="rounded-2xl bg-surface border border-outline-variant/30 divide-y divide-outline-variant/20 overflow-hidden text-xs">
          <!-- Populated dynamically -->
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- CAR GROUP EXPANDED MODAL (ALL PHOTOS + BEFORE/AFTER TOGGLE + EDIT/DELETE) -->
<!-- ========================================================================= -->
<div id="car-detail-modal" class="fixed inset-0 z-50 hidden bg-black/35 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">
  <div class="bg-white rounded-[28px] max-w-5xl w-full max-h-[90vh] flex flex-col shadow-apple-float overflow-hidden border border-outline-variant/30">
    <!-- Modal Header -->
    <div class="px-6 py-4 border-b border-surface-container flex flex-wrap items-center justify-between gap-3 bg-surface">
      <div class="flex items-center gap-3">
        <span id="modal-car-plate-badge" class="px-3.5 py-1.5 rounded-xl bg-primary-fixed text-primary font-extrabold text-sm tracking-wider uppercase">SXX 1234 A</span>
        <div>
          <h3 id="modal-car-title" class="text-lg font-bold text-on-surface">2023 Porsche 911 GT3</h3>
          <p id="modal-car-count" class="text-xs text-on-surface-variant">0 photos</p>
        </div>
        <button type="button" onclick="toggleEditCarGroupForm()" class="p-1.5 rounded-full hover:bg-surface-container text-on-surface-variant" title="Edit plate number or car model">
          <span class="material-symbols-outlined text-[18px]">edit</span>
        </button>
      </div>

      <div class="flex items-center gap-2.5">
        <!-- Before / After Toggle inside Car Modal -->
        <div class="inline-flex items-center bg-surface-container p-1 rounded-full">
          <button type="button" onclick="setModalCompareMode('after')" id="modal-btn-after" class="px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm">Plate Removed</button>
          <button type="button" onclick="setModalCompareMode('before')" id="modal-btn-before" class="px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant">Original (Before)</button>
        </div>

        <button type="button" onclick="downloadCarZip(activeModalCarId, event)" class="px-3 py-1.5 rounded-full bg-primary-fixed hover:bg-primary hover:text-white text-primary text-xs font-semibold flex items-center gap-1 transition-colors">
          <span class="material-symbols-outlined text-[16px]">download</span>
          <span>Download ZIP</span>
        </button>

        <button type="button" onclick="openDeleteModal('car', activeModalCarId)" class="px-3 py-1.5 rounded-full bg-error-container/50 hover:bg-error-container text-error text-xs font-semibold flex items-center gap-1">
          <span class="material-symbols-outlined text-[16px]">delete</span>
          <span>Delete Group</span>
        </button>

        <button type="button" onclick="closeCarDetailModal()" class="w-9 h-9 rounded-full bg-surface-container hover:bg-surface-container-high flex items-center justify-center text-on-surface">
          <span class="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>
    </div>

    <!-- Inline Edit Car Group Drawer (Hidden by default) -->
    <div id="modal-edit-car-drawer" class="hidden px-6 py-4 bg-surface-container-low border-b border-outline-variant/30">
      <div class="grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Plate Number (Group ID)</label>
          <input id="edit-car-plate" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-bold uppercase text-on-surface"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Car Model</label>
          <input id="edit-car-model" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-semibold text-on-surface"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Subtitle / Specs</label>
          <input id="edit-car-specs" type="text" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs text-on-surface"/>
        </div>
        <div>
          <label class="block text-[11px] font-semibold text-on-surface-variant mb-1">Price (optional)</label>
          <input id="edit-car-price" type="text" placeholder="Empty = hidden" class="w-full bg-white border border-outline-variant/50 rounded-xl px-3 py-2 text-xs font-semibold text-primary"/>
        </div>
        <div class="flex gap-2">
          <button type="button" onclick="saveCarGroupMetadata()" class="flex-1 py-2 rounded-xl bg-primary text-white text-xs font-semibold">Save Changes</button>
          <button type="button" onclick="toggleEditCarGroupForm()" class="px-3 py-2 rounded-xl bg-surface-container text-xs font-semibold">Cancel</button>
        </div>
      </div>
    </div>

    <!-- All Photos Scrollable Container inside Modal -->
    <div class="flex-1 min-h-0 overflow-y-auto overscroll-contain p-5 sm:p-7">
      <div id="modal-photos-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 items-start">
        <!-- Populated by JS -->
      </div>
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- SCREEN 4: FLOATING SELECTION ACTION BAR & DELETE CONFIRMATION SHEET/MODAL -->
<!-- ========================================================================= -->
<div id="selection-floating-bar" class="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-40 hidden w-[94%] max-w-2xl">
  <div class="apple-glass bg-white/90 border border-outline-variant/40 rounded-full px-5 py-3 shadow-apple-float flex flex-wrap items-center justify-between gap-3">
    <div class="flex items-center gap-3">
      <button type="button" onclick="selectAllGalleryItems()" class="text-xs sm:text-sm font-semibold text-primary hover:underline">
        Select All
      </button>
      <span class="text-outline-variant">•</span>
      <button type="button" onclick="clearAllSelections()" class="text-xs sm:text-sm font-medium text-on-surface-variant hover:text-on-surface">
        Deselect
      </button>
      <span id="selection-counter-pill" class="px-2.5 py-0.5 rounded-full bg-primary-fixed text-primary text-xs font-bold">0 selected</span>
    </div>

    <div class="flex items-center gap-2">
      <button type="button" onclick="openDeleteModal('selected')" id="btn-floating-delete"
              class="px-5 py-2 rounded-full bg-error text-white text-xs sm:text-sm font-semibold shadow-sm hover:opacity-95 active:scale-95 transition-all flex items-center gap-1.5">
        <span class="material-symbols-outlined text-[18px]">delete</span>
        <span id="btn-floating-delete-label">Delete Selected (0)</span>
      </button>
    </div>
  </div>
</div>

<!-- Apple-Style Confirmation Bottom Sheet / Modal for Delete -->
<div id="delete-confirm-modal" class="fixed inset-0 z-50 hidden bg-black/35 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-4">
  <div class="bg-white w-full sm:max-w-md rounded-t-[28px] sm:rounded-[28px] p-6 sm:p-7 shadow-apple-sheet border border-outline-variant/30 space-y-5">
    <div class="w-10 h-1.5 bg-surface-container-highest rounded-full mx-auto sm:hidden"></div>

    <div class="flex items-start gap-4">
      <div class="w-12 h-12 rounded-2xl bg-error-container text-error flex items-center justify-center shrink-0">
        <span class="material-symbols-outlined text-2xl">delete_forever</span>
      </div>
      <div>
        <h3 id="delete-modal-title" class="text-lg font-bold text-on-surface">Confirm Deletion</h3>
        <p id="delete-modal-desc" class="text-xs sm:text-sm text-on-surface-variant mt-1">
          Choose what you want to remove from the showroom gallery.
        </p>
      </div>
    </div>

    <!-- Deletion Scope Options: Selected photos, Entire car group, or All photos -->
    <div class="space-y-2 bg-surface-container-low p-3 rounded-2xl border border-outline-variant/30">
      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="selected" checked onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-on-surface">Delete selected photos only</span>
        </div>
        <span id="del-count-selected" class="text-xs font-bold text-on-surface-variant">0 photos</span>
      </label>

      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="car" onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-on-surface">Delete entire car group</span>
        </div>
        <span id="del-count-car" class="text-xs font-bold text-on-surface-variant">1 group</span>
      </label>

      <label class="flex items-center justify-between p-2.5 rounded-xl hover:bg-white cursor-pointer transition-colors">
        <div class="flex items-center gap-2.5">
          <input type="radio" name="delete-scope-radio" value="all" onchange="updateDeleteModalSummary()" class="text-error focus:ring-error"/>
          <span class="text-xs sm:text-sm font-semibold text-error">Delete all photos in inventory</span>
        </div>
        <span id="del-count-all" class="text-xs font-bold text-error">All</span>
      </label>
    </div>

    <!-- Red Destructive Button and Cancel -->
    <div class="flex flex-col sm:flex-row gap-2.5 pt-1">
      <button type="button" onclick="closeDeleteModal()"
              class="flex-1 py-3.5 rounded-2xl bg-surface-container hover:bg-surface-container-high text-on-surface font-semibold text-sm transition-all">
        Cancel
      </button>
      <button type="button" onclick="confirmExecuteDelete()" id="btn-confirm-destructive-delete"
              class="flex-1 py-3.5 rounded-2xl bg-error hover:opacity-95 text-white font-semibold text-sm shadow-md shadow-error/20 transition-all">
        Delete Items
      </button>
    </div>
  </div>
</div>

<!-- ========================================================================= -->
<!-- MOBILE BOTTOM TAB BAR (4 TABS: UPLOAD, GALLERY, FRAMES, PROFILE)          -->
<!-- ========================================================================= -->
<nav class="md:hidden fixed bottom-0 left-0 right-0 z-40 apple-glass border-t border-outline-variant/30 px-6 py-2 flex items-center justify-around">
  <button type="button" onclick="switchTab('upload')" id="nav-mob-upload" class="flex flex-col items-center gap-0.5 py-1 text-primary font-semibold">
    <span class="material-symbols-outlined text-[24px]">cloud_upload</span>
    <span class="text-[11px]">Upload</span>
  </button>
  <button type="button" onclick="switchTab('gallery')" id="nav-mob-gallery" class="flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium">
    <span class="material-symbols-outlined text-[24px]">photo_library</span>
    <span class="text-[11px]">Gallery</span>
  </button>
  <button type="button" onclick="switchTab('frames')" id="nav-mob-frames" class="flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium">
    <span class="material-symbols-outlined text-[24px]">crop_free</span>
    <span class="text-[11px]">Frames</span>
  </button>
  <button type="button" onclick="switchTab('profile')" id="nav-mob-profile" class="flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium">
    <span class="material-symbols-outlined text-[24px]">account_circle</span>
    <span class="text-[11px]">Profile</span>
  </button>
</nav>

<script>
  // Application State
  let appState = {
    cars_output: {},
    cars_review: {},
    cars_meta: {}
  };
  let activeTab = 'upload';
  let uploadFilesQueue = [];
  let uploadRatio = '1:1';

  // Gallery & Selection State
  let galleryFilter = 'all';
  let globalCompareMode = 'after'; // 'after' (Plate Removed) or 'before' (Original)
  let cardCompareModes = {};       // per-car override: {car_id: 'after' | 'before'}
  let selectionMode = false;
  let selectedPhotoKeys = new Set(); // "car_id::filename"
  let selectedCarIds = new Set();    // "car_id"
  let activeModalCarId = null;
  let modalCompareMode = 'after';
  let pendingDeleteTargetCarId = null;

  // Frame Studio & Interactive Plate Cover Adjustment State
  let studioCarId = null;
  let studioFilename = null;
  let studioRatio = '1:1';
  let studioFitMode = 'fit'; // 'fit' (blurred photo bg) or 'fill' (crop + pan)
  let studioTemplate = 'clean_white';
  let studioOffsetX = 0.5;
  let studioOffsetY = 0.5;
  let isPanning = false;
  let panStartX = 0;
  let panStartY = 0;
  let studioDebounceTimer = null;

  // 4-Corner Plate Cover Calibration & Multi-Select State (coordinates in 0..100% of original image)
  let plateAdjustMode = false;
  let studioQuadPct = [[36, 62], [64, 62], [64, 74], [36, 74]];
  let plateQuadModified = false;
  let studioNoOverlay = false;
  let studioSelectedFilenames = new Set();
  let activeCornerIdx = -1;
  let isDraggingPlateBox = false;
  let plateDragStartPt = { x: 0, y: 0 };
  let plateDragStartQuad = null;

  const SAMPLE_PLATES = ['SXX 1234 A', 'SBA 8888 X', 'SGP 9110 T', 'SLR 4580 M', 'SKL 2026 Z'];

  const TAB_DISPLAY_NAMES = {
    upload: 'Upload & Plate Removal',
    gallery: 'Vehicle Gallery',
    frames: 'Frame Template Editor',
    profile: 'Profile & Dealership Settings'
  };

  // Switch between the 4 primary tabs: Upload, Gallery, Frames open freely (with Sample Trial when signed out); Profile opens Sign-In when signed out
  function switchTab(tab) {
    activeTab = tab;
    const isLoggedIn = Boolean(appState && appState.profile && appState.profile.is_logged_in);
    const showAuthGate = (tab === 'profile' && !isLoggedIn);

    const authView = document.getElementById('profile-auth-view');
    if (authView) authView.classList.toggle('hidden', !showAuthGate);

    const tabPill = document.getElementById('auth-target-tab-pill');
    if (tabPill) {
      tabPill.textContent = 'Profile & Dealership Workspace';
    }

    ['upload', 'gallery', 'frames', 'profile'].forEach(t => {
      const sec = document.getElementById('screen-' + t);
      if (sec) {
        if (t === 'profile') {
          sec.classList.toggle('hidden', tab !== 'profile' || !isLoggedIn);
        } else {
          sec.classList.toggle('hidden', t !== tab);
        }
      }

      const deskBtn = document.getElementById('nav-desk-' + t);
      if (deskBtn) {
        if (t === tab) {
          deskBtn.className = 'px-5 py-1.5 rounded-full text-sm font-semibold transition-all flex items-center gap-1.5 bg-white text-primary shadow-sm';
        } else {
          deskBtn.className = 'px-5 py-1.5 rounded-full text-sm font-medium text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
        }
      }

      const mobBtn = document.getElementById('nav-mob-' + t);
      if (mobBtn) {
        mobBtn.className = (t === tab)
          ? 'flex flex-col items-center gap-0.5 py-1 text-primary font-semibold'
          : 'flex flex-col items-center gap-0.5 py-1 text-on-surface-variant font-medium';
      }
    });

    if (showAuthGate) {
      document.getElementById('selection-floating-bar')?.classList.add('hidden');
      const hasAcct = Boolean(appState && appState.profile && appState.profile.has_account);
      setProfileAuthMode(hasAcct ? 'signin' : 'signup');
      return;
    }

    if (tab !== 'gallery') {
      document.getElementById('selection-floating-bar').classList.add('hidden');
    } else {
      updateSelectionBar();
      renderGallery();
    }

    if (tab === 'frames') {
      populateFrameStudioSelectors();
      refreshStudioCanvas();
    }

    if (tab === 'profile') {
      populateProfilePage();
    }
  }

  // Fetch backend state for the currently authenticated account session
  async function fetchState() {
    try {
      const res = await fetch('/api/state', { credentials: 'same-origin' });
      if (!res.ok) return;
      appState = await res.json();
      if (appState.frame_config) {
        syncUiWithFrameConfig(appState.frame_config);
      }
      if (appState.profile) {
        syncUiWithProfile(appState.profile);
      }
      updateGalleryCountBadge();
      renderGallery();
      populateFrameStudioSelectors();
      populateProfilePage();
      switchTab(activeTab);
    } catch (err) {
      console.error('Error loading state:', err);
    }
  }

  function syncUiWithFrameConfig(fcfg) {
    if (!fcfg) return;
    studioRatio = fcfg.ratio || studioRatio;
    uploadRatio = fcfg.ratio || uploadRatio;
    studioFitMode = fcfg.fit_mode || studioFitMode;
    studioTemplate = fcfg.template_style || studioTemplate;
    studioOffsetX = typeof fcfg.offset_x === 'number' ? fcfg.offset_x : studioOffsetX;
    studioOffsetY = typeof fcfg.offset_y === 'number' ? fcfg.offset_y : studioOffsetY;

    // Update Upload ratio buttons
    ['1:1', '16:9', '9:16'].forEach(r => {
      const btn = document.getElementById('up-ratio-' + r);
      if (btn) {
        btn.className = (r === uploadRatio)
          ? 'py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
      const stBtn = document.getElementById('st-ratio-' + r);
      if (stBtn) {
        stBtn.className = (r === studioRatio)
          ? 'px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
    });

    // Update Fit/Fill buttons
    const fitBtn = document.getElementById('st-fit-fit');
    const fillBtn = document.getElementById('st-fit-fill');
    if (fitBtn && fillBtn) {
      fitBtn.className = (studioFitMode === 'fit')
        ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
        : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
      fillBtn.className = (studioFitMode === 'fill')
        ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
        : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
    }

    // Update Template cards
    const tplLbl = document.getElementById('studio-active-template-label');
    if (tplLbl) tplLbl.textContent = TEMPLATE_LABELS[studioTemplate] || studioTemplate;
    Object.keys(TEMPLATE_LABELS).forEach(k => {
      const b = document.getElementById('tpl-' + k);
      if (b) {
        b.className = (k === studioTemplate)
          ? 'p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all'
          : 'p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all';
      }
    });

    const capToggle = document.getElementById('studio-caption-toggle');
    if (capToggle && typeof fcfg.caption_enabled === 'boolean') {
      capToggle.checked = fcfg.caption_enabled;
    }

    const presetPill = document.getElementById('upload-active-preset-pill');
    if (presetPill) {
      const tName = TEMPLATE_LABELS[studioTemplate] || 'Clean White';
      const fName = studioFitMode === 'fill' ? 'Fill' : 'Fit (Blur)';
      presetPill.textContent = `${tName} • ${fName} • ${studioRatio}`;
    }

    const ovBadge = document.getElementById('overlay-status-badge');
    if (ovBadge) {
      ovBadge.textContent = fcfg.has_custom_overlay ? 'Custom Cover' : 'Default Cover';
    }
  }

  function getAllCarIds() {
    const outKeys = Object.keys(appState.cars_output || {});
    const revKeys = Object.keys(appState.cars_review || {});
    return Array.from(new Set([...outKeys, ...revKeys])).sort();
  }

  function getCarPhotos(carId) {
    const outList = (appState.cars_output && appState.cars_output[carId]) || [];
    const revList = (appState.cars_review && appState.cars_review[carId]) || [];
    return [...outList, ...revList];
  }

  function getCarMeta(carId) {
    const meta = (appState.cars_meta && appState.cars_meta[carId]) || {};
    return {
      plate_display: meta.plate_display || carId.replace(/-/g, ' '),
      car_model: meta.car_model || 'Forest Wheel Showroom Vehicle',
      car_price: typeof meta.car_price === 'string' ? meta.car_price : '',
      car_specs: typeof meta.car_specs === 'string' ? meta.car_specs : 'Verified Pre-Owned • Singapore'
    };
  }

  function updateGalleryCountBadge() {
    const cids = getAllCarIds();
    const badge = document.getElementById('badge-desk-gallery');
    if (badge) badge.textContent = String(cids.length);
  }

  // =========================================================================
  // SCREEN 1: UPLOAD & PROGRESS RING LOGIC
  // =========================================================================
  function setUploadRatio(ratio) {
    uploadRatio = ratio;
    ['1:1', '16:9', '9:16'].forEach(r => {
      const btn = document.getElementById('up-ratio-' + r);
      if (!btn) return;
      btn.className = (r === ratio)
        ? 'py-2 rounded-xl text-xs font-bold bg-white text-primary shadow-sm transition-all'
        : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    });
  }

  function handleFilesSelected(fileList) {
    if (!fileList || !fileList.length) return;
    const arr = Array.from(fileList);
    arr.forEach((file, idx) => {
      const objUrl = URL.createObjectURL(file);
      uploadFilesQueue.push({
        file: file,
        name: file.name,
        previewUrl: objUrl,
        stage: 'detecting', // 'detecting' -> 'removing' -> 'ready' | 'done'
        progress: 38
      });
    });

    // Auto-fill Plate number if still default or empty
    const plateInput = document.getElementById('input-plate-number');
    if (plateInput && (!plateInput.value.trim() || plateInput.value === 'SXX 1234 A')) {
      const pick = SAMPLE_PLATES[Math.floor(Math.random() * SAMPLE_PLATES.length)];
      plateInput.value = pick;
    }

    renderUploadQueue();

    // Animate simulated plate detection pre-scan ring (Detecting plate -> Ready to remove)
    setTimeout(() => {
      uploadFilesQueue.forEach(item => {
        if (item.stage === 'detecting') {
          item.stage = 'removing';
          item.progress = 76;
        }
      });
      renderUploadQueue();
    }, 450);

    setTimeout(() => {
      uploadFilesQueue.forEach(item => {
        if (item.stage === 'removing') {
          item.stage = 'detected';
          item.progress = 100;
        }
      });
      renderUploadQueue();
    }, 950);
  }

  function clearUploadQueue() {
    uploadFilesQueue = [];
    renderUploadQueue();
  }

  function removeQueuedFile(idx) {
    uploadFilesQueue.splice(idx, 1);
    renderUploadQueue();
  }

  function renderUploadQueue() {
    const grid = document.getElementById('upload-thumbnails-grid');
    const badge = document.getElementById('upload-queue-badge');
    if (badge) badge.textContent = `${uploadFilesQueue.length} Photo${uploadFilesQueue.length === 1 ? '' : 's'}`;
    if (!grid) return;

    if (uploadFilesQueue.length === 0) {
      grid.innerHTML = `
        <div class="col-span-full apple-card-white rounded-2xl p-6 text-center text-xs text-on-surface-variant">
          No photos queued yet. Click <strong>Upload photos</strong> above to select car photos.
        </div>`;
      return;
    }

    const circumference = 2 * Math.PI * 18;
    grid.innerHTML = uploadFilesQueue.map((item, idx) => {
      const offset = circumference - (item.progress / 100) * circumference;
      let statusBadge = '';
      if (item.stage === 'detecting') {
        statusBadge = `
          <div class="apple-glass px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
            <svg class="w-5 h-5 spin-ring" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#d8e2ff" stroke-width="4"/>
              <circle cx="22" cy="22" r="18" fill="none" stroke="#0058bc" stroke-width="4" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
            </svg>
            <span class="text-[11px] font-bold text-on-surface">Detecting plate…</span>
          </div>`;
      } else if (item.stage === 'removing') {
        statusBadge = `
          <div class="apple-glass px-3 py-1.5 rounded-full flex items-center gap-2 shadow-sm">
            <svg class="w-5 h-5 spin-ring" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" fill="none" stroke="#d8e2ff" stroke-width="4"/>
              <circle cx="22" cy="22" r="18" fill="none" stroke="#0070eb" stroke-width="4" stroke-dasharray="${circumference}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
            </svg>
            <span class="text-[11px] font-bold text-primary">Removing plate…</span>
          </div>`;
      } else {
        statusBadge = `
          <div class="bg-emerald-600/95 text-white px-3 py-1 rounded-full flex items-center gap-1.5 shadow-sm">
            <span class="material-symbols-outlined text-[15px] material-fill">check_circle</span>
            <span class="text-[11px] font-bold">${item.stage === 'done' ? 'Done' : 'Plate Detected'}</span>
          </div>`;
      }

      return `
        <div class="group relative aspect-[4/3] rounded-2xl overflow-hidden bg-surface-container border border-outline-variant/30 shadow-sm">
          <img src="${item.previewUrl}" alt="${item.name}" class="w-full h-full object-cover"/>
          <div class="absolute inset-0 bg-black/15 flex items-center justify-center">
            ${statusBadge}
          </div>
          <button type="button" onclick="removeQueuedFile(${idx})" class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <span class="material-symbols-outlined text-[16px]">close</span>
          </button>
          <div class="absolute bottom-2 left-2 right-2 px-2.5 py-1 rounded-lg bg-black/45 backdrop-blur-xs text-white text-[10px] font-medium truncate">
            ${item.name}
          </div>
        </div>
      `;
    }).join('');
  }

  async function submitUploadBatch() {
    const plateVal = (document.getElementById('input-plate-number').value || 'SXX 1234 A').trim();
    const modelVal = (document.getElementById('input-car-model').value || '').trim();
    const priceVal = (document.getElementById('input-car-price').value || '').trim();
    const specsVal = (document.getElementById('input-car-specs')?.value || '').trim();
    const msgEl = document.getElementById('upload-status-msg');
    const btnLabel = document.getElementById('btn-process-save-label');

    if (uploadFilesQueue.length === 0) {
      msgEl.textContent = 'No local files selected — loading sample showroom batch for ' + plateVal + '…';
      await runDemoBatch(plateVal);
      return;
    }

    // Mark all items as "Removing plate…" during server processing
    uploadFilesQueue.forEach(item => { item.stage = 'removing'; item.progress = 82; });
    renderUploadQueue();
    btnLabel.textContent = 'Processing Plates…';

    const fd = new FormData();
    fd.append('car_id', plateVal);
    fd.append('ratio', uploadRatio);
    fd.append('car_model', modelVal);
    fd.append('car_price', priceVal);
    fd.append('car_specs', specsVal);
    uploadFilesQueue.forEach(item => fd.append('files', item.file));

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: fd,
        credentials: 'same-origin'
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      uploadFilesQueue.forEach(item => { item.stage = 'done'; item.progress = 100; });
      renderUploadQueue();
      btnLabel.textContent = 'Process & Save';
      msgEl.textContent = `Processed ${data.processed_count} photos for ${plateVal} (${data.output_count} ready, ${data.review_count} in review).`;

      await fetchState();
      setTimeout(() => {
        clearUploadQueue();
        switchTab('gallery');
      }, 650);
    } catch (err) {
      btnLabel.textContent = 'Process & Save';
      msgEl.textContent = 'Error: ' + err.message;
    }
  }

  async function runDemoBatch(customPlate) {
    const plate = customPlate || document.getElementById('input-plate-number').value || 'SXX-1234-A';
    const btn = document.getElementById('btn-demo-load');
    if (btn) btn.disabled = true;
    try {
      const res = await fetch(`/api/demo-batch?car_id=${encodeURIComponent(plate)}&ratio=${encodeURIComponent(uploadRatio)}`, {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        await fetchState();
        switchTab('gallery');
      }
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // =========================================================================
  // SCREEN 2: VEHICLE GALLERY (GROUPED BY PLATE NUMBER) & BEFORE/AFTER TOGGLE
  // =========================================================================
  function setGalleryFilter(flt) {
    galleryFilter = flt;
    ['all', 'ready', 'review'].forEach(k => {
      const b = document.getElementById('flt-' + k);
      if (!b) return;
      b.className = (k === flt)
        ? 'px-4 py-1.5 rounded-full text-xs font-semibold bg-on-surface text-white transition-all'
        : 'px-4 py-1.5 rounded-full text-xs font-semibold bg-surface-container text-on-surface-variant hover:text-on-surface transition-all';
    });
    renderGallery();
  }

  function setGlobalCompareMode(mode) {
    globalCompareMode = mode;
    cardCompareModes = {};
    document.getElementById('btn-global-after').className = (mode === 'after')
      ? 'px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    document.getElementById('btn-global-before').className = (mode === 'before')
      ? 'px-3.5 py-1 rounded-full text-xs font-semibold bg-white text-primary shadow-sm transition-all'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    renderGallery();
  }

  function toggleCardCompareMode(carId, mode, ev) {
    if (ev) ev.stopPropagation();
    cardCompareModes[carId] = mode;
    renderGallery();
  }

  function getMediaUrlForPhoto(carId, photoObj, compareMode, fullRes = false) {
    const fn = encodeURIComponent(photoObj.filename);
    const cid = encodeURIComponent(carId);
    const fullParam = fullRes ? '&full=1' : '';
    const activeRatio = encodeURIComponent(studioRatio || uploadRatio || '1:1');
    if (compareMode === 'before') {
      return `/media/original/${cid}/${fn}?full=${fullRes ? 1 : 0}`;
    }
    if (photoObj.status === 'ready') {
      return `/media/output/${cid}/${fn}?ratio=${activeRatio}${fullParam}`;
    }
    return `/media/after/${cid}/${fn}?ratio=${activeRatio}${fullParam}`;
  }

  function getCarExportZipUrl(carId) {
    const params = new URLSearchParams({
      ratio: studioRatio || uploadRatio || '1:1',
      fit_mode: studioFitMode || 'fit',
      template_style: studioTemplate || 'clean_white'
    });
    return `/api/export/${encodeURIComponent(carId)}?${params.toString()}`;
  }

  function downloadCarZip(carId, ev) {
    if (ev) {
      ev.stopPropagation();
      ev.preventDefault();
    }
    if (!carId) return;
    window.location.href = getCarExportZipUrl(carId);
  }

  function openPhotoFullWindow(carId, filename, status, compareMode, ev) {
    if (ev) ev.stopPropagation();
    const url = getMediaUrlForPhoto(carId, { filename: filename, status: status }, compareMode, true);
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  function renderGallery() {
    const container = document.getElementById('gallery-cards-container');
    if (!container) return;

    const query = (document.getElementById('gallery-search-input')?.value || '').trim().toLowerCase();
    const carIds = getAllCarIds().filter(cid => {
      const meta = getCarMeta(cid);
      const photos = getCarPhotos(cid);
      if (photos.length === 0) return false;
      if (galleryFilter === 'ready' && !photos.some(p => p.status === 'ready')) return false;
      if (galleryFilter === 'review' && !photos.some(p => p.status !== 'ready')) return false;
      if (!query) return true;
      return cid.toLowerCase().includes(query) ||
             meta.plate_display.toLowerCase().includes(query) ||
             meta.car_model.toLowerCase().includes(query);
    });

    if (carIds.length === 0) {
      container.innerHTML = `
        <div class="col-span-full apple-card-white rounded-[28px] p-12 text-center space-y-4">
          <div class="w-14 h-14 rounded-2xl bg-surface-container mx-auto flex items-center justify-center text-outline">
            <span class="material-symbols-outlined text-3xl">directions_car</span>
          </div>
          <div>
            <h3 class="text-lg font-bold text-on-surface">No vehicles found</h3>
            <p class="text-xs sm:text-sm text-on-surface-variant mt-1">Upload car photos in the Upload tab to populate the gallery.</p>
          </div>
          <button type="button" onclick="switchTab('upload')" class="px-5 py-2.5 rounded-full bg-primary text-white text-xs font-semibold shadow-sm">
            Go to Upload
          </button>
        </div>`;
      return;
    }

    container.innerHTML = carIds.map(cid => {
      const meta = getCarMeta(cid);
      const photos = getCarPhotos(cid);
      const mode = cardCompareModes[cid] || globalCompareMode;
      const previewPhotos = photos.slice(0, 4);
      const isCarSelected = selectedCarIds.has(cid);
      const readyCount = photos.filter(p => p.status === 'ready').length;
      const reviewCount = photos.length - readyCount;

      const thumbsHtml = previewPhotos.map(p => {
        const key = `${cid}::${p.filename}`;
        const isSelected = selectedPhotoKeys.has(key) || isCarSelected;
        const imgUrl = getMediaUrlForPhoto(cid, p, mode);

        return `
          <div onclick="onGalleryThumbClick('${cid}', '${p.filename}', event)"
               class="relative aspect-square rounded-2xl overflow-hidden bg-surface-container border ${isSelected ? 'border-primary ring-2 ring-primary' : 'border-outline-variant/25'} cursor-pointer group">
            <img src="${imgUrl}" alt="${p.filename}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
            <div class="absolute bottom-1.5 left-1.5 px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider ${mode === 'before' ? 'bg-amber-500/90 text-white' : 'bg-black/55 text-white'}">
              ${mode === 'before' ? 'Original' : 'Plate Removed'}
            </div>
            ${selectionMode ? `
              <div class="absolute top-2 right-2 w-6 h-6 rounded-full ${isSelected ? 'bg-primary text-white' : 'bg-white/85 text-transparent border border-outline-variant'} flex items-center justify-center shadow-sm">
                <span class="material-symbols-outlined text-[16px] material-fill">check</span>
              </div>
            ` : ''}
          </div>
        `;
      }).join('');

      return `
        <div onclick="onCarCardClick('${cid}', event)"
             class="apple-card-white rounded-[26px] p-5 sm:p-6 transition-all hover:shadow-apple-float cursor-pointer ${isCarSelected ? 'ring-2 ring-primary bg-primary-fixed/10' : ''}">
          <!-- Card Top Row: Plate Number Title + Photo Count + Before/After Toggle -->
          <div class="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div class="flex items-center gap-3">
              ${selectionMode ? `
                <button type="button" onclick="toggleSelectCarGroup('${cid}', event)"
                        class="w-7 h-7 rounded-full ${isCarSelected ? 'bg-primary text-white' : 'bg-surface-container border border-outline-variant text-transparent'} flex items-center justify-center transition-all">
                  <span class="material-symbols-outlined text-[18px] material-fill">check</span>
                </button>
              ` : ''}
              <div>
                <div class="flex items-center gap-2">
                  <span class="px-3 py-1 rounded-xl bg-primary-fixed text-primary font-extrabold text-sm tracking-wider uppercase">${meta.plate_display}</span>
                  <span class="text-xs font-semibold text-on-surface-variant">${photos.length} photo${photos.length === 1 ? '' : 's'}</span>
                  ${reviewCount > 0 ? `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">${reviewCount} Review</span>` : ''}
                </div>
                <h3 class="text-base font-bold text-on-surface mt-1.5">${meta.car_model}</h3>
                ${meta.car_specs ? `<p class="text-xs text-on-surface-variant mt-0.5">${meta.car_specs}${meta.car_price ? ' • <span class="text-primary font-semibold">' + meta.car_price + '</span>' : ''}</p>` : (meta.car_price ? `<p class="text-xs text-primary font-semibold mt-0.5">${meta.car_price}</p>` : '')}
              </div>
            </div>

            <!-- Card-Level Before / After Segmented Toggle -->
            <div class="flex items-center gap-1.5" onclick="event.stopPropagation()">
              <div class="inline-flex bg-surface-container p-0.5 rounded-full border border-outline-variant/25">
                <button type="button" onclick="toggleCardCompareMode('${cid}', 'after', event)"
                        class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${mode === 'after' ? 'bg-white text-primary shadow-xs' : 'text-on-surface-variant'}">
                  Clean
                </button>
                <button type="button" onclick="toggleCardCompareMode('${cid}', 'before', event)"
                        class="px-2.5 py-1 rounded-full text-[11px] font-semibold ${mode === 'before' ? 'bg-white text-primary shadow-xs' : 'text-on-surface-variant'}">
                  Original
                </button>
              </div>

              <!-- Quick Delete Car Group Button -->
              <button type="button" onclick="openDeleteModal('car', '${cid}', event)"
                      class="w-8 h-8 rounded-full hover:bg-error-container/50 text-on-surface-variant hover:text-error flex items-center justify-center transition-colors"
                      title="Delete entire car group">
                <span class="material-symbols-outlined text-[18px]">delete</span>
              </button>
            </div>
          </div>

          <!-- Horizontal Strip / Grid of 3-4 Preview Thumbnails -->
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-4">
            ${thumbsHtml}
          </div>

          <!-- Card Footer Actions -->
          <div class="flex items-center justify-between pt-3 border-t border-surface-container text-xs font-semibold">
            <span class="text-primary flex items-center gap-1">
              <span>Tap to view all ${photos.length} photos</span>
              <span class="material-symbols-outlined text-[15px]">chevron_right</span>
            </span>
            <div class="flex items-center gap-3" onclick="event.stopPropagation()">
              <button type="button" onclick="openCarInFrames('${cid}')" class="text-on-surface-variant hover:text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">crop_free</span>
                <span>Frame Studio</span>
              </button>
              <a href="${getCarExportZipUrl(cid)}" onclick="downloadCarZip('${cid}', event)" class="text-on-surface-variant hover:text-primary flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">download</span>
                <span>ZIP</span>
              </a>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function onCarCardClick(carId, ev) {
    if (selectionMode) {
      toggleSelectCarGroup(carId, ev);
      return;
    }
    openCarDetailModal(carId);
  }

  function onGalleryThumbClick(carId, filename, ev) {
    if (ev) ev.stopPropagation();
    if (selectionMode) {
      const key = `${carId}::${filename}`;
      if (selectedPhotoKeys.has(key)) {
        selectedPhotoKeys.delete(key);
        selectedCarIds.delete(carId);
      } else {
        selectedPhotoKeys.add(key);
      }
      updateSelectionBar();
      renderGallery();
      return;
    }
    const photos = getCarPhotos(carId);
    const pObj = photos.find(p => p.filename === filename) || { filename: filename, status: 'ready' };
    const mode = cardCompareModes[carId] || globalCompareMode;
    openPhotoFullWindow(carId, filename, pObj.status, mode, ev);
  }

  // =========================================================================
  // CAR DETAIL MODAL (ALL PHOTOS FOR THAT CAR + BEFORE/AFTER + EDIT/DELETE)
  // =========================================================================
  function openCarDetailModal(carId) {
    activeModalCarId = carId;
    modalCompareMode = cardCompareModes[carId] || globalCompareMode;
    document.getElementById('modal-edit-car-drawer').classList.add('hidden');
    document.getElementById('car-detail-modal').classList.remove('hidden');
    renderCarDetailModal();
  }

  function closeCarDetailModal() {
    document.getElementById('car-detail-modal').classList.add('hidden');
    activeModalCarId = null;
  }

  function setModalCompareMode(mode) {
    modalCompareMode = mode;
    document.getElementById('modal-btn-after').className = (mode === 'after')
      ? 'px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant';
    document.getElementById('modal-btn-before').className = (mode === 'before')
      ? 'px-3.5 py-1 rounded-full text-xs font-bold bg-white text-primary shadow-sm'
      : 'px-3.5 py-1 rounded-full text-xs font-semibold text-on-surface-variant';
    renderCarDetailModal();
  }

  function toggleEditCarGroupForm() {
    if (!activeModalCarId) return;
    const drawer = document.getElementById('modal-edit-car-drawer');
    const meta = getCarMeta(activeModalCarId);
    document.getElementById('edit-car-plate').value = meta.plate_display;
    document.getElementById('edit-car-model').value = meta.car_model;
    document.getElementById('edit-car-specs').value = meta.car_specs;
    document.getElementById('edit-car-price').value = meta.car_price;
    drawer.classList.toggle('hidden');
  }

  async function saveCarGroupMetadata() {
    if (!activeModalCarId) return;
    const newPlate = document.getElementById('edit-car-plate').value.trim();
    const newModel = document.getElementById('edit-car-model').value.trim();
    const newSpecs = document.getElementById('edit-car-specs').value.trim();
    const newPrice = document.getElementById('edit-car-price').value.trim();

    const res = await fetch(`/api/cars/${encodeURIComponent(activeModalCarId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        new_car_id: newPlate,
        plate_display: newPlate,
        car_model: newModel,
        car_specs: newSpecs,
        car_price: newPrice
      })
    });
    if (res.ok) {
      const data = await res.json();
      activeModalCarId = data.car_id;
      document.getElementById('modal-edit-car-drawer').classList.add('hidden');
      await fetchState();
      renderCarDetailModal();
    }
  }

  function renderCarDetailModal() {
    if (!activeModalCarId) return;
    const meta = getCarMeta(activeModalCarId);
    const photos = getCarPhotos(activeModalCarId);

    document.getElementById('modal-car-plate-badge').textContent = meta.plate_display;
    document.getElementById('modal-car-title').textContent = meta.car_model;
    const subParts = [`${photos.length} photo${photos.length === 1 ? '' : 's'}`];
    if (meta.car_specs) subParts.push(meta.car_specs);
    if (meta.car_price) subParts.push(meta.car_price);
    document.getElementById('modal-car-count').textContent = subParts.join(' • ');

    const grid = document.getElementById('modal-photos-grid');
    if (photos.length === 0) {
      closeCarDetailModal();
      return;
    }

    grid.innerHTML = photos.map(p => {
      const imgUrl = getMediaUrlForPhoto(activeModalCarId, p, modalCompareMode);
      const isReview = p.status !== 'ready';
      return `
        <div class="apple-card-white rounded-2xl overflow-hidden flex flex-col justify-between border border-outline-variant/30 shrink-0">
          <div onclick="openPhotoFullWindow('${activeModalCarId}', '${p.filename}', '${p.status}', '${modalCompareMode}', event)"
               class="relative w-full aspect-square bg-surface-container cursor-zoom-in group overflow-hidden" title="Click to open full image in new window">
            <img src="${imgUrl}" alt="${p.filename}" loading="lazy" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"/>
            <span class="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase ${modalCompareMode === 'before' ? 'bg-amber-500 text-white' : 'bg-emerald-600 text-white'}">
              ${modalCompareMode === 'before' ? 'Original' : 'Plate Removed'}
            </span>
            <button type="button" onclick="event.stopPropagation(); deleteSinglePhoto('${activeModalCarId}', '${p.filename}')"
                    class="absolute top-2.5 right-2.5 w-8 h-8 rounded-full bg-white/90 hover:bg-error hover:text-white text-error flex items-center justify-center shadow-sm transition-colors"
                    title="Delete this photo">
              <span class="material-symbols-outlined text-[18px]">delete</span>
            </button>
          </div>
          <div class="p-3.5 flex items-center justify-between gap-2">
            <div class="truncate">
              <p class="text-xs font-bold text-on-surface truncate">${p.filename}</p>
              <p class="text-[10px] text-on-surface-variant">${isReview ? 'Needs review: ' + p.reason : 'Plate masked & verified'}</p>
            </div>
            <div class="flex items-center gap-1.5 shrink-0">
              ${isReview ? `
                <button type="button" onclick="approveReviewPhoto('${activeModalCarId}', '${p.filename}')" class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white text-[11px] font-semibold">Approve</button>
              ` : ''}
              <button type="button" onclick="closeCarDetailModal(); openPhotoInFrames('${activeModalCarId}', '${p.filename}')"
                      class="px-3 py-1.5 rounded-xl bg-primary-fixed text-primary text-xs font-semibold hover:bg-primary hover:text-white transition-colors">
                ${isReview ? 'Edit &amp; Approve' : 'Frame'}
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async function approveReviewPhoto(carId, filename) {
    const res = await fetch(`/api/approve/${encodeURIComponent(carId)}/${encodeURIComponent(filename)}`, {
      method: 'POST',
      credentials: 'same-origin'
    });
    if (res.ok) {
      await fetchState();
      if (activeModalCarId) renderCarDetailModal();
    }
  }

  async function deleteSinglePhoto(carId, filename) {
    const res = await fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        scope: 'selected',
        items: [{ car_id: carId, filename: filename }]
      })
    });
    if (res.ok) {
      await fetchState();
      if (activeModalCarId) renderCarDetailModal();
    }
  }

  // =========================================================================
  // SCREEN 4: SELECTION MODE & DELETE CONFIRMATION MODAL
  // =========================================================================
  function toggleSelectionMode() {
    selectionMode = !selectionMode;
    const btn = document.getElementById('btn-toggle-select-mode');
    const lbl = document.getElementById('label-select-mode');
    if (selectionMode) {
      btn.className = 'px-5 py-2.5 rounded-full font-semibold text-sm bg-primary text-white transition-all flex items-center gap-1.5 shadow-sm';
      lbl.textContent = 'Done';
    } else {
      btn.className = 'px-5 py-2.5 rounded-full font-semibold text-sm border border-outline-variant/50 bg-white hover:bg-surface-container-low text-on-surface transition-all flex items-center gap-1.5 shadow-sm';
      lbl.textContent = 'Select';
      selectedPhotoKeys.clear();
      selectedCarIds.clear();
    }
    updateSelectionBar();
    renderGallery();
  }

  function toggleSelectCarGroup(carId, ev) {
    if (ev) ev.stopPropagation();
    const photos = getCarPhotos(carId);
    if (selectedCarIds.has(carId)) {
      selectedCarIds.delete(carId);
      photos.forEach(p => selectedPhotoKeys.delete(`${carId}::${p.filename}`));
    } else {
      selectedCarIds.add(carId);
      photos.forEach(p => selectedPhotoKeys.add(`${carId}::${p.filename}`));
    }
    updateSelectionBar();
    renderGallery();
  }

  function selectAllGalleryItems() {
    getAllCarIds().forEach(cid => {
      selectedCarIds.add(cid);
      getCarPhotos(cid).forEach(p => selectedPhotoKeys.add(`${cid}::${p.filename}`));
    });
    updateSelectionBar();
    renderGallery();
  }

  function clearAllSelections() {
    selectedPhotoKeys.clear();
    selectedCarIds.clear();
    updateSelectionBar();
    renderGallery();
  }

  function updateSelectionBar() {
    const bar = document.getElementById('selection-floating-bar');
    if (!bar) return;
    const count = selectedPhotoKeys.size;
    if (selectionMode && activeTab === 'gallery') {
      bar.classList.remove('hidden');
      document.getElementById('selection-counter-pill').textContent = `${count} selected`;
      document.getElementById('btn-floating-delete-label').textContent = `Delete Selected (${count})`;
    } else {
      bar.classList.add('hidden');
    }
  }

  function openDeleteModal(defaultScope, targetCarId, ev) {
    if (ev) ev.stopPropagation();
    pendingDeleteTargetCarId = targetCarId || activeModalCarId || Array.from(selectedCarIds)[0] || getAllCarIds()[0] || null;

    const radios = document.querySelectorAll('input[name="delete-scope-radio"]');
    radios.forEach(r => { r.checked = (r.value === defaultScope); });

    const totalInventoryPhotos = getAllCarIds().reduce((acc, cid) => acc + getCarPhotos(cid).length, 0);
    const selCount = selectedPhotoKeys.size;
    const carGroupCount = selectedCarIds.size > 0
      ? selectedCarIds.size
      : (pendingDeleteTargetCarId ? 1 : 0);

    document.getElementById('del-count-selected').textContent = `${selCount} photo${selCount === 1 ? '' : 's'}`;
    document.getElementById('del-count-car').textContent = pendingDeleteTargetCarId
      ? `${pendingDeleteTargetCarId} (${getCarPhotos(pendingDeleteTargetCarId).length} photos)`
      : `${carGroupCount} group`;
    document.getElementById('del-count-all').textContent = `${totalInventoryPhotos} photos`;

    updateDeleteModalSummary();
    document.getElementById('delete-confirm-modal').classList.remove('hidden');
  }

  function updateDeleteModalSummary() {
    const chosen = document.querySelector('input[name="delete-scope-radio"]:checked')?.value || 'selected';
    const btn = document.getElementById('btn-confirm-destructive-delete');
    const totalInventoryPhotos = getAllCarIds().reduce((acc, cid) => acc + getCarPhotos(cid).length, 0);

    if (chosen === 'all') {
      btn.textContent = `Delete All (${totalInventoryPhotos} Photos)`;
    } else if (chosen === 'car') {
      const cids = selectedCarIds.size > 0 ? Array.from(selectedCarIds) : (pendingDeleteTargetCarId ? [pendingDeleteTargetCarId] : []);
      btn.textContent = `Delete Car Group (${cids.join(', ') || '1 Group'})`;
    } else {
      btn.textContent = `Delete Selected (${selectedPhotoKeys.size})`;
    }
  }

  function closeDeleteModal() {
    document.getElementById('delete-confirm-modal').classList.add('hidden');
  }

  async function confirmExecuteDelete() {
    const chosen = document.querySelector('input[name="delete-scope-radio"]:checked')?.value || 'selected';
    let payload = { scope: chosen };

    if (chosen === 'car') {
      const cids = selectedCarIds.size > 0
        ? Array.from(selectedCarIds)
        : (pendingDeleteTargetCarId ? [pendingDeleteTargetCarId] : []);
      payload.car_ids = cids;
    } else if (chosen === 'selected') {
      payload.items = Array.from(selectedPhotoKeys).map(k => {
        const [cid, fn] = k.split('::');
        return { car_id: cid, filename: fn };
      });
    }

    const res = await fetch('/api/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      selectedPhotoKeys.clear();
      selectedCarIds.clear();
      closeDeleteModal();
      closeCarDetailModal();
      if (selectionMode) toggleSelectionMode();
      await fetchState();
    }
  }

  // =========================================================================
  // SCREEN 3: FRAME TEMPLATE EDITOR + INTERACTIVE PLATE COVER CALIBRATION
  // =========================================================================
  function getCurrentStudioPhotoObj() {
    if (!studioCarId || !studioFilename) return null;
    const photos = getCarPhotos(studioCarId);
    return photos.find(p => p.filename === studioFilename) || null;
  }

  function updateStudioReviewStatusUI() {
    const photoObj = getCurrentStudioPhotoObj();
    const isReview = photoObj && photoObj.status !== 'ready';
    const selCount = studioSelectedFilenames.size;

    const badge = document.getElementById('studio-photo-status-badge');
    const selCountBadge = document.getElementById('studio-selection-count-badge');
    const clearBtn = document.getElementById('btn-studio-clear-sel');
    const nameEl = document.getElementById('studio-current-photo-name');
    const btnApprove = document.getElementById('btn-studio-approve-save');
    const lblApprove = document.getElementById('lbl-studio-approve-save');
    const stageLblApprove = document.getElementById('stage-approve-btn-label');
    const lblRemoveCover = document.getElementById('lbl-remove-plate-cover');
    const stageLblRemoveCover = document.getElementById('stage-remove-cover-btn-label');
    const btnReject = document.getElementById('btn-studio-reject');

    if (selCountBadge) {
      if (selCount > 0) {
        selCountBadge.textContent = `${selCount} selected`;
        selCountBadge.classList.remove('hidden');
      } else {
        selCountBadge.classList.add('hidden');
      }
    }
    if (clearBtn) {
      clearBtn.classList.toggle('hidden', selCount === 0);
    }

    if (nameEl) {
      if (selCount > 1) {
        nameEl.textContent = `${selCount} photos selected • Approve or remove plate cover in bulk`;
      } else if (photoObj) {
        nameEl.textContent = isReview
          ? `${photoObj.filename} • Needs review (${photoObj.reason || 'adjust plate cover'})`
          : `${photoObj.filename} • Drag plate cover to fine-tune placement`;
      } else {
        nameEl.textContent = 'Drag plate cover over photo to fix tilt or placement';
      }
    }

    if (badge) {
      if (isReview) {
        badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800';
        badge.textContent = 'Needs Review';
      } else {
        badge.className = 'px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800';
        badge.textContent = 'Approved';
      }
    }

    if (lblRemoveCover) {
      lblRemoveCover.textContent = selCount > 0
        ? `Remove Plate Cover (${selCount})`
        : 'Remove Plate Cover';
    }
    if (stageLblRemoveCover) {
      stageLblRemoveCover.textContent = selCount > 0
        ? `Remove Plate Cover (${selCount})`
        : 'Remove Plate Cover';
    }

    if (btnApprove && lblApprove) {
      btnApprove.className = 'flex-1 py-3 px-4 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md hover:opacity-95 active:scale-[0.98] transition-all flex items-center justify-center gap-1.5';
      if (selCount > 1) {
        lblApprove.textContent = `Approve & Save Selected (${selCount})`;
        if (stageLblApprove) stageLblApprove.textContent = `Approve Selected (${selCount})`;
      } else if (selCount === 1) {
        lblApprove.textContent = 'Approve & Save Selected (1)';
        if (stageLblApprove) stageLblApprove.textContent = 'Approve & Save (1)';
      } else if (isReview) {
        lblApprove.textContent = 'Approve & Save Photo to Gallery';
        if (stageLblApprove) stageLblApprove.textContent = 'Approve & Save';
      } else {
        lblApprove.textContent = 'Approve & Save Plate Fix';
        if (stageLblApprove) stageLblApprove.textContent = 'Save Plate Fix';
      }
    }

    if (btnReject) {
      btnReject.classList.toggle('hidden', !isReview);
    }
  }

  function openCarInFrames(carId) {
    studioCarId = carId;
    studioSelectedFilenames.clear();
    studioNoOverlay = false;
    const photos = getCarPhotos(carId);
    const revPhoto = photos.find(p => p.status !== 'ready');
    studioFilename = revPhoto ? revPhoto.filename : (photos.length > 0 ? photos[0].filename : null);
    const meta = getCarMeta(carId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    document.getElementById('studio-specs-input').value = meta.car_specs;
    switchTab('frames');
    loadPlateQuadForCurrentPhoto(Boolean(revPhoto));
  }

  function openPhotoInFrames(carId, filename) {
    studioCarId = carId;
    studioFilename = filename;
    studioSelectedFilenames.clear();
    studioNoOverlay = false;
    const meta = getCarMeta(carId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    document.getElementById('studio-specs-input').value = meta.car_specs;
    const pObj = getCarPhotos(carId).find(p => p.filename === filename);
    const isRev = Boolean(pObj && pObj.status !== 'ready');
    switchTab('frames');
    loadPlateQuadForCurrentPhoto(isRev);
  }

  function populateFrameStudioSelectors() {
    const sel = document.getElementById('frame-car-select');
    if (!sel) return;
    const cids = getAllCarIds();
    if (cids.length === 0) {
      sel.innerHTML = `<option value="">Sample Showroom Car</option>`;
      return;
    }
    if (!studioCarId || !cids.includes(studioCarId)) {
      studioCarId = cids[0];
      studioSelectedFilenames.clear();
    }
    sel.innerHTML = cids.map(cid => {
      const meta = getCarMeta(cid);
      return `<option value="${cid}" ${cid === studioCarId ? 'selected' : ''}>${meta.plate_display} — ${meta.car_model}</option>`;
    }).join('');

    renderFramePhotoStrip();
    updateStudioReviewStatusUI();
  }

  function onFrameCarChange() {
    const sel = document.getElementById('frame-car-select');
    studioCarId = sel.value;
    studioSelectedFilenames.clear();
    studioNoOverlay = false;
    const photos = getCarPhotos(studioCarId);
    studioFilename = photos.length > 0 ? photos[0].filename : null;
    const meta = getCarMeta(studioCarId);
    document.getElementById('studio-model-input').value = meta.car_model;
    document.getElementById('studio-price-input').value = meta.car_price;
    document.getElementById('studio-specs-input').value = meta.car_specs;
    plateQuadModified = false;
    renderFramePhotoStrip();
    loadPlateQuadForCurrentPhoto(false);
    refreshStudioCanvas();
  }

  function renderFramePhotoStrip() {
    const strip = document.getElementById('frame-photo-strip');
    if (!strip || !studioCarId) return;
    const photos = getCarPhotos(studioCarId);
    // Prune any stale selected filenames that no longer exist
    const validNames = new Set(photos.map(p => p.filename));
    Array.from(studioSelectedFilenames).forEach(fn => {
      if (!validNames.has(fn)) studioSelectedFilenames.delete(fn);
    });

    if (!studioFilename || !photos.some(p => p.filename === studioFilename)) {
      studioFilename = photos.length > 0 ? photos[0].filename : null;
    }
    strip.innerHTML = photos.map(p => {
      const active = p.filename === studioFilename;
      const checked = studioSelectedFilenames.has(p.filename);
      const isRev = p.status !== 'ready';
      const thumbUrl = getMediaUrlForPhoto(studioCarId, p, 'after');
      return `
        <div onclick="selectStudioPhoto('${p.filename}')"
             class="relative aspect-square rounded-xl overflow-hidden border-2 cursor-pointer ${active ? 'border-primary ring-2 ring-primary/30' : (checked ? 'border-primary/80 bg-primary/5' : 'border-transparent opacity-80 hover:opacity-100')} transition-all group"
             title="${p.filename}${isRev ? ' (Needs Review)' : ''}">
          <img src="${thumbUrl}" alt="${p.filename}" class="w-full h-full object-cover"/>
          <!-- Multi-Select Checkbox -->
          <button type="button" onclick="toggleStudioPhotoCheck('${p.filename}', event)"
                  class="absolute top-1 left-1 w-5 h-5 rounded-md flex items-center justify-center transition-all shadow-sm ${checked ? 'bg-primary text-white border border-white' : 'bg-white/85 hover:bg-white text-transparent hover:text-primary/50 border border-outline-variant/60'}"
                  title="Select for batch approval or plate cover removal">
            <span class="material-symbols-outlined text-[14px] font-bold">check</span>
          </button>
          ${isRev ? `<span class="absolute top-1 right-1 w-2.5 h-2.5 rounded-full bg-amber-500 ring-2 ring-white" title="Needs Review"></span>` : ''}
        </div>
      `;
    }).join('');
    updateStudioReviewStatusUI();
  }

  function toggleStudioPhotoCheck(fn, ev) {
    if (ev) ev.stopPropagation();
    if (studioSelectedFilenames.has(fn)) {
      studioSelectedFilenames.delete(fn);
    } else {
      studioSelectedFilenames.add(fn);
    }
    renderFramePhotoStrip();
  }

  function studioSelectAllPhotos() {
    if (!studioCarId) return;
    getCarPhotos(studioCarId).forEach(p => studioSelectedFilenames.add(p.filename));
    renderFramePhotoStrip();
  }

  function studioSelectReviewPhotos() {
    if (!studioCarId) return;
    studioSelectedFilenames.clear();
    getCarPhotos(studioCarId).forEach(p => {
      if (p.status !== 'ready') studioSelectedFilenames.add(p.filename);
    });
    renderFramePhotoStrip();
  }

  function studioClearPhotoSelection() {
    studioSelectedFilenames.clear();
    renderFramePhotoStrip();
  }

  function selectStudioPhoto(fn) {
    studioFilename = fn;
    plateQuadModified = false;
    studioNoOverlay = false;
    renderFramePhotoStrip();
    const pObj = getCurrentStudioPhotoObj();
    const isRev = Boolean(pObj && pObj.status !== 'ready');
    loadPlateQuadForCurrentPhoto(isRev);
    refreshStudioCanvas();
  }

  // Interactive 4-Corner & Center Move Plate Cover Adjustment
  async function loadPlateQuadForCurrentPhoto(autoEnterAdjust = false) {
    updateStudioReviewStatusUI();
    if (!studioCarId || !studioFilename) return;

    const origImg = document.getElementById('plate-calib-orig-img');
    if (origImg) {
      origImg.src = `/media/original/${encodeURIComponent(studioCarId)}/${encodeURIComponent(studioFilename)}?full=1`;
    }
    const coverSvgImg = document.getElementById('plate-calib-cover-img');
    if (coverSvgImg) {
      coverSvgImg.setAttribute('href', `/media/plate-overlay?t=${Date.now()}`);
    }

    try {
      const res = await fetch(`/api/plate-quad/${encodeURIComponent(studioCarId)}/${encodeURIComponent(studioFilename)}`, {
        credentials: 'same-origin'
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.quad_pct) && data.quad_pct.length === 4) {
          studioQuadPct = data.quad_pct.map(pt => [Number(pt[0]), Number(pt[1])]);
          plateQuadModified = (data.mode === 'manual_default');
        }
      }
    } catch (e) {
      console.error('Failed to load plate quad:', e);
    }

    renderPlateCalibOverlay();
    if (autoEnterAdjust) {
      togglePlateAdjustMode(true);
    }
  }

  function togglePlateAdjustMode(forceState) {
    plateAdjustMode = (typeof forceState === 'boolean') ? forceState : !plateAdjustMode;
    const stage = document.getElementById('plate-adjust-stage');
    const canvasWrap = document.getElementById('studio-canvas-wrapper');
    const topBtn = document.getElementById('btn-toggle-plate-adjust');
    const topLbl = document.getElementById('lbl-toggle-plate-adjust');
    const sideLbl = document.getElementById('lbl-sidebar-adjust-plate');

    if (stage) stage.classList.toggle('hidden', !plateAdjustMode);
    if (canvasWrap) canvasWrap.classList.toggle('hidden', plateAdjustMode);

    if (topBtn && topLbl) {
      if (plateAdjustMode) {
        topBtn.className = 'px-3.5 py-2 rounded-xl text-xs font-bold bg-primary text-white shadow-sm transition-all flex items-center gap-1.5';
        topLbl.textContent = 'Preview in Frame';
      } else {
        topBtn.className = 'px-3.5 py-2 rounded-xl text-xs font-bold border border-primary/30 bg-primary-fixed/40 text-primary hover:bg-primary hover:text-white transition-all flex items-center gap-1.5';
        topLbl.textContent = 'Adjust Plate Cover';
      }
    }
    if (sideLbl) {
      sideLbl.textContent = plateAdjustMode ? 'Preview Adjusted Plate in Frame' : 'Move / Adjust Plate Cover on Photo';
    }

    if (plateAdjustMode) {
      if (studioCarId && studioFilename) {
        const origImg = document.getElementById('plate-calib-orig-img');
        if (origImg && !origImg.getAttribute('src')) {
          loadPlateQuadForCurrentPhoto(true);
        } else {
          renderPlateCalibOverlay();
        }
      }
    } else {
      refreshStudioCanvas();
    }
  }

  function renderPlateCalibOverlay() {
    const poly = document.getElementById('plate-calib-poly');
    const coverImg = document.getElementById('plate-calib-cover-img');
    const centerHandle = document.getElementById('handle-plate-center');
    if (!poly || !studioQuadPct || studioQuadPct.length !== 4) return;

    // Hide/show plate cover overlay elements if studioNoOverlay is toggled
    poly.classList.toggle('hidden', studioNoOverlay);
    if (coverImg) coverImg.classList.toggle('hidden', studioNoOverlay);
    if (centerHandle) centerHandle.classList.toggle('hidden', studioNoOverlay);
    for (let i = 0; i < 4; i++) {
      const h = document.getElementById(`handle-corner-${i}`);
      if (h) h.classList.toggle('hidden', studioNoOverlay);
    }
    if (studioNoOverlay) return;

    const ptsStr = studioQuadPct.map(pt => `${pt[0].toFixed(2)},${pt[1].toFixed(2)}`).join(' ');
    poly.setAttribute('points', ptsStr);

    let cx = 0;
    let cy = 0;
    for (let i = 0; i < 4; i++) {
      const h = document.getElementById(`handle-corner-${i}`);
      if (h) {
        h.style.left = `${studioQuadPct[i][0]}%`;
        h.style.top = `${studioQuadPct[i][1]}%`;
      }
      cx += studioQuadPct[i][0];
      cy += studioQuadPct[i][1];
    }
    cx /= 4.0;
    cy /= 4.0;

    if (centerHandle) {
      centerHandle.style.left = `${cx}%`;
      centerHandle.style.top = `${cy}%`;
    }

    // Position and tilt the live plate cover SVG image inside the quadrilateral
    if (coverImg) {
      const topW = Math.hypot(studioQuadPct[1][0] - studioQuadPct[0][0], studioQuadPct[1][1] - studioQuadPct[0][1]);
      const botW = Math.hypot(studioQuadPct[2][0] - studioQuadPct[3][0], studioQuadPct[2][1] - studioQuadPct[3][1]);
      const leftH = Math.hypot(studioQuadPct[3][0] - studioQuadPct[0][0], studioQuadPct[3][1] - studioQuadPct[0][1]);
      const rightH = Math.hypot(studioQuadPct[2][0] - studioQuadPct[1][0], studioQuadPct[2][1] - studioQuadPct[1][1]);
      const avgW = Math.max(4, (topW + botW) / 2.0);
      const avgH = Math.max(2, (leftH + rightH) / 2.0);
      const angleDeg = Math.atan2(
        (studioQuadPct[1][1] - studioQuadPct[0][1]) + (studioQuadPct[2][1] - studioQuadPct[3][1]),
        (studioQuadPct[1][0] - studioQuadPct[0][0]) + (studioQuadPct[2][0] - studioQuadPct[3][0])
      ) * 180.0 / Math.PI;

      coverImg.setAttribute('x', (cx - avgW / 2.0).toFixed(2));
      coverImg.setAttribute('y', (cy - avgH / 2.0).toFixed(2));
      coverImg.setAttribute('width', avgW.toFixed(2));
      coverImg.setAttribute('height', avgH.toFixed(2));
      coverImg.setAttribute('transform', `rotate(${angleDeg.toFixed(2)} ${cx.toFixed(2)} ${cy.toFixed(2)})`);
    }
  }

  function getCalibRelativePct(ev) {
    const container = document.getElementById('plate-calib-container');
    if (!container) return { x: 50, y: 50 };
    const rect = container.getBoundingClientRect();
    const pt = ev.touches ? ev.touches[0] : ev;
    const x = Math.max(0, Math.min(100, ((pt.clientX - rect.left) / Math.max(1, rect.width)) * 100.0));
    const y = Math.max(0, Math.min(100, ((pt.clientY - rect.top) / Math.max(1, rect.height)) * 100.0));
    return { x, y };
  }

  function startCornerDrag(idx, ev) {
    if (ev) {
      ev.stopPropagation();
      if (ev.cancelable) ev.preventDefault();
    }
    studioNoOverlay = false;
    activeCornerIdx = idx;
    isDraggingPlateBox = false;
    plateQuadModified = true;
  }

  function startPlateBoxDrag(ev) {
    if (ev) {
      ev.stopPropagation();
      if (ev.cancelable) ev.preventDefault();
    }
    studioNoOverlay = false;
    activeCornerIdx = -1;
    isDraggingPlateBox = true;
    plateQuadModified = true;
    plateDragStartPt = getCalibRelativePct(ev);
    plateDragStartQuad = studioQuadPct.map(pt => [pt[0], pt[1]]);
  }

  function onPlateCalibMove(ev) {
    if (activeCornerIdx < 0 && !isDraggingPlateBox) return;
    if (ev && ev.cancelable) ev.preventDefault();
    const cur = getCalibRelativePct(ev);

    if (activeCornerIdx >= 0) {
      studioQuadPct[activeCornerIdx] = [cur.x, cur.y];
      renderPlateCalibOverlay();
    } else if (isDraggingPlateBox && plateDragStartQuad) {
      const dx = cur.x - plateDragStartPt.x;
      const dy = cur.y - plateDragStartPt.y;
      studioQuadPct = plateDragStartQuad.map(pt => [
        Math.max(0, Math.min(100, pt[0] + dx)),
        Math.max(0, Math.min(100, pt[1] + dy))
      ]);
      renderPlateCalibOverlay();
    }
  }

  function onPlateCalibUp() {
    if (activeCornerIdx >= 0 || isDraggingPlateBox) {
      activeCornerIdx = -1;
      isDraggingPlateBox = false;
      debouncedRefreshStudio();
    }
  }

  async function resetPlateQuadToAuto() {
    plateQuadModified = false;
    studioNoOverlay = false;
    await loadPlateQuadForCurrentPhoto(true);
    refreshStudioCanvas();
  }

  function setStudioRatio(r) {
    studioRatio = r;
    uploadRatio = r;
    ['1:1', '16:9', '9:16'].forEach(k => {
      const b = document.getElementById('st-ratio-' + k);
      if (b) {
        b.className = (k === r)
          ? 'px-4 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all'
          : 'px-4 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      }
    });
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  function setStudioFitMode(mode) {
    studioFitMode = mode;
    document.getElementById('st-fit-fit').className = (mode === 'fit')
      ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
      : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';
    document.getElementById('st-fit-fill').className = (mode === 'fill')
      ? 'px-3.5 py-1.5 rounded-lg text-xs font-bold bg-white text-primary shadow-sm transition-all flex items-center gap-1.5'
      : 'px-3.5 py-1.5 rounded-lg text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all flex items-center gap-1.5';

    document.getElementById('studio-pan-hint').classList.toggle('hidden', mode !== 'fill');
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  const TEMPLATE_LABELS = {
    clean_white: 'Clean White',
    soft_grey: 'Soft Grey',
    minimal_border: 'Minimal Border',
    rounded_card: 'Rounded Card',
    glass_overlay: 'Glass Overlay'
  };

  function setStudioTemplate(tpl) {
    studioTemplate = tpl;
    document.getElementById('studio-active-template-label').textContent = TEMPLATE_LABELS[tpl] || tpl;
    Object.keys(TEMPLATE_LABELS).forEach(k => {
      const btn = document.getElementById('tpl-' + k);
      if (!btn) return;
      if (k === tpl) {
        btn.className = 'p-3 rounded-2xl border-2 border-primary bg-primary-fixed/15 text-left transition-all';
      } else {
        btn.className = 'p-3 rounded-2xl border border-outline-variant/40 hover:border-primary/50 bg-surface-container-low text-left transition-all';
      }
    });
    refreshStudioCanvas();
    saveGlobalFramePreset(true);
  }

  async function saveGlobalFramePreset(silent = false) {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ?? true;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';
    const fb = document.getElementById('studio-save-feedback');

    const res = await fetch('/api/frame-config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({
        ratio: studioRatio,
        fit_mode: studioFitMode,
        template_style: studioTemplate,
        offset_x: studioOffsetX,
        offset_y: studioOffsetY,
        caption_enabled: captionOn,
        car_model: model,
        car_price: price,
        car_specs: specs
      })
    });
    if (res.ok) {
      const data = await res.json();
      syncUiWithFrameConfig(data.frame_config);
      if (!silent && fb) {
        fb.textContent = `Default Frame Preset saved (${TEMPLATE_LABELS[studioTemplate] || studioTemplate} • ${studioRatio}) and applied!`;
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 3500);
      }
      await fetchState();
    }
  }

  async function uploadCustomPlateOverlay(fileList) {
    if (!fileList || !fileList.length) return;
    const file = fileList[0];
    const fd = new FormData();
    fd.append('file', file);
    const fb = document.getElementById('overlay-upload-feedback');

    const res = await fetch('/api/plate-overlay', {
      method: 'POST',
      body: fd,
      credentials: 'same-origin'
    });
    if (res.ok) {
      const ts = Date.now();
      const prev = document.getElementById('plate-overlay-preview-img');
      if (prev) prev.src = '/media/plate-overlay?t=' + ts;
      const coverSvgImg = document.getElementById('plate-calib-cover-img');
      if (coverSvgImg) coverSvgImg.setAttribute('href', '/media/plate-overlay?t=' + ts);
      if (fb) {
        fb.textContent = `Plate cover updated (${file.name}) and applied to all vehicles!`;
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 4000);
      }
      refreshStudioCanvas();
      await fetchState();
    }
  }

  async function resetCustomPlateOverlay() {
    const fb = document.getElementById('overlay-upload-feedback');
    const res = await fetch('/api/plate-overlay', {
      method: 'DELETE',
      credentials: 'same-origin'
    });
    if (res.ok) {
      const ts = Date.now();
      const prev = document.getElementById('plate-overlay-preview-img');
      if (prev) prev.src = '/media/plate-overlay?t=' + ts;
      const coverSvgImg = document.getElementById('plate-calib-cover-img');
      if (coverSvgImg) coverSvgImg.setAttribute('href', '/media/plate-overlay?t=' + ts);
      if (fb) {
        fb.textContent = 'Reset to default Forest Wheel plate cover.';
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 3500);
      }
      refreshStudioCanvas();
      await fetchState();
    }
  }

  function buildStudioRenderUrl(download = 0) {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ? 1 : 0;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';

    const params = new URLSearchParams({
      ratio: studioRatio,
      fit_mode: studioFitMode,
      template_style: studioTemplate,
      offset_x: studioOffsetX.toFixed(2),
      offset_y: studioOffsetY.toFixed(2),
      caption: String(captionOn),
      car_model: model,
      car_price: price,
      car_specs: specs,
      download: String(download),
      t: String(Date.now())
    });
    if (studioCarId) params.set('car_id', studioCarId);
    if (studioFilename) params.set('filename', studioFilename);
    if (studioNoOverlay) {
      params.set('no_overlay', '1');
    } else if (plateQuadModified && studioQuadPct && studioQuadPct.length === 4) {
      const flat = studioQuadPct.map(pt => `${pt[0].toFixed(2)},${pt[1].toFixed(2)}`).join(',');
      params.set('quad', flat);
    }
    return `/api/frame-render?${params.toString()}`;
  }

  function refreshStudioCanvas() {
    const img = document.getElementById('studio-preview-img');
    if (!img) return;
    img.src = buildStudioRenderUrl(0);
  }

  function debouncedRefreshStudio() {
    if (studioDebounceTimer) clearTimeout(studioDebounceTimer);
    studioDebounceTimer = setTimeout(refreshStudioCanvas, 280);
  }

  // Drag / pinch to reposition when in "Fill frame" mode
  function startCanvasPan(ev) {
    if (studioFitMode !== 'fill') return;
    isPanning = true;
    const pt = ev.touches ? ev.touches[0] : ev;
    panStartX = pt.clientX;
    panStartY = pt.clientY;
  }

  function moveCanvasPan(ev) {
    if (!isPanning || studioFitMode !== 'fill') return;
    const pt = ev.touches ? ev.touches[0] : ev;
    const dx = (panStartX - pt.clientX) / 260;
    const dy = (panStartY - pt.clientY) / 260;
    panStartX = pt.clientX;
    panStartY = pt.clientY;
    studioOffsetX = Math.max(0.0, Math.min(1.0, studioOffsetX + dx));
    studioOffsetY = Math.max(0.0, Math.min(1.0, studioOffsetY + dy));
    debouncedRefreshStudio();
  }

  function endCanvasPan() {
    isPanning = false;
  }

  function getTargetStudioFilenames() {
    if (studioSelectedFilenames.size > 0) {
      return Array.from(studioSelectedFilenames);
    }
    return studioFilename ? [studioFilename] : [];
  }

  async function approveOrSaveCurrentStudioPhoto() {
    const targets = getTargetStudioFilenames();
    await saveStudioFrameToGallery(true, studioNoOverlay, targets);
  }

  async function removePlateCoverAction() {
    studioNoOverlay = true;
    renderPlateCalibOverlay();
    refreshStudioCanvas();
    const targets = getTargetStudioFilenames();
    await saveStudioFrameToGallery(true, true, targets);
  }

  async function rejectCurrentStudioPhoto() {
    const targets = getTargetStudioFilenames();
    if (!studioCarId || targets.length === 0) return;
    const fb = document.getElementById('studio-save-feedback');
    for (const fn of targets) {
      await fetch(`/api/reject/${encodeURIComponent(studioCarId)}/${encodeURIComponent(fn)}`, {
        method: 'POST',
        credentials: 'same-origin'
      });
    }
    if (fb) {
      fb.textContent = `Marked ${targets.length} photo(s) as rejected.`;
      fb.classList.remove('hidden');
      setTimeout(() => fb.classList.add('hidden'), 3500);
    }
    studioSelectedFilenames.clear();
    await fetchState();
  }

  async function saveStudioFrameToGallery(inPlace = false, removePlateCover = false, targetFilenames = null) {
    const captionOn = document.getElementById('studio-caption-toggle')?.checked ?? true;
    const model = document.getElementById('studio-model-input')?.value || '';
    const price = document.getElementById('studio-price-input')?.value || '';
    const specs = document.getElementById('studio-specs-input')?.value || '';
    const fb = document.getElementById('studio-save-feedback');
    const filenamesList = (Array.isArray(targetFilenames) && targetFilenames.length > 0)
      ? targetFilenames
      : (studioFilename ? [studioFilename] : ['showroom.jpg']);

    const bodyPayload = {
      car_id: studioCarId || 'SXX-1234-A',
      filename: studioFilename || filenamesList[0],
      filenames: filenamesList,
      ratio: studioRatio,
      fit_mode: studioFitMode,
      template_style: studioTemplate,
      offset_x: studioOffsetX,
      offset_y: studioOffsetY,
      caption: captionOn,
      car_model: model,
      car_price: price,
      car_specs: specs,
      in_place: Boolean(inPlace),
      remove_plate_cover: Boolean(removePlateCover),
      quad_pct: studioQuadPct
    };

    const res = await fetch('/api/frame-save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(bodyPayload)
    });
    if (res.ok) {
      const data = await res.json();
      studioFilename = data.saved_filename || studioFilename;
      plateQuadModified = false;
      studioSelectedFilenames.clear();
      if (plateAdjustMode) {
        togglePlateAdjustMode(false);
      }
      if (fb) {
        const count = data.processed_count || filenamesList.length;
        if (data.plate_cover_removed) {
          fb.textContent = count > 1
            ? `Removed plate cover & approved ${count} photos in Gallery!`
            : `Removed plate cover & saved ${data.saved_filename} to Gallery!`;
        } else if (data.approved_from_review) {
          fb.textContent = count > 1
            ? `Approved & saved ${count} selected photos to ${data.car_id} in Gallery!`
            : `Approved & saved ${data.saved_filename} to ${data.car_id} in Gallery!`;
        } else {
          fb.textContent = count > 1
            ? `Saved ${count} selected photos to ${data.car_id} in Gallery!`
            : `Saved ${data.saved_filename} to ${data.car_id} in Gallery!`;
        }
        fb.classList.remove('hidden');
        setTimeout(() => fb.classList.add('hidden'), 4000);
      }
      await fetchState();
      refreshStudioCanvas();
    }
  }

  function exportStudioFrame() {
    window.location.href = buildStudioRenderUrl(1);
  }

  // =========================================================================
  // SCREEN 4: PROFILE & DEALERSHIP SETTINGS LOGIC
  // =========================================================================
  let profileAuthMode = 'signin';

  function setProfileAuthMode(mode) {
    profileAuthMode = (mode === 'signup') ? 'signup' : 'signin';
    const isSignup = profileAuthMode === 'signup';

    const tabSignin = document.getElementById('auth-tab-signin');
    const tabSignup = document.getElementById('auth-tab-signup');
    if (tabSignin && tabSignup) {
      tabSignin.className = !isSignup
        ? 'py-2 rounded-xl text-xs font-bold bg-white text-on-surface shadow-sm transition-all'
        : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
      tabSignup.className = isSignup
        ? 'py-2 rounded-xl text-xs font-bold bg-white text-on-surface shadow-sm transition-all'
        : 'py-2 rounded-xl text-xs font-semibold text-on-surface-variant hover:text-on-surface transition-all';
    }

    const titleEl = document.getElementById('auth-card-title');
    if (titleEl) titleEl.textContent = isSignup ? 'Create Profile Account' : 'Sign in to Profile';

    const confirmWrap = document.getElementById('auth-confirm-wrap');
    if (confirmWrap) confirmWrap.classList.toggle('hidden', !isSignup);

    const submitLabel = document.getElementById('auth-submit-label');
    if (submitLabel) submitLabel.textContent = isSignup ? 'Create Account' : 'Sign In';

    const switchPrompt = document.getElementById('auth-switch-prompt');
    if (switchPrompt) switchPrompt.textContent = isSignup ? 'Already have an account?' : "Don't have an account?";

    const switchLink = document.getElementById('auth-switch-link');
    if (switchLink) switchLink.textContent = isSignup ? 'Sign in' : 'Create account';

    const fb = document.getElementById('profile-auth-feedback');
    if (fb) fb.classList.add('hidden');
  }

  function toggleProfileAuthMode() {
    setProfileAuthMode(profileAuthMode === 'signin' ? 'signup' : 'signin');
  }

  async function submitProfileAuth() {
    const email = (document.getElementById('auth-email-input')?.value || '').trim();
    const password = document.getElementById('auth-password-input')?.value || '';
    const confirmPassword = document.getElementById('auth-confirm-input')?.value || '';

    if (!email || !email.includes('@')) {
      showProfileFeedback('profile-auth-feedback', 'Please enter a valid email address.', true);
      return;
    }
    if (!password) {
      showProfileFeedback('profile-auth-feedback', 'Please enter your password.', true);
      return;
    }

    const endpoint = profileAuthMode === 'signup' ? '/api/profile/register' : '/api/profile/login';
    const body = profileAuthMode === 'signup'
      ? { email: email, password: password, confirm_password: confirmPassword }
      : { email: email, password: password };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(body)
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        document.getElementById('auth-password-input').value = '';
        const confEl = document.getElementById('auth-confirm-input');
        if (confEl) confEl.value = '';
        studioCarId = null;
        studioFilename = null;
        await fetchState();
        refreshBrandLogoImages();
        switchTab(activeTab);
      } else {
        showProfileFeedback('profile-auth-feedback', data.detail || 'Authentication failed.', true);
      }
    } catch (err) {
      showProfileFeedback('profile-auth-feedback', 'Network error while signing in.', true);
    }
  }

  let googleModalLinkMode = false;
  let gsiScriptLoaded = false;

  function ensureGoogleGsiScript(callback) {
    if (window.google && window.google.accounts && window.google.accounts.id) {
      callback();
      return;
    }
    if (gsiScriptLoaded) return;
    gsiScriptLoaded = true;
    const s = document.createElement('script');
    s.src = 'https://accounts.google.com/gsi/client';
    s.async = true;
    s.defer = true;
    s.onload = () => { if (callback) callback(); };
    document.head.appendChild(s);
  }

  function renderGoogleGsiButtonIfConfigured() {
    const prof = (appState && appState.profile) ? appState.profile : {};
    const cid = (prof.google_client_id || '').trim();
    const pill = document.getElementById('google-oauth-status-pill');
    const cidInput = document.getElementById('oauth-client-id-input');
    if (cidInput && cid && !cidInput.value) cidInput.value = cid;

    const hintEl = document.getElementById('oauth-callback-uri-hint');
    if (hintEl) hintEl.textContent = window.location.origin + '/api/auth/google/callback';

    if (!cid) {
      if (pill) {
        pill.textContent = 'Client ID Not Set';
        pill.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800';
      }
      return;
    }
    if (pill) {
      pill.textContent = 'OAuth 2.0 Ready';
      pill.className = 'px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700';
    }
    ensureGoogleGsiScript(() => {
      if (!window.google || !window.google.accounts || !window.google.accounts.id) return;
      const container = document.getElementById('g_id_signin_container');
      if (!container) return;
      container.innerHTML = '';
      window.google.accounts.id.initialize({
        client_id: cid,
        callback: handleGoogleCredentialResponse
      });
      window.google.accounts.id.renderButton(container, {
        theme: 'outline',
        size: 'large',
        width: 320,
        text: googleModalLinkMode ? 'continue_with' : 'signin_with'
      });
    });
  }

  async function handleGoogleCredentialResponse(response) {
    if (!response || !response.credential) return;
    try {
      const res = await fetch('/api/profile/google-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          credential: response.credential,
          link_account: googleModalLinkMode
        })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        closeGoogleLoginModal();
        studioCarId = null;
        studioFilename = null;
        await fetchState();
        refreshBrandLogoImages();
        switchTab(activeTab);
        showProfileFeedback('profile-cred-feedback', 'Verified & connected with Google OAuth!', false);
      } else {
        showProfileFeedback('google-login-feedback', data.detail || 'Google token verification failed.', true);
      }
    } catch (err) {
      showProfileFeedback('google-login-feedback', 'Network error verifying Google token.', true);
    }
  }

  function startGoogleOAuthRedirect() {
    const prof = (appState && appState.profile) ? appState.profile : {};
    if (!prof.google_client_id) {
      const drawer = document.getElementById('oauth-config-drawer');
      if (drawer) drawer.classList.remove('hidden');
      showProfileFeedback('google-login-feedback', 'Please configure your Google Cloud OAuth Client ID & Secret below first, or connect your Google email directly.', true);
      return;
    }
    const mode = googleModalLinkMode ? 'link' : 'login';
    window.location.href = `/api/auth/google/start?mode=${mode}`;
  }

  async function saveGoogleOAuthConfig() {
    const cid = (document.getElementById('oauth-client-id-input')?.value || '').trim();
    const sec = (document.getElementById('oauth-client-secret-input')?.value || '').trim();
    try {
      const res = await fetch('/api/profile/oauth-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ google_client_id: cid, google_client_secret: sec })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        appState.profile = data.profile;
        renderGoogleGsiButtonIfConfigured();
        showProfileFeedback('google-login-feedback', 'Google OAuth 2.0 credentials saved to SQLite!', false);
      }
    } catch (err) {
      showProfileFeedback('google-login-feedback', 'Could not save OAuth settings.', true);
    }
  }

  function openGoogleLoginModal(isLinking) {
    googleModalLinkMode = Boolean(isLinking);
    const modal = document.getElementById('google-login-modal');
    if (modal) modal.classList.remove('hidden');
    const fb = document.getElementById('google-login-feedback');
    if (fb) fb.classList.add('hidden');

    const titleEl = document.getElementById('google-modal-title');
    if (titleEl) titleEl.textContent = googleModalLinkMode ? 'Link Google Account' : 'Sign in with Google';

    renderGoogleGsiButtonIfConfigured();

    const emailInput = document.getElementById('google-email-input');
    const authEmail = (document.getElementById('auth-email-input')?.value || '').trim();
    if (emailInput) {
      if (authEmail && !emailInput.value) emailInput.value = authEmail;
      setTimeout(() => emailInput.focus(), 50);
    }
  }

  function closeGoogleLoginModal() {
    const modal = document.getElementById('google-login-modal');
    if (modal) modal.classList.add('hidden');
  }

  async function submitGoogleEmailLogin() {
    const email = (document.getElementById('google-email-input')?.value || '').trim();
    if (!email || !email.includes('@')) {
      showProfileFeedback('google-login-feedback', 'Please enter a valid Google email address.', true);
      return;
    }
    try {
      const res = await fetch('/api/profile/google-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          email: email,
          link_account: googleModalLinkMode
        })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        closeGoogleLoginModal();
        studioCarId = null;
        studioFilename = null;
        await fetchState();
        refreshBrandLogoImages();
        switchTab(activeTab);
        if (googleModalLinkMode) {
          showProfileFeedback('profile-cred-feedback', `Linked Google account (${email})!`, false);
        }
      } else {
        showProfileFeedback('google-login-feedback', data.detail || 'Google sign-in failed.', true);
      }
    } catch (err) {
      showProfileFeedback('google-login-feedback', 'Network error during Google sign-in.', true);
    }
  }

  async function handleGoogleLinkAction() {
    const prof = (appState && appState.profile) ? appState.profile : {};
    if (prof.google_linked) {
      try {
        const res = await fetch('/api/profile/google-unlink', {
          method: 'POST',
          credentials: 'same-origin'
        });
        const data = await res.json().catch(() => ({}));
        if (res.ok) {
          appState.profile = data.profile;
          populateProfilePage();
          showProfileFeedback('profile-cred-feedback', 'Google account unlinked.', false);
        } else {
          showProfileFeedback('profile-cred-feedback', data.detail || 'Could not unlink Google account.', true);
        }
      } catch (err) {
        showProfileFeedback('profile-cred-feedback', 'Network error unlinking Google account.', true);
      }
    } else {
      openGoogleLoginModal(true);
    }
  }

  async function openSecuritySessionsModal() {
    const modal = document.getElementById('security-sessions-modal');
    if (modal) modal.classList.remove('hidden');
    await refreshSecuritySessionsModal();
  }

  function closeSecuritySessionsModal() {
    const modal = document.getElementById('security-sessions-modal');
    if (modal) modal.classList.add('hidden');
  }

  async function refreshSecuritySessionsModal() {
    const sessContainer = document.getElementById('security-sessions-list');
    const auditContainer = document.getElementById('security-audit-list');
    try {
      const res = await fetch('/api/profile/security', { credentials: 'same-origin' });
      if (!res.ok) return;
      const data = await res.json();
      const sessions = data.sessions || [];
      const logs = data.audit_logs || [];

      if (sessContainer) {
        sessContainer.innerHTML = sessions.length === 0
          ? '<p class="text-xs text-on-surface-variant p-3">No active token sessions.</p>'
          : sessions.map(s => `
              <div class="p-3.5 rounded-2xl bg-surface border border-outline-variant/30 flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-on-surface">Session #${s.id_prefix}</span>
                    ${s.is_current ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Current Browser</span>' : ''}
                  </div>
                  <p class="text-[11px] text-on-surface-variant truncate mt-0.5">IP: ${s.ip_address} • ${s.user_agent}</p>
                </div>
                <span class="text-[10px] text-outline shrink-0">${(s.last_active_at || '').slice(0, 19).replace('T', ' ')}</span>
              </div>
            `).join('');
      }

      if (auditContainer) {
        auditContainer.innerHTML = logs.length === 0
          ? '<p class="text-xs text-on-surface-variant p-3">No security events recorded yet.</p>'
          : logs.map(ev => `
              <div class="px-3.5 py-2.5 flex items-center justify-between gap-3">
                <div class="min-w-0">
                  <span class="font-bold text-on-surface uppercase tracking-wider text-[10px] px-2 py-0.5 rounded bg-surface-container mr-1.5">${ev.event_type}</span>
                  <span class="text-on-surface-variant">${ev.detail || ev.email}</span>
                </div>
                <span class="text-[10px] text-outline shrink-0">${(ev.created_at || '').slice(0, 19).replace('T', ' ')}</span>
              </div>
            `).join('');
      }
    } catch (err) {
      console.error('Security modal fetch error:', err);
    }
  }

  async function revokeOtherSessions() {
    try {
      const res = await fetch('/api/profile/sessions/revoke-others', {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        await refreshSecuritySessionsModal();
      }
    } catch (err) {
      console.error('Revoke sessions error:', err);
    }
  }

  async function logoutProfileAccount() {
    try {
      const res = await fetch('/api/profile/logout', {
        method: 'POST',
        credentials: 'same-origin'
      });
      if (res.ok) {
        uploadFilesQueue = [];
        studioCarId = null;
        studioFilename = null;
        selectedPhotoKeys.clear();
        selectedCarIds.clear();
        renderUploadQueue();
        await fetchState();
        refreshBrandLogoImages();
        switchTab(activeTab);
      }
    } catch (err) {
      console.error('Logout error:', err);
    }
  }

  function openChangePasswordModal() {
    const modal = document.getElementById('change-password-modal');
    if (modal) modal.classList.remove('hidden');
    const fb = document.getElementById('modal-password-feedback');
    if (fb) fb.classList.add('hidden');
    const curEl = document.getElementById('profile-current-password');
    const newEl = document.getElementById('profile-new-password');
    const confEl = document.getElementById('profile-confirm-password');
    if (curEl) curEl.value = '';
    if (newEl) newEl.value = '';
    if (confEl) confEl.value = '';
    setTimeout(() => { if (curEl) curEl.focus(); }, 50);
  }

  function closeChangePasswordModal() {
    const modal = document.getElementById('change-password-modal');
    if (modal) modal.classList.add('hidden');
  }

  function syncUiWithProfile(prof) {
    if (!prof) return;
    const isLoggedIn = Boolean(prof.is_logged_in);
    const dealerNameEl = document.getElementById('header-dealer-name');
    if (dealerNameEl) dealerNameEl.textContent = prof.dealer_name || 'Forest Wheel';

    const taglineEl = document.getElementById('header-dealer-tagline');
    if (taglineEl) taglineEl.textContent = prof.dealer_tagline || 'Plate Studio';

    const displayUser = isLoggedIn ? (prof.email || prof.username || 'Account') : 'Sign In';
    const userLabelEl = document.getElementById('header-username-label');
    if (userLabelEl) userLabelEl.textContent = displayUser;

    const avatarEl = document.getElementById('header-user-avatar');
    if (avatarEl) avatarEl.textContent = ((displayUser || 'S')[0] || 'S').toUpperCase();

    const headerSignoutBtn = document.getElementById('header-signout-btn');
    if (headerSignoutBtn) {
      headerSignoutBtn.classList.toggle('hidden', !isLoggedIn);
      headerSignoutBtn.classList.toggle('flex', isLoggedIn);
    }

    const customBadge = document.getElementById('profile-logo-custom-badge');
    if (customBadge) customBadge.classList.toggle('hidden', !prof.has_custom_logo);

    // Pre-fill default specs in Upload page if empty
    const uploadSpecsInput = document.getElementById('input-car-specs');
    if (uploadSpecsInput && prof.default_specs) {
      uploadSpecsInput.value = prof.default_specs;
    }
  }

  function populateProfilePage() {
    const prof = (appState && appState.profile) ? appState.profile : {};
    const isLoggedIn = Boolean(prof.is_logged_in);

    if (!isLoggedIn) {
      setProfileAuthMode(prof.has_account ? 'signin' : 'signup');
      return;
    }

    const activeEmail = prof.email || prof.username || 'user@forestwheel.com';
    const signedInEmailEl = document.getElementById('profile-signed-in-email');
    if (signedInEmailEl) signedInEmailEl.textContent = activeEmail;

    const acctEmailEl = document.getElementById('profile-acct-email-display');
    if (acctEmailEl) acctEmailEl.textContent = activeEmail;

    const acctIdBadge = document.getElementById('profile-acct-id-badge');
    if (acctIdBadge) acctIdBadge.textContent = prof.user_id ? `SQLite #${prof.user_id}` : 'SQLite Active';

    const acctAvatarEl = document.getElementById('profile-acct-avatar');
    if (acctAvatarEl) acctAvatarEl.textContent = ((activeEmail[0] || 'U')).toUpperCase();

    const providerBadgeEl = document.getElementById('profile-acct-provider-badge');
    if (providerBadgeEl) {
      if (prof.auth_provider === 'both') {
        providerBadgeEl.textContent = 'Email + Google';
      } else if (prof.auth_provider === 'google') {
        providerBadgeEl.textContent = 'Google OAuth';
      } else {
        providerBadgeEl.textContent = 'Email Account';
      }
    }

    const gLinkStatus = document.getElementById('profile-google-link-status');
    const gLinkBtn = document.getElementById('btn-google-link-action');
    if (gLinkStatus && gLinkBtn) {
      if (prof.google_linked && prof.google_email) {
        gLinkStatus.textContent = `Linked: ${prof.google_email}`;
        gLinkStatus.className = 'text-emerald-700 font-semibold truncate';
        gLinkBtn.textContent = 'Unlink';
        gLinkBtn.className = 'text-xs font-bold text-error hover:underline shrink-0';
      } else {
        gLinkStatus.textContent = 'Google email not linked';
        gLinkStatus.className = 'text-on-surface-variant truncate';
        gLinkBtn.textContent = 'Link Google';
        gLinkBtn.className = 'text-xs font-bold text-primary hover:underline shrink-0';
      }
    }

    const nameInput = document.getElementById('profile-dealer-name');
    if (nameInput) nameInput.value = prof.dealer_name || 'Forest Wheel';

    const tagInput = document.getElementById('profile-dealer-tagline');
    if (tagInput) tagInput.value = prof.dealer_tagline || 'Plate Studio';

    const specsInput = document.getElementById('profile-default-specs');
    if (specsInput) specsInput.value = prof.default_specs || '';

    const currInput = document.getElementById('profile-currency-prefix');
    if (currInput) currInput.value = prof.currency_prefix || 'S$';

    const wmToggle = document.getElementById('profile-watermark-toggle');
    if (wmToggle) wmToggle.checked = Boolean(prof.show_logo_watermark);

    // Update Workspace Overview Stats
    const outCars = appState.cars_output || {};
    const revCars = appState.cars_review || {};
    const allCarIds = new Set([...Object.keys(outCars), ...Object.keys(revCars)]);
    let readyCount = 0;
    let reviewCount = 0;
    Object.values(outCars).forEach(arr => { readyCount += (arr ? arr.length : 0); });
    Object.values(revCars).forEach(arr => { reviewCount += (arr ? arr.length : 0); });

    const elCars = document.getElementById('stat-total-cars');
    if (elCars) elCars.textContent = String(allCarIds.size);
    const elReady = document.getElementById('stat-ready-photos');
    if (elReady) elReady.textContent = String(readyCount);
    const elRev = document.getElementById('stat-review-photos');
    if (elRev) elRev.textContent = String(reviewCount);
    const elPreset = document.getElementById('stat-active-preset');
    if (elPreset) {
      const fcfg = appState.frame_config || {};
      const r = fcfg.ratio || studioRatio || '1:1';
      const fm = (fcfg.fit_mode || studioFitMode) === 'fill' ? 'Fill' : 'Fit';
      elPreset.textContent = `${r} • ${fm}`;
    }
  }

  function refreshBrandLogoImages() {
    const bust = '/media/brand-logo?t=' + Date.now();
    const headerImg = document.getElementById('header-brand-logo-img');
    if (headerImg) headerImg.src = bust;
    const prevImg = document.getElementById('profile-logo-preview-img');
    if (prevImg) prevImg.src = bust;
    const ovBust = '/media/plate-overlay?t=' + Date.now();
    const ovImg = document.getElementById('plate-overlay-preview-img');
    if (ovImg) ovImg.src = ovBust;
    const calibOv = document.getElementById('plate-calib-cover-img');
    if (calibOv) calibOv.setAttribute('href', ovBust);
  }

  async function uploadBrandLogo(files) {
    if (!files || !files.length) return;
    const fd = new FormData();
    fd.append('file', files[0]);
    try {
      const res = await fetch('/api/profile/logo', {
        method: 'POST',
        credentials: 'same-origin',
        body: fd
      });
      if (res.ok) {
        refreshBrandLogoImages();
        await fetchState();
        showProfileFeedback('profile-brand-feedback', 'Dealership logo uploaded!', false);
      } else {
        showProfileFeedback('profile-brand-feedback', 'Failed to upload logo image.', true);
      }
    } catch (err) {
      console.error('Upload brand logo error:', err);
    }
  }

  async function resetBrandLogo() {
    try {
      const res = await fetch('/api/profile/logo', {
        method: 'DELETE',
        credentials: 'same-origin'
      });
      if (res.ok) {
        refreshBrandLogoImages();
        await fetchState();
        showProfileFeedback('profile-brand-feedback', 'Reset to default Forest Wheel logo.', false);
      }
    } catch (err) {
      console.error('Reset brand logo error:', err);
    }
  }

  async function saveProfileSettings() {
    const payload = {
      dealer_name: (document.getElementById('profile-dealer-name')?.value || 'Forest Wheel').trim(),
      dealer_tagline: (document.getElementById('profile-dealer-tagline')?.value || 'Plate Studio').trim(),
      default_specs: (document.getElementById('profile-default-specs')?.value || '').trim(),
      currency_prefix: (document.getElementById('profile-currency-prefix')?.value || 'S$').trim(),
      show_logo_watermark: Boolean(document.getElementById('profile-watermark-toggle')?.checked)
    };
    try {
      const res = await fetch('/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        appState.profile = data.profile;
        syncUiWithProfile(data.profile);
        showProfileFeedback('profile-brand-feedback', 'Brand settings saved!', false);
      } else {
        showProfileFeedback('profile-brand-feedback', 'Could not save brand settings.', true);
      }
    } catch (err) {
      console.error('Save profile error:', err);
    }
  }

  async function saveProfileCredentials() {
    const currentPassword = document.getElementById('profile-current-password')?.value || '';
    const newPassword = document.getElementById('profile-new-password')?.value || '';
    const confirmPassword = document.getElementById('profile-confirm-password')?.value || '';

    if (!currentPassword) {
      showProfileFeedback('modal-password-feedback', 'Please enter your current password.', true);
      return;
    }
    if (!newPassword || newPassword.length < 4) {
      showProfileFeedback('modal-password-feedback', 'New password must be at least 4 characters.', true);
      return;
    }
    if (newPassword !== confirmPassword) {
      showProfileFeedback('modal-password-feedback', 'New password and confirmation do not match.', true);
      return;
    }

    try {
      const res = await fetch('/api/profile/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
          confirm_password: confirmPassword
        })
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        document.getElementById('profile-current-password').value = '';
        document.getElementById('profile-new-password').value = '';
        document.getElementById('profile-confirm-password').value = '';
        closeChangePasswordModal();
        showProfileFeedback('profile-cred-feedback', 'Password updated in SQLite database!', false);
        await fetchState();
      } else {
        showProfileFeedback('modal-password-feedback', data.detail || 'Failed to update password.', true);
      }
    } catch (err) {
      showProfileFeedback('modal-password-feedback', 'Error updating password.', true);
    }
  }

  function showProfileFeedback(elId, msg, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = msg;
    el.className = isError
      ? 'text-xs font-semibold text-error'
      : 'text-xs font-semibold text-emerald-700';
    el.classList.remove('hidden');
    setTimeout(() => el.classList.add('hidden'), 4500);
  }

  // Initialize on page load
  window.addEventListener('DOMContentLoaded', async () => {
    renderUploadQueue();
    await fetchState();
    const params = new URLSearchParams(window.location.search);
    if (params.get('tab') === 'profile') {
      switchTab('profile');
    }
  });
</script>
</body>
</html>
"""
